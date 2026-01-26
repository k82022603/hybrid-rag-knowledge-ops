package com.knowledge.backend.domain.entity;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.UUID;

import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.Id;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.relational.core.mapping.Column;
import org.springframework.data.relational.core.mapping.Table;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Document Entity
 *
 * <p>Master document records (SSOT) mapped to 'documents' table.
 * Uses UUID primary key as per schema v3.0.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Table("documents")
public class Document {

    @Id
    private UUID id;

    @Column("title")
    private String title;

    @Column("document_type")
    private String documentType;

    @Column("project_id")
    private UUID projectId;

    @Column("author_id")
    private UUID authorId;

    @Column("uploaded_by")
    private UUID uploadedBy;

    @Column("valid_start_date")
    private LocalDate validStartDate;

    @Column("valid_end_date")
    private LocalDate validEndDate;

    @Column("file_path")
    private String filePath;

    @Column("file_name")
    private String fileName;

    @Column("file_size")
    private Long fileSize;

    @Column("file_type")
    private String fileType;

    @Column("file_hash")
    private String fileHash;

    @Column("processing_status")
    private String processingStatus;

    @Column("processing_error")
    private String processingError;

    @Column("processed_at")
    private LocalDateTime processedAt;

    @Column("chunk_count")
    private Integer chunkCount;

    @Column("entity_count")
    private Integer entityCount;

    @Column("es_synced")
    private Boolean esSynced;

    @Column("es_synced_at")
    private LocalDateTime esSyncedAt;

    @Column("neo4j_synced")
    private Boolean neo4jSynced;

    @Column("neo4j_synced_at")
    private LocalDateTime neo4jSyncedAt;

    @CreatedDate
    @Column("created_at")
    private LocalDateTime createdAt;

    @LastModifiedDate
    @Column("updated_at")
    private LocalDateTime updatedAt;
}
