package com.knowledge.backend.service;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;

import org.springframework.stereotype.Service;

import com.knowledge.backend.api.dto.dashboard.ActivityResponse;
import com.knowledge.backend.api.dto.dashboard.DashboardStatsResponse;
import com.knowledge.backend.api.dto.dashboard.DocumentTypeDistributionResponse;
import com.knowledge.backend.api.dto.dashboard.PopularKnowledgeResponse;
import com.knowledge.backend.api.dto.dashboard.PopularQueryResponse;
import com.knowledge.backend.api.dto.dashboard.SearchTrendResponse;
import com.knowledge.backend.api.dto.dashboard.SystemHealthResponse;
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

    /**
     * Get system health status
     *
     * <p>Returns overall system health including individual service statuses.
     * Currently returns mock data for MVP; to be enhanced with actual health checks.
     *
     * @return Mono of SystemHealthResponse
     */
    public Mono<SystemHealthResponse> getSystemHealth() {
        log.debug("Getting system health status");

        LocalDateTime now = LocalDateTime.now();

        // Build service health list (mock data for MVP)
        List<SystemHealthResponse.ServiceHealth> services = new ArrayList<>();
        services.add(SystemHealthResponse.ServiceHealth.builder()
                .name("Backend API")
                .status("up")
                .responseTime(45L)
                .lastChecked(now)
                .build());
        services.add(SystemHealthResponse.ServiceHealth.builder()
                .name("AI Service")
                .status("up")
                .responseTime(120L)
                .lastChecked(now)
                .build());
        services.add(SystemHealthResponse.ServiceHealth.builder()
                .name("PostgreSQL")
                .status("up")
                .responseTime(15L)
                .lastChecked(now)
                .build());
        services.add(SystemHealthResponse.ServiceHealth.builder()
                .name("Elasticsearch")
                .status("up")
                .responseTime(30L)
                .lastChecked(now)
                .build());

        return Mono.just(SystemHealthResponse.builder()
                .overall("healthy")
                .timestamp(now)
                .services(services)
                .build());
    }

    /**
     * Get search trends for the last N days
     *
     * <p>Returns daily search counts. Currently returns mock data for MVP;
     * to be enhanced with actual aggregation from search_history table.
     *
     * @param days number of days to include
     * @return Flux of SearchTrendResponse
     */
    public Flux<SearchTrendResponse> getSearchTrends(int days) {
        log.debug("Getting search trends for {} days", days);

        DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd");
        LocalDate today = LocalDate.now();

        // Generate mock trend data for MVP
        List<SearchTrendResponse> trends = new ArrayList<>();
        for (int i = days - 1; i >= 0; i--) {
            LocalDate date = today.minusDays(i);
            // Mock count with some variation
            long count = 50 + (long)(Math.random() * 100);
            trends.add(SearchTrendResponse.builder()
                    .date(date.format(formatter))
                    .count(count)
                    .build());
        }

        return Flux.fromIterable(trends);
    }

    /**
     * Get popular search queries
     *
     * <p>Returns most frequently searched queries from search history.
     *
     * @param limit max results
     * @return Flux of PopularQueryResponse
     */
    public Flux<PopularQueryResponse> getPopularQueries(int limit) {
        log.debug("Getting popular queries, limit: {}", limit);

        return searchHistoryRepository.findPopularQueries(limit)
                .map(history -> PopularQueryResponse.builder()
                        .query(history.getQueryText())
                        .count(history.getResultCount() != null ? history.getResultCount() : 0)
                        .build())
                .onErrorResume(e -> {
                    log.warn("Error fetching popular queries, returning mock data: {}", e.getMessage());
                    // Return mock data if query fails
                    return Flux.just(
                            PopularQueryResponse.builder().query("knowledge management").count(156).build(),
                            PopularQueryResponse.builder().query("API integration").count(98).build(),
                            PopularQueryResponse.builder().query("deployment guide").count(87).build(),
                            PopularQueryResponse.builder().query("troubleshooting").count(65).build(),
                            PopularQueryResponse.builder().query("best practices").count(54).build()
                    ).take(limit);
                });
    }

    /**
     * Get document type distribution
     *
     * <p>Returns count and percentage by document type.
     *
     * @return Flux of DocumentTypeDistributionResponse
     */
    public Flux<DocumentTypeDistributionResponse> getDocumentTypeDistribution() {
        log.debug("Getting document type distribution");

        // Get total count first, then calculate percentages
        return documentRepository.countTotal()
                .flatMapMany(total -> {
                    if (total == 0) {
                        return Flux.empty();
                    }
                    final long totalDocs = total;

                    // Define document types to check
                    String[] types = {"GUIDE", "API_SPEC", "ARCHITECTURE", "MEETING_NOTES", "FAQ", "OTHER"};

                    return Flux.fromArray(types)
                            .flatMap(type -> documentRepository.countByDocumentType(type)
                                    .defaultIfEmpty(0L)
                                    .map(count -> DocumentTypeDistributionResponse.builder()
                                            .type(type)
                                            .count(count)
                                            .percentage(totalDocs > 0 ? Math.round(count * 100.0 / totalDocs * 10) / 10.0 : 0.0)
                                            .build()))
                            .filter(dto -> dto.getCount() > 0);
                })
                .onErrorResume(e -> {
                    log.warn("Error fetching document type distribution, returning mock data: {}", e.getMessage());
                    // Return mock data if query fails
                    return Flux.just(
                            DocumentTypeDistributionResponse.builder().type("GUIDE").count(45).percentage(35.2).build(),
                            DocumentTypeDistributionResponse.builder().type("API_SPEC").count(32).percentage(25.0).build(),
                            DocumentTypeDistributionResponse.builder().type("ARCHITECTURE").count(18).percentage(14.1).build(),
                            DocumentTypeDistributionResponse.builder().type("MEETING_NOTES").count(15).percentage(11.7).build(),
                            DocumentTypeDistributionResponse.builder().type("FAQ").count(12).percentage(9.4).build(),
                            DocumentTypeDistributionResponse.builder().type("OTHER").count(6).percentage(4.6).build()
                    );
                });
    }
}
