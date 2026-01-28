package com.knowledge.backend.api.controller;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;

import java.time.Instant;
import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.reactive.WebFluxTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.web.reactive.server.WebTestClient;

import com.knowledge.backend.api.dto.SearchRequest;
import com.knowledge.backend.api.dto.SearchResponse;
import com.knowledge.backend.api.dto.search.ChatSearchRequest;
import com.knowledge.backend.api.dto.search.SearchHistoryResponse;
import com.knowledge.backend.exception.GlobalExceptionHandler;
import com.knowledge.backend.service.SearchService;

import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

/**
 * Integration tests for SearchController
 *
 * <p>Tests REST endpoints with mocked SearchService using WebFluxTest.
 * Covers all AC requirements:
 * - AC1: POST /api/v1/search/chat
 * - AC2: GET /api/v1/search/chat/stream
 * - AC3: Circuit breaker fallback (tested via SearchServiceTest)
 * - AC4: Search history endpoint
 * - AC5: userId passed with requests
 */
@WebFluxTest(SearchController.class)
@Import(GlobalExceptionHandler.class)
class SearchControllerTest {

    @Autowired
    private WebTestClient webTestClient;

    @MockBean
    private SearchService searchService;

    private SearchResponse mockSearchResponse;

    @BeforeEach
    void setUp() {
        mockSearchResponse = SearchResponse.builder()
                .query("test query")
                .results(List.of(
                        SearchResponse.SearchResult.builder()
                                .documentId("doc-1")
                                .title("Test Document")
                                .content("Test content about Spring Boot")
                                .snippet("Test snippet...")
                                .score(0.95)
                                .documentType("guide")
                                .projectName("knowledge-platform")
                                .relatedDocuments(List.of("doc-2"))
                                .build()
                ))
                .totalCount(1)
                .processingTimeMs(150L)
                .timestamp(Instant.now())
                .build();
    }

    @Nested
    @DisplayName("POST /api/v1/search/chat Tests (AC1)")
    class ChatSearchTests {

        @Test
        @WithMockUser(roles = "USER")
        @DisplayName("Should perform chat search successfully")
        void shouldPerformChatSearchSuccessfully() {
            // Given
            ChatSearchRequest request = ChatSearchRequest.builder()
                    .query("What is Spring Boot?")
                    .topK(5)
                    .history(List.of(
                            ChatSearchRequest.ChatMessage.builder()
                                    .role("user")
                                    .content("Tell me about Java")
                                    .build()
                    ))
                    .build();

            when(searchService.chatSearch(
                    eq("What is Spring Boot?"),
                    any(List.class),
                    eq(5),
                    any()))
                    .thenReturn(Mono.just(mockSearchResponse));

            // When & Then
            webTestClient.post()
                    .uri("/api/v1/search/chat")
                    .contentType(MediaType.APPLICATION_JSON)
                    .bodyValue(request)
                    .exchange()
                    .expectStatus().isOk()
                    .expectBody()
                    .jsonPath("$.query").isEqualTo("test query")
                    .jsonPath("$.totalCount").isEqualTo(1)
                    .jsonPath("$.results[0].title").isEqualTo("Test Document")
                    .jsonPath("$.results[0].score").isEqualTo(0.95)
                    .jsonPath("$.processingTimeMs").isNotEmpty();
        }

        @Test
        @WithMockUser(roles = "USER")
        @DisplayName("Should return 400 for empty query")
        void shouldReturn400ForEmptyQuery() {
            // Given
            ChatSearchRequest request = ChatSearchRequest.builder()
                    .query("")
                    .build();

            // When & Then
            webTestClient.post()
                    .uri("/api/v1/search/chat")
                    .contentType(MediaType.APPLICATION_JSON)
                    .bodyValue(request)
                    .exchange()
                    .expectStatus().isBadRequest()
                    .expectBody()
                    .jsonPath("$.status").isEqualTo(400);
        }

        @Test
        @DisplayName("Should return 401 when not authenticated")
        void shouldReturn401WhenNotAuthenticated() {
            // Given
            ChatSearchRequest request = ChatSearchRequest.builder()
                    .query("test query")
                    .build();

            // When & Then
            webTestClient.post()
                    .uri("/api/v1/search/chat")
                    .contentType(MediaType.APPLICATION_JSON)
                    .bodyValue(request)
                    .exchange()
                    .expectStatus().isUnauthorized();
        }

