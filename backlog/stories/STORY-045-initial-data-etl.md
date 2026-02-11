# STORY-045: 초기 데이터 ETL

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-34 |
| **Epic** | EPIC-002 |
| **Status** | Done |
| **Priority** | High |
| **Story Points** | 3 |
| **Assignee** | Data |
| **Sprint** | 3 |

---

## User Story

**As a** 시스템 관리자,
**I want** 초기 문서 데이터를 ES/Neo4j에 로딩,
**So that** 검색 시스템이 실제 데이터로 동작할 수 있음.

---

## Acceptance Criteria

- [ ] **Given** 프로젝트 문서 (~65개), **When** ETL 실행, **Then** 모든 문서가 ES/Neo4j에 저장
- [ ] **Given** Markdown 문서, **When** 파싱, **Then** 청크 분할 및 임베딩 생성
- [ ] **Given** ETL 완료, **When** 검증, **Then** 문서 수, 청크 수, 엔티티 수 확인
- [ ] **Given** 검색 테스트, **When** 샘플 쿼리 실행, **Then** 관련 문서 검색 성공
- [ ] **Given** ETL 오류 시, **When** 실행, **Then** 에러 로그 및 재시도 가능

---

## Tasks

- [ ] 초기 데이터 폴더 구조 설정 (knowledge_data/)
- [ ] Bootstrap 스크립트 작성 (문서 복사)
- [ ] InitialDataLoader 클래스 구현
- [ ] Elasticsearch 인덱스 매핑 생성
- [ ] Neo4j 제약조건/인덱스 생성
- [ ] ETL 실행 스크립트 작성
- [ ] 검증 스크립트 작성
- [ ] 문서화

---

## 기술 노트

### 데이터 소스 (knowledge_data/)

```
knowledge_data/
├── documents/
│   ├── technical/          # 기술 문서 (~24개)
│   │   ├── hybrid_rag_platform_detailed_design.md
│   │   ├── backend_detailed_design.md
│   │   ├── frontend_detailed_design.md
│   │   └── ...
│   ├── guides/             # 가이드/매뉴얼 (~4개)
│   │   ├── 01.Ralph_Playbook_완전가이드.md
│   │   └── ...
│   └── presentations/      # 발표자료 (~5개)
│       └── *.pptx
├── processed/              # 처리된 데이터 (시스템 생성)
│   ├── chunks/
│   └── embeddings/
└── exports/                # 백업/스냅샷
```

### Bootstrap 스크립트

```bash
#!/bin/bash
# scripts/seed-initial-data.sh

set -e

KNOWLEDGE_DATA="./knowledge_data/documents"

echo "========================================"
echo "  초기 데이터 Seeding"
echo "========================================"

# 기술 문서 복사
mkdir -p "$KNOWLEDGE_DATA/technical"
cp knowledge_service/docs/01_planning/*.md "$KNOWLEDGE_DATA/technical/" 2>/dev/null || true
cp knowledge_service/docs/02_design/*.md "$KNOWLEDGE_DATA/technical/" 2>/dev/null || true

# 가이드 복사
mkdir -p "$KNOWLEDGE_DATA/guides"
cp docs/claude_code_virtual_team_alm_guide/*.md "$KNOWLEDGE_DATA/guides/" 2>/dev/null || true

# 발표자료 복사
mkdir -p "$KNOWLEDGE_DATA/presentations"
cp docs/presentations/*.pptx "$KNOWLEDGE_DATA/presentations/" 2>/dev/null || true

echo "Seeded files:"
find "$KNOWLEDGE_DATA" -type f | wc -l
echo "========================================"
```

### InitialDataLoader

