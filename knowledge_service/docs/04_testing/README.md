# 04_testing - 테스트 문서

Hybrid RAG Knowledge Operations Platform의 테스트 관련 문서 모음입니다.

---

## 폴더 구조

```
04_testing/
├── README.md                                          # 본 문서
├── 01_unit_integration_test_plan.md                   # 단위/통합 테스트 계획서 (기반 문서)
│
├── 01_test_plans/                                     # Story별 테스트 계획서
│   ├── 00_unit_integration_test_plan.md               # 단위/통합 테스트 계획서
│   ├── 01_E2E_playwright_test_plan.md                 # Playwright E2E 테스트 계획서
│   ├── 02_STORY-024_auth_test_plan.md                 # STORY-024 인증 테스트 계획서
│   ├── 03_STORY-031_rrf_fusion_test_plan.md           # STORY-031 RRF Fusion 테스트 계획서
│   ├── 04_STORY-041_dashboard_ui_test_plan.md         # STORY-041 Dashboard UI 테스트 계획서
│   ├── 05_STORY-044_backend_search_service_test_plan.md # STORY-044 Backend 검색 테스트 계획서
│   ├── 06_STORY-045_initial_data_etl_test_plan.md     # STORY-045 초기 데이터 ETL 테스트 계획서
│   ├── 07_STORY-032_bge_reranker_test_plan.md         # STORY-032 BGE Reranker 테스트 계획서
│   └── 08_STORY-042_search_ui_test_plan.md            # STORY-042 검색 UI 테스트 계획서
│
├── 02_test_cases/                                     # 테스트 케이스
│   └── auth/
│       └── 01_login_redis_integration_test.md         # 로그인 Redis 통합 테스트
│
├── 03_technical_assessment/                           # 기술 평가
│   └── 01_stub_services_testing_strategy.md           # Stub 서비스 테스트 전략
│
├── 04_infrastructure_e2e/                             # 인프라 E2E 테스트
│   ├── 01_infrastructure_e2e_test_plan.md             # 인프라 E2E 테스트 계획서
│   ├── 02_e2e_100_percent_test_plan.md                # E2E 100% 테스트 계획서
│   ├── 03_infrastructure_e2e_test_report_2026-01-20.md # 인프라 E2E 결과 (01-20)
│   ├── 04_infrastructure_e2e_test_report_2026-01-21.md # 인프라 E2E 결과 (01-21)
│   ├── 05_infrastructure_e2e_test_report_2026-01-26.md # 인프라 E2E 결과 (01-26)
│   └── 06_keycloak_e2e_test_report_2026-01-30.md      # Keycloak E2E 결과 (01-30)
│
├── 05_e2e/                                            # E2E 테스트 (계획서, 결과, 가이드)
│   ├── 01_e2e_test_plan_sprint02.md                   # Sprint 02 E2E 테스트 계획서
│   ├── 02_sprint03_wave3_test_plan.md                 # Sprint 03 Wave 3 테스트 계획서 (88 TC)
│   ├── 03_sprint04_e2e_test_plan.md                   # Sprint 04 E2E 테스트 계획서 (78 TC)
│   ├── 04_sprint04_frontend_backend_e2e_test_plan.md  # Sprint 04 Frontend-Backend E2E 계획서
│   ├── 05_frontend_backend_e2e_test_guide.md          # Frontend-Backend E2E 테스트 가이드
│   ├── 06_e2e_test_process.md                         # E2E 테스트 프로세스
│   ├── 07_ui_e2e_test_plan.md                         # UI E2E 테스트 계획서 (28 TC)
│   ├── 08_ui_e2e_test_report_2026-01-30.md            # UI E2E 테스트 결과 (01-30)
│   ├── 09_e2e_failure_analysis_report_2026-01-30.md   # E2E 실패 분석 보고서 (01-30)
│   ├── 10_qa_test_issue_report_2026-01-30.md          # QA 테스트 이슈 보고서 (01-30)
│   ├── 11_ui_api_verification_test_report_2026-01-30.md # UI-API 검증 테스트 보고서 (01-30)
│   ├── 12_e2e_test_review_meeting_2026-01-30.md       # E2E 테스트 검토 회의록 (01-30)
│   ├── 13_docker_env_test_result_2026-01-30.md        # Docker 환경 테스트 결과 (01-30)
│   ├── 14_pm_work_delegation_search_api_2026-01-30.md # PM 작업 위임서: 검색 API (01-30)
│   ├── 15_frontend_e2e_test_results_2026-02-02.md     # Frontend E2E 결과 (02-02)
│   ├── 16_frontend_e2e_test_results_2026-02-03.md     # Frontend E2E 결과 (02-03)
│   ├── 17_frontend_ui_test_methodology.md             # Frontend UI 테스트 방법론
│   └── 18_sprint04_day1_e2e_test_results.md           # Sprint 04 Day 1 E2E 결과 (01-28) *from results/*
│
├── 06_staging/                                        # Staging 환경 검증
│   ├── 01_staging_validation_checklist.md             # Staging 검증 체크리스트
│   └── 02_staging_validation_report_template.md       # Staging 검증 보고서 템플릿
│
├── 07_test_results/                                   # 테스트 실행 결과
│   ├── 01_STORY-024_auth_test_result.md               # STORY-024 인증 테스트 결과
│   ├── 02_E2E_playwright_test_result.md               # Playwright E2E 테스트 결과
│   ├── 03_docker_mode_test_report_2026-02-05.md       # Docker 모드 Unit 테스트 결과 (02-05) *from results/*
│   ├── 04_unit_test_coverage_improvement_report.md    # 커버리지 개선 결과 (02-05) *from results/*
│   ├── 05_embedding_pipeline_verification_report_2026-02-05.md # 임베딩 파이프라인 검증 (02-05) *from results/*
│   ├── 06_story-002_retest_report.md                  # STORY-002 재테스트 결과 (01-27) *from results/*
│   ├── 07_sprint04_document_parser_retry_report.md    # DocumentParser Retry 검증 (01-28) *from results/*
│   └── 08_sprint11_test_gap_p1_report.md              # Sprint 11 테스트 갭 P1 보고서
│
├── 08_analysis/                                       # 분석/감사 보고서
│   ├── 01_docling_parser_test_report.md               # Docling Parser 테스트 보고서
│   ├── 02_sprint03_day2_qa_report.md                  # Sprint 03 Day 2 QA 보고서
│   ├── 03_mock_test_audit_report.md                   # Mock 테스트 전수조사 보고서
│   ├── 04_security_test_results_story055.md           # 보안 테스트 결과 (STORY-055)
│   ├── 05_sprint04_contract_test_report.md            # Sprint 04 Contract 테스트 보고서
│   ├── 06_rag_service_analysis_report.md              # RAG 서비스 분석 보고서
│   ├── 07_unimplemented_api_analysis_report.md        # 미구현 API 분석 보고서
│   ├── 08_full_codebase_unimplemented_analysis_2026-01-30.md # 전체 코드베이스 미구현 분석 (01-30)
│   ├── 09_rag_pipeline_test_results_2026-02-02.md     # RAG 파이프라인 테스트 결과 (02-02)
│   ├── 10_performance_baseline_report.md              # 성능 베이스라인 보고서
│   ├── 11_issue_report_hybrid_search_cpu_bottleneck.md # CPU 병목 이슈 보고서
│   ├── 12_sprint06_phase4_completion_report.md        # Sprint 06 Phase 4 완료 보고서 (02-04) *from results/*
│   └── 13_perf_benchmark_2026-02-06.md                # 성능 벤치마크 결과 (02-06) *from results/*
│
├── 09_user_acceptance_tests/                          # UAT (사용자 인수 테스트)
│   ├── README.md                                      # UAT 개요
│   ├── 00_full_cycle_test_guide.md                    # 전체 사이클 테스트 가이드
│   ├── 01_authentication_login_test_2026-02-04.md     # 인증/로그인 테스트 (02-04)
│   ├── 02_document_upload_test_2026-02-04.md          # 문서 업로드 테스트 (02-04)
│   ├── 03_uat_test_checklist_2026-02-05.md            # UAT 테스트 체크리스트 (02-05)
│   ├── 04_uat_comprehensive_test_2026-02-06.md        # UAT 종합 테스트 시나리오 (02-06)
│   ├── 05_uat_partA_execution_results_2026-02-06.md   # UAT Part A 실행 결과 (02-06)
│   ├── 06_uat_partB_execution_results_2026-02-06.md   # UAT Part B 실행 결과 (02-06)
│   ├── 07_uat_partA_execution_results_2026-02-07.md   # UAT Part A 실행 결과 (02-07)
│   ├── 08_uat_partB_execution_results_2026-02-07.md   # UAT Part B 실행 결과 (02-07)
│   └── 09_uat_manual_test_timeline_2026-02-07.md      # UAT 수동 테스트 타임라인 (02-07)
│
├── 10_smoke_test/                                     # 검색 품질 스모크 테스트 *from results/smoke_test/*
│   ├── smoke_test_search_2026-02-10.json              # 스모크 테스트 원본 (JSON)
│   └── smoke_test_search_report_2026-02-10.md         # 스모크 테스트 리포트 (Graph ON/OFF 비교)
│
├── 11_ragas/                                          # RAGAS/RAG 품질 평가
│   ├── 01_rag_test_dataset_plan.md                    # RAG 테스트 데이터셋 계획서
│   ├── 02_ragas_evaluation_criteria.md                # RAGAS 평가 기준/메트릭
│   ├── 03_graph_rag_effectiveness_analysis.md         # Graph RAG 효과성 분석
│   ├── 04_ragas_cross_system_evaluation_guide.md      # RAGAS 크로스 시스템 평가 가이드
│   └── results/                                       # RAGAS 평가 실행 결과 *from results/ragas/*
│       ├── 01_ragas_evaluation_2026-02-04_022522.json  # 초기 평가 원본 (JSON)
│       ├── 01_ragas_evaluation_2026-02-04_022522.md   # 초기 평가 리포트
│       ├── 02_hrkp_vs_rcsv_2026-02-10.json            # v1 비교 결과 (JSON)
│       ├── 02_hrkp_vs_rcsv_report_2026-02-10.md       # v1 비교 리포트
│       ├── 03_hrkp_vs_rcsv_2026-02-10_v2.json         # v2 비교 결과 (JSON)
│       ├── 03_hrkp_vs_rcsv_report_2026-02-10_v2.md    # v2 비교 리포트
│       ├── 04_hrkp_vs_rcsv_2026-02-10_v3.json         # v3 비교 결과 (JSON)
│       ├── 04_hrkp_vs_rcsv_report_2026-02-10_v3.md    # v3 비교 리포트
│       ├── 05_hrkp_vs_rcsv_2026-02-10_v4.json         # v4 비교 결과 (JSON, 50쿼리)
│       ├── 05_hrkp_vs_rcsv_report_2026-02-10_v4.md    # v4 비교 리포트 (50쿼리)
│       ├── 06_ragas_cross_system_2026-02-10.json       # 크로스시스템 원본 (JSON)
│       ├── 06_ragas_cross_system_report_2026-02-10.md  # 크로스시스템 리포트
│       ├── 07_RAGAS_평가_총평.md                      # 7회 평가 이력 종합 분석
│       ├── 08_RAGAS_v5_50쿼리_평가결과.md             # v5 50쿼리 평가 결과 분석 (STORY-111)
│       ├── 09_RAGAS_크로스시스템_최종분석.md           # 크로스시스템 최종 분석
│       ├── 10_hrkp_ragas_v6_2026-02-11.json           # v6 평가 결과 (JSON, 50쿼리)
│       └── 10_hrkp_ragas_v6_report_2026-02-11.md      # v6 평가 리포트
│
├── 12_embedding_evaluation/                           # 임베딩 평가
│   ├── 01_etl_3phase_embedding_report.md              # ETL 3-Phase 임베딩 보고서
│   ├── 02_bge_m3_and_107k_embeddings.md               # BGE-M3 107K 임베딩 평가
│   ├── 03_ragas_v7_live_evaluation.md                 # RAGAS v7 라이브 평가
│   └── 04_ragas_v7_comprehensive_evaluation.md        # RAGAS v7 종합 평가
│
├── 13_etl_v2_reprocessing/                            # ETL v2 재처리
│   ├── 00_work_plan.md                                # 작업 계획
│   ├── 01_speed_optimization_report.md                # 속도 최적화 보고서
│   ├── 02_data_quality_report.md                      # 데이터 품질 보고서
│   ├── 03_gcloud_gpu_embedding_guide.md               # GCloud GPU 임베딩 가이드
│   ├── 04_ragas_v9_4way_rrf_evaluation.md             # RAGAS v9 4-Way RRF 평가
│   └── 05_ragas_v10_post_entity_evaluation.md         # RAGAS v10 엔티티 후처리 평가
│
└── 14_issues/                                         # 테스트 이슈 트래킹
    ├── 01_ISSUE-010_graph_search_zero_results.md      # Graph 검색 0건 이슈
    └── 02_ISSUE-011_entity_name_filename_bug.md       # Entity 이름 파일명 버그
```

