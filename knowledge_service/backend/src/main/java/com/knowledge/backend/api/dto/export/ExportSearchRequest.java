package com.knowledge.backend.api.dto.export;

import jakarta.validation.constraints.NotBlank;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Export Search Request DTO
 *
 * <p>Request format for exporting search results.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ExportSearchRequest {

    @NotBlank(message = "Query is required")
    private String query;

    @Builder.Default
    private String format = "csv";

    @Builder.Default
    private Integer maxResults = 100;
}
