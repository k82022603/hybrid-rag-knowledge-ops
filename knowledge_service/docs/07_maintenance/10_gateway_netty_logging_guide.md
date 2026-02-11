# Gateway Netty Logging Guide

> SCRUM-62: Netty Channel Error 대응 - 로그 최적화 가이드

## 개요

Spring Cloud Gateway는 Netty를 기반으로 동작하며, 연결 풀 관리 과정에서 다양한 로그를 생성합니다.
이 가이드는 환경별 로그 설정과 불필요한 노이즈를 필터링하는 방법을 설명합니다.

## 환경별 프로필

| 프로필 | 용도 | 활성화 방법 |
|--------|------|------------|
| `local` | 로컬 개발 (기본값) | `SPRING_PROFILES_ACTIVE=local` |
| `dev` | 개발 환경 (상세 디버깅) | `SPRING_PROFILES_ACTIVE=dev` |
| `docker` | Docker 환경 | `SPRING_PROFILES_ACTIVE=docker` |
| `prod` | 프로덕션 환경 | `SPRING_PROFILES_ACTIVE=prod` |

## 로그 레벨 매트릭스

### Application Level

| Logger | local | dev | docker | prod |
|--------|-------|-----|--------|------|
| `root` | INFO | INFO | INFO | INFO |
| `com.knowledge.gateway` | DEBUG | DEBUG | INFO | INFO |

### Spring Framework

| Logger | local | dev | docker | prod |
|--------|-------|-----|--------|------|
| `org.springframework.cloud.gateway` | DEBUG | DEBUG | WARN | WARN |
| `org.springframework.security` | DEBUG | DEBUG | WARN | WARN |

### Netty & Reactor (핵심)

| Logger | local | dev | docker | prod | 설명 |
|--------|-------|-----|--------|------|------|
| `reactor.netty` | INFO | INFO | WARN | WARN | Reactor Netty 전체 |
| `reactor.netty.http.client` | INFO | INFO | WARN | WARN | HTTP 클라이언트 |
| `io.netty` | WARN | INFO | WARN | WARN | Netty 전체 |
| `io.netty.channel` | WARN | INFO | ERROR | WARN | 채널 관련 |
| `reactor.netty.channel.ChannelOperationsHandler` | **ERROR** | WARN | **ERROR** | **ERROR** | 채널 에러 (노이즈) |
| `reactor.netty.http.client.HttpClientOperations` | **ERROR** | WARN | **ERROR** | **ERROR** | HTTP 작업 에러 |
| `reactor.netty.resources.PooledConnectionProvider` | INFO | INFO | WARN | WARN | 연결 풀 |

## 필터링되는 노이즈 로그

### 1. Connection Reset (연결 리셋)

```
ERROR r.n.channel.ChannelOperationsHandler - Connection reset by peer
```

**원인**: 클라이언트가 응답을 받기 전에 연결을 종료함
**대응**: ERROR 레벨로 필터링 (무시해도 됨)

### 2. Premature Close (조기 종료)

```
WARN r.n.http.client.HttpClientOperations - Premature close before response
```

**원인**: 서버가 응답을 완료하기 전에 연결이 닫힘
**대응**: ERROR 레벨로 필터링

### 3. Channel Closed (채널 닫힘)

```
DEBUG io.netty.channel.DefaultChannelPipeline - Channel closed unexpectedly
```

**원인**: Idle 타임아웃 또는 네트워크 문제
**대응**: WARN 이상으로 필터링

## 트러블슈팅 시 로그 활성화

### 상세 디버깅이 필요한 경우

1. **환경변수로 활성화**:
```bash
SPRING_PROFILES_ACTIVE=dev java -jar gateway.jar
```

2. **특정 로거만 활성화** (application.yml 수정):
```yaml
logging:
  level:
    reactor.netty: DEBUG
    reactor.netty.http.client: DEBUG
```

3. **Wiretap 활성화** (HTTP 요청/응답 전체 로깅):
```yaml
spring:
  cloud:
    gateway:
      httpclient:
        wiretap: true
```

> **주의**: Wiretap은 보안상 민감한 데이터를 노출할 수 있으므로 프로덕션에서 사용하지 마세요.

## 연결 풀 모니터링

### Actuator 엔드포인트

```bash
# Gateway 라우트 정보
curl http://localhost:8080/actuator/gateway/routes

# 메트릭 (Prometheus 형식)
curl http://localhost:8080/actuator/prometheus | grep gateway
```

### 주요 메트릭

| 메트릭 | 설명 |
|--------|------|
| `reactor_netty_connection_provider_active_connections` | 활성 연결 수 |
| `reactor_netty_connection_provider_idle_connections` | 유휴 연결 수 |
| `reactor_netty_connection_provider_pending_connections` | 대기 연결 수 |
| `gateway_requests_seconds` | 요청 처리 시간 |

## 참고

- [Connection Pool 설정](../02_design/10_infrastructure_detailed_design.md)
- [Circuit Breaker 운영 매뉴얼](./circuit_breaker_operations_manual.md)
- [Netty 에러 분석 보고서](./incident_report_2026-02-02_ai_service_startup.md)