---

## 문서 카테고리 요약

| 카테고리 | 폴더 | 문서 수 | 설명 |
|----------|------|---------|------|
| 기반 계획서 | `/` (루트) | 1 | 단위/통합 테스트 계획서 |
| Story 계획서 | `01_test_plans/` | 9 | Story 단위 테스트 계획서 |
| 테스트 케이스 | `02_test_cases/` | 1 | 상세 테스트 케이스 |
| 기술 평가 | `03_technical_assessment/` | 1 | 기술 평가/전략 문서 |
| 인프라 E2E | `04_infrastructure_e2e/` | 6 | 인프라 레벨 E2E 테스트 |
| E2E 테스트 | `05_e2e/` | 18 | Sprint별 E2E 계획서, 결과, 가이드 |
| Staging | `06_staging/` | 2 | Staging 환경 검증 |
| 테스트 결과 | `07_test_results/` | 8 | 테스트 실행 결과 |
| 분석/보고서 | `08_analysis/` | 13 | 감사, 분석, 성능 보고서 |
| UAT | `09_user_acceptance_tests/` | 10 | 사용자 인수 테스트 |
| 스모크 테스트 | `10_smoke_test/` | 2 | 검색 품질 스모크 테스트 |
| RAGAS 평가 (가이드) | `11_ragas/` | 4 | RAG 품질 평가 기준/가이드 |
| RAGAS 결과 | `11_ragas/results/` | 17 | RAGAS 평가 실행 결과 (JSON + MD) |
| 임베딩 평가 | `12_embedding_evaluation/` | 4 | 임베딩 품질 평가 |
| ETL v2 재처리 | `13_etl_v2_reprocessing/` | 6 | ETL v2 재처리 평가 |
| 이슈 | `14_issues/` | 2 | 테스트 중 발견된 이슈 |
| **합계** | | **104** | |

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

