package com.knowledge.backend.api.dto.knowledge;

import java.time.LocalDateTime;
import java.util.UUID;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.knowledge.backend.domain.entity.Document;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Document Status Response DTO
 *
 * <p>Response format for document processing status endpoint.
 * Provides detailed processing state information.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class DocumentStatusResponse {

    private UUID id;
    private String title;
    private String processingStatus;
    private String processingError;
    private LocalDateTime processedAt;
    private Integer chunkCount;
    private Integer entityCount;
    private Boolean esSynced;
    private LocalDateTime esSyncedAt;
    private Boolean neo4jSynced;
    private LocalDateTime neo4jSyncedAt;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    /**
     * Convert Document entity to DocumentStatusResponse DTO
     *
     * @param doc the Document entity
     * @return DocumentStatusResponse DTO
     */
    public static DocumentStatusResponse from(Document doc) {
        return DocumentStatusResponse.builder()
                .id(doc.getId())
                .title(doc.getTitle())
                .processingStatus(doc.getProcessingStatus())
                .processingError(doc.getProcessingError())
                .processedAt(doc.getProcessedAt())
                .chunkCount(doc.getChunkCount())
                .entityCount(doc.getEntityCount())
                .esSynced(doc.getEsSynced())
                .esSyncedAt(doc.getEsSyncedAt())
                .neo4jSynced(doc.getNeo4jSynced())
                .neo4jSyncedAt(doc.getNeo4jSyncedAt())
                .createdAt(doc.getCreatedAt())
                .updatedAt(doc.getUpdatedAt())
                .build();
    }
}
