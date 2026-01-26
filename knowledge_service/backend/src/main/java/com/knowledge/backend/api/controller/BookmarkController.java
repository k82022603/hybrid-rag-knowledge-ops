package com.knowledge.backend.api.controller;

import java.util.UUID;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.knowledge.backend.api.dto.bookmark.BookmarkCreateRequest;
import com.knowledge.backend.api.dto.bookmark.BookmarkResponse;
import com.knowledge.backend.security.JwtUser;
import com.knowledge.backend.service.BookmarkService;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

/**
 * Bookmark API Controller
 *
 * <p>Handles bookmark CRUD operations.
 *
 * <p>Endpoints:
 * <ul>
 *   <li>GET    /api/v1/bookmarks       - List bookmarks</li>
 *   <li>POST   /api/v1/bookmarks       - Create bookmark</li>
 *   <li>DELETE /api/v1/bookmarks/{id}  - Delete bookmark</li>
 * </ul>
 */
@Slf4j
@RestController
@RequestMapping("/api/v1/bookmarks")
@RequiredArgsConstructor
public class BookmarkController {

    private final BookmarkService bookmarkService;

    /**
     * Get current user's bookmarks
     *
     * @param principal authenticated user
     * @return Flux of BookmarkResponse
     */
    @GetMapping
    @PreAuthorize("hasAnyRole('USER', 'DEVELOPER', 'ADMIN')")
    public Flux<BookmarkResponse> getBookmarks(@AuthenticationPrincipal Object principal) {
        UUID userId = extractUserId(principal);
        if (userId == null) {
            log.warn("GET /bookmarks - unable to resolve user ID");
            return Flux.empty();
        }

        log.info("GET /bookmarks - user: {}", userId);
        return bookmarkService.getBookmarks(userId);
    }

    /**
     * Create a bookmark
     *
     * @param request bookmark creation data
     * @param principal authenticated user
     * @return Mono of created BookmarkResponse
     */
    @PostMapping
    @PreAuthorize("hasAnyRole('USER', 'DEVELOPER', 'ADMIN')")
    public Mono<ResponseEntity<BookmarkResponse>> createBookmark(
            @Valid @RequestBody BookmarkCreateRequest request,
            @AuthenticationPrincipal Object principal
    ) {
        UUID userId = extractUserId(principal);
        if (userId == null) {
            return Mono.just(ResponseEntity.status(HttpStatus.UNAUTHORIZED).build());
        }

        log.info("POST /bookmarks - user: {}, document: {}", userId, request.getDocumentId());

        return bookmarkService.createBookmark(userId, request.getDocumentId(), request.getComment())
                .map(bookmark -> ResponseEntity.status(HttpStatus.CREATED).body(bookmark));
    }

    /**
     * Delete a bookmark
     *
     * @param id        the bookmark UUID
     * @param principal authenticated user
     * @return empty response with 204 No Content
     */
    @DeleteMapping("/{id}")
    @PreAuthorize("hasAnyRole('USER', 'DEVELOPER', 'ADMIN')")
    public Mono<ResponseEntity<Void>> deleteBookmark(
            @PathVariable UUID id,
            @AuthenticationPrincipal Object principal
    ) {
        UUID userId = extractUserId(principal);
        if (userId == null) {
            return Mono.just(ResponseEntity.status(HttpStatus.UNAUTHORIZED).build());
        }

        log.info("DELETE /bookmarks/{} - user: {}", id, userId);

        return bookmarkService.deleteBookmark(id, userId)
                .then(Mono.just(ResponseEntity.noContent().<Void>build()));
    }

    /**
     * Extract user UUID from authentication principal
     *
     * @param principal the authentication principal
     * @return user UUID or null
     */
    private UUID extractUserId(Object principal) {
        if (principal instanceof JwtUser user) {
            try {
                return UUID.fromString(user.id());
            } catch (IllegalArgumentException e) {
                log.debug("User ID is not a UUID: {}", user.id());
                return null;
            }
        }
        return null;
    }
}
