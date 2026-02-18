# 프로젝트 회고: Backend Developer

**역할**: SpringBoot API Gateway / 비즈니스 로직
**참여 기간**: Sprint 2 ~ Sprint 12
**모델**: Sonnet 4.6

---

## 1. Gateway의 무게 -- API 라우팅의 복잡성

Sprint 2에서 처음 Gateway 라우팅 작업(STORY-021)을 할당받았을 때, 단순한 프록시 서버 정도로 생각했다. Frontend에서 들어오는 `/api/v1/**` 요청을 Backend SpringBoot 서비스와 AI Service(FastAPI)로 분배하면 되는 것 아닌가. 그런데 현실은 달랐다.

Spring Cloud Gateway 4.x 위에서 SecurityConfig, JwtAuthenticationFilter, JwtTokenValidator, GatewayRouteConfig를 한꺼번에 올려놓고 보니, 필터 체인 순서 하나가 잘못되면 전체 인증이 무너지는 구조였다. 특히 필터의 실행 순서를 `BEFORE_AUTHENTICATION`으로 설정하는 부분에서 초기에 많은 시행착오를 겪었다. Gateway는 단순한 라우터가 아니라, 모든 요청이 반드시 거치는 관문이었고, 그 관문의 무게는 프로젝트가 진행될수록 무거워졌다.

라우팅 테이블만 해도 그렇다. Knowledge API 8개, Search API 6개, Users API 5개, Bookmarks API 4개, Dashboard API 3개, Export API 2개, Admin API 4개 -- 총 32개 엔드포인트(후에 35개로 늘어난)를 경로별로 올바른 서비스에 매핑해야 했다. `/api/v1/search/**`는 Backend의 SearchService를 거쳐 AI Service로 프록시되어야 하고, `/api/v1/documents`는 Backend에서 직접 처리하되 파일 업로드만큼은 AI Service의 FastAPI 쪽으로 넘겨야 한다. 이 경로 매핑 규칙을 `application.yml`에 선언적으로 정의하면서도, 인증/인가 필터가 정확히 원하는 순서로 동작하도록 만드는 것은 생각보다 정교한 작업이었다.

Sprint 3에서 Backend API 전체 구현(STORY-047, 13 SP)을 맡았을 때가 가장 밀도 높은 기간이었다. Controller 7개, Service 7개, Entity 10개, Repository 9개, DTO 30개 이상을 한꺼번에 만들어야 했다. `Controller -> Service -> Repository`라는 계층 분리 원칙을 철저히 지켰다. Controller에서는 RequestDTO를 받아 도메인 파라미터로 변환한 뒤 Service를 호출하고, Service에서 비즈니스 로직을 처리한 뒤 Repository를 통해 데이터에 접근하는 구조를 빠짐없이 적용했다. 안티패턴 -- Controller에서 Repository를 직접 호출하거나, Service에 RequestDTO를 그대로 전달하는 방식 -- 을 절대 허용하지 않았다. 이 원칙 덕분에 Sprint 12에서 API 명세서 전수 대조를 할 때 구조적 문제는 거의 없었다.

그러나 Gateway 점수가 65점(100점 만점)으로 전체 레이어 중 최하위를 기록한 것은 사실이다. 테스트가 0건이었다는 TechLead의 지적은 뼈아팠다. Gateway 레이어에 SecurityConfigTest나 JwtFilterTest를 작성하지 못한 것은 시간의 문제이기도 했지만, 솔직히 "Gateway는 설정 중심이라 테스트할 게 별로 없다"는 안이한 판단이 있었다. 돌이켜보면 Gateway야말로 모든 요청의 입구이므로 가장 먼저 테스트가 필요한 곳이었다.

---

## 2. Keycloak 통합의 현실

STORY-022(JWT 인증 필터, 3 SP)와 STORY-024(직접 로그인 API, 5 SP)를 Sprint 2에서 맡았다. Keycloak SSO와의 통합은 설계서에서는 깔끔해 보였지만, 실제 구현에서는 예상치 못한 난관이 연속이었다.

