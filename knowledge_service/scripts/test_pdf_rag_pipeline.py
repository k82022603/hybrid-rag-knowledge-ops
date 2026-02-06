#!/usr/bin/env python3
"""
PDF RAG 파이프라인 통합 테스트

knowledge_data/documents의 PDF 문서를 처리하여:
1. PDF 파싱 (PyMuPDF)
2. 시맨틱 청킹
3. 임베딩 생성 (BGE-M3)
4. Elasticsearch 저장
5. 하이브리드 검색 테스트
6. RAG 답변 생성 (DeepSeek)

Usage:
    cd knowledge_service
    python scripts/test_pdf_rag_pipeline.py
"""

import asyncio
import os
import sys
import hashlib
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 PYTHONPATH에 추가
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

# 환경변수 로드
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

# PyMuPDF 임포트
try:
    import fitz  # PyMuPDF
    print("[OK] PyMuPDF 로드 완료")
except ImportError:
    print("[ERROR] PyMuPDF 미설치: pip install PyMuPDF")
    sys.exit(1)


def extract_pdf_text(pdf_path: str, max_pages: int = 10) -> str:
    """PDF에서 텍스트 추출 (최대 페이지 제한)"""
    doc = fitz.open(pdf_path)
    text_parts = []

    for page_num in range(min(len(doc), max_pages)):
        page = doc[page_num]
        text_parts.append(page.get_text())

    doc.close()
    return "\n\n".join(text_parts)


def chunk_text(text: str, chunk_size: int = 600, overlap: int = 100) -> list[str]:
    """텍스트를 청크로 분할"""
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]

        # 문장 끝에서 자르기 시도
        if end < len(text):
            last_period = chunk.rfind('.')
            last_newline = chunk.rfind('\n')
            cut_point = max(last_period, last_newline)
            if cut_point > chunk_size // 2:
                chunk = chunk[:cut_point + 1]
                end = start + cut_point + 1

        if chunk.strip():
            chunks.append(chunk.strip())

        start = end - overlap

    return chunks


