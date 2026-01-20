# Sprint 04: Integration + Observability

## 스프린트 정보

| 항목 | 값 |
|------|-----|
| **기간** | 2026-03-03 ~ 2026-03-14 (2주) |
| **Velocity (계획)** | 34 pts |
| **Velocity (실제)** | - |
| **Status** | planned |
| **Jira Sprint ID** | 38 |

---

## 스프린트 목표

> **E2E 통합 완성 + Observability 스택 구축**

핵심 목표:
1. Frontend -> Backend -> AI Service E2E 연동
2. Prometheus/Grafana 메트릭 수집 및 대시보드
3. Loki 로그 집계 및 검색
4. Jaeger 분산 트레이싱
5. 알림 규칙 설정

---

## 선행 조건

Sprint 3 완료 항목 (필수):
- [ ] HybridRetriever 구현 (STORY-030)
- [ ] RRF Fusion 알고리즘 (STORY-031)
- [ ] BGE Reranker 통합 (STORY-032)
- [ ] LangGraph 워크플로우 (STORY-033)
- [ ] Frontend Keycloak 연동 (STORY-040)
- [ ] Dashboard UI (STORY-041)
- [ ] Search UI 컴포넌트 (STORY-042)
- [ ] SSE 스트리밍 응답 (STORY-043)
- [ ] Backend Search Service (STORY-044)
- [ ] 초기 데이터 ETL (STORY-045)

---

## 백로그

### E2E 통합 (10 pts)

| Priority | ID | Jira | 제목 | Points | Assignee | Status |
|----------|-----|------|------|--------|----------|--------|
| P0 | STORY-046 | SCRUM-47 | E2E 통합 테스트 시나리오 | 5 | QA | To Do |
| P0 | STORY-047 | SCRUM-48 | Playwright E2E 테스트 | 5 | QA | To Do |

### Epic 004: Observability & Monitoring (24 pts)

| Priority | ID | Jira | 제목 | Points | Assignee | Status |
|----------|-----|------|------|--------|----------|--------|
| P0 | STORY-050 | SCRUM-51 | Prometheus 메트릭 수집 | 5 | DevOps | To Do |
| P0 | STORY-051 | SCRUM-52 | Grafana 대시보드 구성 | 5 | DevOps | To Do |
| P0 | STORY-052 | SCRUM-53 | Loki 로그 집계 | 5 | DevOps | To Do |
| P1 | STORY-053 | SCRUM-54 | Jaeger 분산 트레이싱 | 5 | DevOps, Backend | To Do |
| P1 | STORY-054 | SCRUM-55 | 알림 규칙 및 Alertmanager | 4 | DevOps | To Do |

### Stretch (여유 시 추가)

| ID | 제목 | Points |
|----|------|--------|
| - | Custom RAG 메트릭 대시보드 | 3 |
| - | 에러 분석 대시보드 | 2 |
| - | SLA 리포트 자동 생성 | 3 |

---

## 기술 의존성 (사전 준비)

### Observability Stack
- [ ] Prometheus 2.48 컨테이너 구성
- [ ] Grafana 10.2 컨테이너 구성
- [ ] Loki 2.9 + Promtail 구성
- [ ] Jaeger 1.51 컨테이너 구성

### Backend/AI Service
- [ ] Spring Boot Actuator 메트릭 노출
- [ ] FastAPI prometheus-fastapi-instrumentator
- [ ] OpenTelemetry SDK 연동

---

## 일일 계획

### Week 1

#### Day 1 (03-03, Mon)
- [ ] 스프린트 킥오프 미팅
- [ ] STORY-046 착수: E2E 테스트 시나리오 작성
- [ ] STORY-050 착수: Prometheus 설정

#### Day 2 (03-04, Tue)
- [ ] STORY-046: 인증/검색/지식 CRUD 시나리오
- [ ] STORY-050: Backend Actuator 연동

#### Day 3 (03-05, Wed)
- [ ] STORY-046 완료
- [ ] STORY-047 착수: Playwright 테스트 구현
- [ ] STORY-050: AI Service 메트릭 연동

#### Day 4 (03-06, Thu)
- [ ] STORY-047: 인증 플로우 테스트
- [ ] STORY-050 완료
- [ ] STORY-051 착수: Grafana 대시보드

#### Day 5 (03-07, Fri)
- [ ] STORY-047: 검색 플로우 테스트
- [ ] STORY-051: System Overview 대시보드
- [ ] Week 1 리뷰

### Week 2

#### Day 6 (03-10, Mon)
- [ ] STORY-047 완료
- [ ] STORY-051: API Performance 대시보드
- [ ] STORY-052 착수: Promtail 설정

