# UI 사용자 테스트 — 2026-02-18

Sprint 12 완료 후 UI 기반 사용자 테스트 수행 기록

---

## 서비스 접속 정보 (Development)

| 서비스 | URL | ID / Password |
|--------|-----|---------------|
| **Frontend** | http://localhost | (아래 AI Service 또는 Keycloak SSO) |
| **AI Service Login** | http://localhost:8000/api/v1/auth/login | `admin@example.com` / `admin123!` |
| **AI Service Docs** | http://localhost:8000/docs | (인증 불필요) |
| **Keycloak SSO** | Frontend SSO 버튼 | `admin` / `admin123` |
| | | `test` / `password123` |
| **Keycloak Admin** | http://localhost:8180/admin | `admin` / `keycloak_admin_2026!` |
| **Grafana** | http://localhost:3001 | `admin` / `test1234` |
| **Kibana** | http://localhost:5601 | (인증 불필요) |
| **Neo4j Browser** | http://localhost:7474 | `neo4j` / `neo4j_dev_2026!` |
| **MinIO Console** | http://localhost:9001 | `minioadmin` / `minio_dev_2026!` |
| **Prometheus** | http://localhost:9090 | (인증 불필요) |
| **Jaeger UI** | http://localhost:16686 | (인증 불필요) |
| **PostgreSQL** | localhost:5432 | `knowledge` / `knowledge_dev_2026!` |
| **Redis** | localhost:6379 | (비밀번호 없음) |
| **Gateway Health** | http://localhost:8080/actuator/health | (인증 불필요) |
| **Backend Health** | http://localhost:8081/actuator/health | (인증 불필요) |
| **Swagger UI** | http://localhost:8080/swagger-ui.html | (인증 불필요) |

> Keycloak Realm: `hybrid-rag` | Client: `knowledge-frontend` (public)

---

## 테스트 문서 목록

| 파일 | 내용 |
|------|------|
| [00_pre_check_report.md](./00_pre_check_report.md) | 사전점검 보고서 (Infra+DevOps+QA) |
| [01_upload_test_report.md](./01_upload_test_report.md) | 문서 업로드 E2E 테스트 + 이슈 수정 보고서 |
| [02_neo4j_schema_migration_report.md](./02_neo4j_schema_migration_report.md) | Neo4j 스키마 통일 마이그레이션 보고서 |

---

## 시스템 현황

| 항목 | 수치 |
|------|------|
| 컨테이너 | 18개 |
| 문서 | 1,437개 |
| 청크 | 42,462개 |
| 엔티티 | 129,152개 |
| 관계 | 775,366개 |
| RAGAS 등급 | A- (v11) |
| 테스트 커버리지 | 97% |

---

*관리: Claude Code + Agent Teams | Sprint 12*
