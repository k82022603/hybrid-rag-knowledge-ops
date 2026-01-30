package com.knowledge.backend.api.dto.graph;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * Expert Search Response DTO
 *
 * <p>Response format for expert search results from Knowledge Graph.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ExpertSearchResponse {

    private List<Expert> experts;

    private String topic;

    private Integer totalCount;

    /**
     * Expert information
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Expert {

        private String id;

        private String name;

        private String email;

        private String department;

        private List<String> expertise;

        private Double score;

        private Integer documentCount;

        private Integer contributionCount;
    }
}
