package com.knowledge.gateway.filter;

import com.knowledge.gateway.security.JwtTokenValidator;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.mock.http.server.reactive.MockServerHttpRequest;
import org.springframework.mock.web.server.MockServerWebExchange;
import org.springframework.security.core.context.ReactiveSecurityContextHolder;
import org.springframework.security.core.context.SecurityContext;
import org.springframework.web.server.ServerWebExchange;
import org.springframework.web.server.WebFilterChain;
import reactor.core.publisher.Mono;
import reactor.test.StepVerifier;

import java.util.Set;
import java.util.concurrent.atomic.AtomicReference;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * Unit tests for JwtAuthenticationFilter
 *
 * <p>Tests the WebFilter behavior for dual-token (HS256/RS256) handling:
 * <ul>
 *   <li>HS256 tokens: validated, SecurityContext set, Authorization header stripped</li>
 *   <li>RS256 tokens: passed through to OAuth2 Resource Server</li>
 *   <li>No token: passed through</li>
 *   <li>Invalid HS256: returns 401 Unauthorized</li>
 * </ul>
 */
@ExtendWith(MockitoExtension.class)
class JwtAuthenticationFilterTest {

    @Mock
    private JwtTokenValidator jwtTokenValidator;

    private JwtAuthenticationFilter filter;

    private static final String VALID_HS256_TOKEN = "eyJhbGciOiJIUzI1NiJ9.payload.signature";
    private static final String RS256_TOKEN = "eyJhbGciOiJSUzI1NiJ9.payload.signature";

    @BeforeEach
    void setUp() {
        filter = new JwtAuthenticationFilter(jwtTokenValidator);
    }

    @Nested
    @DisplayName("When no Authorization header")
    class NoAuthorizationHeader {

        @Test
        @DisplayName("Passes through to next filter")
        void passesThrough_WhenNoAuthHeader() {
            MockServerHttpRequest request = MockServerHttpRequest
                .get("/api/v1/knowledge")
                .build();
            MockServerWebExchange exchange = MockServerWebExchange.from(request);

            AtomicReference<ServerWebExchange> capturedExchange = new AtomicReference<>();
            WebFilterChain chain = ex -> {
                capturedExchange.set(ex);
                return Mono.empty();
            };

            StepVerifier.create(filter.filter(exchange, chain))
                .verifyComplete();

            assertThat(capturedExchange.get()).isNotNull();
            verify(jwtTokenValidator, never()).isSelfIssuedToken(anyString());
        }
    }

    @Nested
    @DisplayName("When Authorization header without Bearer prefix")
    class NonBearerAuthorizationHeader {

        @Test
        @DisplayName("Passes through to next filter")
        void passesThrough_WhenNotBearerToken() {
            MockServerHttpRequest request = MockServerHttpRequest
                .get("/api/v1/knowledge")
                .header(HttpHeaders.AUTHORIZATION, "Basic dXNlcjpwYXNz")
                .build();
            MockServerWebExchange exchange = MockServerWebExchange.from(request);

            AtomicReference<ServerWebExchange> capturedExchange = new AtomicReference<>();
            WebFilterChain chain = ex -> {
                capturedExchange.set(ex);
                return Mono.empty();
            };

            StepVerifier.create(filter.filter(exchange, chain))
                .verifyComplete();

            assertThat(capturedExchange.get()).isNotNull();
            verify(jwtTokenValidator, never()).isSelfIssuedToken(anyString());
        }
    }

    @Nested
    @DisplayName("When RS256 token is present")
    class RS256Token {

        @Test
        @DisplayName("Passes through to OAuth2 Resource Server")
        void passesThrough_ForRS256Token() {
            when(jwtTokenValidator.isSelfIssuedToken(RS256_TOKEN)).thenReturn(false);

            MockServerHttpRequest request = MockServerHttpRequest
                .get("/api/v1/knowledge")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + RS256_TOKEN)
                .build();
            MockServerWebExchange exchange = MockServerWebExchange.from(request);

