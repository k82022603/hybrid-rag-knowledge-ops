# API 아키텍처 설계 방향 검토

---

## 문서 정보

| 항목 | 내용 |
|------|------|
| **문서명** | API 아키텍처 설계 방향 검토 |
| **버전** | 1.0 |
| **작성일** | 2026-01-16 |
| **작성자** | Claude AI |
| **상태** | 검토 완료 |

---

## 1. 검토 배경

### 1.1 검토 목적

Hybrid RAG Knowledge Platform의 API 연동 아키텍처를 설계하기 위해 Spring Cloud 솔루션 사용 여부와 최적의 아키텍처 옵션을 검토합니다.

### 1.2 검토 범위

- Spring Cloud 구성 요소 사용 여부
- API Gateway 구성 방안
- 서비스 간 통신 패턴
- 장애 대응 전략

### 1.3 시스템 구성

```
┌─────────────────────────────────────────────────────────────┐
│                     시스템 구성도                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   [Frontend]  ───▶  [Gateway]  ───▶  [Backend]              │
│   React 18          Spring Cloud     SpringBoot 3.x         │
│                     Gateway                                 │
│                                          │                  │
│                                          ▼                  │
│                                    [AI Service]             │
│                                    FastAPI + LangGraph      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Spring Cloud 구성 요소 검토

### 2.1 검토 대상 구성 요소

| 구성 요소 | 역할 | 검토 결과 |
|----------|------|----------|
| **Spring Cloud Gateway** | API Gateway, 라우팅, 인증 | **사용** |
| **Spring Cloud Eureka** | 서비스 디스커버리 | 미사용 |
| **Spring Cloud Config** | 중앙 집중식 설정 관리 | 미사용 |
| **Resilience4j** | Circuit Breaker, Rate Limiter | **사용** |
| **Spring Cloud Sleuth** | 분산 추적 | 선택적 사용 |

### 2.2 상세 검토

#### 2.2.1 Spring Cloud Gateway - 사용

**사용 이유:**
- Keycloak OAuth 2.0 통합에 최적화
- 라우팅, 필터링, Rate Limiting 기본 제공
- Reactive 기반으로 높은 성능
- Spring Security와 자연스러운 통합

**주요 기능:**
```yaml
# 라우팅 예시
spring:
  cloud:
    gateway:
      routes:
        - id: backend-api
          uri: lb://backend-service
          predicates:
            - Path=/api/v1/**
          filters:
            - TokenRelay
            - name: CircuitBreaker
              args:
                name: backendCircuitBreaker
                fallbackUri: forward:/fallback
```

#### 2.2.2 Spring Cloud Eureka - 미사용

**미사용 이유:**
- 서비스 수가 적음 (Backend 1개, AI Service 1개)
- Docker Compose 환경에서 서비스명으로 직접 통신 가능
- 운영 복잡도 증가 대비 이점 부족
- Kubernetes 배포 시 K8s Service Discovery 활용 가능

**대안:**
```yaml
# Docker Compose 서비스 디스커버리
services:
  backend:
    networks:
      - app-network
  ai-service:
    networks:
      - app-network

# application.yml
ai-service:
  url: http://ai-service:8000  # Docker 서비스명 직접 사용
```

#### 2.2.3 Spring Cloud Config - 미사용

**미사용 이유:**
- 단일 환경 (개발/스테이징/운영) 설정은 환경변수로 충분
- 설정 변경 빈도가 낮음
- Config Server 운영 부담
- Docker Compose / K8s ConfigMap으로 대체 가능

**대안:**
```yaml
# Docker Compose 환경변수
services:
  backend:
    environment:
      - SPRING_PROFILES_ACTIVE=${ENVIRONMENT}
      - DATABASE_URL=${DATABASE_URL}
      - AI_SERVICE_URL=http://ai-service:8000

# Kubernetes ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: backend-config
data:
  SPRING_PROFILES_ACTIVE: "production"
  AI_SERVICE_URL: "http://ai-service:8000"
```

#### 2.2.4 Resilience4j - 사용

**사용 이유:**
- AI Service 호출 시 타임아웃/장애 대응 필수
- LLM API 응답 지연에 대한 Circuit Breaker 필요
- Rate Limiting으로 AI 비용 제어

**설정 예시:**
```yaml
resilience4j:
  circuitbreaker:
    instances:
      aiService:
        slidingWindowSize: 10
        failureRateThreshold: 50
        waitDurationInOpenState: 30s
        permittedNumberOfCallsInHalfOpenState: 3

  timelimiter:
    instances:
      aiService:
        timeoutDuration: 60s  # LLM 응답 대기

  retry:
    instances:
      aiService:
        maxAttempts: 3
        waitDuration: 1s
        retryExceptions:
          - java.io.IOException
          - java.util.concurrent.TimeoutException
```

---

## 3. 아키텍처 옵션 비교

### 3.1 Option A: Full Spring Cloud

```
┌─────────────────────────────────────────────────────────────┐
│                    Option A: Full Spring Cloud               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌──────────────┐    ┌──────────────┐                      │
│   │ Config Server│    │    Eureka    │                      │
│   └──────┬───────┘    └──────┬───────┘                      │
│          │                   │                              │
│          ▼                   ▼                              │
│   ┌──────────────────────────────────────┐                  │
│   │          Spring Cloud Gateway         │                  │
│   └──────────────────┬───────────────────┘                  │
│                      │                                      │
│          ┌───────────┴───────────┐                          │
│          ▼                       ▼                          │
│   ┌─────────────┐         ┌─────────────┐                   │
│   │   Backend   │ ──────▶ │ AI Service  │                   │
│   └─────────────┘         └─────────────┘                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘

장점:
- 완전한 마이크로서비스 인프라
- 동적 서비스 등록/해제
- 중앙 집중식 설정 관리
- 대규모 확장에 유리

단점:
- 운영 복잡도 높음 (서비스 5개)
- 리소스 오버헤드 (16GB RAM 환경에서 부담)
- 현재 서비스 수 대비 과도한 인프라
- 학습 곡선 가파름
```

### 3.2 Option B: Simplified (Gateway 없음)

```
┌─────────────────────────────────────────────────────────────┐
│                 Option B: Simplified                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────────┐                                           │
│   │  Frontend   │                                           │
│   └──────┬──────┘                                           │
│          │                                                  │
│          ▼                                                  │
│   ┌─────────────┐         ┌─────────────┐                   │
│   │   Backend   │ ──────▶ │ AI Service  │                   │
│   │ (직접 노출) │         └─────────────┘                   │
│   └─────────────┘                                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘

장점:
- 가장 단순한 구조
- 최소 리소스 사용
- 빠른 구현

단점:
- API Gateway 기능 직접 구현 필요
- Keycloak 통합 복잡
- 보안 헤더, Rate Limiting 직접 구현
- 확장성 제한
```

### 3.3 Option C: Middle Ground (선택됨)

```
┌─────────────────────────────────────────────────────────────┐
│                 Option C: Middle Ground ✓                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────────┐                                           │
│   │  Frontend   │                                           │
│   └──────┬──────┘                                           │
│          │ HTTPS                                            │
│          ▼                                                  │
│   ┌──────────────────────────────────────┐                  │
│   │      Spring Cloud Gateway            │                  │
│   │  + Keycloak OAuth 2.0 통합           │                  │
│   │  + Rate Limiting                     │                  │
│   └──────────────────┬───────────────────┘                  │
│                      │                                      │
│                      ▼                                      │
│   ┌─────────────────────────────────────┐                   │
│   │            Backend                   │                   │
│   │  + Resilience4j Circuit Breaker     │                   │
│   │  + WebClient (AI Service 호출)      │                   │
│   └──────────────────┬──────────────────┘                   │
│                      │ HTTP/mTLS                            │
│                      ▼                                      │
│   ┌─────────────────────────────────────┐                   │
│   │          AI Service                  │                   │
│   │  FastAPI + LangGraph                │                   │
│   └─────────────────────────────────────┘                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘

장점:
- 적절한 복잡도와 기능성 균형
- Gateway에서 인증/보안 처리
- Circuit Breaker로 장애 격리
- Docker Compose로 간편한 운영
- 16GB RAM 환경에 적합

단점:
- Eureka 없이 수동 서비스 URL 관리
- 설정 변경 시 재배포 필요 (Config Server 없음)

채택 이유:
- 현재 서비스 규모에 적합
- 필수 기능만 포함하여 운영 단순화
- 향후 확장 시 Eureka/Config 추가 가능
```

---

## 4. 선택된 아키텍처 상세

### 4.1 구성 요소 요약

| 구성 요소 | 사용 여부 | 역할 |
|----------|----------|------|
| **Spring Cloud Gateway** | O | API Gateway, 인증, 라우팅 |
| **Spring Cloud Eureka** | X | Docker Compose 서비스명 사용 |
| **Spring Cloud Config** | X | 환경변수로 대체 |
| **Resilience4j** | O | Circuit Breaker, Retry, Rate Limit |

### 4.2 통신 흐름

```
1. Frontend → Gateway
   - HTTPS (TLS 1.3)
   - OAuth 2.0 Access Token 전달

2. Gateway → Backend
   - HTTP (내부 네트워크)
   - JWT 토큰 전달 (TokenRelay)

3. Backend → AI Service
   - HTTP 또는 mTLS
   - WebClient + Resilience4j
   - 내부 API Key 인증

4. Gateway ↛ AI Service
   - Gateway는 AI Service 직접 호출 안함
   - 모든 AI 요청은 Backend 경유
```

### 4.3 서비스 디스커버리

```yaml
# docker-compose.yml
services:
  gateway:
    image: gateway:latest
    environment:
      - BACKEND_URL=http://backend:8080
    networks:
      - app-network

  backend:
    image: backend:latest
    environment:
      - AI_SERVICE_URL=http://ai-service:8000
    networks:
      - app-network

  ai-service:
    image: ai-service:latest
    networks:
      - app-network

networks:
  app-network:
    driver: bridge
```

### 4.4 장애 대응 전략

```java
// Backend에서 AI Service 호출
@Service
public class AIServiceClient {

    private final WebClient webClient;

    @CircuitBreaker(name = "aiService", fallbackMethod = "searchFallback")
    @Retry(name = "aiService")
    @TimeLimiter(name = "aiService")
    public Mono<SearchResponse> search(SearchRequest request) {
        return webClient.post()
            .uri("/api/v1/search/hybrid")
            .bodyValue(request)
            .retrieve()
            .bodyToMono(SearchResponse.class);
    }

    // Fallback: 캐시된 결과 또는 기본 응답
    public Mono<SearchResponse> searchFallback(SearchRequest request, Throwable t) {
        log.warn("AI Service unavailable, using fallback: {}", t.getMessage());
        return Mono.just(SearchResponse.empty());
    }
}
```

---

## 5. 향후 확장 경로

### 5.1 서비스 확장 시

```
현재 (Option C)          →    향후 (필요 시)
─────────────────────────────────────────────
Gateway                       Gateway
Backend                       Backend (다중 인스턴스)
AI Service                    AI Service (다중 인스턴스)
                              + Eureka Server
                              + Config Server
```

### 5.2 확장 트리거

| 트리거 | 추가 구성 요소 |
|--------|---------------|
| 서비스 인스턴스 3개 이상 | Eureka Server |
| 환경별 설정 복잡화 | Config Server |
| 분산 추적 필요 | Zipkin + Sleuth |
| 이벤트 기반 통신 필요 | Kafka / RabbitMQ |

---

## 6. 결론

### 6.1 최종 결정

**Option C (Middle Ground)** 채택

### 6.2 핵심 포인트

1. **Spring Cloud Gateway**: 필수 - Keycloak 통합, 보안, 라우팅
2. **Eureka/Config**: 불필요 - Docker Compose로 충분
3. **Resilience4j**: 필수 - AI Service 장애 대응
4. **Gateway → AI Service 직접 호출**: 없음 - Backend 경유

### 6.3 리소스 영향

| 구성 | 예상 메모리 |
|------|-----------|
| Gateway | 512MB ~ 1GB |
| Backend | 1GB ~ 2GB |
| AI Service | 2GB ~ 4GB |
| **합계** | **3.5GB ~ 7GB** (16GB 중) |

나머지 리소스는 PostgreSQL, Elasticsearch, Neo4j, Keycloak에 할당됩니다.

---

## 7. 관련 문서

- [API 통합 설계서](../api_integration_design.md)
- [인증/권한 설계서](../authentication_authorization_detailed_design.md)
- [상세 설계서](../hybrid_rag_platform_detailed_design.md)

---

**문서 끝**
