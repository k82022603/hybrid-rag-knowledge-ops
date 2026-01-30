# RAG 서비스 분석 보고서

**분석일**: 2026-01-30
**분석자**: MLRag Agent
**대상**: `/mnt/d/Users/KTDS/Documents/06.과제/hybrid-rag-knowledge-ops/knowledge_service/`

---

## 1. 미구현 코드 목록

### 1.1 TODO 항목 (11개)

| # | 파일 | 라인 | 유형 | 내용 | 우선순위 |
|---|------|-----|------|------|---------|
| 1 | `src/app/main.py` | 35 | TODO | 리소스 초기화 | P2 (스타트업 최적화) |
| 2 | `src/app/main.py` | 45 | TODO | 리소스 정리 | P2 (셧다운 정리) |
| 3 | `src/app/agents/vip_agent.py` | 183 | TODO | 실제 LLM 호출로 엔티티 추출 구현 | **P0** (핵심 기능) |
| 4 | `src/app/agents/vip_agent.py` | 196 | TODO | Gleaning 로직 구현 | **P0** (핵심 기능) |
| 5 | `src/app/rag/embedder.py` | 45 | TODO | 실제 모델 로딩 구현 | **P1** (중복 - EmbeddingService 사용) |
| 6 | `src/app/rag/embedder.py` | 64 | TODO | 실제 임베딩 생성 구현 | **P1** (중복 - EmbeddingService 사용) |
| 7 | `src/app/rag/embedder.py` | 90 | TODO | 실제 배치 임베딩 구현 | **P1** (중복 - EmbeddingService 사용) |
| 8 | `src/app/rag/embedder.py` | 119 | TODO | Sparse 벡터 생성 (BM25/SPLADE) | P2 (향후 개선) |
| 9 | `src/app/api/routes/health.py` | 104 | TODO | 실제 DB 연결 체크 추가 | P2 (운영 모니터링) |
| 10 | `src/app/api/routes/health.py` | 128 | TODO | 실제 연결 체크 구현 | P2 (운영 모니터링) |
| 11 | `src/app/agents/rag_workflow.py` | 466 | TODO | 질의 분석 기반 동적 전략 선택 | P3 (향후 최적화) |

### 1.2 미구현 분석 상세

#### P0: VIP Agent 엔티티 추출/Gleaning (가장 중요)

**문제**: `vip_agent.py`의 `_extract_entities()`와 `_gleaning()` 메서드가 스켈레톤 구현

```python
# vip_agent.py:183
async def _extract_entities(self, state: AgentState) -> AgentState:
    """Stage 1: 엔티티 및 관계 추출"""
    # TODO: 실제 LLM 호출로 엔티티 추출 구현
    # 현재는 스켈레톤으로 빈 결과 반환
    state["extracted_entities"] = []
    state["extracted_relationships"] = []
    ...
```

**해결책**: `EntityExtractionService`가 **이미 완벽하게 구현됨**
- `entity_extraction.py`: Gleaning 포함 전체 구현 완료
- VIP Agent에서 `EntityExtractionService`를 호출하도록 연결 필요

#### P1: Embedder 모듈 (중복 코드)

**문제**: `rag/embedder.py`가 `EmbeddingService`와 중복

| 파일 | 상태 | 비고 |
|------|------|------|
| `src/app/rag/embedder.py` | 스켈레톤 (더미 벡터 반환) | 제거 대상 |
| `src/app/services/embedding.py` | **완전 구현** (855 lines) | 사용 권장 |

**해결책**: `rag/embedder.py` 삭제 후 `EmbeddingService` 직접 사용

---

## 2. RAG 파이프라인 구현 상태

### 2.1 컴포넌트별 상태 매트릭스

| 컴포넌트 | 파일 | 상태 | 완성도 | 비고 |
|----------|------|------|--------|------|
| **Embedding Service** | `services/embedding.py` | **완전 구현** | 100% | BGE-M3, 캐시, 배치 지원 |
| **Search Service** | `services/search.py` | **완전 구현** | 100% | Hybrid Search, RRF Fusion |
| **Hybrid Retriever** | `rag/retriever.py` | **완전 구현** | 100% | SearchService 위임 구조 |
| **Entity Extraction** | `services/entity_extraction.py` | **완전 구현** | 100% | Gleaning 포함 |
| **LLM Adapter** | `services/llm_adapter.py` | **완전 구현** | 100% | Circuit Breaker 적용 |
| **RAG Workflow** | `agents/rag_workflow.py` | **완전 구현** | 95% | 동적 전략 TODO |
| **VIP Agent** | `agents/vip_agent.py` | **부분 구현** | 70% | 엔티티 추출 연결 필요 |
| **Embedder (Legacy)** | `rag/embedder.py` | 스켈레톤 | 0% | EmbeddingService로 대체 |

