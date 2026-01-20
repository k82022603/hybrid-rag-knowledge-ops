# STORY-023: CI/CD 파이프라인 기초

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-23 |
| **Epic** | EPIC-001 |
| **Status** | To Do |
| **Priority** | Medium |
| **Story Points** | 3 |
| **Assignee** | DevOps |
| **Sprint** | 2 |

---

## User Story

**As a** 개발자,
**I want** 코드 푸시 시 자동으로 빌드/테스트/린트가 실행,
**So that** 코드 품질을 지속적으로 유지할 수 있음.

---

## Acceptance Criteria

- [ ] **Given** main 브랜치에 PR 생성, **When** 코드 푸시, **Then** 린트/테스트/빌드 파이프라인 자동 실행
- [ ] **Given** 테스트 실패, **When** 파이프라인 실행, **Then** PR 머지 차단
- [ ] **Given** 모든 체크 통과, **When** 파이프라인 완료, **Then** PR 머지 가능
- [ ] **Given** main 머지 후, **When** 파이프라인 실행, **Then** Docker 이미지 빌드 및 레지스트리 푸시

---

## Tasks

- [ ] GitHub Actions 또는 GitLab CI 설정 파일 생성
- [ ] Backend (Java) 빌드/테스트 단계 구성
- [ ] Frontend (Node.js) 빌드/테스트 단계 구성
- [ ] AI Service (Python) 빌드/테스트 단계 구성
- [ ] 린트 단계 구성 (checkstyle, eslint, ruff)
- [ ] Docker 이미지 빌드 단계 구성
- [ ] 환경 변수 및 시크릿 설정
- [ ] 파이프라인 테스트

---

## 기술 노트

### GitHub Actions 예시

```yaml
# .github/workflows/ci.yml
name: CI Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  # Backend (Java)
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up JDK 17
        uses: actions/setup-java@v4
        with:
          java-version: '17'
          distribution: 'temurin'

      - name: Cache Gradle
        uses: actions/cache@v4
        with:
          path: ~/.gradle/caches
          key: ${{ runner.os }}-gradle-${{ hashFiles('**/*.gradle*') }}

      - name: Lint (Checkstyle)
        run: cd backend && ./gradlew checkstyleMain

      - name: Test
        run: cd backend && ./gradlew test

      - name: Build
        run: cd backend && ./gradlew build -x test

  # Frontend (Node.js)
  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        run: cd frontend && npm ci

      - name: Lint (ESLint)
        run: cd frontend && npm run lint

      - name: Test
        run: cd frontend && npm run test

      - name: Build
        run: cd frontend && npm run build

  # AI Service (Python)
  ai-service:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install Poetry
        run: pip install poetry

      - name: Cache Poetry
        uses: actions/cache@v4
        with:
          path: ~/.cache/pypoetry
          key: ${{ runner.os }}-poetry-${{ hashFiles('ai-service/poetry.lock') }}

      - name: Install dependencies
        run: cd ai-service && poetry install

      - name: Lint (Ruff)
        run: cd ai-service && poetry run ruff check .

      - name: Test
        run: cd ai-service && poetry run pytest --cov=src

  # Docker Build (main only)
  docker-build:
    needs: [backend, frontend, ai-service]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ secrets.REGISTRY_URL }}
          username: ${{ secrets.REGISTRY_USERNAME }}
          password: ${{ secrets.REGISTRY_PASSWORD }}

      - name: Build and Push
        run: |
          docker-compose build
          docker-compose push
```

### GitLab CI 예시

```yaml
# .gitlab-ci.yml
stages:
  - lint
  - test
  - build
  - deploy

variables:
  GRADLE_OPTS: "-Dorg.gradle.daemon=false"

# Backend
backend:lint:
  stage: lint
  image: gradle:8-jdk17
  script:
    - cd backend && ./gradlew checkstyleMain

backend:test:
  stage: test
  image: gradle:8-jdk17
  script:
    - cd backend && ./gradlew test
  artifacts:
    reports:
      junit: backend/**/build/test-results/test/*.xml

backend:build:
  stage: build
  image: gradle:8-jdk17
  script:
    - cd backend && ./gradlew build -x test
  artifacts:
    paths:
      - backend/**/build/libs/*.jar

# Frontend
frontend:lint:
  stage: lint
  image: node:20
  script:
    - cd frontend && npm ci && npm run lint

frontend:test:
  stage: test
  image: node:20
  script:
    - cd frontend && npm ci && npm run test

frontend:build:
  stage: build
  image: node:20
  script:
    - cd frontend && npm ci && npm run build
  artifacts:
    paths:
      - frontend/dist/

# AI Service
ai-service:lint:
  stage: lint
  image: python:3.11
  script:
    - cd ai-service && pip install poetry && poetry install && poetry run ruff check .

ai-service:test:
  stage: test
  image: python:3.11
  script:
    - cd ai-service && pip install poetry && poetry install && poetry run pytest --cov=src
```

### 영향 범위
- `.github/workflows/ci.yml` 또는 `.gitlab-ci.yml`
- `docker-compose.yml` (이미지 태그 설정)

---

## 테스트 계획

- [ ] Unit Test: 각 서비스 빌드 성공 확인
- [ ] Integration Test: PR 생성 시 파이프라인 트리거
- [ ] Integration Test: 테스트 실패 시 머지 차단
- [ ] Integration Test: main 푸시 시 Docker 빌드

---

## 참고 자료

- [GitHub Actions 문서](https://docs.github.com/en/actions)
- [GitLab CI/CD 문서](https://docs.gitlab.com/ee/ci/)
- [Docker Compose Build](https://docs.docker.com/compose/compose-file/build/)