#### Day 7 (03-11, Tue)
- [ ] STORY-051: RAG Quality 대시보드
- [ ] STORY-052: 로그 레이블 설계

#### Day 8 (03-12, Wed)
- [ ] STORY-051, 052 완료
- [ ] STORY-053 착수: Jaeger 설정
- [ ] STORY-053: Backend OpenTelemetry

#### Day 9 (03-13, Thu)
- [ ] STORY-053: AI Service 트레이싱
- [ ] STORY-054 착수: 알림 규칙 정의
- [ ] STORY-054: Alertmanager 설정

#### Day 10 (03-14, Fri)
- [ ] STORY-053, 054 완료
- [ ] 전체 통합 검증
- [ ] 스프린트 리뷰 & 회고
- [ ] Sprint 5 계획 준비

---

## Definition of Done

각 Story 완료 기준:
- [ ] 모든 Acceptance Criteria 충족
- [ ] 단위 테스트 작성 (커버리지 80%+)
- [ ] 코드 리뷰 완료
- [ ] 문서 업데이트
- [ ] 기술 부채 없음

---

## 리스크 및 블로커

| 유형 | 설명 | 영향 | 대응 | 상태 |
|------|------|------|------|------|
| Risk | 메트릭 카디널리티 | High | 레이블 최소화 | Open |
| Risk | 로그 볼륨 과다 | Medium | 샘플링 설정 | Open |
| Risk | 트레이싱 오버헤드 | Low | 샘플링 비율 | Open |
| Blocker | Sprint 3 미완료 시 | Critical | Sprint 3 우선 | Monitoring |

---

## 산출물

### Observability 설정
```
infrastructure/
├── prometheus/
│   ├── prometheus.yml              # STORY-050
│   └── rules/
│       └── alert_rules.yml         # STORY-054
├── grafana/
│   ├── provisioning/
│   │   ├── dashboards/
│   │   │   ├── system-overview.json    # STORY-051
│   │   │   ├── api-performance.json
│   │   │   └── rag-quality.json
│   │   └── datasources/
│   │       └── datasources.yml
│   └── alerting/
├── loki/
│   └── loki-config.yml             # STORY-052
├── promtail/
│   └── promtail-config.yml         # STORY-052
└── jaeger/
    └── jaeger-config.yml           # STORY-053
```

### 테스트
```
e2e-tests/
├── playwright.config.ts
├── tests/
│   ├── auth.spec.ts                # STORY-047
│   ├── search.spec.ts
│   └── knowledge.spec.ts
└── fixtures/
```

### 문서
- [ ] E2E 테스트 시나리오 문서
- [ ] Grafana 대시보드 가이드
- [ ] 알림 규칙 설명서
- [ ] 트레이싱 가이드

---

## 메트릭 목표

| 메트릭 | 목표 | 측정 방법 |
|--------|------|-----------|
| E2E 테스트 통과율 | 100% | Playwright |
| 메트릭 수집 | 모든 서비스 | Prometheus targets |
| 대시보드 | 5개 이상 | Grafana |
| 알림 규칙 | 10개 이상 | Alertmanager |

---

## Grafana 대시보드 구성

### 1. System Overview
- 전체 서비스 상태 (Up/Down)
- CPU/Memory 사용률
- 네트워크 트래픽
- 컨테이너 상태

### 2. API Performance
- Request Rate (RPS)
- Response Time (P50, P95, P99)
- Error Rate
- Top 10 느린 엔드포인트

### 3. RAG Quality
- Faithfulness Score
- Answer Relevancy Score
- Context Precision
- 검색 쿼리 수

### 4. Error Analysis
- 에러 유형별 분포
- 에러 발생 추이
- Top 10 에러 메시지
- 에러 발생 서비스

### 5. SLA Monitoring
- 가용성 (Uptime)
- P95 Latency SLA 준수
- Error Rate SLA 준수

---

## 스프린트 리뷰

### 완료된 항목
- (스프린트 종료 후 작성)

### 미완료 항목
- (스프린트 종료 후 작성)

### 데모 노트
- (스프린트 종료 후 작성)

---

## 회고 (Retrospective)

### Keep (계속할 것)
-

### Problem (문제점)
-

### Try (시도할 것)
-

---

## 참고 자료

- [EPIC-004: Observability & Monitoring](../epics/EPIC-004-observability-monitoring.md)
- [스프린트 실행 계획서](../../docs/02_스프린트_실행_계획서.md)
- [인프라 상세 설계서](../../knowledge_service/docs/02_design/infrastructure_detailed_design.md)
