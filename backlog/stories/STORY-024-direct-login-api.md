# STORY-024: 직접 로그인 API 개발

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-21 |
| **Epic** | EPIC-003 |
| **Status** | Done |
| **Priority** | Critical (P0 - Blocker) |
| **Story Points** | 5 |
| **Assignee** | Backend, QA |
| **Sprint** | 2 |

---

## User Story

**As a** 사용자,
**I want** 이메일과 비밀번호로 직접 로그인,
**So that** Keycloak SSO 없이도 시스템에 접근할 수 있음.

---

## 배경

Frontend 로그인 UI가 구현되었으나, 직접 로그인 API가 미개발 상태.
- Frontend: `POST /api/auth/login` 호출
- Backend: 해당 엔드포인트 없음

현재 `auth_server.py` (로컬 Python 서버)로 임시 테스트 중이나, 실제 백엔드 API 개발 필요.

---

## Acceptance Criteria

- [ ] **Given** 유효한 이메일/비밀번호, **When** POST /api/auth/login, **Then** JWT 토큰 및 사용자 정보 반환 (200 OK)
- [ ] **Given** 잘못된 비밀번호, **When** POST /api/auth/login, **Then** 401 Unauthorized (에러 메시지 포함)
- [ ] **Given** 존재하지 않는 이메일, **When** POST /api/auth/login, **Then** 401 Unauthorized (에러 메시지 포함)
- [ ] **Given** 유효한 Refresh Token, **When** POST /api/auth/refresh, **Then** 새 Access Token 반환
- [ ] **Given** 만료된 Refresh Token, **When** POST /api/auth/refresh, **Then** 401 Unauthorized
- [ ] **Given** 인증된 사용자, **When** POST /api/auth/logout, **Then** 세션 종료 및 200 OK
- [ ] **Given** 5회 연속 로그인 실패, **When** 추가 로그인 시도, **Then** 429 Too Many Requests (Rate Limiting)

---

## Tasks

- [ ] AuthController 클래스 생성
  - POST /api/auth/login
  - POST /api/auth/refresh
  - POST /api/auth/logout
- [ ] AuthService 비즈니스 로직 구현
  - 사용자 인증 (PostgreSQL users 테이블 조회)
  - 비밀번호 검증 (BCrypt)
  - JWT 토큰 생성/검증
- [ ] DTO 클래스 생성
  - LoginRequest (email, password)
  - LoginResponse (user, accessToken, refreshToken, expiresIn)
  - RefreshRequest (refreshToken)
  - ErrorResponse (status, message, timestamp)
- [ ] Rate Limiting 설정 (Bucket4j 또는 Redis 기반)
- [ ] 단위 테스트 작성 (80%+ 커버리지)
- [ ] 통합 테스트 작성
- [ ] API 문서 업데이트 (OpenAPI/Swagger)

---

## 기술 노트

### API 명세

```yaml
# POST /api/auth/login
request:
  Content-Type: application/json
  body:
    email: string (required)
    password: string (required)

response (200):
  body:
    user:
      id: string
      email: string
      username: string
      roles: string[]
    accessToken: string (JWT)
    refreshToken: string
    expiresIn: number (seconds)

response (401):
  body:
    status: 401
    message: "이메일 또는 비밀번호가 올바르지 않습니다."
    timestamp: string
```

### 구현 방향

```java
@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;

    @PostMapping("/login")
    public ResponseEntity<LoginResponse> login(@RequestBody @Valid LoginRequest request) {
        return ResponseEntity.ok(authService.authenticate(request));
    }

    @PostMapping("/refresh")
    public ResponseEntity<TokenResponse> refresh(@RequestBody @Valid RefreshRequest request) {
        return ResponseEntity.ok(authService.refreshToken(request));
    }

    @PostMapping("/logout")
    public ResponseEntity<Void> logout(@AuthenticationPrincipal JwtUser user) {
        authService.logout(user.getId());
        return ResponseEntity.ok().build();
    }
}
```

### 데이터베이스 스키마

PostgreSQL `users` 테이블 활용:
```sql
-- 이미 존재하는 테이블 확인 필요
SELECT * FROM users WHERE email = ? AND active = true;
```

비밀번호 해싱:
```java
// BCryptPasswordEncoder 사용
passwordEncoder.matches(rawPassword, encodedPassword);
```

### JWT 토큰 설정

```yaml
jwt:
  secret: ${JWT_SECRET}
  access-token-validity: 3600  # 1시간
  refresh-token-validity: 604800  # 7일
```

### 영향 범위

- `backend/src/main/java/com/knowledge/backend/api/controller/AuthController.java` (신규)
- `backend/src/main/java/com/knowledge/backend/service/AuthService.java` (신규)
- `backend/src/main/java/com/knowledge/backend/api/dto/auth/` (신규 디렉토리)
- `backend/src/main/java/com/knowledge/backend/config/SecurityConfig.java` (수정 - /api/auth/** 공개 경로 추가)
- `backend/src/main/resources/application.yml` (JWT 설정 추가)

---

## 테스트 계획

- [ ] Unit Test: AuthService 로직 테스트
  - 유효한 자격 증명 → 성공
  - 잘못된 비밀번호 → 실패
  - 존재하지 않는 사용자 → 실패
  - 비활성화된 계정 → 실패
- [ ] Unit Test: JWT 토큰 생성/검증
- [ ] Integration Test: 전체 로그인 플로우
- [ ] Integration Test: Rate Limiting 동작 확인

---

## 참고 자료

- [인증/인가 상세 설계서](../../knowledge_service/docs/02_design/authentication_authorization_detailed_design.md)
- [Frontend authSlice.ts](../../knowledge_service/frontend/src/store/slices/authSlice.ts) - API 호출 명세 참조
- [Spring Security OAuth2](https://docs.spring.io/spring-security/reference/)
- STORY-022: JWT 인증 필터 (Keycloak JWT 검증)

---

## 연관 Story

| Story | 관계 |
|-------|------|
| STORY-022 | depends on (JWT 인증 필터) |
| STORY-040 | related (Frontend Keycloak 연동) |
