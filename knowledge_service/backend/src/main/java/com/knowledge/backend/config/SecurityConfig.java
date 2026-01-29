package com.knowledge.backend.config;

import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.config.annotation.method.configuration.EnableReactiveMethodSecurity;
import org.springframework.security.config.annotation.web.reactive.EnableWebFluxSecurity;
import org.springframework.security.config.web.server.SecurityWebFiltersOrder;
import org.springframework.security.config.web.server.ServerHttpSecurity;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.ReactiveSecurityContextHolder;
import org.springframework.security.web.server.SecurityWebFilterChain;
import org.springframework.security.web.server.authentication.AuthenticationWebFilter;
import org.springframework.web.server.ServerWebExchange;
import org.springframework.web.server.WebFilter;
import org.springframework.web.server.WebFilterChain;

import com.knowledge.backend.security.JwtTokenProvider;
import com.knowledge.backend.security.JwtUser;
import com.knowledge.backend.security.JwtUserAuthenticationToken;

import lombok.RequiredArgsConstructor;
import reactor.core.publisher.Mono;

/**
 * Spring Security Configuration
 *
 * <p>Supports both:
 * <ul>
 *   <li>Self-issued JWT tokens (for direct login)</li>
 *   <li>Keycloak JWT tokens (for OAuth2 integration)</li>
 * </ul>
 */
@Configuration
@EnableWebFluxSecurity
@EnableReactiveMethodSecurity
@RequiredArgsConstructor
public class SecurityConfig {

    private final JwtTokenProvider jwtTokenProvider;

    @Bean
    public SecurityWebFilterChain securityWebFilterChain(ServerHttpSecurity http) {
        return http
            .csrf(ServerHttpSecurity.CsrfSpec::disable)
            .authorizeExchange(exchanges -> exchanges
                // Actuator endpoints - public
                .pathMatchers("/actuator/health/**").permitAll()
                .pathMatchers("/actuator/info").permitAll()
                .pathMatchers("/actuator/prometheus").permitAll()

                // Health check endpoint - public
                .pathMatchers("/api/v1/health").permitAll()
                .pathMatchers("/api/v1/health/**").permitAll()

                // Auth endpoints - login/refresh are public, logout requires auth
                .pathMatchers("/api/auth/login").permitAll()
                .pathMatchers("/api/auth/refresh").permitAll()
                .pathMatchers("/api/v1/auth/login").permitAll()
                .pathMatchers("/api/v1/auth/refresh").permitAll()
                // Logout requires authentication
                .pathMatchers("/api/auth/logout").authenticated()
                .pathMatchers("/api/v1/auth/logout").authenticated()

                // Admin endpoints - admin role required
                .pathMatchers("/api/v1/admin/**").hasRole("ADMIN")

                // Debug endpoints - developer or admin
                .pathMatchers("/api/v1/debug/**").hasAnyRole("DEVELOPER", "ADMIN")

                // Knowledge/Document management
                .pathMatchers(HttpMethod.GET, "/api/v1/knowledge/**").hasAnyRole("USER", "VIEWER", "DEVELOPER", "ADMIN")
                .pathMatchers(HttpMethod.POST, "/api/v1/knowledge/**").hasAnyRole("USER", "DEVELOPER", "ADMIN")
                .pathMatchers(HttpMethod.PUT, "/api/v1/knowledge/**").hasAnyRole("USER", "DEVELOPER", "ADMIN")
                .pathMatchers(HttpMethod.DELETE, "/api/v1/knowledge/**").hasAnyRole("DEVELOPER", "ADMIN")

                // Legacy document endpoints
                .pathMatchers(HttpMethod.GET, "/api/v1/documents/**").hasAnyRole("USER", "VIEWER", "DEVELOPER", "ADMIN")
                .pathMatchers(HttpMethod.POST, "/api/v1/documents/**").hasAnyRole("USER", "DEVELOPER", "ADMIN")
                .pathMatchers(HttpMethod.PUT, "/api/v1/documents/**").hasAnyRole("USER", "DEVELOPER", "ADMIN")
                .pathMatchers(HttpMethod.DELETE, "/api/v1/documents/**").hasAnyRole("DEVELOPER", "ADMIN")

                // Search endpoints
                .pathMatchers("/api/v1/search/**").hasAnyRole("USER", "VIEWER", "DEVELOPER", "ADMIN")

                // User profile endpoints
                .pathMatchers("/api/v1/users/me/**").authenticated()
                .pathMatchers("/api/v1/users/**").authenticated()

                // Bookmark endpoints
                .pathMatchers("/api/v1/bookmarks/**").authenticated()

                // Dashboard endpoints
                .pathMatchers("/api/v1/dashboard/**").hasAnyRole("USER", "VIEWER", "DEVELOPER", "ADMIN")

                // Export endpoints
                .pathMatchers("/api/v1/export/**").hasAnyRole("USER", "DEVELOPER", "ADMIN")

                // Graph endpoints
                .pathMatchers("/api/v1/graph/**").hasAnyRole("USER", "DEVELOPER", "ADMIN")

                // All other API endpoints - authenticated
                .pathMatchers("/api/**").authenticated()

                // Everything else
                .anyExchange().authenticated()
            )
            // Add custom JWT filter before the default security filter
            .addFilterAt(jwtAuthenticationFilter(), SecurityWebFiltersOrder.AUTHENTICATION)
            .build();
    }

    /**
     * Custom JWT Authentication WebFilter for self-issued tokens
     */
    private WebFilter jwtAuthenticationFilter() {
        return (exchange, chain) -> {
            String authHeader = exchange.getRequest().getHeaders().getFirst(HttpHeaders.AUTHORIZATION);

            if (authHeader != null && authHeader.startsWith("Bearer ")) {
                String token = authHeader.substring(7);

                try {
                    if (jwtTokenProvider.validateToken(token)) {
                        Long userId = jwtTokenProvider.getUserIdFromToken(token);
                        String email = jwtTokenProvider.getEmailFromToken(token);
                        String username = jwtTokenProvider.getUsernameFromToken(token);
                        Set<String> roles = jwtTokenProvider.getRolesFromToken(token);

                        // Create authorities with ROLE_ prefix
                        List<SimpleGrantedAuthority> authorities = roles.stream()
                            .map(role -> new SimpleGrantedAuthority("ROLE_" + role.toUpperCase()))
                            .collect(Collectors.toList());

                        // Create JwtUser
                        JwtUser jwtUser = new JwtUser(
                            userId.toString(),
                            username,
                            email,
                            null,
                            null,
                            roles,
                            Set.of(),
                            authorities
                        );

                        // Create authentication token
                        UsernamePasswordAuthenticationToken authToken =
                            new UsernamePasswordAuthenticationToken(jwtUser, null, authorities);

                        return chain.filter(exchange)
                            .contextWrite(ReactiveSecurityContextHolder.withAuthentication(authToken));
                    }
                } catch (Exception e) {
                    // Invalid token, continue with unauthenticated request
                }
            }

            return chain.filter(exchange);
        };
    }
}
