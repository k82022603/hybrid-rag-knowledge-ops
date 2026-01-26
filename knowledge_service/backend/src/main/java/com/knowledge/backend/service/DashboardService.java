package com.knowledge.backend.service;

import org.springframework.stereotype.Service;

import com.knowledge.backend.api.dto.dashboard.ActivityResponse;
import com.knowledge.backend.api.dto.dashboard.DashboardStatsResponse;
import com.knowledge.backend.api.dto.dashboard.PopularKnowledgeResponse;
import com.knowledge.backend.domain.repository.AuditLogRepository;
import com.knowledge.backend.domain.repository.ChunkRepository;
import com.knowledge.backend.domain.repository.DocumentRepository;
import com.knowledge.backend.domain.repository.KnowledgeUserRepository;
import com.knowledge.backend.domain.repository.SearchHistoryRepository;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

/**
 * Dashboard Service
 *
 * <p>Aggregates statistics and activity data for the dashboard.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class DashboardService {

    private final DocumentRepository documentRepository;
    private final ChunkRepository chunkRepository;
    private final KnowledgeUserRepository knowledgeUserRepository;
    private final SearchHistoryRepository searchHistoryRepository;
    private final AuditLogRepository auditLogRepository;

    /**
     * Get aggregated dashboard statistics
     *
     * @return Mono of DashboardStatsResponse
     */
    public Mono<DashboardStatsResponse> getStats() {
        log.debug("Aggregating dashboard statistics");

        return Mono.zip(
                documentRepository.countTotal().defaultIfEmpty(0L),
                chunkRepository.countTotal().defaultIfEmpty(0L),
                knowledgeUserRepository.countTotal().defaultIfEmpty(0L),
                knowledgeUserRepository.countActive().defaultIfEmpty(0L),
                searchHistoryRepository.countTotal().defaultIfEmpty(0L),
                documentRepository.countByProcessingStatus("completed").defaultIfEmpty(0L),
                documentRepository.countByProcessingStatus("pending").defaultIfEmpty(0L),
                documentRepository.countByProcessingStatus("failed").defaultIfEmpty(0L)
        ).map(tuple -> DashboardStatsResponse.builder()
                .totalDocuments(tuple.getT1())
                .totalChunks(tuple.getT2())
                .totalUsers(tuple.getT3())
                .activeUsers(tuple.getT4())
                .totalSearches(tuple.getT5())
                .completedDocuments(tuple.getT6())
                .pendingDocuments(tuple.getT7())
                .failedDocuments(tuple.getT8())
                .build()
        ).doOnSuccess(stats -> log.info("Dashboard stats: docs={}, users={}, searches={}",
                stats.getTotalDocuments(), stats.getTotalUsers(), stats.getTotalSearches()));
    }

    /**
     * Get popular knowledge items (most recently accessed documents)
     *
     * @param limit max results
     * @return Flux of PopularKnowledgeResponse
     */
    public Flux<PopularKnowledgeResponse> getPopularKnowledge(int limit) {
        log.debug("Getting popular knowledge items, limit: {}", limit);

        return documentRepository.findRecent(limit)
                .map(doc -> PopularKnowledgeResponse.builder()
                        .documentId(doc.getId())
                        .title(doc.getTitle())
                        .documentType(doc.getDocumentType())
                        .searchCount(0)
                        .lastAccessed(doc.getUpdatedAt())
                        .build());
    }

    /**
     * Get recent activity from audit logs
     *
     * @param limit max results
     * @return Flux of ActivityResponse
     */
    public Flux<ActivityResponse> getRecentActivity(int limit) {
        log.debug("Getting recent activity, limit: {}", limit);

        return auditLogRepository.findRecent(limit)
                .map(auditLog -> ActivityResponse.builder()
                        .id(auditLog.getId())
                        .activityType(auditLog.getAction())
                        .description(auditLog.getAction() + " on " + auditLog.getResourceType())
                        .userId(auditLog.getUserId())
                        .resourceId(auditLog.getResourceId())
                        .resourceType(auditLog.getResourceType())
                        .createdAt(auditLog.getCreatedAt())
                        .build());
    }
}
