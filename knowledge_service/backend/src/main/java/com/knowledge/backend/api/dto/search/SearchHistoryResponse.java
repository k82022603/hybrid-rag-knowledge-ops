package com.knowledge.backend.api.dto.search;

import java.time.LocalDateTime;
import java.util.UUID;

import com.knowledge.backend.domain.entity.SearchHistory;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Search History Response DTO
 *
 * <p>Response format for search history entries.
 * Contains the query text, result metadata, and timing information.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SearchHistoryResponse {

    private UUID id;

    private String queryText;

    private String intent;

    private Integer resultCount;

    private Integer searchDurationMs;

    private Boolean cached;

    private LocalDateTime createdAt;

    /**
     * Create SearchHistoryResponse from SearchHistory entity
     *
     * @param entity SearchHistory entity
     * @return SearchHistoryResponse DTO
     */
    public static SearchHistoryResponse from(SearchHistory entity) {
        return SearchHistoryResponse.builder()
                .id(entity.getId())
                .queryText(entity.getQueryText())
                .intent(entity.getIntent())
                .resultCount(entity.getResultCount())
                .searchDurationMs(entity.getSearchDurationMs())
                .cached(entity.getCached())
                .createdAt(entity.getCreatedAt())
                .build();
    }
}
