package com.knowledge.backend.service;

import com.knowledge.backend.api.dto.graph.ExpertSearchResponse;
import com.knowledge.backend.client.AIServiceClient;
import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;
import io.github.resilience4j.retry.annotation.Retry;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;

import java.util.List;

/**
 * Graph Service
 *
 * <p>Handles Knowledge Graph operations including expert search.
 * Communicates with AI Service for graph-based queries.
 *
 * <p>Features:
 * <ul>
 *   <li>Expert search by topic</li>
 *   <li>Circuit Breaker for fault tolerance</li>
 *   <li>Fallback responses on AI Service failure</li>
 * </ul>
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class GraphService {

    private final AIServiceClient aiServiceClient;

    /**
     * Search for experts by topic in Knowledge Graph
     *
     * <p>Queries the Knowledge Graph to find experts with expertise
     * in the specified topic. Results are ranked by relevance score.
     *
     * @param topic the topic to search for experts
     * @param limit maximum number of experts to return
     * @param userId authenticated user ID for access control
     * @return expert search response with ranked results
     */
    @CircuitBreaker(name = "aiService", fallbackMethod = "findExpertsFallback")
    @Retry(name = "aiService")
    public Mono<ExpertSearchResponse> findExperts(String topic, Integer limit, String userId) {
        log.info("Searching experts for topic: {}, limit: {}, user: {}", topic, limit, userId);

        return aiServiceClient.findExperts(topic, limit, userId)
                .doOnSuccess(response ->
                        log.info("Expert search completed - topic: {}, found: {} experts",
                                topic, response.getTotalCount()))
                .doOnError(error ->
                        log.error("Expert search failed for topic: {}, error: {}",
                                topic, error.getMessage()));
    }

    /**
     * Fallback method for expert search when AI Service is unavailable
     *
     * @param topic the topic to search for experts
     * @param limit maximum number of experts to return
     * @param userId authenticated user ID
     * @param t the throwable that triggered the fallback
     * @return fallback response with empty results
     */
    public Mono<ExpertSearchResponse> findExpertsFallback(
            String topic,
            Integer limit,
            String userId,
            Throwable t
    ) {
        log.warn("Expert search fallback triggered for topic: {}, reason: {}",
                topic, t.getMessage());

        return Mono.just(ExpertSearchResponse.builder()
                .topic(topic)
                .experts(List.of())
                .totalCount(0)
                .build());
    }
}
