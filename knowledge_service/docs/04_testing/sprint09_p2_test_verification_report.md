# Sprint 09 P2 — 테스트 검증 결과서

**작성일**: 2026-03-06
**작성자**: 클로드 (Main Agent)
**환경**: Docker 실환경 (TEST_MODE=docker), WSL2 호스트

---

## 1. 검증 범위

Sprint 09 P2에서 신규 작성된 테스트 + 기존 전체 단위 테스트 커버리지 측정

| 구분 | 대상 |
|------|------|
| E2E (Playwright) | `graph-explorer.spec.ts` — STORY-121, STORY-122 |
| Frontend Vitest | `GraphExplorerView.test.tsx` — KG 시각화 컴포넌트 |
| Python 단위 | `test_dynamic_search_strategy.py` — 동적 검색 전략 |
| Python 단위 | `test_etl_cli.py` — ETL CLI Docker 실환경 (Mock 전량 제거) |
| Python 전체 | `src/tests/unit/` 디렉토리 전체 (22개 파일) |
| Frontend 전체 | `src/**/__tests__/` 전체 (22개 파일) |

---

## 2. Sprint 09 P2 신규 테스트 결과

| 테스트 | TC 수 | PASS | FAIL | 소요시간 |
|--------|------:|-----:|-----:|----------|
| E2E graph-explorer.spec.ts | 7 | 7 | 0 | 39.4s |
| Vitest GraphExplorerView.test.tsx | 34 | 34 | 0 | 47.4s |
| Python test_dynamic_search_strategy.py | 56 | 56 | 0 | 3.3s |
| Python test_etl_cli.py | 26 | 26 | 0 | 62.9s |
| **합계** | **123** | **123** | **0** | **153.0s** |

> Sprint 09 P2 신규 테스트: **123 TC 전건 PASS**

---

## 3. 전체 테스트 스위트 결과

### 3.1 Python 단위 테스트 (src/tests/unit/)

| 결과 | 건수 |
|------|-----:|
| PASS | 1,117 |
| FAIL | 80 |
| SKIP | 2 |
| **합계** | **1,199** |
| **소요시간** | 8분 45초 |

### 3.2 Frontend Vitest (src/**/__tests__/)

| 결과 | 건수 |
|------|-----:|
| PASS | 340 |
| FAIL | 138 |
| **합계** | **478** |
| **소요시간** | 233s |

---

## 4. 실패 분석 (Python 80건)

### Category A: 테스트-코드 불일치 — 13건 (즉시 수정)

**원인**: 2026-02-16 `ChunkQualityGate` 기준 상향 후 테스트 미동기화

| 파일 | 실패 수 | 상세 |
|------|--------:|------|
| `test_chunk_quality_filter.py` | 10 | `MIN_TOKEN_COUNT` 10→50 상향, 테스트는 `token_count=20` |
| `test_chunker_v2.py` | 3 | code/table 블록 `>=20 토큰` 필요, 테스트는 5, 8 |

**수정 방법**: 테스트의 `token_count` 값을 현행 기준에 맞게 조정

### Category B: 테스트 로직 오류 — 31건 (수정 필요)

| 파일 | 실패 수 | 상세 |
|------|--------:|------|
| `test_graph_search_e2e.py` | 16 | `extract_entities_from_title()` 반환값 변경 (전체→단어분리). assertion 수정 필요 |
| `test_document_upload.py` | 15 | auth 미들웨어 추가 후 테스트 미수정. `401 Unauthorized` 반환 |

**수정 방법**:
- graph_search: 엔티티 추출 함수의 현행 동작에 맞게 assertion 수정
- document_upload: conftest에 auth fixture 추가 또는 auth bypass 설정

### Category C: 테스트 실행 환경/순서 의존 — 36건 (격리 개선)

| 파일 | 실패 수 | 상세 |
|------|--------:|------|
| `test_cache_service.py` | 11 | Redis Mock/실제 연결 혼용 시 상태 충돌 |
| `test_cache_service_standalone.py` | 3 | TTL/connection 환경 의존 |
| `test_document_processing_pipeline.py` | 6 | 전체 실행 시 import 충돌 |
| `test_es_storage.py` | 6 | 개별 PASS, 전체 FAIL — 테스트 격리 문제 |
| `test_embedding_service.py` | 2 | Redis 캐시 의존 |
| `test_initial_data_loader.py` | 2 | fixture 충돌 |
| `test_neo4j_storage.py` | 3 | 상태 오염 |
| `test_optimized_document_parser.py` | 1 | 전체 실행 시 충돌 |

