package com.knowledge.backend.api.dto.knowledge;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.UUID;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.knowledge.backend.domain.entity.Document;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Document Response DTO
 *
 * <p>Response format for document API endpoints.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class DocumentResponse {

    private UUID id;
    private String title;
    private String documentType;
    private UUID projectId;
    private UUID authorId;
    private UUID uploadedBy;
    private LocalDate validStartDate;
    private LocalDate validEndDate;
    private String filePath;
    private String fileName;
    private Long fileSize;
    private String fileType;
    private String processingStatus;
    private Integer chunkCount;
    private Integer entityCount;
    private Boolean esSynced;
    private Boolean neo4jSynced;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    /**
     * Convert Document entity to DocumentResponse DTO
     *
     * @param doc the Document entity
     * @return DocumentResponse DTO
     */
    public static DocumentResponse from(Document doc) {
        return DocumentResponse.builder()
                .id(doc.getId())
                .title(doc.getTitle())
                .documentType(doc.getDocumentType())
                .projectId(doc.getProjectId())
                .authorId(doc.getAuthorId())
                .uploadedBy(doc.getUploadedBy())
                .validStartDate(doc.getValidStartDate())
                .validEndDate(doc.getValidEndDate())
                .filePath(doc.getFilePath())
                .fileName(doc.getFileName())
                .fileSize(doc.getFileSize())
                .fileType(doc.getFileType())
                .processingStatus(doc.getProcessingStatus())
                .chunkCount(doc.getChunkCount())
                .entityCount(doc.getEntityCount())
                .esSynced(doc.getEsSynced())
                .neo4jSynced(doc.getNeo4jSynced())
                .createdAt(doc.getCreatedAt())
                .updatedAt(doc.getUpdatedAt())
                .build();
    }
}
