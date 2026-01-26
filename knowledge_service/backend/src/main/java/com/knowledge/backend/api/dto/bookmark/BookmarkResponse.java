package com.knowledge.backend.api.dto.bookmark;

import java.time.LocalDateTime;
import java.util.UUID;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.knowledge.backend.domain.entity.SearchFeedback;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Bookmark Response DTO
 *
 * <p>Response format for bookmark data.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class BookmarkResponse {

    private UUID id;
    private UUID documentId;
    private String comment;
    private LocalDateTime createdAt;

    /**
     * Convert SearchFeedback entity to BookmarkResponse DTO
     *
     * @param feedback the SearchFeedback entity (with feedback_type = 'bookmark')
     * @return BookmarkResponse DTO
     */
    public static BookmarkResponse from(SearchFeedback feedback) {
        return BookmarkResponse.builder()
                .id(feedback.getId())
                .documentId(feedback.getDocumentId())
                .comment(feedback.getComment())
                .createdAt(feedback.getCreatedAt())
                .build();
    }
}
