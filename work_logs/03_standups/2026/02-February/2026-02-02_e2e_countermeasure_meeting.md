# E2E 테스트 대책 회의록

**날짜**: 2026-02-02 11:40 KST
**참석자**: PM, TechLead, QA, 클로드
**주제**: E2E 테스트 실패 원인 분석 및 대책 수립

---

## 1. 문제 상황

### 1.1 발생한 이슈

| # | 이슈 | 상세 |
|---|------|------|
| 1 | **Rate Limiting 초과** | `admin@example.com` 계정에 대해 15분 잠금 발생 |
| 2 | **Mock 환경 테스트 실행** | Docker 환경이 아닌 Vite dev server (localhost:3000)에서 테스트 |
| 3 | **재빌드 미실행** | 최신 소스가 Docker에 반영되지 않은 상태에서 테스트 시도 |

### 1.2 Backend 로그 증거

```
2026-02-02T02:36:33.489Z  WARN  c.knowledge.backend.service.AuthService : Rate limit exceeded for email: admin@example.com
2026-02-02T02:36:33.490Z ERROR c.k.b.api.controller.AuthController      : Login attempts exceeded. Please try again after 15 minutes.
```

### 1.3 테스트 실행 환경 분석

**실제 실행된 환경**:
- `baseURL: 'http://localhost:3000'` (Vite dev server)
- Mock 인증 폴백 (localStorage 주입)

**매뉴얼이 명시한 환경**:
- Docker Compose 18개 서비스 기동
- `baseURL: 'http://localhost:80'` (Nginx) 또는 `http://localhost:8080` (Gateway)
- 실제 Backend 인증 API

---

## 2. 매뉴얼 위반 사항

### 2.1 위반된 E2E 테스트 원칙

**문서 참조**: `docs/04_testing/e2e_test_process.md`

| # | 매뉴얼 원칙 | 위반 내용 |
|---|-----------|----------|
| 1 | "E2E 테스트 = Docker Compose 환경 필수" | Mock 환경에서 실행 |
| 2 | "No Docker, No E2E Test" | Vite dev server에서 실행 |
| 3 | "E2E 테스트 전 Docker 이미지 재빌드는 필수" | 재빌드 없이 테스트 시도 |
| 4 | Section 2.0 재빌드 체크리스트 | 체크리스트 확인 없이 진행 |

### 2.2 문제의 테스트 헬퍼 코드

**파일**: `frontend/e2e/helpers/auth.helper.ts`

```typescript
// 문제: API 실패 시 Mock 폴백 로직
if (stillOnLogin) {
  // Set up mock auth and navigate to dashboard
  await setupMockAuth(page, 'admin');
  await page.goto('/dashboard');
}
```

**사용자 요구사항 위반**:
> "E2E 테스트만을 위한 코드 추가나 Mock 이용한 테스트는 없어야 합니다."

---

## 3. 원인 분석

### 3.1 근본 원인

| 원인 | 분류 | 영향도 |
|------|------|--------|
| QA가 Docker 환경 설정 없이 테스트 실행 | **프로세스 미준수** | High |
| auth.helper.ts의 Mock 폴백 로직 | **코드 설계 문제** | Medium |
| Playwright 설정이 localhost:3000 (Vite) 지정 | **설정 불일치** | Medium |
| 테스트 반복 실행으로 Rate Limit 초과 | **테스트 설계 문제** | Medium |

### 3.2 Rate Limiting 문제

Rate Limiting은 **정상적인 보안 기능**이며, 비활성화해서는 안 됨.

**문제의 본질**: 동일 계정으로 반복 로그인 시도
- 테스트 실패 → 재실행 → 실패 → 재실행 → Rate Limit

---

## 4. 대책 수립

### 4.1 즉시 조치 (P0)

| # | 조치 | 담당 | 기한 |
|---|------|------|------|
| 1 | Rate Limit 잠금 해제 대기 (15분) 또는 Redis 키 삭제 | Infra | 즉시 |
| 2 | Docker 서비스 전체 재시작 | Infra | 즉시 |
| 3 | 최신 소스로 Docker 이미지 재빌드 | Infra | 30분 |

