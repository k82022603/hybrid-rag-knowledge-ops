# Infrastructure Scripts

백업, 복원, 롤백, 배포, 유지보수, 시크릿 관리, 성능 테스트를 위한 인프라 스크립트 모음입니다.

## 스크립트 목록

| 스크립트 | 설명 | 추가일 |
|----------|------|--------|
| `deploy.sh` | 메인 배포 스크립트 (환경별 배포, 롤백 포함) | 2026-02-04 |
| `pre-deploy-check.sh` | 배포 전 사전 검증 스크립트 | 2026-02-04 |
| `post-deploy-verify.sh` | 배포 후 검증 스크립트 | 2026-02-04 |
| `blue-green-deploy.sh` | Blue-Green 무중단 배포 스크립트 | 2026-02-04 |
| `staging-validation.sh` | Staging 환경 종합 검증 스크립트 (STORY-080) | 2026-02-04 |
| `performance-test.sh` | 성능 테스트 실행 스크립트 (STORY-081) | 2026-02-04 |
| `backup.sh` | PostgreSQL, Elasticsearch, Neo4j, MinIO 자동 백업 |  |
| `restore.sh` | 백업 데이터 복원 |  |
| `rollback.sh` | 애플리케이션/데이터베이스 롤백 |  |
| `validate-secrets.sh` | 시크릿 검증 및 생성 (STORY-076) |  |
| `backup.cron.example` | Crontab 설정 예시 |  |

---

## performance-test.sh - 성능 테스트 스크립트 (NEW)

### 개요

프로덕션 배포 전 성능 기준선을 설정하고 부하 테스트를 수행하는 스크립트입니다.
STORY-081: Performance Baseline Testing 구현의 일환으로 작성되었습니다.

k6 또는 Locust를 사용하여 부하 테스트를 수행합니다.

### 성능 목표

| Metric | Target | Acceptable |
|--------|--------|------------|
| API Response (P50) | < 500ms | < 1s |
| API Response (P95) | < 2s | < 3s |
| Search Latency (P95) | < 3s | < 5s |
| Throughput | > 100 req/s | > 50 req/s |
| Error Rate | < 0.1% | < 1% |

### 사용법

```bash
# 빠른 스모크 테스트 (10 VUs, 1분)
./performance-test.sh --quick

# 기본 부하 테스트 (k6, 100 VUs, 5분)
./performance-test.sh

# 전체 테스트 스위트 (Smoke -> Load -> Stress -> Spike)
./performance-test.sh --full

# Locust 사용 (Python 기반)
./performance-test.sh --tool locust --vus 50

# 커스텀 설정
./performance-test.sh \
    --tool k6 \
    --vus 100 \
    --duration 10m \
    --url http://localhost:8000

# Locust Web UI 모드
./performance-test.sh --tool locust --web

# 도움말
./performance-test.sh --help
```

### 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `-t, --tool` | 테스트 도구 (k6/locust) | k6 |
| `-u, --url` | 서비스 URL | http://localhost:8000 |
| `-v, --vus` | 가상 사용자 수 | 100 |
| `-d, --duration` | 테스트 기간 | 5m |
| `-r, --spawn-rate` | 사용자 생성 속도 (Locust) | 10 |
| `--auth-token` | Bearer 토큰 | - |
| `--quick` | 빠른 스모크 테스트 | - |
| `--full` | 전체 테스트 스위트 | - |
| `--web` | Locust Web UI 모드 | - |

### 테스트 시나리오

#### 1. Smoke Test (--quick)
- 1-10 VUs, 30초-1분
- 시스템 기본 기능 확인

#### 2. Load Test (default)
- 50-100 VUs, 10분
- 일반 운영 조건 시뮬레이션
- 기준선 측정

#### 3. Stress Test (--full 포함)
- 150 VUs, 6분
- 시스템 한계점 탐색

#### 4. Spike Test (--full 포함)
- 200 VUs 갑자기 증가
- 트래픽 급증 대응 확인

### 결과 출력

테스트 결과는 다음 위치에 저장됩니다:

