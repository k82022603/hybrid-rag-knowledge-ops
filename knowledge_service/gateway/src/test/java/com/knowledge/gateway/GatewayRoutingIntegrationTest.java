package com.knowledge.gateway;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.cloud.gateway.route.RouteDefinition;
import org.springframework.cloud.gateway.route.RouteDefinitionLocator;
import org.springframework.test.context.ActiveProfiles;
import reactor.test.StepVerifier;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Integration tests for Gateway Routing Configuration
 *
 * <p>Verifies all route definitions are properly configured
 * with correct predicates, filters, and circuit breakers.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("test")
class GatewayRoutingIntegrationTest {

    @Autowired
    private RouteDefinitionLocator routeDefinitionLocator;

    @Test
    @DisplayName("Application context loads successfully")
    void contextLoads() {
        assertThat(routeDefinitionLocator).isNotNull();
    }

    @Test
    @DisplayName("All expected route IDs are registered")
    void allExpectedRouteIds_AreRegistered() {
        List<String> expectedRouteIds = List.of(
            "auth-service",
            "auth-service-v1",
            "knowledge-service",
            "search-service-stream",
            "search-service",
            "user-service",
            "backend-api",
            "ai-service",
            "keycloak"
        );

        List<String> actualRouteIds = routeDefinitionLocator.getRouteDefinitions()
            .map(RouteDefinition::getId)
            .collectList()
            .block();

        assertThat(actualRouteIds).isNotNull();
        assertThat(actualRouteIds).containsAll(expectedRouteIds);
    }

    @Test
    @DisplayName("Auth service route has correct predicate")
    void authServiceRoute_HasCorrectPredicate() {
        RouteDefinition authRoute = findRouteById("auth-service");
        assertThat(authRoute).isNotNull();
        assertThat(authRoute.getPredicates()).isNotEmpty();
        assertThat(authRoute.getPredicates().get(0).getName()).isEqualTo("Path");
        assertThat(authRoute.getPredicates().get(0).getArgs()).containsValue("/api/auth/**");
    }

    @Test
    @DisplayName("Auth service v1 route has correct predicate")
    void authServiceV1Route_HasCorrectPredicate() {
        RouteDefinition authV1Route = findRouteById("auth-service-v1");
        assertThat(authV1Route).isNotNull();
        assertThat(authV1Route.getPredicates().get(0).getArgs()).containsValue("/api/v1/auth/**");
    }

    @Test
    @DisplayName("Knowledge service route points to backend")
    void knowledgeServiceRoute_PointsToBackend() {
        RouteDefinition route = findRouteById("knowledge-service");
        assertThat(route).isNotNull();
        assertThat(route.getUri().toString()).contains("localhost:8081");
    }

    @Test
    @DisplayName("Search service route points to AI service")
    void searchServiceRoute_PointsToAiService() {
        RouteDefinition route = findRouteById("search-service");
        assertThat(route).isNotNull();
        assertThat(route.getUri().toString()).contains("localhost:8000");
    }

    // internal-ai-service route REMOVED (보안: 설계서에서 "내부 네트워크에서만 접근" 명시)
    // Docker 네트워크(kp-backend)를 통해 직접 통신으로 변경

    @Test
    @DisplayName("Backend API catch-all route has correct predicate")
    void backendApiRoute_HasCorrectPredicate() {
        RouteDefinition route = findRouteById("backend-api");
        assertThat(route).isNotNull();
        assertThat(route.getPredicates().get(0).getArgs()).containsValue("/api/v1/**");
    }

    @Test
    @DisplayName("All protected routes have CircuitBreaker filter")
    void allProtectedRoutes_HaveCircuitBreakerFilter() {
        List<String> routeIds = List.of(
            "auth-service", "auth-service-v1", "knowledge-service",
            "search-service", "user-service", "backend-api"
        );

        for (String routeId : routeIds) {
            RouteDefinition route = findRouteById(routeId);
            assertThat(route)
                .as("Route %s should exist", routeId)
                .isNotNull();
            boolean hasCircuitBreaker = route.getFilters().stream()
                .anyMatch(f -> "CircuitBreaker".equals(f.getName()));
            assertThat(hasCircuitBreaker)
                .as("Route %s should have CircuitBreaker filter", routeId)
                .isTrue();
        }
    }

    @Test
    @DisplayName("All protected routes have RequestRateLimiter filter")
    void allProtectedRoutes_HaveRateLimiterFilter() {
        List<String> routeIds = List.of(
            "auth-service", "auth-service-v1", "knowledge-service",
            "search-service", "user-service", "backend-api"
        );

        for (String routeId : routeIds) {
            RouteDefinition route = findRouteById(routeId);
            assertThat(route).isNotNull();
            boolean hasRateLimiter = route.getFilters().stream()
                .anyMatch(f -> "RequestRateLimiter".equals(f.getName()));
            assertThat(hasRateLimiter)
                .as("Route %s should have RequestRateLimiter filter", routeId)
                .isTrue();
        }
    }

    @Test
    @DisplayName("Authenticated routes have TokenRelay filter")
    void authenticatedRoutes_HaveTokenRelayFilter() {
        List<String> tokenRelayRoutes = List.of(
            "knowledge-service", "search-service", "user-service",
            "backend-api", "ai-service"
        );

        for (String routeId : tokenRelayRoutes) {
            RouteDefinition route = findRouteById(routeId);
            assertThat(route).isNotNull();
            boolean hasTokenRelay = route.getFilters().stream()
                .anyMatch(f -> "TokenRelay".equals(f.getName()));
            assertThat(hasTokenRelay)
                .as("Route %s should have TokenRelay filter", routeId)
                .isTrue();
        }
    }

    @Test
    @DisplayName("Auth routes do NOT have TokenRelay filter")
    void authRoutes_DoNotHaveTokenRelayFilter() {
        List<String> authRoutes = List.of("auth-service", "auth-service-v1");

        for (String routeId : authRoutes) {
            RouteDefinition route = findRouteById(routeId);
            assertThat(route).isNotNull();
            boolean hasTokenRelay = route.getFilters().stream()
                .anyMatch(f -> "TokenRelay".equals(f.getName()));
            assertThat(hasTokenRelay)
                .as("Auth route %s should NOT have TokenRelay filter", routeId)
                .isFalse();
        }
    }

    @Test
    @DisplayName("Route definitions can be loaded without errors")
    void routeDefinitions_CanBeLoaded() {
        StepVerifier.create(routeDefinitionLocator.getRouteDefinitions())
            .thenConsumeWhile(route -> {
                assertThat(route.getId()).isNotBlank();
                assertThat(route.getUri()).isNotNull();
                assertThat(route.getPredicates()).isNotEmpty();
                return true;
            })
            .verifyComplete();
    }

    private RouteDefinition findRouteById(String routeId) {
        return routeDefinitionLocator.getRouteDefinitions()
            .filter(r -> routeId.equals(r.getId()))
            .blockFirst();
    }
}
