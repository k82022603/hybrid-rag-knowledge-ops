package com.knowledge.backend.domain.repository;

import java.util.UUID;

import org.springframework.data.r2dbc.repository.Query;
import org.springframework.data.r2dbc.repository.R2dbcRepository;
import org.springframework.stereotype.Repository;

import com.knowledge.backend.domain.entity.Category;

import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

/**
 * Category Repository
 *
 * <p>R2DBC repository for Category entity (categories table).
 * Supports hierarchical category tree queries.
 */
@Repository
public interface CategoryRepository extends R2dbcRepository<Category, UUID> {

    /**
     * Find active categories ordered by level and sort order
     *
     * @return Flux of active categories
     */
    @Query("SELECT * FROM categories WHERE is_active = true ORDER BY level ASC, sort_order ASC")
    Flux<Category> findAllActiveOrdered();

    /**
     * Find categories by parent ID
     *
     * @param parentId the parent category UUID
     * @return Flux of child categories
     */
    Flux<Category> findByParentId(UUID parentId);

    /**
     * Find root categories (no parent)
     *
     * @return Flux of root categories
     */
    @Query("SELECT * FROM categories WHERE parent_id IS NULL AND is_active = true ORDER BY sort_order ASC")
    Flux<Category> findRootCategories();

    /**
     * Find category by code
     *
     * @param code the category code
     * @return Mono of category
     */
    Mono<Category> findByCode(String code);

    /**
     * Find categories by level
     *
     * @param level the hierarchy level (1, 2, 3)
     * @return Flux of categories at that level
     */
    Flux<Category> findByLevel(Integer level);
}