- [RAG 성능 테스트 설계서](../02_design/12_rag_performance_test_design.md) - 추론/응답 품질 평가 기준
- [백엔드 설계서](../02_design/06_backend_detailed_design.md) - 테스트 구조 참조
- [API 통합 설계서](../02_design/04_api_integration_design.md) - API 스펙 참조
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

---

## 2026-02-11 파일 이동 이력 (from results/)

`knowledge_service/docs/results/` 에서 테스트/평가 관련 파일을 이 디렉토리로 이동했습니다.

### 이동된 파일 목록

| 원본 경로 (results/) | 이동 경로 (04_testing/) | 분류 |
|----------------------|------------------------|------|
| `ragas/` (15개 파일 전체) | `11_ragas/results/` | RAGAS 평가 결과 |
| `smoke_test/` (2개 파일 전체) | `10_smoke_test/` | 검색 품질 스모크 테스트 |
| `docker_mode_test_report_2026-02-05.md` | `07_test_results/03_docker_mode_test_report_2026-02-05.md` | Unit 테스트 결과 |
| `unit_test_coverage_improvement_report.md` | `07_test_results/04_unit_test_coverage_improvement_report.md` | 커버리지 개선 보고서 |
| `embedding_pipeline_verification_report_2026-02-05.md` | `07_test_results/05_embedding_pipeline_verification_report_2026-02-05.md` | 파이프라인 검증 보고서 |
| `story-002_retest_report.md` | `07_test_results/06_story-002_retest_report.md` | 재테스트 결과 |
| `sprint04_document_parser_retry_report.md` | `07_test_results/07_sprint04_document_parser_retry_report.md` | QA 검증 보고서 |
| `sprint04_day1_e2e_test_results.md` | `05_e2e/18_sprint04_day1_e2e_test_results.md` | E2E 테스트 결과 |

