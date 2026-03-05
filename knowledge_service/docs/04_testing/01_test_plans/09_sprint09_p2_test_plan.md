# Sprint 09 P2 테스트 계획서

**문서 ID**: TP-09-P2
**버전**: 1.0
**작성일**: 2026-03-05
**작성자**: QA Agent
**스프린트**: Sprint 09 Phase 2

---

## 1. 테스트 범위

Sprint 09 P2에서 완료된 7개 Story에 대한 검증 계획입니다.

| Story | 제목 | 테스트 유형 | TC 수 |
|-------|------|------------|-------|
| STORY-121 | KG Visualization (GraphExplorerView) | Vitest 단위 + E2E | 12 + 5 |
| STORY-122 | 동적 검색 전략 | pytest 단위 + E2E | 14 + 2 |
| STORY-123 | Alertmanager 라우팅 설정 | 설정 검증 | 6 |
| STORY-124 | Neo4j 스키마 정의 | 스키마 검증 | 5 |
| STORY-125 | ETL CLI 인터페이스 | pytest 단위 | 8 |
| STORY-126 | Grafana SLA 대시보드 | JSON 검증 | 4 |
| STORY-127 | API Gateway JWT 검증 | JUnit 단위 | 10 |

**총 테스트 케이스**: 66 TC

---

## 2. 테스트 전략

### 2.1 설정 검증 (Phase 1)

인프라/설정 파일에 대한 정적 검증입니다.

#### STORY-123: Alertmanager 설정 검증

**대상 파일**: `infrastructure/docker/alertmanager/alertmanager.yml`

| TC ID | 검증 항목 | 합격 기준 |
|-------|----------|----------|
| C01 | YAML 문법 유효성 | 파싱 오류 없음 |
| C02 | 8개 receiver 라우팅 | critical→alerts, db→alerts, ai→alerts, security→alerts, infra→alerts, sla→alerts, warning→dev, info→dev |
| C03 | severity 매칭 규칙 | critical/warning/info 각각 별도 route 존재 |
| C04 | 억제 규칙 (inhibit_rules) | critical이 warning/info 억제 |
| C05 | infrastructure 카테고리 라우팅 | category: infra → infra-slack receiver |
| C06 | SLA 카테고리 라우팅 | category: sla → sla-slack receiver |

