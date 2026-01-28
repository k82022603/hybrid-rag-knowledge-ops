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

---

## 관련 문서

- [RAG 성능 테스트 설계서](../02_design/rag_performance_test_design.md) - 추론/응답 품질 평가 기준
- [백엔드 설계서](../02_design/backend_detailed_design.md) - 테스트 구조 참조
- [API 통합 설계서](../02_design/api_integration_design.md) - API 스펙 참조
- [Sprint 04 계획](../../../backlog/sprints/sprint-04.md) - 스프린트 범위 및 일정

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
