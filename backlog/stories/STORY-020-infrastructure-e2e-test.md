# STORY-020: Infrastructure E2E Test Execution

## Metadata

| Item | Value |
|------|-------|
| **Jira ID** | SCRUM-20 |
| **Epic** | EPIC-000 (Infrastructure Setup) |
| **Status** | In Progress |
| **Priority** | P0 (Critical) |
| **Story Points** | 5 |
| **Assignee** | QA |
| **Sprint** | Sprint 01 Validation |

---

## User Story

**As a** DevOps engineer and QA lead,
**I want** to execute end-to-end integration tests on the Sprint 01 infrastructure,
**So that** we can validate all 18 Docker containers work together correctly before proceeding to Sprint 02.

---

## Background

Sprint 01 was completed on Day 1 (2026-01-20) with the following deliverables that need validation:
- Docker Compose environment with 18 containers
- Database initialization scripts (PostgreSQL, Elasticsearch, Neo4j)
- Keycloak SSO configuration
- Project skeletons (Backend, Frontend, AI Service, API Gateway)

---

## Acceptance Criteria

### Container Health
- [ ] **Given** Docker Compose is started, **When** all containers initialize, **Then** all 18 containers reach healthy state within 5 minutes
- [ ] **Given** all containers are running, **When** checking container status, **Then** no containers are in restart loop

### Database Initialization
- [ ] **Given** init-db script runs, **When** checking PostgreSQL, **Then** all tables (knowledge, users, documents, etc.) exist with correct schema
- [ ] **Given** init-db script runs, **When** checking Elasticsearch, **Then** knowledge-chunks index exists with dense_vector mapping
- [ ] **Given** init-db script runs, **When** checking Neo4j, **Then** all constraints and indices are applied
- [ ] **Given** init-db script runs, **When** checking MinIO, **Then** all required buckets exist (documents, processed, temp, backups)

### Authentication Flow
- [ ] **Given** Keycloak is running, **When** accessing admin console, **Then** login succeeds with admin credentials
- [ ] **Given** Keycloak realm exists, **When** performing OAuth2 password grant, **Then** valid JWT token is returned
- [ ] **Given** valid JWT token, **When** accessing protected API, **Then** request succeeds
- [ ] **Given** no/invalid token, **When** accessing protected API, **Then** HTTP 401 is returned

### Service Integration
- [ ] **Given** all services are running, **When** client requests through Nginx, **Then** requests are routed to correct backend
- [ ] **Given** API Gateway is running, **When** backend routes are called, **Then** responses are returned correctly
- [ ] **Given** Backend is running, **When** it connects to databases, **Then** connections succeed

### Observability
- [ ] **Given** Prometheus is running, **When** checking targets, **Then** all scrape targets are UP
- [ ] **Given** Grafana is running, **When** accessing dashboards, **Then** metrics are displayed
- [ ] **Given** Loki is running, **When** querying logs, **Then** container logs are returned

---

## Tasks

### Phase 1: Preparation (Day 1)
- [ ] Set up test environment with .env configuration
- [ ] Review test plan document
- [ ] Prepare test scripts and tools

### Phase 2: Container Health Tests (Day 1)
- [ ] TC-INFRA-101: Execute `docker compose up -d`
- [ ] TC-INFRA-102 ~ TC-INFRA-116: Run health checks for all containers
- [ ] Document any startup issues

### Phase 3: Database Tests (Day 2)
- [ ] TC-INFRA-201 ~ TC-INFRA-203: Verify PostgreSQL schema
- [ ] TC-INFRA-204 ~ TC-INFRA-205: Verify Elasticsearch indices
- [ ] TC-INFRA-206 ~ TC-INFRA-207: Verify Neo4j constraints
- [ ] TC-INFRA-208: Verify MinIO buckets

### Phase 4: Authentication Tests (Day 3)
- [ ] TC-INFRA-301 ~ TC-INFRA-304: Keycloak configuration verification
- [ ] TC-INFRA-305 ~ TC-INFRA-310: OAuth2 flow testing

### Phase 5: Integration Tests (Day 4)
- [ ] TC-INFRA-401 ~ TC-INFRA-404: Routing tests
- [ ] TC-INFRA-405 ~ TC-INFRA-410: Service connectivity tests

### Phase 6: Observability Tests (Day 5)
- [ ] TC-INFRA-501 ~ TC-INFRA-508: Metrics, logs, traces verification

### Phase 7: Reporting (Day 6)
- [ ] Fix critical defects
- [ ] Re-run failed tests
- [ ] Generate test report
- [ ] Update documentation

---

## Technical Notes

### Test Environment

```bash
# Start full stack
cd infrastructure/docker
docker compose --profile init up -d

# Run health check script
./scripts/test/infrastructure_health_check.sh

# Run full E2E test suite
pytest tests/e2e/infrastructure/ -v --html=report.html
```

### Test Tools Required
- Docker Compose v2.20+
- curl, jq for API testing
- pytest for automated tests
- Docker exec for container commands

### Test Data Requirements
- Test user credentials for Keycloak
- Sample documents for MinIO upload
- Test queries for database verification

---

## Sub-Tasks

| Sub-Task ID | Description | Assignee | Status |
|-------------|-------------|----------|--------|
| TASK-020-1 | Container health test execution | QA | To Do |
| TASK-020-2 | Database initialization verification | QA | To Do |
| TASK-020-3 | Keycloak authentication testing | QA | To Do |
| TASK-020-4 | Service integration testing | QA | To Do |
| TASK-020-5 | Observability stack verification | QA | To Do |
| TASK-020-6 | Test report generation | QA | To Do |

---

## Definition of Done

- [ ] All 52 test cases executed
- [ ] P0 test pass rate: 100%
- [ ] P1 test pass rate: >= 95%
- [ ] All Critical/High defects resolved
- [ ] Test report generated and reviewed
- [ ] Documentation updated
- [ ] Sprint 02 blockers identified and communicated

---

## Test Plan Reference

- [Infrastructure E2E Test Plan](../../knowledge_service/docs/04_testing/infrastructure_e2e_test_plan.md)

---

## Risk and Dependencies

### Dependencies
- Sprint 01 deliverables must be complete
- Docker environment must have sufficient resources (16GB+ RAM)
- All required .env variables must be configured

### Risks
| Risk | Mitigation |
|------|------------|
| Memory exhaustion | Use lightweight mode or selective startup |
| Container startup failures | Check logs, increase health check timeout |
| Network issues | Verify Docker network configuration |

---

## Timeline

| Phase | Duration | Dates |
|-------|----------|-------|
| Preparation | 0.5 day | 01-21 AM |
| Container Tests | 0.5 day | 01-21 PM |
| Database Tests | 1 day | 01-22 |
| Auth Tests | 1 day | 01-23 |
| Integration Tests | 1 day | 01-24 |
| Observability + Fixes | 1 day | 01-25 |
| Reporting | 0.5 day | 01-27 |
| **Total** | **5.5 days** | 01-21 ~ 01-27 |

---

## References

- [Sprint 01 Backlog](../sprints/sprint-01.md)
- [Docker Compose Configuration](../../infrastructure/docker/docker-compose.yml)
- [Unit/Integration Test Plan](../../knowledge_service/docs/04_testing/unit_integration_test_plan.md)
