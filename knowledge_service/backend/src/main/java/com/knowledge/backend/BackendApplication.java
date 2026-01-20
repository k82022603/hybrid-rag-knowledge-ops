package com.knowledge.backend;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Knowledge Platform Backend Application
 *
 * <p>SpringBoot 3.x 기반 Backend 서비스
 * - REST API 제공
 * - SSE 스트리밍 지원
 * - AI Service 연동
 */
@SpringBootApplication
public class BackendApplication {

    public static void main(String[] args) {
        SpringApplication.run(BackendApplication.class, args);
    }
}
