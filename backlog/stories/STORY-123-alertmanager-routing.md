# STORY-123: Alertmanager 채널 분기 (팀별 라우팅)

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | - |
| **Epic** | Observability 강화 |
| **Status** | To Do |
| **Priority** | P2 |
| **Story Points** | 2 |
| **Assignee** | DevOps |
| **Sprint** | Sprint 09 |

---

## Acceptance Criteria

- [ ] database-slack receiver → proj-hrkp-alerts (DB 전용)
- [ ] ai-service-slack receiver → proj-hrkp-alerts (AI 전용)
- [ ] security-slack receiver → proj-hrkp-alerts (보안 전용)
- [ ] 라우팅 규칙 테스트 완료

---

## Tasks

- [ ] `alertmanager.yml` 6개 receiver 채널 분기 적용
- [ ] 라우팅 규칙 검증 (`amtool check-config`)
- [ ] 테스트 알림 발송 확인

---

## 의존성

- **선행**: STORY-117 (Prometheus Exporter 활성화 — 메트릭 수집 선행 필요)