```
knowledge_service/docs/results/performance/
  k6_results_YYYYMMDD_HHMMSS.json
  k6_summary_YYYYMMDD_HHMMSS.json
  locust_report_YYYYMMDD_HHMMSS.html
  locust_YYYYMMDD_HHMMSS_stats.csv
```

### 사전 요구사항

```bash
# k6 설치
# macOS
brew install k6

# Ubuntu/Debian
sudo apt-get update && sudo apt-get install k6

# Windows
choco install k6

# Locust 설치
pip install -r ../performance/requirements.txt
```

### 관련 문서

- [Performance Baseline Report](../../knowledge_service/docs/04_testing/performance_baseline_report.md)
- [Performance Testing Suite README](../performance/README.md)
- [k6 Load Test Script](../performance/k6-load-test.js)
- [Locust Test File](../performance/locustfile.py)

---

## staging-validation.sh - Staging 환경 종합 검증 (NEW)

### 개요

프로덕션 배포 전 Staging 환경에서 모든 검증 항목을 자동으로 수행하는 스크립트입니다.
STORY-080: Staging Environment Validation 구현의 일환으로 작성되었습니다.

### 검증 항목

| Category | Test Count | Target |
|----------|------------|--------|
| Infrastructure | 20+ | All Pass |
| Unit Tests | 627 | 100% |
| Integration Tests | 121 | 100% |
| E2E Tests | 192 | 100% |
| Security Tests | 35 | 100% |
| API Contract | 10+ | All Pass |
| Data Flow | 6 | Complete |

### 사용법

```bash
# 전체 검증 (권장)
./staging-validation.sh --full

# 빠른 스모크 테스트 (컨테이너 + 헬스체크만)
./staging-validation.sh --smoke

# 특정 카테고리만 실행
./staging-validation.sh --category unit
./staging-validation.sh --category integration
./staging-validation.sh --category e2e
./staging-validation.sh --category security
./staging-validation.sh --category contract
./staging-validation.sh --category dataflow

# 데이터 플로우 검증만
./staging-validation.sh --data-flow

# 도움말
./staging-validation.sh --help
```

### 검증 순서

```
[1] Pre-validation    - Docker, 환경 파일, 디렉토리 확인
[2] Container checks  - 18개 컨테이너 상태 확인
[3] Health checks     - 서비스 헬스 엔드포인트 확인
[4] Unit tests        - Backend, AI Service, Frontend 단위 테스트
[5] Integration tests - DB, API 통합 테스트
[6] E2E tests         - Playwright E2E 테스트
[7] Security tests    - 보안 취약점 검사
[8] Contract tests    - API 계약 검증
[9] Data flow         - 문서 업로드 -> 검색 전체 흐름 검증
```

### 출력 예시

```
=============================================================================
Hybrid RAG Knowledge Platform - Staging Environment Validation
=============================================================================
Mode:        --full
Timestamp:   2026-02-04 10:30:00
Project:     /path/to/hybrid-rag-knowledge-ops
=============================================================================

=== Pre-Validation Checks ===
[PASS] [INFRA] Docker daemon is running
[PASS] [INFRA] Docker Compose is available
[PASS] [INFRA] Staging environment file exists

=== Container Health Checks ===
[PASS] [CONTAINER] kp-nginx is running (health: healthy)
[PASS] [CONTAINER] kp-backend is running (health: healthy)
...

=============================================================================
VALIDATION SUMMARY
=============================================================================
Total Tests:  85
Passed:       82
Failed:       0
Skipped:      3
=============================================================================
VALIDATION PASSED
```

### 보고서 생성

Full validation 실행 시 자동으로 보고서가 생성됩니다:
- 위치: `knowledge_service/docs/results/staging_validation/`
- 형식: `validation_YYYYMMDD_HHMMSS.md`

### 관련 문서

- [Staging Validation Checklist](../../knowledge_service/docs/04_testing/staging_validation_checklist.md)
- [Staging Validation Report Template](../../knowledge_service/docs/04_testing/staging_validation_report_template.md)

---

## deploy.sh - 메인 배포 스크립트

### 기능

- **환경별 배포**: staging, production 환경 지원
- **사전 검증**: 디스크, 메모리, 포트, 환경변수 자동 확인
- **자동 백업**: 배포 전 자동 백업 생성
- **헬스체크**: 배포 후 서비스 상태 자동 확인
- **자동 롤백**: 실패 시 자동 롤백 (production)
- **Slack 알림**: 배포 시작/완료/실패 알림

