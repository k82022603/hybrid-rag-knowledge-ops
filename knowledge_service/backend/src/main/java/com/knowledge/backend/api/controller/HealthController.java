package com.knowledge.backend.api.controller;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import reactor.core.publisher.Mono;

import java.time.Instant;
import java.util.Map;

/**
 * Health Check Controller
 *
 * <p>Provides health check endpoints for container orchestration
 */
@RestController
@RequestMapping("/api/v1")
public class HealthController {

    @Value("${spring.application.name}")
    private String applicationName;

    /**
     * Simple health check endpoint
     *
     * @return health status
     */
    @GetMapping("/health")
    public Mono<ResponseEntity<Map<String, Object>>> health() {
        return Mono.just(ResponseEntity.ok(Map.of(
            "status", "UP",
            "service", applicationName,
            "timestamp", Instant.now().toString()
        )));
    }

    /**
     * Readiness check endpoint
     *
     * @return readiness status
     */
    @GetMapping("/ready")
    public Mono<ResponseEntity<Map<String, Object>>> ready() {
        return Mono.just(ResponseEntity.ok(Map.of(
            "status", "READY",
            "service", applicationName,
            "timestamp", Instant.now().toString()
        )));
    }

    /**
     * Liveness check endpoint
     *
     * @return liveness status
     */
    @GetMapping("/live")
    public Mono<ResponseEntity<Map<String, Object>>> live() {
        return Mono.just(ResponseEntity.ok(Map.of(
            "status", "LIVE",
            "service", applicationName,
            "timestamp", Instant.now().toString()
        )));
    }
}
