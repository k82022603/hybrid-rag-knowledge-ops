package com.knowledge.backend.api.dto.dashboard;

import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Document Type Distribution Response DTO
 *
 * <p>Document type count and percentage for distribution chart.
 * Used by GET /api/v1/dashboard/document-types endpoint.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class DocumentTypeDistributionResponse {

    /**
     * Document type name
     */
    private String type;

    /**
     * Number of documents of this type
     */
    private long count;

    /**
     * Percentage of total documents
     */
    private double percentage;
}
