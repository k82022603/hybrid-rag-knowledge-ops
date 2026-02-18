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
| [01_upload_test_report.md](./01_upload_test_report.md) | 문서 업로드 E2E 테스트 + 이슈 수정 + 스키마 재검증 + **대용량 PDF 테스트** |
| [02_neo4j_schema_migration_report.md](./02_neo4j_schema_migration_report.md) | Neo4j 스키마 통일 마이그레이션 + **검색 검증** 보고서 |

---

## 테스트 진행 타임라인

| 시간 | 내용 | 결과 |
|------|------|:----:|
| 14:00~15:00 | 사전점검 (인프라 18개 컨테이너) | PASS |
| 15:40~16:30 | 업로드 E2E 테스트 (13 케이스) | 9 PASS, 3 WARN, 1 FAIL |
| 16:30~18:00 | 발견 이슈 6건 수정 (인증, Neo4j, PG, 엔티티) | 6/6 해결 |
| 19:30~20:30 | Neo4j 스키마 통일 코드 수정 + DB 마이그레이션 | 완료 (298K 관계) |
| 20:50~21:15 | **스키마 통일 후 재검증** (4파일 업로드 + 14건 검색) | **전체 PASS** |
| 21:05~21:15 | **대용량 PDF 업로드 테스트** (Nike 10-K 3건, 사용자 직접) | **0/3 FAIL** |
| 21:15~21:30 | **타임아웃 증가 적용** (Frontend/Nginx/Docling 1200s 통일) | 적용 완료 |
| 21:30~21:50 | **대시보드 빠른 검색 버그 수정** + 3개 컨테이너 재배포 | **수정 완료** |

---

## 시스템 현황 (재검증 후)

| 항목 | 수치 |
|------|------|
| 컨테이너 | 18개 (전체 healthy) |
| 문서 | 1,437 + 4 (테스트) |
| 청크 | 42,462+개 |
| 엔티티 | 129,152+개 |
| RELATED_TO 관계 | 298,636 (통일 완료) |
| MENTIONS 관계 | 404,411 (통일 완료) |
| RAGAS 등급 | A- (v11) |
| 테스트 커버리지 | 97% |

---

*관리: Claude Code + Agent Teams | Sprint 12*
