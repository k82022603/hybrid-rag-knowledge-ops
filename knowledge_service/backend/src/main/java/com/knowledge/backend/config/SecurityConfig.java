package com.knowledge.backend.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.method.configuration.EnableReactiveMethodSecurity;
import org.springframework.security.config.annotation.web.reactive.EnableWebFluxSecurity;
import org.springframework.security.config.web.server.ServerHttpSecurity;
import org.springframework.security.web.server.SecurityWebFilterChain;

import com.knowledge.backend.security.KeycloakJwtAuthenticationConverter;

import lombok.RequiredArgsConstructor;

/**
 * Spring Security Configuration
 *
 * <p>OAuth2 Resource Server with Keycloak JWT validation
 * <p>Role-based access control using Keycloak realm roles
 */
@Configuration
@EnableWebFluxSecurity
@EnableReactiveMethodSecurity
@RequiredArgsConstructor
public class SecurityConfig {

    private final KeycloakJwtAuthenticationConverter keycloakJwtAuthenticationConverter;

    @Bean
    public SecurityWebFilterChain securityWebFilterChain(ServerHttpSecurity http) {
        return http
            .csrf(ServerHttpSecurity.CsrfSpec::disable)
            .authorizeExchange(exchanges -> exchanges
                // Actuator endpoints - public
                .pathMatchers("/actuator/health/**").permitAll()
                .pathMatchers("/actuator/info").permitAll()
                .pathMatchers("/actuator/prometheus").permitAll()

                // Admin endpoints - admin role required
                .pathMatchers("/api/v1/admin/**").hasRole("ADMIN")

                // Debug endpoints - developer or admin
                .pathMatchers("/api/v1/debug/**").hasAnyRole("DEVELOPER", "ADMIN")

                // Document management
                .pathMatchers(HttpMethod.GET, "/api/v1/documents/**").hasAnyRole("USER", "VIEWER", "DEVELOPER", "ADMIN")
                .pathMatchers(HttpMethod.POST, "/api/v1/documents/**").hasAnyRole("USER", "DEVELOPER", "ADMIN")
                .pathMatchers(HttpMethod.PUT, "/api/v1/documents/**").hasAnyRole("USER", "DEVELOPER", "ADMIN")
                .pathMatchers(HttpMethod.DELETE, "/api/v1/documents/**").hasAnyRole("DEVELOPER", "ADMIN")

                // Search endpoints
                .pathMatchers("/api/v1/search/**").hasAnyRole("USER", "VIEWER", "DEVELOPER", "ADMIN")

                // Graph endpoints
                .pathMatchers("/api/v1/graph/**").hasAnyRole("USER", "DEVELOPER", "ADMIN")

                // All other API endpoints - authenticated
                .pathMatchers("/api/**").authenticated()

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
}