### 사용법

```bash
# Staging 환경 배포 (기본)
./deploy.sh staging

# Production 환경 배포
./deploy.sh production

# Dry-run 모드 (변경 없이 실행 확인)
./deploy.sh staging --dry-run

# 백업 건너뛰기
./deploy.sh staging --skip-backup

# 테스트 건너뛰기
./deploy.sh staging --skip-tests

# 사전 검증 실패 무시 (주의)
./deploy.sh staging --force

# 도움말
./deploy.sh --help
```

### 배포 단계

```
[1/8] Pre-deployment checks     - 시스템 요구사항 검증
[2/8] Creating backup           - 롤백용 백업 생성
[3/8] Updating codebase         - Git pull (develop/main)
[4/8] Pulling Docker images     - 최신 이미지 다운로드
[5/8] Deploying containers      - Docker Compose up
[6/8] Waiting for health        - 서비스 기동 대기
[7/8] Running health checks     - 헬스체크 실행
[8/8] Post-deployment verify    - 배포 완료 검증
```

### 옵션

| 옵션 | 설명 |
|------|------|
| `--dry-run` | 실제 변경 없이 실행 예상 결과 확인 |
| `--skip-backup` | 배포 전 백업 건너뛰기 |
| `--skip-tests` | 배포 후 검증 테스트 건너뛰기 |
| `--force` | 사전 검증 실패 무시하고 진행 |

---

## pre-deploy-check.sh - 사전 검증 스크립트

### 기능

- **시스템 리소스 검증**: 디스크 공간, 메모리, CPU
- **Docker 환경 검증**: Docker/Compose 설치, 볼륨 상태
- **포트 가용성 검증**: 필수 포트 사용 중 여부
- **환경 설정 검증**: .env 파일, 필수 변수
- **Git 상태 검증**: 브랜치, 커밋 상태
- **기존 컨테이너 상태**: 실행 중인 컨테이너 확인

### 사용법

```bash
# Staging 환경 검증
./pre-deploy-check.sh staging

# Production 환경 검증
./pre-deploy-check.sh production

# 도움말
./pre-deploy-check.sh --help
```

### 검증 항목

| 카테고리 | 검증 항목 | 기본값 |
|----------|----------|--------|
| 디스크 | 최소 여유 공간 | 20GB |
| 메모리 | 최소 총 메모리 | 8GB |
| CPU | 최소 코어 수 | 2 |
| 포트 | 필수 포트 (80, 443, 8080, 8081, 8000, 5432, 9200, 등) | - |
| 환경변수 | DB_PASSWORD, JWT_SECRET, DEEPSEEK_API_KEY, 등 | - |

### 종료 코드

| 코드 | 의미 |
|------|------|
| 0 | 모든 검증 통과 (경고 포함 가능) |
| 1 | 심각한 오류 발견 - 배포 불가 |

---

## post-deploy-verify.sh - 배포 후 검증 스크립트

### 기능

- **컨테이너 상태 확인**: 실행 상태, 헬스체크 상태
- **서비스 헬스체크**: Backend, AI Service, Gateway, Frontend
- **데이터베이스 연결**: PostgreSQL, Elasticsearch, Neo4j, Redis
- **모니터링 서비스**: Prometheus, Grafana
- **로그 에러 분석**: 최근 로그에서 에러 검출
- **리소스 사용량**: CPU, 메모리 사용량

### 사용법

```bash
# Staging 환경 검증
./post-deploy-verify.sh staging

# Production 환경 검증
./post-deploy-verify.sh production

# 도움말
./post-deploy-verify.sh --help
```

### 검증 항목

```
=== Container Status ===
- 컨테이너 실행 상태
- 헬스체크 상태 (healthy/unhealthy)

=== Application Services ===
- Backend: http://localhost:8081/actuator/health
- AI Service: http://localhost:8000/api/v1/health
- API Gateway: http://localhost:8080/actuator/health
- Frontend: http://localhost:80/

=== Data Services ===
- PostgreSQL: pg_isready
- Elasticsearch: /_cluster/health
- Neo4j: http://localhost:7474
- Redis: redis-cli ping
- Keycloak: /health/ready

=== Monitoring Services ===
- Prometheus: /-/healthy
- Grafana: /api/health

=== Log Analysis ===
- 최근 100줄에서 error/exception 검출

=== Resource Usage ===
- 컨테이너별 CPU/메모리 사용량
```

