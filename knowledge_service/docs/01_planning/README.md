# 01_planning - 기획 문서

Hybrid RAG Knowledge Platform 프로젝트의 기획 단계 문서를 관리합니다.

## 문서 목록

| # | 문서 | 설명 | 생성일 |
|---|------|------|--------|
| 01 | [01_hybrid_rag_knowledge_platform_plan.md](./01_hybrid_rag_knowledge_platform_plan.md) | Neo4j Graph RAG 기반 Hybrid 지식 플랫폼 구축 계획서 | 2026-01-12 |
| 02 | [02_frontend_implementation_plan.md](./02_frontend_implementation_plan.md) | React 기반 프론트엔드 구축계획서 | 2026-01-12 |
| 03 | [03_requirements_specification.md](./03_requirements_specification.md) | 요구사항 명세서 (SRS) | 2026-01-14 |
| 04 | [04_backend_implementation_plan.md](./04_backend_implementation_plan.md) | SpringBoot/SpringCloud 백엔드 구축계획서 | 2026-01-14 |
| 05 | [05_ai_service_implementation_plan.md](./05_ai_service_implementation_plan.md) | Python FastAPI + LangGraph 기반 AI Service 구현 계획서 v2.0 | 2026-01-14 |
| 06 | [06_dev_environment_plan.md](./06_dev_environment_plan.md) | 개발 환경 구축 계획서 | 2026-01-14 |
| 07 | [07_devops_alm_plan.md](./07_devops_alm_plan.md) | DevOps & ALM 통합 계획서 | 2026-01-14 |
| 08 | [08_test_plan.md](./08_test_plan.md) | 테스트 계획서 | 2026-01-14 |

## 하위 디렉토리

### review/

기획 문서 리뷰 결과를 보관합니다.

| # | 문서 | 설명 | 생성일 |
|---|------|------|--------|
| 01 | [01_2026-01-14_planning_review_report.md](./review/01_2026-01-14_planning_review_report.md) | 기획 문서 리뷰 결과 보고서 | 2026-01-14 |

### technical_assessment/

기술 검토 보고서를 보관합니다. 프로젝트 초기 기술 스택 선정 및 아키텍처 결정을 위한 기술 분석 문서입니다.

| # | 문서 | 설명 | 생성일 |
|---|------|------|--------|
| 01 | [01_metadata_driven_rag_tech_review.md](./technical_assessment/01_metadata_driven_rag_tech_review.md) | 메타데이터 지능형 RAG 시스템 기술 검토 | 2026-01-13 |
| 02 | [02_document_parsing_embedding_comparison.md](./technical_assessment/02_document_parsing_embedding_comparison.md) | 문서 파싱 및 임베딩 기술 비교 분석 | 2026-01-13 |
| 03 | [03_elasticsearch_license_verification.md](./technical_assessment/03_elasticsearch_license_verification.md) | Elasticsearch 라이선스 정책 검증 | 2026-01-13 |
| 04 | [04_hybrid_rag_architecture_free_license.md](./technical_assessment/04_hybrid_rag_architecture_free_license.md) | ES Basic 라이선스 기반 하이브리드 RAG 아키텍처 | 2026-01-13 |
| 05 | [05_enterprise_knowledge_search_technical_design.md](./technical_assessment/05_enterprise_knowledge_search_technical_design.md) | 사내 지식 검색 시스템 기술 설계서 | 2026-01-13 |
| 06 | [06_source_code_review_metadata_analysis.md](./technical_assessment/06_source_code_review_metadata_analysis.md) | 소스코드 검토: 메타데이터 자동 생성 분석 | 2026-01-13 |
| 07 | [07_graphrag_neo4j_integration_guide.md](./technical_assessment/07_graphrag_neo4j_integration_guide.md) | GraphRAG + Neo4j 통합 Hybrid RAG 설계 가이드 | 2026-01-13 |
| 08 | [08_deep_agents_hybrid_orchestration_strategy.md](./technical_assessment/08_deep_agents_hybrid_orchestration_strategy.md) | Deep Agents 기반 하이브리드 오케스트레이션 전략 | 2026-01-14 |
| 08-1 | [08-1_deep_agents_phase2_3_impact_analysis.md](./technical_assessment/08-1_deep_agents_phase2_3_impact_analysis.md) | Deep Agents Phase 2-3 영향도 분석 | 2026-01-14 |

## 관련 문서

- [../02_design/](../02_design/) - 설계 문서
- [../03_implementation/](../03_implementation/) - 구현 문서
- [../04_testing/](../04_testing/) - 테스트 문서

## 명명 규칙

- 파일명 접두사: `XX_` (생성일 기준 순번)
- 파일명 형식: `snake_case`
- 예: `01_hybrid_rag_knowledge_platform_plan.md`
