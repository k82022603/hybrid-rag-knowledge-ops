package com.knowledge.gateway.config;

import io.github.resilience4j.timelimiter.TimeLimiterConfig;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.circuitbreaker.resilience4j.ReactiveResilience4JCircuitBreakerFactory;
import org.springframework.cloud.circuitbreaker.resilience4j.Resilience4JConfigBuilder;
import org.springframework.cloud.client.circuitbreaker.Customizer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.time.Duration;

/**
 * Gateway Route Configuration
 *
 * <p>Registers a default circuit breaker customizer for Spring Cloud Gateway.
 * Per-service circuit breaker behavior (sliding window, failure rate, timeouts) is
 * fully controlled by {@code resilience4j.circuitbreaker} and
 * {@code resilience4j.timelimiter} sections in application.yml — no duplication here.
 *
 * <p>Routes are defined in application.yml for easier configuration management.
 */
@Configuration
@Slf4j
public class GatewayRouteConfig {

    /**
     * Registers a default ReactiveResilience4JCircuitBreakerFactory customizer.
     *
     * <p>Individual service configurations (auth, backend, knowledge, user, ai-service)
     * are driven by application.yml {@code resilience4j} properties via Spring Boot
     * auto-configuration — no Java-side per-service overrides needed.
     */
    @Bean
    public Customizer<ReactiveResilience4JCircuitBreakerFactory> defaultCustomizer() {
        return factory -> {
            factory.configureDefault(id -> new Resilience4JConfigBuilder(id)
                .timeLimiterConfig(TimeLimiterConfig.custom()
                    .timeoutDuration(Duration.ofSeconds(30))
                    .build())
                .build());
            log.info("Circuit breaker default customizer initialized (per-service config via application.yml)");
        };
    }
}
