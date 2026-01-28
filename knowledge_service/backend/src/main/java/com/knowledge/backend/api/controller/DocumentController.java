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
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.knowledge.backend.api.dto.knowledge.ChunkResponse;
import com.knowledge.backend.api.dto.knowledge.DocumentCreateRequest;
import com.knowledge.backend.api.dto.knowledge.DocumentResponse;
import com.knowledge.backend.api.dto.knowledge.DocumentStatusResponse;
import com.knowledge.backend.api.dto.knowledge.CategoryResponse;
import com.knowledge.backend.api.dto.knowledge.ProjectResponse;
import com.knowledge.backend.security.JwtUser;
import com.knowledge.backend.service.KnowledgeService;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

/**
 * Document API Controller (Legacy path: /api/v1/documents)
 *
 * <p>Provides backward-compatible access to document APIs using the /api/v1/documents path.
 * The canonical path is /api/v1/knowledge/documents via KnowledgeController.
 *
 * <p>Endpoints:
 * <ul>
 *   <li>POST   /api/v1/documents          - Upload/create document</li>
 *   <li>GET    /api/v1/documents          - List documents</li>
 *   <li>GET    /api/v1/documents/{id}     - Get document detail</li>
 *   <li>DELETE /api/v1/documents/{id}     - Delete document</li>
 *   <li>GET    /api/v1/documents/{id}/status - Processing status</li>
 *   <li>GET    /api/v1/documents/{id}/chunks - Document chunks</li>
 *   <li>GET    /api/v1/categories         - Category list</li>
 *   <li>GET    /api/v1/projects           - Project list</li>
 * </ul>
 */
@Slf4j
@RestController
@RequestMapping("/api/v1")
@RequiredArgsConstructor
public class DocumentController {

    private final KnowledgeService knowledgeService;

    /**
     * Upload / create a new document
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
        log.info("POST /documents - title={}", request.getTitle());

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
        log.info("GET /documents - page={}, size={}, type={}, keyword={}", page, size, type, keyword);
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
        log.info("GET /documents/{}", id);
        return knowledgeService.getDocument(id)
                .map(ResponseEntity::ok);
    }

    /**
     * Delete a document (soft delete)
     *
     * @param id the document UUID
     * @return empty response with 204
     */
    @DeleteMapping("/documents/{id}")
    @PreAuthorize("hasAnyRole('DEVELOPER', 'ADMIN')")
    public Mono<ResponseEntity<Void>> deleteDocument(@PathVariable UUID id) {
        log.info("DELETE /documents/{}", id);
        return knowledgeService.deleteDocument(id)
                .then(Mono.just(ResponseEntity.noContent().<Void>build()));
    }

    /**
     * Get document processing status
     *
     * @param id the document UUID
     * @return Mono of DocumentStatusResponse
     */
    @GetMapping("/documents/{id}/status")
    @PreAuthorize("hasAnyRole('USER', 'VIEWER', 'DEVELOPER', 'ADMIN')")
    public Mono<ResponseEntity<DocumentStatusResponse>> getDocumentStatus(@PathVariable UUID id) {
        log.info("GET /documents/{}/status", id);
        return knowledgeService.getDocumentStatus(id)
                .map(ResponseEntity::ok);
    }

    /**
     * Get document chunks
     *
     * @param id the document UUID
     * @return Flux of ChunkResponse
     */
    @GetMapping("/documents/{id}/chunks")
    @PreAuthorize("hasAnyRole('USER', 'VIEWER', 'DEVELOPER', 'ADMIN')")
    public Flux<ChunkResponse> getDocumentChunks(@PathVariable UUID id) {
        log.info("GET /documents/{}/chunks", id);
        return knowledgeService.getDocumentChunks(id);
    }

    /**
     * Get all categories
     *
     * @return Flux of CategoryResponse
     */
    @GetMapping("/categories")
    @PreAuthorize("hasAnyRole('USER', 'VIEWER', 'DEVELOPER', 'ADMIN')")
    public Flux<CategoryResponse> getCategories() {
        log.info("GET /categories");
        return knowledgeService.getCategoryTree();
    }

    /**
     * Get all projects
     *
     * @return Flux of ProjectResponse
     */
    @GetMapping("/projects")
    @PreAuthorize("hasAnyRole('USER', 'VIEWER', 'DEVELOPER', 'ADMIN')")
    public Flux<ProjectResponse> getProjects() {
        log.info("GET /projects");
        return knowledgeService.getProjects();
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
