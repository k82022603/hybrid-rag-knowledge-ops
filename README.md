# Hybrid RAG Knowledge Operations

Graph RAG 기반 지능형 지식 검색 시스템

`#GraphRAG` `#HybridSearch` `#AI가상팀`

---

기업 내부 문서(기술 문서, 매뉴얼, 위키 등)를 자동 수집하여
파싱 → 청킹 → 임베딩 → 엔티티 추출까지
**3-Phase ETL**로 처리한다.

검색은 **4-Way Hybrid** 방식:
Dense Vector(의미 유사도) + Sparse Vector(키워드) +
BM25(Nori 한국어) + Graph Search(Neo4j 엔티티 관계)를
**RRF(Reciprocal Rank Fusion)**로 통합하여 최적 결과를 도출한다.

**Knowledge Graph**는 문서 간 숨겨진 관계를 시각화하고,
"A 기술이 B 프로젝트에 어떻게 쓰이는가" 같은
관계 기반 질의를 지원한다.

기술 스택은 **Python FastAPI**(AI Service) +
**SpringBoot**(API Gateway) + **React 18**(Frontend).
데이터는 **PostgreSQL**(SSOT) + **Elasticsearch**(벡터/전문검색) +
**Neo4j**(그래프) 3중 저장.
런타임 LLM은 **DeepSeek V3.2**로
GPT-4o급 품질을 95% 비용 절감으로 운영한다.

**Docker Compose** 기반 18개 컨테이너로 구성되며,
Prometheus / Grafana / Kibana / Jaeger
옵저버빌리티 스택을 갖추고 있다.

개발은 **Claude Code + 13개 AI 에이전트 가상팀**이 협업하며,
PM / TechLead / Developer / QA 역할 분리로
실제 개발팀처럼 운영한다.

---

Automatically collects internal enterprise documents
(technical docs, manuals, wikis) and processes them through
a **3-Phase ETL** pipeline:
parsing, chunking, embedding, and entity extraction.

Search uses a **4-Way Hybrid** approach:
Dense Vector (semantic similarity) + Sparse Vector (keyword) +
BM25 (Nori Korean analyzer) + Graph Search (Neo4j entity relationships),
unified through **RRF (Reciprocal Rank Fusion)**
to deliver optimal results.

The **Knowledge Graph** visualizes hidden relationships
between documents, supporting relationship-based queries like
"How is Technology A used in Project B?"

Tech stack: **Python FastAPI** (AI Service) +
**SpringBoot** (API Gateway) + **React 18** (Frontend).
Data is stored across **PostgreSQL** (SSOT) +
**Elasticsearch** (vector/full-text search) +
**Neo4j** (graph) — a triple-store architecture.
Runtime LLM is **DeepSeek V3.2**,
delivering GPT-4o-level quality at 95% cost reduction.

Built on **Docker Compose** with 18 containers,
equipped with a Prometheus / Grafana / Kibana / Jaeger
observability stack.

Development is powered by
**Claude Code + a virtual team of 13 AI agents**,
operating like a real dev team with
PM / TechLead / Developer / QA role separation.

---

| 항목 | 내용 |
|------|------|
| **Version** | 5.0 |
| **Updated** | 2026-02-16 |
| **Status** | Sprint 12 - Entity Extraction Phase 2 (66% complete) |
| **Test Coverage** | 97% avg across 5 core modules (Docker mode) |
| **CI/CD** | 8 GitHub Actions workflows |
| **AI Model** | Claude Opus 4.6 + Agent Teams (13 agents) |

---

## 📁 폴더 구조

```
.
├── knowledge_service/             # Python AI Service (핵심)
│   ├── src/app/                   # 소스코드 (services, api, models)
│   ├── scripts/                   # ETL/배치 스크립트
│   ├── docs/                      # 프로젝트 문서 (01~07)
│   └── frontend/                  # React 18 프론트엔드
│
├── infrastructure/docker/         # Docker Compose + Nginx
├── scripts/                       # 공통 유틸 (send_slack.sh 등)
├── work_logs/                     # 작업 일지 / 세션 로그
├── CLAUDE.md                      # Claude Code 규칙 (v2.28)
├── PLAN.md                        # 프로젝트 계획
└── README.md                      # 이 파일
```

## 🚀 빠른 시작

