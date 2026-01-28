package com.knowledge.backend.service;

import java.time.LocalDateTime;
import java.util.UUID;

import org.springframework.stereotype.Service;

import com.knowledge.backend.api.dto.bookmark.BookmarkResponse;
import com.knowledge.backend.domain.entity.SearchFeedback;
import com.knowledge.backend.domain.repository.DocumentRepository;
import com.knowledge.backend.domain.repository.SearchFeedbackRepository;
import com.knowledge.backend.exception.BadRequestException;
import com.knowledge.backend.exception.ResourceNotFoundException;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

/**
 * Bookmark Service
 *
 * <p>Handles bookmark operations using search_feedback table
 * with feedback_type = 'bookmark'.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class BookmarkService {

    private final SearchFeedbackRepository searchFeedbackRepository;
    private final DocumentRepository documentRepository;

    /**
     * Get user's bookmarks
     *
     * @param userId the user UUID
     * @return Flux of BookmarkResponse
     */
    public Flux<BookmarkResponse> getBookmarks(UUID userId) {
        log.debug("Getting bookmarks for user: {}", userId);

        return searchFeedbackRepository.findBookmarksByUserId(userId)
                .map(BookmarkResponse::from);
    }

    /**
     * Create a bookmark
     *
     * @param userId     the user UUID
     * @param documentId the document UUID to bookmark
     * @param comment    optional comment
     * @return Mono of BookmarkResponse
     */
    public Mono<BookmarkResponse> createBookmark(UUID userId, UUID documentId, String comment) {
        log.info("Creating bookmark: user={}, document={}", userId, documentId);

        // Verify document exists
        return documentRepository.findById(documentId)
                .switchIfEmpty(Mono.error(new ResourceNotFoundException("Document", documentId)))
                .flatMap(doc ->
                    // Check if already bookmarked
                    searchFeedbackRepository.isBookmarked(userId, documentId)
                        .flatMap(exists -> {
                            if (Boolean.TRUE.equals(exists)) {
                                return Mono.error(new BadRequestException("Document is already bookmarked"));
                            }

                            SearchFeedback bookmark = SearchFeedback.builder()
                                    .userId(userId)
                                    .documentId(documentId)
                                    .feedbackType("bookmark")
                                    .comment(comment)
                                    .createdAt(LocalDateTime.now())
                                    .build();

                            return searchFeedbackRepository.save(bookmark);
                        })
                )
                .doOnSuccess(b -> log.info("Bookmark created: id={}", b.getId()))
                .map(BookmarkResponse::from);
    }

    /**
     * Update bookmark comment
     *
     * @param bookmarkId the bookmark UUID
     * @param userId     the user UUID (for ownership verification)
     * @param comment    new comment text
     * @return Mono of BookmarkResponse
     */
    public Mono<BookmarkResponse> updateBookmark(UUID bookmarkId, UUID userId, String comment) {
        log.info("Updating bookmark: id={}, user={}", bookmarkId, userId);

        return searchFeedbackRepository.findById(bookmarkId)
                .switchIfEmpty(Mono.error(new ResourceNotFoundException("Bookmark", bookmarkId)))
                .flatMap(feedback -> {
                    if (!userId.equals(feedback.getUserId())) {
                        return Mono.error(new BadRequestException("Cannot update another user's bookmark"));
                    }
                    feedback.setComment(comment);
                    return searchFeedbackRepository.save(feedback);
                })
                .doOnSuccess(b -> log.info("Bookmark updated: id={}", b.getId()))
                .map(BookmarkResponse::from);
    }

    /**
     * Delete a bookmark by ID
     *
     * @param bookmarkId the bookmark UUID
     * @param userId     the user UUID (for ownership verification)
     * @return Mono of void
     */
    public Mono<Void> deleteBookmark(UUID bookmarkId, UUID userId) {
        log.info("Deleting bookmark: id={}, user={}", bookmarkId, userId);

        return searchFeedbackRepository.findById(bookmarkId)
                .switchIfEmpty(Mono.error(new ResourceNotFoundException("Bookmark", bookmarkId)))
                .flatMap(feedback -> {
                    if (!userId.equals(feedback.getUserId())) {
                        return Mono.error(new BadRequestException("Cannot delete another user's bookmark"));
                    }
                    return searchFeedbackRepository.delete(feedback);
                })
                .doOnSuccess(v -> log.info("Bookmark deleted: id={}", bookmarkId));
    }
}
