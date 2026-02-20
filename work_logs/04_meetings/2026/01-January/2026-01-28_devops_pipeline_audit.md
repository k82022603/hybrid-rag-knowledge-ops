# CI/CD Pipeline & Build/Deploy 전수 점검 결과

**날짜**: 2026-01-28
**담당**: DevOps Engineer
**범위**: Sprint 03 완료 시점 CI/CD 파이프라인, Docker 설정, Observability 전체 점검

---

## 1. 종합 배포 준비도

| 환경 | 준비도 | 점수 |
|------|:------:|:----:|
| Development | READY | 8/10 |
| Staging | PARTIALLY READY | 5/10 |
| Production | NOT READY | 3/10 |

**종합 점수: 6.7/10**

---

## 2. GitHub Actions 워크플로우 현황

| 파일 | 트리거 | 용도 | 상태 |
|------|--------|------|:----:|
| `ci.yml` | PR/push to main/develop | Full CI (lint, test, build, security, docker) | GOOD |
| `pr-build.yml` | PR to main/develop | PR 빌드 검증 | GOOD |
| `code-quality.yml` | PR/push to develop | Lint, formatting, static analysis | GOOD |
| `docker-compose-validate.yml` | compose 파일 변경 시 | YAML + healthcheck 검증 | GOOD |
| `e2e-test.yml` | PR (frontend 변경) | Playwright E2E | GOOD |
| `docker-build.yml` | push to main/develop, tags | Docker 이미지 빌드 + push | GOOD |
| `cd.yml` | push to main, tags, manual | Staging/Production 배포 | GOOD |

---

## 3. 발견된 이슈 (우선순위별)

### HIGH (5건)

| ID | 파일 | 이슈 | 영향 |
|----|------|------|------|
| DF-02 | AI Service | 프로덕션 Dockerfile 부재 (`knowledge_service/Dockerfile` 없음) | 프로덕션 배포 불가 |
| CD-02/03 | `cd.yml` | Health check 검증 주석 처리 (staging + production) | 배포 검증 불가 |
| CD-05 | `cd.yml` | `docker-compose.prod.yml` 참조하나 파일 미존재 | 프로덕션 배포 실패 |
| ENV-01 | `infrastructure/docker/.env` | 개발 크리덴셜이 git에 추적됨 | 보안 위험 |
| DF-01 | `infrastructure/docker/backend/Dockerfile` | JWT Secret, 평문 비밀번호 하드코딩 (스텁) | 스텁이 프로덕션에 사용될 위험 |

### MEDIUM (6건)

| ID | 이슈 |
|----|------|
| DF-04/05 | JDK 버전 불일치: Dockerfile JDK 17 vs CI Java 21 |
| CI-01/02/03 | 품질 체크에서 `|| true`로 에러 무시 |
| CI-06 | code-quality.yml의 `continue-on-error: true` |
| CD-01 | `sleep 30` 대신 active health polling 필요 |
| CD-04 | 롤백 Job 로직 트리거 조건 불확실 |
| ENV-02 | `.gitignore`가 `infrastructure/docker/.env` 미커버 |

### LOW (5건)

| ID | 이슈 |
|----|------|
| CI-05 | `pr-build.yml`과 `ci.yml` 중복 |
| DF-06 | `.dockerignore` 파일 누락 |
| DF-03 | Frontend 프로덕션 Dockerfile이 root로 실행 |
| CD-06 | Canary/Blue-green 배포 전략 없음 |
| HC-01~06 | 일부 서비스 healthcheck에서 `localhost` 사용 (BusyBox 호환성) |

---

## 4. 강점

- **Change Detection**: `dorny/paths-filter@v3`로 변경된 컴포넌트만 빌드
- **Concurrency Control**: `cancel-in-progress: true`로 중복 실행 방지
- **빌드 캐시**: 4개 스택(Java, Python, Node, Docker) 모두 적절한 캐싱
- **Observability 3대 축**: Metrics(Prometheus), Logs(Loki), Traces(Jaeger) 완비
- **4개 Grafana 데이터소스 자동 프로비저닝**
- **Alert Rules 10개 정의** (단, Alertmanager 미구성)
- **WSL2 호환**: 전용 override 파일 + 자동 감지 스크립트

---

## 5. 서비스 Health Check 현황

| 서비스 | Health Check | Interval | Start Period |
|--------|-------------|:--------:|:------------:|
| nginx | `nginx -t` | 30s | - |
| frontend | `wget .../` | 30s | 30s |
| api-gateway | `wget .../` | 30s | 60s |
| backend | `wget .../actuator/health` | 30s | 90s |
| ai-service | `wget .../health` | 30s | 120s |
| keycloak | TCP 8080 | 30s | 90s |
| postgresql | `pg_isready` | 10s | - |
| neo4j | `wget .../7474` | 30s | 60s |
| elasticsearch | `curl .../_cluster/health` | 30s | 60s |
| redis | `redis-cli ping` | 10s | - |

18개 서비스 전체 health check 구성 양호.

---

## 6. 개선 액션 아이템

### P0 (Sprint 04 시작 전)

1. `.env` 파일 git 추적 해제 + `.gitignore` 보강
2. Backend 스텁 JWT Secret/비밀번호 환경변수화

### P1 (Sprint 04 중)

3. PR 워크플로우 중복 해소
4. docker-build.yml에서 main 트리거 제거
5. JDK 버전 통일 (17 또는 21)
6. CD 파이프라인 롤백 자동화
7. 배포 후 health check 활성화

### P2 (Sprint 04-05)

8. `docker-compose.prod.yml` 생성
9. Stub → Production Dockerfile 전환 계획
10. Alertmanager 컨테이너 추가
11. AI Service Production Dockerfile 작성
12. 테스트 커버리지 임계값 설정

---

*작성: DevOps Engineer Agent | 2026-01-28*
