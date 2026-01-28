# Mock 테스트 전수 조사 보고서

**작성일**: 2026-01-28 | **작성자**: QA (PM 요청)
**Jira**: SCRUM-54 관련 | **Sprint**: Sprint 04 Day 3

---

## 1. 조사 목적

Frontend/Backend E2E 테스트 준비 미흡 이슈(SCRUM-54) 대응으로, 프로젝트 전체 테스트에서 Mock 사용 현황을 파악하고 Real Integration 전환이 필요한 테스트를 식별.

---

## 2. 전체 현황 요약

| 항목 | 파일 수 | 비율 |
|------|---------|------|
| **전체 테스트 파일** | **74개** | 100% |
| Pure Mock (Docker 불필요) | 46개 | 62% |
| Partial Mock (E2E Mock 모드) | 5개 | 7% |
| Real Integration (Docker 필수) | 6개 | 8% |
| 설정/유틸리티 | 17개 | 23% |

**Mock 사용률**: 92% (68/74 파일이 Docker 없이 실행 가능)

---

## 3. 언어별 Mock 현황

### 3.1 Python 테스트 (47개 파일)

#### Unit Tests (11개) - 전부 Pure Mock

| 파일 | Mock 대상 | Docker |
|------|----------|--------|
| `test_embedding_service.py` | Redis 캐시, 임베딩 모델 | 불필요 |
| `test_search_service.py` | Elasticsearch, Neo4j, 임베더 | 불필요 |
| `test_entity_extraction.py` | LLM 서비스, 임베더 | 불필요 |
| `test_neo4j_storage.py` | Neo4j 드라이버 | 불필요 |
| `test_es_storage.py` | Elasticsearch 클라이언트 | 불필요 |
| `test_document_parser.py` | Docling 라이브러리 | 조건부 (1개 skip) |
| `test_document_upload.py` | 스토리지 서비스 | 불필요 |
| `test_hybrid_retriever.py` | 검색 서비스들 | 불필요 |
| `test_semantic_chunker.py` | 청킹 모델 | 불필요 |
| `test_initial_data_loader.py` | DB 서비스들 | 불필요 |
| `test_rag_pipeline.py` | 전체 파이프라인 | 불필요 |

#### Integration Tests (4개) - Partial Mock

| 파일 | 내용 | Mock 범위 |
|------|------|----------|
| `test_story050_sse_protocol.py` | SSE 프로토콜 | 서비스 Mock, 프로토콜 실제 |
| `test_story051_rag_pipeline.py` | RAG 파이프라인 | LLM Mock, 알고리즘 실제 |
| `test_story052_reranker_async.py` | Reranker 비동기 | 모델 Mock, async 실제 |
| `test_story053_security.py` | 보안 검증 | 전체 Mock |

#### E2E Frontend/Backend Tests (5개) - Dual Mode (Mock/Docker)

| 파일 | 카테고리 | 현재 모드 | 전환 필요 |
|------|---------|----------|----------|
| `test_auth_flow.py` | A: 인증 | **Mock** | Docker 모드 추가 완료 |
| `test_search_flow.py` | B: 검색 | **Mock** | Docker 모드 추가 완료 |
| `test_sse_streaming.py` | C: SSE | **Mock** | Docker 모드 추가 완료 |
| `test_security_verification.py` | D: 보안 | **Mock** | Docker 모드 추가 완료 |
| `test_error_handling.py` | E: 에러 | **Mock** | Docker 모드 추가 완료 |