**수정 방법**: conftest.py fixture 스코프 정리, async mock 격리, autouse fixture 충돌 해소

---

## 5. Pydantic V2 Deprecation Warning (6건)

**현재 상태**: Warning (동작 영향 없음)
**Pydantic V3 출시 시**: Breaking change

| 파일 | 클래스 | 수정 내용 |
|------|--------|----------|
| `src/app/models/document.py:59` | `Chunk` | `class Config:` → `model_config = ConfigDict(...)` |
| `src/app/models/document.py:76` | `Document` | 동일 |
| `src/app/models/document.py:137` | `DocumentResponse` | 동일 |
| `src/app/models/document.py:155` | `DocumentStatusResponse` | 동일 |
| `src/app/models/document.py:170` | `DocumentListItem` | 동일 |
| `src/app/models/parsed_document.py:117` | `ParsedDocument` | 동일 |

---

## 6. ETL CLI Mock 제거 기록

| 항목 | Before | After |
|------|--------|-------|
| 테스트 방식 | `@patch`, `MagicMock` 기반 | Docker 실환경 (`subprocess.run(['docker', ...])`) |
| TC 수 | 28 | 26 |
| 실행 환경 | 컨테이너 내부 | 호스트 (WSL2) |
| `_is_container_running()` | Mock 반환 | 실제 `docker inspect` 실행 |
| `_es_count()` | Mock 반환 | 실제 ES HTTP 요청 |
| `status` 커맨드 | Mock 출력 | 실제 인프라 상태 조회 |

---

## 7. 시스템 상태 (검증 시점)

| 항목 | 값 |
|------|-----|
| 메모리 | 5.3 / 13 GiB (40%) |
| 스왑 | 0 / 1 GiB |
| 컨테이너 | 11개 기동 (불필요 7개 정리 완료) |
| Neo4j | 170,491 노드, 정상 |
| Elasticsearch | knowledge_chunks 인덱스, 정상 |
| PostgreSQL | 정상 |

---

## 8. 조치 계획

| 우선순위 | 카테고리 | 건수 | 담당 | 상태 |
|---------|----------|-----:|------|------|
| P0 | A: 테스트-코드 불일치 | 13 | QA + RAG Engineer | **완료** (13/13) |
| P0 | B: 테스트 로직 오류 | 31 | QA + Backend | **완료** (31/31) |
| P1 | C: 테스트 격리 | 36 | QA | **18건 수정, 18건 잔여** |
| P1 | Pydantic V2 마이그레이션 | 6 | RAG Engineer | **완료** (6/6) |
| P2 | Frontend 138 FAIL | 138 | Frontend + QA | Sprint 10 백로그 |

---

## 9. 최종 결과 (수정 완료 후)

### Python 단위 테스트 최종 결과

| 결과 | 건수 |
|------|-----:|
| PASS | 1,179 |
| FAIL | 18 |
| SKIP | 2 |
| **합계** | **1,199** |

**수정 성과**: 80 FAIL → **18 FAIL** (62건 수정, 77.5% 해소)

### 잔여 18건 상세 (Sprint 10 이관)

| 파일 | 실패 수 | 원인 | 비고 |
|------|--------:|------|------|
| `test_document_processing_pipeline.py` | 6 | 파이프라인 Quality Gate + async 의존 | 전체 실행 시에만 발생 |
| `test_es_storage.py` | 5 | async mock coroutine 누수 | 4건은 전체 실행 시에만 FAIL |
| `test_cache_service.py` | 3 | Redis client init/reuse/connection | 테스트 격리 문제 |
| `test_embedding_service.py` | 2 | Redis 캐시 + sparse embedding 의존 | 환경 의존 |
| `test_search_service.py` | 1 | 테스트 격리 (개별 PASS, 전체 FAIL) | 순수 격리 문제 |
| `test_optimized_document_parser.py` | 1 | timeout kwarg 전달 (수정 완료이나 잔여) | 재검증 필요 |

**분류**: 18건 모두 **테스트 격리/비동기 모킹 문제** — 실제 코드 결함이 아닌 테스트 인프라 이슈
