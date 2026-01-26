package com.knowledge.backend.api.dto.knowledge;

import java.time.LocalDate;
import java.util.UUID;

import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Document Update Request DTO
 *
 * <p>Request format for updating an existing document.
 * All fields are optional (partial update).
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DocumentUpdateRequest {

    @Size(max = 500, message = "Title must be at most 500 characters")
    private String title;

    @Size(max = 50, message = "Document type must be at most 50 characters")
    private String documentType;

    private UUID projectId;

    private UUID authorId;

    private LocalDate validStartDate;

    private LocalDate validEndDate;
}
