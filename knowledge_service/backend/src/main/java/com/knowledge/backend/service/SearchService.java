package com.knowledge.backend.service;

import com.knowledge.backend.api.dto.SearchRequest;
import com.knowledge.backend.api.dto.SearchResponse;
import com.knowledge.backend.api.dto.search.ChatSearchRequest;
import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;
import io.github.resilience4j.retry.annotation.Retry;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

import java.time.Instant;
import java.util.List;

/**
 * Search Service
 *
 * <p>Handles search operations by communicating with AI Service
 * - Circuit breaker for fault tolerance
 * - Retry mechanism for transient failures
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class SearchService {

    private final WebClient aiServiceWebClient;

    /**
     * Perform hybrid search (Vector + Graph)
     *
     * @param request search request
     * @param userId user ID for access control
     * @return search response
     */
    @CircuitBreaker(name = "ai-service", fallbackMethod = "hybridSearchFallback")
    @Retry(name = "ai-service")
    public Mono<SearchResponse> hybridSearch(SearchRequest request, String userId) {
        log.debug("Performing hybrid search for user: {}, query: {}", userId, request.getQuery());

        long startTime = System.currentTimeMillis();

        return aiServiceWebClient.post()
            .uri("/api/v1/search/hybrid")
            .bodyValue(request)
            .retrieve()
            .bodyToMono(SearchResponse.class)
            .doOnSuccess(response -> {
                long processingTime = System.currentTimeMillis() - startTime;
                log.info("Hybrid search completed in {}ms, results: {}",
                    processingTime, response.getTotalCount());
            })
            .doOnError(error -> log.error("Hybrid search failed: {}", error.getMessage()));
    }

    /**
     * Fallback method for hybrid search
     */
    public Mono<SearchResponse> hybridSearchFallback(SearchRequest request, String userId, Throwable t) {
        log.warn("Hybrid search fallback triggered for query: {}, reason: {}",
            request.getQuery(), t.getMessage());

        return Mono.just(SearchResponse.builder()
            .query(request.getQuery())
            .results(List.of())
            .totalCount(0)
            .processingTimeMs(0L)
            .timestamp(Instant.now())
            .build());
    }

    /**
     * Chat-based conversational search
     *
     * @param request chat search request with conversation history
     * @param userId user ID for access control
     * @return search response
     */
    @CircuitBreaker(name = "ai-service", fallbackMethod = "chatSearchFallback")
    @Retry(name = "ai-service")
    public Mono<SearchResponse> chatSearch(ChatSearchRequest request, String userId) {
        log.debug("Performing chat search for user: {}, query: {}", userId, request.getQuery());

        long startTime = System.currentTimeMillis();

        return aiServiceWebClient.post()
            .uri("/api/v1/search/chat")
            .bodyValue(request)
            .retrieve()
            .bodyToMono(SearchResponse.class)
            .doOnSuccess(response -> {
                long processingTime = System.currentTimeMillis() - startTime;
                log.info("Chat search completed in {}ms, results: {}",
                    processingTime, response.getTotalCount());
            })
            .doOnError(error -> log.error("Chat search failed: {}", error.getMessage()));
    }

    /**
     * Fallback method for chat search
     */
    public Mono<SearchResponse> chatSearchFallback(ChatSearchRequest request, String userId, Throwable t) {
        log.warn("Chat search fallback triggered for query: {}, reason: {}",
            request.getQuery(), t.getMessage());

        return Mono.just(SearchResponse.builder()
            .query(request.getQuery())
            .results(List.of())
            .totalCount(0)
            .processingTimeMs(0L)
            .timestamp(Instant.now())
            .build());
    }

    /**
     * Stream search results via SSE
     *
     * @param query search query
     * @param userId user ID for access control
     * @return flux of search result chunks
     */
    @CircuitBreaker(name = "ai-service", fallbackMethod = "streamSearchFallback")
    public Flux<String> streamSearch(String query, String userId) {
        log.debug("Starting stream search for user: {}, query: {}", userId, query);

        return aiServiceWebClient.get()
            .uri(uriBuilder -> uriBuilder
                .path("/api/v1/search/stream")
                .queryParam("query", query)
                .build())
            .retrieve()
            .bodyToFlux(String.class)
            .doOnComplete(() -> log.info("Stream search completed for query: {}", query))
            .doOnError(error -> log.error("Stream search failed: {}", error.getMessage()));
    }

    /**
     * Fallback method for stream search
     */
    public Flux<String> streamSearchFallback(String query, String userId, Throwable t) {
        log.warn("Stream search fallback triggered for query: {}, reason: {}",
            query, t.getMessage());

        return Flux.just("{\"error\": \"Service temporarily unavailable\"}");
    }
}