가장 큰 도전은 Dual-Token 인증 체계를 구현한 것이다. 시스템은 두 가지 방식의 JWT를 동시에 지원해야 했다: (1) 자체 발급 JWT(HS256 알고리즘, `POST /api/v1/auth/login`으로 발급), (2) Keycloak에서 발급한 OAuth2 토큰(RS256 알고리즘). JwtTokenValidator에서 토큰의 알고리즘을 먼저 확인하고, HS256이면 자체 시크릿으로, RS256이면 Keycloak의 공개키로 검증하는 분기 로직을 만들어야 했다. 이 과정에서 토큰 헤더의 `alg` 필드 파싱, JWKS 엔드포인트에서 공개키 캐싱, 키 로테이션 대응까지 고려해야 했다.

Sprint 4에서 STORY-053(보안 강화, 3 SP)을 맡았을 때 JWT Secret을 환경변수로 분리하는 작업을 했다. 이전까지 `application.yml`에 하드코딩되어 있던 시크릿 키를 `JWT_SECRET` 환경변수로 이동하고, `.env` 파일에서 관리하도록 변경했다. 단순한 작업처럼 보이지만, Gateway, Backend, AI Service 세 곳에서 동일한 시크릿을 공유해야 하는 구조 때문에 Docker Compose의 환경변수 주입 체계와의 정합성을 맞추는 데 꽤 신경을 썼다.

Sprint 8에서 STORY-084(Gateway Keycloak SSO Routing Fix, 3 SP)를 맡았을 때가 Keycloak과의 전쟁이 절정에 달한 시점이었다. UAT(User Acceptance Testing) Part B 과정에서 Gateway를 통한 Keycloak SSO 라우팅이 실패하는 문제가 발견되었다. 직접 Backend 서비스에 접근하면 정상이지만, Gateway를 경유하면 Keycloak realm 설정이 제대로 전달되지 않는 현상이었다. 원인을 추적해 보니 Gateway의 프록시 헤더 설정에서 `X-Forwarded-*` 헤더가 누락되어 Keycloak이 올바른 redirect URI를 생성하지 못하는 문제였다. 이 수정은 겉보기에는 헤더 몇 줄 추가에 불과했지만, 원인 파악까지 상당한 디버깅 시간이 소요되었다.

AI Service(FastAPI)와의 JWT 공유 부분도 까다로웠다. Backend(SpringBoot)에서 검증된 사용자 정보를 AI Service로 전달할 때, Gateway에서 `X-Auth-User-Id`, `X-Auth-User-Role` 같은 커스텀 헤더를 주입하는 방식을 채택했다. 이렇게 하면 AI Service 쪽에서는 JWT를 직접 검증할 필요 없이 Gateway가 이미 검증한 사용자 정보를 신뢰할 수 있다. 하지만 이 방식은 AI Service를 Gateway 없이 직접 호출하면 인증이 우회된다는 약점이 있어, Internal API 경로(`/internal/v1/*`)에 대한 네트워크 수준 격리를 Docker Compose의 네트워크 설정으로 보완해야 했다.

---

## 3. API 35개 엔드포인트 전수 대조

Sprint 12의 마지막 작업 중 하나로 `05_api_specification.md` v1.1 문서와 실제 구현 코드를 1:1로 대조하는 작업이 있었다. 이 작업은 처음에는 단순 확인 작업으로 보였지만, 실제로 진행해 보니 꽤 많은 불일치를 발견했다.

총 35개 엔드포인트를 문서 기준으로 하나씩 코드와 대조한 결과, 인증 관련 10건의 정정 사항이 발견되었다. 문서에는 `인증 필수`로 명시되어 있는데 실제 코드에서는 `permitAll()`로 열려 있거나, 반대로 문서에는 공개 API로 되어 있는데 코드에서는 인증을 요구하는 경우가 있었다. 특히 `GET /api/v1/documents/{id}/status` 엔드포인트가 문서에서는 인증 필수인데 코드에서는 공개로 되어 있는 것은 보안 관점에서 즉시 수정이 필요한 사항이었다.

