package com.knowledge.backend.domain.entity;

import java.time.LocalDateTime;
import java.util.UUID;

import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.Id;
import org.springframework.data.relational.core.mapping.Column;
import org.springframework.data.relational.core.mapping.Table;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Chunk Entity
 *
 * <p>Document text chunks for RAG processing.
 * Mapped to 'chunks' table with UUID primary key.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Table("chunks")
public class Chunk {

    @Id
    private UUID id;

    @Column("document_id")
    private UUID documentId;

    @Column("chunk_index")
    private Integer chunkIndex;

    @Column("content")
    private String content;

    @Column("token_count")
    private Integer tokenCount;

    @Column("start_char")
    private Integer startChar;

    @Column("end_char")
    private Integer endChar;

    @Column("heading")
    private String heading;

    @Column("es_id")
    private String esId;

    @CreatedDate
    @Column("created_at")
    private LocalDateTime createdAt;
}
