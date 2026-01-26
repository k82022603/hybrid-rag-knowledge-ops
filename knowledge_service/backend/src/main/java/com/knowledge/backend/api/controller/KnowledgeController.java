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
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.knowledge.backend.api.dto.knowledge.CategoryResponse;
import com.knowledge.backend.api.dto.knowledge.ChunkResponse;
import com.knowledge.backend.api.dto.knowledge.DocumentCreateRequest;
import com.knowledge.backend.api.dto.knowledge.DocumentResponse;
import com.knowledge.backend.api.dto.knowledge.DocumentUpdateRequest;
import com.knowledge.backend.security.JwtUser;
import com.knowledge.backend.service.KnowledgeService;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

/**
 * Knowledge API Controller
 *
 * <p>Handles document CRUD, chunk retrieval, and category management.
 *
 * <p>Endpoints:
 * <ul>
 *   <li>GET    /api/v1/knowledge/documents          - List documents (paged)</li>
 *   <li>GET    /api/v1/knowledge/documents/{id}     - Get document detail</li>
 *   <li>POST   /api/v1/knowledge/documents          - Create document</li>
 *   <li>PUT    /api/v1/knowledge/documents/{id}     - Update document</li>
 *   <li>DELETE /api/v1/knowledge/documents/{id}     - Soft delete document</li>
 *   <li>GET    /api/v1/knowledge/documents/{id}/chunks - Get document chunks</li>
 *   <li>GET    /api/v1/knowledge/categories         - Get category tree</li>
 * </ul>
 */
@Slf4j
@RestController
@RequestMapping("/api/v1/knowledge")
@RequiredArgsConstructor
public class KnowledgeController {

    private final KnowledgeService knowledgeService;

    /**
     * Get paginated document list
     *
     * @param page    page number (default 0)
     * @param size    page size (default 20)
     * @param type    optional document type filter
     * @param keyword optional keyword search
     * @return Flux of DocumentResponse
     */
    @GetMapping("/documents")
    @PreAuthorize("hasAnyRole('USER', 'VIEWER', 'DEVELOPER', 'ADMIN')")
    public Flux<DocumentResponse> getDocuments(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(required = false) String type,
            @RequestParam(required = false) String keyword
    ) {
        log.info("GET /knowledge/documents - page={}, size={}, type={}, keyword={}", page, size, type, keyword);
        return knowledgeService.getDocuments(page, size, type, keyword);
    }

    /**
     * Get document by ID
     *
     * @param id the document UUID
     * @return Mono of DocumentResponse
     */
    @GetMapping("/documents/{id}")
    @PreAuthorize("hasAnyRole('USER', 'VIEWER', 'DEVELOPER', 'ADMIN')")
    public Mono<ResponseEntity<DocumentResponse>> getDocument(@PathVariable UUID id) {
        log.info("GET /knowledge/documents/{}", id);
        return knowledgeService.getDocument(id)
                .map(ResponseEntity::ok);
    }

    /**
     * Create a new document (metadata)
     *
     * @param request document creation data
     * @param principal authenticated user
     * @return Mono of created DocumentResponse
     */
    @PostMapping("/documents")
    @PreAuthorize("hasAnyRole('USER', 'DEVELOPER', 'ADMIN')")
    public Mono<ResponseEntity<DocumentResponse>> createDocument(
            @Valid @RequestBody DocumentCreateRequest request,
            @AuthenticationPrincipal Object principal
    ) {
        log.info("POST /knowledge/documents - title={}", request.getTitle());

        UUID uploadedBy = extractUserId(principal);

        return knowledgeService.createDocument(
                request.getTitle(),
                request.getDocumentType(),
                request.getProjectId(),
                request.getAuthorId(),
                request.getValidStartDate(),
                request.getValidEndDate(),
                request.getFilePath(),
                request.getFileName(),
                request.getFileSize(),
                request.getFileType(),
                uploadedBy
        ).map(doc -> ResponseEntity.status(HttpStatus.CREATED).body(doc));
    }

    /**
     * Update an existing document
     *
     * @param id      the document UUID
     * @param request document update data
     * @return Mono of updated DocumentResponse
     */
    @PutMapping("/documents/{id}")
    @PreAuthorize("hasAnyRole('USER', 'DEVELOPER', 'ADMIN')")
    public Mono<ResponseEntity<DocumentResponse>> updateDocument(
            @PathVariable UUID id,
            @Valid @RequestBody DocumentUpdateRequest request
    ) {
        log.info("PUT /knowledge/documents/{}", id);

        return knowledgeService.updateDocument(
                id,
                request.getTitle(),
                request.getDocumentType(),
                request.getProjectId(),
                request.getAuthorId(),
                request.getValidStartDate(),
                request.getValidEndDate()
        ).map(ResponseEntity::ok);
    }

    /**
     * Soft delete a document
     *
     * @param id the document UUID
     * @return empty response with 204 No Content
     */
    @DeleteMapping("/documents/{id}")
    @PreAuthorize("hasAnyRole('DEVELOPER', 'ADMIN')")
    public Mono<ResponseEntity<Void>> deleteDocument(@PathVariable UUID id) {
        log.info("DELETE /knowledge/documents/{}", id);

        return knowledgeService.deleteDocument(id)
                .then(Mono.just(ResponseEntity.noContent().<Void>build()));
    }

    /**
     * Get chunks for a document
     *
     * @param id the document UUID
     * @return Flux of ChunkResponse
     */
    @GetMapping("/documents/{id}/chunks")
    @PreAuthorize("hasAnyRole('USER', 'VIEWER', 'DEVELOPER', 'ADMIN')")
    public Flux<ChunkResponse> getDocumentChunks(@PathVariable UUID id) {
        log.info("GET /knowledge/documents/{}/chunks", id);
        return knowledgeService.getDocumentChunks(id);
    }

    /**
     * Get category tree
     *
     * @return Flux of CategoryResponse with nested children
     */
    @GetMapping("/categories")
    @PreAuthorize("hasAnyRole('USER', 'VIEWER', 'DEVELOPER', 'ADMIN')")
    public Flux<CategoryResponse> getCategories() {
        log.info("GET /knowledge/categories");
        return knowledgeService.getCategoryTree();
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
