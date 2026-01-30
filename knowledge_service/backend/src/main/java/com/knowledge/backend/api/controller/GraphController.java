package com.knowledge.backend.api.controller;

import com.knowledge.backend.api.dto.graph.ExpertSearchRequest;
import com.knowledge.backend.api.dto.graph.ExpertSearchResponse;
import com.knowledge.backend.security.JwtUser;
import com.knowledge.backend.service.GraphService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import reactor.core.publisher.Mono;

/**
 * Graph API Controller
 *
 * <p>Provides Knowledge Graph endpoints for expert discovery and relationship queries.
 * All endpoints require authentication via JWT token.
 *
 * <p>Endpoints:
 * <ul>
 *   <li>POST /api/v1/graph/experts - Search for experts by topic</li>
 * </ul>
 *
 * <p>Architecture: Controller converts DTOs to domain parameters
 * before calling Service methods (no RequestDTO passed to Service layer).
 */
@RestController
@RequestMapping("/api/v1/graph")
@RequiredArgsConstructor
@Validated
@Slf4j
public class GraphController {

    private final GraphService graphService;

    /**
     * Search for experts by topic
     *
     * <p>Queries the Knowledge Graph to find experts with expertise
     * in the specified topic. Uses vector similarity and graph relationships
     * to identify relevant experts.
     *
     * @param request expert search request with topic and limit
     * @param user authenticated JWT user
     * @return expert search response with ranked results
     */
    @PostMapping("/experts")
    @PreAuthorize("hasAnyRole('USER', 'VIEWER', 'DEVELOPER', 'ADMIN')")
    public Mono<ExpertSearchResponse> findExperts(
            @Valid @RequestBody ExpertSearchRequest request,
            @AuthenticationPrincipal JwtUser user
    ) {
        String userId = user != null ? user.id() : null;
        log.info("Expert search from user: {} ({}), topic: {}, limit: {}",
                user != null ? user.username() : "anonymous",
                user != null ? user.realmRoles() : "no roles",
                request.getTopic(),
                request.getLimit());

        return graphService.findExperts(
                request.getTopic(),
                request.getLimit(),
                userId
        );
    }
}