        @Test
        @WithMockUser(roles = "USER")
        @DisplayName("Should handle chat search with empty history")
        void shouldHandleChatSearchWithEmptyHistory() {
            // Given
            ChatSearchRequest request = ChatSearchRequest.builder()
                    .query("simple query")
                    .topK(10)
                    .build();

            when(searchService.chatSearch(
                    eq("simple query"),
                    any(),
                    eq(10),
                    any()))
                    .thenReturn(Mono.just(mockSearchResponse));

            // When & Then
            webTestClient.post()
                    .uri("/api/v1/search/chat")
                    .contentType(MediaType.APPLICATION_JSON)
                    .bodyValue(request)
                    .exchange()
                    .expectStatus().isOk()
                    .expectBody()
                    .jsonPath("$.totalCount").isEqualTo(1);
        }
    }

    @Nested
    @DisplayName("GET /api/v1/search/chat/stream Tests (AC2)")
    class StreamSearchTests {

        @Test
        @WithMockUser(roles = "USER")
        @DisplayName("Should stream search results via SSE")
        void shouldStreamSearchResultsViaSSE() {
            // Given
            when(searchService.streamSearch(eq("stream query"), any()))
                    .thenReturn(Flux.just(
                            "{\"chunk\": \"part1\"}",
                            "{\"chunk\": \"part2\"}",
                            "{\"chunk\": \"part3\"}"
                    ));

            // When & Then
            webTestClient.get()
                    .uri(uriBuilder -> uriBuilder
                            .path("/api/v1/search/chat/stream")
                            .queryParam("query", "stream query")
                            .build())
                    .accept(MediaType.TEXT_EVENT_STREAM)
                    .exchange()
                    .expectStatus().isOk()
                    .expectHeader().contentTypeCompatibleWith(MediaType.TEXT_EVENT_STREAM);
        }

        @Test
        @DisplayName("Should return 401 for unauthenticated stream request")
        void shouldReturn401ForUnauthenticatedStreamRequest() {
            // When & Then
            webTestClient.get()
                    .uri(uriBuilder -> uriBuilder
                            .path("/api/v1/search/chat/stream")
                            .queryParam("query", "test")
                            .build())
                    .exchange()
                    .expectStatus().isUnauthorized();
        }
    }

    @Nested
    @DisplayName("POST /api/v1/search/hybrid Tests")
    class HybridSearchTests {

        @Test
        @WithMockUser(roles = "USER")
        @DisplayName("Should perform hybrid search successfully")
        void shouldPerformHybridSearchSuccessfully() {
            // Given
            SearchRequest request = SearchRequest.builder()
                    .query("hybrid test query")
                    .topK(10)
                    .useGraph(true)
                    .useVector(true)
                    .build();

            when(searchService.hybridSearch(
                    eq("hybrid test query"),
                    eq(10),
                    eq(true),
                    eq(true),
                    any()))
                    .thenReturn(Mono.just(mockSearchResponse));

            // When & Then
            webTestClient.post()
                    .uri("/api/v1/search/hybrid")
                    .contentType(MediaType.APPLICATION_JSON)
                    .bodyValue(request)
                    .exchange()
                    .expectStatus().isOk()
                    .expectBody()
                    .jsonPath("$.query").isEqualTo("test query")
                    .jsonPath("$.totalCount").isEqualTo(1)
                    .jsonPath("$.results").isArray();
        }

        @Test
        @WithMockUser(roles = "USER")
        @DisplayName("Should return 400 for short query")
        void shouldReturn400ForShortQuery() {
            // Given
            SearchRequest request = SearchRequest.builder()
                    .query("a")
                    .build();

            // When & Then
            webTestClient.post()
                    .uri("/api/v1/search/hybrid")
                    .contentType(MediaType.APPLICATION_JSON)
                    .bodyValue(request)
                    .exchange()
                    .expectStatus().isBadRequest()
                    .expectBody()
                    .jsonPath("$.status").isEqualTo(400)
                    .jsonPath("$.validationErrors.query").exists();
        }
    }

    @Nested
    @DisplayName("GET /api/v1/search/history Tests (AC4)")
    class SearchHistoryTests {

