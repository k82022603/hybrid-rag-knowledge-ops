package com.knowledge.backend.api.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.Map;

/**
 * Search Request DTO
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SearchRequest {

    @NotBlank(message = "Query is required")
    @Size(min = 2, max = 1000, message = "Query must be between 2 and 1000 characters")
    private String query;

    @Builder.Default
    private Integer topK = 10;

    @Builder.Default
    private Boolean useGraph = true;

    @Builder.Default
    private Boolean useVector = true;

    private List<String> documentTypes;

    private List<String> projectNames;

    private Map<String, Object> filters;
}
