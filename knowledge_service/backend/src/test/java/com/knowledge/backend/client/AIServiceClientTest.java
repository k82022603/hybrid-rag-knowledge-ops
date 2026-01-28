package com.knowledge.backend.client;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

import java.time.Instant;
import java.util.List;
import java.util.function.Function;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClient.RequestBodySpec;
import org.springframework.web.reactive.function.client.WebClient.RequestBodyUriSpec;
import org.springframework.web.reactive.function.client.WebClient.RequestHeadersSpec;
import org.springframework.web.reactive.function.client.WebClient.RequestHeadersUriSpec;
import org.springframework.web.reactive.function.client.WebClient.ResponseSpec;
import org.springframework.web.util.UriBuilder;

import com.knowledge.backend.api.dto.SearchResponse;
import com.knowledge.backend.api.dto.search.ChatSearchRequest;

import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;
import reactor.test.StepVerifier;

/**
 * Unit tests for AIServiceClient
 *
 * <p>Tests WebClient-based communication with AI Service.
 */
@ExtendWith(MockitoExtension.class)
class AIServiceClientTest {

    @Mock
    private WebClient aiServiceWebClient;

    @Mock
    private RequestBodyUriSpec requestBodyUriSpec;

    @Mock
    private RequestBodySpec requestBodySpec;

    @Mock
    private RequestHeadersSpec requestHeadersSpec;

    @Mock
    private RequestHeadersUriSpec requestHeadersUriSpec;

    @Mock
    private ResponseSpec responseSpec;

    private AIServiceClient aiServiceClient;
    private SearchResponse mockResponse;

    @BeforeEach
    void setUp() {
        aiServiceClient = new AIServiceClient(aiServiceWebClient);

        mockResponse = SearchResponse.builder()
                .query("test query")
                .results(List.of(
                        SearchResponse.SearchResult.builder()
                                .documentId("doc-1")
                                .title("Test Result")
                                .content("Test content")
                                .score(0.9)
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
        @DisplayName("Should call AI Service hybrid search endpoint")
        void shouldCallHybridSearchEndpoint() {
            // Given
            when(aiServiceWebClient.post()).thenReturn(requestBodyUriSpec);
            when(requestBodyUriSpec.uri("/api/v1/search/hybrid")).thenReturn(requestBodySpec);
            when(requestBodySpec.bodyValue(any())).thenReturn(requestHeadersSpec);
            when(requestHeadersSpec.retrieve()).thenReturn(responseSpec);
            when(responseSpec.bodyToMono(SearchResponse.class)).thenReturn(Mono.just(mockResponse));

            // When & Then
            StepVerifier.create(aiServiceClient.hybridSearch(
                    "test query", 10, true, true, "user-123"))
                    .expectNextMatches(response -> {
                        return response.getQuery().equals("test query") &&
                               response.getTotalCount() == 1 &&
                               response.getResults().get(0).getTitle().equals("Test Result");
                    })
                    .verifyComplete();
        }

        @Test
        @DisplayName("Should propagate error from AI Service")
        void shouldPropagateErrorFromAIService() {
            // Given
            when(aiServiceWebClient.post()).thenReturn(requestBodyUriSpec);
            when(requestBodyUriSpec.uri("/api/v1/search/hybrid")).thenReturn(requestBodySpec);
            when(requestBodySpec.bodyValue(any())).thenReturn(requestHeadersSpec);
            when(requestHeadersSpec.retrieve()).thenReturn(responseSpec);
            when(responseSpec.bodyToMono(SearchResponse.class))
                    .thenReturn(Mono.error(new RuntimeException("Connection refused")));

            // When & Then
            StepVerifier.create(aiServiceClient.hybridSearch(
                    "test query", 10, true, true, "user-123"))
                    .expectErrorMessage("Connection refused")
                    .verify();
        }
    }

    @Nested
    @DisplayName("Chat Search Tests")
    class ChatSearchTests {

        @Test
        @DisplayName("Should call AI Service chat search endpoint")
        void shouldCallChatSearchEndpoint() {
            // Given
            List<ChatSearchRequest.ChatMessage> history = List.of(
                    ChatSearchRequest.ChatMessage.builder()
                            .role("user")
                            .content("previous question")
                            .build()
            );

            when(aiServiceWebClient.post()).thenReturn(requestBodyUriSpec);
            when(requestBodyUriSpec.uri("/api/v1/search/chat")).thenReturn(requestBodySpec);
            when(requestBodySpec.bodyValue(any())).thenReturn(requestHeadersSpec);
            when(requestHeadersSpec.retrieve()).thenReturn(responseSpec);
            when(responseSpec.bodyToMono(SearchResponse.class)).thenReturn(Mono.just(mockResponse));

            // When & Then
            StepVerifier.create(aiServiceClient.chatSearch(
                    "test query", history, 5, "user-123"))
                    .expectNextMatches(response -> {
                        return response.getQuery().equals("test query") &&
                               response.getTotalCount() == 1;
                    })
                    .verifyComplete();
        }
    }

    @Nested
    @DisplayName("Stream Search Tests")
    class StreamSearchTests {

        @Test
        @DisplayName("Should call AI Service stream search endpoint")
        void shouldCallStreamSearchEndpoint() {
            // Given
            when(aiServiceWebClient.get()).thenReturn(requestHeadersUriSpec);
            when(requestHeadersUriSpec.uri(any(Function.class))).thenReturn(requestHeadersSpec);
            when(requestHeadersSpec.retrieve()).thenReturn(responseSpec);
            when(responseSpec.bodyToFlux(String.class))
                    .thenReturn(Flux.just("chunk1", "chunk2"));

            // When & Then
            StepVerifier.create(aiServiceClient.streamSearch("test query", "user-123"))
                    .expectNext("chunk1")
                    .expectNext("chunk2")
                    .verifyComplete();
        }

        @Test
        @DisplayName("Should handle stream error from AI Service")
        void shouldHandleStreamError() {
            // Given
            when(aiServiceWebClient.get()).thenReturn(requestHeadersUriSpec);
            when(requestHeadersUriSpec.uri(any(Function.class))).thenReturn(requestHeadersSpec);
            when(requestHeadersSpec.retrieve()).thenReturn(responseSpec);
            when(responseSpec.bodyToFlux(String.class))
                    .thenReturn(Flux.error(new RuntimeException("Stream interrupted")));

            // When & Then
            StepVerifier.create(aiServiceClient.streamSearch("test query", "user-123"))
                    .expectErrorMessage("Stream interrupted")
                    .verify();
        }
    }
}
