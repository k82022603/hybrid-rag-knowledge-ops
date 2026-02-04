# Circuit Breaker 운영 매뉴얼

**Version**: 1.0
**Last Updated**: 2026-02-02
**Author**: Backend Agent / Claude Code

---

## 1. 개요

### 1.1 Circuit Breaker란?

Circuit Breaker는 분산 시스템에서 **장애 전파를 방지**하는 디자인 패턴입니다. 하위 서비스 장애 시 빠른 실패(Fail-Fast)를 통해 시스템 전체 안정성을 유지합니다.

```
┌─────────────────────────────────────────────────────────────┐
│                    Circuit Breaker 상태                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   CLOSED ──(실패율 초과)──> OPEN ──(대기시간 경과)──> HALF-OPEN │
│      ↑                        │                        │    │
│      └────────────────────────┴────(성공)──────────────┘    │
│                               │                             │
│                         (실패)─┘                            │
│                               ↓                             │
│                             OPEN                            │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 프로젝트 적용 현황

| 구성요소 | 기술 | 위치 |
|----------|------|------|
| **Gateway** | Spring Cloud Gateway | `gateway/` |
| **Circuit Breaker** | Resilience4j | Gateway 내장 |
| **Fallback** | FallbackController | Gateway 내장 |

---

## 2. 서비스별 설정

### 2.1 설정 요약

| 서비스 | Sliding Window | Failure Threshold | Wait Duration | Timeout |
|--------|:--------------:|:-----------------:|:-------------:|:-------:|
| auth-circuit-breaker | 10 | 50% | 5s | 15s |
| backend-circuit-breaker | 10 | 50% | 5s | 30s |
| knowledge-circuit-breaker | 10 | 50% | 5s | 30s |
| user-circuit-breaker | 10 | 50% | 5s | 15s |
| **ai-service-circuit-breaker** | **5** | 50% | **10s** | **60s** |

### 2.2 AI 서비스 특수 설정

AI 서비스는 처리 시간이 길어 별도 설정 적용:

```yaml
ai-service-circuit-breaker:
  slidingWindowSize: 5              # 적은 샘플로 빠른 판단
  failureRateThreshold: 50          # 50% 실패 시 Open
  waitDurationInOpenState: 10s      # 10초 대기 (복구 시간)
  slowCallDurationThreshold: 5s     # 5초 이상이면 Slow Call
  slowCallRateThreshold: 80         # 80% Slow Call 시 Open
  permittedNumberOfCallsInHalfOpenState: 3
```

### 2.3 설정 파일 위치

```
gateway/src/main/resources/application.yml
└── resilience4j.circuitbreaker.instances.*
```

---

## 3. 설정 파라미터 상세

### 3.1 핵심 파라미터

| 파라미터 | 설명 | 기본값 |
|----------|------|:------:|
| `slidingWindowSize` | 실패율 계산에 사용할 요청 수 | 10 |
| `failureRateThreshold` | Circuit Open 임계 실패율 (%) | 50 |
| `waitDurationInOpenState` | Open 상태 유지 시간 | 5s |
| `permittedNumberOfCallsInHalfOpenState` | Half-Open 시 허용 요청 수 | 3 |

### 3.2 Slow Call 파라미터 (AI 서비스용)

| 파라미터 | 설명 | AI 서비스 값 |
|----------|------|:------------:|
| `slowCallDurationThreshold` | Slow Call 기준 시간 | 5s |
| `slowCallRateThreshold` | Slow Call 비율 임계 (%) | 80 |

### 3.3 타임아웃 설정

```yaml
# TimeLimiter 설정
resilience4j.timelimiter.instances:
  ai-service-circuit-breaker:
    timeoutDuration: 60s  # AI 서비스 타임아웃
```

---

## 4. Fallback 동작

### 4.1 Fallback Controller

위치: `gateway/src/main/java/com/knowledge/gateway/route/FallbackController.java`

```java
@RestController
public class FallbackController {

    @GetMapping("/fallback/backend")
    public ResponseEntity<Map<String, Object>> backendFallback() {
        return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
            .body(Map.of(
                "status", 503,
                "service", "backend",
                "error", "Backend service is temporarily unavailable",
                "message", "Please try again later"
            ));
    }

    @GetMapping("/fallback/ai-service")
    public ResponseEntity<Map<String, Object>> aiServiceFallback() {
        return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
            .body(Map.of(
                "status", 503,
                "service", "ai-service",
                "error", "AI service is temporarily unavailable",
                "message", "Please try again later"
            ));
    }
}
```

### 4.2 Fallback 응답 형식

```json
{
  "status": 503,
  "service": "backend",
  "timestamp": "2026-02-02T01:30:40.927011728Z",
  "error": "Backend service is temporarily unavailable",
  "message": "Please try again later"
}
```

---

## 5. 모니터링

### 5.1 로그 확인

```bash
# Gateway 로그에서 Circuit Breaker 상태 확인
docker logs kp-api-gateway 2>&1 | grep -i "circuit"

# 예상 로그
WARN c.k.gateway.route.FallbackController : Backend service fallback triggered - circuit breaker open
INFO ... : CircuitBreaker 'backend-circuit-breaker' changed state from CLOSED to OPEN
INFO ... : CircuitBreaker 'backend-circuit-breaker' changed state from OPEN to HALF_OPEN
INFO ... : CircuitBreaker 'backend-circuit-breaker' changed state from HALF_OPEN to CLOSED
```

### 5.2 Actuator 엔드포인트

```bash
# Circuit Breaker 상태 조회
curl http://localhost:8080/actuator/circuitbreakers

