package com.knowledge.backend.security;

import java.util.Collection;

import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;

/**
 * JWT User Authentication Token
 *
 * <p>Extends JwtAuthenticationToken to include JwtUser as principal
 */
public class JwtUserAuthenticationToken extends JwtAuthenticationToken {

    private final JwtUser jwtUser;

    public JwtUserAuthenticationToken(
            Jwt jwt,
            Collection<? extends GrantedAuthority> authorities,
            JwtUser jwtUser) {
        super(jwt, authorities, jwtUser.username());
        this.jwtUser = jwtUser;
    }

    /**
     * Get the JwtUser principal
     *
     * @return the JWT user
     */
    public JwtUser getJwtUser() {
        return jwtUser;
    }

    @Override
    public Object getPrincipal() {
        return jwtUser;
    }
}
