# 05_development - 개발 가이드 문서

Hybrid RAG Knowledge Operations Platform의 개발 관련 가이드 문서 모음입니다.

---

## 폴더 구조

```
05_development/
├── README.md                                  # 본 문서
├── 01_developer_agent_guide.md                # 개발자 에이전트 도구 가이드
├── 02_developer_integration_guide.md          # 개발자 통합 가이드
├── 03_development_conventions.md              # 개발 컨벤션
├── 04_development_environment_setup.md        # 개발 환경 설정 가이드
├── 05_quick_start_guide.md                    # 빠른 시작 가이드
├── 06_mui_to_tailwind_migration.md            # MUI → Tailwind 마이그레이션 가이드
├── 07_playwright_setup_guide.md               # Playwright E2E 테스트 설정 가이드
├── 08_ragas_evaluation_guide.md               # RAGAS RAG 평가 가이드
├── 09_issue_report_bge_m3_cache_volume.md     # BGE-M3 캐시 볼륨 이슈 리포트
├── 10_retriever_benchmark_manual.md           # Retriever 벤치마크 매뉴얼
└── 11_initial_data_loader_dedup_review.md     # 초기 데이터 로더 중복 검토
```

---

## 문서 목록

| 문서 | 설명 | 대상 | 버전 |
|------|------|------|------|
| [01_developer_agent_guide.md](./01_developer_agent_guide.md) | Claude Code 개발자 에이전트 도구 가이드 | AI 에이전트 | 1.0 |
| [02_developer_integration_guide.md](./02_developer_integration_guide.md) | Jira, Slack, GitHub 연동 가이드 | 개발자 | 1.0 |
| [03_development_conventions.md](./03_development_conventions.md) | 코드 스타일, 커밋 규칙, PR 가이드 | 개발자 | 1.0 |
| [04_development_environment_setup.md](./04_development_environment_setup.md) | 로컬 개발 환경 설정, Docker Compose 실행 | 개발자 | 1.0 |
| [05_quick_start_guide.md](./05_quick_start_guide.md) | 5분 만에 개발 환경 구축 | 개발자 | 1.0 |
| [Agent Teams 활용 가이드](../../../../docs/12_Agent_Teams_활용_가이드.md) | Agent Teams 멀티-에이전트 협업 가이드 (→ docs/ 이동) | AI 에이전트 운영자 | 1.0 |
| [06_mui_to_tailwind_migration.md](./06_mui_to_tailwind_migration.md) | MUI → Tailwind CSS 마이그레이션 가이드 | Frontend 개발자 | 1.0 |
| [07_playwright_setup_guide.md](./07_playwright_setup_guide.md) | Playwright E2E 테스트 환경 설정 | QA, Frontend 개발자 | 1.0 |
| [08_ragas_evaluation_guide.md](./08_ragas_evaluation_guide.md) | RAGAS 기반 RAG 품질 평가 가이드 | RAG 엔지니어, QA | 1.0 |
| [09_issue_report_bge_m3_cache_volume.md](./09_issue_report_bge_m3_cache_volume.md) | BGE-M3 캐시 볼륨 이슈 리포트 | Infra, RAG 엔지니어 | 1.0 |
| [10_retriever_benchmark_manual.md](./10_retriever_benchmark_manual.md) | Retriever 벤치마크 매뉴얼 | RAG 엔지니어, QA | 1.0 |
| [11_initial_data_loader_dedup_review.md](./11_initial_data_loader_dedup_review.md) | 초기 데이터 로더 중복 검토 | ETL, Backend | 1.0 |

---

## 문서 목적

### 개발 환경 설정 가이드 (NEW)
- **목적**: 로컬 개발 환경 구축 및 Docker Compose 실행 안내
- **대상**: 신규 개발자, 환경 설정이 필요한 개발자
- **내용**: 시스템 요구사항, 도구 설치, 서비스별 실행 방법

### 빠른 시작 가이드 (NEW)
- **목적**: 5분 만에 개발 환경 구축
- **대상**: 빠르게 시작하려는 개발자
- **내용**: 필수 체크리스트, 단계별 실행 명령어, FAQ

### 개발 컨벤션 (NEW)
- **목적**: 일관된 코드 스타일 및 개발 프로세스 유지
- **대상**: 모든 개발자
- **내용**: 코드 스타일, 커밋 규칙, 브랜치 전략, PR 가이드

### 개발자 에이전트 가이드
- **목적**: Claude Code 기반 개발자 에이전트 도구 사용법 안내
- **대상**: Claude Code, AI 개발자 에이전트
- **내용**: 상황별 도구 선택, Subagent 활용법, 명령어 레퍼런스

### 개발자 통합 가이드
- **목적**: 개발 도구 연동 및 워크플로우 안내
- **대상**: 개발자
- **내용**: GitHub 브랜치 전략, Jira/Slack 연동, Claude Code 활용

### Agent Teams 활용 가이드 (→ docs/12 이동)
- **목적**: Agent Teams 멀티-에이전트 협업 기능 이해 및 적용
- **위치**: [`docs/12_Agent_Teams_활용_가이드.md`](../../../../docs/12_Agent_Teams_활용_가이드.md)

### MUI → Tailwind 마이그레이션 가이드
- **목적**: Material UI에서 Tailwind CSS로의 마이그레이션 안내
- **대상**: Frontend 개발자
- **내용**: 컴포넌트 매핑, 스타일 변환, Headless UI 활용

### Playwright 설정 가이드
- **목적**: Playwright E2E 테스트 환경 구축
- **대상**: QA, Frontend 개발자
- **내용**: 설치, 설정, 테스트 작성, CI 연동

### RAGAS 평가 가이드
- **목적**: RAGAS 프레임워크 기반 RAG 품질 평가
- **대상**: RAG 엔지니어, QA
- **내용**: 평가 지표, 데이터셋 준비, 평가 실행, 결과 분석

---

## 관련 문서

- [CLAUDE.md](../../../CLAUDE.md) - 프로젝트 개발 규칙
- [.claude/commands/README.md](../../../.claude/commands/README.md) - 설치된 명령어 전체 목록
- [단위/통합 테스트 계획서](../04_testing/01_unit_integration_test_plan.md) - 테스트 접근 방식 가이드

---

## 버전 정보

| 문서 | 버전 | 생성일 |
|------|------|--------|
| 01_developer_agent_guide | 1.0 | 2026-01-17 |
| 02_developer_integration_guide | 1.0 | 2026-01-18 |
| 03_development_conventions | 1.0 | 2026-01-20 |
| 04_development_environment_setup | 1.0 | 2026-01-20 |
| 05_quick_start_guide | 1.0 | 2026-01-20 |
| agent_teams_guide (→ docs/12) | 1.0 | 2026-02-06 |
| 06_mui_to_tailwind_migration | 1.0 | 2026-01-25 |
| 07_playwright_setup_guide | 1.0 | 2026-01-26 |
| 08_ragas_evaluation_guide | 1.0 | 2026-02-04 |
| 09_issue_report_bge_m3_cache_volume | 1.0 | 2026-02-06 |
| 10_retriever_benchmark_manual | 1.0 | 2026-02-06 |
| 11_initial_data_loader_dedup_review | 1.0 | 2026-02-08 |
