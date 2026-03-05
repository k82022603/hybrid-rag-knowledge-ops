package com.knowledge.gateway.route;

import com.knowledge.gateway.dto.ErrorResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.time.Instant;
import java.util.Map;

/**
 * Fallback Controller
 *
 * <p>Provides fallback responses when circuit breaker is open or service is unavailable.
 * Uses the unified {@link ErrorResponse} DTO for consistent error format across the Gateway.
 */
@RestController
@RequestMapping("/fallback")
@Slf4j
public class FallbackController {

    /**
     * Fallback for Auth service
     */
    @RequestMapping(value = "/auth", method = {RequestMethod.GET, RequestMethod.POST})
    public Mono<ResponseEntity<ErrorResponse>> authFallback(ServerWebExchange exchange) {
        log.warn("Auth service fallback triggered - circuit breaker open");
        return Mono.just(createFallbackResponse(exchange,
            "Authentication service is temporarily unavailable",
            "Login/logout is currently unavailable. Please try again later."
        ));
    }

    /**
     * Fallback for Backend service
     */
    @RequestMapping(value = "/backend", method = {RequestMethod.GET, RequestMethod.POST})
    public Mono<ResponseEntity<ErrorResponse>> backendFallback(ServerWebExchange exchange) {
        log.warn("Backend service fallback triggered - circuit breaker open");
        return Mono.just(createFallbackResponse(exchange,
            "Backend service is temporarily unavailable",
            "Please try again later."
        ));
    }

    /**
     * Fallback for Knowledge Service
     */
    @RequestMapping(value = "/knowledge", method = {RequestMethod.GET, RequestMethod.POST})
    public Mono<ResponseEntity<ErrorResponse>> knowledgeFallback(ServerWebExchange exchange) {
        log.warn("Knowledge service fallback triggered - circuit breaker open");
        return Mono.just(createFallbackResponse(exchange,
            "Knowledge service is temporarily unavailable",
            "Document management is currently limited. Please try again later."
        ));
    }

    /**
     * Fallback for User Service
     */
    @RequestMapping(value = "/user", method = {RequestMethod.GET, RequestMethod.POST})
    public Mono<ResponseEntity<ErrorResponse>> userFallback(ServerWebExchange exchange) {
        log.warn("User service fallback triggered - circuit breaker open");
        return Mono.just(createFallbackResponse(exchange,
            "User service is temporarily unavailable",
            "User management is currently limited. Please try again later."
        ));
    }

    /**
     * Fallback for AI Service (Search)
     */
    @RequestMapping(value = "/ai-service", method = {RequestMethod.GET, RequestMethod.POST})
    public Mono<ResponseEntity<ErrorResponse>> aiServiceFallback(ServerWebExchange exchange) {
        log.warn("AI service fallback triggered - circuit breaker open");
        return Mono.just(createFallbackResponse(exchange,
            "AI service is temporarily unavailable",
            "Search and RAG functionality is currently limited. Please try again later."
        ));
    }

    /**
     * Fallback for Search Service (alias for AI service search)
     */
    @RequestMapping(value = "/search", method = {RequestMethod.GET, RequestMethod.POST})
    public Mono<ResponseEntity<ErrorResponse>> searchFallback(ServerWebExchange exchange) {
        log.warn("Search service fallback triggered - circuit breaker open");
        return Mono.just(createFallbackResponse(exchange,
            "Search service is temporarily unavailable",
            "Search functionality is currently limited. Please try again later."
        ));
    }

    /**
     * Health check endpoint
     */
    @RequestMapping(value = "/health", method = RequestMethod.GET)
    public Mono<ResponseEntity<Map<String, Object>>> health() {
        return Mono.just(ResponseEntity.ok(Map.of(
            "status", "UP",
            "service", "gateway-fallback",
            "timestamp", Instant.now().toString()
        )));
    }

    /**
     * Generic fallback for any undefined service
     */
    @RequestMapping(value = "/**", method = {RequestMethod.GET, RequestMethod.POST})
    public Mono<ResponseEntity<ErrorResponse>> genericFallback(ServerWebExchange exchange) {
        log.warn("Generic fallback triggered - unknown service or route");
        return Mono.just(createFallbackResponse(exchange,
            "Service is temporarily unavailable",
            "The requested service is experiencing issues. Please try again later."
        ));
    }

    /**
     * Creates a unified 503 fallback response using {@link ErrorResponse}.
     */
    private ResponseEntity<ErrorResponse> createFallbackResponse(
            ServerWebExchange exchange, String error, String message) {
        String traceId = exchange.getRequest().getId();
        String path = exchange.getRequest().getPath().value();

        return ResponseEntity
            .status(HttpStatus.SERVICE_UNAVAILABLE)
            .body(ErrorResponse.of(
                HttpStatus.SERVICE_UNAVAILABLE.value(),
                error,
                message,
                path,
                traceId
            ));
    }
}
