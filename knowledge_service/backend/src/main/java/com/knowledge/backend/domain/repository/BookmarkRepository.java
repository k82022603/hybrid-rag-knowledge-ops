package com.knowledge.backend.domain.repository;

import java.util.UUID;

import org.springframework.data.r2dbc.repository.R2dbcRepository;
import org.springframework.stereotype.Repository;

import com.knowledge.backend.domain.entity.Bookmark;

/**
 * Bookmark Repository
 *
 * <p>R2DBC repository for Bookmark entity (search_feedback table with feedback_type='bookmark').
 * Provides typed access for bookmark-specific operations.
 */
@Repository
public interface BookmarkRepository extends R2dbcRepository<Bookmark, UUID> {
}
