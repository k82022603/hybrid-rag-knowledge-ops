# 이슈 보고서: Netty 채널 에러 (EpollEventLoop)

## 기본 정보

| 항목 | 내용 |
|------|------|
| **보고일** | 2026-02-04 |
| **보고자** | TechLead |
| **우선순위** | Medium |
| **상태** | 분석 완료 |
| **컴포넌트** | API Gateway (Spring Cloud Gateway) |
| **Netty 버전** | 4.1.105.Final |

---

## 에러 요약

Spring Cloud Gateway에서 Netty Epoll 기반 비동기 I/O 처리 중 발생한 채널 읽기 에러로, 주로 **연결 끊김** 또는 **타임아웃** 상황에서 발생합니다.

---

## 스택 트레이스

```
at io.netty.channel.DefaultChannelPipeline$HeadContext.channelRead(DefaultChannelPipeline.java:1410)
at io.netty.channel.AbstractChannelHandlerContext.invokeChannelRead(AbstractChannelHandlerContext.java:440)
at io.netty.channel.AbstractChannelHandlerContext.invokeChannelRead(AbstractChannelHandlerContext.java:420)
at io.netty.channel.DefaultChannelPipeline.fireChannelRead(DefaultChannelPipeline.java:919)
at io.netty.channel.epoll.AbstractEpollStreamChannel$EpollStreamUnsafe.epollInReady(AbstractEpollStreamChannel.java:800)
at io.netty.channel.epoll.EpollEventLoop.processReady(EpollEventLoop.java:509)
at io.netty.channel.epoll.EpollEventLoop.run(EpollEventLoop.java:407)
at io.netty.util.concurrent.SingleThreadEventExecutor$4.run(SingleThreadEventExecutor.java:997)
at io.netty.util.internal.ThreadExecutorMap$2.run(ThreadExecutorMap.java:74)
at io.netty.util.concurrent.FastThreadLocalRunnable.run(FastThreadLocalRunnable.java:30)
at java.base/java.lang.Thread.run(Unknown Source)
```

---

## 원인 분석

### 설계 문제 vs 구현 문제

| 판단 | 근거 |
|------|------|
| **구현 문제 (Configuration Issue)** | 설계 자체는 올바르나, 타임아웃/연결 풀 설정이 부적절할 가능성 |

**스택 트레이스 해석**:
- `EpollEventLoop.run` → Linux epoll 기반 이벤트 루프 실행
- `AbstractEpollStreamChannel$EpollStreamUnsafe.epollInReady` → 소켓에서 데이터 수신 준비
- `DefaultChannelPipeline.fireChannelRead` → 파이프라인을 통해 데이터 전달
- `HeadContext.channelRead` → 파이프라인 헤드에서 데이터 읽기

이 스택 트레이스 자체는 **정상적인 Netty 처리 흐름**이며, 실제 예외 메시지가 없으면 단순 로깅일 수 있습니다.

### 상세 분석

#### 1. 발생 가능한 시나리오

| 시나리오 | 설명 | 가능성 |
|----------|------|--------|
| **연결 끊김** | 클라이언트가 요청 중 연결을 끊음 | 높음 |
| **타임아웃** | 업스트림 서비스 응답 지연 | 높음 |
| **리소스 부족** | 채널/버퍼 풀 고갈 | 낮음 |
| **네트워크 불안정** | Docker 네트워크 이슈 | 중간 |

#### 2. 현재 Gateway 설정 검토

**application.yml 타임아웃 설정 (현재)**:

```yaml
resilience4j:
  timelimiter:
    instances:
      auth-circuit-breaker:
        timeout-duration: 15s
      backend-circuit-breaker:
        timeout-duration: 30s
      ai-service-circuit-breaker:
        timeout-duration: 60s
```

**WebClientConfig (Backend) 설정**:

```java
HttpClient httpClient = HttpClient.create()
    .option(ChannelOption.CONNECT_TIMEOUT_MILLIS, (int) timeout.toMillis())
    .responseTimeout(timeout)
    .doOnConnected(conn -> conn
        .addHandlerLast(new ReadTimeoutHandler(timeout.toSeconds(), TimeUnit.SECONDS))
        .addHandlerLast(new WriteTimeoutHandler(timeout.toSeconds(), TimeUnit.SECONDS))
    );
```

#### 3. 잠재적 문제점

| 구분 | 현재 상태 | 권장 사항 |
|------|----------|----------|
| **Connection Pool** | 기본값 사용 | 명시적 설정 필요 |
| **Keep-Alive** | 기본값 | 명시적 설정 필요 |
| **Idle Timeout** | 미설정 | 30s 설정 권장 |
| **에러 로깅** | Netty 연결 끊김 WARN 레벨 | DEBUG로 조정하여 로그 노이즈 감소 |

