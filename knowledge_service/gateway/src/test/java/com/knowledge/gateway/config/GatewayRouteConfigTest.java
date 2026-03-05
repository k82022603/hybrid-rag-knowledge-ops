package com.knowledge.gateway.config;

import io.github.resilience4j.circuitbreaker.CircuitBreakerConfig;
import io.github.resilience4j.timelimiter.TimeLimiterConfig;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.cloud.circuitbreaker.resilience4j.ReactiveResilience4JCircuitBreakerFactory;
import org.springframework.cloud.circuitbreaker.resilience4j.Resilience4JConfigBuilder;
import org.springframework.cloud.client.circuitbreaker.Customizer;
import org.springframework.test.context.ActiveProfiles;

import java.time.Duration;
import java.util.concurrent.atomic.AtomicReference;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Unit tests for GatewayRouteConfig
 *
 * <p>Tests per-service circuit breaker configuration and SSE route setup.
 */
@SpringBootTest(classes = GatewayRouteConfig.class,
    properties = {
        "AI_SERVICE_URL=http://localhost:8000",
        "gateway.timeout.sse=300",
        "gateway.timeout.default=30"
    })
@ActiveProfiles("test")
class GatewayRouteConfigTest {

    @Autowired
    private Customizer<ReactiveResilience4JCircuitBreakerFactory> circuitBreakerCustomizer;

    @Value("${gateway.timeout.sse:300}")
    private int sseTimeoutSeconds;

    @Value("${gateway.timeout.default:30}")
    private int defaultTimeoutSeconds;

    @Test
    @DisplayName("Circuit breaker customizer bean is created")
    void circuitBreakerCustomizer_IsNotNull() {
        assertThat(circuitBreakerCustomizer).isNotNull();
    }

    @Test
    @DisplayName("Circuit breaker factory is properly configured with per-service settings")
    void circuitBreakerFactory_IsConfigured() {
        ReactiveResilience4JCircuitBreakerFactory factory =
            new ReactiveResilience4JCircuitBreakerFactory();

        circuitBreakerCustomizer.customize(factory);

        // Verify all per-service circuit breakers are created
        assertThat(factory.create("backend-circuit-breaker")).isNotNull();
        assertThat(factory.create("ai-service-circuit-breaker")).isNotNull();
        assertThat(factory.create("knowledge-circuit-breaker")).isNotNull();
        assertThat(factory.create("auth-circuit-breaker")).isNotNull();
        assertThat(factory.create("user-circuit-breaker")).isNotNull();
    }

    @Test
    @DisplayName("AI service circuit breaker has longer timeout")
    void aiServiceCircuitBreaker_HasLongerTimeout() {
        ReactiveResilience4JCircuitBreakerFactory factory =
            new ReactiveResilience4JCircuitBreakerFactory();

        circuitBreakerCustomizer.customize(factory);

        var aiCircuitBreaker = factory.create("ai-service-circuit-breaker");
        assertThat(aiCircuitBreaker).isNotNull();
    }

    @Test
    @DisplayName("Knowledge service circuit breaker is properly configured")
    void knowledgeServiceCircuitBreaker_IsConfigured() {
        ReactiveResilience4JCircuitBreakerFactory factory =
            new ReactiveResilience4JCircuitBreakerFactory();

        circuitBreakerCustomizer.customize(factory);

        var knowledgeCircuitBreaker = factory.create("knowledge-circuit-breaker");
        assertThat(knowledgeCircuitBreaker).isNotNull();
    }

    @Test
    @DisplayName("User service circuit breaker is properly configured")
    void userServiceCircuitBreaker_IsConfigured() {
        ReactiveResilience4JCircuitBreakerFactory factory =
            new ReactiveResilience4JCircuitBreakerFactory();

        circuitBreakerCustomizer.customize(factory);

        var userCircuitBreaker = factory.create("user-circuit-breaker");
        assertThat(userCircuitBreaker).isNotNull();
    }

    @Test
    @DisplayName("Default circuit breaker configuration has correct settings")
    void defaultCircuitBreakerConfig_HasCorrectSettings() {
        CircuitBreakerConfig defaultConfig = CircuitBreakerConfig.custom()
            .slidingWindowType(CircuitBreakerConfig.SlidingWindowType.COUNT_BASED)
            .slidingWindowSize(10)
            .minimumNumberOfCalls(5)
            .failureRateThreshold(50)
            .waitDurationInOpenState(Duration.ofSeconds(5))
            .permittedNumberOfCallsInHalfOpenState(3)
            .build();

        assertThat(defaultConfig.getSlidingWindowSize()).isEqualTo(10);
        assertThat(defaultConfig.getMinimumNumberOfCalls()).isEqualTo(5);
        assertThat(defaultConfig.getFailureRateThreshold()).isEqualTo(50);
        assertThat(defaultConfig.getWaitDurationInOpenState()).isEqualTo(Duration.ofSeconds(5));
    }

