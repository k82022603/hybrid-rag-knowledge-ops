package com.knowledge.backend.service;

import com.knowledge.backend.api.dto.SearchResponse;
import com.knowledge.backend.api.dto.search.ChatSearchRequest;
import com.knowledge.backend.api.dto.search.SearchFeedbackResponse;
import com.knowledge.backend.api.dto.search.SearchHistoryResponse;
import com.knowledge.backend.api.dto.search.SearchSuggestionResponse;
import com.knowledge.backend.client.AIServiceClient;
import com.knowledge.backend.domain.entity.SearchFeedback;
import com.knowledge.backend.domain.entity.SearchHistory;
import com.knowledge.backend.domain.repository.SearchFeedbackRepository;
import com.knowledge.backend.domain.repository.SearchHistoryRepository;
import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;
import io.github.resilience4j.retry.annotation.Retry;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.time.LocalDateTime;
import java.util.HexFormat;
import java.util.List;
import java.util.UUID;

/**
 * Search Service
 *
 * <p>Handles search operations by communicating with AI Service via AIServiceClient.
 * Provides fault tolerance through Circuit Breaker and Retry mechanisms.
 * Saves search history after successful search operations.
 *
 * <p>Features:
 * <ul>
 *   <li>Hybrid search (Vector + Graph) with Circuit Breaker</li>
 *   <li>Chat-based conversational search with Circuit Breaker</li>
 *   <li>SSE streaming search</li>
 *   <li>Search history recording</li>
 *   <li>Fallback responses on AI Service failure</li>
 * </ul>
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class SearchService {

    private final AIServiceClient aiServiceClient;
    private final SearchHistoryRepository searchHistoryRepository;
    private final SearchFeedbackRepository searchFeedbackRepository;

    /**
     * Perform hybrid search (Vector + Graph)
     *
     * <p>Calls AI Service for hybrid search, saves search history,
     * and returns results. Uses Circuit Breaker for fault tolerance.
     *
     * @param query search query text
     * @param topK number of top results
     * @param useGraph whether to use graph search
     * @param useVector whether to use vector search
     * @param userId authenticated user ID
     * @return search response with results
     */
    @CircuitBreaker(name = "aiService", fallbackMethod = "hybridSearchFallback")
    @Retry(name = "aiService")
    public Mono<SearchResponse> hybridSearch(
            String query,
            Integer topK,
            Boolean useGraph,
            Boolean useVector,
            String userId
    ) {
        log.debug("Performing hybrid search for user: {}, query: {}", userId, query);

        long startTime = System.currentTimeMillis();

        return aiServiceClient.hybridSearch(query, topK, useGraph, useVector, userId)
                .flatMap(response -> {
                    long durationMs = System.currentTimeMillis() - startTime;
                    response.setProcessingTimeMs(durationMs);
                    log.info("Hybrid search completed in {}ms, results: {}",
                            durationMs, response.getTotalCount());

                    return saveSearchHistory(userId, query, "hybrid",
                            response.getTotalCount(), (int) durationMs, false)
                            .thenReturn(response);
                });
    }

    /**
     * Fallback method for hybrid search when AI Service is unavailable
     *
     * @param query search query text
     * @param topK number of top results
     * @param useGraph whether to use graph search
     * @param useVector whether to use vector search
     * @param userId authenticated user ID
     * @param t the throwable that triggered the fallback
     * @return fallback search response with empty results
     */
    public Mono<SearchResponse> hybridSearchFallback(
            String query,
            Integer topK,
            Boolean useGraph,
            Boolean useVector,
            String userId,
            Throwable t
    ) {
        log.warn("Hybrid search fallback triggered for query: {}, reason: {}",
                query, t.getMessage());

        return Mono.just(SearchResponse.builder()
                .query(query)
                .results(List.of())
                .totalCount(0)
                .processingTimeMs(0L)
                .timestamp(Instant.now())
                .build());
    }

    /**
     * Chat-based conversational search
     *
     * <p>Calls AI Service for conversational search with history context,
     * saves search history, and returns results.
     *
     * @param query search query text
     * @param history conversation history
     * @param topK number of top results
     * @param userId authenticated user ID
     * @return search response with results
     */
    @CircuitBreaker(name = "aiService", fallbackMethod = "chatSearchFallback")
    @Retry(name = "aiService")
    public Mono<SearchResponse> chatSearch(
            String query,
            List<ChatSearchRequest.ChatMessage> history,
            Integer topK,
            String userId
    ) {
        log.debug("Performing chat search for user: {}, query: {}", userId, query);

        long startTime = System.currentTimeMillis();

        return aiServiceClient.chatSearch(query, history, topK, userId)
                .flatMap(response -> {
                    long durationMs = System.currentTimeMillis() - startTime;
                    response.setProcessingTimeMs(durationMs);
                    log.info("Chat search completed in {}ms, results: {}",
                            durationMs, response.getTotalCount());

                    return saveSearchHistory(userId, query, "chat",
                            response.getTotalCount(), (int) durationMs, false)
                            .thenReturn(response);
                });
    }

    /**
     * Fallback method for chat search when AI Service is unavailable
     *
     * @param query search query text
     * @param history conversation history
     * @param topK number of top results
     * @param userId authenticated user ID
     * @param t the throwable that triggered the fallback
     * @return fallback search response with empty results
     */
    public Mono<SearchResponse> chatSearchFallback(
            String query,
            List<ChatSearchRequest.ChatMessage> history,
            Integer topK,
            String userId,
            Throwable t
    ) {
        log.warn("Chat search fallback triggered for query: {}, reason: {}",
                query, t.getMessage());

        return Mono.just(SearchResponse.builder()
                .query(query)
                .results(List.of())
                .totalCount(0)
                .processingTimeMs(0L)
                .timestamp(Instant.now())
                .build());
    }

    /**
     * Stream search results via SSE
     *
     * <p>Calls AI Service for streaming search and returns a Flux of result chunks.
     * Supports conversation history and topK parameters for richer context.
     *
     * @param query search query text
     * @param history conversation history (nullable)
     * @param topK number of top results (nullable)
     * @param userId authenticated user ID
     * @return flux of search result chunks as strings
     */
    @CircuitBreaker(name = "aiService", fallbackMethod = "streamSearchFallback")
    public Flux<String> streamSearch(
            String query,
            List<ChatSearchRequest.ChatMessage> history,
            Integer topK,
            String userId
    ) {
        log.debug("Starting stream search for user: {}, query: {}, historySize: {}, topK: {}",
                userId, query, history != null ? history.size() : 0, topK);

        return aiServiceClient.streamSearch(query, history, topK, userId)
                .doOnComplete(() -> {
                    log.info("Stream search completed for query: {}", query);
                    saveSearchHistory(userId, query, "stream", 0, 0, false)
                            .subscribe();
                })
                .doOnError(error ->
                        log.error("Stream search failed: {}", error.getMessage()));
    }

    /**
     * Fallback method for stream search when AI Service is unavailable
     *
     * @param query search query text
     * @param history conversation history (nullable)
     * @param topK number of top results (nullable)
     * @param userId authenticated user ID
     * @param t the throwable that triggered the fallback
     * @return fallback flux with error message
     */
    public Flux<String> streamSearchFallback(
            String query,
            List<ChatSearchRequest.ChatMessage> history,
            Integer topK,
            String userId,
            Throwable t
    ) {
        log.warn("Stream search fallback triggered for query: {}, reason: {}",
                query, t.getMessage());

        return Flux.just("{\"error\": \"Search service is temporarily unavailable. Please try again later.\"}");
    }

    /**
     * Get search history for a user
     *
     * @param userId authenticated user ID
     * @return flux of search history responses
     */
    public Flux<SearchHistoryResponse> getSearchHistory(String userId) {
        log.debug("Getting search history for user: {}", userId);

        try {
            UUID userUuid = UUID.fromString(userId);
            return searchHistoryRepository.findByUserIdRecent(userUuid)
                    .map(SearchHistoryResponse::from)
                    .doOnComplete(() ->
                            log.debug("Search history retrieval completed for user: {}", userId));
        } catch (IllegalArgumentException e) {
            log.warn("Invalid user ID format for search history: {}", userId);
            return Flux.empty();
        }
    }

    /**
     * Get search suggestions based on popular queries
     *
     * <p>Returns popular search queries matching the prefix.
     * If no prefix is provided, returns overall popular queries.
     *
     * @param prefix partial query text for prefix matching (optional)
     * @param limit max number of suggestions
     * @return flux of search suggestions
     */
    public Flux<SearchSuggestionResponse> getSearchSuggestions(String prefix, int limit) {
        log.debug("Getting search suggestions - prefix: {}, limit: {}", prefix, limit);

        if (prefix != null && !prefix.isBlank()) {
            return searchHistoryRepository.findRecent(limit * 5)
                    .filter(h -> h.getQueryText() != null
                            && h.getQueryText().toLowerCase().contains(prefix.toLowerCase()))
                    .distinct()
                    .take(limit)
                    .map(h -> SearchSuggestionResponse.builder()
                            .suggestion(h.getQueryText())
                            .frequency(1L)
                            .build());
        }

        return searchHistoryRepository.findPopularQueries(limit)
                .map(h -> SearchSuggestionResponse.builder()
                        .suggestion(h.getQueryText())
                        .frequency(h.getResultCount() != null ? h.getResultCount().longValue() : 1L)
                        .build());
    }

    /**
     * Submit search feedback
     *
     * @param userId user UUID
     * @param searchId search history ID (optional)
     * @param documentId document ID (optional)
     * @param rating feedback rating (1-5)
     * @param feedbackType type of feedback
     * @param comment optional comment
     * @return Mono of SearchFeedbackResponse
     */
    public Mono<SearchFeedbackResponse> submitFeedback(
            UUID userId,
            UUID searchId,
            UUID documentId,
            Integer rating,
            String feedbackType,
            String comment
    ) {
        log.info("Submitting search feedback: user={}, rating={}, type={}", userId, rating, feedbackType);

        SearchFeedback feedback = SearchFeedback.builder()
                .userId(userId)
                .searchId(searchId)
                .documentId(documentId)
                .rating(rating)
                .feedbackType(feedbackType != null ? feedbackType : "rating")
                .comment(comment)
                .createdAt(LocalDateTime.now())
                .build();

        return searchFeedbackRepository.save(feedback)
                .doOnSuccess(saved -> log.info("Search feedback saved: id={}", saved.getId()))
                .map(SearchFeedbackResponse::from);
    }

    /**
     * Save search history entry
     *
     * @param userId user ID
     * @param queryText the search query text
     * @param intent the search intent type (hybrid, chat, stream)
     * @param resultCount number of results returned
     * @param durationMs search duration in milliseconds
     * @param cached whether the result was from cache
     * @return Mono of saved SearchHistory entity
     */
    private Mono<SearchHistory> saveSearchHistory(
            String userId,
            String queryText,
            String intent,
            Integer resultCount,
            Integer durationMs,
            Boolean cached
    ) {
        if (userId == null) {
            log.debug("Skipping search history save - no user ID");
            return Mono.empty();
        }

        try {
            UUID userUuid = UUID.fromString(userId);
            SearchHistory history = SearchHistory.builder()
                    .userId(userUuid)
                    .queryText(queryText)
                    .queryHash(computeQueryHash(queryText))
                    .intent(intent)
                    .resultCount(resultCount)
                    .searchDurationMs(durationMs)
                    .cached(cached)
                    .createdAt(LocalDateTime.now())
                    .build();

            return searchHistoryRepository.save(history)
                    .doOnSuccess(saved ->
                            log.debug("Search history saved: id={}, query={}", saved.getId(), queryText))
                    .doOnError(error ->
                            log.error("Failed to save search history: {}", error.getMessage()))
                    .onErrorResume(error -> Mono.empty());
        } catch (IllegalArgumentException e) {
            log.warn("Invalid user ID format for search history save: {}", userId);
            return Mono.empty();
        }
    }

    /**
     * Compute SHA-256 hash of query text for deduplication
     *
     * @param queryText the query text
     * @return hex-encoded SHA-256 hash
     */
    private String computeQueryHash(String queryText) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(queryText.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(hash);
        } catch (NoSuchAlgorithmException e) {
            log.warn("SHA-256 not available, using query text as hash");
            return queryText;
        }
    }
}