---

## 영향 범위

### 영향받는 기능

| 기능 | 영향 | 설명 |
|------|------|------|
| API Gateway 라우팅 | 잠재적 | 간헐적 연결 실패 가능 |
| 인증 (Auth) | 잠재적 | 15s 타임아웃 내 응답 필요 |
| 검색 (AI Service) | 높음 | 60s 타임아웃, LLM 지연 시 발생 가능 |
| 일반 API | 낮음 | 30s 타임아웃 |

### 영향받는 서비스

```
[Frontend] → [Nginx] → [API Gateway] ← 에러 발생 지점
                              ↓
                    [Backend] / [AI Service]
```

---

## 해결 방안

### 단기 조치 (Immediate)

#### 1. 로그 레벨 조정으로 상세 분석

```yaml
# application.yml에 추가
logging:
  level:
    io.netty: DEBUG
    reactor.netty: DEBUG
    org.springframework.cloud.gateway: DEBUG
```

#### 2. 에러 컨텍스트 확인

실제 예외 메시지가 무엇인지 확인 필요:
- `Connection reset by peer` → 클라이언트 측 연결 끊김
- `Connection timed out` → 업스트림 서비스 지연
- `Channel closed` → 비정상 종료

### 장기 조치 (Long-term)

#### 1. Connection Pool 명시적 설정

**Gateway application.yml에 추가**:

```yaml
spring:
  cloud:
    gateway:
      httpclient:
        connect-timeout: 5000
        response-timeout: 30s
        pool:
          type: elastic
          max-idle-time: 30s
          max-connections: 500
          acquire-timeout: 45000
```

#### 2. Keep-Alive 설정

```yaml
spring:
  cloud:
    gateway:
      httpclient:
        wiretap: true  # 디버깅용
        pool:
          evict-in-background: 30s
```

#### 3. Netty 연결 끊김 로그 레벨 조정

> **참고**: Netty 채널 레벨 예외(Connection reset, premature close 등)는 GlobalExceptionHandler에서 처리하는 것이 **부적절**합니다.
> - 클라이언트가 이미 연결을 끊은 상태이므로 응답을 보낼 채널이 없음
> - Netty 내부에서 이미 채널을 닫고 정리함
> - 비즈니스 예외와 네트워크 레이어 예외는 처리 레이어가 다름

**권장**: 로그 레벨만 조정하여 노이즈 감소

```yaml
# application.yml
logging:
  level:
    reactor.netty.channel.ChannelOperationsHandler: ERROR  # 연결 끊김 로그 숨김
    io.netty.handler.codec: WARN
```

---

## 담당자 지정

| 역할 | 담당 | 작업 |
|------|------|------|
| **분석** | TechLead | 완료 |
| **구현** | Backend Developer | Connection Pool 설정 추가 |
| **검증** | QA Engineer | 부하 테스트 후 에러 재현 확인 |
| **인프라** | Infra Engineer | Docker 네트워크 점검 |

---

## 내일 할 일

- [ ] Gateway 로그 레벨을 DEBUG로 변경하여 실제 예외 메시지 확인
- [ ] Connection Pool 명시적 설정 추가 (spring.cloud.gateway.httpclient)
- [ ] AI Service 응답 시간 모니터링 (60s 타임아웃 적절성 검토)
- [ ] 부하 테스트로 에러 재현 시도
- [ ] Netty 연결 끊김 로그 레벨 조정 (WARN → DEBUG/ERROR)

---

## 참고 자료

### 관련 파일

| 파일 | 설명 |
|------|------|
| `/knowledge_service/gateway/src/main/resources/application.yml` | Gateway 설정 |
| `/knowledge_service/gateway/src/main/java/.../config/GatewayRouteConfig.java` | Circuit Breaker 설정 |
| `/knowledge_service/gateway/src/main/java/.../exception/GlobalExceptionHandler.java` | 예외 처리 |
| `/knowledge_service/backend/src/main/java/.../config/WebClientConfig.java` | WebClient 설정 |
| `/infrastructure/docker/docker-compose.yml` | 컨테이너 설정 |

### 관련 이슈

- `incident_report_2026-02-02_ai_service_startup.md` - AI Service DNS 해결 실패 (관련 이슈)

---

## 변경 이력

| 날짜 | 버전 | 변경 내용 |
|------|------|----------|
| 2026-02-04 | 1.0 | 초기 보고서 작성 |
| 2026-02-04 | 1.1 | GlobalExceptionHandler 권장사항 제거 (네트워크 레이어 예외는 처리 대상 아님) |

---

**검토자**: Tech Lead (자체 검토)
**승인 필요**: PM
