# ADR-003: Auth 엔드포인트 보안 정책

## 상태
Accepted

## 일자
2026-01-29

## 컨텍스트

Sprint 04 Day 3 Docker E2E 테스트에서 `/api/v1/auth/**` 경로의 보안 정책 불일치로 4건의 테스트가 실패했습니다.

### 관련 이슈

| 이슈 | 문제 | 영향 |
|------|------|------|
| SCRUM-56 | Logout 엔드포인트가 인증 없이 200 반환 | 3건 실패 |
| SCRUM-59 | /api/v1/health가 인증으로 차단됨 | 1건 실패 |

### 문제 상황

```
[기존 SecurityConfig]
.pathMatchers("/api/v1/auth/**").permitAll()  // 모든 auth 경로 public

문제:
1. logout이 인증 없이 호출 가능 (보안 취약)
2. health가 auth 경로 아래가 아님 → 별도 규칙 필요
```

## 결정

**Auth 경로를 세분화하여 엔드포인트별 인증 정책을 적용합니다.**

### 엔드포인트별 보안 정책

| 엔드포인트 | Method | 인증 | 이유 |
|-----------|--------|------|------|
| `/api/v1/auth/login` | POST | Public | 로그인 수행 |
| `/api/v1/auth/refresh` | POST | Public | Refresh Token으로 Access Token 갱신 |
| `/api/v1/auth/logout` | POST | **JWT 필수** | 인증된 세션만 로그아웃 가능 |
| `/api/v1/auth/me` | GET | **JWT 필수** | 본인 정보 조회 |
| `/api/v1/health` | GET | Public | 헬스체크 (모니터링/LB용) |
| `/actuator/**` | GET | Public (내부망) | 운영 메트릭 |

### SecurityConfig 구현

```java
// Gateway SecurityConfig.java
@Bean
public SecurityWebFilterChain securityWebFilterChain(ServerHttpSecurity http) {
    return http
        .authorizeExchange(exchanges -> exchanges
            // ===== Public Endpoints =====
            // 인증 관련 (로그인, 토큰 갱신)
            .pathMatchers(HttpMethod.POST, "/api/v1/auth/login").permitAll()
            .pathMatchers(HttpMethod.POST, "/api/v1/auth/refresh").permitAll()
            
            // 헬스체크 (Load Balancer, Kubernetes Probe)
            .pathMatchers("/api/v1/health").permitAll()
            .pathMatchers("/actuator/health").permitAll()
            .pathMatchers("/actuator/info").permitAll()
            
            // ===== Protected Endpoints =====
            // 인증 관련 (로그아웃, 사용자 정보)
            .pathMatchers(HttpMethod.POST, "/api/v1/auth/logout").authenticated()
            .pathMatchers(HttpMethod.GET, "/api/v1/auth/me").authenticated()
            
            // 그 외 auth 경로 (기본 차단)
            .pathMatchers("/api/v1/auth/**").authenticated()
            
            // ===== 기타 모든 요청 =====
            .anyExchange().authenticated()
        )
        .csrf(csrf -> csrf.disable())  // REST API이므로 CSRF 비활성화
        .oauth2ResourceServer(oauth2 -> oauth2.jwt(Customizer.withDefaults()))
        .build();
}
```

### Logout 엔드포인트 동작

```
[Logout 흐름]

인증된 사용자:
POST /api/v1/auth/logout
Authorization: Bearer <valid_token>
→ 200 OK (세션 종료, 토큰 블랙리스트 등록)

비인증 사용자:
POST /api/v1/auth/logout
(No Authorization header)
→ 401 Unauthorized
```

## 근거

1. **Logout 보안**: 인증된 세션만 종료 가능해야 함
   - 비인가 logout 허용 시 타인 세션 종료 시도 가능
   - 토큰 블랙리스트 등록 시 유효한 토큰 필요

2. **Health 공개**: 모니터링 시스템이 인증 없이 헬스 확인 필요
   - Kubernetes liveness/readiness probe
   - Load Balancer health check
   - 외부 모니터링 도구 (Prometheus, Datadog 등)

3. **최소 권한 원칙**: 필요한 것만 public, 나머지는 protected

## 결과

### 긍정적 영향
- Logout 보안 강화 (SCRUM-56 해결, 3건)
- Health 엔드포인트 정상 접근 (SCRUM-59 해결, 1건)
- 명확한 보안 정책 문서화

### 부정적 영향
- SecurityConfig 규칙 복잡도 증가
- 엔드포인트 추가 시 보안 정책 검토 필요

### 체크리스트

새로운 Auth 엔드포인트 추가 시:
- [ ] 인증 필요 여부 결정
- [ ] SecurityConfig 규칙 추가
- [ ] ADR 업데이트
- [ ] E2E 테스트 케이스 추가

## 관련 이슈

- **SCRUM-56**: Logout 엔드포인트 인증 없이 200 반환 (3건 실패)
- **SCRUM-59**: /api/v1/health 인증 차단 (1건 실패)

## 참고 자료

- [OWASP Session Management](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/06-Session_Management_Testing/)
- [Kubernetes Health Probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)
- [Spring Security Path Matchers](https://docs.spring.io/spring-security/reference/reactive/authorization/authorize-http-requests.html)
