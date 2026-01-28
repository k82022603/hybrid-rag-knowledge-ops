package com.knowledge.backend.service;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.time.Instant;
import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import com.knowledge.backend.api.dto.SearchResponse;
import com.knowledge.backend.api.dto.search.ChatSearchRequest;
import com.knowledge.backend.api.dto.search.SearchHistoryResponse;
import com.knowledge.backend.client.AIServiceClient;
import com.knowledge.backend.domain.entity.SearchHistory;
import com.knowledge.backend.domain.repository.SearchHistoryRepository;

import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;
import reactor.test.StepVerifier;

/**
 * Unit tests for SearchService
 *
 * <p>Tests search operations with mocked AI Service client and repository.
 * Covers hybrid search, chat search, stream search, history, and fallbacks.
 */
@ExtendWith(MockitoExtension.class)
class SearchServiceTest {

    @Mock
    private AIServiceClient aiServiceClient;

    @Mock
    private SearchHistoryRepository searchHistoryRepository;

    @InjectMocks
    private SearchService searchService;

    private SearchResponse mockSearchResponse;
    private String testUserId;
    private UUID testUserUuid;

    @BeforeEach
    void setUp() {
        testUserUuid = UUID.randomUUID();
        testUserId = testUserUuid.toString();

        mockSearchResponse = SearchResponse.builder()
                .query("test query")
                .results(List.of(
                        SearchResponse.SearchResult.builder()
                                .documentId("doc-1")
                                .title("Test Document")
                                .content("Test content")
                                .snippet("Test snippet")
                                .score(0.95)
                                .documentType("guide")
                                .build()
                ))
                .totalCount(1)
                .processingTimeMs(100L)
                .timestamp(Instant.now())
                .build();
    }

    @Nested
    @DisplayName("Hybrid Search Tests")
    class HybridSearchTests {

        @Test
        @DisplayName("Should perform hybrid search successfully and save history")
        void shouldPerformHybridSearchSuccessfully() {
            // Given
            String query = "test query";
            Integer topK = 10;
            Boolean useGraph = true;
            Boolean useVector = true;

            when(aiServiceClient.hybridSearch(query, topK, useGraph, useVector, testUserId))
                    .thenReturn(Mono.just(mockSearchResponse));
            when(searchHistoryRepository.save(any(SearchHistory.class)))
                    .thenReturn(Mono.just(SearchHistory.builder()
                            .id(UUID.randomUUID())
                            .userId(testUserUuid)
                            .queryText(query)
                            .build()));

            // When & Then
            StepVerifier.create(searchService.hybridSearch(query, topK, useGraph, useVector, testUserId))
                    .expectNextMatches(response -> {
                        return response.getQuery().equals("test query") &&
                               response.getTotalCount() == 1 &&
                               response.getResults().size() == 1 &&
                               response.getResults().get(0).getTitle().equals("Test Document");
                    })
                    .verifyComplete();

            verify(searchHistoryRepository).save(any(SearchHistory.class));
        }

        @Test
        @DisplayName("Should skip history save when userId is null")
        void shouldSkipHistorySaveWhenUserIdNull() {
            // Given
            String query = "test query";
            Integer topK = 10;
            Boolean useGraph = true;
            Boolean useVector = true;

            when(aiServiceClient.hybridSearch(query, topK, useGraph, useVector, null))
                    .thenReturn(Mono.just(mockSearchResponse));

            // When & Then
            StepVerifier.create(searchService.hybridSearch(query, topK, useGraph, useVector, null))
                    .expectNextMatches(response -> response.getQuery().equals("test query"))
                    .verifyComplete();

            verify(searchHistoryRepository, never()).save(any(SearchHistory.class));
        }

        @Test
        @DisplayName("Should return fallback response when AI Service is unavailable")
        void shouldReturnFallbackWhenAIServiceUnavailable() {
            // Given
            String query = "test query";
            Integer topK = 10;
            Boolean useGraph = true;
            Boolean useVector = true;
            Throwable error = new RuntimeException("AI Service unavailable");

            // When & Then - call fallback directly
            StepVerifier.create(searchService.hybridSearchFallback(
                    query, topK, useGraph, useVector, testUserId, error))
                    .expectNextMatches(response -> {
                        return response.getQuery().equals("test query") &&
                               response.getTotalCount() == 0 &&
                               response.getResults().isEmpty() &&
                               response.getTimestamp() != null;
                    })
                    .verifyComplete();
        }
    }

