package com.knowledge.backend.api.dto.knowledge;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

/**
 * Document Upload Response DTO
 *
 * <p>Response format for file upload operations.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DocumentUploadResponse {

    private String documentId;

    private String filename;

    private String status;

    private Long fileSize;

    private String fileType;

    private Instant uploadedAt;

    private String message;
}
