package com.knowledge.backend.config;

import io.minio.MinioClient;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * MinIO Configuration
 *
 * <p>Configures MinIO client for S3-compatible object storage.
 * Used for storing uploaded document files.
 *
 * <p>Environment variables (from docker-compose):
 * <ul>
 *   <li>MINIO_URL - MinIO server URL (default: http://localhost:9000)</li>
 *   <li>MINIO_ACCESS_KEY - Access key</li>
 *   <li>MINIO_SECRET_KEY - Secret key</li>
 *   <li>MINIO_BUCKET - Default bucket name (default: documents)</li>
 * </ul>
 */
@Slf4j
@Configuration
public class MinioConfig {

    @Value("${minio.url:http://localhost:9000}")
    private String minioUrl;

    @Value("${minio.access-key:}")
    private String accessKey;

    @Value("${minio.secret-key:}")
    private String secretKey;

    @Value("${minio.bucket:documents}")
    private String bucket;

    /**
     * Creates MinIO client bean
     *
     * @return configured MinioClient instance
     */
    @Bean
    public MinioClient minioClient() {
        log.info("Initializing MinIO client - url: {}, bucket: {}", minioUrl, bucket);

        if (accessKey == null || accessKey.isBlank()) {
            log.warn("MinIO access key is not set. File upload will fail.");
        }

        return MinioClient.builder()
                .endpoint(minioUrl)
                .credentials(accessKey, secretKey)
                .build();
    }

    /**
     * Get configured bucket name
     *
     * @return bucket name
     */
    public String getBucket() {
        return bucket;
    }
}
