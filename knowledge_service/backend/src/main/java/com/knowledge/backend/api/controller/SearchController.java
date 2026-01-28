package com.knowledge.backend.api.controller;

import java.util.UUID;
import java.util.regex.Pattern;

import com.knowledge.backend.api.dto.SearchRequest;
import com.knowledge.backend.api.dto.SearchResponse;
import com.knowledge.backend.api.dto.search.ChatSearchRequest;
import com.knowledge.backend.api.dto.search.SearchFeedbackRequest;
import com.knowledge.backend.api.dto.search.SearchFeedbackResponse;
import com.knowledge.backend.api.dto.search.SearchHistoryResponse;
import com.knowledge.backend.api.dto.search.SearchSuggestionResponse;
import com.knowledge.backend.exception.BadRequestException;
import com.knowledge.backend.security.JwtUser;
import com.knowledge.backend.service.SearchService;
import com.knowledge.backend.util.InputSanitizer;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

/**
 * Search API Controller
 *
 * <p>Provides search endpoints for knowledge retrieval.
 * All endpoints require authentication via JWT token.
 *
 * <p>Endpoints:
 * <ul>
 *   <li>POST /api/v1/search/hybrid  - Hybrid search (Vector + Graph)</li>
 *   <li>POST /api/v1/search/chat    - RAG-based conversational search</li>
 *   <li>GET  /api/v1/search/chat/stream - SSE streaming search</li>
 *   <li>GET  /api/v1/search/history  - Search history for authenticated user</li>
 * </ul>
 *
 * <p>Architecture: Controller converts DTOs to domain parameters
 * before calling Service methods (no RequestDTO passed to Service layer).
 */
@RestController
@RequestMapping("/api/v1/search")
@RequiredArgsConstructor
@Validated
@Slf4j
public class SearchController {

    /** Maximum allowed query length for search endpoints */
    private static final int MAX_QUERY_LENGTH = 1000;

    private final SearchService searchService;

    /**
     * Hybrid search endpoint
     *
     * <p>Performs combined Vector + Graph search via AI Service.
     *
     * @param request search request with query and options
     * @param user authenticated JWT user
     * @return search results
     */
    @PostMapping("/hybrid")
    @PreAuthorize("hasAnyRole('USER', 'VIEWER', 'DEVELOPER', 'ADMIN')")
    public Mono<SearchResponse> hybridSearch(
        @Valid @RequestBody SearchRequest request,
        @AuthenticationPrincipal JwtUser user
    ) {
        String userId = user != null ? user.id() : null;
        log.info("Hybrid search from user: {} ({}), query: {}",
            user != null ? user.username() : "anonymous",
            user != null ? user.realmRoles() : "no roles",
            request.getQuery());

        return searchService.hybridSearch(
            request.getQuery(),
            request.getTopK(),
            request.getUseGraph(),
            request.getUseVector(),
            userId
        );
    }

    /**
     * Legacy search endpoint (backward compatibility)
     *
     * <p>Maps to hybrid search for backward compatibility.
     *
     * @param request search request with query and options
     * @param user authenticated JWT user
     * @return search results
     */
    @PostMapping
    @PreAuthorize("hasAnyRole('USER', 'VIEWER', 'DEVELOPER', 'ADMIN')")
    public Mono<SearchResponse> search(
        @Valid @RequestBody SearchRequest request,
        @AuthenticationPrincipal JwtUser user
    ) {
        String userId = user != null ? user.id() : null;
        log.info("Search request from user: {} ({}), query: {}",
            user != null ? user.username() : "anonymous",
            user != null ? user.realmRoles() : "no roles",
            request.getQuery());

        return searchService.hybridSearch(
            request.getQuery(),
            request.getTopK(),
            request.getUseGraph(),
            request.getUseVector(),
            userId
        );
    }

    /**
     * Chat-based conversational search endpoint (AC1)
     *
     * <p>RAG-based search with conversation history context.
     * Calls AI Service and returns results. Saves search history.
     *
     * @param request chat search request with conversation history
     * @param user authenticated JWT user (AC5)
     * @return search results
     */
    @PostMapping("/chat")
    @PreAuthorize("hasAnyRole('USER', 'VIEWER', 'DEVELOPER', 'ADMIN')")
    public Mono<SearchResponse> chatSearch(
        @Valid @RequestBody ChatSearchRequest request,
        @AuthenticationPrincipal JwtUser user
    ) {
        String userId = user != null ? user.id() : null;
        log.info("Chat search from user: {} ({}), query: {}",
            user != null ? user.username() : "anonymous",
            user != null ? user.realmRoles() : "no roles",
            request.getQuery());

        return searchService.chatSearch(
            request.getQuery(),
            request.getHistory(),
            request.getTopK(),
            userId
        );
    }

