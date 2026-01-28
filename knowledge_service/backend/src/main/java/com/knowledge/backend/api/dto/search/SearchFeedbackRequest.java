package com.knowledge.backend.api.dto.search;

import java.util.UUID;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Search Feedback Request DTO
 *
 * <p>Request format for submitting search feedback.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SearchFeedbackRequest {

    private UUID searchId;

    private UUID documentId;

    @NotNull(message = "Rating is required")
    @Min(value = 1, message = "Rating must be at least 1")
    @Max(value = 5, message = "Rating must be at most 5")
    private Integer rating;

    private String feedbackType;

    private String comment;
}
