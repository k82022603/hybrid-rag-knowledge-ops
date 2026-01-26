# 장애 보고서: GitHub Actions Docker Build / CD Pipeline 실패

## 개요

| 항목 | 내용 |
|------|------|
| **장애 ID** | INC-2026-01-26-001 |
| **발생 일시** | 2026-01-26 08:21 KST (최초 확인) |
| **해결 일시** | 2026-01-26 22:22 KST |
| **총 소요 시간** | 약 30분 (분석 20분 + 수정/검증 10분) |
| **영향 범위** | GitHub Actions CI/CD 파이프라인 (Docker Build, CD Pipeline) |
| **심각도** | Medium (프로덕션 영향 없음, CI/CD 파이프라인 부분 실패) |
| **작성자** | 클로드 (Claude Code) |
| **검토자** | - |

---

## 1. 장애 요약

GitHub Actions의 Docker Build 워크플로우에서 Backend/Gateway 이미지 빌드가 실패하고, CD Pipeline 워크플로우가 시작 자체에 실패하는 2건의 장애가 동시에 발생.

### 영향받은 워크플로우

| 워크플로우 | 증상 | 심각도 |
|-----------|------|--------|
| Docker Build | Build Backend, Build Gateway 실패 (1초 만에) | High |
| CD Pipeline | 0 jobs / 0초로 즉시 실패 (워크플로우 시작 불가) | Critical |

### 영향받지 않은 워크플로우

| 워크플로우 | 상태 |
|-----------|------|
| CI Pipeline | 정상 |
| PR Build | 정상 |
| Code Quality | 정상 |
| Docker Compose Validate | 정상 |
| E2E Tests | 정상 |

---

## 2. 타임라인

| 시간 (KST) | 이벤트 |
|------------|--------|
| 08:21 | 커밋 `ca931fa` push → Docker Build 트리거 |
| 08:22 | Build Backend, Build Gateway 1초 만에 실패 (Build AI Service, Build Frontend 성공) |
| 08:22 | CD Pipeline 0 jobs / 0초로 즉시 실패 |
| 21:53 | 사용자가 GitHub Actions 상태 스크린샷 공유, 조사 시작 |
| 22:00 | GitHub API로 check-runs annotations 분석 → Docker Build 근본 원인 식별 |
| 22:04 | Docker Build 수정: 빌드 플랫폼 `linux/amd64`로 변경 |
| 22:05 | 커밋 `26ddea1` push |
| 22:08 | Docker Build 전체 성공 확인 (5/5 jobs) |
| 22:10 | CD Pipeline 여전히 0 jobs 실패 확인 → 별도 원인 조사 |
| 22:15 | CD Pipeline 근본 원인 식별: matrix job outputs 동적 step ID 문제 |
| 22:20 | CD Pipeline 수정: outputs 섹션 및 동적 step ID 제거 |
| 22:20 | 커밋 `a3baf54` push |
| 22:22 | **CD Pipeline Build 4건 성공 확인** (Deploy to Staging은 시크릿 미설정으로 실패 — 예상된 동작) |

---

## 3. 근본 원인 분석 (Root Cause Analysis)

### 장애 A: Docker Build — Backend/Gateway arm64 빌드 실패

#### 3.1 직접 원인

`eclipse-temurin:17-jre-alpine` Docker 이미지가 `linux/arm64` 플랫폼 매니페스트를 제공하지 않음.

```
ERROR: failed to build: failed to solve:
eclipse-temurin:17-jre-alpine: failed to resolve source metadata for
docker.io/library/eclipse-temurin:17-jre-alpine:
no match for platform in manifest: not found
```

#### 3.2 근본 원인

워크플로우의 기본 빌드 플랫폼이 `linux/amd64,linux/arm64` (멀티아키텍처)로 설정되어 있었으나, Backend/Gateway Dockerfile의 런타임 이미지(`eclipse-temurin:17-jre-alpine`)가 amd64만 지원.

```yaml
# docker-build.yml (수정 전)
platforms: ${{ github.event.inputs.platform || 'linux/amd64,linux/arm64' }}
```

```dockerfile
# Backend/Gateway Dockerfile
FROM eclipse-temurin:17-jre-alpine  # arm64 미지원
```

Frontend(`node:20-alpine`, `nginx:alpine`)와 AI Service는 arm64를 지원하므로 성공.

#### 3.3 발생 조건

- push 이벤트로 트리거 시 `workflow_dispatch` 입력값이 없어 기본값 `linux/amd64,linux/arm64` 사용
- Docker Buildx가 arm64 베이스 이미지 매니페스트를 조회하는 단계에서 즉시 실패 (1초)

---

### 장애 B: CD Pipeline — 워크플로우 시작 실패 (0 jobs)

#### 3.4 직접 원인

CD Pipeline 워크플로우가 GitHub Actions 평가(evaluation) 단계에서 실패하여 어떤 job도 생성되지 않음.

