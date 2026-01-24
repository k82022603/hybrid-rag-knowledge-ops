package com.knowledge.gateway.config;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.cloud.gateway.filter.ratelimit.KeyResolver;
import org.springframework.mock.http.server.reactive.MockServerHttpRequest;
import org.springframework.mock.web.server.MockServerWebExchange;
import org.springframework.security.authentication.TestingAuthenticationToken;
import org.springframework.test.context.ActiveProfiles;
import reactor.test.StepVerifier;

import java.net.InetSocketAddress;

/**
 * Unit tests for RateLimiterConfig
 *
 * <p>Tests KeyResolver behavior for different scenarios
 */
@SpringBootTest(classes = RateLimiterConfig.class)
@ActiveProfiles("test")
class RateLimiterConfigTest {

    @Autowired
    private KeyResolver userKeyResolver;

    @Test
    @DisplayName("KeyResolver returns X-Forwarded-For header when present")
    void keyResolver_ReturnsXForwardedFor_WhenPresent() {
        MockServerHttpRequest request = MockServerHttpRequest.get("/api/v1/test")
            .header("X-Forwarded-For", "192.168.1.100")
            .remoteAddress(new InetSocketAddress("127.0.0.1", 8080))
            .build();
        MockServerWebExchange exchange = MockServerWebExchange.from(request);

        StepVerifier.create(userKeyResolver.resolve(exchange))
            .expectNext("192.168.1.100")
            .verifyComplete();
    }

    @Test
    @DisplayName("KeyResolver returns remote address when X-Forwarded-For is missing")
    void keyResolver_ReturnsRemoteAddress_WhenXForwardedForMissing() {
        MockServerHttpRequest request = MockServerHttpRequest.get("/api/v1/test")
            .remoteAddress(new InetSocketAddress("10.0.0.50", 8080))
            .build();
        MockServerWebExchange exchange = MockServerWebExchange.from(request);

        StepVerifier.create(userKeyResolver.resolve(exchange))
            .expectNext("10.0.0.50")
            .verifyComplete();
    }

    @Test
    @DisplayName("KeyResolver returns anonymous for null remote address")
    void keyResolver_ReturnsAnonymous_WhenNoAddressInfo() {
        MockServerHttpRequest request = MockServerHttpRequest.get("/api/v1/test")
            .build();
        MockServerWebExchange exchange = MockServerWebExchange.from(request);

        StepVerifier.create(userKeyResolver.resolve(exchange))
            .expectNext("anonymous")
            .verifyComplete();
    }

    @Test
    @DisplayName("KeyResolver returns username when authenticated")
    void keyResolver_ReturnsUsername_WhenAuthenticated() {
        MockServerHttpRequest request = MockServerHttpRequest.get("/api/v1/test")
            .remoteAddress(new InetSocketAddress("127.0.0.1", 8080))
            .build();
        MockServerWebExchange exchange = MockServerWebExchange.from(request);

        // Add authentication principal
        TestingAuthenticationToken authentication =
            new TestingAuthenticationToken("testuser@example.com", "password");
        exchange = exchange.mutate()
            .principal(reactor.core.publisher.Mono.just(authentication))
            .build();

        StepVerifier.create(userKeyResolver.resolve(exchange))
            .expectNext("testuser@example.com")
            .verifyComplete();
    }
}
