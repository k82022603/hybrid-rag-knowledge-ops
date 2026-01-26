package com.knowledge.backend.api.dto.bookmark;

import java.util.UUID;

import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Bookmark Create Request DTO
 *
 * <p>Request format for creating a bookmark.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class BookmarkCreateRequest {

    @NotNull(message = "Document ID is required")
    private UUID documentId;

    private String comment;
}
