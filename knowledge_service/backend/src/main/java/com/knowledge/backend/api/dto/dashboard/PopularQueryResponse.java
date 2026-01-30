package com.knowledge.backend.api.dto.dashboard;

import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Popular Query Response DTO
 *
 * <p>Popular search query with count.
 * Used by GET /api/v1/dashboard/popular-queries endpoint.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class PopularQueryResponse {

    /**
     * Search query text
     */
    private String query;

    /**
     * Number of times this query was searched
     */
    private long count;
}
