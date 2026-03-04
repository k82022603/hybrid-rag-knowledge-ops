# STORY-118: RAGAS 베이스라인 측정 + CI/CD 통합

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | - |
| **Epic** | 테스트 자동화 |
| **Status** | To Do |
| **Priority** | P1 |
| **Story Points** | 3 |
| **Assignee** | QA/DevOps |
| **Sprint** | Sprint 09 |

---

## User Story

**As a** QA Engineer,
**I want** RAGAS 품질 메트릭이 CI/CD에서 자동으로 측정되고 보고되기를,
**So that** 코드 변경이 RAG 품질에 미치는 영향을 즉시 파악할 수 있다.

---

## 배경

현재 RAGAS 평가 결과:
- Mean: 0.711 (A-)
- Faithfulness: 0.935
- Precision: 0.618 (약점)
- Recall: 0.672

평가 결과가 4곳에 분산 저장되어 있고 수동 측정만 가능한 상태.

---

## Acceptance Criteria

- [ ] Sprint 09 착수 시점 RAGAS 베이스라인 측정 완료 (현재 값 확정)
- [ ] RAGAS 평가 스크립트 CI/CD 통합 (주간 자동 실행)
- [ ] 품질 기준 미달 시 Slack 알림 (Faithfulness < 0.9, Relevancy < 0.85)
- [ ] 평가 결과 리포트 자동 저장

---

## Tasks

- [ ] RAGAS 베이스라인 측정 실행 (TEST_MODE=docker)
- [ ] `.github/workflows/ragas-eval.yml` 워크플로우 작성 (주 1회 스케줄)
- [ ] 품질 임계값 설정 (Faithfulness >0.9, Relevancy >0.85, Precision >0.8)
- [ ] 결과 Slack 알림 연동 (DevOps 협업)
- [ ] 평가 결과 `knowledge_service/docs/results/` 자동 저장

---

## 기술 노트

### 영향 범위
- `.github/workflows/ragas-eval.yml` (신규)
- `knowledge_service/src/tests/evaluation/`

---

## 의존성

- **선행**: Docker 환경 기동
- **관련**: STORY-119 (RAGAS 종합 리포트), STORY-115 (Reranker 업그레이드 효과 측정)
