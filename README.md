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
| **Version** | 5.1 |
| **Updated** | 2026-02-16 |
| **Status** | Sprint 12 - Entity Extraction 완료, RAGAS v10 B+ 등급 |
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
| 청크 | 42,462개 (쓰레기 청크 13,601건 정리 후) |
| 엔티티 노드 | 169,886 (Entity + Technology + Person) |
| 관계 | 775,366 (MENTIONS + RELATED_TO + HAS_ENTITY + PART_OF) |
| Dense + Sparse 임베딩 | 100% 완료 |
| Entity Extraction | 100% 완료 (23,074건 처리) |
| 3-Store 정합성 | ES = PG = Neo4j 100% |

## 📅 현재 진행 상황

### Sprint 12 (2026-02-16)

| 상태 | 작업 | 설명 |
|:----:|------|------|
| ✅ | ETL Phase 1 | 파싱+청킹 → 1,437 docs → 56,063 chunks |
| ✅ | ETL Phase 2 | Colab GPU 임베딩 (Dense+Sparse 100%) |
| ✅ | Phase 3 Round 1 | Entity Extraction (tc>=100) → 16,185건 |
| ✅ | Phase 3 Round 2 | Entity Extraction (tc>=50) → 23,074건 완료 |
| ✅ | 쓰레기 청크 삭제 | tc<50 청크 13,601건 ES/Neo4j/PG 정리 |
| ✅ | 4-Way RRF 검색 | Dense+Sparse+BM25+Graph 통합 |
| ✅ | RAGAS v10 평가 | **B+ 등급** (51쿼리, 7도메인) |

### 주요 마일스톤

| 날짜 | 마일스톤 |
|------|----------|
| 01-16 | 설계 문서 6종 완성 (종합 9.1/10) |
| 01-24 | 인프라 18개 컨테이너 + CI/CD 구축 |
| 01-30 | Backend API 12개 + 테스트 626/627 |
| 02-05 | Phase 5 배포, 테스트 97%, Opus 4.6 전환 |
| 02-10 | ETL Phase 1+2 완료 (56,063건 100%) |
| 02-15 | Phase 3 Entity Extraction Round 1 + RAGAS v9 |
| 02-16 | **Phase 3 Round 2 완료 + RAGAS v10 B+ 달성** |

## 📈 프로젝트 성과

### 검색 품질 (RAGAS v10)

| 지표 | 점수 | 등급 | 의미 |
|------|:----:|:----:|------|
| **Faithfulness** | 0.919 | A | 환각 8% 이하 — 실무 배포 가능 수준 |
| **Answer Relevancy** | 0.647 | B | v9 대비 +18.3% 회복 |
| **Context Precision** | 0.489 | C | 검색 정밀도 — 개선 여지 |
| **Context Recall** | 0.474 | C | 검색 재현율 — 개선 여지 |
| **종합** | **B+** | | HIGH 30건(59%), PARTIAL 11건, NONE 10건 |

### 핵심 성과

**"데이터의 양이 아닌 구조화의 질이 검색 성능을 결정한다"**는 것을 수치로 입증했다.

v8 시스템은 108,000개 청크를 무차별 인덱싱했다.
v10은 그 중 61%를 제거하고 42,462개만 남겼음에도
동등하거나 그 이상의 검색 품질을 달성했다.
92,209개 엔티티와 775,366개 관계를 Knowledge Graph로 구축하여,
비정형 텍스트 덩어리를 의미적 연결을 갖춘 지식 네트워크로 전환한 결과다.

- **entity_relation 도메인**: 7건 전부 HIGH (100%) — 엔티티 간 관계 질의 완벽 대응
- **multi_hop 도메인**: 7건 중 6건 HIGH (86%) — 여러 문서에 걸친 추론 경로 제공
- **v8→v9→v10 진화**: "양으로 밀어붙이기" → "품질 정제" → "Knowledge Graph로 보강"

### 기술적 의의

1. **4-Way RRF 검증**: Dense + Sparse + BM25(Nori) + Graph Search를 RRF로 결합하여
   한국어 1,437문서 / 7도메인 51쿼리에서 체계적으로 평가한 실무 사례
2. **3-Phase ETL 확립**: GPU 없는 환경에서도 Colab 무료 GPU를 활용한 대규모 RAG 구축 가능 —
   소규모 팀/개인 프로젝트에서 현실적으로 적용 가능한 아키텍처
3. **Post-RRF 엔티티 보강**: RRF 퓨전 후 chunk_id로 Neo4j MENTIONS 직접 조회하여
   검색 재현율을 유지하면서 답변 관련성을 높이는 패턴 적용

### 비용 효율

전체 파이프라인(Entity Extraction + RAGAS 평가 + 운영)을
**DeepSeek V3.2로 약 $52(~75,000원)**에 완료했다.

| 비교 대상 | 예상 비용 | 배수 |
|----------|:---------:|:----:|
| **DeepSeek V3.2** (실측) | **$52** | 1x |
| GPT-4o | $775 | 15x |
| Claude Sonnet 4.5 | $1,063 | 20x |
| Claude Opus 4.6 | $5,314 | 102x |

$52로 92,209개 엔티티 추출 + 775,366개 관계 구축 + B+ 등급 달성 —
DeepSeek V3.2의 비용 효율은 "실험적으로 재미있는 수준"이 아니라
**"실용 시스템 구축을 가능하게 하는 수준"**이다.

> 상세 평가: [RAGAS v10 종합 보고서](./knowledge_service/docs/04_testing/etl_v2_reprocessing/05_ragas_v10_post_entity_evaluation.md)

## 📚 문서

| 문서 | 설명 |
|------|------|
| [CLAUDE.md](./CLAUDE.md) | Claude Code 규칙 v2.28 |
| [PLAN.md](./PLAN.md) | 프로젝트 계획 |
| [플랫폼 상세 설계서](./knowledge_service/docs/02_design/01_hybrid_rag_platform_detailed_design.md) | Gleaning 포함 핵심 설계 |
| [ETL 배치 설계서](./knowledge_service/docs/03_implementation/etl_batch_pipeline_design.md) | 3-Phase 분리 전략 |
| [ETL 운영 가이드](./knowledge_service/docs/07_maintenance/22_etl_3phase_operations_guide.md) | 3-Phase 실행/모니터링 |
| [RAGAS v10 종합 보고서](./knowledge_service/docs/04_testing/etl_v2_reprocessing/05_ragas_v10_post_entity_evaluation.md) | B+ 등급 달성 + 총평 + LLM 비용 비교 |
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