> `conftest.py`에 `E2E_MODE` 환경변수 추가하여 Mock/Docker 모드 전환 가능 (P0 아이템 #4)

#### Contract Tests (3개) - Pure Mock (Schema 검증)

| 파일 | 계약 범위 |
|------|----------|
| `test_backend_ai_contract.py` | Backend <-> AI Service |
| `test_ai_knowledge_contract.py` | AI Service <-> Knowledge Service |
| `test_sse_event_contract.py` | SSE 이벤트 포맷 |

#### Legacy/기타 테스트 (6개) - Pure Mock

| 파일 | 내용 |
|------|------|
| `test_auth.py` | 인증 라우터 |
| `test_auth_standalone.py` | 독립 인증 |
| `test_auth_unit.py` | JWT 검증만 |
| `test_health.py` | 헬스체크 |
| `test_search.py` | 검색 라우터 |
| `test_rrf_fusion.py` | RRF 알고리즘 |

#### Docker 필수 E2E (2개) - Real Integration

| 파일 | 내용 | 전제조건 |
|------|------|---------|
| `test_integration.py` | 서비스 통합 검증 | Docker Compose 전체 |
| `test_infrastructure.py` | 인프라 검증 | Docker Compose 전체 |

---

### 3.2 Java 테스트 (17개 파일)

#### Backend Tests (9개)

| 파일 | Mock 분류 | Mock 패턴 |
|------|----------|----------|
| `AuthServiceTest.java` | Pure Mock | @Mock, Mockito.when |
| `SearchServiceTest.java` | Pure Mock | @Mock, when/verify |
| `AuthControllerTest.java` | Pure Mock | @Mock, MockMvc |
| `SearchControllerTest.java` | Pure Mock | @MockBean, TestClient |
| `AIServiceClientTest.java` | Pure Mock | @Mock WebClient |
| `JwtTokenProviderTest.java` | Pure Mock | Mockito |
| `SecurityConfigTest.java` | Pure Mock | @Mock |
| `InputSanitizerTest.java` | Pure Mock | 최소 Mock |
| `BackendApplicationTests.java` | **Real Integration** | @SpringBootTest |

#### Gateway Tests (8개)

| 파일 | Mock 분류 | Mock 패턴 |
|------|----------|----------|
| `JwtAuthenticationFilterTest.java` | Pure Mock | @Mock ReactiveWebFilter |
| `SecurityConfigTest.java` | Pure Mock | @Mock WebFlux |
| `GatewayRouteConfigTest.java` | Pure Mock | @Mock RouteLocator |
| `RateLimiterConfigTest.java` | Pure Mock | @Mock RateLimiter |
| `JwtTokenValidatorTest.java` | Pure Mock | @Mock JWT |
| `FallbackControllerTest.java` | Pure Mock | @Mock |
| `GatewayApplicationTests.java` | **Real Integration** | @SpringBootTest |
| `GatewayRoutingIntegrationTest.java` | **Real Integration** | TestRestTemplate |

---

### 3.3 TypeScript 테스트 (10개 파일)

#### Unit/Component Tests (8개) - Pure Mock

| 파일 | Mock 라이브러리 |
|------|---------------|
| `SSEClient.test.ts` | vitest (vi.mock, vi.fn) |
| `useStreamingSearch.test.ts` | vitest |
| `ChatSearch.test.tsx` | vitest + React Testing Library |
| `Dashboard.test.tsx` | vitest + React Testing Library |
| `useDashboardStats.test.ts` | vitest |
| `QuickSearch.test.tsx` | vitest |
| `StatCard.test.tsx` | vitest |
| `RecentSearches.test.tsx` | vitest |

#### Playwright E2E (2개) - Real Integration

| 파일 | Docker 필요 |
|------|-----------|
| `auth.spec.ts` | 필수 (실제 브라우저) |
| `smoke-pages.spec.ts` | 필수 (실제 브라우저) |

---

## 4. Mock 대상 Top 10

| 순위 | Mock 대상 | Python | Java | TS | 합계 |
|------|----------|--------|------|-----|------|
| 1 | Repository/DAO | 5 | 14 | 1 | **20** |
| 2 | Authentication/JWT | 4 | 6 | 5 | **15** |
| 3 | Elasticsearch | 10 | 2 | 2 | **14** |
| 4 | Redis | 9 | 5 | - | **14** |
| 5 | HTTP Client | 2 | 8 | 3 | **13** |
| 6 | FastAPI/Spring Router | 7 | 4 | 2 | **13** |
| 7 | 외부 API | 6 | 3 | 4 | **13** |
| 8 | LLM Service | 12 | - | - | **12** |
| 9 | Neo4j | 8 | 2 | 1 | **11** |
| 10 | 임베딩 모델 | 8 | - | 1 | **9** |

---

## 5. Skip 상태 테스트

| 파일 | 테스트 | Skip 이유 | 해제 담당 |
|------|--------|----------|----------|
| `test_document_parser.py:421` | `TestDoclingAdapter::test_parse_pdf_with_tables` | Docling 미설치 | ETL (STORY-063) |

> Skip 테스트는 1건만 존재. STORY-063에서 Docling Docker 이미지 완성 후 ETL 엔지니어가 해제 예정.

---

## 6. Real Integration 전환 필요 목록

### 즉시 전환 가능 (인프라 준비 완료 시)

| 파일 | 현재 | 전환 방법 |
|------|------|----------|
| `test_auth_flow.py` | Mock | `E2E_MODE=docker` 설정 |
| `test_search_flow.py` | Mock | `E2E_MODE=docker` 설정 |
| `test_sse_streaming.py` | Mock | `E2E_MODE=docker` 설정 |
| `test_security_verification.py` | Mock | `E2E_MODE=docker` 설정 |
| `test_error_handling.py` | Mock | `E2E_MODE=docker` 설정 |

### Docker 전제조건

```
Tier 0: PostgreSQL, Elasticsearch, Neo4j, Redis, MinIO
Tier 1: Keycloak
Tier 2: Backend, AI Service
Tier 3: API Gateway, Nginx
Tier 4: Frontend
```

### 추가 필요사항

- [ ] 테스트 데이터 시딩 스크립트
- [ ] Keycloak realm/client 설정 확인
- [ ] DB 스키마 초기화 확인
- [ ] 서비스 헬스체크 wait 로직 (docker_helpers.py 활용)

---

## 7. 테스트 실행 전략

### Phase 1: Mock E2E (현재, Docker 불필요)
```bash
pytest knowledge_service/src/tests/unit -v
E2E_MODE=mock pytest knowledge_service/src/tests/e2e/frontend_backend -v
```

### Phase 2: Docker E2E (인프라 준비 후)
```bash
docker compose up -d
# 전체 서비스 healthy 확인 후
E2E_MODE=docker pytest knowledge_service/src/tests/e2e/frontend_backend -v
```

### Phase 3: 풀스택 E2E (Sprint 05 예정)
```bash
# Playwright 브라우저 테스트
npx playwright test
```

---

## 8. 결론

- **전체 74개 테스트 파일 중 92%가 Mock 기반** - Docker 없이 실행 가능
- **Real Integration 테스트는 6개 파일** (Python 2, Java 3, TS 2) - Docker Compose 필수
- **E2E Frontend/Backend 5개 파일**은 `E2E_MODE` 환경변수로 Mock/Docker 전환 가능
- **Skip 테스트 1건**: Docling 관련 (STORY-063 ETL 담당)
- Mock 테스트는 로직 검증에 유효하나, **실제 서비스 간 통신 검증에는 Docker 모드 필수**

---

## 참고

- 회의록: `work_logs/meetings/2026/01-January/2026-01-28_e2e_test_readiness_meeting.md`
- Jira: SCRUM-54
- Sprint: sprint-04.md
- conftest.py: `knowledge_service/src/tests/e2e/frontend_backend/conftest.py`
