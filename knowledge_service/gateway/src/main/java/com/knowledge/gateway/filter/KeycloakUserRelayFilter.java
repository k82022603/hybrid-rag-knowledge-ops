package com.knowledge.gateway.filter;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.security.core.context.ReactiveSecurityContextHolder;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;

import lombok.extern.slf4j.Slf4j;
import reactor.core.publisher.Mono;

/**
 * GlobalFilter that relays Keycloak user info to downstream services via X-Auth-* headers.
 *
 * <p>When a request is authenticated via Keycloak RS256 token (OAuth2 Resource Server),
 * this filter extracts user information from the JWT and adds X-Auth-* headers
 * so that downstream services (Backend) can identify the user without needing
 * to validate the Keycloak token themselves.
 *
 * <p>This complements {@link JwtAuthenticationFilter} which handles HS256 tokens.
 * Together, both token types result in consistent X-Auth-* headers for the Backend.
 */
@Slf4j
@Component
public class KeycloakUserRelayFilter implements GlobalFilter, Ordered {

    @Override
    public int getOrder() {
        // Run after security filters but before route filters
        return -1;
    }

    @Override
    @SuppressWarnings("unchecked")
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        // Skip if X-Auth-* headers already set (HS256 path handled by JwtAuthenticationFilter)
        if (exchange.getRequest().getHeaders().containsKey("X-Auth-User-Id")) {
            return chain.filter(exchange);
        }

        return ReactiveSecurityContextHolder.getContext()
            .filter(ctx -> ctx.getAuthentication() instanceof JwtAuthenticationToken)
            .map(ctx -> (JwtAuthenticationToken) ctx.getAuthentication())
            .flatMap(auth -> {
                Jwt jwt = auth.getToken();

                String userId = jwt.getSubject();
                String username = jwt.getClaimAsString("preferred_username");
                String email = jwt.getClaimAsString("email");

                // Extract realm roles
                Map<String, Object> realmAccess = jwt.getClaim("realm_access");
                final String roles;
                if (realmAccess != null) {
                    List<String> roleList = (List<String>) realmAccess.get("roles");
                    if (roleList != null && !roleList.isEmpty()) {
                        roles = roleList.stream()
                            .filter(r -> !r.startsWith("default-roles-"))
                            .collect(Collectors.joining(","));
                    } else {
                        roles = "USER";
                    }
                } else {
                    roles = "USER";
                }

                log.debug("Keycloak user relay: user={}, email={}, roles={}", username, email, roles);

                ServerHttpRequest mutatedRequest = exchange.getRequest().mutate()
                    .headers(headers -> {
                        headers.set("X-Auth-User-Id", userId != null ? userId : "");
                        headers.set("X-Auth-User-Email", email != null ? email : "");
                        headers.set("X-Auth-User-Name", username != null ? username : "");
                        headers.set("X-Auth-User-Roles", roles);
                        headers.set("X-Auth-Method", "keycloak");
                    })
                    .build();

                return chain.filter(exchange.mutate().request(mutatedRequest).build());
            })
            .switchIfEmpty(chain.filter(exchange));
    }
}
