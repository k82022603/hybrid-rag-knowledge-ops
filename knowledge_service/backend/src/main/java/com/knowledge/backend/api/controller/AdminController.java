package com.knowledge.backend.api.controller;

import java.util.Map;
import java.util.UUID;

import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.knowledge.backend.api.dto.admin.AuditLogResponse;
import com.knowledge.backend.api.dto.admin.RoleUpdateRequest;
import com.knowledge.backend.api.dto.admin.StatusUpdateRequest;
import com.knowledge.backend.api.dto.admin.SystemConfigResponse;
import com.knowledge.backend.api.dto.admin.SystemConfigUpdateRequest;
import com.knowledge.backend.api.dto.user.UserProfileResponse;
import com.knowledge.backend.security.JwtUser;
import com.knowledge.backend.service.AdminService;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

/**
 * Admin API Controller
 *
 * <p>Administrative operations requiring ADMIN role.
 *
 * <p>Endpoints:
 * <ul>
 *   <li>GET  /api/v1/admin/users              - List users</li>
 *   <li>PUT  /api/v1/admin/users/{id}/roles   - Update user role (RESTful plural)</li>
 *   <li>PUT  /api/v1/admin/users/{id}/status  - Update user status</li>
 *   <li>GET  /api/v1/admin/system             - Get system config</li>
 *   <li>PUT  /api/v1/admin/system             - Update system config</li>
 *   <li>GET  /api/v1/admin/audit-logs         - Get audit logs</li>
 * </ul>
 */
@Slf4j
@RestController
@RequestMapping("/api/v1/admin")
@RequiredArgsConstructor
@PreAuthorize("hasRole('ADMIN')")
public class AdminController {

    private final AdminService adminService;

    /**
     * Get paginated user list
     *
     * @param page page number (default 0)
     * @param size page size (default 20)
     * @return Flux of UserProfileResponse
     */
    @GetMapping("/users")
    public Flux<UserProfileResponse> getUsers(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size
    ) {
        log.info("GET /admin/users - page={}, size={}", page, size);
        return adminService.getUsers(page, size);
    }

    /**
     * Update user role
     *
     * @param id      the user UUID
     * @param request role update data
     * @return Mono of updated UserProfileResponse
     */
    @PutMapping("/users/{id}/roles")
    public Mono<ResponseEntity<UserProfileResponse>> updateUserRoles(
            @PathVariable UUID id,
            @Valid @RequestBody RoleUpdateRequest request
    ) {
        log.info("PUT /admin/users/{}/roles - role={}", id, request.getRole());

        return adminService.updateUserRole(id, request.getRole())
                .map(ResponseEntity::ok);
    }

    /**
     * Update user active status
     *
     * @param id      the user UUID
     * @param request status update data
     * @return Mono of updated UserProfileResponse
     */
    @PutMapping("/users/{id}/status")
    public Mono<ResponseEntity<UserProfileResponse>> updateUserStatus(
            @PathVariable UUID id,
            @Valid @RequestBody StatusUpdateRequest request
    ) {
        log.info("PUT /admin/users/{}/status - isActive={}", id, request.getIsActive());

        return adminService.updateUserStatus(id, request.getIsActive())
                .map(ResponseEntity::ok);
    }

    /**
     * Get system configuration
     *
     * @return Flux of SystemConfigResponse
     */
    @GetMapping("/system")
    public Flux<SystemConfigResponse> getSystemConfig() {
        log.info("GET /admin/system");
        return adminService.getSystemConfig();
    }

    /**
     * Update system configuration
     *
     * @param request system config update data
     * @param principal authenticated admin user
     * @return Flux of updated SystemConfigResponse
     */
    @PutMapping("/system")
    public Flux<SystemConfigResponse> updateSystemConfig(
            @Valid @RequestBody SystemConfigUpdateRequest request,
            @AuthenticationPrincipal Object principal
    ) {
        UUID updatedBy = extractUserId(principal);
        log.info("PUT /admin/system - {} entries, by user: {}", request.getConfigs().size(), updatedBy);

        return adminService.updateSystemConfig(request.getConfigs(), updatedBy);
    }

    /**
     * Get audit logs
     *
     * @param page page number (default 0)
     * @param size page size (default 50)
     * @return Flux of AuditLogResponse
     */
    @GetMapping("/audit-logs")
    public Flux<AuditLogResponse> getAuditLogs(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "50") int size
    ) {
        log.info("GET /admin/audit-logs - page={}, size={}", page, size);
        return adminService.getAuditLogs(page, size);
    }

    /**
     * Get system statistics
     *
     * @return Mono of system stats map
     */
    @GetMapping("/stats")
    public Mono<Map<String, Object>> getSystemStats() {
        log.info("GET /admin/stats");
        return adminService.getSystemStats();
    }

    /**
     * Extract user UUID from authentication principal
     *
     * @param principal the authentication principal
     * @return user UUID or null
     */
    private UUID extractUserId(Object principal) {
        if (principal instanceof JwtUser user) {
            try {
                return UUID.fromString(user.id());
            } catch (IllegalArgumentException e) {
                log.debug("User ID is not a UUID: {}", user.id());
                return null;
            }
        }
        return null;
    }
}
