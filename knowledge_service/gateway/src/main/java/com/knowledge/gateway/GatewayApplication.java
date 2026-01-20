package com.knowledge.gateway;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Knowledge Platform API Gateway
 *
 * <p>Spring Cloud Gateway based API Gateway
 * - JWT token validation with Keycloak
 * - Circuit Breaker with Resilience4j
 * - Rate Limiting
 * - Request routing to Backend and AI services
 */
@SpringBootApplication
public class GatewayApplication {

    public static void main(String[] args) {
        SpringApplication.run(GatewayApplication.class, args);
    }
}
