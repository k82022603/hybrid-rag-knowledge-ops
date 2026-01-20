package com.knowledge.backend.security;

import java.util.Collection;
import java.util.Set;

import org.springframework.security.core.GrantedAuthority;

/**
 * JWT User Principal
 *
 * <p>Represents the authenticated user from Keycloak JWT token
 */
public record JwtUser(
    String id,
    String username,
    String email,
    String firstName,
    String lastName,
    Set<String> realmRoles,
    Set<String> clientRoles,
    Collection<? extends GrantedAuthority> authorities
) {

    /**
     * Check if user has a specific realm role
     *
     * @param role the role to check
     * @return true if user has the role
     */
    public boolean hasRole(String role) {
        return realmRoles.contains(role);
    }

    /**
     * Check if user has admin role
     *
     * @return true if user is admin
     */
    public boolean isAdmin() {
        return hasRole("admin");
    }

    /**
     * Check if user has developer role
     *
     * @return true if user is developer
     */
    public boolean isDeveloper() {
        return hasRole("developer") || isAdmin();
    }

    /**
     * Check if user has a specific client role
     *
     * @param role the client role to check
     * @return true if user has the client role
     */
    public boolean hasClientRole(String role) {
        return clientRoles.contains(role);
    }

    /**
     * Get full name
     *
     * @return full name or username if names not available
     */
    public String getFullName() {
        if (firstName != null && lastName != null) {
            return firstName + " " + lastName;
        }
        return username;
    }
}