```bash
# 1. 환경 설정
cp .env.example .env
# .env 파일에 DEEPSEEK_API_KEY 등 입력

# 2. 인프라 실행
cd infrastructure/docker
docker-compose up -d

# 3. 개발 환경
cd knowledge_service
poetry install
python src/scripts/init_databases.py

# 4. 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 🛠 기술 스택

| 레이어 | 기술 |
|--------|------|
| **AI Service** | Python 3.11, FastAPI, LangGraph, LangChain |
| **API Gateway** | SpringBoot 3.x, Resilience4j |
| **Frontend** | React 18, Tailwind CSS, TypeScript |
| **Database** | PostgreSQL 16, Neo4j 5.x, Elasticsearch 8.x |
| **LLM** | DeepSeek V3.2 (런타임), Claude Opus 4.6 (개발) |
| **Embedding** | BGE-M3 (Dense + Sparse) |
| **문서 파싱** | Docling 2.x (PDF, DOCX, HWP, MD, TXT, HTML) |
| **Infra** | Docker Compose (18 컨테이너), Nginx |
| **Observability** | Prometheus, Grafana, Kibana, Loki, Jaeger |

## 📊 데이터 현황

| 항목 | 수치 |
|------|------|
| 문서 | 1,437개 |
| 청크 | 56,063개 |
| 엔티티 | 90,000+ (Neo4j) |
| 관계 | 488,000+ (MENTIONS + RELATED + PART_OF) |
| Dense + Sparse 임베딩 | 100% 완료 |
| 3-Store 정합성 | ES = PG = Neo4j 100% |

## 📅 현재 진행 상황

### Sprint 12 (2026-02-16)

| 상태 | 작업 | 설명 |
|:----:|------|------|
| ✅ | ETL Phase 1 | 파싱+청킹 → 1,437 docs → 56,063 chunks |
| ✅ | ETL Phase 2 | Colab GPU 임베딩 (Dense+Sparse 100%) |
| ✅ | Phase 3 Round 1 | Entity Extraction (tc>=100) → 16,185건 |
| ✅ | 4-Way RRF 검색 | Dense+Sparse+BM25+Graph 통합 |
| ✅ | RAGAS v9 평가 | B+ 등급 (51쿼리) |
| ⏳ | **Phase 3 Round 2** | **Entity Extraction (tc>=50) → 23,074건 (66%)** |
| 📋 | 쓰레기 청크 삭제 | tc<50 청크 16,766건 ES/Neo4j/PG 정리 |
| 📋 | Neo4j MERGE 최적화 | UNWIND 배치 MERGE 적용 |

### 주요 마일스톤

| 날짜 | 마일스톤 |
|------|----------|
| 01-16 | 설계 문서 6종 완성 (종합 9.1/10) |
| 01-24 | 인프라 18개 컨테이너 + CI/CD 구축 |
| 01-30 | Backend API 12개 + 테스트 626/627 |
| 02-05 | Phase 5 배포, 테스트 97%, Opus 4.6 전환 |
| 02-10 | ETL Phase 1+2 완료 (56,063건 100%) |
| 02-15 | Phase 3 Entity Extraction + RAGAS v9 |
| 02-16 | Phase 3 Round 2 (3-워커 병렬, 66% 진행 중) |

## 📚 문서

| 문서 | 설명 |
|------|------|
| [CLAUDE.md](./CLAUDE.md) | Claude Code 규칙 v2.28 |
| [PLAN.md](./PLAN.md) | 프로젝트 계획 |
| [플랫폼 상세 설계서](./knowledge_service/docs/02_design/01_hybrid_rag_platform_detailed_design.md) | Gleaning 포함 핵심 설계 |
| [ETL 배치 설계서](./knowledge_service/docs/03_implementation/etl_batch_pipeline_design.md) | 3-Phase 분리 전략 |
| [ETL 운영 가이드](./knowledge_service/docs/07_maintenance/22_etl_3phase_operations_guide.md) | 3-Phase 실행/모니터링 |
| [Entity Extraction 보고서](./knowledge_service/docs/results/entity_extraction_report_2026-02-15.md) | 실측 비용 + 타 LLM 비교 |
| [개발자 에이전트 가이드](./knowledge_service/docs/05_development/01_developer_agent_guide.md) | AI 에이전트 도구 사용법 |
| [Agent Teams 가이드](./docs/12_Agent_Teams_활용_가이드.md) | 멀티-에이전트 협업 |

## 🔐 보안

- API 키는 `.env` 파일에서 관리 (git 제외)
- PostgreSQL / Neo4j 기본 비밀번호 변경 권장
- 프로덕션 환경에서는 Elasticsearch 보안 활성화

## 📝 라이선스

[MIT License](./LICENSE)

---

**Made with Claude Code (Opus 4.6) & DeepSeek V3.2**
