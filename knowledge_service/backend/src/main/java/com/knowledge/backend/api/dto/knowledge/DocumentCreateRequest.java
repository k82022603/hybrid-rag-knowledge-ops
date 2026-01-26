package com.knowledge.backend.api.dto.knowledge;

import java.time.LocalDate;
import java.util.UUID;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Document Create Request DTO
 *
 * <p>Request format for creating a new document (metadata).
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DocumentCreateRequest {

    @NotBlank(message = "Title is required")
    @Size(max = 500, message = "Title must be at most 500 characters")
    private String title;

    @NotBlank(message = "Document type is required")
    @Size(max = 50, message = "Document type must be at most 50 characters")
    private String documentType;

    private UUID projectId;

    private UUID authorId;

    private LocalDate validStartDate;

    private LocalDate validEndDate;

    @NotBlank(message = "File path is required")
    private String filePath;

    @Size(max = 500)
    private String fileName;

    private Long fileSize;

    @Size(max = 50)
    private String fileType;
}
