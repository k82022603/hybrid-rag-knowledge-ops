# Knowledge Service

Graph RAG 기반 지능형 지식 검색 서비스 - LangGraph, Neo4j, Elasticsearch를 활용한 Python AI Service

**Version**: 1.1 | **Updated**: 2026-01-17

## 📁 폴더 구조

```
knowledge_service/
├── src/                          # Python 소스코드
│   ├── app/                      # FastAPI 애플리케이션
│   │   ├── api/                  # REST API 엔드포인트
│   │   ├── core/                 # 핵심 로직 (검색, 그래프, 임베딩)
│   │   ├── services/             # 비즈니스 로직
│   │   ├── models/               # 데이터 모델
│   │   └── utils/                # 유틸리티
│   ├── scripts/                  # 초기화 및 데이터 처리 스크립트
│   └── tests/                    # 테스트 코드
├── data/                         # 입력 데이터
│   ├── documents/                # PDF 등 원본 파일
│   ├── sample/                   # 샘플 데이터
│   └── fixtures/                 # 테스트 데이터
├── docs/                         # 프로젝트 문서
│   ├── 01_planning/              # 구현 계획
│   ├── 02_design/                # 기술 설계
│   ├── 03_implementation/        # 구현 문서
│   ├── 04_testing/               # 테스트 문서
│   ├── 05_development/           # 개발 가이드 ⭐
│   ├── 06_deployment/            # 배포 문서
│   ├── 07_maintenance/           # 운영/유지보수
│   ├── images/                   # 이미지 리소스
│   └── results/                  # 실행 결과
├── results/                      # 실행 결과 (임시)
│   ├── search_logs/
│   ├── metadata_exports/
│   └── cost_reports/
├── .antigravity/                 # Antigravity 규칙
├── .claude/                      # Claude Code 설정
├── .agent/                       # 워크플로우
├── pyproject.toml
├── CLAUDE.md                     # 프로젝트 Claude 규칙
└── README.md
```

## 🚀 빠른 시작

```bash
# 의존성 설치
poetry install

# 데이터베이스 초기화
python src/scripts/init_databases.py

# 애플리케이션 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 📚 주요 문서

### 기획 및 설계

| 문서 | 설명 |
|------|------|
| [AI Service 구현 계획](./docs/01_planning/05_ai_service_implementation_plan.md) | AI Service 구현 계획 v2.0 |
| [플랫폼 상세 설계서](./docs/02_design/01_hybrid_rag_platform_detailed_design.md) | 상세 설계서 v2.4 (Gleaning 포함) |
| [API 통합 설계서](./docs/02_design/04_api_integration_design.md) | OpenAPI 3.0 스펙 |
| [통합 설계서](./docs/02_design/11_integrated_detailed_design.md) | 프로젝트 전체 통합 설계 |

### 테스트 및 개발

| 문서 | 설명 |
|------|------|
| [단위/통합 테스트 계획서](./docs/04_testing/01_unit_integration_test_plan.md) | TDD/Test-Along 기준 포함 |
| [개발자 에이전트 가이드](./docs/05_development/01_developer_agent_guide.md) | AI 에이전트 도구 사용법 ⭐ |
| [RAG 성능 테스트 설계](./docs/02_design/12_rag_performance_test_design.md) | RAG 파이프라인 성능 테스트 |

### 운영

| 문서 | 설명 |
|------|------|
| [Observability 설계서](./docs/02_design/14_observability_detailed_design.md) | 모니터링/트레이싱/로깅 |
| [에러 코드 표준](./docs/02_design/08_error_code_standards.md) | 에러 코드 체계 |

## 🛠 기술 스택

| 영역 | 기술 |
|------|------|
| **Framework** | FastAPI 0.110+ |
| **LLM Orchestration** | LangGraph 1.0+, LangChain 1.2+ |
| **Embedding** | BGE-M3 (Dense + Sparse) |
| **Document Parsing** | Docling 2.x (97.9% 테이블 정확도) |
| **Vector Search** | Elasticsearch 8.x |
| **Graph DB** | Neo4j 5.x |
| **Runtime LLM** | DeepSeek V3.2 (95% 비용 절감) |

## 🧪 테스트

```bash
# 전체 테스트
pytest

# 특정 파일
pytest tests/test_search.py

# 커버리지 포함
pytest --cov=app --cov-report=html
```

테스트 접근 방식은 [테스트 계획서](./docs/04_testing/01_unit_integration_test_plan.md)를 참조하세요.

## 🛠 개발 규칙

- [CLAUDE.md](../CLAUDE.md) - 프로젝트 전체 개발 규칙
- [개발자 에이전트 가이드](./docs/05_development/01_developer_agent_guide.md) - AI 에이전트 도구 사용법
