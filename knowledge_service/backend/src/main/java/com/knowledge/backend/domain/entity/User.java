package com.knowledge.backend.domain.entity;

import java.time.LocalDateTime;
import java.util.Set;

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
 * User Entity
 *
 * <p>Represents an authentication user in the system
 * <p>Uses auth_users table for authentication data
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Table("auth_users")
public class User {

    @Id
    private Long id;

    @Column("email")
    private String email;

    @Column("username")
    private String username;

    @Column("password_hash")
    private String passwordHash;

    @Column("first_name")
    private String firstName;

    @Column("last_name")
    private String lastName;

    @Column("roles")
    private String roles;

    @Column("is_active")
    private Boolean isActive;

    @Column("is_locked")
    private Boolean isLocked;

    @Column("failed_login_attempts")
    private Integer failedLoginAttempts;

    @Column("locked_until")
    private LocalDateTime lockedUntil;

    @Column("last_login_at")
    private LocalDateTime lastLoginAt;

    @CreatedDate
    @Column("created_at")
    private LocalDateTime createdAt;

    @LastModifiedDate
    @Column("updated_at")
    private LocalDateTime updatedAt;

    /**
     * Get roles as Set
     *
     * @return Set of role strings
     */
    public Set<String> getRolesAsSet() {
        if (roles == null || roles.isEmpty()) {
            return Set.of();
        }
        return Set.of(roles.split(","));
    }

    /**
     * Check if user account is locked
     *
     * @return true if account is locked and lock is still valid
     */
    public boolean isAccountLocked() {
        if (Boolean.TRUE.equals(isLocked) && lockedUntil != null) {
            return lockedUntil.isAfter(LocalDateTime.now());
        }
        return Boolean.TRUE.equals(isLocked);
    }

    /**
     * Check if user account is active
     *
     * @return true if account is active
     */
    public boolean isAccountActive() {
        return Boolean.TRUE.equals(isActive);
    }

    /**
     * Increment failed login attempts
     */
    public void incrementFailedLoginAttempts() {
        if (failedLoginAttempts == null) {
            failedLoginAttempts = 1;
        } else {
            failedLoginAttempts++;
        }
    }

    /**
     * Reset failed login attempts
     */
    public void resetFailedLoginAttempts() {
        failedLoginAttempts = 0;
        isLocked = false;
        lockedUntil = null;
    }

    /**
     * Lock account for specified duration
     *
     * @param durationMinutes lock duration in minutes
     */
    public void lockAccount(int durationMinutes) {
        isLocked = true;
        lockedUntil = LocalDateTime.now().plusMinutes(durationMinutes);
    }
}
