package com.knowledge.backend.domain.entity;

import java.time.LocalDateTime;
import java.util.UUID;

import org.springframework.data.annotation.Id;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.relational.core.mapping.Column;
import org.springframework.data.relational.core.mapping.Table;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * System Config Entity
 *
 * <p>Key-value system configuration stored as JSONB values.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Table("system_config")
public class SystemConfig {

    @Id
    @Column("key")
    private String key;

    @Column("value")
    private String value;

    @Column("description")
    private String description;

    @Column("updated_by")
    private UUID updatedBy;

    @LastModifiedDate
    @Column("updated_at")
    private LocalDateTime updatedAt;
}
