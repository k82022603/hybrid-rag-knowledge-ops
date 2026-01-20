package com.knowledge.gateway.filter;

import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.http.HttpHeaders;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.util.UUID;

/**
 * Global Logging Filter
 *
 * <p>Logs all incoming requests and adds correlation ID
 */
@Component
@Slf4j
public class LoggingFilter implements GlobalFilter, Ordered {

    private static final String CORRELATION_ID_HEADER = "X-Correlation-ID";
    private static final String REQUEST_TIME_ATTR = "requestTime";

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        // Generate or get correlation ID
        String correlationId = exchange.getRequest()
            .getHeaders()
            .getFirst(CORRELATION_ID_HEADER);

        if (correlationId == null || correlationId.isEmpty()) {
            correlationId = UUID.randomUUID().toString();
        }

        String finalCorrelationId = correlationId;
        long startTime = System.currentTimeMillis();

        // Add correlation ID to response headers
        exchange.getResponse().getHeaders().add(CORRELATION_ID_HEADER, finalCorrelationId);

        // Log request
        log.info("[{}] Incoming request: {} {} from {}",
            finalCorrelationId,
            exchange.getRequest().getMethod(),
            exchange.getRequest().getPath(),
            exchange.getRequest().getRemoteAddress());

        return chain.filter(exchange)
            .doFinally(signalType -> {
                long duration = System.currentTimeMillis() - startTime;
                log.info("[{}] Response: {} {} - Status: {} - Duration: {}ms",
                    finalCorrelationId,
                    exchange.getRequest().getMethod(),
                    exchange.getRequest().getPath(),
                    exchange.getResponse().getStatusCode(),
                    duration);
            });
    }

    @Override
    public int getOrder() {
        return Ordered.HIGHEST_PRECEDENCE;
    }
}
