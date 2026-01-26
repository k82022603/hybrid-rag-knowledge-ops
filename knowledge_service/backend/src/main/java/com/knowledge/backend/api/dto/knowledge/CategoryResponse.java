package com.knowledge.backend.api.dto.knowledge;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.knowledge.backend.domain.entity.Category;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Category Response DTO
 *
 * <p>Response format for category data including children for tree structure.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class CategoryResponse {

    private UUID id;
    private String name;
    private String code;
    private String description;
    private UUID parentId;
    private Integer level;
    private Integer sortOrder;
    private Boolean isActive;
    private List<CategoryResponse> children;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    /**
     * Convert Category entity to CategoryResponse DTO (without children)
     *
     * @param category the Category entity
     * @return CategoryResponse DTO
     */
    public static CategoryResponse from(Category category) {
        return CategoryResponse.builder()
                .id(category.getId())
                .name(category.getName())
                .code(category.getCode())
                .description(category.getDescription())
                .parentId(category.getParentId())
                .level(category.getLevel())
                .sortOrder(category.getSortOrder())
                .isActive(category.getIsActive())
                .createdAt(category.getCreatedAt())
                .updatedAt(category.getUpdatedAt())
                .build();
    }
}
