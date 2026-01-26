package com.knowledge.backend.api.dto.knowledge;

import java.time.LocalDateTime;
import java.util.UUID;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.knowledge.backend.domain.entity.Chunk;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Chunk Response DTO
 *
 * <p>Response format for document chunk data.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class ChunkResponse {

    private UUID id;
    private UUID documentId;
    private Integer chunkIndex;
    private String content;
    private Integer tokenCount;
    private Integer startChar;
    private Integer endChar;
    private String heading;
    private LocalDateTime createdAt;

    /**
     * Convert Chunk entity to ChunkResponse DTO
     *
     * @param chunk the Chunk entity
     * @return ChunkResponse DTO
     */
    public static ChunkResponse from(Chunk chunk) {
        return ChunkResponse.builder()
                .id(chunk.getId())
                .documentId(chunk.getDocumentId())
                .chunkIndex(chunk.getChunkIndex())
                .content(chunk.getContent())
                .tokenCount(chunk.getTokenCount())
                .startChar(chunk.getStartChar())
                .endChar(chunk.getEndChar())
                .heading(chunk.getHeading())
                .createdAt(chunk.getCreatedAt())
                .build();
    }
}
