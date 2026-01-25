# GitHub Branch Protection 설정 가이드

## 개요

PR 머지 전 E2E 테스트 자동 실행을 강제하기 위한 GitHub Branch Protection Rules 설정 가이드입니다.

## 설정 방법

### 1. Repository Settings 접근

1. GitHub Repository 페이지에서 **Settings** 탭 클릭
2. 좌측 메뉴에서 **Branches** 선택

### 2. Branch Protection Rule 추가

**Add branch protection rule** 버튼 클릭 후 아래 설정 적용:

#### 기본 설정

| 항목 | 값 | 설명 |
|------|-----|------|
| Branch name pattern | `main` | 보호할 브랜치 (main, develop 각각 설정) |
| Require a pull request before merging | **체크** | PR을 통해서만 머지 가능 |
| Require approvals | **1** | 최소 1명의 리뷰어 승인 필요 |

#### Required Status Checks (필수)

**Require status checks to pass before merging** 체크 후:

| Status Check | Job 이름 | 워크플로우 |
|--------------|----------|-----------|
| E2E Tests | `Playwright E2E Tests` | e2e-test.yml |
| Frontend Tests | `Frontend Tests` | ci.yml |
| CI Summary | `CI Summary` | ci.yml |

**Status checks that are required**에 다음 항목 추가:
- `Playwright E2E Tests`
- `E2E Test Summary`

#### 추가 권장 설정

| 항목 | 권장 값 | 설명 |
|------|--------|------|
| Require conversation resolution before merging | **체크** | 모든 코멘트 해결 필요 |
| Do not allow bypassing the above settings | **체크** | 관리자도 규칙 우회 불가 |
| Restrict who can push to matching branches | **체크** | 직접 push 제한 |

### 3. develop 브랜치에도 동일 적용

`develop` 브랜치에 대해서도 동일한 규칙을 추가합니다.

## 설정 검증

### PR 생성 시 확인사항

1. PR 생성 후 **Checks** 탭에서 워크플로우 실행 확인
2. 다음 체크가 모두 **Required**로 표시되어야 함:
   - `Playwright E2E Tests`
   - `E2E Test Summary`

### 머지 버튼 상태

| 상태 | 머지 버튼 |
|------|----------|
| 모든 체크 통과 | **녹색** (Merge 가능) |
| 체크 진행 중 | **회색** (대기 중) |
| 체크 실패 | **빨간색** (Merge 차단) |

## 워크플로우 파일 참조

```
.github/workflows/
  e2e-test.yml       # E2E 테스트 워크플로우
  ci.yml             # CI 파이프라인 (Unit Test 포함)
  pr-build.yml       # PR 빌드 검증
```

## 트러블슈팅

### Status Check가 목록에 없는 경우

1. 해당 워크플로우가 한 번 이상 실행되어야 목록에 표시됨
2. PR을 생성하여 워크플로우를 트리거한 후 다시 설정

### E2E 테스트가 실행되지 않는 경우

1. `paths` 필터 확인: `knowledge_service/frontend/**` 경로 변경 시에만 실행
2. 수동 실행: Actions 탭에서 **workflow_dispatch** 사용

## 참고 문서

- [GitHub Branch Protection Rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [Playwright CI/CD](https://playwright.dev/docs/ci-intro)