### 4.2 프로세스 개선 (P1)

| # | 개선 사항 | 담당 |
|---|----------|------|
| 1 | E2E 테스트 전 Pre-flight 체크리스트 의무화 | QA/PM |
| 2 | Playwright 설정에 Docker 환경 URL 명시 | Frontend |
| 3 | auth.helper.ts Mock 폴백 로직 제거 검토 | Frontend |
| 4 | QA 테스트 실행 시 환경 확인 단계 추가 | QA |

### 4.3 테스트 설계 개선 (P1)

**Rate Limit 대응 방안 (Mock/코드 추가 없이)**:

| # | 방안 | 장점 | 단점 |
|---|------|------|------|
| A | 테스트별 고유 계정 사용 | Rate Limit 분산 | 계정 관리 복잡 |
| B | 테스트 간 충분한 대기 시간 | 구현 단순 | 테스트 시간 증가 |
| C | 실패 시 다른 계정으로 전환 | 유연성 | 로직 복잡 |

**권장**: 방안 A + B 조합
- `admin@example.com` → 관리자 기능 테스트
- `test@example.com` → 일반 사용자 기능 테스트
- `user@example.com` → 추가 테스트 (예비)
- 테스트 파일 간 5초 대기

---

## 5. 올바른 E2E 테스트 실행 절차

### 5.1 Pre-flight 체크리스트 (필수)

```bash
# 1. 최신 소스 pull
git pull origin main

# 2. Docker 이미지 재빌드
cd infrastructure/docker
docker-compose build --no-cache backend frontend ai-service

# 3. 서비스 기동
docker-compose up -d

# 4. 헬스체크 (모든 서비스 healthy 확인)
./scripts/healthcheck.sh

# 5. Rate Limit 상태 확인 (Redis)
docker exec kp-redis redis-cli KEYS "rate_limit:*"
```

### 5.2 E2E 테스트 실행

```bash
# Playwright 설정 확인 (baseURL이 Docker 환경인지)
# baseURL: 'http://localhost:8080' (Gateway 경유)

cd knowledge_service/frontend

# Docker 환경에서 테스트 실행
E2E_BASE_URL=http://localhost:8080 npx playwright test
```

### 5.3 테스트 실패 시 대응

1. **Rate Limit 초과 시**: 15분 대기 또는 다른 계정 사용
2. **서비스 장애 시**: Infra에 에스컬레이션, Docker 로그 확인
3. **인증 실패 시**: 계정 정보 확인, Backend 로그 확인

---

## 6. 결론 및 합의 사항

### 6.1 합의 사항

| # | 내용 | 합의자 |
|---|------|--------|
| 1 | E2E 테스트는 반드시 Docker 환경에서만 실행 | 전원 |
| 2 | Mock 폴백/우회 로직 사용 금지 | 전원 |
| 3 | Rate Limiting은 항상 활성화 상태 유지 | 전원 |
| 4 | 테스트 전 재빌드 및 Pre-flight 체크 필수 | 전원 |
| 5 | 테스트 계정은 분리하여 Rate Limit 분산 | 전원 |

### 6.2 후속 조치

| 조치 | 담당 | 기한 | 상태 |
|------|------|------|------|
| Docker 서비스 재시작 및 재빌드 | Infra | 2026-02-02 | ☐ 대기 |
| Rate Limit 해제 후 테스트 재실행 | QA | 2026-02-02 | ☐ 대기 |
| auth.helper.ts Mock 폴백 제거 검토 | Frontend | 2026-02-03 | ☐ 미착수 |
| Playwright 설정 Docker URL로 변경 | Frontend | 2026-02-03 | ☐ 미착수 |

---

## 7. 회의 결론

**핵심 메시지**:
> "E2E 테스트는 실제 환경에서 실제 동작을 검증하는 것이 목적입니다.
> Mock이나 우회 로직은 E2E의 의미를 무효화합니다.
> Rate Limiting 같은 보안 기능은 테스트 대상이지, 제거 대상이 아닙니다."

---

**회의 종료**: 2026-02-02 11:45 KST
**작성자**: 클로드 (PM 대행)
**검토자**: TechLead, QA
