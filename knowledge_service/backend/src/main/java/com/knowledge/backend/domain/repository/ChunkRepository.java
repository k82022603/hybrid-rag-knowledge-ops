package com.knowledge.backend.domain.repository;

import java.util.UUID;

import org.springframework.data.r2dbc.repository.Query;
import org.springframework.data.r2dbc.repository.R2dbcRepository;
import org.springframework.stereotype.Repository;

import com.knowledge.backend.domain.entity.Chunk;

import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

/**
 * Chunk Repository
 *
 * <p>R2DBC repository for Chunk entity (chunks table).
 */
@Repository
public interface ChunkRepository extends R2dbcRepository<Chunk, UUID> {

    /**
     * Find chunks by document ID ordered by chunk index
     *
     * @param documentId the document UUID
     * @return Flux of chunks
     */
    @Query("SELECT * FROM chunks WHERE document_id = :documentId ORDER BY chunk_index ASC")
    Flux<Chunk> findByDocumentIdOrderByChunkIndex(UUID documentId);

    /**
     * Count chunks by document ID
     *
     * @param documentId the document UUID
     * @return chunk count
     */
    Mono<Long> countByDocumentId(UUID documentId);

    /**
     * Delete all chunks for a document
     *
     * @param documentId the document UUID
     * @return Mono of void
     */
    @Query("DELETE FROM chunks WHERE document_id = :documentId")
    Mono<Void> deleteByDocumentId(UUID documentId);

    /**
     * Count total chunks
     *
     * @return total chunk count
     */
    @Query("SELECT COUNT(*) FROM chunks")
    Mono<Long> countTotal();
}
