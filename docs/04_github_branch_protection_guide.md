# GitHub Branch Protection 설정 가이드

**Version**: 1.1 | **Updated**: 2026-01-26

> **현행화 정보**
> - **최종 현행화**: 2026-02-20
> - **프로젝트 상태**: 종료 (2026-02-18)
> - **문서 상태**: 현행
> - **주요 변경사항**: CI 워크플로우 파일 목록은 실제 구현과 일치함. `pr-build.yml`, `code-quality.yml`, `e2e-test.yml`, `docker-compose-validate.yml`, `cd.yml` 모두 존재 확인.

## 개요

GitHub Branch Protection Rules를 설정하여 코드 품질과 배포 안정성을 보장하기 위한 가이드입니다.
main 브랜치에 대한 force push, 삭제 차단 및 PR 머지 전 CI 통과를 강제합니다.

> **상세 가이드**: [Branch Protection 설정 가이드 v1.0](../knowledge_service/docs/06_deployment/01_branch_protection_guide.md) — gh CLI 설정, CODEOWNERS, 긴급 Bypass 등 포함

---

## 1. 설정 진입

GitHub Repository 페이지에서 **"Your main branch isn't protected"** 배너의 **Protect this branch** 클릭 또는:

```
Repository → Settings → Branches → Add branch protection rule
```

---

## 2. main 브랜치 보호 규칙

### 2.1 팀 개발 환경 (권장 설정)

**Branch name pattern**: `main`

| 설정 | 값 | 설명 |
|------|-----|------|
| **Require a pull request before merging** | ON | Direct push 차단 |
| ├─ Required approvals | **1** | 최소 1명의 리뷰어 승인 필요 |
| ├─ Dismiss stale approvals | ON | 새 커밋 push 시 기존 승인 무효화 |
| **Require status checks to pass** | ON | CI Pipeline 통과 필수 |
| ├─ Require branches to be up to date | ON | 최신 base와 동기화 |
| ├─ Status checks 추가 | `CI Summary` | ci.yml의 ci-summary job |
| **Require conversation resolution** | ON | 모든 리뷰 대화 해결 필수 |
| **Do not allow force pushes** | ON (기본) | Force push 차단 |
| **Do not allow deletions** | ON | 브랜치 삭제 차단 |

### 2.2 1인 개발 환경 (실용적 설정)

> 1인 프로젝트에서 "Required approvals: 1"로 설정하면 본인이 올린 PR을 본인이 승인할 수 없어 **머지가 불가능**합니다.

| 설정 | 값 | 설명 |
|------|-----|------|
| **Require a pull request before merging** | OFF 또는 approvals=0 | 1인 개발 시 PR 없이도 push 가능 |
| **Require status checks to pass** | ON | CI 통과는 필수 유지 |
| ├─ Require branches to be up to date | ON | 최신 base와 동기화 |
| ├─ Status checks 추가 | `CI Summary` | ci.yml의 ci-summary job |
| **Do not allow force pushes** | ON (기본) | Force push 차단 |
| **Do not allow deletions** | ON | 브랜치 삭제 차단 |
| **Include administrators** | OFF | 관리자(본인)는 긴급 시 우회 가능 |

**핵심 포인트**: CI가 통과해야만 머지되고, force push/삭제는 방지하면서 혼자 작업하는 데 불편함이 없는 구성.

---

## 3. Required Status Checks

### 3.1 필수 Status Check

| Status Check | Job 이름 | 워크플로우 | 설명 |
|--------------|----------|-----------|------|
| **CI Summary** | `ci-summary` | ci.yml | Backend/Gateway/Frontend/AI 전체 빌드/테스트 종합 |

`CI Summary`는 모든 서비스의 빌드/테스트 결과를 종합 판단합니다:

| 포함 Job | 검증 내용 |
|----------|----------|
| `backend-test` | Backend 빌드/테스트 |
| `gateway-test` | Gateway 빌드/테스트 |
| `frontend-test` | Frontend 빌드/테스트 |
| `ai-service-test` | AI Service 빌드/테스트 |
| `security-scan` | Trivy 보안 스캔 (경고만) |
| `docker-build-test` | Docker 이미지 빌드 검증 (경고만) |

### 3.2 선택 Status Check (권장)

| Status Check | 워크플로우 | 용도 |
|--------------|-----------|------|
| `PR Build Summary` | pr-build.yml | PR 빌드 검증 |
| `Quality Summary` | code-quality.yml | 코드 품질 (Python/Java/TypeScript) |
| `E2E Test Summary` | e2e-test.yml | Playwright E2E 테스트 |
| `Validate Docker Compose` | docker-compose-validate.yml | 인프라 설정 검증 |

---

## 4. develop 브랜치 보호 규칙

| 설정 | 값 | 설명 |
|------|-----|------|
| **Require a pull request before merging** | ON (approvals=0) | PR 필수, 승인은 선택 |
| **Require status checks to pass** | ON | 빌드 통과 필수 |
| ├─ Status checks 추가 | `PR Build Summary` | pr-build.yml |
| **Do not allow force pushes** | ON | Force push 차단 |
| **Do not allow deletions** | ON | 브랜치 삭제 차단 |

---

## 5. 설정 검증

### PR 생성 시 확인사항

1. PR 생성 후 **Checks** 탭에서 워크플로우 실행 확인
2. Required Check가 모두 표시되는지 확인

### 머지 버튼 상태

| 상태 | 머지 버튼 |
|------|----------|
| 모든 체크 통과 | **녹색** (Merge 가능) |
| 체크 진행 중 | **회색** (대기 중) |
| 체크 실패 | **빨간색** (Merge 차단) |

---

## 6. 트러블슈팅

### Status Check가 목록에 없는 경우

해당 워크플로우가 한 번 이상 실행되어야 검색에 표시됩니다. PR을 생성하여 워크플로우를 트리거한 후 다시 설정하세요.

### E2E 테스트가 실행되지 않는 경우

1. `paths` 필터 확인: `knowledge_service/frontend/**` 경로 변경 시에만 실행
2. 수동 실행: Actions 탭에서 **workflow_dispatch** 사용

### 1인 개발자가 PR 머지 불가한 경우

"Required approvals: 1" 설정 시 본인 PR을 본인이 승인할 수 없습니다.
해결: Branches 설정에서 approvals 수를 **0**으로 변경하거나 "Require a pull request" 옵션을 해제합니다.

---

## 7. 워크플로우 파일 참조

```
.github/workflows/
  ci.yml                       # CI Pipeline (빌드/테스트/보안)
  pr-build.yml                 # PR 빌드 검증
  code-quality.yml             # 코드 품질 분석
  e2e-test.yml                 # Playwright E2E 테스트
  docker-build.yml             # Docker 이미지 빌드
  docker-compose-validate.yml  # Docker Compose 검증
  cd.yml                       # CD Pipeline (배포)
```

---

## 8. 참고 문서

- [Branch Protection 상세 가이드 v1.0](../knowledge_service/docs/06_deployment/01_branch_protection_guide.md) — gh CLI, CODEOWNERS, Bypass 절차 포함
- [GitHub Actions CI/CD 운영 가이드 v2.0](../knowledge_service/docs/07_maintenance/03_github_actions_cicd_guide.md)
- [GitHub Branch Protection Rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)

---

## 현행화 이력

| 일자 | 작성자 | 내용 |
|------|--------|------|
| 2026-02-20 | Claude (doc-agent) | 프로젝트 종료 후 현행화 — 워크플로우 파일 실제 존재 여부 확인 (모두 구현됨), 문서 상태 현행으로 판정 |