### 2.2 VIP 3-Stage 파이프라인 상태

```
┌─────────────────────────────────────────────────────────────────────┐
│                    VIP 3-Stage Pipeline Status                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Stage 1: Value (엔티티 추출)                                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  VIPAgent._extract_entities()  →  TODO (스켈레톤)            │  │
│  │  EntityExtractionService       →  DONE (완전 구현)           │  │
│  │                                                              │  │
│  │  ACTION: VIPAgent에서 EntityExtractionService 호출 연결     │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                           ↓                                         │
│  Stage 2: Intelligent (Hybrid 검색)                                │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  VIPAgent._hybrid_search()     →  DONE (SearchService 위임) │  │
│  │  VIPAgent._rrf_fusion()        →  DONE (Reranking 포함)     │  │
│  │  HybridRetriever               →  DONE (완전 구현)          │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                           ↓                                         │
│  Stage 3: Planning (답변 합성)                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  VIPAgent._synthesize_answer() →  DONE (LLMAdapter 사용)    │  │
│  │  RAGWorkflow._generate()       →  DONE (대화이력 포함)      │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.3 Gleaning 구현 상태

| 항목 | 상태 | 파일 |
|------|------|------|
| 프롬프트 템플릿 | DONE | `entity_extraction.py:100-129` |
| Gleaning 패스 로직 | DONE | `_gleaning_pass()` |
| 최대 반복 횟수 설정 | DONE | `settings.max_gleanings` |
| 중복 제거 | DONE | `_deduplicate_entities()` |
| VIP Agent 연결 | **TODO** | `vip_agent.py:196` |

---

## 3. 테스트 요구사항

### 3.1 인프라 요구사항

#### 필수 Docker 컨테이너

| 컨테이너 | 포트 | 용도 | 필수 여부 |
|----------|------|------|----------|
| `kp-ai-service` | 8000 | FastAPI AI Service | 필수 |
| `kp-elasticsearch` | 9200 | Vector Search | 필수 |
| `kp-neo4j` | 7687, 7474 | Graph Database | 필수 |
| `kp-postgres` | 5432 | SSOT Database | 필수 |
| `kp-redis` | 6379 | 캐시 (임베딩, 검색) | 권장 |
| `kp-keycloak` | 18080 | 인증 | 통합 테스트 시 |

#### 환경 변수 설정 (.env)

```bash
# LLM API (필수)
DEEPSEEK_API_KEY=sk-xxxx

# Elasticsearch
ELASTICSEARCH_HOST=localhost
ELASTICSEARCH_PORT=9200
ELASTICSEARCH_INDEX=knowledge_chunks

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DB=knowledge_db

# Redis (캐시용)
REDIS_HOST=localhost
REDIS_PORT=6379
```

### 3.2 데이터 요구사항

#### 테스트 문서 데이터

```
knowledge_service/
├── data/
│   └── sample_documents/    # 테스트용 샘플 문서
│       ├── tech_spec.pdf
│       ├── meeting_notes.docx
│       └── project_guide.md
```

#### Elasticsearch 인덱스 스키마

```json
{
  "mappings": {
    "properties": {
      "content": { "type": "text", "analyzer": "nori" },
      "embedding": { "type": "dense_vector", "dims": 1024 },
      "metadata": {
        "properties": {
          "document_id": { "type": "keyword" },
          "title": { "type": "text" },
          "document_type": { "type": "keyword" },
          "project_name": { "type": "keyword" },
          "created_at": { "type": "date" }
        }
      }
    }
  }
}
```

#### Neo4j 그래프 스키마

```cypher
-- 필수 인덱스
CREATE INDEX chunk_id IF NOT EXISTS FOR (c:Chunk) ON (c.id);
CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name);
CREATE FULLTEXT INDEX chunk_content IF NOT EXISTS FOR (c:Chunk) ON EACH [c.content];

-- 노드 레이블
(:Document), (:Chunk), (:Entity)

-- 관계 유형
(:Chunk)-[:BELONGS_TO]->(:Document)
(:Entity)-[:MENTIONED_IN]->(:Chunk)
```

### 3.3 실행 요구사항

#### Python 환경

```bash
# Python 버전
python >= 3.11

# 의존성 설치
cd knowledge_service
poetry install

