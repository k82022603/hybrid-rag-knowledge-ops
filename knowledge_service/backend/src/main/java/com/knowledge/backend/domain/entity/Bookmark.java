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
 * Bookmark Entity
 *
 * <p>User bookmarks for documents. Since the schema does not include
 * a bookmarks table, this entity will be created as needed.
 * For now, we store bookmarks via search_feedback with feedback_type = 'bookmark'.
 *
 * <p>Note: This uses a lightweight approach with search_feedback table
 * until a dedicated bookmarks table is added to the schema.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Table("search_feedback")
public class Bookmark {

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
