# STORY-019: E2E Retest (Goal 100%)

## Metadata

| Item | Value |
|------|-------|
| **Jira ID** | SCRUM-19 |
| **Epic** | EPIC-000 (Infrastructure Setup) |
| **Status** | To Do |
| **Priority** | P1 |
| **Story Points** | 3 |
| **Assignee** | QA |
| **Sprint** | Sprint 02 (Carry Over from Sprint 01 Validation) |

---

## User Story

**As a** QA engineer,
**I want** to resolve all skipped E2E tests and achieve 100% pass rate,
**So that** we can confirm the infrastructure is fully operational before proceeding with Sprint 02 development.

---

## Background

Sprint 01 E2E 테스트 결과:
- **76개 테스트** 중 **52개 통과 (68%)**, **0개 실패**, **24개 Skip**
- Skip 원인 분석 완료 (SCRUM-15~18에서 일부 해결)

### Skip 테스트 분류

| Category | Count | Reason | Resolution |
|----------|-------|--------|------------|
| Test User Not Set | 4 | Keycloak test-user 미설정 | Keycloak 설정 |
| init-db Not Run | 5 | ES/Neo4j 스키마 미생성 | init-db 실행 |
| Stub Mode Limit | 7 | 실제 서비스 연결 필요 | Sprint 02+ 서비스 개발 |
| Grafana Auth | 4 | API 인증 필요 | 환경변수 설정 |
| Data Collection | 4 | Metrics/Logs 수집 대기 | Continuous |

---

## Acceptance Criteria

### Sprint 02 초반 해소 가능 (13개)

- [ ] **Given** Keycloak realm에 test-user 추가, **When** OAuth2 Password Grant 수행, **Then** 4개 테스트 통과
- [ ] **Given** init-db 컨테이너 실행, **When** ES/Neo4j 스키마 생성, **Then** 5개 테스트 통과
- [ ] **Given** Grafana 환경변수 설정, **When** API 인증 활성화, **Then** 4개 테스트 통과

### Sprint 02+ 해소 (11개)

- [ ] **Given** 실제 서비스 개발 완료, **When** Stub 교체, **Then** 7개 테스트 통과
- [ ] **Given** 충분한 운영 시간 경과, **When** 메트릭/로그 수집, **Then** 4개 테스트 통과

---

## Tasks

### Phase 1: Quick Wins (Sprint 02 Day 1-2)

| # | Task | Skip Count | Effort |
|---|------|------------|--------|
| 1 | Keycloak test-user 추가 (realm-export.json 또는 스크립트) | 4 | Low |
| 2 | init-db 컨테이너 실행 | 5 | Low |
| 3 | Grafana API 인증 설정 (GRAFANA_ADMIN_PASSWORD) | 4 | Low |

### Phase 2: Retest Execution (Sprint 02 Day 3)

- [ ] 전체 E2E 테스트 재실행
- [ ] Skip 테스트 상태 확인
- [ ] 결과 보고서 업데이트

### Phase 3: Long-term Resolution (Sprint 02+)

- [ ] Stub 서비스 -> 실제 서비스 교체 (Backend, AI Service 개발 후)
- [ ] 메트릭/로그 수집 확인 (운영 안정화 후)

---

## Technical Notes

### Keycloak Test User 추가

```bash
# Option 1: Admin API
curl -X POST "http://localhost:8089/admin/realms/hybrid-rag/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "test-user",
    "email": "test@example.com",
    "enabled": true,
    "credentials": [{"type": "password", "value": "test123"}]
  }'

# Option 2: realm-export.json 업데이트
# infrastructure/keycloak/realm-export.json에 users 섹션 추가
```

### init-db 실행

```bash
cd infrastructure/docker
docker compose --profile init up init-db
```

### Grafana 인증 설정

```bash
# .env 파일에 추가
GRAFANA_ADMIN_PASSWORD=admin

# 또는 anonymous access 활성화
GF_AUTH_ANONYMOUS_ENABLED=true
```

---

## Definition of Done

- [ ] 13개 Quick Wins Skip 테스트 해소 (4+5+4)
- [ ] E2E 통과율 85% 이상 (65/76)
- [ ] 잔여 Skip 테스트 해소 계획 문서화
- [ ] 테스트 보고서 업데이트

---

## Related Issues

- **Predecessor**: SCRUM-18 (E2E 테스트 코드 환경변수 수정) - Done
- **Related**: SCRUM-20 (Infrastructure E2E Test) - In Progress
- **Blocker for**: Sprint 02 Core API 개발

---

## Risk and Dependencies

### Dependencies
- Keycloak Admin 접근 권한
- Docker Compose 환경 동작 확인
- 충분한 시스템 리소스 (16GB+ RAM)

### Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| init-db 실행 실패 | Medium | 수동 스키마 적용 |
| Keycloak API 접근 불가 | Medium | 직접 realm-export.json 수정 |
| 리소스 부족 | Low | Selective container startup |

---

## Timeline

| Phase | Duration | Target Date |
|-------|----------|-------------|
| Quick Wins | 2 days | Sprint 02 Day 1-2 |
| Retest | 1 day | Sprint 02 Day 3 |
| Long-term | Ongoing | Sprint 02+ |

---

## References

- [QA Review: E2E Test Coverage Analysis](../../knowledge_service/docs/02_design/review/2026-01-22_qa_review.md)
- [Infrastructure E2E Test Report (2026-01-21)](../../knowledge_service/docs/04_testing/infrastructure_e2e/04.infrastructure_e2e_test_report_2026-01-21.md)
- [STORY-020: Infrastructure E2E Test](./STORY-020-infrastructure-e2e-test.md)
