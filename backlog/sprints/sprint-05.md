# Sprint 05: RAG Performance Test

## 스프린트 정보

| 항목 | 값 |
|------|-----|
| **기간** | 2026-03-17 ~ 2026-03-28 (2주) |
| **Velocity (계획)** | 26 pts |
| **Velocity (실제)** | - |
| **Status** | planned |
| **Jira Sprint ID** | 39 |

---

## 스프린트 목표

> **RAG 품질 평가 + 성능 최적화 + 보안 테스트**

핵심 목표:
1. Ragas 프레임워크 기반 RAG 품질 평가
2. 검색 품질 메트릭 측정 (Precision, Recall, MRR, NDCG)
3. k6 성능 부하 테스트 실행
4. 병목 구간 식별 및 최적화
5. OWASP 보안 취약점 스캔

---

## 선행 조건

Sprint 4 완료 항목 (필수):
- [ ] E2E 통합 테스트 시나리오 (STORY-046)
- [ ] Playwright E2E 테스트 (STORY-047)
- [ ] Prometheus 메트릭 수집 (STORY-050)
- [ ] Grafana 대시보드 구성 (STORY-051)
- [ ] Loki 로그 집계 (STORY-052)
- [ ] Jaeger 분산 트레이싱 (STORY-053)
- [ ] 알림 규칙 설정 (STORY-054)

---

## 백로그

### Epic 005: RAG Quality & Performance (26 pts)

| Priority | ID | Jira | 제목 | Points | Assignee | Status |
|----------|-----|------|------|--------|----------|--------|
| P0 | STORY-060 | SCRUM-61 | Ragas 평가 파이프라인 | 5 | QA, MLRag | To Do |
| P0 | STORY-061 | SCRUM-62 | 검색 품질 평가 (IR Metrics) | 5 | QA | To Do |
| P0 | STORY-062 | SCRUM-63 | 성능 부하 테스트 (k6) | 5 | QA, DevOps | To Do |
| P0 | STORY-063 | SCRUM-64 | 최적화 및 튜닝 | 5 | MLRag, Backend | To Do |
| P1 | STORY-064 | SCRUM-65 | 보안 취약점 스캔 | 3 | QA, DevOps | To Do |
| P1 | STORY-065 | SCRUM-66 | 품질 게이트 자동화 | 3 | DevOps | To Do |

### Stretch (여유 시 추가)

| ID | 제목 | Points |
|----|------|--------|
| - | A/B 테스트 프레임워크 | 5 |
| - | 자동 하이퍼파라미터 튜닝 | 5 |
| - | 성능 회귀 테스트 자동화 | 3 |

---

## 기술 의존성 (사전 준비)

### 테스트 데이터
- [ ] Q&A 데이터셋 100개 이상 준비
- [ ] Ground Truth 어노테이션
- [ ] 테스트 쿼리 컬렉션

### 도구
- [ ] Ragas 라이브러리 설치
- [ ] k6 성능 테스트 도구
- [ ] Trivy 컨테이너 스캔
- [ ] OWASP ZAP 웹 스캔

---

## 일일 계획

### Week 1

#### Day 1 (03-17, Mon)
- [ ] 스프린트 킥오프 미팅
- [ ] 테스트 데이터셋 최종 검토
- [ ] STORY-060 착수: Ragas 환경 설정

#### Day 2 (03-18, Tue)
- [ ] STORY-060: RAG 파이프라인 실행
- [ ] STORY-060: Ragas 메트릭 수집

#### Day 3 (03-19, Wed)
- [ ] STORY-060: 품질 리포트 생성
- [ ] STORY-061 착수: IR 메트릭 구현

#### Day 4 (03-20, Thu)
- [ ] STORY-060 완료
- [ ] STORY-061: Precision, Recall 측정
- [ ] STORY-061: MRR, NDCG 측정

#### Day 5 (03-21, Fri)
- [ ] STORY-061 완료
- [ ] STORY-062 착수: k6 시나리오 작성
- [ ] Week 1 리뷰

### Week 2

#### Day 6 (03-24, Mon)
- [ ] STORY-062: 부하 테스트 실행
- [ ] STORY-062: 성능 리포트 분석

#### Day 7 (03-25, Tue)
- [ ] STORY-062 완료
- [ ] STORY-063 착수: 병목 구간 식별
- [ ] STORY-063: 캐싱 전략 적용

#### Day 8 (03-26, Wed)
- [ ] STORY-063: 쿼리 최적화
- [ ] STORY-063: 인덱스 튜닝
- [ ] STORY-064 착수: Trivy 스캔