---

## blue-green-deploy.sh - Blue-Green 무중단 배포

### 개념

Blue-Green 배포는 두 개의 동일한 환경(Blue, Green)을 유지하면서 트래픽을 전환하는 무중단 배포 전략입니다.

```
                    +------------------+
                    |   Load Balancer  |
                    +--------+---------+
                             |
              +--------------+--------------+
              |                             |
       +------v------+               +------v------+
       |    Blue     |               |    Green    |
       |  (Active)   |               |  (Standby)  |
       +-------------+               +-------------+
```

### 사용법

```bash
# 현재 상태 확인
./blue-green-deploy.sh status

# 새 버전을 비활성 환경에 배포
./blue-green-deploy.sh deploy --version v1.2.0

# 트래픽 전환 (Blue <-> Green)
./blue-green-deploy.sh switch

# 롤백 (이전 환경으로 전환)
./blue-green-deploy.sh rollback

# 비활성 환경 정리
./blue-green-deploy.sh cleanup
```

### 배포 순서

1. **deploy**: 새 버전을 비활성 환경에 배포
2. **status**: 양쪽 환경 상태 확인
3. **switch**: 트래픽을 새 환경으로 전환
4. **cleanup**: (선택) 이전 환경 정리

### 장점

- **무중단 배포**: 서비스 중단 없이 배포
- **빠른 롤백**: 문제 시 즉시 이전 환경으로 전환
- **안전한 테스트**: 새 환경을 먼저 검증 후 전환

---

## validate-secrets.sh - 시크릿 검증 스크립트

### 기능

- **시크릿 존재 검증**: 필수 시크릿이 설정되어 있는지 확인
- **강도 검증**: 시크릿이 최소 길이 요구사항을 충족하는지 확인
- **플레이스홀더 감지**: `__*__`, `changeme` 등 플레이스홀더 값 감지
- **환경별 검증**: development, staging, production 환경별 다른 요구사항 적용
- **시크릿 생성**: 새로운 시크릿 자동 생성 기능

### 사용법

```bash
# 개발 환경 시크릿 검증
./validate-secrets.sh development

# 스테이징 환경 검증 (상세 출력)
./validate-secrets.sh staging --verbose

# 프로덕션 환경 검증 (CI/CD 모드)
./validate-secrets.sh production --ci-mode

# 프로덕션용 시크릿 생성
./validate-secrets.sh --generate production

# 도움말
./validate-secrets.sh --help
```

### 환경별 요구사항

| 시크릿 | Development | Staging | Production |
|--------|-------------|---------|------------|
| DB_PASSWORD | 8 chars | 8 chars | **32 chars** |
| JWT_SECRET | 32 chars | 32 chars | **64 chars** |
| NEO4J_PASSWORD | 8 chars | 8 chars | **16 chars** |
| KEYCLOAK_ADMIN_PASSWORD | 8 chars | 8 chars | **32 chars** |

---

## rollback.sh - 롤백 스크립트

### 기능

- **애플리케이션 롤백**: 컨테이너 이미지를 이전 버전으로 복원
- **데이터베이스 롤백**: 백업 시점으로 데이터 복원
- **자동 롤백**: 헬스체크 실패 시 자동으로 이전 버전 복원
- **모니터링**: 배포 후 지속적인 상태 확인

### 사용법

```bash
# 애플리케이션 롤백 (가장 일반적)
./rollback.sh app v1.2.0 "버그 발견으로 인한 롤백"

# 데이터베이스 롤백 (주의: 데이터 손실 가능)
./rollback.sh db 2026-02-03 postgresql

# 모든 데이터베이스 롤백
./rollback.sh db 2026-02-03 all

# 배포 후 자동 롤백 모니터링 (5분간)
./rollback.sh monitor v1.2.0 300

# 현재 상태 확인
./rollback.sh verify

# 사용 가능한 버전/백업 목록
./rollback.sh list

# 도움말
./rollback.sh --help
```

