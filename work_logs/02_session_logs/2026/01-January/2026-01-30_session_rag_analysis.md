# 세션 로그: RAG 서비스 분석 결과

**일시**: 2026-01-30
**세션 유형**: RAG 서비스 코드 분석 및 Backend-RAG API 통합 검토
**참여 에이전트**: 클로드, PM, TechLead, RAG Engineer, Backend Developer, QA

---

## 1. 세션 개요

E2E 테스트 실패 분석에서 시작하여 전체 시스템의 미구현 코드를 파악하고, Backend-RAG 간 API 통합 상태를 검증하는 세션을 진행했습니다.

### 주요 성과
- Backend API 12개 완전 구현 (P0/P1/P3)
- 전체 코드베이스 미구현 분석 완료
- Backend ↔ RAG API 불일치 2건 발견

---

## 2. RAG 서비스 분석 결과

### 2.1 미구현 코드 목록 (11개 TODO)

| # | 파일 | 라인 | 내용 | 우선순위 |
|---|------|-----|------|---------|
| 1 | `main.py` | 35 | 리소스 초기화 (lifespan) | P2 |
| 2 | `main.py` | 45 | 리소스 정리 | P2 |
| 3 | `vip_agent.py` | 183 | **실제 LLM 호출로 엔티티 추출 구현** | **P0** |
| 4 | `vip_agent.py` | 196 | **Gleaning 로직 구현** | **P0** |
| 5 | `embedder.py` | 45 | 모델 로딩 | P1 (삭제 대상) |
| 6 | `embedder.py` | 64 | 임베딩 생성 | P1 (삭제 대상) |
| 7 | `embedder.py` | 90 | 배치 임베딩 | P1 (삭제 대상) |
| 8 | `embedder.py` | 119 | Sparse 벡터 생성 (SPLADE) | P2 |
| 9 | `health.py` | 104 | Elasticsearch 실제 연결 체크 | P2 |
| 10 | `health.py` | 128 | Neo4j 실제 연결 체크 | P2 |
| 11 | `rag_workflow.py` | 466 | 동적 검색 전략 선택 | P3 |

### 2.2 RAG 파이프라인 구현 상태 (85% 완성)

| 컴포넌트 | 상태 | 완성도 | 비고 |
|----------|------|--------|------|
| **EmbeddingService** | 완전 구현 | 100% | OpenAI/DeepSeek 지원 |
| **SearchService** | 완전 구현 | 100% | Hybrid, Semantic, Keyword |
| **HybridRetriever** | 완전 구현 | 100% | RRF Fusion |
| **EntityExtractionService** | 완전 구현 | 100% | **Gleaning 포함** |
| **LLMAdapter** | 완전 구현 | 100% | DeepSeek V3.2 |
| **RAGWorkflow** | 거의 완료 | 95% | LangGraph 기반 |
| **VIPAgent** | 연결 필요 | 70% | EntityExtractionService 연결 필요 |
| Legacy Embedder | 삭제 대상 | 0% | EmbeddingService로 대체됨 |

### 2.3 핵심 발견사항