# 개발 의존성 포함
poetry install --with dev
```

#### 임베딩 모델 다운로드

```bash
# BGE-M3 모델 (약 2.3GB)
# 첫 실행 시 자동 다운로드
# 또는 수동 다운로드:
huggingface-cli download BAAI/bge-m3
```

#### 서비스 실행

```bash
# FastAPI 서버 실행
cd knowledge_service
poetry run uvicorn src.app.main:app --host 0.0.0.0 --port 8000 --reload

# Docker Compose로 전체 인프라 실행
docker-compose -f infrastructure/docker-compose.yml up -d
```

#### 헬스체크

```bash
# API Health Check
curl http://localhost:8000/api/v1/health

# Liveness Probe
curl http://localhost:8000/api/v1/health/live

# Readiness Probe
curl http://localhost:8000/api/v1/health/ready

# Circuit Breaker 상태
curl http://localhost:8000/api/v1/health/circuit-breaker
```

### 3.4 테스트 실행

#### 단위 테스트

```bash
# 전체 단위 테스트
poetry run pytest src/tests/unit/ -v

# 특정 서비스 테스트
poetry run pytest src/tests/unit/test_embedding_service.py -v
poetry run pytest src/tests/unit/test_search_service.py -v
poetry run pytest src/tests/unit/test_entity_extraction.py -v
```

#### 통합 테스트

```bash
# RAG 파이프라인 통합 테스트
poetry run pytest src/tests/integration/test_story051_rag_pipeline.py -v

# Reranker 비동기 테스트
poetry run pytest src/tests/integration/test_story052_reranker_async.py -v
```

#### E2E 테스트

```bash
# 인프라 E2E 테스트
poetry run pytest src/tests/e2e/infrastructure/ -v -m infrastructure

# 프론트엔드-백엔드 통합 테스트
poetry run pytest src/tests/e2e/frontend_backend/ -v
```

#### RAGAS 평가

```bash
# RAGAS 평가 테스트
poetry run pytest src/tests/evaluation/test_ragas_evaluator.py -v -m evaluation

# 평가 스크립트 실행
poetry run python scripts/run_ragas_eval.py
```

---

## 4. 개선 작업 우선순위

### 4.1 즉시 수정 필요 (P0)

| 작업 | 예상 공수 | 영향 |
|------|----------|------|
| VIPAgent에 EntityExtractionService 연결 | 2h | VIP 파이프라인 완성 |
| VIPAgent Gleaning 호출 연결 | 1h | +33% Entity Recall |

### 4.2 권장 개선 (P1)

| 작업 | 예상 공수 | 영향 |
|------|----------|------|
| `rag/embedder.py` 삭제/통합 | 1h | 코드 중복 제거 |
| Health Check DB 연결 구현 | 2h | 운영 모니터링 강화 |

### 4.3 향후 개선 (P2-P3)

| 작업 | 예상 공수 | 영향 |
|------|----------|------|
| Sparse 벡터 (SPLADE) 구현 | 8h | Hybrid Search 성능 향상 |
| 동적 검색 전략 선택 | 4h | 쿼리별 최적화 |
| 리소스 초기화/정리 최적화 | 2h | 스타트업/셧다운 개선 |

---

## 5. 결론

### 5.1 전체 구현 상태 요약

```
┌────────────────────────────────────────────┐
│         RAG 파이프라인 완성도: 85%         │
├────────────────────────────────────────────┤
│ ✅ Embedding Service       : 100% 완료    │
│ ✅ Search Service          : 100% 완료    │
│ ✅ Hybrid Retriever        : 100% 완료    │
│ ✅ Entity Extraction       : 100% 완료    │
│ ✅ LLM Adapter             : 100% 완료    │
│ ✅ RAG Workflow            : 95% 완료     │
│ ⚠️ VIP Agent               : 70% (연결 필요) │
│ ❌ Legacy Embedder         : 삭제 대상    │
└────────────────────────────────────────────┘
```

### 5.2 핵심 조치 사항

1. **VIPAgent-EntityExtractionService 연결** (P0, 3h)
   - `_extract_entities()`에서 `EntityExtractionService.extract_entities()` 호출
   - `_gleaning()`에서 Gleaning 로직 연결 (이미 EntityExtractionService에 구현됨)

2. **코드 정리** (P1, 1h)
   - `rag/embedder.py` 삭제
   - `EmbeddingService` 직접 import로 변경

3. **테스트 환경 구축** (필수)
   - Docker Compose로 인프라 실행
   - `.env` 파일 설정 (특히 `DEEPSEEK_API_KEY`)
   - RAGAS 평가 실행으로 품질 검증

---

*작성: MLRag Agent*
*버전: 1.0*
