# 02_design - 기술 설계 문서

Hybrid RAG Knowledge Operations Platform의 상세 설계 문서 모음입니다.

---

## 폴더 구조

```
02_design/
├── README.md                                              # 본 문서
├── 01_hybrid_rag_platform_detailed_design.md              # 핵심 플랫폼 설계 (138KB)
├── 02_frontend_detailed_design.md                         # React 프론트엔드 설계
├── 03_authentication_authorization_detailed_design.md     # 인증/권한 관리
├── 04_api_integration_design.md                           # API 통합 설계
├── 05_data_encryption_design.md                           # 데이터 암호화 설계
├── 06_backend_detailed_design.md                          # SpringBoot 백엔드 설계
├── 07_devops_detailed_design.md                           # DevOps 파이프라인
├── 08_error_code_standards.md                             # 에러 코드 표준
├── 09_glossary.md                                         # 용어사전
├── 10_infrastructure_detailed_design.md                   # Docker Compose 인프라 설계
├── 11_integrated_detailed_design.md                       # 통합 설계서
├── 12_rag_performance_test_design.md                      # RAG 성능 테스트
├── 13_ui_design_system_guide.md                           # UI 디자인 시스템
├── 14_observability_detailed_design.md                    # Observability (모니터링/트레이싱/로깅)
├── 15_rag_search_api_specification.md                     # RAG Search API 상세 스펙
├── 16_embedding_batch_detailed_design.md                  # 임베딩 배치 처리 상세 설계
├── Hybrid_RAG_Platform_Presentation.pptx                  # 플랫폼 프레젠테이션
├── adr/                                                   # Architecture Decision Records
├── components/                                            # UI 컴포넌트 스펙
├── review/                                                # 설계 리뷰 기록
├── technical_assessment/                                  # 기술 검토 문서
└── ui_storyboard/                                         # UI 스토리보드
```

> 번호는 git 최초 생성일 기준으로 부여 (01=가장 오래된 문서)

---

## 핵심 설계 문서

### 플랫폼 아키텍처

| # | 문서 | 설명 | 생성일 |
|---|------|------|--------|
| 01 | [hybrid_rag_platform_detailed_design](./01_hybrid_rag_platform_detailed_design.md) | **핵심 설계서** - Neo4j Graph RAG, Gleaning, LangGraph 워크플로우 | 2026-01-13 |
| 11 | [integrated_detailed_design](./11_integrated_detailed_design.md) | 전체 시스템 통합 관점의 설계서 | 2026-01-16 |
| 09 | [glossary](./09_glossary.md) | 프로젝트 용어 정의 (Gleaning 용어 포함) | 2026-01-16 |

### 계층별 설계

| # | 문서 | 설명 | 생성일 |
|---|------|------|--------|
| 04 | [api_integration_design](./04_api_integration_design.md) | External API (Frontend-Backend) + Internal API (Backend-AI) | 2026-01-16 |
| 06 | [backend_detailed_design](./06_backend_detailed_design.md) | SpringBoot 3.x 기반 백엔드 아키텍처 | 2026-01-16 |
| 02 | [frontend_detailed_design](./02_frontend_detailed_design.md) | React 18 기반 프론트엔드 설계 | 2026-01-15 |
| 10 | [infrastructure_detailed_design](./10_infrastructure_detailed_design.md) | Docker Compose 기반 인프라 구성 (18개 컨테이너) | 2026-01-16 |
| 15 | [rag_search_api_specification](./15_rag_search_api_specification.md) | RAG Search API 상세 스펙 - Search/Embed/Extract/Health | 2026-01-25 |
| 16 | [embedding_batch_detailed_design](./16_embedding_batch_detailed_design.md) | 임베딩 배치 처리 상세 설계 (Mermaid 7개) | 2026-02-09 |

### 보안 설계

| # | 문서 | 설명 | 생성일 |
|---|------|------|--------|
| 03 | [authentication_authorization_detailed_design](./03_authentication_authorization_detailed_design.md) | JWT, RBAC, OAuth 2.0 인증/권한 | 2026-01-15 |
| 05 | [data_encryption_design](./05_data_encryption_design.md) | AES-256, TLS 1.3 암호화 전략 | 2026-01-16 |

### 운영 및 품질

| # | 문서 | 설명 | 생성일 |
|---|------|------|--------|
| 07 | [devops_detailed_design](./07_devops_detailed_design.md) | CI/CD, 배포 전략 | 2026-01-16 |
| 08 | [error_code_standards](./08_error_code_standards.md) | 에러 코드 체계 및 공통 코드 | 2026-01-16 |
| 12 | [rag_performance_test_design](./12_rag_performance_test_design.md) | RAG 파이프라인 성능 테스트 계획 | 2026-01-16 |
| 14 | [observability_detailed_design](./14_observability_detailed_design.md) | Observability 통합 - 메트릭/로깅/트레이싱, SLA, 보안 모니터링 | 2026-01-17 |

