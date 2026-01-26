package com.knowledge.gateway.config;

import java.util.Arrays;
import java.util.List;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.annotation.Order;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.web.reactive.EnableWebFluxSecurity;
import org.springframework.security.config.web.server.SecurityWebFiltersOrder;
import org.springframework.security.config.web.server.ServerHttpSecurity;
import org.springframework.security.web.server.SecurityWebFilterChain;
import org.springframework.security.web.server.util.matcher.OrServerWebExchangeMatcher;
import org.springframework.security.web.server.util.matcher.PathPatternParserServerWebExchangeMatcher;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.reactive.CorsConfigurationSource;
import org.springframework.web.cors.reactive.UrlBasedCorsConfigurationSource;

import com.knowledge.gateway.filter.JwtAuthenticationFilter;
import com.knowledge.gateway.security.JwtTokenValidator;
import com.knowledge.gateway.security.KeycloakJwtAuthenticationConverter;

import lombok.RequiredArgsConstructor;

/**
 * Gateway Security Configuration
 *
 * <p>Supports dual-token authentication:
 * <ul>
 *   <li><strong>HS256 (self-issued)</strong>: Tokens from Direct Login ({@code /api/v1/auth/login}).
 *       Validated by {@link JwtAuthenticationFilter} before the OAuth2 filter runs.</li>
 *   <li><strong>RS256 (Keycloak)</strong>: Tokens from Keycloak OAuth2 flow.
 *       Validated by Spring OAuth2 Resource Server with {@link KeycloakJwtAuthenticationConverter}.</li>
 * </ul>
 *
 * <p>Two security chains:
 * <ul>
 *   <li>Auth chain (Order 1): {@code /api/auth/**}, {@code /api/v1/auth/**}
 *       - No JWT validation (Backend handles authentication)</li>
 *   <li>Default chain (Order 2): Everything else
 *       - HS256 tokens processed by {@link JwtAuthenticationFilter}
 *       - RS256 tokens processed by OAuth2 Resource Server</li>
 * </ul>
 */
@Configuration
@EnableWebFluxSecurity
@RequiredArgsConstructor
public class SecurityConfig {

    private final KeycloakJwtAuthenticationConverter keycloakJwtAuthenticationConverter;
    private final JwtTokenValidator jwtTokenValidator;

    @Value("${cors.allowed-origins:http://localhost:3000,http://localhost:5173,http://localhost}")
    private String allowedOrigins;

    /**
     * Security chain for /api/auth/** and /api/v1/auth/** endpoints.
     *
     * <p>No JWT validation is applied. These are public endpoints for:
     * <ul>
     *   <li>Direct Login ({@code POST /api/v1/auth/login})</li>
     *   <li>Token Refresh ({@code POST /api/v1/auth/refresh})</li>
     *   <li>Logout ({@code POST /api/v1/auth/logout})</li>
     * </ul>
     * Backend handles its own HS256 token validation for these endpoints.
     */
    @Bean
    @Order(1)
    public SecurityWebFilterChain authSecurityWebFilterChain(ServerHttpSecurity http) {
        return http
            .securityMatcher(new OrServerWebExchangeMatcher(
                new PathPatternParserServerWebExchangeMatcher("/api/auth/**"),
                new PathPatternParserServerWebExchangeMatcher("/api/v1/auth/**")
            ))
            .csrf(ServerHttpSecurity.CsrfSpec::disable)
            .cors(cors -> cors.configurationSource(corsConfigurationSource()))
            .authorizeExchange(exchanges -> exchanges
                .anyExchange().permitAll()
            )
            // No oauth2ResourceServer - allows HS256 tokens to pass through to Backend
            .build();
    }

    /**
     * Default security chain for all other endpoints.
     *
     * <p>Authentication flow:
     * <ol>
     *   <li>{@link JwtAuthenticationFilter} runs first (registered BEFORE AUTHENTICATION order).
     *       If an HS256 token is detected, it validates the token, sets the SecurityContext,
     *       and strips the Authorization header to prevent OAuth2 re-processing.</li>
     *   <li>If no HS256 token (or RS256 token is present), the OAuth2 Resource Server filter
     *       processes the token using Keycloak's JWK Set URI for RS256 validation.</li>
     *   <li>If no token at all, Spring Security's authorization rules determine access
     *       (permitAll for public paths, authenticated for protected paths).</li>
     * </ol>
     */
    @Bean
    @Order(2)
    public SecurityWebFilterChain defaultSecurityWebFilterChain(ServerHttpSecurity http) {
        return http
            .csrf(ServerHttpSecurity.CsrfSpec::disable)
            .cors(cors -> cors.configurationSource(corsConfigurationSource()))
            .authorizeExchange(exchanges -> exchanges
                // Public endpoints
                .pathMatchers("/actuator/health/**").permitAll()
                .pathMatchers("/actuator/info").permitAll()
                .pathMatchers("/actuator/prometheus").permitAll()
                .pathMatchers("/actuator/gateway/**").permitAll()
                .pathMatchers("/fallback/**").permitAll()

                // Keycloak auth endpoints - always public
                .pathMatchers("/auth/**").permitAll()

                // CORS preflight
                .pathMatchers(HttpMethod.OPTIONS).permitAll()

                // Admin endpoints - admin role required
                .pathMatchers("/api/v1/admin/**").hasRole("ADMIN")

                // Debug endpoints - developer or admin
                .pathMatchers("/api/v1/debug/**").hasAnyRole("DEVELOPER", "ADMIN")

                // API endpoints require authentication
                .pathMatchers("/api/**").authenticated()
                .pathMatchers("/ai/**").authenticated()

                // Everything else
                .anyExchange().authenticated()
            )
            // Register HS256 JWT filter BEFORE the OAuth2 authentication filter.
            // This ensures self-issued tokens are validated first, and the Authorization
            // header is stripped before OAuth2 Resource Server tries to parse it as RS256.
            // Note: JwtAuthenticationFilter is NOT a @Component to prevent automatic
            // global WebFilter registration (which would apply it to all security chains).
            .addFilterBefore(
                new JwtAuthenticationFilter(jwtTokenValidator),
                SecurityWebFiltersOrder.AUTHENTICATION
            )
            // OAuth2 Resource Server handles RS256 Keycloak tokens (unchanged)
            .oauth2ResourceServer(oauth2 -> oauth2
                .jwt(jwt -> jwt
                    .jwtAuthenticationConverter(keycloakJwtAuthenticationConverter)
                )
            )
            .build();
    }

    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration configuration = new CorsConfiguration();

        // Parse allowed origins from configuration
        List<String> origins = Arrays.asList(allowedOrigins.split(","));
        configuration.setAllowedOrigins(origins);

        configuration.setAllowedMethods(Arrays.asList(
            "GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"
        ));

        configuration.setAllowedHeaders(Arrays.asList(
            "Authorization",
            "Content-Type",
            "Accept",
            "Origin",
            "X-Requested-With",
            "Access-Control-Request-Method",
            "Access-Control-Request-Headers"
        ));

        configuration.setExposedHeaders(Arrays.asList(
            "Access-Control-Allow-Origin",
            "Access-Control-Allow-Credentials",
            "X-Request-Id"
        ));

        configuration.setAllowCredentials(true);
        configuration.setMaxAge(3600L);

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", configuration);

        return source;
    }
}
