# AI Service 구현 계획서
## Python FastAPI + LangGraph 기반 Hybrid RAG Service

---

## 문서 정보

| 항목 | 내용 |
|------|------|
| **문서명** | AI Service 구현 계획서 |
| **버전** | 2.0 |
| **작성일** | 2026-01-14 |
| **작성자** | Claude Code (Opus 4.5) |
| **상태** | 초안 |
| **참조 문서** | [상세 설계서](../02_design/01_hybrid_rag_platform_detailed_design.md), [백엔드 구현 계획서](./backend_implementation_plan.md) |

---

## 변경 이력

| 버전 | 일자 | 작성자 | 변경 내용 |
|------|------|--------|----------|
| 1.0 | 2026-01-14 | Claude Code | 초안 작성 (상세 코드 포함) |
| 2.0 | 2026-01-14 | Claude Code | **구현 계획 형식으로 재작성**: 코드 제거, Phase/Task/의존성 중심 |

---

## 목차

1. [개요](#1-개요)
2. [구현 범위](#2-구현-범위)
3. [기술 스택](#3-기술-스택)
4. [구현 단계 (Phases)](#4-구현-단계-phases)
5. [태스크 브레이크다운](#5-태스크-브레이크다운)
6. [디렉토리 구조](#6-디렉토리-구조)
7. [API 명세 요약](#7-api-명세-요약)
8. [구현 가이드라인](#8-구현-가이드라인)
9. [리스크 및 대응 방안](#9-리스크-및-대응-방안)
10. [품질 기준](#10-품질-기준)
11. [참고 자료](#11-참고-자료)

---

## 1. 개요

### 1.1 목적

AI Service 구현 계획서는 Python 기반 AI 처리 서비스의 **구현 순서, 태스크 분해, 의존성 관계**를 정의합니다.

### 1.2 문서 범위

| 포함 | 미포함 |
|------|--------|
| 구현 단계 및 마일스톤 | 상세 코드 구현 (설계서 참조) |
| 태스크별 의존성 및 우선순위 | 비즈니스 로직 상세 (백엔드 계획서 참조) |
| 완료 기준 (Definition of Done) | 인프라 구성 (DevOps 계획서 참조) |
| 리스크 및 대응 방안 | |

### 1.3 시스템 위치

```
┌─────────────────────────────────────────────────────────────────────┐
│                        시스템 아키텍처                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   React UI ──► SpringBoot Backend ──► AI Service (이 문서의 범위)    │
│                                          │                           │
│                                          ▼                           │
│                              ┌───────────────────────┐               │
│                              │  DeepSeek API         │               │
│                              │  Elasticsearch        │               │
│                              │  Neo4j                │               │
│                              └───────────────────────┘               │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. 구현 범위

### 2.1 In Scope (구현 대상)

| 기능 | 설명 | 우선순위 |
|------|------|----------|
| **Hybrid 검색** | Vector(ES) + Graph(Neo4j) 결합 검색 | P0 (필수) |
| **VIP 파이프라인** | Value-Intelligent-Planning 3단계 LLM 처리 | P0 (필수) |
| **엔티티 추출** | 문서에서 Person, Project, Technology 등 추출 | P0 (필수) |
| **메타데이터 생성** | 문서 유형, 카테고리, 유효기간 자동 분류 | P0 (필수) |
| **임베딩 생성** | BGE-M3 Dense/Sparse 벡터 생성 | P0 (필수) |
| **문서 파싱** | PDF/DOCX 텍스트 추출 (Docling) | P1 (중요) |
| **ReAct Agent** | 복잡한 질의 자동 분해 | P1 (중요) |
| **스트리밍 응답** | SSE 기반 실시간 답변 | P2 (권장) |

### 2.2 Out of Scope (구현 제외)

| 기능 | 사유 | 담당 |
|------|------|------|
| 사용자 인증/인가 | SpringBoot 담당 | Backend |
| 문서 CRUD | SpringBoot 담당 | Backend |
| 파일 저장소 관리 | SpringBoot 담당 | Backend |
| 인프라 프로비저닝 | DevOps 담당 | DevOps |

---

## 3. 기술 스택

### 3.1 핵심 기술

| 구분 | 기술 | 버전 | 선정 사유 |
|------|------|------|----------|
| **Runtime** | Python | 3.11+ | AI/ML 라이브러리 생태계 |
| **Framework** | FastAPI | 0.110+ | 비동기 처리, OpenAPI 자동 생성 |
| **AI Framework** | LangChain | 0.3+ | LLM 통합, 프롬프트 관리 |
| **Agent** | LangGraph | 0.2+ | ReAct Agent, 워크플로우 |
| **LLM** | DeepSeek | V3.2 | 95% 비용 절감 |
| **Embedding** | BGE-M3 | - | Dense + Sparse 지원 |
| **Document** | Docling | 2.x | PDF/DOCX 파싱 |

### 3.2 데이터베이스 클라이언트

| DB | 클라이언트 | 용도 |
|----|-----------|------|
| Elasticsearch | elasticsearch-py (async) | 벡터 검색 |
| Neo4j | neo4j-python-driver | 그래프 탐색 |
| PostgreSQL | asyncpg | 읽기 전용 조회 |
| Redis | redis-py | 캐싱 |

---

## 4. 구현 단계 (Phases)

### 4.1 Phase 개요

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           구현 단계 (Phases)                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Phase 1: 기반 구축          Phase 2: 핵심 기능         Phase 3: 통합/최적화   │
│  ─────────────────          ─────────────────         ─────────────────     │
│  • 프로젝트 초기화           • VIP 파이프라인          • ReAct Agent          │
│  • 설정/환경 구성           • Hybrid 검색 엔진        • 스트리밍 응답         │
│  • DB 연결                  • 엔티티 추출             • 성능 최적화           │
│  • 기본 API 구조            • 임베딩 서비스           • 모니터링              │
│  • 헬스체크                 • 문서 파싱               • 부하 테스트           │
│                                                                              │
│  [──────────────]──────────[────────────────]──────────[────────────────]    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Phase 1: 기반 구축

**목표**: 개발 환경 구성 및 기본 인프라 연결

| Task ID | 태스크 | 산출물 | 완료 기준 |
|---------|--------|--------|----------|
| P1-01 | 프로젝트 초기화 | pyproject.toml, 디렉토리 구조 | poetry install 성공 |
| P1-02 | 설정 관리 구현 | app/config.py | 환경변수 로드 성공 |
| P1-03 | FastAPI 앱 구조 | app/main.py, 라우터 구조 | uvicorn 실행 성공 |
| P1-04 | 헬스체크 API | /health, /health/ready | 200 OK 응답 |
| P1-05 | ES 연결 | ElasticsearchRepo | 연결 테스트 통과 |
| P1-06 | Neo4j 연결 | Neo4jRepo | 연결 테스트 통과 |
| P1-07 | PostgreSQL 연결 | PostgresRepo | 연결 테스트 통과 |
| P1-08 | 로깅 설정 | structlog 설정 | 로그 출력 확인 |

**의존성 그래프**:
```
P1-01 ──► P1-02 ──► P1-03 ──► P1-04
              │
              └──► P1-05 ──┐
              └──► P1-06 ──┼──► P1-08
              └──► P1-07 ──┘
```

### 4.3 Phase 2: 핵심 기능

**목표**: 검색, 추출, 임베딩 핵심 기능 구현

| Task ID | 태스크 | 산출물 | 완료 기준 |
|---------|--------|--------|----------|
| P2-01 | LLM 클라이언트 | app/core/llm_client.py | DeepSeek API 호출 성공 |
| P2-02 | 임베딩 모델 로드 | app/core/embedding.py | BGE-M3 로드 성공 |
| P2-03 | VIP Stage 1 구현 | vip_pipeline.value_stage() | 엔티티 추출 테스트 통과 |
| P2-04 | VIP Stage 2 구현 | vip_pipeline.intelligent_stage() | 의도 분석 테스트 통과 |
| P2-05 | VIP Stage 3 구현 | vip_pipeline.planning_stage() | 답변 합성 테스트 통과 |
| P2-06 | Vector Search 구현 | vector_search.py | ES knn 검색 성공 |
| P2-07 | Graph Search 구현 | graph_search.py | Neo4j Cypher 실행 성공 |
| P2-08 | RRF 융합 구현 | rrf_fusion.py | 결과 병합 테스트 통과 |
| P2-09 | Hybrid 검색 통합 | hybrid_engine.py | 통합 검색 테스트 통과 |
| P2-10 | 검색 API 구현 | /api/v1/search/* | API 테스트 통과 |
| P2-11 | 추출 서비스 구현 | extract_service.py | 엔티티 추출 API 동작 |
| P2-12 | 추출 API 구현 | /api/v1/extract/* | API 테스트 통과 |
| P2-13 | 임베딩 서비스 구현 | embed_service.py | 임베딩 생성 성공 |
| P2-14 | 임베딩 API 구현 | /api/v1/embed | API 테스트 통과 |
| P2-15 | 문서 파서 구현 | document_parser.py | PDF 파싱 성공 |

**의존성 그래프**:
```
                    P2-01 ──► P2-03 ──► P2-04 ──► P2-05
                      │
P1-05 ──► P2-06 ──────┼──► P2-08 ──► P2-09 ──► P2-10
P1-06 ──► P2-07 ──────┘
                      │
                      └──► P2-11 ──► P2-12

P2-02 ──► P2-13 ──► P2-14

P2-15 (독립)
```

### 4.4 Phase 3: 통합 및 최적화

**목표**: 고급 기능 및 성능 최적화

| Task ID | 태스크 | 산출물 | 완료 기준 |
|---------|--------|--------|----------|
| P3-01 | ReAct Agent 구현 | react_agent.py | 복잡 질의 처리 성공 |
| P3-02 | Tool 정의 | tools.py | Agent 도구 호출 성공 |
| P3-03 | 스트리밍 응답 구현 | SSE endpoint | 실시간 응답 확인 |
| P3-04 | 배치 임베딩 최적화 | batch_embed() | 100 docs/sec 달성 |
| P3-05 | 캐싱 레이어 추가 | Redis 캐싱 | 캐시 히트율 80%+ |
| P3-06 | 에러 핸들링 강화 | 글로벌 예외 처리 | 에러 응답 표준화 |
| P3-07 | 비용 추적 구현 | cost_tracker.py | API 비용 로깅 |
| P3-08 | 단위 테스트 작성 | tests/unit/* | 커버리지 80%+ |
| P3-09 | 통합 테스트 작성 | tests/integration/* | 주요 시나리오 통과 |
| P3-10 | 부하 테스트 | locustfile.py | 100 동시 요청 처리 |
| P3-11 | Docker 이미지 빌드 | Dockerfile | 이미지 빌드 성공 |
| P3-12 | docker-compose 구성 | docker-compose.yml | 전체 스택 실행 |

**의존성 그래프**:
```
P2-10 ──► P3-01 ──► P3-02
P2-10 ──► P3-03
P2-14 ──► P3-04
P2-09 ──► P3-05
          P3-06 (독립)
P2-01 ──► P3-07
P2-* ──► P3-08, P3-09
P3-08 ──► P3-10
P1-* ──► P3-11 ──► P3-12
```

---

## 5. 태스크 브레이크다운

### 5.1 Phase 1 상세

#### P1-01: 프로젝트 초기화

| 항목 | 내용 |
|------|------|
| **설명** | Poetry 프로젝트 생성 및 의존성 정의 |
| **의존성** | 없음 |
| **산출물** | pyproject.toml, poetry.lock |
| **완료 기준** | `poetry install` 성공, 가상환경 활성화 |
| **예상 작업** | 1. poetry init, 2. 의존성 추가, 3. 디렉토리 생성 |

#### P1-02: 설정 관리 구현

| 항목 | 내용 |
|------|------|
| **설명** | Pydantic Settings 기반 환경 설정 클래스 |
| **의존성** | P1-01 |
| **산출물** | app/config.py |
| **완료 기준** | .env 파일에서 설정 로드 성공 |
| **구현 항목** | DEEPSEEK_API_KEY, ES_URL, NEO4J_URI, POSTGRES_URL, REDIS_URL |

#### P1-03: FastAPI 앱 구조

| 항목 | 내용 |
|------|------|
| **설명** | FastAPI 애플리케이션 및 라우터 구조 |
| **의존성** | P1-02 |
| **산출물** | app/main.py, app/api/routes/__init__.py |
| **완료 기준** | `uvicorn app.main:app` 실행 성공 |
| **구현 항목** | lifespan 이벤트, CORS 설정, 라우터 등록 |

#### P1-04: 헬스체크 API

| 항목 | 내용 |
|------|------|
| **설명** | 서비스 상태 확인 엔드포인트 |
| **의존성** | P1-03 |
| **산출물** | app/api/routes/health.py |
| **완료 기준** | GET /health → 200 OK |
| **구현 항목** | /health (liveness), /health/ready (readiness) |

#### P1-05 ~ P1-07: DB 연결

| 항목 | P1-05 (ES) | P1-06 (Neo4j) | P1-07 (PostgreSQL) |
|------|------------|---------------|-------------------|
| **설명** | ES 비동기 클라이언트 | Neo4j 드라이버 | asyncpg 풀 |
| **의존성** | P1-02 | P1-02 | P1-02 |
| **산출물** | elasticsearch_repo.py | neo4j_repo.py | postgres_repo.py |
| **완료 기준** | 연결 테스트 통과 | 연결 테스트 통과 | 연결 테스트 통과 |

### 5.2 Phase 2 상세

#### P2-01: LLM 클라이언트

| 항목 | 내용 |
|------|------|
| **설명** | DeepSeek API 호출 클라이언트 |
| **의존성** | P1-02 |
| **산출물** | app/core/llm_client.py |
| **완료 기준** | chat(), reason(), stream() 메서드 동작 |
| **구현 항목** | - httpx 비동기 클라이언트<br>- tenacity 재시도 로직<br>- 스트리밍 지원 |

#### P2-02: 임베딩 모델

| 항목 | 내용 |
|------|------|
| **설명** | BGE-M3 임베딩 모델 로드 및 추론 |
| **의존성** | P1-01 |
| **산출물** | app/core/embedding.py |
| **완료 기준** | embed(), batch_embed() 메서드 동작 |
| **구현 항목** | - SentenceTransformer 로드<br>- Dense/Sparse 벡터 생성<br>- GPU/CPU 자동 선택 |

#### P2-03 ~ P2-05: VIP 파이프라인

| 항목 | P2-03 (Stage 1) | P2-04 (Stage 2) | P2-05 (Stage 3) |
|------|-----------------|-----------------|-----------------|
| **설명** | 엔티티 추출 | 의도 분석/검색 | 답변 합성 |
| **의존성** | P2-01 | P2-03 | P2-04 |
| **산출물** | value_stage() | intelligent_stage() | planning_stage() |
| **완료 기준** | JSON 엔티티 반환 | 검색 결과 반환 | 자연어 답변 생성 |

#### P2-06 ~ P2-09: Hybrid 검색

| 항목 | P2-06 | P2-07 | P2-08 | P2-09 |
|------|-------|-------|-------|-------|
| **설명** | ES 벡터 검색 | Neo4j 그래프 검색 | RRF 융합 | 통합 엔진 |
| **의존성** | P1-05 | P1-06 | P2-06, P2-07 | P2-08 |
| **산출물** | vector_search.py | graph_search.py | rrf_fusion.py | hybrid_engine.py |

### 5.3 Phase 3 상세

#### P3-01 ~ P3-02: ReAct Agent

| 항목 | 내용 |
|------|------|
| **설명** | LangGraph 기반 ReAct Agent 구현 |
| **의존성** | P2-10 |
| **산출물** | react_agent.py, tools.py |
| **완료 기준** | 복잡한 질의 자동 분해 및 처리 |
| **구현 항목** | - StateGraph 워크플로우<br>- vector_search_tool<br>- graph_traversal_tool<br>- temporal_filter_tool |

#### P3-08 ~ P3-09: 테스트

| 항목 | P3-08 (단위) | P3-09 (통합) |
|------|-------------|-------------|
| **설명** | 개별 모듈 테스트 | 전체 흐름 테스트 |
| **의존성** | Phase 2 전체 | P3-08 |
| **산출물** | tests/unit/* | tests/integration/* |
| **완료 기준** | 커버리지 80%+ | 주요 시나리오 100% 통과 |
| **테스트 항목** | LLM Client, Embedding, VIP Pipeline | 검색 API, 추출 API, E2E |

---

## 6. 디렉토리 구조

```
ai-service/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI 진입점
│   ├── config.py                   # 설정 관리
│   │
│   ├── api/                        # API Layer
│   │   ├── __init__.py
│   │   ├── dependencies.py         # 의존성 주입
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── search.py           # /api/v1/search/*
│   │       ├── extract.py          # /api/v1/extract/*
│   │       ├── embed.py            # /api/v1/embed
│   │       └── health.py           # /health
│   │
│   ├── services/                   # Service Layer
│   │   ├── __init__.py
│   │   ├── search_service.py
│   │   ├── extract_service.py
│   │   └── embed_service.py
│   │
│   ├── core/                       # Core Layer
│   │   ├── __init__.py
│   │   ├── llm_client.py           # DeepSeek 클라이언트
│   │   ├── embedding.py            # BGE-M3 모델
│   │   ├── document_parser.py      # Docling 파서
│   │   └── vip_pipeline.py         # VIP 파이프라인
│   │
│   ├── search/                     # Hybrid Search
│   │   ├── __init__.py
│   │   ├── hybrid_engine.py
│   │   ├── vector_search.py
│   │   ├── graph_search.py
│   │   └── rrf_fusion.py
│   │
│   ├── agents/                     # LangGraph Agents
│   │   ├── __init__.py
│   │   ├── react_agent.py
│   │   ├── tools.py
│   │   └── prompts.py
│   │
│   ├── repositories/               # Repository Layer
│   │   ├── __init__.py
│   │   ├── elasticsearch_repo.py
│   │   ├── neo4j_repo.py
│   │   └── postgres_repo.py
│   │
│   ├── models/                     # Pydantic Models
│   │   ├── __init__.py
│   │   ├── search.py
│   │   ├── extract.py
│   │   └── common.py
│   │
│   └── utils/                      # Utilities
│       ├── __init__.py
│       ├── logging.py
│       ├── cost_tracker.py
│       └── retry.py
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_llm_client.py
│   │   ├── test_embedding.py
│   │   └── test_vip_pipeline.py
│   ├── integration/
│   │   ├── test_search_service.py
│   │   └── test_extract_service.py
│   └── e2e/
│       └── test_api_endpoints.py
│
├── prompts/                        # 프롬프트 템플릿
│   ├── entity_extraction.txt
│   ├── intent_analysis.txt
│   └── answer_synthesis.txt
│
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── poetry.lock
└── README.md
```

---

## 7. API 명세 요약

> 상세 API 스펙은 [상세 설계서 섹션 5](../02_design/01_hybrid_rag_platform_detailed_design.md#5-api-설계)를 참조하세요.

### 7.1 엔드포인트 목록

| 엔드포인트 | 메서드 | 설명 | Phase |
|------------|--------|------|-------|
| `/health` | GET | Liveness 체크 | P1 |
| `/health/ready` | GET | Readiness 체크 | P1 |
| `/api/v1/search/hybrid` | POST | Hybrid 검색 | P2 |
| `/api/v1/search/chat` | POST | 대화형 검색 | P2 |
| `/api/v1/search/chat/stream` | POST | SSE 스트리밍 | P3 |
| `/api/v1/extract/entities` | POST | 엔티티 추출 | P2 |
| `/api/v1/extract/metadata` | POST | 메타데이터 생성 | P2 |
| `/api/v1/embed` | POST | 텍스트 임베딩 | P2 |
| `/api/v1/embed/batch` | POST | 배치 임베딩 | P2 |

### 7.2 요청/응답 모델 요약

**검색 요청**
```
HybridSearchRequest:
  - query: string (필수)
  - filters: object (선택)
  - search_type: "vector" | "graph" | "hybrid"
  - top_k: integer (기본 10)
```

**검색 응답**
```
HybridSearchResponse:
  - results: SearchResultItem[]
  - total: integer
  - took_ms: float
```

---

## 8. 구현 가이드라인

### 8.1 코딩 표준

| 항목 | 표준 |
|------|------|
| **Python 버전** | 3.11+ (Type Hints 활용) |
| **코드 스타일** | Black (88 columns), isort |
| **Type Checking** | mypy strict mode |
| **Docstring** | Google style |
| **네이밍** | snake_case (함수/변수), PascalCase (클래스) |

### 8.2 에러 처리 원칙

| 레벨 | 처리 방식 |
|------|----------|
| **API Layer** | HTTPException 반환 (400, 404, 500) |
| **Service Layer** | Custom Exception 발생 |
| **Repository Layer** | 원본 예외 래핑 후 전파 |
| **External API** | tenacity 재시도 후 실패 시 예외 |

### 8.3 로깅 원칙

| 레벨 | 용도 |
|------|------|
| **DEBUG** | 개발 중 상세 디버깅 |
| **INFO** | 요청/응답 로깅, 처리 단계 |
| **WARNING** | 비정상 상황 (재시도, fallback) |
| **ERROR** | 예외 발생, 처리 실패 |

### 8.4 테스트 원칙

| 테스트 유형 | 범위 | Mock 대상 |
|------------|------|----------|
| **Unit** | 개별 함수/클래스 | 모든 외부 의존성 |
| **Integration** | 서비스 레이어 | 외부 API만 |
| **E2E** | 전체 API | 없음 (실제 환경) |

---

## 9. 리스크 및 대응 방안

### 9.1 기술 리스크

| 리스크 | 영향도 | 발생 가능성 | 대응 방안 |
|--------|--------|------------|----------|
| **DeepSeek API 불안정** | 높음 | 중간 | Fallback 모델 준비 (Claude API), Circuit Breaker |
| **BGE-M3 메모리 부족** | 높음 | 중간 | 배치 크기 조절, 모델 경량화 검토 |
| **ES knn 성능 저하** | 중간 | 낮음 | num_candidates 조정, 인덱스 최적화 |
| **Neo4j 쿼리 타임아웃** | 중간 | 낮음 | 쿼리 최적화, depth 제한 |

### 9.2 일정 리스크

| 리스크 | 영향도 | 대응 방안 |
|--------|--------|----------|
| **Phase 1 지연** | 높음 | 기존 템플릿 활용, 최소 기능 우선 |
| **LangGraph 학습 곡선** | 중간 | 공식 문서 기반 구현, 단순 Agent부터 시작 |
| **테스트 커버리지 미달** | 중간 | 핵심 경로 우선 테스트, P2 완료 후 보완 |

### 9.3 대응 전략

```
┌─────────────────────────────────────────────────────────────────┐
│                       리스크 대응 전략                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [예방]                    [완화]                   [대응]        │
│  ─────                    ─────                   ─────        │
│  • 단계별 검증            • 점진적 구현           • Fallback 준비 │
│  • 의존성 최소화          • 모듈화                • 롤백 계획     │
│  • 설정 외부화            • 느슨한 결합           • 수동 처리     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 10. 품질 기준

### 10.1 성능 목표

| 지표 | 목표 | 측정 방법 |
|------|------|----------|
| **검색 응답 시간** | ≤ 1초 (P95) | Locust 부하 테스트 |
| **채팅 첫 토큰** | ≤ 2초 (P95) | 스트리밍 시작 시간 |
| **임베딩 처리량** | ≥ 100 docs/sec | 배치 처리 벤치마크 |
| **동시 요청** | ≥ 100 | Locust 동시 사용자 |
| **API 가용성** | ≥ 99.5% | 헬스체크 모니터링 |

### 10.2 코드 품질 목표

| 지표 | 목표 |
|------|------|
| **테스트 커버리지** | ≥ 80% |
| **Type Coverage** | ≥ 90% |
| **Lint 경고** | 0개 |
| **보안 취약점** | 0개 (Critical/High) |

### 10.3 완료 기준 (Definition of Done)

| 항목 | 기준 |
|------|------|
| **코드** | Black/isort 통과, mypy 통과 |
| **테스트** | 단위 테스트 작성, CI 통과 |
| **문서** | Docstring 작성, API 문서 자동 생성 |
| **리뷰** | PR 리뷰 승인 |

---

## 11. 참고 자료

### 11.1 프로젝트 문서

| 문서 | 위치 | 내용 |
|------|------|------|
| **상세 설계서** | [hybrid_rag_platform_detailed_design.md](../02_design/01_hybrid_rag_platform_detailed_design.md) | 아키텍처, 데이터 모델, 코드 예시 |
| **백엔드 구현 계획서** | [backend_implementation_plan.md](./backend_implementation_plan.md) | SpringBoot 구현 계획 |
| **테스트 계획서** | [test_plan.md](./test_plan.md) | 테스트 전략 및 시나리오 |
| **DevOps 계획서** | [devops_alm_plan.md](./devops_alm_plan.md) | CI/CD, 인프라 구성 |

### 11.2 외부 문서

| 문서 | URL |
|------|-----|
| **FastAPI** | https://fastapi.tiangolo.com/ |
| **LangGraph** | https://python.langchain.com/docs/langgraph/ |
| **DeepSeek API** | https://platform.deepseek.com/api-docs |
| **BGE-M3** | https://huggingface.co/BAAI/bge-m3 |
| **Docling** | https://github.com/DS4SD/docling |
| **Elasticsearch Python** | https://www.elastic.co/guide/en/elasticsearch/client/python-api/current/ |
| **Neo4j Python** | https://neo4j.com/docs/api/python-driver/current/ |

---

## 부록

### A. 환경변수 목록

| 변수명 | 필수 | 설명 | 예시 |
|--------|------|------|------|
| `DEEPSEEK_API_KEY` | ✅ | DeepSeek API 키 | `sk-xxx` |
| `DEEPSEEK_BASE_URL` | ❌ | API 베이스 URL | `https://api.deepseek.com/v1` |
| `ELASTICSEARCH_URL` | ✅ | ES 연결 URL | `http://localhost:9200` |
| `NEO4J_URI` | ✅ | Neo4j 연결 URI | `bolt://localhost:7687` |
| `NEO4J_USER` | ✅ | Neo4j 사용자 | `neo4j` |
| `NEO4J_PASSWORD` | ✅ | Neo4j 비밀번호 | `password` |
| `POSTGRES_URL` | ✅ | PostgreSQL URL | `postgresql://localhost:5432/knowledge` |
| `REDIS_URL` | ❌ | Redis URL | `redis://localhost:6379` |
| `EMBEDDING_MODEL` | ❌ | 임베딩 모델명 | `BAAI/bge-m3` |

### B. 비용 추정

| 작업 | 모델 | 월 예상 토큰 | 비용/1M | 월 예상 비용 |
|------|------|-------------|---------|-------------|
| 엔티티 추출 | DeepSeek-Chat | 입력 10M | $0.28 | $2.80 |
| 의도 분석 | DeepSeek-Chat | 입력 5M | $0.28 | $1.40 |
| 답변 합성 | DeepSeek-Chat | 출력 2M | $1.10 | $2.20 |
| **총계** | | | | **~$6.40** |

### C. 체크리스트

**Phase 1 완료 체크리스트**
- [ ] pyproject.toml 작성 완료
- [ ] config.py 환경변수 로드 확인
- [ ] FastAPI 앱 실행 확인
- [ ] /health 응답 확인
- [ ] ES, Neo4j, PostgreSQL 연결 테스트 통과

**Phase 2 완료 체크리스트**
- [ ] DeepSeek API 호출 성공
- [ ] BGE-M3 임베딩 생성 성공
- [ ] VIP 파이프라인 전체 동작
- [ ] Hybrid 검색 결과 반환
- [ ] 검색/추출/임베딩 API 테스트 통과

**Phase 3 완료 체크리스트**
- [ ] ReAct Agent 복잡 질의 처리
- [ ] SSE 스트리밍 응답 확인
- [ ] 테스트 커버리지 80%+
- [ ] 부하 테스트 100 동시 요청 통과
- [ ] Docker 이미지 빌드 및 실행 성공

---

**문서 작성 완료: 2026-01-14**
