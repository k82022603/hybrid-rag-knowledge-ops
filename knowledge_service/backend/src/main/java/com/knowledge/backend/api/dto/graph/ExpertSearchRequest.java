package com.knowledge.backend.api.dto.graph;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Expert Search Request DTO
 *
 * <p>Request format for searching experts by topic in Knowledge Graph.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ExpertSearchRequest {

    @NotBlank(message = "Topic is required")
    @Size(max = 200, message = "Topic must be at most 200 characters")
    private String topic;

    @Min(value = 1, message = "Limit must be at least 1")
    @Max(value = 100, message = "Limit must be at most 100")
    @Builder.Default
    private Integer limit = 10;
}
