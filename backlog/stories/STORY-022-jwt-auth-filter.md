# STORY-022: JWT 인증 필터

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-23 |
| **Epic** | EPIC-001 |
| **Status** | **Done** ✅ (2026-01-24) |
| **Priority** | High |
| **Story Points** | 3 |
| **Assignee** | Backend |
| **Sprint** | 2 |

---

## User Story

**As a** 보안 관리자,
**I want** API Gateway에서 JWT 토큰을 검증,
**So that** 인증된 사용자만 보호된 API에 접근 가능함.

---

## Acceptance Criteria

- [ ] **Given** 유효한 JWT 토큰, **When** API 요청, **Then** 요청이 백엔드로 전달됨
- [ ] **Given** 만료된 JWT 토큰, **When** API 요청, **Then** 401 Unauthorized 반환 (토큰 만료 메시지)
- [ ] **Given** 잘못된 서명의 JWT, **When** API 요청, **Then** 401 Unauthorized 반환 (서명 검증 실패)
- [ ] **Given** JWT 토큰 없음, **When** 보호된 API 요청, **Then** 401 Unauthorized 반환
- [ ] **Given** 공개 API 경로 (`/health`, `/api/v1/public/*`), **When** 토큰 없이 요청, **Then** 정상 응답

---

## Tasks

- [ ] Spring Security + OAuth2 Resource Server 설정
- [ ] Keycloak JWT 공개키 연동
- [ ] JwtAuthenticationFilter 구현
- [ ] 공개 경로 화이트리스트 설정
- [ ] 에러 응답 표준화 (`ErrorResponse`)
- [ ] 단위 테스트 작성
- [ ] 통합 테스트 작성

---

## 기술 노트

### Security 설정

```java
@Configuration
@EnableWebFluxSecurity
public class SecurityConfig {

    @Bean
    public SecurityWebFilterChain securityWebFilterChain(ServerHttpSecurity http) {
        return http
            .csrf(ServerHttpSecurity.CsrfSpec::disable)
            .authorizeExchange(exchanges -> exchanges
                // 공개 경로
                .pathMatchers("/health", "/ready", "/metrics").permitAll()
                .pathMatchers("/api/v1/public/**").permitAll()
                // 보호 경로
                .pathMatchers("/api/v1/**").authenticated()
                .pathMatchers("/internal/v1/**").authenticated()
                .anyExchange().denyAll()
            )
            .oauth2ResourceServer(oauth2 -> oauth2
                .jwt(jwt -> jwt
                    .jwtDecoder(jwtDecoder())
                )
            )
            .build();
    }

    @Bean
    public ReactiveJwtDecoder jwtDecoder() {
        return ReactiveJwtDecoders.fromIssuerLocation(
            "http://keycloak:8080/realms/hybrid-rag"
        );
    }
}
```

### JWT 클레임 추출

```java
@Component
public class JwtClaimsExtractor {

    public String getUserId(Jwt jwt) {
        return jwt.getClaimAsString("sub");
    }

    public String getUsername(Jwt jwt) {
        return jwt.getClaimAsString("preferred_username");
    }

    public List<String> getRoles(Jwt jwt) {
        Map<String, Object> realmAccess = jwt.getClaimAsMap("realm_access");
        if (realmAccess != null) {
            return (List<String>) realmAccess.get("roles");
        }
        return Collections.emptyList();
    }
}
```

### 영향 범위
- `backend/api-gateway/src/main/java/.../config/SecurityConfig.java`
- `backend/api-gateway/src/main/java/.../filter/JwtAuthenticationFilter.java`
- `backend/api-gateway/src/main/java/.../util/JwtClaimsExtractor.java`

---

## 테스트 계획

- [ ] Unit Test: JWT 파싱 및 검증
- [ ] Unit Test: 클레임 추출
- [ ] Integration Test: 유효 토큰으로 API 접근
- [ ] Integration Test: 무효 토큰 거부
- [ ] Integration Test: 공개 경로 접근

---

## 참고 자료

- [인증/인가 상세 설계서](../../knowledge_service/docs/02_design/03_authentication_authorization_detailed_design.md)
- [Spring Security OAuth2 Resource Server](https://docs.spring.io/spring-security/reference/servlet/oauth2/resource-server/index.html)
- [Keycloak Token Validation](https://www.keycloak.org/docs/latest/securing_apps/#validating-access-tokens)
