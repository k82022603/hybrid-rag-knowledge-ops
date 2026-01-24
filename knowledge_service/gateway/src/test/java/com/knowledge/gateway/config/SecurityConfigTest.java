package com.knowledge.gateway.config;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.reactive.WebFluxTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.security.oauth2.jwt.ReactiveJwtDecoder;
import org.springframework.security.web.server.SecurityWebFilterChain;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.reactive.server.WebTestClient;
import org.springframework.web.cors.reactive.CorsConfigurationSource;

import com.knowledge.gateway.route.FallbackController;
import com.knowledge.gateway.security.KeycloakJwtAuthenticationConverter;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Unit tests for SecurityConfig
 *
 * <p>Tests security configuration including authentication and authorization rules
 */
@WebFluxTest(controllers = FallbackController.class)
@Import({SecurityConfig.class, KeycloakJwtAuthenticationConverter.class})
@ActiveProfiles("test")
class SecurityConfigTest {

    @Autowired
    private WebTestClient webTestClient;

    @Autowired(required = false)
    private SecurityWebFilterChain securityWebFilterChain;

    @Autowired(required = false)
    private CorsConfigurationSource corsConfigurationSource;

    @MockBean
    private ReactiveJwtDecoder jwtDecoder;

    @Test
    @DisplayName("Actuator health endpoint is publicly accessible")
    void actuatorHealth_IsPublic() {
        webTestClient.get()
            .uri("/actuator/health")
            .exchange()
            .expectStatus().isNotFound();  // 404 because endpoint doesn't exist in test
    }

    @Test
    @DisplayName("Fallback endpoints are publicly accessible")
    void fallbackEndpoints_ArePublic() {
        webTestClient.get()
            .uri("/fallback/health")
            .exchange()
            .expectStatus().isOk();
    }

    @Test
    @DisplayName("OPTIONS requests are permitted for CORS preflight")
    void optionsRequests_ArePermitted() {
        webTestClient.options()
            .uri("/api/v1/test")
            .exchange()
            .expectStatus().isNotFound();  // 404 because route doesn't exist, not 401
    }

    @Test
    @DisplayName("SecurityWebFilterChain bean is created")
    void securityWebFilterChain_IsCreated() {
        assertThat(securityWebFilterChain).isNotNull();
    }

    @Test
    @DisplayName("CORS configuration source bean is created")
    void corsConfigurationSource_IsCreated() {
        assertThat(corsConfigurationSource).isNotNull();
    }

    @Test
    @DisplayName("Auth endpoints are publicly accessible")
    void authEndpoints_ArePublic() {
        // /auth/** should not require authentication
        webTestClient.get()
            .uri("/auth/realms/test")
            .exchange()
            .expectStatus().isNotFound();  // 404 because Keycloak is not running
    }
}
