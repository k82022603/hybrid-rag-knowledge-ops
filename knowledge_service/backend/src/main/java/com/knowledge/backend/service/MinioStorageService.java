package com.knowledge.backend.service;

import io.minio.BucketExistsArgs;
import io.minio.GetObjectArgs;
import io.minio.MakeBucketArgs;
import io.minio.MinioClient;
import io.minio.PutObjectArgs;
import io.minio.RemoveObjectArgs;
import io.minio.StatObjectArgs;
import io.minio.StatObjectResponse;
import io.minio.errors.MinioException;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.core.io.buffer.DataBufferUtils;
import org.springframework.http.codec.multipart.FilePart;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;
import reactor.core.scheduler.Schedulers;

import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.security.MessageDigest;
import java.time.LocalDate;
import java.util.UUID;

/**
 * MinIO Storage Service
 *
 * <p>Handles file storage operations using MinIO S3-compatible object storage.
 * Provides reactive wrapper around the synchronous MinIO client.
 *
 * <p>Storage path pattern: {year}/{month}/{documentId}/{filename}
 */
@Slf4j
@Service
public class MinioStorageService {

    private final MinioClient minioClient;
    private final String bucket;

    public MinioStorageService(
            MinioClient minioClient,
            @Value("${minio.bucket:documents}") String bucket
    ) {
        this.minioClient = minioClient;
        this.bucket = bucket;
    }

    /**
     * Initialize bucket if not exists
     *
     * @return Mono<Void> completion signal
     */
    public Mono<Void> initBucket() {
        return Mono.fromCallable(() -> {
            try {
                boolean exists = minioClient.bucketExists(
                        BucketExistsArgs.builder().bucket(bucket).build()
                );
                if (!exists) {
                    minioClient.makeBucket(
                            MakeBucketArgs.builder().bucket(bucket).build()
                    );
                    log.info("Created MinIO bucket: {}", bucket);
                }
                return true;
            } catch (MinioException e) {
                log.error("Failed to initialize bucket: {}", e.getMessage(), e);
                throw new RuntimeException("Failed to initialize MinIO bucket", e);
            }
        }).subscribeOn(Schedulers.boundedElastic()).then();
    }

    /**
     * Upload file to MinIO
     *
     * @param filePart   the file to upload
     * @param documentId document UUID for path organization
     * @return Mono of FileUploadResult containing path, size, and hash
     */
    public Mono<FileUploadResult> uploadFile(FilePart filePart, UUID documentId) {
        String filename = filePart.filename();
        String objectPath = generateObjectPath(documentId, filename);

        log.info("Uploading file to MinIO: bucket={}, path={}", bucket, objectPath);

        return DataBufferUtils.join(filePart.content())
                .flatMap(dataBuffer -> {
                    byte[] bytes = new byte[dataBuffer.readableByteCount()];
                    dataBuffer.read(bytes);
                    DataBufferUtils.release(dataBuffer);

                    return Mono.fromCallable(() -> {
                        try {
                            // Calculate file hash (SHA-256)
                            String fileHash = calculateSha256(bytes);

                            // Determine content type
                            String contentType = determineContentType(filename);

                            // Upload to MinIO
                            try (InputStream inputStream = new ByteArrayInputStream(bytes)) {
                                minioClient.putObject(
                                        PutObjectArgs.builder()
                                                .bucket(bucket)
                                                .object(objectPath)
                                                .stream(inputStream, bytes.length, -1)
                                                .contentType(contentType)
                                                .build()
                                );
                            }

                            log.info("File uploaded successfully: path={}, size={}, hash={}",
                                    objectPath, bytes.length, fileHash.substring(0, 16) + "...");

                            return new FileUploadResult(
                                    objectPath,
                                    (long) bytes.length,
                                    fileHash,
                                    contentType
                            );
                        } catch (Exception e) {
                            log.error("Failed to upload file to MinIO: {}", e.getMessage(), e);
                            throw new RuntimeException("Failed to upload file to MinIO", e);
                        }
                    }).subscribeOn(Schedulers.boundedElastic());
                });
    }

