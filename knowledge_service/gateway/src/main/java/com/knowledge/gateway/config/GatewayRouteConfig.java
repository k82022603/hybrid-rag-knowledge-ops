package com.knowledge.gateway.config;

import io.github.resilience4j.timelimiter.TimeLimiterConfig;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.circuitbreaker.resilience4j.ReactiveResilience4JCircuitBreakerFactory;
import org.springframework.cloud.circuitbreaker.resilience4j.Resilience4JConfigBuilder;
import org.springframework.cloud.client.circuitbreaker.Customizer;
import org.springframework.cloud.gateway.route.RouteLocator;
import org.springframework.cloud.gateway.route.builder.RouteLocatorBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.time.Duration;

/**
 * Gateway Route Configuration
 *
 * <p>Defines programmatic routes with SSE-specific timeout separation
 * and per-service circuit breaker customization.
 *
 * <p>Route priority: Routes defined here (programmatic) have higher priority than
 * application.yml routes. SSE streaming routes are defined here with extended
 * timeouts (300s), while standard routes remain in application.yml (30s default).
 */
@Configuration
@Slf4j
public class GatewayRouteConfig {

    @Value("${AI_SERVICE_URL:http://localhost:8000}")
    private String aiServiceUrl;

    @Value("${gateway.timeout.sse:300}")
    private int sseTimeoutSeconds;

    @Value("${gateway.timeout.default:30}")
    private int defaultTimeoutSeconds;

    /**
     * Programmatic routes for SSE endpoints requiring extended timeouts.
     *
     * <p>SSE streaming endpoints need 300s timeout (vs 30s default) because
     * LLM responses stream over extended periods. The SSE route is defined
     * here to override the application.yml route with SSE-specific settings.
     */
    @Bean
    public RouteLocator sseRouteLocator(RouteLocatorBuilder builder) {
        log.info("Configuring SSE routes: timeout={}s (default={}s)", sseTimeoutSeconds, defaultTimeoutSeconds);

        return builder.routes()
            // SSE Streaming Search - extended timeout (300s)
            .route("search-service-stream-sse", r -> r
                .path("/api/v1/search/stream/**")
                .filters(f -> f
                    .filter((exchange, chain) -> {
                        // Set SSE-specific response timeout via metadata
                        exchange.getAttributes().put("response-timeout",
                            Duration.ofSeconds(sseTimeoutSeconds));
                        return chain.filter(exchange);
                    })
                    .circuitBreaker(config -> config
                        .setName("ai-service-circuit-breaker")
                    )
                    .requestRateLimiter(config -> config
                        .setReplenishRate(20)
                        .setBurstCapacity(40)
                        .setRequestedTokens(2)
                    )
                )
                .uri(aiServiceUrl)
            )
            .build();
    }

    /**
     * Per-service circuit breaker customizer.
     *
     * <p>Configures service-specific time limits:
     * <ul>
     *   <li>AI Service: 120s (LLM cold start: embedding 46s + reranking 9s + LLM 35s)</li>
     *   <li>Knowledge Service: 30s (fast DB queries expected)</li>
     *   <li>Auth/User Service: 15s (quick auth operations)</li>
     *   <li>Default: 30s</li>
     * </ul>
     *
     * <p>Circuit breaker sliding window and failure rate thresholds are configured
     * in application.yml {@code resilience4j.circuitbreaker} section.
     */
    @Bean
    public Customizer<ReactiveResilience4JCircuitBreakerFactory> defaultCustomizer() {
        return factory -> {
            // Default: 30s timeout
            factory.configureDefault(id -> new Resilience4JConfigBuilder(id)
                .timeLimiterConfig(TimeLimiterConfig.custom()
                    .timeoutDuration(Duration.ofSeconds(defaultTimeoutSeconds))
                    .build())
                .build());

            // AI Service: 120s timeout (cold start support)
            factory.configure(builder -> builder
                .timeLimiterConfig(TimeLimiterConfig.custom()
                    .timeoutDuration(Duration.ofSeconds(120))
                    .build()),
                "ai-service-circuit-breaker"
            );

            // Knowledge Service: 30s timeout (fast DB queries)
            factory.configure(builder -> builder
                .timeLimiterConfig(TimeLimiterConfig.custom()
                    .timeoutDuration(Duration.ofSeconds(30))
                    .build()),
                "knowledge-circuit-breaker"
            );

            // Auth Service: 15s timeout
            factory.configure(builder -> builder
                .timeLimiterConfig(TimeLimiterConfig.custom()
                    .timeoutDuration(Duration.ofSeconds(15))
                    .build()),
                "auth-circuit-breaker"
            );

            // User Service: 15s timeout
            factory.configure(builder -> builder
                .timeLimiterConfig(TimeLimiterConfig.custom()
                    .timeoutDuration(Duration.ofSeconds(15))
                    .build()),
                "user-circuit-breaker"
            );

            log.info("Circuit breaker customizer initialized - AI: 120s, Knowledge: 30s, Auth/User: 15s, Default: {}s",
                defaultTimeoutSeconds);
        };
    }
}
