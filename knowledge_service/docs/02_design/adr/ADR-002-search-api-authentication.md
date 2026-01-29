# ADR-002: 검색 API 인증 정책 (JWT 필수)

## 상태
Accepted

## 일자
2026-01-29

## 컨텍스트

Sprint 04 Day 3 Docker E2E 테스트에서 **검색 API(/api/v1/search/**)의 JWT 인증 정책 불일치**로 6건의 테스트가 실패했습니다 (SCRUM-55).

### 문제 상황

```
사용자 요청
    |
    v
[Frontend] --- GET /api/v1/search/query?q=xxx ---> [Gateway]
                                                      |
                              ┌───────────────────────┴───────────────────────┐
                              |                                               |
                        [기존 설정]                                     [테스트 기대]
                    SecurityConfig에서                              JWT 필수 인증
                    permitAll() 허용                                401 Unauthorized
```

Gateway SecurityConfig에서 `/api/v1/search/**` 경로가 `permitAll()`로 설정되어 있어, 인증 없이 데이터 접근이 가능한 보안 취약점이 존재했습니다.

### 보안 위험

| 위험 | 설명 | 심각도 |
|------|------|--------|
| 데이터 노출 | 비인가 사용자가 검색 결과 조회 가능 | High |
| 사용량 추적 불가 | 사용자별 API 사용량 모니터링 불가 | Medium |
| Rate Limiting 우회 | 익명 요청으로 Rate Limit 우회 가능 | Medium |

## 결정

**모든 데이터 접근 API는 JWT 인증을 필수로 요구합니다.**

### 인증 정책 매트릭스

| 엔드포인트 패턴 | 인증 | 이유 |
|----------------|------|------|
| `/api/v1/auth/login` | Public | 로그인 엔드포인트 |
| `/api/v1/auth/refresh` | Public | 토큰 갱신 (refresh token 검증) |
| `/api/v1/auth/logout` | **JWT 필수** | 인증된 세션 종료 |
| `/api/v1/auth/me` | **JWT 필수** | 사용자 정보 조회 |
| `/api/v1/search/**` | **JWT 필수** | 데이터 검색 |
| `/api/v1/documents/**` | **JWT 필수** | 문서 CRUD |
| `/api/v1/knowledge/**` | **JWT 필수** | 지식 그래프 접근 |
| `/api/v1/health` | Public | 헬스체크 (모니터링용) |
| `/actuator/**` | Public (내부망) | 운영 모니터링 |

### SecurityConfig 구현

```java
// Gateway SecurityConfig.java
@Bean
public SecurityWebFilterChain securityWebFilterChain(ServerHttpSecurity http) {
    return http
        .authorizeExchange(exchanges -> exchanges
            // Public endpoints (인증 불필요)
            .pathMatchers("/api/v1/auth/login", "/api/v1/auth/refresh").permitAll()
            .pathMatchers("/api/v1/health", "/actuator/**").permitAll()
            
            // Protected endpoints (JWT 필수)
            .pathMatchers("/api/v1/auth/logout", "/api/v1/auth/me").authenticated()
            .pathMatchers("/api/v1/search/**").authenticated()
            .pathMatchers("/api/v1/documents/**").authenticated()
            .pathMatchers("/api/v1/knowledge/**").authenticated()
            
            // 그 외 모든 요청 인증 필수
            .anyExchange().authenticated()
        )
        .oauth2ResourceServer(oauth2 -> oauth2.jwt(Customizer.withDefaults()))
        .build();
}
```

## 근거

1. **보안 원칙 (Zero Trust)**: 모든 데이터 접근은 인증된 사용자만 허용
2. **사용량 추적**: 사용자별 API 호출 로깅 및 분석 가능
3. **Rate Limiting**: 사용자 식별을 통한 효과적인 Rate Limit 적용
4. **감사 로그**: 누가 언제 어떤 데이터에 접근했는지 추적 가능
5. **보안 정책 확정**: 사용자 승인 완료 (2026-01-28)

## 결과

### 긍정적 영향
- 데이터 접근 보안 강화
- API 사용량 사용자별 추적 가능
- 효과적인 Rate Limiting 적용
- SCRUM-55 관련 6건 E2E 테스트 해결

### 부정적 영향
- 모든 검색 요청에 JWT 토큰 필요 (Frontend 수정)
- 토큰 만료 시 UX 고려 필요 (자동 갱신 로직)

### 예외 처리

| 상황 | 처리 방법 |
|------|----------|
| 토큰 만료 | 401 + `WWW-Authenticate: Bearer` 헤더 반환 |
| 토큰 없음 | 401 Unauthorized |
| 권한 부족 | 403 Forbidden |

## 관련 이슈

- **SCRUM-55**: Gateway 검색 API JWT 인증 정책 불일치 (6건 실패)
- **Sprint 04 Day 3**: 보안 정책 확정 회의 (2026-01-28)

## 참고 자료

- [OWASP API Security](https://owasp.org/API-Security/)
- [OAuth 2.0 Bearer Token](https://datatracker.ietf.org/doc/html/rfc6750)
- [Spring Security WebFlux](https://docs.spring.io/spring-security/reference/reactive/index.html)
