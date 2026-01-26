package com.knowledge.backend.service;

import java.nio.charset.StandardCharsets;
import java.util.UUID;

import org.springframework.stereotype.Service;

import com.knowledge.backend.domain.repository.ChunkRepository;
import com.knowledge.backend.domain.repository.DocumentRepository;
import com.knowledge.backend.exception.ResourceNotFoundException;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import reactor.core.publisher.Mono;

/**
 * Export Service
 *
 * <p>Handles document export operations (PDF, Excel).
 * Currently generates simple text-based exports.
 * Future versions will integrate with proper PDF/Excel generation libraries.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ExportService {

    private final DocumentRepository documentRepository;
    private final ChunkRepository chunkRepository;

    /**
     * Export document as PDF (currently returns text content as bytes)
     *
     * @param documentId the document UUID
     * @return Mono of byte array (PDF content)
     */
    public Mono<byte[]> exportAsPdf(UUID documentId) {
        log.info("Exporting document as PDF: {}", documentId);

        return documentRepository.findById(documentId)
                .switchIfEmpty(Mono.error(new ResourceNotFoundException("Document", documentId)))
                .flatMap(doc ->
                    chunkRepository.findByDocumentIdOrderByChunkIndex(documentId)
                        .map(chunk -> chunk.getContent())
                        .collectList()
                        .map(chunks -> {
                            StringBuilder sb = new StringBuilder();
                            sb.append("Document: ").append(doc.getTitle()).append("\n");
                            sb.append("Type: ").append(doc.getDocumentType()).append("\n");
                            sb.append("Status: ").append(doc.getProcessingStatus()).append("\n");
                            sb.append("Created: ").append(doc.getCreatedAt()).append("\n");
                            sb.append("---\n\n");

                            for (int i = 0; i < chunks.size(); i++) {
                                sb.append("[Chunk ").append(i + 1).append("]\n");
                                sb.append(chunks.get(i)).append("\n\n");
                            }

                            return sb.toString().getBytes(StandardCharsets.UTF_8);
                        })
                )
                .doOnSuccess(bytes -> log.info("PDF export completed for document: {}, size: {} bytes",
                        documentId, bytes.length));
    }

    /**
     * Export document as Excel (currently returns CSV format as bytes)
     *
     * @param documentId the document UUID
     * @return Mono of byte array (Excel/CSV content)
     */
    public Mono<byte[]> exportAsExcel(UUID documentId) {
        log.info("Exporting document as Excel: {}", documentId);

        return documentRepository.findById(documentId)
                .switchIfEmpty(Mono.error(new ResourceNotFoundException("Document", documentId)))
                .flatMap(doc ->
                    chunkRepository.findByDocumentIdOrderByChunkIndex(documentId)
                        .collectList()
                        .map(chunks -> {
                            StringBuilder csv = new StringBuilder();
                            csv.append("chunk_index,heading,content,token_count\n");

                            for (var chunk : chunks) {
                                csv.append(chunk.getChunkIndex()).append(",");
                                csv.append(escapeCSV(chunk.getHeading())).append(",");
                                csv.append(escapeCSV(chunk.getContent())).append(",");
                                csv.append(chunk.getTokenCount() != null ? chunk.getTokenCount() : "").append("\n");
                            }

                            return csv.toString().getBytes(StandardCharsets.UTF_8);
                        })
                )
                .doOnSuccess(bytes -> log.info("Excel export completed for document: {}, size: {} bytes",
                        documentId, bytes.length));
    }

    /**
     * Escape CSV field value
     *
     * @param value the value to escape
     * @return escaped CSV value
     */
    private String escapeCSV(String value) {
        if (value == null) return "";
        if (value.contains(",") || value.contains("\"") || value.contains("\n")) {
            return "\"" + value.replace("\"", "\"\"") + "\"";
        }
        return value;
    }
}