#### 3.5 근본 원인

`build-and-push` matrix job의 `outputs` 섹션에서 동적 step ID를 참조하는 구문이 워크플로우 파싱 단계에서 해석 불가.

```yaml
# cd.yml (수정 전)
build-and-push:
  strategy:
    matrix:
      include:
        - name: backend
        - name: gateway
        - name: frontend
        - name: ai-service

  outputs:  # 문제 원인
    backend-image: ${{ steps.meta-backend.outputs.tags }}
    gateway-image: ${{ steps.meta-gateway.outputs.tags }}
    frontend-image: ${{ steps.meta-frontend.outputs.tags }}
    ai-service-image: ${{ steps.meta-ai-service.outputs.tags }}

  steps:
    - id: meta-${{ matrix.name }}  # 동적 step ID
      run: echo "tags=${{ steps.meta.outputs.tags }}" >> $GITHUB_OUTPUT
```

**문제 메커니즘**:
1. `id: meta-${{ matrix.name }}`은 매트릭스 인스턴스별로 다른 step ID 생성 (예: `meta-backend`, `meta-gateway`)
2. `outputs` 섹션의 `${{ steps.meta-backend.outputs.tags }}`는 특정 매트릭스 인스턴스의 step을 참조
3. GitHub Actions가 워크플로우 YAML을 평가할 때, 매트릭스 확장 전에 outputs 표현식을 검증
4. 평가 단계에서 해당 step ID를 해석할 수 없어 워크플로우 자체가 로드되지 않음

#### 3.6 부가 증거

- GitHub API에서 워크플로우 이름이 `CD Pipeline` 대신 파일 경로(`.github/workflows/cd.yml`)로 표시 → 파싱 실패 시 GitHub가 `name` 필드를 읽지 못해 파일 경로를 대신 사용
- 전체 실행 이력 33회 모두 0 jobs / 0초 실패 → 워크플로우 생성 시점부터 존재한 결함
- `created_at`과 `updated_at`이 동일 → 런타임이 아닌 파싱 단계 실패

---

## 4. 해결 조치

### 4.1 장애 A 해결: Docker Build 플랫폼 변경

**수정 파일**: `.github/workflows/docker-build.yml`, `.github/workflows/cd.yml`

```yaml
# Before (4곳)
platforms: ${{ github.event.inputs.platform || 'linux/amd64,linux/arm64' }}

# After
platforms: ${{ github.event.inputs.platform || 'linux/amd64' }}
```

추가 변경:
- `workflow_dispatch` 옵션에서 `linux/amd64,linux/arm64` 조합 제거
- Summary 단계의 플랫폼 표시 값 수정

**커밋**: `26ddea1` — `[FIX] Docker Build 실패 수정 - eclipse-temurin:17-jre-alpine arm64 미지원`

### 4.2 장애 B 해결: CD Pipeline outputs 제거

**수정 파일**: `.github/workflows/cd.yml`

```yaml
# 삭제된 코드 (11줄)

# 1. job outputs 섹션 (6줄)
outputs:
  backend-image: ${{ steps.meta-backend.outputs.tags }}
  gateway-image: ${{ steps.meta-gateway.outputs.tags }}
  frontend-image: ${{ steps.meta-frontend.outputs.tags }}
  ai-service-image: ${{ steps.meta-ai-service.outputs.tags }}

# 2. 동적 step ID (5줄)
- name: Output image tags
  if: steps.check-dockerfile.outputs.exists == 'true'
  id: meta-${{ matrix.name }}
  run: echo "tags=${{ steps.meta.outputs.tags }}" >> $GITHUB_OUTPUT
```

삭제 근거: downstream job(`deploy-staging`, `deploy-production`)에서 해당 outputs를 참조하지 않음.

**커밋**: `a3baf54` — `[FIX] CD Pipeline 시작 실패 수정 - matrix job outputs 제거`

---

## 5. 검증 결과

### 5.1 Docker Build (커밋 `26ddea1`)

| Job | 결과 | 소요 시간 |
|-----|------|----------|
| Build AI Service | Success | 24초 |
| Build Frontend | Success | 33초 |
| Build Gateway | Success | 1분 52초 |
| Build Backend | Success | 2분 26초 |
| Docker Build Summary | Success | 2초 |

### 5.2 CD Pipeline (커밋 `a3baf54`)

| Job | 결과 | 소요 시간 | 비고 |
|-----|------|----------|------|
| Build and Push (ai-service) | Success | 5초 | Dockerfile 미존재 → 스킵 |
| Build and Push (backend) | Success | 28초 | |
| Build and Push (frontend) | Success | 1분 27초 | |
| Build and Push (gateway) | Success | 1분 33초 | |
| Deploy to Staging | Failure | 15초 | `Error: missing server host` (시크릿 미설정, 예상된 동작) |
| Deploy to Production | Skipped | - | 조건 불충족 (태그 push 아님) |
| Rollback Deployment | Skipped | - | 조건 불충족 (workflow_dispatch 아님) |

