package com.knowledge.backend.domain.entity;

import java.time.LocalDateTime;
import java.util.UUID;

import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.Id;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.relational.core.mapping.Column;
import org.springframework.data.relational.core.mapping.Table;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Knowledge User Entity
 *
 * <p>Platform users for knowledge domain (Design ERD).
 * Separate from auth_users (used for authentication).
 * This entity maps to the 'users' table in the schema.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Table("users")
public class KnowledgeUser {

    @Id
    private UUID id;

    @Column("username")
    private String username;

    @Column("email")
    private String email;

    @Column("password_hash")
    private String passwordHash;

    @Column("display_name")
    private String displayName;

    @Column("department")
    private String department;

    @Column("position")
    private String position;

    @Column("role")
    private String role;

    @Column("is_active")
    private Boolean isActive;

    @Column("last_login_at")
    private LocalDateTime lastLoginAt;

    @CreatedDate
    @Column("created_at")
    private LocalDateTime createdAt;

    @LastModifiedDate
    @Column("updated_at")
    private LocalDateTime updatedAt;

    /**
     * Check if user is admin
     *
     * @return true if role is admin
     */
    public boolean isAdmin() {
        return "admin".equalsIgnoreCase(role);
    }

    /**
     * Check if user account is active
     *
     * @return true if active
     */
    public boolean isAccountActive() {
        return Boolean.TRUE.equals(isActive);
    }
}
