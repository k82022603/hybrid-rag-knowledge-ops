package com.knowledge.backend.api.dto.dashboard;

import java.time.LocalDateTime;
import java.util.UUID;

import com.fasterxml.jackson.annotation.JsonInclude;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Popular Knowledge Response DTO
 *
 * <p>Represents a popular/trending document or search topic.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class PopularKnowledgeResponse {

    private UUID documentId;
    private String title;
    private String documentType;
    private long searchCount;
    private LocalDateTime lastAccessed;
}
