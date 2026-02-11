# GitHub Actions CI/CD 가이드

**프로젝트**: Hybrid RAG Knowledge Operations Platform
**버전**: 2.0
**작성일**: 2026-01-22
**최종 수정일**: 2026-01-26
**작성자**: DevOps Agent

---

## 목차

1. [개요](#1-개요) (현재 운영 현황 포함)
2. [아키텍처](#2-아키텍처)
3. [워크플로우 구성](#3-워크플로우-구성)
4. [CI Pipeline (ci.yml)](#4-ci-pipeline-ciyml)
5. [CD Pipeline (cd.yml)](#5-cd-pipeline-cdyml)
6. [PR Build (pr-build.yml)](#6-pr-build-pr-buildyml)
7. [Docker Build (docker-build.yml)](#7-docker-build-docker-buildyml)
8. [Code Quality (code-quality.yml)](#8-code-quality-code-qualityyml)
9. [Branch Protection Rules](#9-branch-protection-rules)
10. [Docker Compose Validate (docker-compose-validate.yml)](#10-docker-compose-validate-docker-compose-validateyml) **(NEW)**
11. [E2E Tests (e2e-test.yml)](#11-e2e-tests-e2e-testyml) **(NEW)**
12. [환경 변수 및 Secrets](#12-환경-변수-및-secrets)
13. [사용 가이드](#13-사용-가이드)
14. [트러블슈팅](#14-트러블슈팅) (실제 장애 사례 포함)
15. [베스트 프랙티스](#15-베스트-프랙티스)

---

## 1. 개요

### 1.1 CI/CD 파이프라인 목적

| 파이프라인 | 목적 | 파일 |
|------------|------|------|
| **CI Pipeline** | PR 검증, 코드 품질 보장 | `.github/workflows/ci.yml` |
| **CD Pipeline** | Docker 이미지 빌드 및 배포 | `.github/workflows/cd.yml` |
| **PR Build** | PR 시 빌드 및 테스트 검증 | `.github/workflows/pr-build.yml` |
| **Docker Build** | Docker 이미지 빌드 (amd64) | `.github/workflows/docker-build.yml` |
| **Code Quality** | 린트, 포맷, 정적 분석 | `.github/workflows/code-quality.yml` |
| **Docker Compose Validate** | Docker Compose 구문/설정 검증 | `.github/workflows/docker-compose-validate.yml` |
| **E2E Tests** | Playwright E2E 테스트 | `.github/workflows/e2e-test.yml` |
| **Dependabot Updates** | 자동 의존성 업데이트 | `.github/dependabot.yml` (GitHub 자동 관리) |

### 1.2 지원 서비스

| 서비스 | 기술 스택 | 디렉토리 |
|--------|----------|----------|
| **Backend** | Spring Boot 3.x, Java 21 | `knowledge_service/backend/` |
| **Gateway** | Spring Cloud Gateway | `knowledge_service/gateway/` |
| **Frontend** | React 18, TypeScript | `knowledge_service/frontend/` |
| **AI Service** | FastAPI, Python 3.11 | `knowledge_service/src/` |

### 1.3 현재 운영 현황

> **최종 확인일**: 2026-01-26

| 워크플로우 | 현재 상태 | 비고 | 마지막 확인 |
|-----------|----------|------|------------|
| CI Pipeline | 정상 (PR/develop 트리거) | - | 2026-01-26 |
| CD Pipeline | Build 성공 / Deploy 미설정 | SSH 시크릿 미설정 | 2026-01-26 |
| PR Build | 정상 | - | 2026-01-26 |
| Docker Build | 정상 (amd64) | arm64 제외 | 2026-01-26 |
| Code Quality | 정상 | - | 2026-01-26 |
| Docker Compose Validate | 정상 | - | 2026-01-26 |
| E2E Tests | 정상 (PR/수동) | Playwright Chromium | 2026-01-26 |
| Dependabot Updates | 정상 | GitHub 자동 관리 | 2026-01-26 |

#### CD Pipeline 배포를 위한 필수 GitHub Secrets

| 환경 | 필요 Secrets | 상태 |
|------|-------------|------|
| **Staging** | `STAGING_HOST`, `STAGING_USER`, `STAGING_SSH_KEY` | 미설정 |
| **Production** | `PRODUCTION_HOST`, `PRODUCTION_USER`, `PRODUCTION_SSH_KEY` | 미설정 |
| **알림 (선택)** | `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ALERTS` | 미설정 |

### 1.4 전체 흐름

```mermaid
flowchart LR
    subgraph Developer["개발자"]
        Code["코드 작성"]
    end

    subgraph GitHub["GitHub"]
        PR["Pull Request"]
        Main["main 브랜치"]
        Tag["Release Tag"]
    end

    subgraph CI["CI Pipeline"]
        Lint["Lint"]
        Test["Test"]
        Build["Build"]
        Scan["Security Scan"]
    end

    subgraph CD["CD Pipeline"]
        DockerBuild["Docker Build"]
        Push["Push to GHCR"]
        DeployStaging["Deploy Staging"]
        DeployProd["Deploy Production"]
    end

    Code --> PR
    PR --> CI
    CI -->|Pass| Main
    Main --> CD
    Tag --> CD

    Lint --> Test --> Build --> Scan
    DockerBuild --> Push --> DeployStaging --> DeployProd
```

---

## 2. 아키텍처

### 2.1 CI/CD 전체 아키텍처

```mermaid
flowchart TB
    subgraph Triggers["트리거"]
        PR["PR to main/develop"]
        Push["Push to main"]
        TagPush["Tag Push (v*)"]
        Manual["Manual Dispatch"]
    end

    subgraph CI_Pipeline["CI Pipeline"]
        direction TB
        Changes["변경 파일 감지"]

        subgraph Tests["병렬 테스트"]
            BackendTest["Backend Tests<br/>Java 21, Gradle"]
            GatewayTest["Gateway Tests<br/>Java 21, Gradle"]
            FrontendTest["Frontend Tests<br/>Node 20, npm"]
            AITest["AI Service Tests<br/>Python 3.11, Poetry"]
        end

        Security["Security Scan<br/>Trivy"]
        DockerTest["Docker Build Test"]
        Summary["CI Summary"]

        Changes --> Tests
        Tests --> Security
        Tests --> DockerTest
        Security --> Summary
        DockerTest --> Summary
    end

    subgraph CD_Pipeline["CD Pipeline"]
        direction TB
        BuildPush["Build & Push<br/>to GHCR"]

        subgraph Environments["배포 환경"]
            Staging["Staging<br/>자동 배포"]
            Production["Production<br/>승인 필요"]
        end

        Rollback["Rollback<br/>수동"]

        BuildPush --> Staging
        Staging --> Production
        Production -.-> Rollback
    end

    PR --> CI_Pipeline
    Push --> CD_Pipeline
    TagPush --> CD_Pipeline
    Manual --> CD_Pipeline

    CI_Pipeline -->|Pass| Push
```

### 2.2 변경 감지 기반 선택적 실행

CI 파이프라인은 **변경된 파일에 따라 필요한 Job만 실행**합니다:

```mermaid
flowchart LR
    subgraph Changes["변경 파일"]
        Backend["backend/**"]
        Gateway["gateway/**"]
        Frontend["frontend/**"]
        AI["src/** / pyproject.toml"]
        Infra["infrastructure/**"]
    end

    subgraph Jobs["실행 Job"]
        BackendJob["backend-test"]
        GatewayJob["gateway-test"]
        FrontendJob["frontend-test"]
        AIJob["ai-service-test"]
        DockerJob["docker-build-test"]
    end

    Backend --> BackendJob
    Backend --> GatewayJob
    Gateway --> GatewayJob
    Frontend --> FrontendJob
    AI --> AIJob

    Backend --> DockerJob
    Gateway --> DockerJob
    Frontend --> DockerJob
    AI --> DockerJob
```

---

## 3. 워크플로우 구성

### 3.1 워크플로우 파일 목록

```
.github/workflows/
  - ci.yml                        # 통합 CI 파이프라인
  - cd.yml                        # 배포 파이프라인
  - pr-build.yml                  # PR 빌드 전용
  - docker-build.yml              # Docker 빌드 전용
  - code-quality.yml              # 코드 품질 전용
  - docker-compose-validate.yml   # Docker Compose 검증 (NEW)
  - e2e-test.yml                  # E2E 테스트 (NEW)

.github/
  - dependabot.yml                # 의존성 자동 업데이트 (GitHub 관리)
```

### 3.2 워크플로우별 역할

| 워크플로우 | 트리거 | 주요 역할 |
|------------|--------|----------|
| `ci.yml` | PR, push to develop | 종합 CI (린트, 테스트, 보안 스캔) |
| `cd.yml` | push to main, tags | 배포 (Staging, Production) |
| `pr-build.yml` | PR only | PR 빌드 및 테스트 검증 |
| `docker-build.yml` | push, PR, manual | Docker 이미지 빌드 (amd64) |
| `code-quality.yml` | PR, push to develop | 코드 품질 체크만 |
| `docker-compose-validate.yml` | push, PR (docker-compose 변경) | Docker Compose 구문/설정 검증 |
| `e2e-test.yml` | PR (frontend 변경), manual | Playwright E2E 테스트 |
| `dependabot.yml` | GitHub 자동 스케줄 | 의존성 자동 업데이트 |

---

## 4. CI Pipeline (ci.yml)

### 4.1 트리거 조건

| 이벤트 | 브랜치 | 조건 |
|--------|--------|------|
| `pull_request` | main, develop | opened, synchronize, reopened |
| `push` | develop | - |

### 4.2 Job 구성

```mermaid
flowchart TB
    subgraph Changes["changes"]
        Filter["Path Filter<br/>dorny/paths-filter@v3"]
    end

    subgraph Backend["backend-test"]
        JavaSetup1["Setup Java 21"]
        Checkstyle["Checkstyle"]
        BackendUnit["Unit Tests"]
        BackendBuild["Build JAR"]
    end

    subgraph Gateway["gateway-test"]
        JavaSetup2["Setup Java 21"]
        GatewayUnit["Unit Tests"]
        GatewayBuild["Build JAR"]
    end

    subgraph Frontend["frontend-test"]
        NodeSetup["Setup Node 20"]
        ESLint["ESLint"]
        TypeCheck["TypeScript Check"]
        FrontendUnit["Unit Tests"]
        FrontendBuild["Build"]
    end

    subgraph AIService["ai-service-test"]
        PythonSetup["Setup Python 3.11"]
        Ruff["Ruff Lint"]
        Mypy["Mypy Type Check"]
        Pytest["Pytest + Coverage"]
    end

    subgraph Security["security-scan"]
        Trivy["Trivy Scanner"]
        SARIF["Upload SARIF"]
    end

    subgraph Docker["docker-build-test"]
        Buildx["Docker Buildx"]
        BuildNoPublish["Build (No Push)"]
    end

    subgraph Summary["ci-summary"]
        Results["결과 집계"]
        Fail["실패 시 Exit 1"]
    end

    Changes --> Backend
    Changes --> Gateway
    Changes --> Frontend
    Changes --> AIService
    Changes --> Docker

    Backend --> Summary
    Gateway --> Summary
    Frontend --> Summary
    AIService --> Summary
    Security --> Summary
    Docker --> Summary
```

### 4.3 각 서비스별 테스트 상세

#### Backend (Spring Boot)

| 단계 | 명령어 | 설명 |
|------|--------|------|
| Lint | `./gradlew checkstyleMain checkstyleTest` | Checkstyle 검사 |
| Test | `./gradlew test` | JUnit 5 테스트 |
| Build | `./gradlew build -x test` | JAR 빌드 |
| Report | JaCoCo | 커버리지 리포트 |

#### Frontend (React)

| 단계 | 명령어 | 설명 |
|------|--------|------|
| Install | `npm ci` | 의존성 설치 |
| Lint | `npm run lint` | ESLint 검사 |
| Type Check | `npm run type-check` | TypeScript 검사 |
| Test | `npm test -- --coverage` | Jest 테스트 |
| Build | `npm run build` | 프로덕션 빌드 |

#### AI Service (FastAPI)

| 단계 | 명령어 | 설명 |
|------|--------|------|
| Lint | `poetry run ruff check` | Ruff 린트 |
| Format | `poetry run ruff format --check` | 포맷 검사 |
| Type | `poetry run mypy src/` | 타입 검사 |
| Test | `poetry run pytest --cov` | pytest + 커버리지 |

### 4.4 보안 스캔

**Trivy** 취약점 스캐너를 사용하여 의존성 취약점을 검사합니다:

```yaml
- name: Run Trivy vulnerability scanner
  uses: aquasecurity/trivy-action@master
  with:
    scan-type: 'fs'
    severity: 'CRITICAL,HIGH'
    format: 'sarif'
```

결과는 GitHub Security 탭에서 확인할 수 있습니다.

---

## 5. CD Pipeline (cd.yml)

### 5.1 트리거 조건

| 이벤트 | 조건 | 결과 |
|--------|------|------|
| `push` to main | - | Staging 자동 배포 |
| `push` tag `v*` | - | Staging + Production 배포 |
| `workflow_dispatch` | environment 선택 | 수동 배포 |

### 5.2 배포 흐름

> **v2.0 변경사항**:
> - 빌드 플랫폼이 `linux/amd64`로 변경 (arm64 제외, `eclipse-temurin:17-jre-alpine` 미지원)
> - matrix job의 미사용 `outputs` 섹션 및 동적 step ID 제거 (워크플로우 시작 실패 해결)
> - 현재 상태: Build 4건 성공, Deploy to Staging은 SSH 시크릿 미설정으로 실패 (예상된 동작)

```mermaid
flowchart TB
    subgraph Trigger["트리거"]
        MainPush["Push to main"]
        TagPush["Push tag v*"]
        Manual["Manual Dispatch"]
    end

    subgraph Build["Build & Push"]
        Checkout["Checkout"]
        QEMU["Setup QEMU"]
        Buildx["Setup Buildx"]
        Login["Login to GHCR"]
        Meta["Extract Metadata"]
        BuildPush["Build & Push<br/>linux/amd64"]
    end

    subgraph Staging["Staging 배포"]
        StagingSSH["SSH 접속"]
        StagingPull["docker compose pull"]
        StagingUp["docker compose up -d"]
        StagingVerify["Health Check"]
        StagingNotify["Slack 알림"]
    end

    subgraph Production["Production 배포"]
        Approval["승인 대기"]
        Backup["DB 백업"]
        ProdSSH["SSH 접속"]
        ProdPull["docker compose pull"]
        ProdUp["docker compose up -d"]
        ProdVerify["Health Check"]
        ProdNotify["Slack 알림"]
    end

    subgraph Rollback["롤백"]
        RollbackNotify["롤백 필요 알림"]
    end

    MainPush --> Build
    TagPush --> Build
    Manual --> Build

    Build --> Staging
    Staging --> Production

    Staging -.->|실패| Rollback
    Production -.->|실패| Rollback

    Checkout --> QEMU --> Buildx --> Login --> Meta --> BuildPush
    Approval --> Backup --> ProdSSH --> ProdPull --> ProdUp --> ProdVerify --> ProdNotify
```

### 5.3 Docker 이미지 태깅

Docker Metadata Action을 사용한 자동 태깅:

| 태그 패턴 | 예시 | 조건 |
|-----------|------|------|
| `branch` | `main` | 브랜치 푸시 시 |
| `pr-{number}` | `pr-123` | PR 생성 시 |
| `{version}` | `v1.0.0` | 태그 푸시 시 |
| `{major}.{minor}` | `1.0` | 태그 푸시 시 |
| `sha-{7chars}` | `sha-abc1234` | 항상 |
| `latest` | `latest` | main 브랜치 시 |

### 5.4 배포 환경

| 환경 | 트리거 | 승인 | URL (예시) |
|------|--------|------|------------|
| **Staging** | main 푸시 | 자동 | https://staging.knowledge.example.com |
| **Production** | 태그 또는 수동 | 수동 승인 필요 | https://knowledge.example.com |

### 5.5 롤백 전략

Production 배포 전 자동 백업:

```bash
# 배포 전 DB 백업
docker compose exec -T postgresql pg_dumpall -U knowledge > /backup/pre-deploy-$(date +%Y%m%d_%H%M%S).sql
```

---

## 6. PR Build (pr-build.yml)

### 6.1 개요

PR 빌드 전용 워크플로우로, PR 생성/업데이트 시 빌드 및 테스트를 검증합니다.

### 6.2 트리거

```yaml
on:
  pull_request:
    branches: [main, develop]
    types: [opened, synchronize, reopened]
```

### 6.3 Job 구성

| Job | 조건 | 작업 내용 |
|-----|------|----------|
| `changes` | 항상 | 변경 파일 감지 |
| `python-build` | Python 파일 변경 시 | Poetry 빌드, pytest 실행 |
| `java-build` | Java 파일 변경 시 | Gradle 빌드, 테스트 실행 |
| `typescript-build` | TypeScript 파일 변경 시 | npm 빌드, Vitest 실행 |
| `pr-summary` | 항상 | 결과 요약 |

### 6.4 출력

- `python-test-results` - Python 테스트 결과 및 커버리지
- `gateway-test-results` - Gateway 테스트 결과
- `backend-test-results` - Backend 테스트 결과
- `frontend-build` - Frontend 빌드 산출물
- `frontend-coverage` - Frontend 테스트 커버리지

---

## 7. Docker Build (docker-build.yml)

### 7.1 개요

Docker 이미지 빌드 전용 워크플로우입니다.

> **v2.0 변경**: 기본 빌드 플랫폼이 `linux/amd64`로 변경되었습니다.
> Backend/Gateway의 런타임 이미지 `eclipse-temurin:17-jre-alpine`이 arm64 매니페스트를 제공하지 않아
> 멀티 아키텍처 빌드(`linux/amd64,linux/arm64`)가 실패합니다.
> arm64 지원이 필요한 경우 Dockerfile의 런타임 이미지를 `eclipse-temurin:17-jre` (Ubuntu 기반)로 교체해야 합니다.

### 7.2 트리거

```yaml
on:
  push:
    branches: [main, develop]
    tags: ['v*']
    paths:
      - 'knowledge_service/**'
      - 'infrastructure/docker/**'
  pull_request:
    branches: [main]
    paths:
      - 'knowledge_service/**'
      - 'infrastructure/docker/**'
  workflow_dispatch:
    inputs:
      push_images:
        description: 'Push images to registry'
        type: boolean
      platform:
        description: 'Build platform'
        type: choice
        options:
          - linux/amd64
          - linux/arm64
```

### 7.3 빌드 대상

| 이미지 | Dockerfile 위치 | 컨텍스트 |
|--------|----------------|----------|
| `ai-service` | `knowledge_service/Dockerfile` 또는 `infrastructure/docker/ai-service/Dockerfile` | `knowledge_service/` |
| `gateway` | `knowledge_service/gateway/Dockerfile` | `knowledge_service/gateway/` |
| `frontend` | `knowledge_service/frontend/Dockerfile` | `knowledge_service/frontend/` |
| `backend` | `knowledge_service/backend/Dockerfile` | `knowledge_service/backend/` |

### 7.4 이미지 푸시 조건

| 조건 | 푸시 여부 |
|------|----------|
| PR | No (빌드만) |
| push to main | Yes |
| push tag v* | Yes |
| manual with push_images=true | Yes |

---

## 8. Code Quality (code-quality.yml)

### 8.1 개요

코드 품질 체크 전용 워크플로우로, 린트, 포맷, 정적 분석을 수행합니다.

### 8.2 트리거

```yaml
on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [develop]
```

### 8.3 Python 품질 체크

| 도구 | 목적 | 명령어 |
|------|------|--------|
| **Black** | 코드 포맷팅 | `poetry run black --check src/` |
| **isort** | import 정렬 | `poetry run isort --check-only src/` |
| **Ruff** | 린트 (flake8 대체) | `poetry run ruff check src/` |
| **flake8** | 린트 (백업) | `poetry run flake8 src/` |
| **mypy** | 타입 체크 | `poetry run mypy src/` |

### 8.4 Java 품질 체크

| 도구 | 목적 | 명령어 |
|------|------|--------|
| **Checkstyle** | 코드 스타일 | `./gradlew checkstyleMain checkstyleTest` |
| **SpotBugs** | 버그 탐지 | `./gradlew spotbugsMain` |
| **Compile Check** | 컴파일 검증 | `./gradlew compileJava` |

### 8.5 TypeScript 품질 체크

| 도구 | 목적 | 명령어 |
|------|------|--------|
| **ESLint** | 린트 | `npm run lint` |
| **Prettier** | 포맷팅 | `npm run format:check` |
| **TypeScript** | 타입 체크 | `npx tsc --noEmit` |

### 8.6 빠른 수정 명령어

#### Python
```bash
cd knowledge_service
poetry run black src/
poetry run isort src/
poetry run ruff check src/ --fix
```

#### TypeScript
```bash
cd knowledge_service/frontend
npm run lint:fix
npm run format
```

---

## 9. Branch Protection Rules

### 9.1 개요

Branch Protection Rules를 설정하면 빌드 실패 시 PR 머지를 차단할 수 있습니다.

### 9.2 설정 방법

1. **Repository Settings** 이동
2. **Branches** 메뉴 선택
3. **Add branch protection rule** 클릭
4. 다음과 같이 설정:

#### main 브랜치 보호 규칙

| 설정 | 값 | 설명 |
|------|-----|------|
| **Branch name pattern** | `main` | 보호할 브랜치 |
| **Require a pull request before merging** | Yes | 직접 푸시 방지 |
| **Require approvals** | 1 | 최소 1명 승인 필요 |
| **Dismiss stale pull request approvals** | Yes | 새 커밋 시 승인 무효화 |
| **Require status checks to pass** | Yes | CI 통과 필수 |
| **Require branches to be up to date** | Yes | 최신 상태 필수 |
| **Status checks that are required** | (아래 참조) | 필수 체크 목록 |

#### 필수 Status Checks

다음 체크를 필수로 설정합니다:

```
- CI Summary (ci.yml의 ci-summary job)
- PR Build Summary (pr-build.yml의 pr-summary job)
- Quality Summary (code-quality.yml의 quality-summary job)
```

또는 개별 Job을 지정:

```
- Backend Tests
- Gateway Tests
- Frontend Tests
- AI Service Tests
- Docker Build Test
- Python Quality
- Java Quality
- TypeScript Quality
```

### 9.3 develop 브랜치 보호 규칙

| 설정 | 값 | 설명 |
|------|-----|------|
| **Branch name pattern** | `develop` | 보호할 브랜치 |
| **Require a pull request before merging** | Yes | 직접 푸시 방지 |
| **Require status checks to pass** | Yes | CI 통과 필수 |
| **Status checks that are required** | CI Summary | 필수 체크 |

### 9.4 설정 스크린샷 가이드

```
Settings > Branches > Add rule

[x] Require a pull request before merging
    [x] Require approvals: 1
    [x] Dismiss stale pull request approvals when new commits are pushed

[x] Require status checks to pass before merging
    [x] Require branches to be up to date before merging

    Search for status checks:
    - [x] CI Summary
    - [x] PR Build Summary
    - [x] Quality Summary

[x] Do not allow bypassing the above settings
```

### 9.5 확인 방법

PR 페이지에서 다음과 같이 표시됩니다:

| 상태 | 표시 | 머지 가능 |
|------|------|----------|
| 모든 체크 통과 | All checks have passed | Yes |
| 일부 체크 실패 | Some checks were not successful | No |
| 체크 진행 중 | Some checks haven't completed yet | No |
| 승인 필요 | Review required | No |

### 9.6 Ruleset (대안)

GitHub의 새로운 Ruleset 기능을 사용할 수도 있습니다:

1. **Settings > Rules > Rulesets** 이동
2. **New ruleset** 클릭
3. 더 세밀한 규칙 설정 가능

---

## 10. Docker Compose Validate (docker-compose-validate.yml)

### 10.1 개요

Docker Compose 설정 파일의 구문, 설정, 호환성을 자동으로 검증하는 워크플로우입니다.
[INC-2026-01-25-001] 장애를 계기로 도입되었습니다.

### 10.2 트리거

```yaml
on:
  push:
    paths:
      - 'infrastructure/docker/docker-compose*.yml'
  pull_request:
    paths:
      - 'infrastructure/docker/docker-compose*.yml'
```

### 10.3 검증 항목

| 검증 항목 | 설명 | 규칙 |
|-----------|------|------|
| YAML 구문 검증 | YAML 파싱 오류 체크 | 표준 YAML 문법 |
| Docker Compose config | `docker compose config` 검증 | 서비스 정의 유효성 |
| Healthcheck 설정 | 호스트명/명령어 검증 | `localhost` 대신 `127.0.0.1` 사용 |
| WSL2 호환성 | 보안 설정 호환성 체크 | WSL2 환경 동작 보장 |

### 10.4 Healthcheck 검증 규칙

| 규칙 | 잘못된 예 | 올바른 예 |
|------|----------|----------|
| 호스트명 | `localhost` | `127.0.0.1` |
| wget 명령 | `wget --spider` | `wget -q -O /dev/null` |

> **배경**: Docker 컨테이너 내부에서 `localhost`가 호스트 머신이 아닌 컨테이너 자신을 가리키므로
> healthcheck에서 `127.0.0.1`을 명시적으로 사용해야 안정적입니다.

---

## 11. E2E Tests (e2e-test.yml)

### 11.1 개요

Playwright를 활용한 E2E(End-to-End) 테스트 워크플로우입니다.
Frontend 변경이 포함된 PR에서 자동 실행되며, 수동 실행도 지원합니다.

### 11.2 트리거

```yaml
on:
  pull_request:
    branches: [main, develop]
    paths:
      - 'knowledge_service/frontend/**'
  workflow_dispatch:
```

### 11.3 설정

| 항목 | 값 |
|------|-----|
| **Timeout** | 30분 |
| **브라우저** | Chromium만 사용 |
| **Runner** | ubuntu-latest |

### 11.4 Artifacts

| Artifact | 보존 기간 | 조건 |
|----------|----------|------|
| `playwright-report` | 14일 | 항상 업로드 |
| `test-results` | 7일 | 항상 업로드 |
| `screenshots` | 7일 | 테스트 실패 시만 |
| `videos` | 7일 | 테스트 실패 시만 |

### 11.5 로컬 실행

```bash
cd knowledge_service/frontend
npx playwright install chromium
npx playwright test
npx playwright show-report
```

---

## 12. 환경 변수 및 Secrets

### 12.1 필수 Secrets

GitHub Repository Settings → Secrets and variables → Actions에서 설정:

| Secret | 용도 | 필수 |
|--------|------|------|
| `STAGING_HOST` | Staging 서버 호스트 | Staging 배포 시 |
| `STAGING_USER` | Staging SSH 사용자 | Staging 배포 시 |
| `STAGING_SSH_KEY` | Staging SSH 개인키 | Staging 배포 시 |
| `PRODUCTION_HOST` | Production 서버 호스트 | Production 배포 시 |
| `PRODUCTION_USER` | Production SSH 사용자 | Production 배포 시 |
| `PRODUCTION_SSH_KEY` | Production SSH 개인키 | Production 배포 시 |
| `SLACK_BOT_TOKEN` | Slack 알림용 토큰 | 선택 |
| `SLACK_CHANNEL_ALERTS` | Slack 알림 채널 ID | 선택 |

### 12.2 자동 제공 Secrets

| Secret | 설명 |
|--------|------|
| `GITHUB_TOKEN` | GitHub API 접근용 (자동 생성) |

### 12.3 환경 변수

| 변수 | 값 | 용도 |
|------|-----|------|
| `PYTHON_VERSION` | 3.11 | Python 버전 |
| `JAVA_VERSION` | 21 | Java 버전 |
| `NODE_VERSION` | 20 | Node.js 버전 |
| `REGISTRY` | ghcr.io | 컨테이너 레지스트리 |

### 12.4 GitHub Environments 설정

**Repository Settings → Environments**에서 환경별 보호 규칙 설정:

#### Staging Environment
- 보호 규칙: 없음 (자동 배포)

#### Production Environment
- **Required reviewers**: 1명 이상 승인 필요
- **Wait timer**: 선택적 대기 시간
- **Deployment branches**: `main` 및 `v*` 태그만 허용

---

## 13. 사용 가이드

### 13.1 일반 개발 워크플로우

```mermaid
sequenceDiagram
    participant Dev as 개발자
    participant Branch as Feature Branch
    participant PR as Pull Request
    participant CI as CI Pipeline
    participant Main as main Branch
    participant CD as CD Pipeline
    participant Staging as Staging

    Dev->>Branch: 1. 코드 작성
    Dev->>Branch: 2. 커밋 & 푸시
    Dev->>PR: 3. PR 생성
    PR->>CI: 4. CI 자동 실행
    CI-->>PR: 5. 결과 표시
    Note over CI,PR: 린트, 테스트, 빌드, 보안 스캔
    PR->>Main: 6. PR 머지 (승인 후)
    Main->>CD: 7. CD 자동 실행
    CD->>Staging: 8. Staging 배포
```

### 13.2 릴리즈 워크플로우

```mermaid
sequenceDiagram
    participant Dev as 개발자
    participant Main as main Branch
    participant Tag as Release Tag
    participant CD as CD Pipeline
    participant Staging as Staging
    participant Approval as 승인자
    participant Prod as Production

    Dev->>Main: 1. 릴리즈 준비 완료
    Dev->>Tag: 2. 태그 생성 (v1.0.0)
    Tag->>CD: 3. CD 자동 실행
    CD->>Staging: 4. Staging 배포
    Note over Staging: 테스트 및 검증
    CD->>Approval: 5. Production 배포 승인 요청
    Approval->>CD: 6. 승인
    CD->>Prod: 7. Production 배포
    CD->>Dev: 8. Slack 알림
```

### 13.3 태그 생성 방법

```bash
# 버전 태그 생성
git tag v1.0.0
git push origin v1.0.0

# 또는 GitHub Releases에서 생성
# 1. Releases 탭 이동
# 2. "Draft a new release" 클릭
# 3. 태그 및 릴리즈 노트 작성
# 4. "Publish release" 클릭
```

### 13.4 수동 배포

1. **GitHub Actions 탭** 이동
2. 좌측에서 **CD Pipeline** 선택
3. **Run workflow** 버튼 클릭
4. 환경 선택 후 실행

### 13.5 CI 상태 확인

PR 페이지에서 CI 상태 확인:

| 상태 | 의미 | 조치 |
|------|------|------|
| All checks passed | 모든 검증 통과 | 머지 가능 |
| Some checks failed | 일부 검증 실패 | 실패 원인 확인 후 수정 |
| Some checks pending | 검증 진행 중 | 완료 대기 |
| Skipped | 해당 없음 | 변경된 파일 없음 |

---

## 14. 트러블슈팅

### 14.1 CI 실패 원인별 해결

#### Backend Test 실패

```bash
# 로컬에서 테스트 실행
cd knowledge_service/backend
./gradlew test

# Checkstyle 확인
./gradlew checkstyleMain
```

#### Frontend Test 실패

```bash
# 로컬에서 테스트 실행
cd knowledge_service/frontend
npm ci
npm run lint
npm run type-check
npm test
```

#### AI Service Test 실패

```bash
# 로컬에서 테스트 실행
cd knowledge_service
poetry install
poetry run ruff check src/
poetry run pytest src/tests/ -v
```

#### Docker Build 실패

```bash
# 로컬에서 빌드 테스트
docker build -t test-image ./knowledge_service/backend
```

### 14.2 CD 실패 원인별 해결

#### SSH 연결 실패

1. Secrets 설정 확인 (`STAGING_HOST`, `STAGING_USER`, `STAGING_SSH_KEY`)
2. 서버 방화벽 설정 확인
3. SSH 키 권한 확인

#### 이미지 푸시 실패

1. `GITHUB_TOKEN` 권한 확인 (packages:write)
2. Repository Settings → Actions → General → Workflow permissions 확인

#### 배포 후 Health Check 실패

1. 서버 로그 확인: `docker compose logs -f`
2. 컨테이너 상태 확인: `docker compose ps`
3. 네트워크 설정 확인

### 14.3 일반적인 문제

| 문제 | 원인 | 해결 |
|------|------|------|
| "Resource not accessible" | 권한 부족 | Workflow permissions 확인 |
| "Context deadline exceeded" | 타임아웃 | 작업 분할 또는 타임아웃 증가 |
| "Cache not found" | 캐시 키 불일치 | 캐시 키 패턴 확인 |
| "No space left on device" | 디스크 공간 부족 | 이미지 정리 (`docker image prune`) |

### 14.4 실제 장애 사례 및 해결

#### 장애 1: Docker Build - Backend/Gateway arm64 빌드 실패

| 항목 | 내용 |
|------|------|
| **증상** | Build Backend, Build Gateway job에서 "Build and Push" 단계가 1초 만에 실패 |
| **에러** | `eclipse-temurin:17-jre-alpine: no match for platform in manifest: not found` |
| **원인** | Backend/Gateway Dockerfile의 런타임 이미지 `eclipse-temurin:17-jre-alpine`이 arm64 매니페스트를 제공하지 않음. 워크플로우가 `linux/amd64,linux/arm64` 멀티플랫폼 빌드를 시도하여 실패 |
| **해결** | `docker-build.yml`, `cd.yml`의 기본 빌드 플랫폼을 `linux/amd64`로 변경 |
| **커밋** | `26ddea1` |
| **향후 조치** | arm64 지원이 필요한 경우 Dockerfile 런타임 이미지를 `eclipse-temurin:17-jre` (Ubuntu 기반)로 교체 |

#### 장애 2: CD Pipeline - 시작 자체 실패 (0 jobs, 0초)

| 항목 | 내용 |
|------|------|
| **증상** | CD Pipeline이 0초/0 jobs로 즉시 실패. GitHub API에서 워크플로우 이름이 `CD Pipeline` 대신 파일 경로(`cd.yml`)로 표시 |
| **원인** | `build-and-push` matrix job의 `outputs` 섹션이 동적 step ID(`meta-${{ matrix.name }}`)를 참조. GitHub Actions는 워크플로우 YAML 평가(파싱) 단계에서 동적 step ID를 해석할 수 없어 워크플로우 자체가 로드되지 않음 |
| **해결** | 미사용 `outputs` 섹션 및 동적 step ID 제거 |
| **커밋** | `a3baf54` |

```yaml
# 문제가 된 코드 (제거됨)
outputs:
  image-tag-${{ matrix.name }}: ${{ steps.meta-${{ matrix.name }}.outputs.tags }}
```

#### 장애 3: CD Pipeline - Deploy to Staging SSH 실패

| 항목 | 내용 |
|------|------|
| **증상** | Deploy to Staging job에서 `Error: missing server host` |
| **원인** | GitHub Repository Secrets에 `STAGING_HOST`, `STAGING_USER`, `STAGING_SSH_KEY`가 미설정 |
| **해결** | 스테이징 서버 준비 후 GitHub Settings > Secrets and variables > Actions에서 SSH 관련 시크릿 추가 |
| **현재 상태** | 서버 미구축으로 인한 예상된 실패. Build 단계(4건)는 정상 통과 |

---

## 15. 베스트 프랙티스

### 15.1 브랜치 전략

```mermaid
gitGraph
    commit id: "Initial"
    branch develop
    checkout develop
    commit id: "Feature A"
    branch feature/user-auth
    checkout feature/user-auth
    commit id: "Auth impl"
    commit id: "Auth test"
    checkout develop
    merge feature/user-auth
    checkout main
    merge develop tag: "v1.0.0"
    checkout develop
    commit id: "Feature B"
```

### 15.2 커밋 메시지 규칙

```
[TYPE] 간단한 설명

- 상세 변경사항 1
- 상세 변경사항 2

관련 이슈: #123
```

### 15.3 PR 체크리스트

- [ ] 로컬에서 테스트 통과 확인
- [ ] 린트 오류 없음
- [ ] 타입 체크 통과
- [ ] 문서 업데이트 (필요 시)
- [ ] 적절한 리뷰어 지정

### 15.4 CI/CD 최적화 팁

1. **캐시 활용**: 의존성 캐시로 빌드 시간 단축
2. **병렬 실행**: 독립적인 Job은 병렬로 실행
3. **선택적 실행**: 변경된 파일에 따라 필요한 Job만 실행
4. **concurrency 설정**: 동일 브랜치 중복 실행 방지

```yaml
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true
```

### 15.5 보안 권장사항

1. **Secrets 관리**: 민감 정보는 반드시 GitHub Secrets 사용
2. **최소 권한**: 필요한 최소 권한만 부여
3. **환경 보호**: Production 환경에 승인 필수 설정
4. **의존성 스캔**: Trivy, Dependabot 활용
5. **코드 스캔**: CodeQL 또는 추가 보안 스캐너 고려

---

## 참고 자료

### 프로젝트 내 문서

- [DevOps 상세 설계서](../02_design/07_devops_detailed_design.md)
- [Infrastructure 상세 설계서](../02_design/10_infrastructure_detailed_design.md)
- [Docker Troubleshooting](./docker_troubleshooting.md)

### 외부 문서

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitHub Packages (GHCR)](https://docs.github.com/en/packages)
- [Docker Build Push Action](https://github.com/docker/build-push-action)
- [Trivy Scanner](https://github.com/aquasecurity/trivy-action)
- [Branch Protection Rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/managing-a-branch-protection-rule)

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 1.0 | 2026-01-22 | 초기 작성 |
| 1.1 | 2026-01-25 | pr-build.yml, docker-build.yml, code-quality.yml 추가, Branch Protection Rules 섹션 추가 |
| 2.0 | 2026-01-26 | Docker Build arm64 호환 수정, CD Pipeline startup failure 수정, Docker Compose Validate/E2E Tests 워크플로우 추가, 운영 현황 및 트러블슈팅 보강 |

---

**작성자**: DevOps Agent
**검토자**: TechLead Agent
