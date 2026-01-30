package com.knowledge.backend.api.dto;

import com.fasterxml.jackson.annotation.JsonAlias;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Search Request DTO
 *
 * <p>Supports both Backend native format and Frontend format for compatibility:
 * <ul>
 *   <li>topK / pageSize - number of results</li>
 *   <li>documentTypes / filters.documentType - document type filter</li>
 *   <li>projectNames / filters.projectName - project name filter</li>
 *   <li>page - pagination support</li>
 * </ul>
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
public class SearchRequest {

    @NotBlank(message = "Query is required")
    @Size(min = 2, max = 1000, message = "Query must be between 2 and 1000 characters")
    private String query;

    @Builder.Default
    @JsonAlias("pageSize")
    private Integer topK = 10;

    @Builder.Default
    private Boolean useGraph = true;

    @Builder.Default
    private Boolean useVector = true;

    private List<String> documentTypes;

    private List<String> projectNames;

    private Map<String, Object> filters;

    /**
     * Page number for pagination (0-indexed)
     * Frontend compatibility field
     */
    @Builder.Default
    private Integer page = 0;

    /**
     * Custom setter for pageSize (alias for topK)
     * Enables Frontend compatibility
     */
    public void setPageSize(Integer pageSize) {
        if (pageSize != null) {
            this.topK = pageSize;
        }
    }

    /**
     * Process filters map to extract documentType and projectName
     * Frontend sends: filters: { documentType: "...", projectName: "..." }
     * Backend expects: documentTypes: [...], projectNames: [...]
     */
    public void setFilters(Map<String, Object> filters) {
        this.filters = filters;
        if (filters != null) {
            // Handle singular documentType from filters
            if (filters.containsKey("documentType")) {
                Object docType = filters.get("documentType");
                if (docType instanceof String && !((String) docType).isEmpty()) {
                    if (this.documentTypes == null) {
                        this.documentTypes = new ArrayList<>();
                    }
                    if (!this.documentTypes.contains((String) docType)) {
                        this.documentTypes.add((String) docType);
                    }
                }
            }
            // Handle singular projectName from filters
            if (filters.containsKey("projectName")) {
                Object projName = filters.get("projectName");
                if (projName instanceof String && !((String) projName).isEmpty()) {
                    if (this.projectNames == null) {
                        this.projectNames = new ArrayList<>();
                    }
                    if (!this.projectNames.contains((String) projName)) {
                        this.projectNames.add((String) projName);
                    }
                }
            }
        }
    }
}
