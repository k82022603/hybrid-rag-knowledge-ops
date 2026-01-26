package com.knowledge.gateway.filter;

import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.ReactiveSecurityContextHolder;
import org.springframework.web.server.ServerWebExchange;
import org.springframework.web.server.WebFilter;
import org.springframework.web.server.WebFilterChain;

import com.knowledge.gateway.security.JwtTokenValidator;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import reactor.core.publisher.Mono;

/**
 * Spring Security WebFilter for HS256 JWT Authentication at the Gateway.
 *
 * <p>This filter handles dual-token support in the Gateway's security chain:
 * <ul>
 *   <li><strong>HS256</strong>: Self-issued tokens from Direct Login ({@code /api/v1/auth/login}).
 *       Validated directly by this filter using {@link JwtTokenValidator}.
 *       After successful validation, the Authorization header is stripped from the
 *       downstream request to prevent the OAuth2 Resource Server from re-processing it.</li>
 *   <li><strong>RS256</strong>: Keycloak tokens. Left untouched so the existing
 *       Spring OAuth2 Resource Server validates them normally.</li>
 * </ul>
 *
 * <p><strong>Important</strong>: This class is NOT annotated with {@code @Component} to avoid
 * automatic registration as a global WebFilter. It is instantiated and registered explicitly
 * in the Gateway SecurityConfig at {@code SecurityWebFiltersOrder.AUTHENTICATION}, ensuring
 * it only applies to the default security chain (not the auth chain).
 *
 * <p>Processing flow:
 * <ol>
 *   <li>Extract Bearer token from Authorization header</li>
 *   <li>If no token or not HS256: pass through to next filter (OAuth2 handles RS256)</li>
 *   <li>If HS256: validate the token</li>
 *   <li>Valid HS256: set SecurityContext, strip Authorization header, continue</li>
 *   <li>Invalid HS256: return 401 Unauthorized (JSON response)</li>
 * </ol>
 */
@Slf4j
@RequiredArgsConstructor
public class JwtAuthenticationFilter implements WebFilter {

    private final JwtTokenValidator jwtTokenValidator;

    private static final String BEARER_PREFIX = "Bearer ";

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, WebFilterChain chain) {
        ServerHttpRequest request = exchange.getRequest();
        String path = request.getPath().value();

        // Extract Authorization header
        String authHeader = request.getHeaders().getFirst(HttpHeaders.AUTHORIZATION);

        if (authHeader == null || !authHeader.startsWith(BEARER_PREFIX)) {
            // No Bearer token present - pass through
            // Spring Security will handle access control (permitAll vs authenticated)
            return chain.filter(exchange);
        }

        String token = authHeader.substring(BEARER_PREFIX.length());

        // Check if this is a self-issued HS256 token
        if (!jwtTokenValidator.isSelfIssuedToken(token)) {
            // RS256 (Keycloak) token - leave it for OAuth2 Resource Server
            log.debug("RS256 token detected at {}, delegating to OAuth2 Resource Server", path);
            return chain.filter(exchange);
        }

        // HS256 (self-issued) token - validate directly
        log.debug("HS256 token detected at {}, validating with JwtTokenValidator", path);

        if (!jwtTokenValidator.validateToken(token)) {
            log.warn("Invalid HS256 JWT token for path: {}", path);
            return writeUnauthorizedResponse(exchange, "Invalid or expired JWT token");
        }

        // Token is valid - extract user information
        try {
            String userId = jwtTokenValidator.getUserIdFromToken(token);
            String email = jwtTokenValidator.getEmailFromToken(token);
            String username = jwtTokenValidator.getUsernameFromToken(token);
            Set<String> roles = jwtTokenValidator.getRolesFromToken(token);

            log.debug("HS256 token validated - user: {} (id: {}), email: {}, roles: {}",
                username, userId, email, roles);

            // Create Spring Security authorities with ROLE_ prefix
            List<SimpleGrantedAuthority> authorities = roles.stream()
                .map(role -> new SimpleGrantedAuthority("ROLE_" + role.toUpperCase()))
                .collect(Collectors.toList());

            // Build authentication token
            UsernamePasswordAuthenticationToken authentication =
                new UsernamePasswordAuthenticationToken(userId, null, authorities);

            // Strip the Authorization header from the mutated request.
            // This prevents the OAuth2 BearerTokenAuthenticationWebFilter from
            // attempting to re-validate the HS256 token as RS256 (which would fail).
            ServerHttpRequest mutatedRequest = request.mutate()
                .headers(headers -> headers.remove(HttpHeaders.AUTHORIZATION))
                .build();
            ServerWebExchange mutatedExchange = exchange.mutate()
                .request(mutatedRequest)
                .build();

            // Continue the filter chain with the authenticated SecurityContext
            return chain.filter(mutatedExchange)
                .contextWrite(ReactiveSecurityContextHolder.withAuthentication(authentication));

        } catch (Exception e) {
            log.error("Failed to extract claims from HS256 token for path {}: {}",
                path, e.getMessage());
            return writeUnauthorizedResponse(exchange, "Failed to process JWT token");
        }
    }

    /**
     * Write a standardized 401 Unauthorized JSON error response.
     *
     * @param exchange the server web exchange
     * @param message  the error description
     * @return Mono signaling response write completion
     */
    private Mono<Void> writeUnauthorizedResponse(ServerWebExchange exchange, String message) {
        ServerHttpResponse response = exchange.getResponse();
        response.setStatusCode(HttpStatus.UNAUTHORIZED);
        response.getHeaders().setContentType(MediaType.APPLICATION_JSON);

        String path = exchange.getRequest().getPath().value();
        String timestamp = Instant.now().toString();

        String body = String.format(
            "{\"error\":\"UNAUTHORIZED\",\"message\":\"%s\",\"timestamp\":\"%s\",\"path\":\"%s\"}",
            escapeJson(message),
            timestamp,
            escapeJson(path)
        );

        DataBuffer buffer = response.bufferFactory()
            .wrap(body.getBytes(StandardCharsets.UTF_8));
        return response.writeWith(Mono.just(buffer));
    }

    /**
     * Basic JSON string escaping to prevent injection in error responses.
     *
     * @param value the string to escape
     * @return escaped string safe for JSON value inclusion
     */
    private String escapeJson(String value) {
        if (value == null) {
            return "";
        }
        return value
            .replace("\\", "\\\\")
            .replace("\"", "\\\"")
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t");
    }
}