### results/ 정리 완료 (2026-02-11 2차 이동)

`results/` 디렉토리의 나머지 파일도 모두 적절한 위치로 이동 완료하여, `results/` 폴더가 삭제되었습니다.

| 원본 경로 (results/) | 이동 경로 | 분류 |
|----------------------|----------|------|
| `sprint03_day1_code_review.md` | `02_design/review/2026-01-27_sprint03_day1_code_review.md` | 코드 리뷰 |
| `sprint03_day2_code_review.md` | `02_design/review/2026-01-28_sprint03_day2_code_review.md` | 아키텍처 리뷰 |
| `sprint03_day2_wave2_tech_review.md` | `02_design/review/2026-01-28_sprint03_day2_wave2_tech_review.md` | 기술 리뷰 |
| `sprint03_wave3_pre_review.md` | `02_design/review/2026-01-28_sprint03_wave3_pre_review.md` | 사전 구현 리뷰 |
| `story-001_code_review.md` | `02_design/review/2026-01-27_story-001_code_review.md` | 코드 리뷰 |
| `camelcase_snake_case_audit_report.md` | `02_design/review/2026-02-08_camelcase_snake_case_audit_report.md` | 코드 감사 |
| `sprint06_phase4_completion_report.md` | `04_testing/08_analysis/12_sprint06_phase4_completion_report.md` | 스프린트 완료 보고서 |
| `perf_benchmark_2026-02-06.md` | `04_testing/08_analysis/13_perf_benchmark_2026-02-06.md` | 성능 벤치마크 |
| `performance/` (빈 폴더) | 삭제됨 | - |
| `staging_validation/` (빈 폴더) | 삭제됨 | - |

