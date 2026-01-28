package com.knowledge.backend.api.dto.bookmark;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Bookmark Update Request DTO
 *
 * <p>Request format for updating an existing bookmark.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class BookmarkUpdateRequest {

    private String comment;
}