        @Test
        @WithMockUser(roles = "USER")
        @DisplayName("Should get search history for authenticated user")
        void shouldGetSearchHistoryForAuthenticatedUser() {
            // Given
            SearchHistoryResponse history1 = SearchHistoryResponse.builder()
                    .id(UUID.randomUUID())
                    .queryText("query 1")
                    .intent("hybrid")
                    .resultCount(5)
                    .searchDurationMs(150)
                    .cached(false)
                    .createdAt(LocalDateTime.now())
                    .build();

            SearchHistoryResponse history2 = SearchHistoryResponse.builder()
                    .id(UUID.randomUUID())
                    .queryText("query 2")
                    .intent("chat")
                    .resultCount(3)
                    .searchDurationMs(200)
                    .cached(false)
                    .createdAt(LocalDateTime.now())
                    .build();

            when(searchService.getSearchHistory(any()))
                    .thenReturn(Flux.just(history1, history2));

            // When & Then
            webTestClient.get()
                    .uri("/api/v1/search/history")
                    .exchange()
                    .expectStatus().isOk()
                    .expectBody()
                    .jsonPath("$[0].queryText").isEqualTo("query 1")
                    .jsonPath("$[0].intent").isEqualTo("hybrid")
                    .jsonPath("$[0].resultCount").isEqualTo(5)
                    .jsonPath("$[1].queryText").isEqualTo("query 2")
                    .jsonPath("$[1].intent").isEqualTo("chat")
                    .jsonPath("$[1].resultCount").isEqualTo(3);
        }

        @Test
        @DisplayName("Should return 401 for unauthenticated history request")
        void shouldReturn401ForUnauthenticatedHistoryRequest() {
            // When & Then
            webTestClient.get()
                    .uri("/api/v1/search/history")
                    .exchange()
                    .expectStatus().isUnauthorized();
        }

        @Test
        @WithMockUser(roles = "USER")
        @DisplayName("Should return empty list when no history exists")
        void shouldReturnEmptyListWhenNoHistory() {
            // Given
            when(searchService.getSearchHistory(any()))
                    .thenReturn(Flux.empty());

            // When & Then
            webTestClient.get()
                    .uri("/api/v1/search/history")
                    .exchange()
                    .expectStatus().isOk()
                    .expectBody()
                    .jsonPath("$").isArray()
                    .jsonPath("$").isEmpty();
        }
    }

    @Nested
    @DisplayName("Authentication Tests (AC5)")
    class AuthenticationTests {

        @Test
        @WithMockUser(roles = "ADMIN")
        @DisplayName("Should allow ADMIN role to search")
        void shouldAllowAdminRoleToSearch() {
            // Given
            ChatSearchRequest request = ChatSearchRequest.builder()
                    .query("admin query")
                    .topK(5)
                    .build();

            when(searchService.chatSearch(any(), any(), anyInt(), any()))
                    .thenReturn(Mono.just(mockSearchResponse));

            // When & Then
            webTestClient.post()
                    .uri("/api/v1/search/chat")
                    .contentType(MediaType.APPLICATION_JSON)
                    .bodyValue(request)
                    .exchange()
                    .expectStatus().isOk();
        }

        @Test
        @WithMockUser(roles = "DEVELOPER")
        @DisplayName("Should allow DEVELOPER role to search")
        void shouldAllowDeveloperRoleToSearch() {
            // Given
            ChatSearchRequest request = ChatSearchRequest.builder()
                    .query("developer query")
                    .topK(5)
                    .build();

            when(searchService.chatSearch(any(), any(), anyInt(), any()))
                    .thenReturn(Mono.just(mockSearchResponse));

            // When & Then
            webTestClient.post()
                    .uri("/api/v1/search/chat")
                    .contentType(MediaType.APPLICATION_JSON)
                    .bodyValue(request)
                    .exchange()
                    .expectStatus().isOk();
        }

        @Test
        @WithMockUser(roles = "VIEWER")
        @DisplayName("Should allow VIEWER role to access history")
        void shouldAllowViewerRoleToAccessHistory() {
            // Given
            when(searchService.getSearchHistory(any()))
                    .thenReturn(Flux.empty());

            // When & Then
            webTestClient.get()
                    .uri("/api/v1/search/history")
                    .exchange()
                    .expectStatus().isOk();
        }
    }
}