**검증 결과 요약**:
- C01: PASS — YAML 구조 유효 (global, templates, route, receivers, inhibit_rules 섹션 존재)
- C02: PASS — 9개 receiver 정의 (default-slack, critical-slack, database-slack, ai-service-slack, security-slack, infra-slack, sla-slack, warning-slack, info-slack)
- C03: PASS — critical/warning/info 각각 독립 route 정의
- C04: PASS — inhibit_rules 5개 정의 (critical→warning, critical→info, warning→info, ContainerDown→HighUsage, .*Down$→.*High.*|.*Slow.*)
- C05: PASS — `category: infra` → `infra-slack` (channel: #proj-hrkp-alerts)
- C06: PASS — `category: sla` → `sla-slack` (channel: #proj-hrkp-alerts, repeat_interval: 2h)

**최종 결과**: 6/6 PASS

---

#### STORY-126: Grafana 대시보드 JSON 검증

**대상 파일**: `infrastructure/docker/grafana/dashboards/*.json`

| TC ID | 검증 항목 | 합격 기준 |
|-------|----------|----------|
| C01 | 모든 JSON 파일 유효성 | 5개 파일 파싱 오류 없음 |
| C02 | rag-sla-dashboard.json 구조 | 5개 row / 17개 패널 이상 |
| C03 | Datasource UID 일관성 | 모든 패널이 uid: "prometheus" 사용 |
| C04 | Grafana 임포트 호환성 | schemaVersion, templating 필드 존재 |

**대상 파일 목록**:
- `system-overview.json`
- `application-metrics.json`
- `database-metrics.json`
- `rag-sla-dashboard.json`
- `etl-pipeline.json`

**rag-sla-dashboard.json 패널 구조**:

| Row ID | Row 제목 | 패널 수 |
|--------|----------|---------|
| 100 | SLA Overview | 4개 (id: 1,2,3,4) |
| 101 | SLA Trends | 2개 (id: 10,11) |
| 102 | RAG Pipeline Metrics | 3개 (id: 20,21,22) |
| 103 | LLM Metrics | 6개 (id: 30,31,32,33,34,35) |
| 104 | Search Quality | 2개 (id: 40,41) |

총 Row: 5개, 총 패널(row 제외): 17개

**검증 결과 요약**:
- C01: PASS — 5개 JSON 파일 모두 유효한 JSON 구조
- C02: PASS — 5 rows, 17 panels (기준: 5 rows / 13+ panels)
- C03: PASS — 모든 datasource가 `{"type": "prometheus", "uid": "prometheus"}` 사용
- C04: PASS — schemaVersion: 38, templating.list: [] 필드 존재

**최종 결과**: 4/4 PASS

---

#### STORY-124: Neo4j 스키마 Cypher 검증

**대상 파일**: `infrastructure/database/neo4j/schema.cypher`

| TC ID | 검증 항목 | 합격 기준 |
|-------|----------|----------|
| C01 | Cypher 문법 유효성 | CREATE CONSTRAINT/INDEX 문법 유효 |
| C02 | 9개 unique constraint | 지정 노드 유형 전체 포함 |
| C03 | 17개 이상 인덱스 | 일반 인덱스 + fulltext + 관계 인덱스 포함 |
| C04 | 2개 fulltext 인덱스 | entity_fulltext_idx, document_fulltext_idx |
| C05 | ETL 파이프라인 호환성 | neo4j_storage.py에서 사용하는 노드/관계 타입 일치 |

**Constraint 목록 (9개)**:
1. `knowledge_id_unique` — Knowledge.knowledge_id
2. `document_id_unique` — Document.id
3. `chunk_id_unique` — Chunk.id
4. `entity_id_unique` — Entity.id
5. `person_id_unique` — Person.person_id
6. `technology_name_unique` — Technology.name
7. `topic_name_unique` — Topic.name
8. `keyword_value_unique` — Keyword.value
9. `project_id_unique` — Project.id

**Index 목록 (17개)**:
- 일반 인덱스 13개: knowledge_title_idx, knowledge_type_idx, document_type_idx, document_title_idx, chunk_knowledge_idx, chunk_index_idx, entity_type_idx, entity_name_idx, entity_canonical_name_idx, person_name_idx, technology_name_idx, topic_name_idx, keyword_value_idx, project_name_idx (14개)

> **수정**: 일반 인덱스는 14개, 관계 인덱스 2개, fulltext 2개 = 18개 총계

**Fulltext 인덱스 (2개)**:
- `entity_fulltext_idx` — Person|Technology|Topic|Keyword|Entity (name, description)
- `document_fulltext_idx` — Document (title)

**관계 인덱스 (2개)**:
- `contains_rel_idx` — CONTAINS (chunk_index)
- `belongs_rel_idx` — BELONGS_TO (created_at)

**검증 결과 요약**:
- C01: PASS — 유효한 Cypher 구문 (IF NOT EXISTS, FOR...REQUIRE 패턴)
- C02: PASS — 9개 unique constraint 모두 존재
- C03: PASS — 18개 인덱스 (17+ 기준 초과)
- C04: PASS — entity_fulltext_idx, document_fulltext_idx 존재
- C05: PASS — neo4j_storage.py의 Knowledge, Chunk, Entity, Person, Technology, Topic, Keyword 노드 타입과 일치

**최종 결과**: 5/5 PASS

---

### 2.2 단위 테스트 계획 (Phase 2)

#### STORY-121: GraphExplorerView Vitest 단위 테스트

**대상**: `knowledge_service/frontend/src/__tests__/components/GraphExplorerView.test.tsx`
**프레임워크**: Vitest + React Testing Library
**TC 수**: 12개

| TC 범주 | TC 수 | 내용 |
|---------|-------|------|
| 렌더링 | 3 | 초기 렌더, 로딩 상태, 에러 상태 |
| 노드 상호작용 | 3 | 노드 클릭, 호버, 선택 |
| 검색 기능 | 3 | 검색 입력, 결과 필터, 초기화 |
| 레이아웃 | 2 | 그래프 레이아웃 변경 |
| 접근성 | 1 | ARIA 속성 검증 |

#### STORY-122: 동적 검색 전략 pytest 단위 테스트

**대상**: `knowledge_service/src/tests/unit/test_dynamic_search_strategy.py`
**프레임워크**: pytest
**TC 수**: 14개

| TC 범주 | TC 수 | 내용 |
|---------|-------|------|
| 전략 선택 로직 | 4 | query 특성에 따른 전략 자동 선택 |
| Hybrid 검색 | 3 | Dense + Sparse + Graph 결합 |
| Graph 검색 | 3 | Neo4j 서브그래프 탐색 |
| 가중치 조정 | 2 | 동적 가중치 계산 |
| 에러 처리 | 2 | 전략 fallback |

#### STORY-125: ETL CLI pytest 단위 테스트

**대상**: `knowledge_service/src/tests/unit/test_etl_cli.py`
**프레임워크**: pytest
**TC 수**: 8개

| TC 범주 | TC 수 | 내용 |
|---------|-------|------|
| CLI 인자 파싱 | 3 | --phase, --input, --output 옵션 |
| Phase 실행 | 3 | Phase1/2/3 실행 흐름 |
| 에러 처리 | 2 | 잘못된 인자, 파일 없음 |

#### STORY-127: Gateway JUnit 테스트

**대상**: `knowledge_service/backend/src/test/java/.../GatewayAuthTest.java`
**프레임워크**: JUnit 5 + Mockito
**TC 수**: 10개

| TC 범주 | TC 수 | 내용 |
|---------|-------|------|
| JWT 검증 | 4 | 유효/만료/변조/없음 토큰 |
| 라우팅 | 3 | /api/v1/**, /auth/**, /public/** |
| CORS | 2 | Allow/Deny 헤더 |
| Circuit Breaker | 1 | Resilience4j 상태 |

---

### 2.3 E2E 테스트 계획 (Phase 3)

**대상 파일**: `knowledge_service/frontend/e2e/graph-explorer.spec.ts`
**프레임워크**: Playwright
**TC 수**: 7개

| TC ID | Story | 제목 | 합격 기준 |
|-------|-------|------|----------|
| E01 | STORY-121 | /knowledge 페이지 접근 | URL 접근 후 main content 렌더링 |
| E02 | STORY-121 | Graph Explorer 탭 전환 | 탭 클릭 후 graph content 표시 |
| E03 | STORY-121 | Graph 캔버스 렌더링 | canvas/svg 요소 존재 및 크기 > 0 |
| E04 | STORY-121 | 검색이 그래프 업데이트 트리거 | 검색어 입력 후 그래프 변경 |
| E05 | STORY-121 | 접근성 (ARIA) | role, aria-label, heading 존재 |
| E06 | STORY-122 | Chat Search 응답 수신 | "RAG란 무엇인가?" 질문 → 응답 |
| E07 | STORY-122 | Keyword Search 결과 표시 | "Docker" 검색 → 결과 표시 |

---

## 3. 품질 기준 (Quality Gates)

| 지표 | 기준 | 도구 |
|------|------|------|
| 설정 검증 통과율 | 100% (15/15 TC) | 수동 검증 |
| 단위 테스트 통과율 | 95%+ | pytest/Vitest/JUnit |
| E2E 테스트 통과율 | 85%+ | Playwright |
| 코드 커버리지 | 80%+ | pytest-cov/Vitest coverage |

---

## 4. 테스트 환경

| 구성 요소 | 버전/설정 |
|----------|----------|
| OS | Linux (WSL2) |
| Python | 3.11+ |
| pytest | 최신 |
| Playwright | @playwright/test |
| Docker | 컨테이너 기반 통합 테스트 |
| TEST_MODE | docker (Mock 모드 금지) |

---

## 5. 테스트 일정

| 단계 | 작업 | 완료 기준 |
|------|------|----------|
| Phase 1 | 설정 파일 검증 (#1,#2,#3) | 15/15 TC PASS |
| Phase 2 | E2E 테스트 작성 (#8) | 7 TC 작성 완료 |
| Phase 3 | 문서화 (#9,#10) | 계획서 + 결과 보고서 |

---

## 6. 리스크 및 완화 전략

| 리스크 | 영향 | 완화 전략 |
|--------|------|----------|
| Graph 기능 미완성 | E01~E04 실패 | graceful fallback 테스트 작성 |
| Docker 환경 미구동 | 통합 테스트 실패 | 설정 검증은 정적 분석으로 대체 |
| Neo4j 스키마 불일치 | C05 실패 | codebase audit 통해 neo4j_storage.py와 대조 |

---

## 7. 산출물

| 산출물 | 경로 |
|--------|------|
| 테스트 계획서 | `docs/04_testing/01_test_plans/09_sprint09_p2_test_plan.md` |
| E2E 테스트 | `frontend/e2e/graph-explorer.spec.ts` |
| E2E 결과 보고서 | `docs/04_testing/05_e2e/19_sprint09_p2_e2e_test_results.md` |
| 종합 테스트 리포트 | `docs/04_testing/07_test_results/09_sprint09_p2_test_report.md` |
