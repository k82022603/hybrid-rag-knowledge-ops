package com.knowledge.backend.service;

import java.time.LocalDateTime;
import java.util.UUID;
import java.util.regex.Pattern;

import org.springframework.stereotype.Service;

import com.knowledge.backend.domain.repository.AuditLogRepository;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import reactor.core.scheduler.Schedulers;

/**
 * Audit Service
 *
 * <p>Records audit log entries for API request tracking.
 * Saves asynchronously to avoid blocking the main request path.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class AuditService {

    private final AuditLogRepository auditLogRepository;

    /** IPv4/IPv6 basic validation pattern */
    private static final Pattern IP_PATTERN = Pattern.compile(
            "^([0-9]{1,3}\\.){3}[0-9]{1,3}$|^([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}$"
    );

    /**
     * Record an audit log entry (fire-and-forget, non-blocking)
     */
    public void log(
            UUID userId,
            String action,
            String resourceType,
            UUID resourceId,
            String requestPath,
            String ipAddress,
            String userAgent,
            String status,
            String errorMessage,
            Integer durationMs
    ) {
        LocalDateTime now = LocalDateTime.now();

        // Sanitize IP address - only allow valid IP formats
        String sanitizedIp = (ipAddress != null && IP_PATTERN.matcher(ipAddress).matches())
                ? ipAddress : null;

        // Try with user_id first, fallback without on FK violation
        if (userId != null) {
            auditLogRepository.insertLogWithUser(
                            userId, action, resourceType, resourceId,
                            sanitizedIp, userAgent, requestPath,
                            status, errorMessage, durationMs, now)
                    .subscribeOn(Schedulers.boundedElastic())
                    .onErrorResume(error -> {
                        log.debug("Audit with user_id failed (FK?), retrying without: {}",
                                error.getMessage());
                        return auditLogRepository.insertLog(
                                action, resourceType, resourceId,
                                sanitizedIp, userAgent, requestPath,
                                status, errorMessage, durationMs, now);
                    })
                    .subscribe(
                            ignored -> {},
                            error -> log.warn("Failed to save audit log: {}", error.getMessage())
                    );
        } else {
            auditLogRepository.insertLog(
                            action, resourceType, resourceId,
                            sanitizedIp, userAgent, requestPath,
                            status, errorMessage, durationMs, now)
                    .subscribeOn(Schedulers.boundedElastic())
                    .subscribe(
                            ignored -> {},
                            error -> log.warn("Failed to save audit log: {}", error.getMessage())
                    );
        }
    }
}