    @Nested
    @DisplayName("Chat Search Tests")
    class ChatSearchTests {

        @Test
        @DisplayName("Should perform chat search successfully and save history")
        void shouldPerformChatSearchSuccessfully() {
            // Given
            String query = "What is Spring Boot?";
            List<ChatSearchRequest.ChatMessage> history = List.of(
                    ChatSearchRequest.ChatMessage.builder()
                            .role("user")
                            .content("Tell me about Java")
                            .build(),
                    ChatSearchRequest.ChatMessage.builder()
                            .role("assistant")
                            .content("Java is a programming language...")
                            .build()
            );
            Integer topK = 5;

            when(aiServiceClient.chatSearch(query, history, topK, testUserId))
                    .thenReturn(Mono.just(mockSearchResponse));
            when(searchHistoryRepository.save(any(SearchHistory.class)))
                    .thenReturn(Mono.just(SearchHistory.builder()
                            .id(UUID.randomUUID())
                            .userId(testUserUuid)
                            .queryText(query)
                            .build()));

            // When & Then
            StepVerifier.create(searchService.chatSearch(query, history, topK, testUserId))
                    .expectNextMatches(response -> {
                        return response.getQuery().equals("test query") &&
                               response.getTotalCount() == 1;
                    })
                    .verifyComplete();

            verify(searchHistoryRepository).save(any(SearchHistory.class));
        }

        @Test
        @DisplayName("Should return fallback response for chat search failure")
        void shouldReturnFallbackForChatSearchFailure() {
            // Given
            String query = "test query";
            List<ChatSearchRequest.ChatMessage> history = List.of();
            Integer topK = 5;
            Throwable error = new RuntimeException("Connection refused");

            // When & Then
            StepVerifier.create(searchService.chatSearchFallback(
                    query, history, topK, testUserId, error))
                    .expectNextMatches(response -> {
                        return response.getQuery().equals("test query") &&
                               response.getTotalCount() == 0 &&
                               response.getResults().isEmpty();
                    })
                    .verifyComplete();
        }
    }

    @Nested
    @DisplayName("Stream Search Tests")
    class StreamSearchTests {

        @Test
        @DisplayName("Should stream search results successfully")
        void shouldStreamSearchResultsSuccessfully() {
            // Given
            String query = "stream test";
            List<ChatSearchRequest.ChatMessage> history = List.of(
                    ChatSearchRequest.ChatMessage.builder()
                            .role("user")
                            .content("previous question")
                            .build()
            );
            Integer topK = 5;

            when(aiServiceClient.streamSearch(query, history, topK, testUserId))
                    .thenReturn(Flux.just("chunk1", "chunk2", "chunk3"));

            // When & Then
            StepVerifier.create(searchService.streamSearch(query, history, topK, testUserId))
                    .expectNext("chunk1")
                    .expectNext("chunk2")
                    .expectNext("chunk3")
                    .verifyComplete();
        }

        @Test
        @DisplayName("Should return fallback for stream search failure")
        void shouldReturnFallbackForStreamSearchFailure() {
            // Given
            String query = "stream test";
            Throwable error = new RuntimeException("Stream failed");

            // When & Then
            StepVerifier.create(searchService.streamSearchFallback(query, null, null, testUserId, error))
                    .expectNextMatches(chunk -> chunk.contains("temporarily unavailable"))
                    .verifyComplete();
        }
    }

    @Nested
    @DisplayName("Search History Tests")
    class SearchHistoryTests {