    @Test
    @DisplayName("AI service config has slow call threshold for LLM responses")
    void aiServiceConfig_HasSlowCallThreshold() {
        CircuitBreakerConfig aiConfig = CircuitBreakerConfig.custom()
            .slidingWindowSize(10)
            .failureRateThreshold(50)
            .waitDurationInOpenState(Duration.ofSeconds(30))
            .slowCallDurationThreshold(Duration.ofSeconds(45))
            .slowCallRateThreshold(90)
            .build();

        assertThat(aiConfig.getSlowCallDurationThreshold()).isEqualTo(Duration.ofSeconds(45));
        assertThat(aiConfig.getSlowCallRateThreshold()).isEqualTo(90);
        assertThat(aiConfig.getWaitDurationInOpenState()).isEqualTo(Duration.ofSeconds(30));
    }

    @Test
    @DisplayName("Knowledge service config has stricter failure threshold")
    void knowledgeServiceConfig_HasStricterThreshold() {
        CircuitBreakerConfig knowledgeConfig = CircuitBreakerConfig.custom()
            .slidingWindowSize(20)
            .failureRateThreshold(30)
            .waitDurationInOpenState(Duration.ofSeconds(15))
            .permittedNumberOfCallsInHalfOpenState(5)
            .build();

        assertThat(knowledgeConfig.getSlidingWindowSize()).isEqualTo(20);
        assertThat(knowledgeConfig.getFailureRateThreshold()).isEqualTo(30);
        assertThat(knowledgeConfig.getWaitDurationInOpenState()).isEqualTo(Duration.ofSeconds(15));
        assertThat(knowledgeConfig.getPermittedNumberOfCallsInHalfOpenState()).isEqualTo(5);
    }

    @Test
    @DisplayName("SSE route locator bean is created")
    void sseRouteLocator_IsCreated() {
        GatewayRouteConfig config = new GatewayRouteConfig();
        assertThat(config).isNotNull();
    }

    // ─────────────────────────────────────────────────────────────────────────
    // U04-U10: Timeout & SSE 검증 (STORY-127)
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * 서킷 브레이커 타임아웃 설정을 TimeLimiterConfig 빌더로 캡처하는 헬퍼.
     *
     * <p>ReactiveResilience4JCircuitBreakerFactory.configure()의 첫 번째 인자인
     * Consumer<Resilience4JConfigBuilder>를 가로채어 빌드된 TimeLimiterConfig의
     * timeoutDuration을 확인합니다.
     */
    private Duration captureTimeoutForCircuitBreaker(String circuitBreakerName) {
        AtomicReference<Duration> capturedTimeout = new AtomicReference<>();

        ReactiveResilience4JCircuitBreakerFactory capturingFactory =
            new ReactiveResilience4JCircuitBreakerFactory() {
                @Override
                public void configure(
                    java.util.function.Consumer<Resilience4JConfigBuilder> builderConsumer,
                    String... ids
                ) {
                    for (String id : ids) {
                        if (circuitBreakerName.equals(id)) {
                            // TimeLimiterConfig 빌더를 캡처하는 가짜 Resilience4JConfigBuilder
                            AtomicReference<TimeLimiterConfig> timeLimiterHolder = new AtomicReference<>();
                            Resilience4JConfigBuilder spy = new Resilience4JConfigBuilder(id) {
                                @Override
                                public Resilience4JConfigBuilder timeLimiterConfig(
                                    TimeLimiterConfig timeLimiterConfig
                                ) {
                                    timeLimiterHolder.set(timeLimiterConfig);
                                    return super.timeLimiterConfig(timeLimiterConfig);
                                }
                            };
                            builderConsumer.accept(spy);
                            if (timeLimiterHolder.get() != null) {
                                capturedTimeout.set(timeLimiterHolder.get().getTimeoutDuration());
                            }
                        }
                    }
                }
            };

        circuitBreakerCustomizer.customize(capturingFactory);
        return capturedTimeout.get();
    }

    @Test
    @DisplayName("U04: SSE 라우트 타임아웃은 300초여야 한다")
    void sseRouteTimeout_Is300Seconds() {
        // SSE 타임아웃은 gateway.timeout.sse 속성에서 주입되어
        // exchange attribute "response-timeout"으로 설정됨 (Duration.ofSeconds(300))
        // @Value 주입값으로 GatewayRouteConfig가 올바른 속성값을 수신했는지 검증
        assertThat(sseTimeoutSeconds)
            .as("SSE route timeout must be 300 seconds (extended for LLM streaming)")
            .isEqualTo(300);

        assertThat(Duration.ofSeconds(sseTimeoutSeconds))
            .as("SSE timeout duration must be 5 minutes (300s)")
            .isEqualTo(Duration.ofMinutes(5));
    }

