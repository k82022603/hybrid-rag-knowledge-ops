package com.knowledge.gateway.route;

import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import reactor.core.publisher.Mono;

import java.time.Instant;
import java.util.Map;

/**
 * Fallback Controller
 *
 * <p>Provides fallback responses when circuit breaker is open
 */
@RestController
@RequestMapping("/fallback")
@Slf4j
public class FallbackController {

    /**
     * Fallback for Backend service
     */
    @GetMapping("/backend")
    public Mono<ResponseEntity<Map<String, Object>>> backendFallback() {
        log.warn("Backend service fallback triggered");
        return Mono.just(ResponseEntity
            .status(HttpStatus.SERVICE_UNAVAILABLE)
            .body(Map.of(
                "error", "Backend service is temporarily unavailable",
                "message", "Please try again later",
                "service", "backend",
                "timestamp", Instant.now().toString()
            )));
    }

    /**
     * Fallback for AI Service
     */
    @GetMapping("/ai-service")
    public Mono<ResponseEntity<Map<String, Object>>> aiServiceFallback() {
        log.warn("AI service fallback triggered");
        return Mono.just(ResponseEntity
            .status(HttpStatus.SERVICE_UNAVAILABLE)
            .body(Map.of(
                "error", "AI service is temporarily unavailable",
                "message", "Search functionality is currently limited",
                "service", "ai-service",
                "timestamp", Instant.now().toString()
            )));
    }

    /**
     * Health check endpoint
     */
    @GetMapping("/health")
    public Mono<ResponseEntity<Map<String, Object>>> health() {
        return Mono.just(ResponseEntity.ok(Map.of(
            "status", "UP",
            "service", "gateway-fallback",
            "timestamp", Instant.now().toString()
        )));
    }
}
