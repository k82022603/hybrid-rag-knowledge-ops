package com.knowledge.backend.domain.entity;

import java.time.LocalDateTime;
import java.util.UUID;

import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.Id;
import org.springframework.data.relational.core.mapping.Column;
import org.springframework.data.relational.core.mapping.Table;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Search Feedback Entity
 *
 * <p>User feedback on search results for quality improvement.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Table("search_feedback")
public class SearchFeedback {

    @Id
    private UUID id;

    @Column("search_id")
    private UUID searchId;

    @Column("user_id")
    private UUID userId;

    @Column("document_id")
    private UUID documentId;

    @Column("rating")
    private Integer rating;

    @Column("feedback_type")
    private String feedbackType;

    @Column("comment")
    private String comment;

    @CreatedDate
    @Column("created_at")
    private LocalDateTime createdAt;
}
