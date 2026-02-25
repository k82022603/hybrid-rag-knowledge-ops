# 최종 산출물

**프로젝트**: Hybrid RAG Knowledge Operations
**작성일**: 2026-02-19
**Sprint**: 12 (Final)

---

## 산출물 목록

| # | 문서명 | 버전 | 설명 | 대상 |
|---|--------|:----:|------|------|
| 01 | [프로젝트 최종 보고서](./01_project_final_report.md) | v1.1 | 프로젝트 성과, 비용, 마일스톤, Sprint 12 사용자 테스트 | 경영진, PM |
| 02 | [시스템 아키텍처 설명서](./02_system_architecture.md) | v1.1 | 아키텍처, 데이터 흐름, Redis 캐시 아키텍처, 기술 선택 근거 | 개발자, 아키텍트 |
| 03 | [운영자 매뉴얼](./03_operator_manual.md) | v1.1 | 시스템 운영, 타임아웃 가이드, Redis 캐시 API, 장애 대응 | 운영자, DevOps |
| 04 | [사용자 매뉴얼](./04_user_manual.md) | v1.1 | 대시보드, 검색(Chat/Keyword), 문서 관리, Knowledge Graph | 최종 사용자 |
| 05 | [API 명세서](./05_api_specification.md) | v1.1 | REST API 35개 엔드포인트, 인증 정정, 요청/응답 스키마 | 개발자 |
| 06 | [데이터베이스 설계서](./06_database_design.md) | v1.1 | PG/ES/Neo4j/Redis 스키마, 캐시 아키텍처, Neo4j 네이밍 규칙 | DBA, 개발자 |
| 07 | [설치 및 배포 가이드](./07_installation_guide.md) | v1.1 | 설치 절차, Keycloak 설정, startup_check.sh, 메모리 상세 | 운영자, DevOps |
| 08 | [테스트 결과 보고서](./08_test_report.md) | v1.1 | RAGAS 평가, Sprint 12 사용자 테스트 13케이스, 성능 | QA, PM |
| 09 | [Known Issues & Technical Debt](./09_known_issues.md) | v1.0 | 기술부채 4건, 제한사항 8건, 해결 이슈 5건, Deferred 20건 | PM, 개발자 |
| 10 | [Docker 디스크 관리 가이드](./10_docker_disk_maintenance_guide.md) | v1.0 | Docker 디스크 구조, 빌드 캐시 정리, vhdx 축소, Dependabot, 시연 유지보수 | 운영자, DevOps |

---

## 시스템 현황

| 항목 | 수치 |
|------|------|
| 컨테이너 | 18개 |
| 문서 | 1,441개 |
| 청크 | 42,462+개 |
| 엔티티 노드 | 169,886+개 |
| 관계 | 775,366+개 |
| RAGAS 등급 | A- (v11) |
| 테스트 커버리지 | 97% |

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| AI Service | Python 3.11, FastAPI, LangGraph, LangChain |
| API Gateway | SpringBoot 3.x, Resilience4j |
| Frontend | React 18, Tailwind CSS, TypeScript |
| Database | PostgreSQL 16, Neo4j 5.x, Elasticsearch 8.x |
| LLM | DeepSeek V3.2 (런타임), Claude Opus 4.6 + Sonnet 4.6 (개발) |
| Embedding | BGE-M3 (Dense 1024d + Sparse) |
| Reranker | BGE-Reranker (ONNX) |
| 문서 파싱 | Docling 2.x (PDF, DOCX, HWP, MD, TXT, HTML, PPTX) |
| Infra | Docker Compose (18 컨테이너), Nginx |
| Observability | Prometheus, Grafana, Kibana, Loki, Jaeger |

## 검색 파이프라인

```
Dense Vector (BGE-M3 1024d)   --+
Sparse Vector (BGE-M3)        --+-- RRF 융합 -- BGE-Reranker -- 최종 결과
BM25 Keyword (Nori)            --+
Graph Search (Neo4j)           --+
```

## 핵심 성과

- **RAGAS A- 등급**: Faithfulness 0.935, Context Precision +26%, Context Recall +42% (Reranker 효과)
- **95% 비용 절감**: DeepSeek V3.2로 전체 파이프라인 $52 운영 (GPT-4o 대비 15배 절감)
- **3-Phase ETL**: CPU/GPU 분리 파이프라인으로 GPU 없는 환경에서도 대규모 RAG 구축
- **Knowledge Graph**: 169K 엔티티 + 775K 관계로 관계 기반 질의 지원
- **AI 가상팀**: Claude Code + 13개 AI 에이전트가 실제 개발팀처럼 협업

## 서비스 접속 정보

| 서비스 | URL | 계정 |
|--------|-----|------|
| Frontend | http://localhost | AI Service 또는 SSO 로그인 |
| AI Service Login | http://localhost:8000/api/v1/auth/login | admin@example.com / admin123! |
| Swagger UI | http://localhost:8000/docs | 인증 불필요 |
| Keycloak SSO | Frontend SSO 버튼 | admin / admin123 |
| Keycloak Admin | http://localhost:8180/admin | admin / keycloak_admin_2026! |
| Grafana | http://localhost:3001 | admin / test1234 |
| Kibana | http://localhost:5601 | 인증 불필요 |
| Neo4j Browser | http://localhost:7474 | neo4j / neo4j_dev_2026! |
| MinIO Console | http://localhost:9001 | minioadmin / minio_dev_2026! |
| Prometheus | http://localhost:9090 | 인증 불필요 |
| Jaeger UI | http://localhost:16686 | 인증 불필요 |

## 관련 문서

| 문서 | 설명 |
|------|------|
| [README.md](../../../README.md) | 프로젝트 소개 |
| [CLAUDE.md](../../../CLAUDE.md) | Claude Code 개발 규칙 |
| [PLAN.md](../../../PLAN.md) | 프로젝트 계획 |
| [플랫폼 상세 설계서](../02_design/01_hybrid_rag_platform_detailed_design.md) | 핵심 설계 문서 |
| [ETL 배치 설계서](../03_implementation/etl_batch_pipeline_design.md) | 3-Phase 분리 전략 |
| [ETL 운영 가이드](../07_maintenance/22_etl_3phase_operations_guide.md) | 3-Phase 실행/모니터링 |
| [RAGAS 종합 보고서](../04_testing/13_etl_v2_reprocessing/05_ragas_v10_post_entity_evaluation.md) | B+ -> A- 달성 과정 |

---

*Hybrid RAG Knowledge Operations | Sprint 12 (Final) | 2026-02-19*

*작성: Claude Code (Opus 4.6) | 전체 현행화: 2026-02-19*