### 자동 롤백 설정

| 환경 변수 | 기본값 | 설명 |
|----------|--------|------|
| `AUTO_ROLLBACK_ERROR_THRESHOLD` | 5 | 에러율 임계값 (%) |
| `AUTO_ROLLBACK_HEALTH_FAILURES` | 3 | 연속 헬스체크 실패 횟수 |
| `HEALTH_CHECK_INTERVAL` | 10 | 헬스체크 간격 (초) |
| `HEALTH_CHECK_RETRIES` | 30 | 최대 재시도 횟수 |

---

## backup.sh - 자동 백업 스크립트

### 기능

- **PostgreSQL**: `pg_dump`를 사용한 SQL 백업 (gzip 압축)
- **Elasticsearch**: Snapshot API를 사용한 스냅샷 생성
- **Neo4j**: APOC 확장을 사용한 Cypher/JSON 내보내기
- **MinIO**: mc (MinIO Client)를 사용한 버킷 미러링

### 사용법

```bash
# 전체 백업 실행
./backup.sh

# 특정 서비스만 백업
./backup.sh --postgresql
./backup.sh --elasticsearch
./backup.sh --neo4j
./backup.sh --minio

# 사용자 정의 백업 디렉토리 및 보존 기간
./backup.sh -d /data/backups -r 14

# 도움말
./backup.sh --help
```

### 백업 파일 위치

```
backups/
  YYYY-MM-DD/
    backup_YYYYMMDD_HHMMSS.log       # 백업 로그
    postgresql_YYYYMMDD_HHMMSS.sql.gz  # PostgreSQL 백업
    elasticsearch/
      indices_list.txt               # 인덱스 목록
      all_mappings.json              # 매핑 정보
      snapshot_info.json             # 스냅샷 정보
    neo4j_YYYYMMDD_HHMMSS.tar.gz     # Neo4j 백업
    minio_YYYYMMDD_HHMMSS.tar.gz     # MinIO 백업
```

---

## restore.sh - 복원 스크립트

### 사용법

```bash
# PostgreSQL 복원
./restore.sh postgresql ./backups/2026-01-22/postgresql_20260122_020000.sql.gz

# Elasticsearch 복원 (스냅샷 이름 지정)
./restore.sh elasticsearch snapshot_20260122_020000

# Neo4j 복원
./restore.sh neo4j ./backups/2026-01-22/neo4j_20260122_020000.tar.gz

# MinIO 복원
./restore.sh minio ./backups/2026-01-22/minio_20260122_020000.tar.gz

# 도움말
./restore.sh --help
```

---

## Cron 설정

### 설치 방법

```bash
# 방법 1: crontab 직접 편집
crontab -e
# 아래 내용 추가:
0 2 * * * /opt/knowledge-platform/infrastructure/scripts/backup.sh >> /var/log/knowledge-backup.log 2>&1

# 방법 2: cron.d에 파일 복사
sudo cp backup.cron.example /etc/cron.d/knowledge-platform-backup
sudo chmod 644 /etc/cron.d/knowledge-platform-backup
```

### 권장 스케줄

| 작업 | 스케줄 | 설명 |
|------|--------|------|
| 일일 전체 백업 | `0 2 * * *` | 매일 새벽 2시 |
| 주간 추가 백업 | `0 3 * * 0` | 일요일 새벽 3시 |
| 로그 정리 | `0 4 1 * *` | 매월 1일 새벽 4시 |

---

## 긴급 복구 절차

### Quick Reference