---

## 6. 영향도 분석

### 6.1 서비스 영향

| 영향 | 상태 |
|------|------|
| 프로덕션 환경 | 영향 없음 (배포 환경 미구축) |
| 개발 환경 | 영향 없음 (로컬 개발에 영향 없음) |
| Docker 이미지 | GHCR 이미지 빌드/푸시 실패 (수정 후 정상) |
| 데이터 손실 | 없음 |
| 보안 취약점 | 없음 |

### 6.2 비즈니스 영향

- CI/CD 파이프라인 부분 실패로 인한 이미지 빌드 중단
- Sprint 02 진행에는 영향 없음 (개발 환경은 로컬 Docker Compose 사용)

---

## 7. 재발 방지 대책

### 7.1 단기 조치 (완료)

- [x] Docker Build 플랫폼을 `linux/amd64`로 변경
- [x] CD Pipeline의 문제 outputs/동적 step ID 제거
- [x] GitHub Actions CI/CD 가이드 v2.0 업데이트 (트러블슈팅 사례 추가)

### 7.2 중기 조치 (권장)

| 조치 | 담당 | 우선순위 |
|------|------|----------|
| Dockerfile 런타임 이미지를 멀티아키텍처 지원 이미지로 교체 (`eclipse-temurin:17-jre`) | Infra | Medium |
| CD Pipeline deploy job에 시크릿 존재 여부 사전 검증 추가 | DevOps | Low |
| GitHub Actions 워크플로우 변경 시 `actionlint` 로컬 검증 도입 | DevOps | Medium |

### 7.3 장기 조치 (검토)

- 워크플로우 변경 PR에 대한 자동 검증 CI 추가 (actionlint GitHub Action)
- 멀티아키텍처 빌드 필요 시 base image 호환성 매트릭스 문서화

---

## 8. 학습 포인트 (Lessons Learned)

### 8.1 기술적 교훈

1. **Alpine 이미지 플랫폼 지원**: `eclipse-temurin:*-alpine` 계열은 amd64만 지원. arm64가 필요하면 `eclipse-temurin:*-jammy` 또는 비-Alpine 태그 사용
2. **GitHub Actions matrix + outputs 제약**: matrix job에서 동적 step ID를 outputs에서 참조하면 워크플로우 파싱 자체가 실패할 수 있음. matrix outputs는 별도 패턴(artifact, environment variable) 사용 권장
3. **0 jobs / 0초 실패 패턴**: 워크플로우 이름이 파일 경로로 표시되면 YAML 파싱/평가 단계 실패를 의심

### 8.2 프로세스 교훈

1. **워크플로우 파일 로컬 검증**: `actionlint` 도구로 push 전 문법/구조 검증 필요
2. **멀티아키텍처 빌드 테스트**: 새 base image 도입 시 대상 플랫폼 매니페스트 존재 여부 확인
3. **CD Pipeline 모니터링**: 워크플로우 생성 후 최초 1회 성공 확인 필수

---

## 9. 참고 자료

### 관련 파일

| 파일 | 변경 내용 |
|------|----------|
| `.github/workflows/docker-build.yml` | 기본 플랫폼 `linux/amd64`로 변경, 멀티아키텍처 옵션 제거 |
| `.github/workflows/cd.yml` | 플랫폼 변경 + matrix outputs/동적 step ID 제거 |

### 관련 문서

- [GitHub Actions CI/CD 가이드 v2.0](../github_actions_cicd_guide.md)
- [Docker Troubleshooting Guide](../docker_troubleshooting.md)

### 관련 커밋

| 커밋 | 메시지 |
|------|--------|
| `26ddea1` | `[FIX] Docker Build 실패 수정 - eclipse-temurin:17-jre-alpine arm64 미지원` |
| `a3baf54` | `[FIX] CD Pipeline 시작 실패 수정 - matrix job outputs 제거` |

### 에러 메시지 원문

```
# 장애 A - Docker Build
buildx failed with: ERROR: failed to build: failed to solve:
eclipse-temurin:17-jre-alpine: failed to resolve source metadata for
docker.io/library/eclipse-temurin:17-jre-alpine:
no match for platform in manifest: not found

# 장애 B - CD Pipeline
(에러 메시지 없음 — 워크플로우가 0 jobs/0초로 즉시 실패, GitHub API에서 확인만 가능)

# 장애 C - Deploy to Staging (예상된 실패)
2026/01/26 13:21:59 Error: missing server host
```

---

## 10. 승인

| 역할 | 이름 | 서명 | 날짜 |
|------|------|------|------|
| 작성자 | 클로드 | - | 2026-01-26 |
| 검토자 | | | |
| 승인자 | | | |

---

*이 보고서는 Claude Code에 의해 자동 생성되었습니다.*
