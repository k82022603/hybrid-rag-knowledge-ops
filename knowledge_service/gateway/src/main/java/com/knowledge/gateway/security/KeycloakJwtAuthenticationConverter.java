package com.knowledge.gateway.security;

import java.util.Collection;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

import org.springframework.core.convert.converter.Converter;
import org.springframework.security.authentication.AbstractAuthenticationToken;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.stereotype.Component;

import reactor.core.publisher.Mono;

/**
 * Keycloak JWT Authentication Converter for Gateway
 *
 * <p>Converts Keycloak JWT token to Spring Security Authentication
 * with proper role extraction from realm_access and resource_access claims
 */
@Component
public class KeycloakJwtAuthenticationConverter
    implements Converter<Jwt, Mono<AbstractAuthenticationToken>> {

    private static final String REALM_ACCESS_CLAIM = "realm_access";
    private static final String RESOURCE_ACCESS_CLAIM = "resource_access";
    private static final String ROLES_CLAIM = "roles";
    private static final String ROLE_PREFIX = "ROLE_";
    private static final String CLIENT_ID = "knowledge-api-gateway";

    @Override
    public Mono<AbstractAuthenticationToken> convert(Jwt jwt) {
        Collection<GrantedAuthority> authorities = extractAuthorities(jwt);
        String username = jwt.getClaimAsString("preferred_username");

        return Mono.just(new JwtAuthenticationToken(jwt, authorities, username));
    }

    /**
     * Extract all authorities from JWT token
     */
    private Collection<GrantedAuthority> extractAuthorities(Jwt jwt) {
        Set<GrantedAuthority> authorities = new HashSet<>();

        // Extract realm roles
        authorities.addAll(extractRealmRoles(jwt));

        // Extract client roles
        authorities.addAll(extractClientRoles(jwt));

        return authorities;
    }

    /**
     * Extract realm roles from realm_access claim
     */
    @SuppressWarnings("unchecked")
    private Set<GrantedAuthority> extractRealmRoles(Jwt jwt) {
        Map<String, Object> realmAccess = jwt.getClaim(REALM_ACCESS_CLAIM);
        if (realmAccess == null) {
            return Collections.emptySet();
        }

        List<String> roles = (List<String>) realmAccess.get(ROLES_CLAIM);
        if (roles == null) {
            return Collections.emptySet();
        }

        return roles.stream()
            .map(role -> new SimpleGrantedAuthority(ROLE_PREFIX + role.toUpperCase()))
            .collect(Collectors.toSet());
    }

    /**
     * Extract client roles from resource_access claim
     */
    @SuppressWarnings("unchecked")
    private Set<GrantedAuthority> extractClientRoles(Jwt jwt) {
        Map<String, Object> resourceAccess = jwt.getClaim(RESOURCE_ACCESS_CLAIM);
        if (resourceAccess == null) {
            return Collections.emptySet();
        }

        Set<GrantedAuthority> clientAuthorities = new HashSet<>();

        // Extract roles for our specific client
        Map<String, Object> clientAccess = (Map<String, Object>) resourceAccess.get(CLIENT_ID);
        if (clientAccess != null) {
            List<String> clientRoles = (List<String>) clientAccess.get(ROLES_CLAIM);
            if (clientRoles != null) {
                clientAuthorities.addAll(
                    clientRoles.stream()
                        .map(role -> new SimpleGrantedAuthority("CLIENT_" + role.toUpperCase().replace(":", "_")))
                        .collect(Collectors.toSet())
                );
            }
        }

        return clientAuthorities;
    }
}