```
┌─────────────────────────────────────────────────────────────┐
│  중요: EntityExtractionService는 Gleaning 포함 완전히 구현됨  │
│                                                             │
│  VIPAgent에서 이 서비스를 호출하도록 연결만 하면              │
│  VIP 3-Stage 파이프라인이 완성됩니다.                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Backend ↔ RAG API 호출 구조 분석

### 3.1 Backend → AI Service 호출 목록

| # | Backend 메서드 | AI Service URL | HTTP Method | 상태 |
|---|---------------|----------------|-------------|------|
| 1 | `hybridSearch()` | `/api/v1/search/hybrid` | POST | ✅ 일치 |
| 2 | `chatSearch()` | `/api/v1/search/chat` | POST | ✅ 일치 |
| 3 | `streamSearch()` | `/api/v1/search/chat/stream` | POST | ✅ 일치 |
| 4 | `findExperts()` | `/api/v1/graph/experts` | POST | ❌ **미구현** |

### 3.2 AI Service 제공 엔드포인트 (25개)

- Search: `/search/hybrid`, `/search/semantic`, `/search/keyword`, `/search/chat`, `/search/chat/stream`
- Health: `/health`, `/health/live`, `/health/ready`, `/health/circuit-breaker`
- Documents: `/documents/upload`, `/documents/{id}/status`, `/documents`
- Cache: `/cache/stats`, `/cache/clear`, `/cache/invalidate`, `/cache/status`
- Extract: `/extract/entities`, `/extract/metadata`, `/extract/full`
- Embed: `/embed`, `/embed/batch`
- Auth: Various

### 3.3 불일치 항목

| # | 불일치 유형 | Backend 호출 | AI Service | 조치 |
|---|-----------|-------------|-----------|------|
| **1** | 엔드포인트 미존재 | `POST /api/v1/graph/experts` | **미구현** | RAG에서 신규 구현 |
| **2** | 필드 불일치 | `useGraph`, `useVector` | 미처리 | 협의 필요 |

---

## 4. 테스트 요구사항

### 4.1 필수 인프라 (Docker 컨테이너)

| 컨테이너 | 포트 | 역할 | 필수 |
|----------|------|------|------|
| `kp-ai-service` | 8000 | FastAPI AI Service | ✅ |
| `kp-elasticsearch` | 9200 | Vector Search | ✅ |
| `kp-neo4j` | 7687 | Graph Database | ✅ |
| `kp-postgres` | 5432 | SSOT Database | ✅ |
| `kp-redis` | 6379 | Cache | 권장 |

### 4.2 필수 환경 변수

```bash
# AI Service
DEEPSEEK_API_KEY=sk-xxxx          # 필수
OPENAI_API_KEY=sk-xxxx            # 선택 (임베딩)

# Database
ELASTICSEARCH_HOST=localhost
ELASTICSEARCH_PORT=9200
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=knowledge_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
```

### 4.3 테스트 실행 명령어

```bash
# 디렉토리 이동
cd /mnt/d/Users/KTDS/Documents/06.과제/hybrid-rag-knowledge-ops/knowledge_service

# 단위 테스트
poetry run pytest src/tests/unit/ -v

# 통합 테스트
poetry run pytest src/tests/integration/ -v

# RAGAS 평가
poetry run pytest src/tests/evaluation/ -v -m evaluation