    /**
     * Delete file from MinIO
     *
     * @param objectPath the object path to delete
     * @return Mono<Void> completion signal
     */
    public Mono<Void> deleteFile(String objectPath) {
        return Mono.fromCallable(() -> {
            try {
                minioClient.removeObject(
                        RemoveObjectArgs.builder()
                                .bucket(bucket)
                                .object(objectPath)
                                .build()
                );
                log.info("File deleted from MinIO: {}", objectPath);
                return true;
            } catch (Exception e) {
                log.error("Failed to delete file from MinIO: {}", e.getMessage(), e);
                throw new RuntimeException("Failed to delete file from MinIO", e);
            }
        }).subscribeOn(Schedulers.boundedElastic()).then();
    }

    /**
     * Check if file exists in MinIO
     *
     * @param objectPath the object path to check
     * @return Mono<Boolean> true if exists
     */
    public Mono<Boolean> fileExists(String objectPath) {
        return Mono.fromCallable(() -> {
            try {
                minioClient.statObject(
                        StatObjectArgs.builder()
                                .bucket(bucket)
                                .object(objectPath)
                                .build()
                );
                return true;
            } catch (Exception e) {
                return false;
            }
        }).subscribeOn(Schedulers.boundedElastic());
    }

    /**
     * Get file metadata from MinIO
     *
     * @param objectPath the object path
     * @return Mono of StatObjectResponse
     */
    public Mono<StatObjectResponse> getFileInfo(String objectPath) {
        return Mono.fromCallable(() -> {
            try {
                return minioClient.statObject(
                        StatObjectArgs.builder()
                                .bucket(bucket)
                                .object(objectPath)
                                .build()
                );
            } catch (Exception e) {
                log.error("Failed to get file info from MinIO: {}", e.getMessage(), e);
                throw new RuntimeException("Failed to get file info from MinIO", e);
            }
        }).subscribeOn(Schedulers.boundedElastic());
    }

    /**
     * Generate object path for storage
     * Pattern: {year}/{month}/{documentId}/{filename}
     *
     * @param documentId the document UUID
     * @param filename   the original filename
     * @return object path
     */
    private String generateObjectPath(UUID documentId, String filename) {
        LocalDate now = LocalDate.now();
        return String.format("%d/%02d/%s/%s",
                now.getYear(),
                now.getMonthValue(),
                documentId.toString(),
                sanitizeFilename(filename)
        );
    }

    /**
     * Sanitize filename for safe storage
     *
     * @param filename original filename
     * @return sanitized filename
     */
    private String sanitizeFilename(String filename) {
        if (filename == null || filename.isBlank()) {
            return "unnamed";
        }
        // Replace problematic characters but preserve Korean characters
        return filename.replaceAll("[\\\\/:*?\"<>|]", "_");
    }

    /**
     * Calculate SHA-256 hash of file content
     *
     * @param bytes file content
     * @return hex-encoded hash string
     */
    private String calculateSha256(byte[] bytes) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(bytes);
            StringBuilder hexString = new StringBuilder();
            for (byte b : hash) {
                String hex = Integer.toHexString(0xff & b);
                if (hex.length() == 1) {
                    hexString.append('0');
                }
                hexString.append(hex);
            }
            return hexString.toString();
        } catch (Exception e) {
            log.warn("Failed to calculate file hash: {}", e.getMessage());
            return "";
        }
    }

    /**
     * Determine content type from filename
     *
     * @param filename the filename
     * @return MIME content type
     */
    private String determineContentType(String filename) {
        if (filename == null) {
            return "application/octet-stream";
        }
        String lower = filename.toLowerCase();
        if (lower.endsWith(".pdf")) return "application/pdf";
        if (lower.endsWith(".docx")) return "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
        if (lower.endsWith(".doc")) return "application/msword";
        if (lower.endsWith(".xlsx")) return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
        if (lower.endsWith(".xls")) return "application/vnd.ms-excel";
        if (lower.endsWith(".pptx")) return "application/vnd.openxmlformats-officedocument.presentationml.presentation";
        if (lower.endsWith(".ppt")) return "application/vnd.ms-powerpoint";
        if (lower.endsWith(".txt")) return "text/plain";
        if (lower.endsWith(".md")) return "text/markdown";
        if (lower.endsWith(".hwp")) return "application/x-hwp";
        if (lower.endsWith(".hwpx")) return "application/vnd.hancom.hwpx";
        return "application/octet-stream";
    }

    /**
     * File upload result record
     */
    public record FileUploadResult(
            String objectPath,
            Long fileSize,
            String fileHash,
            String contentType
    ) {}
}
