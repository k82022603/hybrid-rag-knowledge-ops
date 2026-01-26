package com.knowledge.backend.domain.repository;

import java.util.UUID;

import org.springframework.data.r2dbc.repository.Query;
import org.springframework.data.r2dbc.repository.R2dbcRepository;
import org.springframework.stereotype.Repository;

import com.knowledge.backend.domain.entity.SearchFeedback;

import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

/**
 * Search Feedback Repository
 *
 * <p>R2DBC repository for SearchFeedback entity (search_feedback table).
 * Also used for bookmark operations (feedback_type = 'bookmark').
 */
@Repository
public interface SearchFeedbackRepository extends R2dbcRepository<SearchFeedback, UUID> {

    /**
     * Find bookmarks by user ID
     *
     * @param userId the user UUID
     * @return Flux of bookmarked entries
     */
    @Query("SELECT * FROM search_feedback WHERE user_id = :userId AND feedback_type = 'bookmark' ORDER BY created_at DESC")
    Flux<SearchFeedback> findBookmarksByUserId(UUID userId);

    /**
     * Count bookmarks by user ID
     *
     * @param userId the user UUID
     * @return bookmark count
     */
    @Query("SELECT COUNT(*) FROM search_feedback WHERE user_id = :userId AND feedback_type = 'bookmark'")
    Mono<Long> countBookmarksByUserId(UUID userId);

    /**
     * Check if document is bookmarked by user
     *
     * @param userId     the user UUID
     * @param documentId the document UUID
     * @return true if bookmarked
     */
    @Query("SELECT COUNT(*) > 0 FROM search_feedback WHERE user_id = :userId AND document_id = :documentId AND feedback_type = 'bookmark'")
    Mono<Boolean> isBookmarked(UUID userId, UUID documentId);

    /**
     * Delete bookmark by user and document
     *
     * @param userId     the user UUID
     * @param documentId the document UUID
     * @return Mono void
     */
    @Query("DELETE FROM search_feedback WHERE user_id = :userId AND document_id = :documentId AND feedback_type = 'bookmark'")
    Mono<Void> deleteBookmark(UUID userId, UUID documentId);

    /**
     * Find feedback by document ID
     *
     * @param documentId the document UUID
     * @return Flux of feedback entries
     */
    Flux<SearchFeedback> findByDocumentId(UUID documentId);
}
