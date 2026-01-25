package com.knowledge.gateway.config;

import java.util.Arrays;
import java.util.List;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.annotation.Order;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.web.reactive.EnableWebFluxSecurity;
import org.springframework.security.config.web.server.ServerHttpSecurity;
import org.springframework.security.web.server.SecurityWebFilterChain;
import org.springframework.security.web.server.util.matcher.OrServerWebExchangeMatcher;
import org.springframework.security.web.server.util.matcher.PathPatternParserServerWebExchangeMatcher;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.reactive.CorsConfigurationSource;
import org.springframework.web.cors.reactive.UrlBasedCorsConfigurationSource;

import com.knowledge.gateway.security.KeycloakJwtAuthenticationConverter;

import lombok.RequiredArgsConstructor;

/**
 * Gateway Security Configuration
 *
 * <p>OAuth2 Resource Server with Keycloak JWT validation
 * <p>Includes CORS configuration and role-based access control
 *
 * <p>Two security chains:
 * <ul>
 *   <li>Auth chain: /api/auth/** - No JWT validation (Backend handles HS256 tokens)</li>
 *   <li>Default chain: Everything else - Keycloak RS256 JWT validation</li>
 * </ul>
 */
@Configuration
@EnableWebFluxSecurity
@RequiredArgsConstructor
public class SecurityConfig {

    private final KeycloakJwtAuthenticationConverter keycloakJwtAuthenticationConverter;

    @Value("${cors.allowed-origins:http://localhost:3000,http://localhost:5173,http://localhost}")
    private String allowedOrigins;

    /**
     * Security chain for /api/auth/** and /api/v1/auth/** endpoints
     * No OAuth2 JWT validation - Backend handles HS256 tokens
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
            // No oauth2ResourceServer - allows HS256 tokens to pass through
            .build();
    }

    /**
     * Default security chain for all other endpoints
     * Uses Keycloak RS256 JWT validation
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
