package com.knowledge.backend.api.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.List;

/**
 * Search Response DTO
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SearchResponse {

    private String query;

    private List<SearchResult> results;

    private Integer totalCount;

    private Long processingTimeMs;

    private Instant timestamp;

    /**
     * Individual search result
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class SearchResult {

        private String documentId;

        private String title;

        private String content;

        private String snippet;

        private Double score;

        private String documentType;

        private String projectName;

        private List<String> relatedDocuments;

        private Metadata metadata;
    }

    /**
     * Document metadata
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Metadata {

        private String author;

        private Instant createdAt;

        private Instant updatedAt;

        private String version;

        private List<String> tags;
    }
}
