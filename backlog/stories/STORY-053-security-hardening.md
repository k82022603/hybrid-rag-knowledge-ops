# STORY-053: 보안 강화 (JWT Secret, 입력 검증, 기본 자격증명 제거)

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | (미정) |
| **Epic** | EPIC-001 |
| **Status** | To Do |
| **Priority** | Critical |
| **Story Points** | 3 |
| **Assignee** | Backend |
| **Sprint** | 4 |

---

## User Story

**As a** 시스템 보안 관리자,
**I want** JWT Secret 하드코딩 제거, SSE 입력 검증, 기본 자격증명 제거를 포함한 보안 강화,
**So that** 알려진 보안 취약점이 제거되어 시스템이 운영 환경에서 안전하게 동작할 수 있음.

---

## Acceptance Criteria

- [ ] **Given** JWT Secret 환경변수가 설정되지 않음, **When** 애플리케이션 시작 시, **Then** 시작 실패하고 명확한 에러 메시지 출력 (기본값 fallback 없음)
- [ ] **Given** SSE 검색 엔드포인트에 쿼리 전송, **When** 쿼리 길이가 1000자 초과, **Then** 400 Bad Request 응답 반환
- [ ] **Given** SSE 검색 엔드포인트에 쿼리 전송, **When** 쿼리에 XSS 패턴 포함, **Then** 입력 새니타이징 후 처리 또는 거부
- [ ] **Given** 시스템 배포 후, **When** 기본 비밀번호(admin/admin 등)로 로그인 시도, **Then** 인증 실패
- [ ] **Given** application.yml 또는 .env, **When** JWT Secret 값 확인, **Then** 하드코딩된 기본값 없음 (환경변수 참조만 존재)

---

## Tasks

- [ ] JWT Secret 기본값 하드코딩 제거 (application.yml, SecurityConfig)
- [ ] JWT Secret 환경변수 미설정 시 애플리케이션 시작 실패 로직 추가
- [ ] SSE 엔드포인트 쿼리 입력 길이 검증 (최대 1000자)
- [ ] 쿼리 입력 새니타이징 (HTML/Script 태그 제거)
- [ ] 기본 자격증명 제거 (Keycloak admin, DB 기본 비밀번호 등)
- [ ] 환경변수 기반 비밀번호 설정 가이드 문서화
- [ ] 보안 설정 검증 통합 테스트 작성

---

## 기술 노트

### 문제점 (Sprint 03 리뷰에서 도출)

Sprint 03 보안 검토에서 다음 취약점이 식별됨:

1. **JWT Secret 하드코딩** - `application.yml`에 기본 JWT Secret이 평문으로 기록되어 있어, 소스코드 유출 시 토큰 위조 가능
2. **SSE 입력 검증 부재** - 쿼리 파라미터에 길이 제한이나 새니타이징이 없어 XSS, 대용량 입력 공격에 취약
3. **기본 자격증명 존재** - Keycloak admin, PostgreSQL 등에 기본 비밀번호가 설정되어 있어 무차별 대입 공격에 취약

### 해결 방향

```java
// Before (취약)
@Value("${jwt.secret:my-default-secret-key}")
private String jwtSecret;

// After (안전)
@Value("${jwt.secret}")
private String jwtSecret;

@PostConstruct
public void validateConfig() {
    if (jwtSecret == null || jwtSecret.isBlank()) {
        throw new IllegalStateException(
            "JWT_SECRET 환경변수가 설정되지 않았습니다. " +
            "애플리케이션을 시작할 수 없습니다."
        );
    }
    if (jwtSecret.length() < 32) {
        throw new IllegalStateException(
            "JWT_SECRET은 최소 32자 이상이어야 합니다."
        );
    }
}
```

```java
// 입력 검증
@GetMapping("/stream")
public SseEmitter streamSearch(
    @RequestParam @Size(max = 1000, message = "쿼리는 1000자 이내") String query
) {
    String sanitized = Jsoup.clean(query, Whitelist.none());
    // ...
}
```

### 영향 범위

- `backend/src/main/resources/application.yml` - JWT Secret 기본값 제거
- `backend/src/main/java/.../config/SecurityConfig.java` - 시작 시 검증
- `backend/src/main/java/.../controller/SearchController.java` - 입력 검증
- `infrastructure/docker-compose.yml` - 기본 비밀번호 환경변수화
- `.env.example` - 필수 환경변수 목록 업데이트

---

## 테스트 계획

- [ ] Unit Test: JWT Secret 미설정 시 시작 실패 확인
- [ ] Unit Test: 쿼리 길이 초과 시 400 응답
- [ ] Unit Test: XSS 패턴 입력 시 새니타이징 또는 거부
- [ ] Integration Test: 기본 자격증명 로그인 실패 확인
- [ ] Security Test: OWASP Top 10 체크리스트 검증

---

## 참고 자료

- Sprint 03 완료 리뷰에서 도출 - 보안 취약점 식별
- [STORY-022 JWT Auth Filter](./STORY-022-jwt-auth-filter.md)
- [STORY-024 Direct Login API](./STORY-024-direct-login-api.md)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
