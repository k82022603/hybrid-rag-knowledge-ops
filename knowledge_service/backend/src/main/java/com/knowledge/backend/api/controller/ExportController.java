package com.knowledge.backend.api.controller;

import java.util.UUID;

import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.knowledge.backend.service.ExportService;

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
 *   <li>GET /api/v1/export/pdf/{documentId}   - Export as PDF</li>
 *   <li>GET /api/v1/export/excel/{documentId} - Export as Excel/CSV</li>
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
}
