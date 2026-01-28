package com.knowledge.backend.client;

import com.knowledge.backend.api.dto.SearchRequest;
import com.knowledge.backend.api.dto.SearchResponse;
import com.knowledge.backend.api.dto.search.ChatSearchRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientResponseException;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

/**
 * AI Service WebClient
 *
 * <p>Handles communication with the AI Service (FastAPI) for search operations.
 * Provides both synchronous and streaming search capabilities.
 *
 * <p>Endpoints called:
 * <ul>
 *   <li>POST /api/v1/search/hybrid - Hybrid search (Vector + Graph)</li>
 *   <li>POST /api/v1/search/chat - Chat-based conversational search</li>
 *   <li>GET /api/v1/search/stream - SSE streaming search</li>
 * </ul>
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class AIServiceClient {

    private final WebClient aiServiceWebClient;

    /**
     * Perform hybrid search via AI Service
     *
     * @param query search query text
     * @param topK number of top results to return
     * @param useGraph whether to use graph search
     * @param useVector whether to use vector search
     * @param userId user ID for access control
     * @return search response from AI Service
     */
    public Mono<SearchResponse> hybridSearch(
            String query,
            Integer topK,
            Boolean useGraph,
            Boolean useVector,
            String userId
    ) {
        log.debug("Calling AI Service hybrid search - query: {}, topK: {}, userId: {}",
                query, topK, userId);

        SearchRequest aiRequest = SearchRequest.builder()
                .query(query)
                .topK(topK)
                .useGraph(useGraph)
                .useVector(useVector)
                .build();

        return aiServiceWebClient.post()
                .uri("/api/v1/search/hybrid")
                .bodyValue(aiRequest)
                .retrieve()
                .bodyToMono(SearchResponse.class)
                .doOnSuccess(response ->
                        log.debug("AI Service hybrid search returned {} results", response.getTotalCount()))
                .doOnError(WebClientResponseException.class, error ->
                        log.error("AI Service hybrid search error - status: {}, body: {}",
                                error.getStatusCode(), error.getResponseBodyAsString()))
                .doOnError(error ->
                        log.error("AI Service hybrid search failed: {}", error.getMessage()));
    }

    /**
     * Perform chat-based conversational search via AI Service
     *
     * @param query search query text
     * @param history conversation history
     * @param topK number of top results to return
     * @param userId user ID for access control
     * @return search response from AI Service
     */
    public Mono<SearchResponse> chatSearch(
            String query,
            java.util.List<ChatSearchRequest.ChatMessage> history,
            Integer topK,
            String userId
    ) {
        log.debug("Calling AI Service chat search - query: {}, historySize: {}, userId: {}",
                query, history != null ? history.size() : 0, userId);

        ChatSearchRequest aiRequest = ChatSearchRequest.builder()
                .query(query)
                .history(history)
                .topK(topK)
                .build();

        return aiServiceWebClient.post()
                .uri("/api/v1/search/chat")
                .bodyValue(aiRequest)
                .retrieve()
                .bodyToMono(SearchResponse.class)
                .doOnSuccess(response ->
                        log.debug("AI Service chat search returned {} results", response.getTotalCount()))
                .doOnError(WebClientResponseException.class, error ->
                        log.error("AI Service chat search error - status: {}, body: {}",
                                error.getStatusCode(), error.getResponseBodyAsString()))
                .doOnError(error ->
                        log.error("AI Service chat search failed: {}", error.getMessage()));
    }

    /**
     * Stream search results via SSE from AI Service
     *
     * @param query search query text
     * @param userId user ID for access control
     * @return flux of search result chunks as strings
     */
    public Flux<String> streamSearch(String query, String userId) {
        log.debug("Calling AI Service stream search - query: {}, userId: {}", query, userId);

        return aiServiceWebClient.get()
                .uri(uriBuilder -> uriBuilder
                        .path("/api/v1/search/stream")
                        .queryParam("query", query)
                        .queryParam("user_id", userId)
                        .build())
                .retrieve()
                .bodyToFlux(String.class)
                .doOnComplete(() -> log.debug("AI Service stream search completed for query: {}", query))
                .doOnError(error ->
                        log.error("AI Service stream search failed: {}", error.getMessage()));
    }
}