파라미터 3건의 수정도 발견했다. 페이지네이션 파라미터의 기본값이 문서(page=1, size=20)와 코드(page=0, size=10)에서 다른 경우, 검색 API의 `top_k` 파라미터 범위가 문서(1-20)와 코드(1-50)에서 상이한 경우 등이었다. 이런 미세한 차이는 Frontend 개발자가 API를 호출할 때 예상치 못한 동작을 유발할 수 있다.

이 전수 대조 작업을 하면서 느낀 것은, API 명세서라는 것이 한 번 작성하면 끝이 아니라는 사실이다. 코드가 진화하면 명세서도 함께 갱신되어야 하는데, 12개 스프린트 동안 코드는 계속 변경되면서 명세서는 v1.0 상태에 머물러 있었다. Sprint 12에서야 v1.1로 올린 것은 솔직히 너무 늦었다. 이상적으로는 매 스프린트 종료 시 API 명세서 동기화 작업이 포함되어야 했다.

이 작업에서 35개 엔드포인트의 구성을 다시 정리하면: 인증 API 4개(login, logout, token refresh, token validate), 검색 API 6개(hybrid search, chat search, stream, history, suggestions, feedback), 문서 API 8개(CRUD + status + chunks + categories + projects), Knowledge Graph API 3개(graph data, stats, relationships), 임베딩 API 3개(batch embed, status, single), 추출 API 2개(entities, metadata), 캐시 API 2개(reset, stats), 시스템 API 7개(health, metrics, admin 등). 각각의 인증 요구사항, HTTP 메서드, 경로 패턴, 요청/응답 스키마를 빠짐없이 검증했다.

---

## 4. Resilience4j와 견고성 패턴

Backend 개발에서 가장 자랑스러운 부분은 Resilience4j를 활용한 견고성 패턴의 적용이다. Circuit Breaker, Retry, Rate Limiter 세 가지 패턴을 AI Service 호출 경로에 적용했다.

Circuit Breaker는 AI Service(FastAPI)가 응답하지 않을 때 Backend가 무한정 기다리지 않도록 하는 장치다. 연속 5회 실패 시 회로가 OPEN 상태로 전환되어 요청을 즉시 거부하고, 30초 후 HALF-OPEN 상태에서 3건의 시험 요청을 보내 성공하면 다시 CLOSED 상태로 복귀하는 구조를 설정했다. Retry 패턴은 일시적 네트워크 오류에 대해 최대 3회까지 지수 백오프(1초, 2초, 4초)로 재시도하도록 구성했다.

Sprint 6에서 STORY-066(Gateway Connection Pool 설정, 3 SP)을 맡았을 때, Netty의 Connection Pool 미설정으로 인한 에러가 발생하는 문제를 해결했다. `spring.cloud.gateway.httpclient.pool.max-connections`와 `max-idle-time` 같은 설정을 명시적으로 지정하여 커넥션 풀이 고갈되는 현상을 방지했다. 이 경험은 "기본값에 의존하지 말라"는 교훈을 남겼다.

하지만 아쉬운 점도 있다. Gateway timeout을 120초로 설정해야 하는 요구사항(KI-001, Known Issue)이 프로젝트 종료 시점까지 미적용된 채로 남았다. AI Service의 임베딩 처리가 대용량 문서에서 60초 이상 걸릴 수 있는데, Gateway의 기본 타임아웃이 30초여서 대용량 처리 시 504 Gateway Timeout 에러가 발생할 수 있는 상태다. 이 설정 하나가 아직도 `application.yml`에 반영되지 않은 것은 기술 부채로 기록되었다. `spring.cloud.gateway.httpclient.response-timeout: 120s` 한 줄이면 해결될 문제인데, 다른 작업의 우선순위에 밀려 끝내 처리하지 못했다.

