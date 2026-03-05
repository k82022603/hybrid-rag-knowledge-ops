package com.knowledge.gateway.route;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.reactive.WebFluxTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.reactive.server.WebTestClient;

/**
 * Unit tests for FallbackController
 *
 * <p>Tests fallback responses using unified ErrorResponse DTO format
 */
@WebFluxTest(FallbackController.class)
@ActiveProfiles("test")
class FallbackControllerTest {

    @Autowired
    private WebTestClient webTestClient;

    @Test
    @DisplayName("Backend fallback returns 503 with unified ErrorResponse format")
    void backendFallback_Returns503WithErrorResponse() {
        webTestClient.get()
            .uri("/fallback/backend")
            .accept(MediaType.APPLICATION_JSON)
            .exchange()
            .expectStatus().isEqualTo(503)
            .expectBody()
            .jsonPath("$.error").isEqualTo("Backend service is temporarily unavailable")
            .jsonPath("$.status").isEqualTo(503)
            .jsonPath("$.timestamp").exists()
            .jsonPath("$.path").exists()
            .jsonPath("$.traceId").exists();
    }

    @Test
    @DisplayName("Knowledge fallback returns 503 with unified ErrorResponse format")
    void knowledgeFallback_Returns503WithErrorResponse() {
        webTestClient.get()
            .uri("/fallback/knowledge")
            .accept(MediaType.APPLICATION_JSON)
            .exchange()
            .expectStatus().isEqualTo(503)
            .expectBody()
            .jsonPath("$.error").isEqualTo("Knowledge service is temporarily unavailable")
            .jsonPath("$.status").isEqualTo(503)
            .jsonPath("$.path").exists()
            .jsonPath("$.traceId").exists();
    }

    @Test
    @DisplayName("User fallback returns 503 with unified ErrorResponse format")
    void userFallback_Returns503WithErrorResponse() {
        webTestClient.get()
            .uri("/fallback/user")
            .accept(MediaType.APPLICATION_JSON)
            .exchange()
            .expectStatus().isEqualTo(503)
            .expectBody()
            .jsonPath("$.error").isEqualTo("User service is temporarily unavailable")
            .jsonPath("$.status").isEqualTo(503)
            .jsonPath("$.traceId").exists();
    }

    @Test
    @DisplayName("AI service fallback returns 503 with unified ErrorResponse format")
    void aiServiceFallback_Returns503WithErrorResponse() {
        webTestClient.get()
            .uri("/fallback/ai-service")
            .accept(MediaType.APPLICATION_JSON)
            .exchange()
            .expectStatus().isEqualTo(503)
            .expectBody()
            .jsonPath("$.error").isEqualTo("AI service is temporarily unavailable")
            .jsonPath("$.status").isEqualTo(503)
            .jsonPath("$.traceId").exists();
    }

    @Test
    @DisplayName("Search fallback returns 503 with unified ErrorResponse format")
    void searchFallback_Returns503WithErrorResponse() {
        webTestClient.get()
            .uri("/fallback/search")
            .accept(MediaType.APPLICATION_JSON)
            .exchange()
            .expectStatus().isEqualTo(503)
            .expectBody()
            .jsonPath("$.error").isEqualTo("Search service is temporarily unavailable")
            .jsonPath("$.status").isEqualTo(503)
            .jsonPath("$.traceId").exists();
    }

    @Test
    @DisplayName("Health endpoint returns 200 with UP status")
    void health_Returns200WithUpStatus() {
        webTestClient.get()
            .uri("/fallback/health")
            .accept(MediaType.APPLICATION_JSON)
            .exchange()
            .expectStatus().isOk()
            .expectBody()
            .jsonPath("$.status").isEqualTo("UP")
            .jsonPath("$.service").isEqualTo("gateway-fallback")
            .jsonPath("$.timestamp").exists();
    }

    @Test
    @DisplayName("POST request to backend fallback returns 503")
    void backendFallbackPost_Returns503() {
        webTestClient.post()
            .uri("/fallback/backend")
            .accept(MediaType.APPLICATION_JSON)
            .exchange()
            .expectStatus().isEqualTo(503)
            .expectBody()
            .jsonPath("$.error").isEqualTo("Backend service is temporarily unavailable")
            .jsonPath("$.traceId").exists();
    }

    @Test
    @DisplayName("POST request to knowledge fallback returns 503")
    void knowledgeFallbackPost_Returns503() {
        webTestClient.post()
            .uri("/fallback/knowledge")
            .accept(MediaType.APPLICATION_JSON)
            .exchange()
            .expectStatus().isEqualTo(503)
            .expectBody()
            .jsonPath("$.error").isEqualTo("Knowledge service is temporarily unavailable")
            .jsonPath("$.traceId").exists();
    }

    @Test
    @DisplayName("Unknown fallback path returns generic 503 with unified format")
    void unknownFallbackPath_Returns503WithUnifiedFormat() {
        webTestClient.get()
            .uri("/fallback/unknown-service")
            .accept(MediaType.APPLICATION_JSON)
            .exchange()
            .expectStatus().isEqualTo(503)
            .expectBody()
            .jsonPath("$.error").isEqualTo("Service is temporarily unavailable")
            .jsonPath("$.status").isEqualTo(503)
            .jsonPath("$.timestamp").exists()
            .jsonPath("$.path").exists()
            .jsonPath("$.traceId").exists();
    }

    @Test
    @DisplayName("Auth fallback returns 503 with unified ErrorResponse format")
    void authFallback_Returns503WithErrorResponse() {
        webTestClient.get()
            .uri("/fallback/auth")
            .accept(MediaType.APPLICATION_JSON)
            .exchange()
            .expectStatus().isEqualTo(503)
            .expectBody()
            .jsonPath("$.error").isEqualTo("Authentication service is temporarily unavailable")
            .jsonPath("$.status").isEqualTo(503)
            .jsonPath("$.traceId").exists();
    }
}
