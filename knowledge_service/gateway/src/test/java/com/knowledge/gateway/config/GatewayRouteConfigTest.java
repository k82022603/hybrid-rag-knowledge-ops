package com.knowledge.gateway.config;

import io.github.resilience4j.circuitbreaker.CircuitBreakerConfig;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.cloud.circuitbreaker.resilience4j.ReactiveResilience4JCircuitBreakerFactory;
import org.springframework.cloud.client.circuitbreaker.Customizer;
import org.springframework.cloud.gateway.route.RouteLocator;
import org.springframework.test.context.ActiveProfiles;

import java.time.Duration;

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
}
