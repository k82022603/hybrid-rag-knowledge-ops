# 04_testing - 테스트 문서

Hybrid RAG Knowledge Operations Platform의 테스트 관련 문서 모음입니다.

---

## 폴더 구조

```
04_testing/
├── README.md                           # 본 문서
├── unit_integration_test_plan.md       # 단위/통합 테스트 계획서
├── e2e_test_plan_sprint02.md           # Sprint 02 E2E 테스트 계획서
├── sprint03_wave3_test_plan.md         # Sprint 03 Wave 3 테스트 계획서
├── sprint03_day2_qa_report.md          # Sprint 03 Day 2 QA 보고서
├── sprint04_e2e_test_plan.md           # Sprint 04 E2E 테스트 계획서 (P0 4건)
├── staging_validation_checklist.md     # Staging 환경 검증 체크리스트 (NEW)
├── staging_validation_report_template.md # Staging 검증 보고서 템플릿 (NEW)
├── docling_parser_test_report.md       # Docling Parser 테스트 리포트
├── rag_test_dataset_plan.md            # RAG 테스트 데이터셋 계획서
├── test_plans/                         # 개별 Story 테스트 계획서
│   ├── E2E_playwright_test_plan.md
│   ├── STORY-024_auth_test_plan.md
│   ├── STORY-031_rrf_fusion_test_plan.md
│   ├── STORY-032_bge_reranker_test_plan.md
│   ├── STORY-041_dashboard_ui_test_plan.md
│   ├── STORY-042_search_ui_test_plan.md
│   ├── STORY-044_backend_search_service_test_plan.md
│   └── STORY-045_initial_data_etl_test_plan.md
├── test_cases/                         # 테스트 케이스
│   └── auth/                           # 인증 테스트 케이스
├── test_results/                       # 테스트 실행 결과
├── infrastructure_e2e/                 # 인프라 E2E 테스트
└── technical_assessment/               # 기술 평가
```

---

## 문서 목록

| 문서 | 설명 | 버전 | 최종 수정 |
|------|------|------|----------|
| [unit_integration_test_plan.md](./unit_integration_test_plan.md) | 단위/통합 테스트 계획서 | 1.0 | 2026-01-17 |
| [e2e_test_plan_sprint02.md](./e2e_test_plan_sprint02.md) | Sprint 02 E2E 테스트 계획서 | 1.0 | 2026-01-26 |
| [sprint03_wave3_test_plan.md](./sprint03_wave3_test_plan.md) | Sprint 03 Wave 3 테스트 계획서 (88 TC) | 1.0 | 2026-01-28 |
| [sprint03_day2_qa_report.md](./sprint03_day2_qa_report.md) | Sprint 03 Day 2 QA 보고서 | 1.0 | 2026-01-28 |
| [sprint04_e2e_test_plan.md](./sprint04_e2e_test_plan.md) | Sprint 04 E2E 테스트 계획서 (78 TC, P0 4건) | 1.0 | 2026-01-28 |
| [staging_validation_checklist.md](./staging_validation_checklist.md) | Staging 환경 검증 체크리스트 | 1.0 | 2026-02-04 |
| [staging_validation_report_template.md](./staging_validation_report_template.md) | Staging 검증 보고서 템플릿 | 1.0 | 2026-02-04 |

---

## Staging Validation (STORY-080)

프로덕션 배포 전 Staging 환경 종합 검증을 위한 문서 및 스크립트입니다.

### 검증 항목

| Category | Test Count | Target | Tool |
|----------|------------|--------|------|
| Unit Tests | 627 | 100% | JUnit, pytest, Vitest |
| Integration Tests | 121 | 100% | Testcontainers |
| E2E Tests | 192 | 100% | Playwright |
| Security Tests | 35 | 100% | pytest, custom |
| **Total** | **975** | **100%** | - |

### 자동화 스크립트

```bash
# Full validation
./infrastructure/scripts/staging-validation.sh --full

# Quick smoke test
./infrastructure/scripts/staging-validation.sh --smoke

# Specific category
./infrastructure/scripts/staging-validation.sh --category unit
./infrastructure/scripts/staging-validation.sh --category e2e
./infrastructure/scripts/staging-validation.sh --category security
```

### 관련 스크립트

| Script | Description | Location |
|--------|-------------|----------|
| staging-validation.sh | Staging 환경 종합 검증 | `infrastructure/scripts/` |
| pre-deploy-check.sh | 배포 전 시스템 점검 | `infrastructure/scripts/` |
| post-deploy-verify.sh | 배포 후 검증 | `infrastructure/scripts/` |

---

## 테스트 주체 요약

| 테스트 유형 | 주체 | 책임 |
|------------|------|------|
| **단위 테스트** | 개발팀 | 작성 및 실행 |
| **통합 테스트** | 개발팀 + QA팀 | 개발팀 작성, QA팀 검증 |
| **E2E 테스트** | QA팀 | 작성 및 실행 |
| **성능 테스트** | 개발팀 + QA팀 | 공동 수행 |
| **Contract 테스트** | QA팀 | STORY-054 (Sprint 04 Week 2) |
| **보안 테스트** | QA팀 | STORY-055 (Sprint 04 Week 2) |
| **Staging 검증** | QA팀 | STORY-080 (Sprint 05) |

---

## 관련 문서

- [RAG 성능 테스트 설계서](../02_design/rag_performance_test_design.md) - 추론/응답 품질 평가 기준
- [백엔드 설계서](../02_design/backend_detailed_design.md) - 테스트 구조 참조
- [API 통합 설계서](../02_design/api_integration_design.md) - API 스펙 참조
- [인프라 스크립트 가이드](../../../infrastructure/scripts/README.md) - 배포/검증 스크립트

---

## 테스트 도구

| 영역 | 도구 |
|------|------|
| Backend | JUnit 5, Mockito, Testcontainers |
| AI Service | pytest, httpx, testcontainers-python |
| Frontend | Vitest, React Testing Library, MSW |
| E2E | Playwright (Chromium), pytest + httpx |
| 성능 | k6, pytest-benchmark |
| 보안 | Custom pytest scripts, OWASP ZAP (optional) |
| CI/CD | GitHub Actions |
| 커버리지 | SonarQube, Codecov, pytest-cov |
| Staging 검증 | staging-validation.sh (Bash) |