            AtomicReference<ServerWebExchange> capturedExchange = new AtomicReference<>();
            WebFilterChain chain = ex -> {
                capturedExchange.set(ex);
                return Mono.empty();
            };

            StepVerifier.create(filter.filter(exchange, chain))
                .verifyComplete();

            // Exchange should pass through unchanged (Authorization header preserved)
            assertThat(capturedExchange.get()).isNotNull();
            assertThat(capturedExchange.get().getRequest().getHeaders()
                .getFirst(HttpHeaders.AUTHORIZATION))
                .isEqualTo("Bearer " + RS256_TOKEN);
        }
    }

    @Nested
    @DisplayName("When valid HS256 token is present")
    class ValidHS256Token {

        @Test
        @DisplayName("Sets SecurityContext and strips Authorization header")
        void setsSecurityContext_AndStripsHeader() {
            when(jwtTokenValidator.isSelfIssuedToken(VALID_HS256_TOKEN)).thenReturn(true);
            when(jwtTokenValidator.validateToken(VALID_HS256_TOKEN)).thenReturn(true);
            when(jwtTokenValidator.getUserIdFromToken(VALID_HS256_TOKEN)).thenReturn("user-123");
            when(jwtTokenValidator.getEmailFromToken(VALID_HS256_TOKEN)).thenReturn("test@example.com");
            when(jwtTokenValidator.getUsernameFromToken(VALID_HS256_TOKEN)).thenReturn("testuser");
            when(jwtTokenValidator.getRolesFromToken(VALID_HS256_TOKEN)).thenReturn(Set.of("USER"));

            MockServerHttpRequest request = MockServerHttpRequest
                .get("/api/v1/knowledge")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + VALID_HS256_TOKEN)
                .build();
            MockServerWebExchange exchange = MockServerWebExchange.from(request);

            AtomicReference<ServerWebExchange> capturedExchange = new AtomicReference<>();
            WebFilterChain chain = ex -> {
                capturedExchange.set(ex);
                return Mono.empty();
            };

            StepVerifier.create(filter.filter(exchange, chain))
                .verifyComplete();

            // Authorization header should be stripped from the mutated request
            assertThat(capturedExchange.get()).isNotNull();
            assertThat(capturedExchange.get().getRequest().getHeaders()
                .getFirst(HttpHeaders.AUTHORIZATION))
                .isNull();
        }

        @Test
        @DisplayName("Creates authentication with correct principal and authorities")
        void createsAuthentication_WithCorrectDetails() {
            when(jwtTokenValidator.isSelfIssuedToken(VALID_HS256_TOKEN)).thenReturn(true);
            when(jwtTokenValidator.validateToken(VALID_HS256_TOKEN)).thenReturn(true);
            when(jwtTokenValidator.getUserIdFromToken(VALID_HS256_TOKEN)).thenReturn("user-123");
            when(jwtTokenValidator.getEmailFromToken(VALID_HS256_TOKEN)).thenReturn("test@example.com");
            when(jwtTokenValidator.getUsernameFromToken(VALID_HS256_TOKEN)).thenReturn("testuser");
            when(jwtTokenValidator.getRolesFromToken(VALID_HS256_TOKEN)).thenReturn(Set.of("USER", "ADMIN"));

            MockServerHttpRequest request = MockServerHttpRequest
                .get("/api/v1/knowledge")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + VALID_HS256_TOKEN)
                .build();
            MockServerWebExchange exchange = MockServerWebExchange.from(request);

            AtomicReference<SecurityContext> capturedContext = new AtomicReference<>();
            WebFilterChain chain = ex -> {
                // Capture the SecurityContext from the reactive context
                return ReactiveSecurityContextHolder.getContext()
                    .doOnNext(capturedContext::set)
                    .then();
            };

            StepVerifier.create(filter.filter(exchange, chain))
                .verifyComplete();

            assertThat(capturedContext.get()).isNotNull();
            assertThat(capturedContext.get().getAuthentication()).isNotNull();
            assertThat(capturedContext.get().getAuthentication().getPrincipal()).isEqualTo("user-123");
            assertThat(capturedContext.get().getAuthentication().getAuthorities())
                .extracting("authority")
                .containsExactlyInAnyOrder("ROLE_USER", "ROLE_ADMIN");
        }
    }

    @Nested
    @DisplayName("When invalid HS256 token is present")
    class InvalidHS256Token {

        @Test
        @DisplayName("Returns 401 Unauthorized")
        void returns401_ForInvalidHS256Token() {
            when(jwtTokenValidator.isSelfIssuedToken(VALID_HS256_TOKEN)).thenReturn(true);
            when(jwtTokenValidator.validateToken(VALID_HS256_TOKEN)).thenReturn(false);

            MockServerHttpRequest request = MockServerHttpRequest
                .get("/api/v1/knowledge")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + VALID_HS256_TOKEN)
                .build();
            MockServerWebExchange exchange = MockServerWebExchange.from(request);

            WebFilterChain chain = ex -> Mono.empty();

            StepVerifier.create(filter.filter(exchange, chain))
                .verifyComplete();

            assertThat(exchange.getResponse().getStatusCode()).isEqualTo(HttpStatus.UNAUTHORIZED);
        }

        @Test
        @DisplayName("Returns JSON error body for invalid token")
        void returnsJsonError_ForInvalidToken() {
            when(jwtTokenValidator.isSelfIssuedToken(VALID_HS256_TOKEN)).thenReturn(true);
            when(jwtTokenValidator.validateToken(VALID_HS256_TOKEN)).thenReturn(false);

            MockServerHttpRequest request = MockServerHttpRequest
                .get("/api/v1/knowledge")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + VALID_HS256_TOKEN)
                .build();
            MockServerWebExchange exchange = MockServerWebExchange.from(request);

            WebFilterChain chain = ex -> Mono.empty();

            StepVerifier.create(filter.filter(exchange, chain))
                .verifyComplete();

            assertThat(exchange.getResponse().getHeaders().getContentType())
                .isNotNull();
            assertThat(exchange.getResponse().getHeaders().getContentType().toString())
                .contains("application/json");
        }

        @Test
        @DisplayName("Does not invoke filter chain for invalid token")
        void doesNotInvokeChain_ForInvalidToken() {
            when(jwtTokenValidator.isSelfIssuedToken(VALID_HS256_TOKEN)).thenReturn(true);
            when(jwtTokenValidator.validateToken(VALID_HS256_TOKEN)).thenReturn(false);

            MockServerHttpRequest request = MockServerHttpRequest
                .get("/api/v1/knowledge")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + VALID_HS256_TOKEN)
                .build();
            MockServerWebExchange exchange = MockServerWebExchange.from(request);

            AtomicReference<Boolean> chainInvoked = new AtomicReference<>(false);
            WebFilterChain chain = ex -> {
                chainInvoked.set(true);
                return Mono.empty();
            };

            StepVerifier.create(filter.filter(exchange, chain))
                .verifyComplete();

            assertThat(chainInvoked.get()).isFalse();
        }
    }

    @Nested
    @DisplayName("When claim extraction fails")
    class ClaimExtractionFailure {

        @Test
        @DisplayName("Returns 401 when claim extraction throws exception")
        void returns401_WhenClaimExtractionFails() {
            when(jwtTokenValidator.isSelfIssuedToken(VALID_HS256_TOKEN)).thenReturn(true);
            when(jwtTokenValidator.validateToken(VALID_HS256_TOKEN)).thenReturn(true);
            when(jwtTokenValidator.getUserIdFromToken(VALID_HS256_TOKEN))
                .thenThrow(new RuntimeException("Claim extraction failed"));

            MockServerHttpRequest request = MockServerHttpRequest
                .get("/api/v1/knowledge")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + VALID_HS256_TOKEN)
                .build();
            MockServerWebExchange exchange = MockServerWebExchange.from(request);

            WebFilterChain chain = ex -> Mono.empty();

            StepVerifier.create(filter.filter(exchange, chain))
                .verifyComplete();

            assertThat(exchange.getResponse().getStatusCode()).isEqualTo(HttpStatus.UNAUTHORIZED);
        }
    }
}
