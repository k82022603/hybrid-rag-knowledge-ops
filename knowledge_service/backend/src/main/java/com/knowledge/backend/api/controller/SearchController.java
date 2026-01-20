package com.knowledge.backend.api.controller;

import com.knowledge.backend.api.dto.SearchRequest;
import com.knowledge.backend.api.dto.SearchResponse;
import com.knowledge.backend.security.JwtUser;
import com.knowledge.backend.service.SearchService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.MediaType;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

/**
 * Search API Controller
 *
 * <p>Provides search endpoints for knowledge retrieval
 * - Hybrid search (Vector + Graph)
 * - SSE streaming for real-time results
 *
 * <p>Requires authentication via Keycloak JWT token
 */
@RestController
@RequestMapping("/api/v1/search")
@RequiredArgsConstructor
@Slf4j
public class SearchController {

    private final SearchService searchService;

    /**
     * Hybrid search endpoint
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
        log.info("Search request from user: {} ({}), query: {}",
            user != null ? user.username() : "anonymous",
            user != null ? user.realmRoles() : "no roles",
            request.getQuery());
        return searchService.hybridSearch(request,
            user != null ? user.id() : null);
    }

    /**
     * SSE streaming search endpoint
     *
     * @param query search query
     * @param user authenticated JWT user
     * @return SSE stream of search chunks
     */
    @GetMapping(value = "/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    @PreAuthorize("hasAnyRole('USER', 'VIEWER', 'DEVELOPER', 'ADMIN')")
    public Flux<ServerSentEvent<String>> streamSearch(
        @RequestParam String query,
        @AuthenticationPrincipal JwtUser user
    ) {
        log.info("Stream search request from user: {} ({}), query: {}",
            user != null ? user.username() : "anonymous",
            user != null ? user.realmRoles() : "no roles",
            query);
        return searchService.streamSearch(query,
            user != null ? user.id() : null)
            .map(chunk -> ServerSentEvent.<String>builder()
                .data(chunk)
                .build());
    }
}