```python
# ai_service/src/etl/initial_data_loader.py
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass
import asyncio

@dataclass
class DataSource:
    category: str
    path: str
    extensions: List[str]
    priority: int = 0

class InitialDataLoader:
    """초기 데이터 ETL 파이프라인"""

    DATA_SOURCES = [
        DataSource("technical", "knowledge_data/documents/technical", [".md"], 0),
        DataSource("guide", "knowledge_data/documents/guides", [".md"], 0),
        DataSource("presentation", "knowledge_data/documents/presentations", [".pptx"], 1),
    ]

    def __init__(
        self,
        parser,
        chunker,
        embedder,
        es_client,
        neo4j_client
    ):
        self.parser = parser
        self.chunker = chunker
        self.embedder = embedder
        self.es_client = es_client
        self.neo4j_client = neo4j_client

    async def load_all(self) -> Dict:
        """전체 데이터 로드"""
        stats = {
            "total_documents": 0,
            "total_chunks": 0,
            "total_entities": 0,
            "by_category": {}
        }

        for source in sorted(self.DATA_SOURCES, key=lambda x: x.priority):
            print(f"\n[{source.category}] 로딩 시작...")
            result = await self._load_source(source)
            stats["total_documents"] += result["documents"]
            stats["total_chunks"] += result["chunks"]
            stats["total_entities"] += result["entities"]
            stats["by_category"][source.category] = result
            print(f"[{source.category}] 완료: {result['documents']}개 문서, {result['chunks']}개 청크")

        return stats

    async def _load_source(self, source: DataSource) -> Dict:
        """개별 소스 로드"""
        files = self._discover_files(source.path, source.extensions)
        results = {"documents": 0, "chunks": 0, "entities": 0, "errors": []}

        for file_path in files:
            try:
                # 1. 파싱
                parsed = await self.parser.parse(file_path)

                # 2. 메타데이터 추출
                metadata = self._extract_metadata(file_path, source.category)

                # 3. 청킹
                chunks = self.chunker.chunk(parsed.content, metadata)

                # 4. 임베딩
                chunks = await self._embed_chunks(chunks)

                # 5. 저장
                await self._save_to_elasticsearch(chunks)
                entities = await self._save_to_neo4j(parsed, chunks, metadata)

                results["documents"] += 1
                results["chunks"] += len(chunks)
                results["entities"] += len(entities)

            except Exception as e:
                print(f"  오류: {file_path} - {e}")
                results["errors"].append({"file": str(file_path), "error": str(e)})

        return results

    def _discover_files(self, path: str, extensions: List[str]) -> List[Path]:
        """파일 탐색"""
        base_path = Path(path)
        if not base_path.exists():
            print(f"  경고: 경로 없음 - {path}")
            return []

        files = []
        for ext in extensions:
            files.extend(base_path.glob(f"**/*{ext}"))
        return sorted(files)

    def _extract_metadata(self, file_path: str, category: str) -> Dict:
        """메타데이터 추출"""
        path = Path(file_path)
        return {
            "file_path": str(path),
            "file_name": path.name,
            "category": category,
            "doc_type": self._classify_doc_type(path),
            "project": "hybrid-rag-knowledge-ops",
            "language": "ko",
        }

    def _classify_doc_type(self, path: Path) -> str:
        """문서 유형 분류"""
        path_str = str(path).lower()
        if "planning" in path_str:
            return "planning"
        elif "design" in path_str:
            return "design"
        elif "guide" in path_str:
            return "guide"
        elif "presentation" in path_str:
            return "presentation"
        return "general"

    async def _embed_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """청크 임베딩 생성"""
        texts = [c["content"] for c in chunks]
        embeddings = await self.embedder.embed_batch(texts)
        for chunk, embedding in zip(chunks, embeddings):
            chunk["embedding"] = embedding
        return chunks

    async def _save_to_elasticsearch(self, chunks: List[Dict]):
        """ES 저장"""
        for chunk in chunks:
            await self.es_client.index(
                index="knowledge_chunks",
                id=chunk["chunk_id"],
                document={
                    "content": chunk["content"],
                    "embedding": chunk["embedding"],
                    "metadata": chunk["metadata"]
                }
            )

    async def _save_to_neo4j(self, parsed, chunks, metadata) -> List[Dict]:
        """Neo4j 저장 (문서, 청크, 엔티티 노드)"""
        # 구현 상세는 STORY-005, 006 참조
        pass
```

### 검증 스크립트

```python
# ai_service/src/etl/validate_initial_data.py
class InitialDataValidation:
    """초기 데이터 검증"""

    EXPECTED_MIN_DOCS = 50
    EXPECTED_MIN_CHUNKS = 500
    EXPECTED_MIN_ENTITIES = 100

    TEST_QUERIES = [
        ("Hybrid RAG 아키텍처", ["hybrid_rag_platform"]),
        ("Keycloak 인증 설정", ["authentication"]),
        ("Frontend React 구조", ["frontend"]),
    ]

    async def run_all(self, es_client, neo4j_client) -> Dict:
        """전체 검증 실행"""
        results = {}

        # 1. 문서 수 검증
        doc_count = await self._count_documents(neo4j_client)
        results["documents"] = {
            "count": doc_count,
            "expected": self.EXPECTED_MIN_DOCS,
            "passed": doc_count >= self.EXPECTED_MIN_DOCS
        }

        # 2. 청크 수 검증
        chunk_count = await self._count_chunks(es_client)
        results["chunks"] = {
            "count": chunk_count,
            "expected": self.EXPECTED_MIN_CHUNKS,
            "passed": chunk_count >= self.EXPECTED_MIN_CHUNKS
        }

        # 3. 검색 품질 검증
        search_results = await self._test_searches(es_client)
        results["search_quality"] = search_results

        all_passed = all(r.get("passed", False) for r in results.values())
        return {"passed": all_passed, "details": results}
```

### ETL 실행 스크립트

```bash
#!/bin/bash
# scripts/load-initial-data.sh

echo "========================================"
echo "  초기 데이터 로딩 시작"
echo "========================================"

# 1. 데이터 Seeding
./scripts/seed-initial-data.sh

# 2. ES/Neo4j 스키마 확인
echo "스키마 확인 중..."
poetry run python -m ai_service.src.etl.ensure_schema

# 3. ETL 실행
echo "ETL 실행 중..."
poetry run python -m ai_service.src.etl.initial_data_loader

# 4. 검증
echo "데이터 검증 중..."
poetry run python -m ai_service.src.etl.validate_initial_data

echo "========================================"
echo "  초기 데이터 로딩 완료"
echo "========================================"
```

### 영향 범위
- `scripts/seed-initial-data.sh` (신규)
- `scripts/load-initial-data.sh` (신규)
- `ai_service/src/etl/initial_data_loader.py` (신규)
- `ai_service/src/etl/validate_initial_data.py` (신규)
- `knowledge_data/` (신규 디렉토리)

---

## 테스트 계획

- [ ] Unit Test: 파일 탐색 로직
- [ ] Unit Test: 메타데이터 추출
- [ ] Integration Test: ES 저장
- [ ] Integration Test: Neo4j 저장
- [ ] E2E Test: 전체 ETL 파이프라인

---

## 참고 자료

- [스프린트 실행 계획서](../../docs/02_스프린트_실행_계획서.md)
- [상세 설계서 v2.4](../../knowledge_service/docs/02_design/01_hybrid_rag_platform_detailed_design.md)
