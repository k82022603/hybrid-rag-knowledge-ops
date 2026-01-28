package com.knowledge.backend.service;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import org.springframework.stereotype.Service;

import com.knowledge.backend.api.dto.knowledge.CategoryResponse;
import com.knowledge.backend.api.dto.knowledge.ChunkResponse;
import com.knowledge.backend.api.dto.knowledge.DocumentResponse;
import com.knowledge.backend.api.dto.knowledge.DocumentStatusResponse;
import com.knowledge.backend.api.dto.knowledge.ProjectResponse;
import com.knowledge.backend.domain.entity.Category;
import com.knowledge.backend.domain.entity.Document;
import com.knowledge.backend.domain.repository.CategoryRepository;
import com.knowledge.backend.domain.repository.ChunkRepository;
import com.knowledge.backend.domain.repository.DocumentRepository;
import com.knowledge.backend.domain.repository.ProjectRepository;
import com.knowledge.backend.exception.ResourceNotFoundException;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

/**
 * Knowledge Service
 *
 * <p>Handles document management, chunk retrieval, and category operations.
 * Business logic layer between controllers and repositories.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class KnowledgeService {

    private final DocumentRepository documentRepository;
    private final ChunkRepository chunkRepository;
    private final CategoryRepository categoryRepository;
    private final ProjectRepository projectRepository;

    // ========================================================================
    // Document Operations
    // ========================================================================

    /**
     * Get paginated document list with optional type filter
     *
     * @param page         page number (0-based)
     * @param size         page size
     * @param documentType optional document type filter
     * @param keyword      optional keyword search filter
     * @return Flux of DocumentResponse
     */
    public Flux<DocumentResponse> getDocuments(int page, int size, String documentType, String keyword) {
        log.debug("Getting documents - page: {}, size: {}, type: {}, keyword: {}", page, size, documentType, keyword);

        long offset = (long) page * size;

        if (keyword != null && !keyword.isBlank()) {
            return documentRepository.searchByKeyword(keyword)
                    .map(DocumentResponse::from);
        }

        if (documentType != null && !documentType.isBlank()) {
            return documentRepository.findByTypePaged(documentType, size, offset)
                    .map(DocumentResponse::from);
        }

        return documentRepository.findAllPaged(size, offset)
                .map(DocumentResponse::from);
    }

    /**
     * Get document by ID
     *
     * @param documentId the document UUID
     * @return Mono of DocumentResponse
     */
    public Mono<DocumentResponse> getDocument(UUID documentId) {
        log.debug("Getting document by id: {}", documentId);

        return documentRepository.findById(documentId)
                .switchIfEmpty(Mono.error(new ResourceNotFoundException("Document", documentId)))
                .map(DocumentResponse::from);
    }

    /**
     * Create a new document (metadata only)
     *
     * @param title          document title
     * @param documentType   document type
     * @param projectId      project UUID (optional)
     * @param authorId       author UUID (optional)
     * @param validStartDate valid start date (optional)
     * @param validEndDate   valid end date (optional)
     * @param filePath       file path
     * @param fileName       file name (optional)
     * @param fileSize       file size (optional)
     * @param fileType       file type (optional)
     * @param uploadedBy     uploader user UUID
     * @return Mono of DocumentResponse
     */
    public Mono<DocumentResponse> createDocument(
            String title, String documentType, UUID projectId, UUID authorId,
            LocalDate validStartDate, LocalDate validEndDate,
            String filePath, String fileName, Long fileSize, String fileType,
            UUID uploadedBy
    ) {
        log.info("Creating document: title={}, type={}", title, documentType);

        Document document = Document.builder()
                .title(title)
                .documentType(documentType)
                .projectId(projectId)
                .authorId(authorId)
                .uploadedBy(uploadedBy)
                .validStartDate(validStartDate)
                .validEndDate(validEndDate)
                .filePath(filePath)
                .fileName(fileName)
                .fileSize(fileSize)
                .fileType(fileType)
                .processingStatus("pending")
                .chunkCount(0)
                .entityCount(0)
                .esSynced(false)
                .neo4jSynced(false)
                .createdAt(LocalDateTime.now())
                .updatedAt(LocalDateTime.now())
                .build();

        return documentRepository.save(document)
                .doOnSuccess(saved -> log.info("Document created: id={}", saved.getId()))
                .map(DocumentResponse::from);
    }

    /**
     * Update an existing document
     *
     * @param documentId     document UUID
     * @param title          new title (optional)
     * @param documentType   new type (optional)
     * @param projectId      new project ID (optional)
     * @param authorId       new author ID (optional)
     * @param validStartDate new valid start date (optional)
     * @param validEndDate   new valid end date (optional)
     * @return Mono of DocumentResponse
     */
    public Mono<DocumentResponse> updateDocument(
            UUID documentId, String title, String documentType,
            UUID projectId, UUID authorId,
            LocalDate validStartDate, LocalDate validEndDate
    ) {
        log.info("Updating document: id={}", documentId);

        return documentRepository.findById(documentId)
                .switchIfEmpty(Mono.error(new ResourceNotFoundException("Document", documentId)))
                .flatMap(existing -> {
                    if (title != null) existing.setTitle(title);
                    if (documentType != null) existing.setDocumentType(documentType);
                    if (projectId != null) existing.setProjectId(projectId);
                    if (authorId != null) existing.setAuthorId(authorId);
                    if (validStartDate != null) existing.setValidStartDate(validStartDate);
                    if (validEndDate != null) existing.setValidEndDate(validEndDate);
                    existing.setUpdatedAt(LocalDateTime.now());

                    return documentRepository.save(existing);
                })
                .doOnSuccess(updated -> log.info("Document updated: id={}", updated.getId()))
                .map(DocumentResponse::from);
    }

    /**
     * Soft delete a document (set processing_status to 'deleted')
     *
     * @param documentId document UUID
     * @return Mono of void
     */
    public Mono<Void> deleteDocument(UUID documentId) {
        log.info("Soft deleting document: id={}", documentId);

        return documentRepository.findById(documentId)
                .switchIfEmpty(Mono.error(new ResourceNotFoundException("Document", documentId)))
                .flatMap(existing -> {
                    existing.setProcessingStatus("deleted");
                    existing.setUpdatedAt(LocalDateTime.now());
                    return documentRepository.save(existing);
                })
                .doOnSuccess(deleted -> log.info("Document soft deleted: id={}", deleted.getId()))
                .then();
    }

    /**
     * Get chunks for a document
     *
     * @param documentId the document UUID
     * @return Flux of ChunkResponse
     */
    public Flux<ChunkResponse> getDocumentChunks(UUID documentId) {
        log.debug("Getting chunks for document: {}", documentId);

        return documentRepository.findById(documentId)
                .switchIfEmpty(Mono.error(new ResourceNotFoundException("Document", documentId)))
                .thenMany(chunkRepository.findByDocumentIdOrderByChunkIndex(documentId))
                .map(ChunkResponse::from);
    }

    /**
     * Count total documents
     *
     * @return Mono of total count
     */
    public Mono<Long> countDocuments() {
        return documentRepository.countTotal();
    }

    // ========================================================================
    // Category Operations
    // ========================================================================

    /**
     * Get document processing status
     *
     * @param documentId the document UUID
     * @return Mono of DocumentStatusResponse
     */
    public Mono<DocumentStatusResponse> getDocumentStatus(UUID documentId) {
        log.debug("Getting document status: {}", documentId);

        return documentRepository.findById(documentId)
                .switchIfEmpty(Mono.error(new ResourceNotFoundException("Document", documentId)))
                .map(DocumentStatusResponse::from);
    }

    // ========================================================================
    // Project Operations
    // ========================================================================

    /**
     * Get all projects
     *
     * @return Flux of ProjectResponse
     */
    public Flux<ProjectResponse> getProjects() {
        log.debug("Getting all projects");

        return projectRepository.findAll()
                .map(ProjectResponse::from);
    }

    // ========================================================================
    // Category Operations
    // ========================================================================

    /**
     * Get all categories as a tree structure
     *
     * @return Flux of CategoryResponse with children populated
     */
    public Flux<CategoryResponse> getCategoryTree() {
        log.debug("Building category tree");

        return categoryRepository.findAllActiveOrdered()
                .collectList()
                .flatMapMany(categories -> {
                    Map<UUID, CategoryResponse> responseMap = new HashMap<>();
                    List<CategoryResponse> roots = new ArrayList<>();

                    // Convert all entities to DTOs
                    for (Category cat : categories) {
                        CategoryResponse dto = CategoryResponse.from(cat);
                        dto.setChildren(new ArrayList<>());
                        responseMap.put(cat.getId(), dto);
                    }

                    // Build tree
                    for (Category cat : categories) {
                        CategoryResponse dto = responseMap.get(cat.getId());
                        if (cat.getParentId() == null) {
                            roots.add(dto);
                        } else {
                            CategoryResponse parent = responseMap.get(cat.getParentId());
                            if (parent != null) {
                                parent.getChildren().add(dto);
                            } else {
                                roots.add(dto);
                            }
                        }
                    }

                    return Flux.fromIterable(roots);
                });
    }
}