Circuit Breaker 튜닝도 충분하지 못했다. 초기 설정값(실패 임계치 50%, 슬로우 콜 임계치 100%)을 프로덕션 부하 패턴에 맞게 조정하려면 실제 트래픽 데이터가 필요한데, 개발 환경에서는 그런 데이터를 얻기 어려웠다. 결국 "합리적 기본값"으로 남겨둔 채 프로젝트가 종료되었다.

---

## 5. Saga 패턴과 트랜잭션 경계

설계서에서 Saga 패턴 트랜잭션을 정의했지만, 실제로 이 패턴이 본격적으로 필요한 시나리오 -- 예를 들어 문서 업로드 시 PostgreSQL 메타데이터 저장, Elasticsearch 인덱싱, Neo4j 그래프 생성이 모두 성공해야 하는 경우 -- 는 AI Service(Python 쪽) 파이프라인에서 처리되는 구조였기 때문에, Backend(SpringBoot)에서 Saga를 직접 구현할 기회는 많지 않았다.

대신 @Transactional 어노테이션을 통한 단일 서비스 내 트랜잭션 관리에 집중했다. TechLead의 소스코드 리뷰에서 "@Transactional 누락"이 Minor 이슈로 지적된 것은, 서비스 메서드에 트랜잭션 경계를 명시적으로 선언하지 않은 부분이 있었기 때문이다. 읽기 전용 메서드에는 `@Transactional(readOnly = true)`를 적용하고, 쓰기 메서드에는 기본 `@Transactional`을 적용하는 패턴을 후반부에 일괄 적용했다.

WebFlux 기반의 리액티브 프로그래밍을 채택했기 때문에 `Mono`와 `Flux`를 반환하는 메서드에서의 트랜잭션 처리가 전통적인 동기 방식과 달라 초기에 혼란이 있었다. R2DBC를 통한 리액티브 DB 접근과 `@Transactional`의 조합이 기대대로 동작하는지 검증하는 데 시간이 걸렸고, 이 부분은 테스트로 더 보강했어야 했다.

---

## 6. 아쉬운 점과 교훈

### 테스트 부족

소스코드 리뷰 시점(Sprint 2 종료 후) Backend 전체 테스트가 3건에 불과했다. 81개 소스 파일에 테스트 3개. 이것은 변명의 여지가 없는 부족함이다. Sprint 2~3에서 32개 API를 빠르게 구현하는 데 집중하다 보니 테스트 작성을 미뤘고, 그 기술 부채는 Sprint 4~6에 걸쳐 다른 팀원들(QA Engineer)이 Contract Test와 보안 테스트로 메워줘야 했다. Backend 자체 Unit Test와 Integration Test를 Sprint 2~3 시점에 함께 작성했다면 전체 품질이 훨씬 나았을 것이다.

### Gateway timeout 120s 미적용 (KI-001)

프로젝트 종료 시점에 Known Issue로 문서화된 이 항목은, 사실 30분이면 적용 가능한 설정 변경이었다. 하지만 Sprint 8~12 동안 RAGAS 평가, 임베딩 배치, Graph RAG 등 AI 파이프라인 쪽 작업이 우선순위를 차지하면서 Backend의 미세 조정 작업은 계속 뒤로 밀렸다. "사소한 것일수록 빨리 처리하라"는 교훈을 얻었다.

### 명세서 동기화

35개 엔드포인트 전수 대조에서 인증 10건, 파라미터 3건의 불일치가 발견된 것은 명세서 관리의 실패다. 코드와 문서의 동기화는 CI/CD 파이프라인에 OpenAPI 스키마 자동 생성을 포함시키는 방식으로 자동화했어야 했다.

### WebClient 빈 주입 미확인

TechLead 리뷰에서 지적된 "WebClient 빈 주입 미확인" 이슈는, AI Service를 호출하는 WebClient가 올바른 base URL과 타임아웃 설정으로 초기화되는지를 테스트하지 않은 것이다. WebClientConfig 클래스를 별도로 만들어 빈을 정의했지만, 해당 빈이 예상대로 주입되는지 검증하는 Integration Test가 없었다.

---

## 7. 팀원들에게

