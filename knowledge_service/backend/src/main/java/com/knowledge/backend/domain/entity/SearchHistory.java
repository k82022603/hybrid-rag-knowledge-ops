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
 * Search History Entity
 *
 * <p>Records search queries and their results for analytics.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Table("search_history")
public class SearchHistory {

    @Id
    private UUID id;

    @Column("user_id")
    private UUID userId;

    @Column("query_text")
    private String queryText;

    @Column("query_hash")
    private String queryHash;

    @Column("intent")
    private String intent;

    @Column("result_count")
    private Integer resultCount;

    @Column("search_duration_ms")
    private Integer searchDurationMs;

    @Column("cached")
    private Boolean cached;

    @CreatedDate
    @Column("created_at")
    private LocalDateTime createdAt;
}
