package com.knowledge.backend.api.dto.search;

import com.fasterxml.jackson.annotation.JsonInclude;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Search Suggestion Response DTO
 *
 * <p>Response format for search autocomplete / suggestion entries.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class SearchSuggestionResponse {

    private String suggestion;
    private Long frequency;
    private String category;
}
