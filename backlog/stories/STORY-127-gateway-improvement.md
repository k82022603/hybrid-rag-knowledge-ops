# STORY-127: Gateway 구조 개선 (65점 → 75+ 목표)

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | - |
| **Epic** | Backend 안정화 |
| **Status** | To Do |
| **Priority** | P2 |
| **Story Points** | 5 |
| **Assignee** | Backend/TechLead |
| **Sprint** | Sprint 09 |

---

## 배경

TechLead 코드 품질 평가: API Gateway 현재 65점 (B-).

### 주요 문제점

| 문제 | 현황 | 목표 |
|------|------|------|
| SSE 응답 처리 | 타임아웃 설정 미비 | 적절한 타임아웃 설정 |
| 에러 응답 형식 | 서비스별 불일치 | 통일된 ErrorResponse |
| Resilience4j | Circuit Breaker 기본값 사용 | 서비스별 튜닝 |
| 라우팅 설정 | application.yml 비대화 | 모듈화 |

Backend Engineer 보고: SSE는 이미 구현됨. 타임아웃·에러 형식 개선 필요.

---

## User Story

**As a** API 소비자,
**I want** Gateway가 일관된 에러 형식과 적절한 타임아웃으로 응답하기를,
**So that** 서비스 장애 시 빠른 원인 파악과 안정적인 폴백이 가능하다.

---

## Acceptance Criteria

- [ ] 통일된 `ErrorResponse` DTO 적용 (모든 Gateway 오류 응답)
- [ ] SSE 엔드포인트 타임아웃 별도 설정 (기본 30s → SSE 300s)
- [ ] Resilience4j Circuit Breaker 서비스별 튜닝 (AI Service / Knowledge Service 분리)
- [ ] Gateway 라우팅 설정 모듈화 (RouteLocator Bean 분리)
- [ ] TechLead 코드 리뷰 후 최종 점수 75+ 확인

---

## Tasks

- [ ] `ErrorResponse` 공통 DTO 정의 및 GlobalExceptionHandler 적용
- [ ] SSE 라우팅 타임아웃 분리 설정 (`/api/v1/search/stream/**`)
- [ ] `CircuitBreakerConfig` ai-service / knowledge-service 분리 정의
- [ ] `application.yml` 라우팅 설정 → `GatewayRouteConfig.java` 분리
- [ ] TechLead 리뷰 요청 및 점수 재측정

---

## 기술 노트

### 영향 범위
- `gateway/src/main/java/com/hrkp/gateway/config/GatewayRouteConfig.java` (신규)
- `gateway/src/main/java/com/hrkp/gateway/exception/GlobalExceptionHandler.java`
- `gateway/src/main/resources/application.yml` (SSE 타임아웃 분리)
- `gateway/src/main/java/com/hrkp/gateway/config/ResilienceConfig.java`

### Resilience4j 목표 설정

```yaml
# AI Service (느린 LLM 응답 허용)
ai-service:
  slidingWindowSize: 10
  failureRateThreshold: 50
  waitDurationInOpenState: 30s

# Knowledge Service (빠른 응답 기대)
knowledge-service:
  slidingWindowSize: 20
  failureRateThreshold: 30
  waitDurationInOpenState: 15s
```

---

## 의존성

- **선행**: 없음
- **관련**: STORY-089 (Gateway 문서 동기화 API 연계), TechLead 리뷰 필수
