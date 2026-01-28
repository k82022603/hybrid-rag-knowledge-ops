package com.knowledge.backend.api.dto.search;

import java.time.LocalDateTime;
import java.util.UUID;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.knowledge.backend.domain.entity.SearchFeedback;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Search Feedback Response DTO
 *
 * <p>Response format for search feedback entries.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class SearchFeedbackResponse {

    private UUID id;
    private UUID searchId;
    private UUID documentId;
    private Integer rating;
    private String feedbackType;
    private String comment;
    private LocalDateTime createdAt;

    /**
     * Convert SearchFeedback entity to SearchFeedbackResponse DTO
     *
     * @param feedback the SearchFeedback entity
     * @return SearchFeedbackResponse DTO
     */
    public static SearchFeedbackResponse from(SearchFeedback feedback) {
        return SearchFeedbackResponse.builder()
                .id(feedback.getId())
                .searchId(feedback.getSearchId())
                .documentId(feedback.getDocumentId())
                .rating(feedback.getRating())
                .feedbackType(feedback.getFeedbackType())
                .comment(feedback.getComment())
                .createdAt(feedback.getCreatedAt())
                .build();
    }
}