# 특정 Circuit Breaker 상태
curl http://localhost:8080/actuator/circuitbreakers/backend-circuit-breaker

# Health Check
curl http://localhost:8080/actuator/health
```

### 5.3 Grafana 대시보드 (권장)

Prometheus + Grafana 연동 시 다음 메트릭 모니터링:

| 메트릭 | 설명 |
|--------|------|
| `resilience4j_circuitbreaker_state` | Circuit Breaker 상태 (0=CLOSED, 1=OPEN, 2=HALF_OPEN) |
| `resilience4j_circuitbreaker_calls_total` | 총 호출 수 |
| `resilience4j_circuitbreaker_failure_rate` | 실패율 |
| `resilience4j_circuitbreaker_slow_call_rate` | Slow Call 비율 |

---

## 6. 트러블슈팅

### 6.1 Circuit Breaker가 Open 상태로 고정

**증상**: 서비스 복구 후에도 계속 503 응답

**원인**:
1. 하위 서비스가 완전히 복구되지 않음
2. Half-Open 상태에서 실패 반복

**해결**:
```bash
# 1. 하위 서비스 상태 확인
docker ps | grep -E "(backend|ai-service)"
curl http://localhost:8081/actuator/health  # Backend
curl http://localhost:8000/health            # AI Service

# 2. Gateway 재시작 (Circuit Breaker 리셋)
docker restart kp-api-gateway

# 3. 또는 Actuator로 리셋 (설정 필요)
curl -X POST http://localhost:8080/actuator/circuitbreakers/backend-circuit-breaker/reset
```

### 6.2 Timeout 오류 빈발

**증상**: `TimeoutException` 또는 Slow Call 증가

**원인**: 하위 서비스 응답 지연

**해결**:
```yaml
# application.yml에서 타임아웃 증가
resilience4j.timelimiter.instances.backend-circuit-breaker:
  timeoutDuration: 60s  # 기존 30s → 60s
```

### 6.3 특정 서비스만 장애

**확인 방법**:
```bash
# 서비스별 직접 호출 테스트
curl http://localhost:8081/actuator/health  # Backend
curl http://localhost:8000/health            # AI Service
curl http://localhost:8180/health            # Keycloak

# Gateway 통한 호출
curl http://localhost:8080/api/v1/health
```

---

## 7. 운영 시나리오별 대응

### 7.1 시나리오 1: Backend 서비스 장애

```
[감지] Gateway 로그에서 "circuit breaker open" 확인
       ↓
[확인] docker ps | grep kp-backend
       docker logs kp-backend --tail 100
       ↓
[조치] docker restart kp-backend
       ↓
[검증] curl http://localhost:8081/actuator/health
       # 정상: {"status":"UP"}
       ↓
[완료] Circuit Breaker가 자동으로 Half-Open → Closed 전환
```

### 7.2 시나리오 2: AI 서비스 응답 지연

```
[감지] Slow Call Rate 증가, 응답 시간 >5s
       ↓
[확인] AI 서비스 리소스 확인
       docker stats kp-ai-service
       ↓
[조치] 1. 타임아웃 임시 증가
       2. AI 서비스 스케일업 또는 재시작
       ↓
[검증] 응답 시간 정상화 확인
```

### 7.3 시나리오 3: 전체 서비스 장애

```
[감지] 모든 엔드포인트에서 503 응답
       ↓
[확인] docker-compose ps
       # 모든 컨테이너 상태 확인
       ↓
[조치] docker-compose restart
       # 또는 개별 서비스 순차 재시작
       ↓
[검증] 전체 Health Check
       curl http://localhost:8080/actuator/health
```

---

## 8. 검증 결과 (2026-02-02)

### 8.1 테스트 시나리오

| 시나리오 | 내용 | 결과 |
|----------|------|:----:|
| Backend 장애 | 서비스 중단 후 Fallback 확인 | ✅ PASS |
| Backend 복구 | 재시작 후 Circuit 복구 | ✅ PASS |
| AI Service 장애 | 서비스 중단 확인 | ✅ PASS |
| AI Service 복구 | 재시작 후 정상 동작 | ✅ PASS |

### 8.2 검증된 동작

1. **Fallback 응답**: HTTP 503 + 구조화된 에러 메시지
2. **상태 전환**: CLOSED → OPEN → HALF_OPEN → CLOSED
3. **로그 출력**: Circuit Breaker 상태 변경 로깅
4. **서비스 복구**: 자동 복구 확인

---

## 9. 설정 변경 방법

### 9.1 실시간 변경 (재시작 불필요)

```bash
# Actuator를 통한 동적 설정 변경 (설정 필요)
# application.yml에 management.endpoint.circuitbreakerevents.enabled=true 추가 필요
```

### 9.2 설정 파일 변경

```bash
# 1. 설정 파일 수정
vi gateway/src/main/resources/application.yml

# 2. Gateway 재시작
docker restart kp-api-gateway

# 3. 설정 적용 확인
curl http://localhost:8080/actuator/circuitbreakers
```

---

## 10. 관련 파일

| 파일 | 설명 |
|------|------|
| `gateway/src/main/resources/application.yml` | Circuit Breaker 설정 |
| `gateway/src/main/java/.../GatewayRouteConfig.java` | 라우트 및 필터 설정 |
| `gateway/src/main/java/.../FallbackController.java` | Fallback 응답 처리 |

---

## 11. 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 1.0 | 2026-02-02 | 최초 작성 - 실환경 검증 완료 |

---

**문서 작성**: Backend Agent
**검토**: Claude Code
**작성 시간**: 2026-02-02 11:15 KST
