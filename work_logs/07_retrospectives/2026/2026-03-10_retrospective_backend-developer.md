# 프로젝트 회고 — Backend Developer

**프로젝트**: Hybrid RAG Knowledge Platform 고도화
**기간**: 2026-01-10 ~ 2026-03-10
**역할**: Spring Cloud Gateway 구현, Keycloak SSO 통합, JWT 인증/인가, API 라우팅

---

## 1. 내가 기여한 것 (What I Did)

- **Spring Cloud Gateway 구현**: API Gateway 패턴을 적용하여 모든 마이크로서비스로의 라우팅을 중앙 집중 관리했습니다. `/api/v1/auth/**`, `/api/v1/search/**`, `/api/v1/knowledge/**` 등 주요 경로를 설계하고 구현했습니다.
- **Keycloak SSO 통합**: Keycloak과 Spring Security를 연동하여 OAuth2/OIDC 기반 인증을 구현했습니다. 관리자/일반 사용자 역할 분리와 리소스 서버 설정을 완료했습니다.
- **JWT 인증 필터**: Gateway 레벨에서 JWT 토큰 검증 필터를 구현하여, 모든 요청이 인증을 거치도록 했습니다. `accessToken`(camelCase) 응답 필드명 표준을 확립했습니다.
- **Resilience4j 장애 대응**: Circuit Breaker, Rate Limiter, Retry 패턴을 Gateway에 적용하여 하위 서비스 장애 시에도 안정적으로 동작하도록 했습니다.
- **타임아웃 체인 설계**: Nginx(180s) -> Gateway(180s) -> Reranker(60s) + LLM(60s)의 타임아웃 체인을 구성하여 요청이 무한 대기하지 않도록 했습니다.

## 2. 잘된 점 (What Went Well)

- **인증 아키텍처 안정성**: Keycloak + JWT + Gateway 조합이 안정적으로 동작하여, 프로젝트 후반부에 인증 관련 장애가 한 건도 없었습니다.
- **Gateway 라우팅 확장성**: 새로운 서비스가 추가될 때 application.yml에 라우트만 추가하면 되는 구조로 설계하여, AI Service 연동 시 10분 만에 라우팅을 완료할 수 있었습니다.

## 3. 아쉬운 점 (What Could Be Better)

- **API 버저닝 전략 미비**: `/api/v1/` 경로만 사용했는데, v2 전환 시나리오를 미리 고려하지 못했습니다. 향후 버전 공존 전략을 사전에 설계했으면 좋았을 것입니다.
- **Gateway 통합 테스트 부족**: 단위 테스트는 충분했지만, Gateway를 경유하는 End-to-End 통합 테스트가 부족하여 일부 라우팅 이슈를 늦게 발견한 경우가 있었습니다.
- **에러 응답 표준화 지연**: 서비스별로 에러 응답 형식이 달랐는데, Gateway에서 통일된 에러 형식으로 변환하는 작업이 프로젝트 후반에야 이루어졌습니다.

## 4. 배운 점 (What I Learned)

- **Spring Cloud Gateway의 WebFlux 기반**: 기존 Spring MVC와 다른 리액티브 프로그래밍 패러다임을 학습했습니다. 블로킹 코드를 피하는 것이 Gateway 성능에 결정적이라는 것을 체감했습니다.
- **타임아웃 체인의 중요성**: 각 계층별 타임아웃이 정합적이지 않으면 불필요한 대기나 조기 타임아웃이 발생합니다. Nginx -> Gateway -> Service 간 타임아웃을 체계적으로 설계하는 법을 배웠습니다.

## 5. 다음 프로젝트에 바라는 점

- API Gateway 계층에 대한 부하 테스트를 Sprint 초기에 수행하여, 병목 구간을 조기에 식별하고 싶습니다.
- OpenAPI 3.0 스펙을 Gateway에서 자동 집계하여, 통합 API 문서를 제공하는 기능을 구현하고 싶습니다.

## 6. 팀원들에게 한마디

Backend에서 Gateway를 구축하면서, 결국 모든 서비스가 이 한 지점을 거쳐간다는 책임감을 크게 느꼈습니다. Infra가 안정적인 Docker 환경을 제공해주고, RAG Engineer가 AI Service API를 깔끔하게 설계해 준 덕분에 Gateway 연동이 수월했습니다. 특히 DB Designer와의 협업으로 accessToken 필드명 같은 사소하지만 중요한 표준을 일찍 잡을 수 있었습니다. 좋은 팀이었습니다.
