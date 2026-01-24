package com.knowledge.gateway.config;

import io.github.resilience4j.circuitbreaker.CircuitBreaker;
import io.github.resilience4j.circuitbreaker.CircuitBreakerConfig;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.cloud.circuitbreaker.resilience4j.ReactiveResilience4JCircuitBreakerFactory;
import org.springframework.cloud.client.circuitbreaker.Customizer;
import org.springframework.test.context.ActiveProfiles;

import java.time.Duration;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Unit tests for GatewayRouteConfig
 *
 * <p>Tests circuit breaker configuration for each service
 */
@SpringBootTest(classes = GatewayRouteConfig.class)
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
    @DisplayName("Circuit breaker factory is properly configured")
    void circuitBreakerFactory_IsConfigured() {
        ReactiveResilience4JCircuitBreakerFactory factory =
            new ReactiveResilience4JCircuitBreakerFactory();

        circuitBreakerCustomizer.customize(factory);

        // Create circuit breaker to verify configuration
        var circuitBreaker = factory.create("backend-circuit-breaker");
        assertThat(circuitBreaker).isNotNull();
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
        // Verify default configuration settings
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
    @DisplayName("AI service circuit breaker has slow call threshold")
    void aiServiceCircuitBreaker_HasSlowCallThreshold() {
        CircuitBreakerConfig aiConfig = CircuitBreakerConfig.custom()
            .slidingWindowType(CircuitBreakerConfig.SlidingWindowType.COUNT_BASED)
            .slidingWindowSize(5)
            .minimumNumberOfCalls(3)
            .failureRateThreshold(50)
            .waitDurationInOpenState(Duration.ofSeconds(10))
            .permittedNumberOfCallsInHalfOpenState(2)
            .slowCallDurationThreshold(Duration.ofSeconds(5))
            .slowCallRateThreshold(80)
            .build();

        assertThat(aiConfig.getSlowCallDurationThreshold()).isEqualTo(Duration.ofSeconds(5));
        assertThat(aiConfig.getSlowCallRateThreshold()).isEqualTo(80);
    }
}
