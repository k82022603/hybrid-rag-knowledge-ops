package com.knowledge.backend.api.controller;

import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.knowledge.backend.api.dto.dashboard.ActivityResponse;
import com.knowledge.backend.api.dto.dashboard.DashboardStatsResponse;
import com.knowledge.backend.api.dto.dashboard.DocumentTypeDistributionResponse;
import com.knowledge.backend.api.dto.dashboard.PopularKnowledgeResponse;
import com.knowledge.backend.api.dto.dashboard.PopularQueryResponse;
import com.knowledge.backend.api.dto.dashboard.SearchTrendResponse;
import com.knowledge.backend.api.dto.dashboard.SystemHealthResponse;
import com.knowledge.backend.service.DashboardService;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

/**
 * Dashboard API Controller
 *
 * <p>Provides aggregated statistics and activity data for the dashboard.
 *
 * <p>Endpoints:
 * <ul>
 *   <li>GET /api/v1/dashboard/stats           - Get aggregated stats</li>
 *   <li>GET /api/v1/dashboard/popular         - Get popular knowledge items</li>
 *   <li>GET /api/v1/dashboard/activities      - Get recent activity (RESTful plural)</li>
 *   <li>GET /api/v1/dashboard/health          - Get system health status</li>
 *   <li>GET /api/v1/dashboard/search-trends   - Get search trends (last N days)</li>
 *   <li>GET /api/v1/dashboard/popular-queries - Get popular search queries</li>
 *   <li>GET /api/v1/dashboard/document-types  - Get document type distribution</li>
 * </ul>
 */
@Slf4j
@RestController
@RequestMapping("/api/v1/dashboard")
@RequiredArgsConstructor
public class DashboardController {

    private final DashboardService dashboardService;

    /**
     * Get dashboard statistics
     *
     * @return Mono of DashboardStatsResponse
     */
    @GetMapping("/stats")
    @PreAuthorize("hasAnyRole('USER', 'VIEWER', 'DEVELOPER', 'ADMIN')")
    public Mono<ResponseEntity<DashboardStatsResponse>> getStats() {
        log.info("GET /dashboard/stats");

        return dashboardService.getStats()
                .map(ResponseEntity::ok);
    }

    /**
     * Get popular knowledge items
     *
     * @param limit max results (default 10)
     * @return Flux of PopularKnowledgeResponse
     */
    @GetMapping("/popular")
    @PreAuthorize("hasAnyRole('USER', 'VIEWER', 'DEVELOPER', 'ADMIN')")
    public Flux<PopularKnowledgeResponse> getPopular(
            @RequestParam(defaultValue = "10") int limit
    ) {
        log.info("GET /dashboard/popular - limit: {}", limit);
        return dashboardService.getPopularKnowledge(limit);
    }

    /**
     * Get recent activity
     *
     * @param limit max results (default 20)
     * @return Flux of ActivityResponse
     */
    @GetMapping("/activities")
    @PreAuthorize("hasAnyRole('USER', 'VIEWER', 'DEVELOPER', 'ADMIN')")
    public Flux<ActivityResponse> getActivities(
            @RequestParam(defaultValue = "20") int limit
    ) {
        log.info("GET /dashboard/activities - limit: {}", limit);
        return dashboardService.getRecentActivity(limit);
    }

    /**
     * Get system health status
     *
     * <p>Returns overall system health and individual service statuses.
     * Frontend expects: { overall: "healthy"|"degraded"|"unhealthy", services: [...] }
     *
     * @return Mono of SystemHealthResponse
     */
    @GetMapping("/health")
    @PreAuthorize("hasAnyRole('USER', 'VIEWER', 'DEVELOPER', 'ADMIN')")
    public Mono<ResponseEntity<SystemHealthResponse>> getHealth() {
        log.info("GET /dashboard/health");
        return dashboardService.getSystemHealth()
                .map(ResponseEntity::ok);
    }

    /**
     * Get search trends for the last N days
     *
     * <p>Returns daily search counts for trend visualization.
     * Frontend expects: [{ date: "YYYY-MM-DD", count: N }, ...]
     *
     * @param days number of days to include (default 7)
     * @return Flux of SearchTrendResponse
     */
    @GetMapping("/search-trends")
    @PreAuthorize("hasAnyRole('USER', 'VIEWER', 'DEVELOPER', 'ADMIN')")
    public Flux<SearchTrendResponse> getSearchTrends(
            @RequestParam(defaultValue = "7") int days
    ) {
        log.info("GET /dashboard/search-trends - days: {}", days);
        return dashboardService.getSearchTrends(days);
    }

    /**
     * Get popular search queries
     *
     * <p>Returns most frequently searched queries.
     * Frontend expects: [{ query: "...", count: N }, ...]
     *
     * @param limit max results (default 10)
     * @return Flux of PopularQueryResponse
     */
    @GetMapping("/popular-queries")
    @PreAuthorize("hasAnyRole('USER', 'VIEWER', 'DEVELOPER', 'ADMIN')")
    public Flux<PopularQueryResponse> getPopularQueries(
            @RequestParam(defaultValue = "10") int limit
    ) {
        log.info("GET /dashboard/popular-queries - limit: {}", limit);
        return dashboardService.getPopularQueries(limit);
    }

    /**
     * Get document type distribution
     *
     * <p>Returns count and percentage by document type for charts.
     * Frontend expects: [{ type: "...", count: N, percentage: X.X }, ...]
     *
     * @return Flux of DocumentTypeDistributionResponse
     */
    @GetMapping("/document-types")
    @PreAuthorize("hasAnyRole('USER', 'VIEWER', 'DEVELOPER', 'ADMIN')")
    public Flux<DocumentTypeDistributionResponse> getDocumentTypeDistribution() {
        log.info("GET /dashboard/document-types");
        return dashboardService.getDocumentTypeDistribution();
    }
}