### 참조 링크 업데이트 필요

이동된 파일을 참조하는 외부 문서들입니다. 해당 문서의 경로를 업데이트해야 합니다.

| 참조하는 문서 | 영향받는 경로 |
|--------------|-------------|
| `knowledge_service/docs/07_maintenance/20_rag_quality_improvement_manual.md` | `docs/results/ragas/` -> `docs/04_testing/11_ragas/results/` |
| `knowledge_service/docs/04_testing/11_ragas/02_ragas_evaluation_criteria.md` | `docs/results/ragas/` -> `docs/04_testing/11_ragas/results/` |
| `knowledge_service/docs/04_testing/11_ragas/04_ragas_cross_system_evaluation_guide.md` | `docs/results/ragas/` -> `docs/04_testing/11_ragas/results/` |
| `knowledge_service/docs/05_development/08_ragas_evaluation_guide.md` | `docs/results/ragas` -> `docs/04_testing/11_ragas/results` |
| `knowledge_service/docs/05_e2e/04_sprint04_frontend_backend_e2e_test_plan.md` | `docs/results/sprint04_day1_e2e_test_results.md` -> `docs/04_testing/05_e2e/18_sprint04_day1_e2e_test_results.md` |
| `work_logs/` (세션 로그, 일일 로그) | 과거 기록이므로 업데이트 불필요 (이력 보존) |
