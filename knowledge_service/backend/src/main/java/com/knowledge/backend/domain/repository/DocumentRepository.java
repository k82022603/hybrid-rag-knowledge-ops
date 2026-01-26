package com.knowledge.backend.domain.repository;

import java.util.UUID;

import org.springframework.data.r2dbc.repository.Query;
import org.springframework.data.r2dbc.repository.R2dbcRepository;
import org.springframework.stereotype.Repository;

import com.knowledge.backend.domain.entity.Document;

import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

/**
 * Document Repository
 *
 * <p>R2DBC repository for Document entity (documents table).
 * Provides reactive CRUD and custom query methods.
 */
@Repository
public interface DocumentRepository extends R2dbcRepository<Document, UUID> {

    /**
     * Find documents by processing status
     *
     * @param processingStatus the status to filter
     * @return Flux of matching documents
     */
    Flux<Document> findByProcessingStatus(String processingStatus);

    /**
     * Find documents by document type
     *
     * @param documentType the type to filter
     * @return Flux of matching documents
     */
    Flux<Document> findByDocumentType(String documentType);

    /**
     * Find documents by project ID
     *
     * @param projectId the project UUID
     * @return Flux of matching documents
     */
    Flux<Document> findByProjectId(UUID projectId);

    /**
     * Search documents by title keyword (case insensitive)
     *
     * @param keyword search keyword
     * @return Flux of matching documents
     */
    @Query("SELECT * FROM documents WHERE title ILIKE '%' || :keyword || '%' ORDER BY created_at DESC")
    Flux<Document> searchByKeyword(String keyword);

    /**
     * Find documents with pagination
     *
     * @param limit  page size
     * @param offset page offset
     * @return Flux of documents
     */
    @Query("SELECT * FROM documents ORDER BY created_at DESC LIMIT :limit OFFSET :offset")
    Flux<Document> findAllPaged(int limit, long offset);

    /**
     * Find documents by type with pagination
     *
     * @param documentType type filter
     * @param limit        page size
     * @param offset       page offset
     * @return Flux of documents
     */
    @Query("SELECT * FROM documents WHERE document_type = :documentType ORDER BY created_at DESC LIMIT :limit OFFSET :offset")
    Flux<Document> findByTypePaged(String documentType, int limit, long offset);

    /**
     * Count documents by type
     *
     * @param documentType the document type
     * @return count
     */
    Mono<Long> countByDocumentType(String documentType);

    /**
     * Count documents by processing status
     *
     * @param processingStatus the status
     * @return count
     */
    Mono<Long> countByProcessingStatus(String processingStatus);

    /**
     * Find most recently created documents
     *
     * @param limit number of results
     * @return Flux of recent documents
     */
    @Query("SELECT * FROM documents ORDER BY created_at DESC LIMIT :limit")
    Flux<Document> findRecent(int limit);

    /**
     * Count total documents
     *
     * @return total document count
     */
    @Query("SELECT COUNT(*) FROM documents")
    Mono<Long> countTotal();
}
