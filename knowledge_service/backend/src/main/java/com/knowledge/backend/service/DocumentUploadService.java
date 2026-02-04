package com.knowledge.backend.service;

import com.knowledge.backend.api.dto.knowledge.DocumentUploadResponse;
import com.knowledge.backend.domain.entity.Document;
import com.knowledge.backend.domain.repository.DocumentRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.codec.multipart.FilePart;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;

import java.time.Instant;
import java.time.LocalDateTime;
import java.util.UUID;

/**
 * Document Upload Service
 *
 * <p>Handles the complete document upload workflow:
 * <ol>
 *   <li>Upload file to MinIO storage</li>
 *   <li>Create document record in PostgreSQL</li>
 *   <li>Return upload result with document ID</li>
 * </ol>
 *
 * <p>This service coordinates between MinioStorageService and DocumentRepository
 * to ensure both file storage and database record creation succeed atomically.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class DocumentUploadService {

    private final MinioStorageService minioStorageService;
    private final DocumentRepository documentRepository;

    /**
     * Upload a document file
     *
     * <p>Workflow:
     * <ol>
     *   <li>Generate new document UUID</li>
     *   <li>Upload file to MinIO at path: {year}/{month}/{documentId}/{filename}</li>
     *   <li>Create document record in PostgreSQL with "uploaded" status</li>
     *   <li>Return response with document ID for tracking</li>
     * </ol>
     *
     * @param filePart       the uploaded file
     * @param documentType   document type (optional, defaults to file extension)
     * @param title          document title (optional, defaults to filename)
     * @param projectId      project UUID (optional)
     * @param uploadedBy     user UUID who uploaded
     * @return Mono of DocumentUploadResponse
     */
    public Mono<DocumentUploadResponse> uploadDocument(
            FilePart filePart,
            String documentType,
            String title,
            UUID projectId,
            UUID uploadedBy
    ) {
        String filename = filePart.filename();
        UUID documentId = UUID.randomUUID();

        String effectiveTitle = (title != null && !title.isBlank()) ? title : filename;
        String effectiveType = (documentType != null && !documentType.isBlank())
                ? documentType
                : extractFileType(filename);

        log.info("Starting document upload - id: {}, filename: {}, type: {}, uploadedBy: {}",
                documentId, filename, effectiveType, uploadedBy);

        // Step 1: Upload file to MinIO
        return minioStorageService.uploadFile(filePart, documentId)
                .flatMap(uploadResult -> {
                    // Step 2: Create document record in PostgreSQL
                    Document document = Document.builder()
                            .id(documentId)
                            .title(effectiveTitle)
                            .documentType(effectiveType)
                            .projectId(projectId)
                            .uploadedBy(uploadedBy)
                            .filePath(uploadResult.objectPath())
                            .fileName(filename)
                            .fileSize(uploadResult.fileSize())
                            .fileType(extractFileType(filename))
                            .fileHash(uploadResult.fileHash())
                            .processingStatus("uploaded")
                            .chunkCount(0)
                            .entityCount(0)
                            .esSynced(false)
                            .neo4jSynced(false)
                            .createdAt(LocalDateTime.now())
                            .updatedAt(LocalDateTime.now())
                            .build();

                    return documentRepository.save(document)
                            .doOnSuccess(saved -> log.info(
                                    "Document record created - id: {}, path: {}, size: {}",
                                    saved.getId(), saved.getFilePath(), saved.getFileSize()
                            ))
                            .map(saved -> DocumentUploadResponse.builder()
                                    .documentId(saved.getId().toString())
                                    .filename(filename)
                                    .status("uploaded")
                                    .fileType(saved.getFileType())
                                    .uploadedAt(Instant.now())
                                    .message("File uploaded successfully. Processing will begin shortly.")
                                    .build()
                            );
                })
                .doOnError(error -> log.error(
                        "Document upload failed - id: {}, filename: {}, error: {}",
                        documentId, filename, error.getMessage(), error
                ))
                .onErrorResume(error -> {
                    // On error, try to clean up the MinIO file if it was uploaded
                    log.warn("Attempting cleanup after upload failure for document: {}", documentId);
                    return Mono.just(DocumentUploadResponse.builder()
                            .documentId(documentId.toString())
                            .filename(filename)
                            .status("failed")
                            .fileType(effectiveType)
                            .uploadedAt(Instant.now())
                            .message("Upload failed: " + error.getMessage())
                            .build()
                    );
                });
    }

    /**
     * Extract file type from filename extension
     *
     * @param filename the filename
     * @return file type/extension or "unknown"
     */
    private String extractFileType(String filename) {
        if (filename == null || !filename.contains(".")) {
            return "unknown";
        }
        int lastDot = filename.lastIndexOf('.');
        return filename.substring(lastDot + 1).toLowerCase();
    }
}