**RAG Engineer에게**: Backend가 AI Service를 호출할 때 Circuit Breaker와 Retry가 걸려 있다는 것을 기억해 달라. AI Service 쪽에서 응답이 5초 이상 걸리면 Backend에서 슬로우 콜로 집계되고, 누적되면 Circuit Breaker가 열린다. Gateway timeout 120s 이슈(KI-001)도 결국 AI Service의 임베딩 처리 시간 때문에 나온 것이다. 이 두 시스템 사이의 타임아웃 체인을 다음 담당자가 반드시 정리해 주면 좋겠다.

**Frontend Developer에게**: API 응답 형식을 일관되게 유지하려고 노력했지만, 일부 엔드포인트에서 에러 응답 형식이 불일치하는 부분이 있었다. GlobalExceptionHandler가 대부분의 케이스를 잡지만, Gateway 레벨에서 발생하는 에러(401, 403, 504)는 별도의 형식으로 내려간다. 프론트엔드에서 에러 처리 시 이 점을 감안해 달라.

**QA Engineer에게**: Contract Test 62건에서 121건으로 확장해 준 것, OWASP Top 10 보안 테스트 35건을 작성해 준 것에 감사한다. Backend 레이어의 테스트 부족을 QA 쪽에서 메워준 덕분에 전체 품질이 유지되었다.

**PM에게**: Sprint 3에서 13 SP짜리 STORY-047(Backend API 32개 전체 구현)을 단기간에 완료한 것은, PM이 적절한 타이밍에 작업을 할당하고 블로커를 빠르게 에스컬레이션해 준 덕분이다. 특히 Sprint 4 Day 4에서 SCRUM-57(LoginResponse @JsonProperty 누락) 해결이 14건의 E2E 테스트 실패를 연쇄 해결한 것은, TechLead의 근본원인 분석과 PM의 빠른 조율이 합쳐진 결과였다.

**TechLead에게**: 소스코드 리뷰에서 Backend 72점, Gateway 65점이라는 냉정한 평가를 받았다. 그 피드백이 없었다면 Connection Pool 설정이나 @Transactional 누락 같은 문제를 방치했을 것이다. ADR-001(직렬화 규칙), ADR-002(검색 API 인증 정책), ADR-003(Auth 보안 강화)를 문서화하면서 설계 결정의 근거를 남긴 것도 TechLead의 리뷰 문화 덕분이다.

---

## 8. 숫자로 보는 41일

- **담당 스토리**: STORY-021, 022, 024, 047, 044, 053, 066, 084 등
- **총 스토리 포인트**: 약 55 SP (직접 담당 기준)
- **구현 엔드포인트**: 35개
- **Controller**: 7개 (Search, Document, User, Bookmark, Dashboard, Export, Admin)
- **Entity**: 10개 (User, Document, Chunk, Bookmark, SearchHistory, Category, Project 등)
- **Repository**: 9개
- **DTO**: 30개 이상
- **Gateway 라우팅 규칙**: 12개 route predicate
- **소스코드 리뷰 점수**: Gateway 65, Backend 72 (전체 평균 72.5, B+)
- **Known Issue**: 1건 (KI-001 Gateway Timeout 120s)
- **기술 부채 해결**: STORY-066(Connection Pool), STORY-070(Keycloak 토큰 인터페이스) 기여

41일 동안 Gateway와 Backend를 책임졌다. 완벽하지 않았지만, 32개에서 35개로 늘어난 API 엔드포인트 하나하나에 `Controller -> Service -> Repository` 계층 원칙을 지키며 코드를 쌓았다. Resilience4j Circuit Breaker가 AI Service 장애를 감싸 안고, Keycloak Dual-Token 인증이 모든 요청을 검문하는 이 Gateway를 다음 스프린트에 맡을 누군가가, 남겨진 KI-001을 반드시 마무리해 주기를 바란다. 그 한 줄의 timeout 설정이 이 시스템의 마지막 퍼즐이다.

---

*작성: Backend Developer Agent (Sonnet 4.6) | 2026-02-19*
