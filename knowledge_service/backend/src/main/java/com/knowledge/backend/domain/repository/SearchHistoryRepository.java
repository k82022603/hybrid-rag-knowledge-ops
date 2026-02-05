package com.knowledge.backend.domain.repository;

import java.util.UUID;

import org.springframework.data.r2dbc.repository.Query;
import org.springframework.data.r2dbc.repository.R2dbcRepository;
import org.springframework.stereotype.Repository;

import com.knowledge.backend.domain.entity.SearchHistory;

import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

/**
 * Search History Repository
 *
 * <p>R2DBC repository for SearchHistory entity (search_history table).
 */
@Repository
public interface SearchHistoryRepository extends R2dbcRepository<SearchHistory, UUID> {

    /**
     * Find search history by user ID
     *
     * @param userId the user UUID
     * @return Flux of search history entries
     */
    @Query("SELECT * FROM search_history WHERE user_id = :userId ORDER BY created_at DESC LIMIT 50")
    Flux<SearchHistory> findByUserIdRecent(UUID userId);

    /**
     * Find popular search queries
     *
     * @param limit max results
     * @return Flux of popular queries
     */
    @Query("SELECT query_text, COUNT(*) as result_count FROM search_history GROUP BY query_text ORDER BY COUNT(*) DESC LIMIT :limit")
    Flux<SearchHistory> findPopularQueries(int limit);

    /**
     * Count total searches
     *
     * @return total search count
     */
    @Query("SELECT COUNT(*) FROM search_history")
    Mono<Long> countTotal();

    /**
     * Find recent search activity
     *
     * @param limit max results
     * @return Flux of recent searches
     */
    @Query("SELECT * FROM search_history ORDER BY created_at DESC LIMIT :limit")
    Flux<SearchHistory> findRecent(int limit);

    /**
     * Count searches by date for trend analysis
     *
     * @param startDate start date (inclusive)
     * @param endDate end date (inclusive)
     * @return Flux of daily search counts (date as query_text, count as result_count)
     */
    @Query("SELECT DATE(created_at) as query_text, COUNT(*) as result_count " +
           "FROM search_history " +
           "WHERE created_at >= :startDate AND created_at < :endDate " +
           "GROUP BY DATE(created_at) " +
           "ORDER BY DATE(created_at) ASC")
    Flux<SearchHistory> countByDateRange(java.time.LocalDateTime startDate, java.time.LocalDateTime endDate);
}
