package com.knowledge.backend.api.dto.dashboard;

import com.fasterxml.jackson.annotation.JsonInclude;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Dashboard Stats Response DTO
 *
 * <p>Aggregated statistics for the dashboard overview.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class DashboardStatsResponse {

    private long totalDocuments;
    private long totalChunks;
    private long totalUsers;
    private long activeUsers;
    private long totalSearches;
    private long completedDocuments;
    private long pendingDocuments;
    private long failedDocuments;
}