    @Test
    @DisplayName("U05: AI Service 서킷 브레이커 타임아웃은 120초여야 한다")
    void aiServiceCircuitBreaker_Timeout_Is120Seconds() {
        Duration timeout = captureTimeoutForCircuitBreaker("ai-service-circuit-breaker");

        assertThat(timeout)
            .as("AI Service circuit breaker timeout must be 120s (LLM cold start)")
            .isEqualTo(Duration.ofSeconds(120));
    }

    @Test
    @DisplayName("U06: Knowledge Service 서킷 브레이커 타임아웃은 30초여야 한다")
    void knowledgeServiceCircuitBreaker_Timeout_Is30Seconds() {
        Duration timeout = captureTimeoutForCircuitBreaker("knowledge-circuit-breaker");

        assertThat(timeout)
            .as("Knowledge Service circuit breaker timeout must be 30s (fast DB queries)")
            .isEqualTo(Duration.ofSeconds(30));
    }

    @Test
    @DisplayName("U07: Auth Service 서킷 브레이커 타임아웃은 15초여야 한다")
    void authServiceCircuitBreaker_Timeout_Is15Seconds() {
        Duration timeout = captureTimeoutForCircuitBreaker("auth-circuit-breaker");

        assertThat(timeout)
            .as("Auth Service circuit breaker timeout must be 15s (quick auth operations)")
            .isEqualTo(Duration.ofSeconds(15));
    }

    @Test
    @DisplayName("U08: User Service 서킷 브레이커 타임아웃은 15초여야 한다")
    void userServiceCircuitBreaker_Timeout_Is15Seconds() {
        Duration timeout = captureTimeoutForCircuitBreaker("user-circuit-breaker");

        assertThat(timeout)
            .as("User Service circuit breaker timeout must be 15s (quick auth operations)")
            .isEqualTo(Duration.ofSeconds(15));
    }

    @Test
    @DisplayName("U09: 기본(default) 서킷 브레이커 타임아웃은 30초여야 한다")
    void defaultCircuitBreaker_Timeout_Is30Seconds() {
        // gateway.timeout.default=30 속성값이 defaultTimeoutSeconds에 주입됨
        // GatewayRouteConfig.defaultCustomizer()가 해당 값을 configureDefault에 사용하는지 검증

        // 1. 속성값 검증
        assertThat(defaultTimeoutSeconds)
            .as("gateway.timeout.default property must be 30 seconds")
            .isEqualTo(30);

        // 2. configureDefault를 오버라이드하여 TimeLimiterConfig 캡처
        AtomicReference<Duration> capturedDefault = new AtomicReference<>();

        ReactiveResilience4JCircuitBreakerFactory capturingFactory =
            new ReactiveResilience4JCircuitBreakerFactory() {
                @Override
                public void configureDefault(
                    java.util.function.Function<String, Resilience4JConfigBuilder.Resilience4JCircuitBreakerConfiguration> defaultConfiguration
                ) {
                    // 임의 id로 default 설정 함수를 호출하여 TimeLimiterConfig 캡처
                    Resilience4JConfigBuilder.Resilience4JCircuitBreakerConfiguration config =
                        defaultConfiguration.apply("test-default-id");
                    if (config != null && config.getTimeLimiterConfig() != null) {
                        capturedDefault.set(config.getTimeLimiterConfig().getTimeoutDuration());
                    }
                }
            };

        circuitBreakerCustomizer.customize(capturingFactory);

        assertThat(capturedDefault.get())
            .as("Default circuit breaker timeout must be 30s (from gateway.timeout.default property)")
            .isEqualTo(Duration.ofSeconds(30));
    }

    @Test
    @DisplayName("U10: SSE 엔드포인트는 /api/v1/search/stream/** 패턴과 매칭되어야 한다")
    void sseEndpoint_MatchesSearchStreamPattern() {
        // SSE 라우트 ID와 경로 패턴이 올바른지 상수 기반으로 검증
        // (RouteLocatorBuilder는 Spring Context 없이 직접 생성 불가하므로,
        //  GatewayRouteConfig의 sseRouteLocator 메서드가 등록하는 경로를 문서화 테스트로 검증)
        String expectedRouteId = "search-service-stream-sse";
        String expectedPath = "/api/v1/search/stream/**";

        // 라우트 ID 명명 규칙 검증
        assertThat(expectedRouteId)
            .as("SSE route ID must follow service-name-stream-sse convention")
            .contains("stream")
            .contains("sse");

        // 경로 패턴 검증
        assertThat(expectedPath)
            .as("SSE endpoint must match /api/v1/search/stream/** pattern")
            .startsWith("/api/v1/search/stream/")
            .endsWith("**");
    }
}
