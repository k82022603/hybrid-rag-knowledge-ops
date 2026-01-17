# 04_testing - 테스트 문서

Hybrid RAG Knowledge Operations Platform의 테스트 관련 문서 모음입니다.

---

## 폴더 구조

```
04_testing/
├── README.md                           # 본 문서
├── unit_integration_test_plan.md       # 단위/통합 테스트 계획서
└── test_cases/                         # 테스트 케이스 (예정)
    ├── backend/                        # Backend 테스트 케이스
    ├── ai_service/                     # AI Service 테스트 케이스
    └── frontend/                       # Frontend 테스트 케이스
```

---

## 문서 목록

| 문서 | 설명 | 버전 | 최종 수정 |
|------|------|------|----------|
| [unit_integration_test_plan.md](./unit_integration_test_plan.md) | 단위/통합 테스트 계획서 | 1.0 | 2026-01-17 |

---

## 테스트 주체 요약

| 테스트 유형 | 주체 | 책임 |
|------------|------|------|
| **단위 테스트** | 개발팀 | 작성 및 실행 |
| **통합 테스트** | 개발팀 + QA팀 | 개발팀 작성, QA팀 검증 |
| **E2E 테스트** | QA팀 | 작성 및 실행 |
| **성능 테스트** | 개발팀 + QA팀 | 공동 수행 |

---

## 관련 문서

- [RAG 성능 테스트 설계서](../02_design/rag_performance_test_design.md) - 추론/응답 품질 평가 기준
- [백엔드 설계서](../02_design/backend_detailed_design.md) - 테스트 구조 참조
- [API 통합 설계서](../02_design/api_integration_design.md) - API 스펙 참조

---

## 테스트 도구

| 영역 | 도구 |
|------|------|
| Backend | JUnit 5, Mockito, Testcontainers |
| AI Service | pytest, httpx, testcontainers-python |
| Frontend | Vitest, React Testing Library, MSW |
| CI/CD | GitHub Actions |
| 커버리지 | SonarQube, Codecov |
