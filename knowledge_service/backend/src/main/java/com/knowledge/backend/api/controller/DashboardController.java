package com.knowledge.backend.api.controller;

import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.knowledge.backend.api.dto.dashboard.ActivityResponse;
import com.knowledge.backend.api.dto.dashboard.DashboardStatsResponse;
import com.knowledge.backend.api.dto.dashboard.PopularKnowledgeResponse;
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
 *   <li>GET /api/v1/dashboard/stats     - Get aggregated stats</li>
 *   <li>GET /api/v1/dashboard/popular   - Get popular knowledge items</li>
 *   <li>GET /api/v1/dashboard/activity  - Get recent activity</li>
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
    @GetMapping("/activity")
    @PreAuthorize("hasAnyRole('USER', 'VIEWER', 'DEVELOPER', 'ADMIN')")
    public Flux<ActivityResponse> getActivity(
            @RequestParam(defaultValue = "20") int limit
    ) {
        log.info("GET /dashboard/activity - limit: {}", limit);
        return dashboardService.getRecentActivity(limit);
    }
}
