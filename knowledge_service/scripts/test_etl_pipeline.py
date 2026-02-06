#!/usr/bin/env python3
"""
ETL Pipeline 테스트 스크립트

knowledge_data/documents 폴더의 문서들을 처리하여:
1. 문서 파싱
2. 시맨틱 청킹
3. 임베딩 생성 (BGE-M3)
4. Elasticsearch 저장
5. Neo4j 저장 (엔티티/관계)

Usage:
    cd knowledge_service
    python scripts/test_etl_pipeline.py
"""

import asyncio
import os
import sys
from pathlib import Path

# 프로젝트 루트를 PYTHONPATH에 추가
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

# 환경변수 로드
from dotenv import load_dotenv
load_dotenv(project_root / ".env")


async def main():
    print("\n" + "=" * 60)
    print("  ETL Pipeline 테스트")
    print("  날짜:", __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M"))
    print("=" * 60 + "\n")

    # 1. 데이터 소스 확인
    print("[1단계] 데이터 소스 확인")
    data_dir = project_root.parent / "knowledge_data" / "documents"

    if not data_dir.exists():
        print(f"[ERROR] 데이터 디렉토리 없음: {data_dir}")
        return

    # 파일 개수 확인
    all_files = list(data_dir.rglob("*"))
    pdf_files = list(data_dir.rglob("*.pdf"))
    docx_files = list(data_dir.rglob("*.docx"))
    md_files = list(data_dir.rglob("*.md"))

    print(f"  - 데이터 디렉토리: {data_dir}")
    print(f"  - 총 파일 수: {len([f for f in all_files if f.is_file()])}")
    print(f"  - PDF 파일: {len(pdf_files)}개")
    print(f"  - DOCX 파일: {len(docx_files)}개")
    print(f"  - Markdown 파일: {len(md_files)}개")

    # 하위 폴더 확인
    subdirs = [d for d in data_dir.iterdir() if d.is_dir()]
    print(f"  - 하위 폴더: {[d.name for d in subdirs]}")

    # 2. 서비스 초기화
    print("\n[2단계] 서비스 초기화")

    try:
        from app.services.initial_data_loader import InitialDataLoader, DataSource, DocType

        # ETL 로더 초기화 (임베딩만 활성화, 엔티티 추출은 시간이 오래 걸리므로 비활성화)
        # embedding_service는 InitialDataLoader 내부에서 자동 초기화됨
        loader = InitialDataLoader(
            project_root=str(project_root),
            enable_embeddings=True,
            enable_entity_extraction=False,  # 시간 절약
            continue_on_error=True,
            max_retries=2,
        )
        print("  [OK] InitialDataLoader 초기화")

    except Exception as e:
        print(f"  [ERROR] 서비스 초기화 실패: {e}")
        import traceback
        traceback.print_exc()
        return

    # 3. 데이터 소스 등록
    print("\n[3단계] 데이터 소스 등록")

    sources = [
        DataSource(
            name="AI",
            path=str(data_dir / "AI"),
            doc_type=DocType.TECHNICAL,
            description="AI/RAG 관련 문서",
        ),
        DataSource(
            name="법률자료",
            path=str(data_dir / "법률자료"),
            doc_type=DocType.POLICY,
            description="법률 문서",
        ),
        DataSource(
            name="technical",
            path=str(data_dir / "technical"),
            doc_type=DocType.TECHNICAL,
            description="기술 문서",
        ),
        DataSource(
            name="guides",
            path=str(data_dir / "guides"),
            doc_type=DocType.GUIDE,
            description="가이드 문서",
        ),
    ]

    for source in sources:
        if Path(source.path).exists():
            loader.add_source(source)
            file_count = len(list(Path(source.path).rglob("*")))
            print(f"  [+] {source.name}: {file_count}개 항목")
        else:
            print(f"  [-] {source.name}: 경로 없음 (건너뜀)")

    # 4. 파일 탐색
    print("\n[4단계] 파일 탐색 (Discovery)")

    files = loader.discover_files()
    print(f"  - 발견된 파일: {len(files)}개")

    # 최대 5개만 표시
    for i, f in enumerate(files[:5]):
        print(f"    [{i+1}] {f.file_name} ({f.file_size:,} bytes)")
    if len(files) > 5:
        print(f"    ... 그 외 {len(files) - 5}개 파일")

    # 5. ETL 실행 (샘플만)
    print("\n[5단계] ETL 파이프라인 실행 (샘플 테스트)")

    # 너무 많으면 샘플만 처리
    max_files = 3
    if len(files) > max_files:
        print(f"  [INFO] 테스트를 위해 {max_files}개 파일만 처리합니다.")
        # 작은 파일 우선 선택
        files_sorted = sorted(files, key=lambda f: f.file_size)
        sample_files = files_sorted[:max_files]

        # 기존 소스 제거하고 샘플 파일만 처리하도록 설정
        loader.data_sources.clear()

        # 샘플 파일들을 개별 소스로 등록
        for f in sample_files:
            source = DataSource(
                name=f"sample_{f.file_name[:20]}",
                path=str(f.file_path.parent),
                extensions=[f.extension],
            )
            loader.add_source(source)

        print(f"  샘플 파일:")
        for f in sample_files:
            print(f"    - {f.file_name} ({f.file_size:,} bytes)")

    try:
        summary = await loader.load_all()

        print("\n" + "=" * 60)
        print("  ETL 결과 요약")
        print("=" * 60)
        print(f"  - 총 파일: {summary.total_files}")
        print(f"  - 성공: {summary.success_count}")
        print(f"  - 실패: {summary.failed_count}")
        print(f"  - 건너뜀: {summary.skipped_count}")
        print(f"  - 생성된 청크: {summary.total_chunks}")
        print(f"  - 추출된 엔티티: {summary.total_entities}")
        print(f"  - 처리 시간: {summary.total_time_ms:.1f}ms")
        print(f"  - 성공률: {summary.success_rate * 100:.1f}%")

    except Exception as e:
        print(f"  [ERROR] ETL 실행 실패: {e}")
        import traceback
        traceback.print_exc()
        return

    # 6. 저장소 확인
    print("\n[6단계] 저장소 확인")

    # Elasticsearch 확인
    try:
        from elasticsearch import Elasticsearch
        es = Elasticsearch(["http://localhost:9200"])

        # 인덱스 목록
        indices = es.indices.get_alias(index="*")
        rag_indices = [idx for idx in indices.keys() if "rag" in idx.lower() or "knowledge" in idx.lower()]
        print(f"  [ES] RAG 관련 인덱스: {rag_indices}")

        for idx in rag_indices:
            count = es.count(index=idx)["count"]
            print(f"       - {idx}: {count}개 문서")

    except Exception as e:
        print(f"  [ES] 확인 실패: {e}")

    # Neo4j 확인
    try:
        from neo4j import GraphDatabase

        neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        neo4j_pass = os.getenv("NEO4J_PASSWORD", "neo4j_dev_2026!")

        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_pass))

        with driver.session() as session:
            # 노드 수 확인
            result = session.run("MATCH (n) RETURN labels(n) as labels, count(*) as count")
            print(f"  [Neo4j] 노드 현황:")
            for record in result:
                print(f"       - {record['labels']}: {record['count']}개")

            # 관계 수 확인
            result = session.run("MATCH ()-[r]->() RETURN type(r) as type, count(*) as count")
            print(f"  [Neo4j] 관계 현황:")
            for record in result:
                print(f"       - {record['type']}: {record['count']}개")

        driver.close()

    except Exception as e:
        print(f"  [Neo4j] 확인 실패: {e}")

    print("\n" + "=" * 60)
    print("  ETL 테스트 완료")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