```
+----------------------------------------------------------+
|           OPERATIONS QUICK REFERENCE                      |
+----------------------------------------------------------+
| PERFORMANCE TEST (BEFORE PRODUCTION):                     |
|   ./performance-test.sh --quick                           |
|   ./performance-test.sh --full                            |
|                                                           |
| STAGING VALIDATION (BEFORE PRODUCTION):                   |
|   ./staging-validation.sh --full                          |
|   ./staging-validation.sh --smoke                         |
|                                                           |
| DEPLOY STAGING:                                           |
|   ./deploy.sh staging                                     |
|                                                           |
| DEPLOY PRODUCTION:                                        |
|   ./deploy.sh production                                  |
|                                                           |
| PRE-DEPLOY CHECK:                                         |
|   ./pre-deploy-check.sh production                        |
|                                                           |
| POST-DEPLOY VERIFY:                                       |
|   ./post-deploy-verify.sh production                      |
|                                                           |
| BLUE-GREEN DEPLOY:                                        |
|   ./blue-green-deploy.sh deploy --version v1.2.0          |
|   ./blue-green-deploy.sh switch                           |
|                                                           |
| APP ROLLBACK:                                             |
|   ./rollback.sh app v1.2.0 "Reason"                      |
|                                                           |
| DB ROLLBACK:                                              |
|   ./rollback.sh db 2026-02-03 postgresql                 |
|                                                           |
| VERIFY:                                                   |
|   ./rollback.sh verify                                   |
|                                                           |
| VALIDATE SECRETS:                                         |
|   ./validate-secrets.sh production --ci-mode             |
|                                                           |
| GITHUB ACTIONS:                                           |
|   Actions > Deploy to Production > Run workflow           |
|   Actions > Rollback Deployment > Run workflow            |
+----------------------------------------------------------+
```

---

## 문제 해결

### 자주 발생하는 문제

1. **컨테이너를 찾을 수 없음**
   ```
   ERROR: PostgreSQL container 'kp-postgresql' is not running
   ```
   - Docker 컨테이너가 실행 중인지 확인: `docker ps`

2. **비밀번호 미설정**
   ```
   ERROR: DB_PASSWORD environment variable is not set
   ```
   - `.env` 파일에 비밀번호가 설정되어 있는지 확인

3. **포트 충돌**
   ```
   WARN: Port 8080 is already in use
   ```
   - 충돌하는 프로세스 확인: `ss -tuln | grep 8080`

4. **디스크 공간 부족**
   ```
   FAIL: Insufficient disk space: 10GB available (minimum: 20GB)
   ```
   - 불필요한 Docker 이미지 정리: `docker system prune -a`

5. **헬스체크 실패**
   ```
   FAIL: Backend: Not responding (HTTP 000)
   ```
   - 컨테이너 로그 확인: `docker logs kp-backend`
   - 포트 바인딩 확인: `docker port kp-backend`

6. **k6 설치되지 않음**
   ```
   ERROR: k6 is not installed
   ```
   - k6 설치: `brew install k6` (macOS) 또는 `apt install k6` (Ubuntu)

### 로그 확인

```bash
# 배포 로그 확인
tail -100 /path/to/project/logs/deployments/deploy_staging_*.log

# 롤백 로그 확인
tail -100 /path/to/project/logs/rollbacks/rollback_*.log

# Blue-Green 로그 확인
tail -100 /path/to/project/logs/blue-green/blue-green_*.log

# Staging Validation 보고서 확인
ls -la knowledge_service/docs/results/staging_validation/

# Performance Test 결과 확인
ls -la knowledge_service/docs/results/performance/

# 컨테이너 로그 확인
docker logs --tail 100 kp-backend
docker logs --tail 100 kp-ai-service
```

---

## 참고

- [Performance Baseline Report](../../knowledge_service/docs/04_testing/performance_baseline_report.md)
- [Performance Testing Suite](../performance/README.md)
- [Staging Validation Checklist](../../knowledge_service/docs/04_testing/staging_validation_checklist.md)
- [Staging Validation Report Template](../../knowledge_service/docs/04_testing/staging_validation_report_template.md)
- [배포 계획](../../knowledge_service/docs/06_deployment/deployment_plan.md)
- [롤백 절차 가이드](../../knowledge_service/docs/06_deployment/rollback_procedure.md)
- [시크릿 관리 가이드](../../knowledge_service/docs/06_deployment/secrets_management_guide.md)
- [GitHub Actions 시크릿 가이드](../../knowledge_service/docs/06_deployment/github_actions_secrets_guide.md)
- [인프라 상세 설계서](../../knowledge_service/docs/02_design/infrastructure_detailed_design.md)
- [Docker Compose 설정](../docker/docker-compose.yml)
