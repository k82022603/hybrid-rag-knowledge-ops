package com.knowledge.backend.client;

import com.knowledge.backend.api.dto.SearchRequest;
import com.knowledge.backend.api.dto.SearchResponse;
import com.knowledge.backend.api.dto.search.ChatSearchRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientResponseException;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

import java.util.List;

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
 *   <li>POST /api/v1/search/chat/stream - SSE streaming search (JSON body)</li>
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
     * <p>Sends a POST request with JSON body containing query, conversation history,
     * and topK parameter. Accepts SSE (text/event-stream) response.
     *
     * @param query search query text
     * @param history conversation history (nullable)
     * @param topK number of top results (nullable, defaults to server-side default)
     * @param userId user ID for access control
     * @return flux of search result chunks as strings
     */
    public Flux<String> streamSearch(
            String query,
            List<ChatSearchRequest.ChatMessage> history,
            Integer topK,
            String userId
    ) {
        log.debug("Calling AI Service stream search - query: {}, historySize: {}, topK: {}, userId: {}",
                query, history != null ? history.size() : 0, topK, userId);

        ChatSearchRequest streamRequest = ChatSearchRequest.builder()
                .query(query)
                .history(history)
                .topK(topK != null ? topK : 5)
                .build();

        return aiServiceWebClient.post()
                .uri("/api/v1/search/chat/stream")
                .contentType(MediaType.APPLICATION_JSON)
                .accept(MediaType.TEXT_EVENT_STREAM)
                .bodyValue(streamRequest)
                .retrieve()
                .bodyToFlux(String.class)
                .doOnComplete(() -> log.debug("AI Service stream search completed for query: {}", query))
                .doOnError(error ->
                        log.error("AI Service stream search failed: {}", error.getMessage()));
    }
}
