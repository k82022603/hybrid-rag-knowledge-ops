# STORY-021: API Gateway 라우팅 구현

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-22 |
| **Epic** | EPIC-001 |
| **Status** | **Done** ✅ (2026-01-24) |
| **Priority** | High |
| **Story Points** | 5 |
| **Assignee** | Backend |
| **Sprint** | 2 |

---

## User Story

**As a** 시스템 관리자,
**I want** API Gateway가 요청을 적절한 서비스로 라우팅,
**So that** 클라이언트는 단일 진입점으로 모든 서비스에 접근 가능함.

---

## Acceptance Criteria

- [ ] **Given** Frontend에서 `/api/v1/*` 요청, **When** API Gateway 수신, **Then** Backend Service로 라우팅
- [ ] **Given** Frontend에서 `/internal/v1/*` 요청, **When** API Gateway 수신, **Then** AI Service로 라우팅
- [ ] **Given** 인증 실패 요청, **When** API Gateway 수신, **Then** 401 Unauthorized 반환
- [ ] **Given** 존재하지 않는 경로, **When** API Gateway 수신, **Then** 404 Not Found 반환
- [ ] **Given** 서비스 장애 시, **When** 요청 라우팅, **Then** Circuit Breaker 동작 및 fallback 응답

---

## Tasks

- [ ] Spring Cloud Gateway 의존성 추가
- [ ] RouteLocator 설정 (`application.yml`)
- [ ] 서비스별 라우팅 규칙 정의
- [ ] CORS 설정
- [ ] Rate Limiting (Resilience4j) 적용
- [ ] Circuit Breaker 설정
- [ ] 단위/통합 테스트 작성
- [ ] API 문서 업데이트

---

## 기술 노트

### 라우팅 규칙

```yaml
# application.yml
spring:
  cloud:
    gateway:
      routes:
        # Backend Service
        - id: backend-service
          uri: lb://backend-service
          predicates:
            - Path=/api/v1/**
          filters:
            - StripPrefix=0
            - name: CircuitBreaker
              args:
                name: backendCircuitBreaker
                fallbackUri: forward:/fallback/backend

        # AI Service (Internal API)
        - id: ai-service
          uri: lb://ai-service
          predicates:
            - Path=/internal/v1/**
          filters:
            - StripPrefix=0
            - name: CircuitBreaker
              args:
                name: aiServiceCircuitBreaker
                fallbackUri: forward:/fallback/ai-service

        # Health Check
        - id: health
          uri: no://op
          predicates:
            - Path=/health
          filters:
            - SetStatus=200
```

### Rate Limiting 설정

```yaml
spring:
  cloud:
    gateway:
      filter:
        request-rate-limiter:
          redis-rate-limiter:
            replenish-rate: 100
            burst-capacity: 200
            requested-tokens: 1
```

### 영향 범위
- `backend/api-gateway/src/main/resources/application.yml`
- `backend/api-gateway/src/main/java/.../config/GatewayConfig.java`
- `backend/api-gateway/src/main/java/.../filter/AuthFilter.java`

---

## 테스트 계획

- [ ] Unit Test: 라우팅 규칙 검증
- [ ] Integration Test: Backend Service 라우팅
- [ ] Integration Test: AI Service 라우팅
- [ ] Integration Test: Circuit Breaker 동작
- [ ] Load Test: Rate Limiting 동작

---

## 참고 자료

- [API 통합 설계서](../../knowledge_service/docs/02_design/04_api_integration_design.md)
- [Spring Cloud Gateway 문서](https://spring.io/projects/spring-cloud-gateway)
- [Resilience4j Circuit Breaker](https://resilience4j.readme.io/docs/circuitbreaker)
