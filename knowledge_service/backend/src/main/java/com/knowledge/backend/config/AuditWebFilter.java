package com.knowledge.backend.config;

import java.util.Map;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicReference;

import org.springframework.core.Ordered;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatusCode;
import org.springframework.security.authentication.AbstractAuthenticationToken;
import org.springframework.security.core.context.ReactiveSecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import org.springframework.web.server.WebFilter;
import org.springframework.web.server.WebFilterChain;

import com.knowledge.backend.security.JwtUser;
import com.knowledge.backend.service.AuditService;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import reactor.core.publisher.Mono;

/**
 * Audit WebFilter
 *
 * <p>Intercepts API requests and records audit log entries.
 * Only audits /api/** paths (excludes actuator, health checks).
 *
 * <p>Maps HTTP methods to actions and URL patterns to resource types.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class AuditWebFilter implements WebFilter, Ordered {

    private final AuditService auditService;

    /** Resource type mapping by URL path prefix (no trailing slash) */
    private static final Map<String, String> RESOURCE_TYPE_MAP = Map.ofEntries(
            Map.entry("/api/v1/auth", "auth"),
            Map.entry("/api/auth", "auth"),
            Map.entry("/api/v1/knowledge", "document"),
            Map.entry("/api/v1/documents", "document"),
            Map.entry("/api/v1/categories", "document"),
            Map.entry("/api/v1/search", "search"),
            Map.entry("/api/v1/graph", "graph"),
            Map.entry("/api/v1/admin", "admin"),
            Map.entry("/api/v1/users", "user"),
            Map.entry("/api/v1/bookmarks", "bookmark"),
            Map.entry("/api/v1/dashboard", "dashboard"),
            Map.entry("/api/v1/export", "export"),
            Map.entry("/api/v1/cache", "cache")
    );

    @Override
    public int getOrder() {
        // Run after security filters (which are at order -100 to 0)
        return Ordered.LOWEST_PRECEDENCE - 10;
    }

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, WebFilterChain chain) {
        String path = exchange.getRequest().getPath().value();

        // Only audit /api/ endpoints (skip actuator, health, static)
        if (!path.startsWith("/api/")) {
            return chain.filter(exchange);
        }

        // Skip health check endpoints
        if (path.contains("/health")) {
            return chain.filter(exchange);
        }

        long startTime = System.currentTimeMillis();
        HttpMethod method = exchange.getRequest().getMethod();
        String ipAddress = extractIpAddress(exchange);
        String userAgent = exchange.getRequest().getHeaders().getFirst("User-Agent");

        // Use AtomicReference to capture user info from security context
        AtomicReference<JwtUser> userRef = new AtomicReference<>(null);

        // Pre-extract user from X-Auth-* headers as reliable fallback.
        // These headers are always set by Gateway (both HS256 and RS256 paths).
        String headerUserId = exchange.getRequest().getHeaders().getFirst("X-Auth-User-Id");
        if (headerUserId != null && !headerUserId.isEmpty()) {
            String headerEmail = exchange.getRequest().getHeaders().getFirst("X-Auth-User-Email");
            String headerUsername = exchange.getRequest().getHeaders().getFirst("X-Auth-User-Name");
            userRef.set(new JwtUser(
                    headerUserId,
                    headerUsername != null ? headerUsername : "unknown",
                    headerEmail,
                    null, null,
                    java.util.Set.of(),
                    java.util.Set.of(),
                    java.util.List.of()
            ));
        }

        return ReactiveSecurityContextHolder.getContext()
                .doOnNext(ctx -> {
                    if (ctx.getAuthentication() instanceof AbstractAuthenticationToken auth
                            && auth.getPrincipal() instanceof JwtUser jwtUser) {
                        userRef.set(jwtUser);
                    }
                })
                .then(chain.filter(exchange))
                .doFinally(signal -> {
                    int durationMs = (int) (System.currentTimeMillis() - startTime);
                    HttpStatusCode statusCode = exchange.getResponse().getStatusCode();
                    String status = (statusCode != null && statusCode.is2xxSuccessful())
                            ? "success" : "failure";
                    String errorMsg = (statusCode != null && !statusCode.is2xxSuccessful())
                            ? "HTTP " + statusCode.value() : null;

                    UUID userId = null;
                    JwtUser jwtUser = userRef.get();
                    if (jwtUser != null && jwtUser.id() != null) {
                        try {
                            userId = UUID.fromString(jwtUser.id());
                        } catch (IllegalArgumentException ignored) {
                            // Non-UUID user id (e.g., numeric from direct login)
                        }
                    }

                    String action = mapAction(method, path);
                    String resourceType = mapResourceType(path);

                    auditService.log(
                            userId,
                            action,
                            resourceType,
                            null,
                            path,
                            ipAddress,
                            userAgent,
                            status,
                            errorMsg,
                            durationMs
                    );
                });
    }

    private String mapAction(HttpMethod method, String path) {
        if (path.contains("/auth/login")) return "LOGIN";
        if (path.contains("/auth/logout")) return "LOGOUT";
        if (path.contains("/search/")) return "SEARCH";

        if (method == null) return "READ";

        return switch (method.name()) {
            case "GET" -> "READ";
            case "POST" -> "CREATE";
            case "PUT", "PATCH" -> "UPDATE";
            case "DELETE" -> "DELETE";
            default -> "READ";
        };
    }

    private String mapResourceType(String path) {
        for (Map.Entry<String, String> entry : RESOURCE_TYPE_MAP.entrySet()) {
            String key = entry.getKey();
            if (path.equals(key) || path.startsWith(key + "/")) {
                return entry.getValue();
            }
        }
        return "system";
    }

    private String extractIpAddress(ServerWebExchange exchange) {
        // Check X-Forwarded-For header (set by Gateway/Nginx)
        String xff = exchange.getRequest().getHeaders().getFirst("X-Forwarded-For");
        if (xff != null && !xff.isEmpty()) {
            return xff.split(",")[0].trim();
        }
        // Fallback to remote address
        var remoteAddress = exchange.getRequest().getRemoteAddress();
        return remoteAddress != null ? remoteAddress.getAddress().getHostAddress() : "unknown";
    }
}
