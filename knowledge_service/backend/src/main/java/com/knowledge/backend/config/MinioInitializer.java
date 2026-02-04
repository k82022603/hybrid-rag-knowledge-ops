package com.knowledge.backend.config;

import com.knowledge.backend.service.MinioStorageService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

/**
 * MinIO Bucket Initializer
 *
 * <p>Ensures the configured MinIO bucket exists on application startup.
 * Runs after all beans are initialized.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class MinioInitializer {

    private final MinioStorageService minioStorageService;

    /**
     * Initialize MinIO bucket on application ready
     */
    @EventListener(ApplicationReadyEvent.class)
    public void initializeMinioBucket() {
        log.info("Initializing MinIO bucket...");

        minioStorageService.initBucket()
                .doOnSuccess(v -> log.info("MinIO bucket initialization completed"))
                .doOnError(e -> log.warn("MinIO bucket initialization failed: {}. " +
                        "File uploads may fail until MinIO is available.", e.getMessage()))
                .subscribe();
    }
}