    /**
     * SSE streaming search endpoint (AC2)
     *
     * <p>Returns search results as Server-Sent Events for real-time streaming.
     * Each chunk is wrapped in a ServerSentEvent.
     *
     * <p>Security: Query input is validated for length (max 1000 chars)
     * and sanitized to remove XSS patterns before processing.
     *
     * @param query search query (max 1000 characters)
     * @param user authenticated JWT user (AC5)
     * @return SSE stream of search chunks
     */
    @GetMapping(value = "/chat/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    @PreAuthorize("hasAnyRole('USER', 'VIEWER', 'DEVELOPER', 'ADMIN')")
    public Flux<ServerSentEvent<String>> streamSearch(
        @RequestParam @Size(max = 1000, message = "Query must not exceed 1000 characters") String query,
        @AuthenticationPrincipal JwtUser user
    ) {
        // Validate and sanitize input
        String sanitizedQuery = validateAndSanitizeQuery(query);

        String userId = user != null ? user.id() : null;
        log.info("Stream search request from user: {} ({}), query: {}",
            user != null ? user.username() : "anonymous",
            user != null ? user.realmRoles() : "no roles",
            sanitizedQuery);

        return searchService.streamSearch(sanitizedQuery, userId)
            .map(chunk -> ServerSentEvent.<String>builder()
                .data(chunk)
                .build());
    }

    /**
     * Legacy streaming endpoint (backward compatibility)
     *
     * <p>Maps to the same stream search for backward compatibility.
     *
     * <p>Security: Query input is validated for length (max 1000 chars)
     * and sanitized to remove XSS patterns before processing.
     *
     * @param query search query (max 1000 characters)
     * @param user authenticated JWT user
     * @return SSE stream of search chunks
     */
    @GetMapping(value = "/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    @PreAuthorize("hasAnyRole('USER', 'VIEWER', 'DEVELOPER', 'ADMIN')")
    public Flux<ServerSentEvent<String>> streamSearchLegacy(
        @RequestParam @Size(max = 1000, message = "Query must not exceed 1000 characters") String query,
        @AuthenticationPrincipal JwtUser user
    ) {
        // Validate and sanitize input
        String sanitizedQuery = validateAndSanitizeQuery(query);

        String userId = user != null ? user.id() : null;
        log.info("Stream search (legacy) from user: {}, query: {}",
            user != null ? user.username() : "anonymous", sanitizedQuery);

        return searchService.streamSearch(sanitizedQuery, userId)
            .map(chunk -> ServerSentEvent.<String>builder()
                .data(chunk)
                .build());
    }

    /**
     * Search history endpoint (AC4)
     *
     * <p>Returns search history for the authenticated user.
     * Results are ordered by creation time (most recent first), limited to 50 entries.
     *
     * @param user authenticated JWT user (AC5)
     * @return list of search history entries
     */
    @GetMapping("/history")
    @PreAuthorize("hasAnyRole('USER', 'VIEWER', 'DEVELOPER', 'ADMIN')")
    public Flux<SearchHistoryResponse> getSearchHistory(
        @AuthenticationPrincipal JwtUser user
    ) {
        String userId = user != null ? user.id() : null;
        log.info("Search history request from user: {}",
            user != null ? user.username() : "anonymous");

        if (userId == null) {
            return Flux.empty();
        }

        return searchService.getSearchHistory(userId);
    }

    /**
     * Search suggestions / autocomplete endpoint
     *
     * <p>Returns search suggestions based on popular and recent queries.
     *
     * @param q partial query text for prefix matching (max 200 characters)
     * @param limit max results (default 10)
     * @return list of search suggestions
     */
    @GetMapping("/suggestions")
    @PreAuthorize("hasAnyRole('USER', 'VIEWER', 'DEVELOPER', 'ADMIN')")
    public Flux<SearchSuggestionResponse> getSearchSuggestions(
        @RequestParam(required = false) @Size(max = 200, message = "Suggestion query must not exceed 200 characters") String q,
        @RequestParam(defaultValue = "10") int limit
    ) {
        String sanitizedQ = (q != null) ? InputSanitizer.sanitize(q) : null;
        log.info("Search suggestions request - q: {}, limit: {}", sanitizedQ, limit);
        return searchService.getSearchSuggestions(sanitizedQ, limit);
    }

    /**
     * Search feedback endpoint
     *
     * <p>Allows users to submit feedback (rating, comments) on search results.
     *
     * @param request feedback data
     * @param user authenticated JWT user
     * @return created feedback response
     */
    @PostMapping("/feedback")
    @PreAuthorize("hasAnyRole('USER', 'DEVELOPER', 'ADMIN')")
    public Mono<ResponseEntity<SearchFeedbackResponse>> submitFeedback(
        @Valid @RequestBody SearchFeedbackRequest request,
        @AuthenticationPrincipal JwtUser user
    ) {
        String userId = user != null ? user.id() : null;
        log.info("Search feedback from user: {} - rating: {}, type: {}",
            user != null ? user.username() : "anonymous",
            request.getRating(), request.getFeedbackType());

        if (userId == null) {
            return Mono.just(ResponseEntity.status(HttpStatus.UNAUTHORIZED).build());
        }

        UUID userUuid;
        try {
            userUuid = UUID.fromString(userId);
        } catch (IllegalArgumentException e) {
            return Mono.just(ResponseEntity.badRequest().build());
        }

        return searchService.submitFeedback(
                userUuid,
                request.getSearchId(),
                request.getDocumentId(),
                request.getRating(),
                InputSanitizer.sanitize(request.getFeedbackType()),
                InputSanitizer.sanitize(request.getComment())
        ).map(response -> ResponseEntity.status(HttpStatus.CREATED).body(response));
    }

    /**
     * Validate and sanitize query input for streaming endpoints.
     *
     * <p>Performs:
     * <ul>
     *   <li>Null/blank check</li>
     *   <li>Length validation (max 1000 characters)</li>
     *   <li>XSS pattern removal (HTML/Script tags)</li>
     * </ul>
     *
     * @param query raw query input
     * @return sanitized query string
     * @throws BadRequestException if query is blank or exceeds max length
     */
    private String validateAndSanitizeQuery(String query) {
        if (query == null || query.isBlank()) {
            throw new BadRequestException("Query parameter is required and must not be blank");
        }
        if (query.length() > MAX_QUERY_LENGTH) {
            throw new BadRequestException(
                "Query must not exceed " + MAX_QUERY_LENGTH + " characters. Current length: " + query.length()
            );
        }
        return InputSanitizer.sanitize(query);
    }
}