#### Day 9 (03-27, Thu)
- [ ] STORY-063: 재측정 및 검증
- [ ] STORY-064: OWASP ZAP 스캔
- [ ] STORY-065 착수: CI 품질 게이트

#### Day 10 (03-28, Fri)
- [ ] STORY-063, 064, 065 완료
- [ ] 전체 품질 리포트 작성
- [ ] 스프린트 리뷰 & 회고
- [ ] Sprint 6 계획 준비

---

## Definition of Done

각 Story 완료 기준:
- [ ] 모든 Acceptance Criteria 충족
- [ ] 테스트 리포트 작성
- [ ] 코드 리뷰 완료
- [ ] 품질 기준 충족
- [ ] 기술 부채 없음

---

## 리스크 및 블로커

| 유형 | 설명 | 영향 | 대응 | 상태 |
|------|------|------|------|------|
| Risk | 품질 기준 미달 | High | 튜닝 iteration | Open |
| Risk | 테스트 데이터 품질 | High | 전문가 검토 | Open |
| Risk | 성능 병목 해결 어려움 | Medium | 아키텍처 변경 검토 | Open |
| Blocker | Sprint 4 미완료 시 | Critical | Sprint 4 우선 | Monitoring |

---

## 산출물

### 평가 코드
```
ai-service/src/
├── evaluation/
│   ├── ragas_eval.py               # STORY-060
│   ├── ir_metrics.py               # STORY-061
│   └── test_datasets/
│       ├── qa_dataset.json
│       └── ground_truth.json
```

### 성능 테스트
```
tests/performance/
├── k6/
│   ├── load-test.js                # STORY-062
│   ├── stress-test.js
│   └── spike-test.js
└── reports/
    └── performance-report.html
```

### 보안 스캔
```
tests/security/
├── trivy/
│   └── scan-results.json           # STORY-064
├── owasp-zap/
│   └── scan-report.html
└── dependency-check/
    └── report.html
```

### CI/CD
```
.gitlab-ci.yml  # 또는 .github/workflows/
├── quality-gate.yml                # STORY-065
│   ├── ragas-check
│   ├── performance-check
│   └── security-check
```

### 리포트
- [ ] Ragas 품질 리포트
- [ ] IR 메트릭 리포트
- [ ] 성능 테스트 리포트
- [ ] 보안 스캔 리포트
- [ ] 최적화 전후 비교 리포트

---

## 품질 게이트 기준

### RAG 품질 (Ragas)
| 메트릭 | 목표 | 게이트 |
|--------|------|--------|
| Faithfulness | >= 0.9 | PASS/FAIL |
| Answer Relevancy | >= 0.85 | PASS/FAIL |
| Context Precision | >= 0.8 | PASS/FAIL |
| Context Recall | >= 0.75 | PASS/FAIL |

### 검색 품질 (IR Metrics)
| 메트릭 | 목표 | 게이트 |
|--------|------|--------|
| Precision@5 | >= 0.8 | PASS/FAIL |
| Recall@10 | >= 0.85 | PASS/FAIL |
| MRR | >= 0.7 | PASS/FAIL |
| NDCG@10 | >= 0.8 | PASS/FAIL |

### 성능 (k6)
| 메트릭 | 목표 | 게이트 |
|--------|------|--------|
| P50 Latency | < 1초 | PASS/FAIL |
| P95 Latency | < 3초 | PASS/FAIL |
| P99 Latency | < 5초 | PASS/FAIL |
| Error Rate | < 1% | PASS/FAIL |
| Throughput | >= 50 QPS | PASS/FAIL |

### 보안 (Trivy, OWASP ZAP)
| 항목 | 목표 | 게이트 |
|------|------|--------|
| Critical 취약점 | 0개 | PASS/FAIL |
| High 취약점 | <= 5개 | PASS/FAIL |
| OWASP Top 10 | 통과 | PASS/FAIL |

---

## 메트릭 목표

| 메트릭 | 목표 | 측정 방법 |
|--------|------|-----------|
| Ragas Faithfulness | >= 0.9 | Ragas |
| P95 Latency | < 3초 | k6 |
| Critical 취약점 | 0개 | Trivy |
| 품질 게이트 통과 | 100% | CI/CD |

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

- [EPIC-005: RAG Quality & Performance](../epics/EPIC-005-rag-quality-performance.md)
- [스프린트 실행 계획서](../../docs/02_스프린트_실행_계획서.md)
- [테스트 계획서](../../knowledge_service/docs/04_testing/unit_integration_test_plan.md)
- [Ragas 공식 문서](https://docs.ragas.io/)
- [k6 성능 테스트](https://k6.io/docs/)
