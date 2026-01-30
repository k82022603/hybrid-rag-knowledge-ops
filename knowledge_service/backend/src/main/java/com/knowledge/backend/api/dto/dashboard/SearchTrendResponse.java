package com.knowledge.backend.api.dto.dashboard;

import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Search Trend Response DTO
 *
 * <p>Daily search count for trend analysis.
 * Used by GET /api/v1/dashboard/search-trends endpoint.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class SearchTrendResponse {

    /**
     * Date in YYYY-MM-DD format
     */
    private String date;

    /**
     * Number of searches on this date
     */
    private long count;
}
