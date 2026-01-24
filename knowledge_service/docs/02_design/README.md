# 02_design - 기술 설계 문서

Hybrid RAG Knowledge Operations Platform의 상세 설계 문서 모음입니다.

---

## 📁 폴더 구조

```
02_design/
├── README.md                                    # 본 문서
├── hybrid_rag_platform_detailed_design.md       # 핵심 플랫폼 설계 (137KB)
├── api_integration_design.md                    # API 통합 설계
├── rag_search_api_specification.md              # RAG Search API 상세 스펙
├── backend_detailed_design.md                   # SpringBoot 백엔드 설계
├── frontend_detailed_design.md                  # React 프론트엔드 설계
├── infrastructure_detailed_design.md            # Docker Compose 인프라 설계
├── integrated_detailed_design.md                # 통합 설계서
├── authentication_authorization_detailed_design.md  # 인증/권한 관리
├── data_encryption_design.md                    # 데이터 암호화 설계
├── devops_detailed_design.md                    # DevOps 파이프라인
├── observability_detailed_design.md             # Observability (모니터링/트레이싱/로깅)
├── error_code_standards.md                      # 에러 코드 표준
├── rag_performance_test_design.md               # RAG 성능 테스트
├── ui_design_system_guide.md                    # UI 디자인 시스템
├── glossary.md                                  # 용어사전
├── diagrams/                                    # 다이어그램 (예정)
├── review/                                      # 설계 리뷰 기록
├── technical_assessment/                        # 기술 검토 문서
└── ui_storyboard/                               # UI 스토리보드
```

---

## 📚 핵심 설계 문서

### 플랫폼 아키텍처

| 문서 | 설명 |
|------|------|
| [hybrid_rag_platform_detailed_design.md](./hybrid_rag_platform_detailed_design.md) | **핵심 설계서** - Neo4j Graph RAG, Gleaning, LangGraph 워크플로우 포함 |
| [integrated_detailed_design.md](./integrated_detailed_design.md) | 전체 시스템 통합 관점의 설계서 |
| [glossary.md](./glossary.md) | 프로젝트 용어 정의 |

### 계층별 설계

| 문서 | 설명 |
|------|------|
| [api_integration_design.md](./api_integration_design.md) | External API (Frontend↔Backend) + Internal API (Backend↔AI) |
| [rag_search_api_specification.md](./rag_search_api_specification.md) | **RAG Search API 상세 스펙** - Search/Embed/Extract/Health API |
| [backend_detailed_design.md](./backend_detailed_design.md) | SpringBoot 3.x 기반 백엔드 아키텍처 |
| [frontend_detailed_design.md](./frontend_detailed_design.md) | React 18 기반 프론트엔드 설계 |
| [infrastructure_detailed_design.md](./infrastructure_detailed_design.md) | Docker Compose 기반 인프라 구성 |

### 보안 설계

| 문서 | 설명 |
|------|------|
| [authentication_authorization_detailed_design.md](./authentication_authorization_detailed_design.md) | JWT, RBAC, OAuth 2.0 인증/권한 |
| [data_encryption_design.md](./data_encryption_design.md) | AES-256, TLS 1.3 암호화 전략 |

### 운영 및 품질

| 문서 | 설명 |
|------|------|
| [devops_detailed_design.md](./devops_detailed_design.md) | CI/CD, 배포 전략 |
| [observability_detailed_design.md](./observability_detailed_design.md) | **Observability 통합** - 메트릭/로깅/트레이싱, SLA, 보안 모니터링 |
| [error_code_standards.md](./error_code_standards.md) | 에러 코드 체계 및 공통 코드 |
| [rag_performance_test_design.md](./rag_performance_test_design.md) | RAG 파이프라인 성능 테스트 계획 |

### UI/UX 설계

| 문서 | 설명 |
|------|------|
| [ui_design_system_guide.md](./ui_design_system_guide.md) | 색상, 타이포그래피, 컴포넌트 가이드 |
| [ui_storyboard/](./ui_storyboard/) | 화면별 스토리보드 (로그인, 검색, 관리자 등) |

---

## 📂 하위 폴더

### review/
설계 리뷰 및 검토 기록
- `REVIEW_SUMMARY.md` - 리뷰 요약
- `2026-01-16_design_2nd_review.md` - 2차 설계 리뷰
- 각 설계서별 개별 리뷰 문서

### technical_assessment/
기술 검토 및 평가 문서
- `gleaning_knowledge_graph_quality_assessment.md` - Gleaning 기법 평가
- `infrastructure_k8s_reference_design.md` - K8s 참조 설계 (백업)
- API 아키텍처 및 TLS 인증서 검토

### ui_storyboard/
UI 스토리보드 및 프레젠테이션
- 화면별 상세 스토리보드 (로그인, 검색, 지식관리, 관리자)
- PowerPoint 프레젠테이션

---

## 🔗 관련 문서

- [../01_planning/](../01_planning/) - 구현 계획 문서
- [../results/](../results/) - 실행 결과
- [PLAN.md](../../../PLAN.md) - 프로젝트 전체 계획
- [CLAUDE.md](../../../CLAUDE.md) - 개발 가이드라인

---

## 📝 문서 버전

| 문서 | 버전 | 최종 수정 |
|------|------|----------|
| hybrid_rag_platform_detailed_design | 2.4 | 2026-01-17 |
| infrastructure_detailed_design | 2.0 | 2026-01-16 |
| api_integration_design | 1.4 | 2026-01-22 |
| rag_search_api_specification | 1.0 | 2026-01-24 |
| authentication_authorization_detailed_design | 1.1 | 2026-01-17 |
| observability_detailed_design | 1.0 | 2026-01-17 |
| integrated_detailed_design | 1.1 | 2026-01-17 |
| backend_detailed_design | 1.2 | 2026-01-17 |
| frontend_detailed_design | 1.2 | 2026-01-17 |
| ui_design_system_guide | 1.1 | 2026-01-17 |
| error_code_standards | 1.1 | 2026-01-17 |
| 기타 문서 | 1.0 | 2026-01-15~16 |
