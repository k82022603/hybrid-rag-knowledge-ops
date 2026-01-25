package com.knowledge.gateway.route;

import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import reactor.core.publisher.Mono;

import java.time.Instant;
import java.util.Map;

/**
 * Fallback Controller
 *
 * <p>Provides fallback responses when circuit breaker is open or service is unavailable.
 * Each service has its own fallback endpoint with appropriate error messages.
 */
@RestController
@RequestMapping("/fallback")
@Slf4j
public class FallbackController {

    private static final String ERROR_KEY = "error";
    private static final String MESSAGE_KEY = "message";
    private static final String SERVICE_KEY = "service";
    private static final String TIMESTAMP_KEY = "timestamp";
    private static final String STATUS_KEY = "status";

    /**
     * Fallback for Auth service
     */
    @GetMapping("/auth")
    @PostMapping("/auth")
    public Mono<ResponseEntity<Map<String, Object>>> authFallback() {
        log.warn("Auth service fallback triggered - circuit breaker open");
        return Mono.just(createServiceUnavailableResponse(
            "Authentication service is temporarily unavailable",
            "Login/logout is currently unavailable. Please try again later.",
            "auth"
        ));
    }

    /**
     * Fallback for Backend service
     */
    @GetMapping("/backend")
    @PostMapping("/backend")
    public Mono<ResponseEntity<Map<String, Object>>> backendFallback() {
        log.warn("Backend service fallback triggered - circuit breaker open");
        return Mono.just(createServiceUnavailableResponse(
            "Backend service is temporarily unavailable",
            "Please try again later",
            "backend"
        ));
    }

    /**
     * Fallback for Knowledge Service
     */
    @GetMapping("/knowledge")
    @PostMapping("/knowledge")
    public Mono<ResponseEntity<Map<String, Object>>> knowledgeFallback() {
        log.warn("Knowledge service fallback triggered - circuit breaker open");
        return Mono.just(createServiceUnavailableResponse(
            "Knowledge service is temporarily unavailable",
            "Document management is currently limited. Please try again later.",
            "knowledge"
        ));
    }

    /**
     * Fallback for User Service
     */
    @GetMapping("/user")
    @PostMapping("/user")
    public Mono<ResponseEntity<Map<String, Object>>> userFallback() {
        log.warn("User service fallback triggered - circuit breaker open");
        return Mono.just(createServiceUnavailableResponse(
            "User service is temporarily unavailable",
            "User management is currently limited. Please try again later.",
            "user"
        ));
    }

    /**
     * Fallback for AI Service (Search)
     */
    @GetMapping("/ai-service")
    @PostMapping("/ai-service")
    public Mono<ResponseEntity<Map<String, Object>>> aiServiceFallback() {
        log.warn("AI service fallback triggered - circuit breaker open");
        return Mono.just(createServiceUnavailableResponse(
            "AI service is temporarily unavailable",
            "Search and RAG functionality is currently limited. Please try again later.",
            "ai-service"
        ));
    }

    /**
     * Fallback for Search Service (alias for AI service search)
     */
    @GetMapping("/search")
    @PostMapping("/search")
    public Mono<ResponseEntity<Map<String, Object>>> searchFallback() {
        log.warn("Search service fallback triggered - circuit breaker open");
        return Mono.just(createServiceUnavailableResponse(
            "Search service is temporarily unavailable",
            "Search functionality is currently limited. Please try again later.",
            "search"
        ));
    }

    /**
     * Health check endpoint
     */
    @GetMapping("/health")
    public Mono<ResponseEntity<Map<String, Object>>> health() {
        return Mono.just(ResponseEntity.ok(Map.of(
            STATUS_KEY, "UP",
            SERVICE_KEY, "gateway-fallback",
            TIMESTAMP_KEY, Instant.now().toString()
        )));
    }

    /**
     * Generic fallback for any undefined service
     */
    @GetMapping("/**")
    @PostMapping("/**")
    public Mono<ResponseEntity<Map<String, Object>>> genericFallback() {
        log.warn("Generic fallback triggered - unknown service or route");
        return Mono.just(createServiceUnavailableResponse(
            "Service is temporarily unavailable",
            "The requested service is experiencing issues. Please try again later.",
            "unknown"
        ));
    }

    /**
     * Helper method to create service unavailable response
     */
    private ResponseEntity<Map<String, Object>> createServiceUnavailableResponse(
            String error, String message, String service) {
        return ResponseEntity
            .status(HttpStatus.SERVICE_UNAVAILABLE)
            .body(Map.of(
                ERROR_KEY, error,
                MESSAGE_KEY, message,
                SERVICE_KEY, service,
                TIMESTAMP_KEY, Instant.now().toString(),
                STATUS_KEY, HttpStatus.SERVICE_UNAVAILABLE.value()
            ));
    }
}