async def main():
    print("\n" + "=" * 60)
    print("  PDF RAG 파이프라인 통합 테스트")
    print(f"  시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60 + "\n")

    # 1. 데이터 소스 확인
    print("[1단계] PDF 문서 확인")
    data_dir = project_root.parent / "knowledge_data" / "documents"

    if not data_dir.exists():
        print(f"[ERROR] 데이터 디렉토리 없음: {data_dir}")
        return

    pdf_files = list(data_dir.rglob("*.pdf"))
    print(f"  - 발견된 PDF: {len(pdf_files)}개")

    # 작은 파일 2개 선택 (테스트용)
    small_pdfs = sorted(pdf_files, key=lambda f: f.stat().st_size)[:2]
    print(f"  - 테스트 대상 (가장 작은 2개):")
    for pdf in small_pdfs:
        size_kb = pdf.stat().st_size / 1024
        print(f"    - {pdf.name} ({size_kb:.1f} KB)")

    # 2. PDF 파싱
    print("\n[2단계] PDF 파싱")
    documents = []

    for pdf_path in small_pdfs:
        try:
            text = extract_pdf_text(str(pdf_path), max_pages=5)
            if text.strip():
                documents.append({
                    "file_name": pdf_path.name,
                    "file_path": str(pdf_path),
                    "content": text,
                    "char_count": len(text)
                })
                print(f"  [OK] {pdf_path.name}: {len(text):,} 문자 추출")
            else:
                print(f"  [SKIP] {pdf_path.name}: 텍스트 없음")
        except Exception as e:
            print(f"  [ERROR] {pdf_path.name}: {e}")

    if not documents:
        print("[ERROR] 파싱된 문서 없음")
        return

    # 3. 청킹
    print("\n[3단계] 시맨틱 청킹")
    all_chunks = []

    for doc in documents:
        chunks = chunk_text(doc["content"], chunk_size=600, overlap=100)
        for i, chunk in enumerate(chunks):
            chunk_id = hashlib.md5(f"{doc['file_name']}_{i}".encode()).hexdigest()[:12]
            all_chunks.append({
                "chunk_id": chunk_id,
                "file_name": doc["file_name"],
                "chunk_index": i,
                "content": chunk,
                "char_count": len(chunk)
            })
        print(f"  - {doc['file_name']}: {len(chunks)}개 청크")

    print(f"  - 총 청크 수: {len(all_chunks)}개")

    # 4. 임베딩 생성
    print("\n[4단계] 임베딩 생성 (BGE-M3)")

    try:
        from app.services.embedding import get_embedding_service
        embedding_service = get_embedding_service()
        print(f"  [OK] EmbeddingService: {embedding_service.model_name}")

        # 청크 텍스트 리스트
        chunk_texts = [c["content"] for c in all_chunks]

        # 배치 임베딩
        print(f"  임베딩 생성 중: {len(chunk_texts)}개 청크...")
        embeddings = await embedding_service.embed_batch(chunk_texts)
        print(f"  [OK] 임베딩 생성 완료: {len(embeddings)}개, 차원: {len(embeddings[0])}")

        # 청크에 임베딩 추가
        for i, chunk in enumerate(all_chunks):
            chunk["embedding"] = embeddings[i]

    except Exception as e:
        print(f"  [ERROR] 임베딩 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return

    # 5. Elasticsearch 저장
    print("\n[5단계] Elasticsearch 저장")

    try:
        from elasticsearch import Elasticsearch
        es = Elasticsearch(["http://localhost:9200"])

        index_name = "rag-pdf-test"

        # 기존 인덱스 삭제 후 재생성
        if es.indices.exists(index=index_name):
            es.indices.delete(index=index_name)
            print(f"  [INFO] 기존 인덱스 '{index_name}' 삭제")

        # 인덱스 생성 (벡터 필드 포함)
        es.indices.create(
            index=index_name,
            body={
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0
                },
                "mappings": {
                    "properties": {
                        "chunk_id": {"type": "keyword"},
                        "file_name": {"type": "keyword"},
                        "chunk_index": {"type": "integer"},
                        "content": {"type": "text", "analyzer": "standard"},
                        "embedding": {
                            "type": "dense_vector",
                            "dims": 1024,
                            "index": True,
                            "similarity": "cosine"
                        }
                    }
                }
            }
        )
        print(f"  [OK] 인덱스 '{index_name}' 생성")

        # 문서 인덱싱
        for chunk in all_chunks:
            es.index(
                index=index_name,
                id=chunk["chunk_id"],
                body={
                    "chunk_id": chunk["chunk_id"],
                    "file_name": chunk["file_name"],
                    "chunk_index": chunk["chunk_index"],
                    "content": chunk["content"],
                    "embedding": chunk["embedding"]
                }
            )

        es.indices.refresh(index=index_name)
        count = es.count(index=index_name)["count"]
        print(f"  [OK] {count}개 청크 인덱싱 완료")

    except Exception as e:
        print(f"  [ERROR] Elasticsearch 저장 실패: {e}")
        import traceback
        traceback.print_exc()
        return

    # 6. 하이브리드 검색 테스트
    print("\n[6단계] 하이브리드 검색 테스트")

    test_queries = [
        "AI 에이전트의 핵심 개념은 무엇인가?",
        "법률 문서의 주요 조항은?",
        "LLM 기반 시스템의 특징"
    ]

    for query in test_queries:
        print(f"\n  쿼리: '{query}'")

        try:
            # 쿼리 임베딩
            query_embedding = (await embedding_service.embed_batch([query]))[0]

            # 하이브리드 검색 (Vector + Keyword)
            response = es.search(
                index=index_name,
                body={
                    "size": 3,
                    "query": {
                        "bool": {
                            "should": [
                                # 키워드 검색
                                {
                                    "match": {
                                        "content": {
                                            "query": query,
                                            "boost": 1.0
                                        }
                                    }
                                },
                                # 벡터 검색
                                {
                                    "script_score": {
                                        "query": {"match_all": {}},
                                        "script": {
                                            "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                                            "params": {"query_vector": query_embedding}
                                        }
                                    }
                                }
                            ]
                        }
                    }
                }
            )

            hits = response["hits"]["hits"]
            print(f"  결과: {len(hits)}개")
            for hit in hits[:2]:
                score = hit["_score"]
                content = hit["_source"]["content"][:100].replace("\n", " ")
                file_name = hit["_source"]["file_name"]
                print(f"    [{score:.2f}] {file_name}: {content}...")

        except Exception as e:
            print(f"  [ERROR] 검색 실패: {e}")

    # 7. RAG 답변 생성 (DeepSeek)
    print("\n[7단계] RAG 답변 생성 (DeepSeek)")

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("  [SKIP] DEEPSEEK_API_KEY 없음")
    else:
        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com"
            )

            # 검색 결과로 컨텍스트 구성
            query = "이 문서들의 핵심 내용을 요약해주세요."
            query_embedding = (await embedding_service.embed_batch([query]))[0]

            response = es.search(
                index=index_name,
                body={
                    "size": 3,
                    "knn": {
                        "field": "embedding",
                        "query_vector": query_embedding,
                        "k": 3,
                        "num_candidates": 10
                    }
                }
            )

            contexts = [hit["_source"]["content"] for hit in response["hits"]["hits"]]
            context_text = "\n\n---\n\n".join(contexts)

            # RAG 프롬프트
            prompt = f"""다음 문서 내용을 바탕으로 질문에 답변해주세요.

## 문서 내용
{context_text}

## 질문
{query}

## 답변 (한국어로 간결하게)"""

            # DeepSeek API 호출
            completion = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.7
            )

            answer = completion.choices[0].message.content
            tokens = completion.usage

            print(f"  [답변]\n  {answer[:500]}...")
            print(f"\n  [토큰] Prompt: {tokens.prompt_tokens}, Completion: {tokens.completion_tokens}")

        except Exception as e:
            print(f"  [ERROR] RAG 생성 실패: {e}")
            import traceback
            traceback.print_exc()

    # 8. 결과 요약
    print("\n" + "=" * 60)
    print("  테스트 결과 요약")
    print("=" * 60)
    print(f"  - 처리된 PDF: {len(documents)}개")
    print(f"  - 생성된 청크: {len(all_chunks)}개")
    print(f"  - Elasticsearch 인덱스: {index_name}")
    print(f"  - 저장된 문서 수: {count}개")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