### UI/UX 설계

| # | 문서 | 설명 | 생성일 |
|---|------|------|--------|
| 13 | [ui_design_system_guide](./13_ui_design_system_guide.md) | 색상, 타이포그래피, 컴포넌트 가이드 | 2026-01-16 |
| - | [ui_storyboard/](./ui_storyboard/) | 화면별 스토리보드 (로그인, 검색, 관리자 등) | 2026-01-15 |
| - | [components/](./components/) | UI 컴포넌트 스펙 (SearchResultCard 등) | 2026-01-25 |

---

## 하위 폴더

### adr/
Architecture Decision Records (기술 결정 기록)
- `ADR-001-serialization-strategy.md` - 직렬화 전략
- `ADR-002-search-api-authentication.md` - 검색 API 인증
- `ADR-003-auth-endpoint-security.md` - Auth 엔드포인트 보안

### review/
설계 리뷰 및 검토 기록 (날짜 기반 네이밍)
- `REVIEW_SUMMARY.md` - 리뷰 전체 요약
- `2026-01-13_*` ~ `2026-02-08_*` - 날짜별 리뷰 문서
- `2026-01-22/` - 01-22 전체 팀 리뷰 (8개 역할별 리뷰 + 회의록)
- `2026-01-28_sprint04_*` - Sprint 04 기술 리뷰/이슈 보고서
- 개별 설계서 리뷰 (`*_review.md`)

### technical_assessment/
기술 검토 및 평가 문서 (번호순)

| # | 문서 | 생성일 |
|---|------|--------|
| 01 | API_architecture_design_review | 2026-01-16 |
| 02 | TLS_certificate_implementation_review | 2026-01-16 |
| 03 | gleaning_knowledge_graph_quality_assessment | 2026-01-16 |
| 04 | infrastructure_k8s_reference_design | 2026-01-16 |
| 05 | neo4j_subgraph_query_optimization | 2026-02-08 |

### ui_storyboard/
UI 스토리보드 및 프레젠테이션
- 화면별 상세 스토리보드 (로그인, 검색, 지식관리, 관리자)
- PowerPoint 프레젠테이션

### components/
UI 컴포넌트 상세 스펙
- `search_result_card.md` - 검색 결과 카드 컴포넌트

---

## 관련 문서

- [../01_planning/](../01_planning/) - 구현 계획 문서
- [../03_implementation/](../03_implementation/) - 구현 문서
- [../04_testing/](../04_testing/) - 테스트 문서
- [PLAN.md](../../../PLAN.md) - 프로젝트 전체 계획
- [CLAUDE.md](../../../CLAUDE.md) - 개발 가이드라인

---

## 문서 버전

| 문서 | 버전 | 최종 수정 |
|------|------|----------|
| 01_hybrid_rag_platform_detailed_design | 2.4 | 2026-01-17 |
| 02_frontend_detailed_design | 1.2 | 2026-01-25 |
| 03_authentication_authorization_detailed_design | 1.1 | 2026-01-17 |
| 04_api_integration_design | 1.4 | 2026-01-22 |
| 05_data_encryption_design | 1.0 | 2026-01-18 |
| 06_backend_detailed_design | 1.2 | 2026-01-22 |
| 07_devops_detailed_design | 1.0 | 2026-01-16 |
| 08_error_code_standards | 1.1 | 2026-01-22 |
| 09_glossary | 2.1 | 2026-01-25 |
| 10_infrastructure_detailed_design | 2.0 | 2026-02-11 |
| 11_integrated_detailed_design | 1.1 | 2026-02-11 |
| 12_rag_performance_test_design | 1.0 | 2026-01-16 |
| 13_ui_design_system_guide | 1.1 | 2026-01-25 |
| 14_observability_detailed_design | 1.0 | 2026-02-11 |
| 15_rag_search_api_specification | 1.0 | 2026-01-24 |
| 16_embedding_batch_detailed_design | 1.0 | 2026-02-09 |

---

## 변경 이력

| 날짜 | 변경 내용 |
|------|----------|
| 2026-02-11 | 디렉토리 정리: 파일 번호 매기기 (git 생성일순), sprint04 리뷰 파일을 review/로 이동, 빈 diagrams/ 삭제, technical_assessment 번호 통일 |
| 2026-01-24 | README 초기 작성 |