# 전체 테스트
poetry run pytest --cov=src/app --cov-report=html
```

---

## 5. 필요 조치 우선순위

### P0 - 즉시 조치 (블로커)

| # | 작업 | 담당 | 예상 공수 |
|---|------|------|----------|
| 1 | AI Service에 `/api/v1/graph/experts` 구현 | RAG | 4h |
| 2 | VIPAgent에 EntityExtractionService 연결 | RAG | 3h |

### P1 - 단기 조치 (이번 Sprint)

| # | 작업 | 담당 | 예상 공수 |
|---|------|------|----------|
| 3 | SearchRequest `useGraph`/`useVector` 처리 | RAG | 2h |
| 4 | `rag/embedder.py` 삭제 (레거시) | RAG | 1h |

### P2 - 중기 조치 (다음 Sprint)

| # | 작업 | 담당 | 예상 공수 |
|---|------|------|----------|
| 5 | Health Check 실제 DB 연결 | RAG | 2h |
| 6 | Lifespan 리소스 관리 | RAG | 2h |
| 7 | Sparse 벡터 (SPLADE) 구현 | RAG | 8h |

---

## 6. 세션 산출물

| 문서 | 경로 |
|------|------|
| QA 테스트 이슈 보고서 | `docs/04_testing/e2e/09.qa_test_issue_report_2026-01-30.md` |
| UI-API 검증 테스트 보고서 | `docs/04_testing/e2e/10.ui-api-verification-test-report_2026-01-30.md` |
| E2E 테스트 검토 회의록 | `docs/04_testing/e2e/11.e2e-test-review-meeting_2026-01-30.md` |
| Docker 환경 테스트 결과 | `docs/04_testing/e2e/12.docker-env-test-result_2026-01-30.md` |
| PM 작업 위임서 | `docs/04_testing/e2e/13.pm_work_delegation_search_api_2026-01-30.md` |
| 전체 코드 미구현 분석 | `docs/04_testing/14.full_codebase_unimplemented_analysis_2026-01-30.md` |
| 미구현 API 분석 보고서 | `docs/04_testing/10.unimplemented_api_analysis_report.md` |
| RAG 서비스 분석 보고서 | `docs/04_testing/rag_service_analysis_report.md` |

---

## 7. Git 커밋 이력

| 커밋 | 메시지 | 파일 수 |
|------|--------|--------|
| `f9a05bf` | [FEAT] Backend API 12개 완전 구현 | 15 files |
| `62ded91` | [TEST][DOCS] E2E 테스트 환경 분리 + 분석 보고서 | 9 files |

---

## 8. DeepSeek API 비용 분석

### 8.1 DeepSeek V3 가격 (2024년 기준)

| 항목 | 가격 | 비고 |
|------|------|------|
| Input (cache miss) | $0.07 / 1M tokens | |
| Input (cache hit) | $0.014 / 1M tokens | 80% 절감 |
| Output | $0.27 / 1M tokens | |

**참고**: GPT-4 대비 약 **95% 저렴**

### 8.2 프로젝트 용도별 예상 사용량

| 용도 | 호출 빈도 | 토큰/호출 | 월 예상 |
|------|----------|----------|--------|
| RAG 응답 생성 | 100회/일 | 2K tokens | ~6M tokens |
| 엔티티 추출 | 50회/일 | 1K tokens | ~1.5M tokens |
| Gleaning | 20회/일 | 3K tokens | ~1.8M tokens |
| 검색 요약 | 100회/일 | 1K tokens | ~3M tokens |
| **월 합계** | | | **~12M tokens** |

### 8.3 권장 충전 금액

| 단계 | 권장 금액 | 예상 사용 기간 | 비고 |
|------|----------|--------------|------|
| **개발/테스트** | **$10 ~ $20** | 1-2개월 | 충분한 테스트 가능 |
| **MVP 운영** | **$50** | 2-3개월 | 여유 있는 운영 |
| **프로덕션** | **$100+** | 3-6개월 | 사용량에 따라 조정 |

### 8.4 현재 권장

```
┌─────────────────────────────────────────────────────────────┐
│  현재 단계: 개발/테스트                                       │
│                                                             │
│  권장 금액: $20 USD                                          │
│                                                             │
│  이유:                                                       │
│  1. RAG 파이프라인 테스트 충분히 가능                         │
│  2. E2E 테스트 반복 실행 가능                                │
│  3. 환불 수수료 (4.4% + $0.3) 고려 시 소액 충전이 유리       │
│  4. 부족하면 추가 충전 가능                                  │
└─────────────────────────────────────────────────────────────┘
```

### 8.5 환불 정책 요약

| 항목 | 내용 |
|------|------|
| 환불 수수료 | 4.4% + $0.3 USD |
| PayPal 환불 기한 | 180일 이내 |
| 처리 기간 | 영업일 5일 |
| 최소 환불 금액 | $1 USD |

---

## 9. 다음 단계

1. **RAG Engineer**: `/api/v1/graph/experts` 엔드포인트 구현
2. **RAG Engineer**: VIPAgent에 EntityExtractionService 연결
3. **QA**: Docker 환경에서 E2E 테스트 재실행
4. **PM**: Sprint 05 품질 목표 달성 확인
5. **Infra**: DeepSeek API 키 발급 및 환경 변수 설정

---

**세션 종료 시간**: 2026-01-30
**작성자**: 클로드
