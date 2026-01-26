package com.knowledge.backend.api.dto.search;

import java.util.List;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Chat Search Request DTO
 *
 * <p>Request format for conversational search with context.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ChatSearchRequest {

    @NotBlank(message = "Query is required")
    @Size(min = 2, max = 2000, message = "Query must be between 2 and 2000 characters")
    private String query;

    private List<ChatMessage> history;

    @Builder.Default
    private Integer topK = 5;

    /**
     * Chat message in conversation history
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ChatMessage {
        private String role;
        private String content;
    }
}