        @Test
        @DisplayName("Should get search history for user")
        void shouldGetSearchHistoryForUser() {
            // Given
            SearchHistory history1 = SearchHistory.builder()
                    .id(UUID.randomUUID())
                    .userId(testUserUuid)
                    .queryText("query 1")
                    .intent("hybrid")
                    .resultCount(5)
                    .searchDurationMs(150)
                    .cached(false)
                    .createdAt(LocalDateTime.now())
                    .build();

            SearchHistory history2 = SearchHistory.builder()
                    .id(UUID.randomUUID())
                    .userId(testUserUuid)
                    .queryText("query 2")
                    .intent("chat")
                    .resultCount(3)
                    .searchDurationMs(200)
                    .cached(false)
                    .createdAt(LocalDateTime.now())
                    .build();

            when(searchHistoryRepository.findByUserIdRecent(testUserUuid))
                    .thenReturn(Flux.just(history1, history2));

            // When & Then
            StepVerifier.create(searchService.getSearchHistory(testUserId))
                    .expectNextMatches(response -> {
                        return response.getQueryText().equals("query 1") &&
                               response.getIntent().equals("hybrid") &&
                               response.getResultCount() == 5;
                    })
                    .expectNextMatches(response -> {
                        return response.getQueryText().equals("query 2") &&
                               response.getIntent().equals("chat") &&
                               response.getResultCount() == 3;
                    })
                    .verifyComplete();
        }

        @Test
        @DisplayName("Should return empty for invalid userId format")
        void shouldReturnEmptyForInvalidUserId() {
            // Given
            String invalidUserId = "not-a-uuid";

            // When & Then
            StepVerifier.create(searchService.getSearchHistory(invalidUserId))
                    .verifyComplete();

            verify(searchHistoryRepository, never()).findByUserIdRecent(any(UUID.class));
        }

        @Test
        @DisplayName("Should return empty when no history exists")
        void shouldReturnEmptyWhenNoHistory() {
            // Given
            when(searchHistoryRepository.findByUserIdRecent(testUserUuid))
                    .thenReturn(Flux.empty());

            // When & Then
            StepVerifier.create(searchService.getSearchHistory(testUserId))
                    .verifyComplete();
        }
    }

    @Nested
    @DisplayName("Circuit Breaker Fallback Tests")
    class CircuitBreakerFallbackTests {

        @Test
        @DisplayName("Hybrid search fallback should return empty results with query")
        void hybridSearchFallbackShouldReturnEmptyResults() {
            // Given
            String query = "failing query";
            Throwable error = new RuntimeException("Circuit breaker open");

            // When & Then
            StepVerifier.create(searchService.hybridSearchFallback(
                    query, 10, true, true, testUserId, error))
                    .expectNextMatches(response -> {
                        return response.getQuery().equals("failing query") &&
                               response.getTotalCount() == 0 &&
                               response.getResults().isEmpty() &&
                               response.getProcessingTimeMs() == 0L &&
                               response.getTimestamp() != null;
                    })
                    .verifyComplete();
        }

        @Test
        @DisplayName("Chat search fallback should return empty results with query")
        void chatSearchFallbackShouldReturnEmptyResults() {
            // Given
            String query = "chat failing query";
            List<ChatSearchRequest.ChatMessage> history = List.of(
                    ChatSearchRequest.ChatMessage.builder()
                            .role("user")
                            .content("previous message")
                            .build()
            );
            Throwable error = new RuntimeException("Service timeout");

            // When & Then
            StepVerifier.create(searchService.chatSearchFallback(
                    query, history, 5, testUserId, error))
                    .expectNextMatches(response -> {
                        return response.getQuery().equals("chat failing query") &&
                               response.getTotalCount() == 0 &&
                               response.getResults().isEmpty();
                    })
                    .verifyComplete();
        }

        @Test
        @DisplayName("Stream search fallback should return error message")
        void streamSearchFallbackShouldReturnErrorMessage() {
            // Given
            String query = "stream failing query";
            Throwable error = new RuntimeException("Connection reset");

            // When & Then
            StepVerifier.create(searchService.streamSearchFallback(query, testUserId, error))
                    .expectNextMatches(chunk -> {
                        return chunk.contains("error") &&
                               chunk.contains("temporarily unavailable");
                    })
                    .verifyComplete();
        }
    }
}
