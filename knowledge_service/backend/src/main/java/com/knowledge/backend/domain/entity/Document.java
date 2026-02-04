package com.knowledge.backend.domain.entity;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.UUID;

import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.Id;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.annotation.Transient;
import org.springframework.data.domain.Persistable;
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
 *
 * <p>Implements Persistable to properly handle INSERT vs UPDATE in R2DBC
 * when using pre-generated UUIDs.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Table("documents")
public class Document implements Persistable<UUID> {

    @Id
    private UUID id;

    /**
     * Flag to indicate if this is a new entity (for R2DBC INSERT vs UPDATE).
     * Must be set to true when creating new documents with pre-generated UUIDs.
     */
    @Transient
    @Builder.Default
    private boolean isNew = true;

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

    /**
     * Returns whether the entity is new (for R2DBC INSERT vs UPDATE decision).
     * Required by Persistable interface.
     *
     * @return true if new entity (INSERT), false if existing (UPDATE)
     */
    @Override
    public boolean isNew() {
        return isNew;
    }

    /**
     * Returns the entity ID.
     * Required by Persistable interface.
     *
     * @return the document UUID
     */
    @Override
    public UUID getId() {
        return id;
    }
}
