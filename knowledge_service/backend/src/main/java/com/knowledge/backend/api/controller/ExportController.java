package com.knowledge.backend.api.controller;

import java.util.UUID;

import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.knowledge.backend.api.dto.export.ExportSearchRequest;
import com.knowledge.backend.service.ExportService;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import reactor.core.publisher.Mono;

/**
 * Export API Controller
 *
 * <p>Handles document export operations.
 *
 * <p>Endpoints:
 * <ul>
 *   <li>GET  /api/v1/export/pdf/{documentId}     - Export as PDF</li>
 *   <li>GET  /api/v1/export/excel/{documentId}   - Export as Excel/CSV</li>
 *   <li>POST /api/v1/export/search               - Export search results</li>
 *   <li>GET  /api/v1/export/document/{documentId} - Export document content</li>
 * </ul>
 */
@Slf4j
@RestController
@RequestMapping("/api/v1/export")
@RequiredArgsConstructor
public class ExportController {

    private final ExportService exportService;

    /**
     * Export document as PDF
     *
     * @param documentId the document UUID
     * @return byte array of PDF content
     */
    @GetMapping("/pdf/{documentId}")
    @PreAuthorize("hasAnyRole('USER', 'DEVELOPER', 'ADMIN')")
    public Mono<ResponseEntity<byte[]>> exportPdf(@PathVariable UUID documentId) {
        log.info("GET /export/pdf/{}", documentId);

        return exportService.exportAsPdf(documentId)
                .map(bytes -> ResponseEntity.ok()
                        .header(HttpHeaders.CONTENT_DISPOSITION,
                                "attachment; filename=\"document-" + documentId + ".pdf\"")
                        .contentType(MediaType.APPLICATION_PDF)
                        .contentLength(bytes.length)
                        .body(bytes));
    }

    /**
     * Export document as Excel (CSV format)
     *
     * @param documentId the document UUID
     * @return byte array of Excel/CSV content
     */
    @GetMapping("/excel/{documentId}")
    @PreAuthorize("hasAnyRole('USER', 'DEVELOPER', 'ADMIN')")
    public Mono<ResponseEntity<byte[]>> exportExcel(@PathVariable UUID documentId) {
        log.info("GET /export/excel/{}", documentId);

        return exportService.exportAsExcel(documentId)
                .map(bytes -> ResponseEntity.ok()
                        .header(HttpHeaders.CONTENT_DISPOSITION,
                                "attachment; filename=\"document-" + documentId + ".csv\"")
                        .contentType(MediaType.parseMediaType("text/csv"))
                        .contentLength(bytes.length)
                        .body(bytes));
    }

    /**
     * Export search results as CSV
     *
     * <p>Performs a search and exports the results in the requested format.
     *
     * @param request export search request with query and format
     * @return byte array of exported search results
     */
    @PostMapping("/search")
    @PreAuthorize("hasAnyRole('USER', 'DEVELOPER', 'ADMIN')")
    public Mono<ResponseEntity<byte[]>> exportSearchResults(
            @Valid @RequestBody ExportSearchRequest request
    ) {
        log.info("POST /export/search - query: {}, format: {}", request.getQuery(), request.getFormat());

        return exportService.exportSearchResults(request.getQuery(), request.getFormat(), request.getMaxResults())
                .map(bytes -> {
                    String filename = "search-results." + (request.getFormat() != null ? request.getFormat() : "csv");
                    String contentType = "csv".equalsIgnoreCase(request.getFormat())
                            ? "text/csv"
                            : "application/octet-stream";

                    return ResponseEntity.ok()
                            .header(HttpHeaders.CONTENT_DISPOSITION,
                                    "attachment; filename=\"" + filename + "\"")
                            .contentType(MediaType.parseMediaType(contentType))
                            .contentLength(bytes.length)
                            .body(bytes);
                });
    }

    /**
     * Export document content (combined text)
     *
     * <p>Exports the full document content as a text file.
     *
     * @param documentId the document UUID
     * @param format optional format (txt or md, default txt)
     * @return byte array of document content
     */
    @GetMapping("/document/{documentId}")
    @PreAuthorize("hasAnyRole('USER', 'DEVELOPER', 'ADMIN')")
    public Mono<ResponseEntity<byte[]>> exportDocument(
            @PathVariable UUID documentId,
            @RequestParam(defaultValue = "txt") String format
    ) {
        log.info("GET /export/document/{} - format: {}", documentId, format);

        return exportService.exportDocumentContent(documentId, format)
                .map(bytes -> {
                    String contentType = "md".equalsIgnoreCase(format)
                            ? "text/markdown"
                            : "text/plain";

                    return ResponseEntity.ok()
                            .header(HttpHeaders.CONTENT_DISPOSITION,
                                    "attachment; filename=\"document-" + documentId + "." + format + "\"")
                            .contentType(MediaType.parseMediaType(contentType))
                            .contentLength(bytes.length)
                            .body(bytes);
                });
    }
}
