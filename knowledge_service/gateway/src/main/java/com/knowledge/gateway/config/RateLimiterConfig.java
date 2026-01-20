package com.knowledge.gateway.config;

import org.springframework.cloud.gateway.filter.ratelimit.KeyResolver;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import reactor.core.publisher.Mono;

import java.security.Principal;

/**
 * Rate Limiter Configuration
 *
 * <p>Configures rate limiting based on user or IP address
 */
@Configuration
public class RateLimiterConfig {

    /**
     * User-based rate limiting key resolver
     * Falls back to IP address for anonymous users
     */
    @Bean
    public KeyResolver userKeyResolver() {
        return exchange -> exchange.getPrincipal()
            .map(Principal::getName)
            .switchIfEmpty(Mono.justOrEmpty(
                exchange.getRequest()
                    .getHeaders()
                    .getFirst("X-Forwarded-For")
            ))
            .switchIfEmpty(Mono.justOrEmpty(
                exchange.getRequest()
                    .getRemoteAddress()
                    .getAddress()
                    .getHostAddress()
            ))
            .defaultIfEmpty("anonymous");
    }
}
