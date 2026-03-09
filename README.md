# Hybrid RAG Knowledge Platform

> **[고도화 진행중]** 2026-01-12 ~ 진행중 (Sprint 09 고도화) | Graph RAG 기반 지능형 지식 검색 시스템 — 4-Way Hybrid Search + Knowledge Graph + 13 AI Agents

[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)](#) [![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white)](#) [![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](#) [![Docker](https://img.shields.io/badge/Docker_Compose-18_containers-2496ED?logo=docker&logoColor=white)](#) [![RAGAS](https://img.shields.io/badge/RAGAS-A--grade-brightgreen)](#) [![Coverage](https://img.shields.io/badge/Coverage-97%25-success)](#)

기업 내부 문서를 **3-Phase ETL**(파싱 → 청킹 → 임베딩 → 엔티티 추출)로 자동 처리하고, **4-Way Hybrid Search**(Dense + Sparse + BM25 + Graph)를 RRF로 통합하여 최적의 검색 결과를 제공합니다. Knowledge Graph가 문서 간 숨겨진 관계를 시각화하고 관계 기반 질의를 지원합니다.

### Highlights

- **4-Way Hybrid Search** — Dense Vector + Sparse Vector + BM25(Nori) + Graph Search, RRF 통합 + BGE-Reranker
- **Knowledge Graph** — 92K 엔티티, 775K 관계로 "A 기술이 B 프로젝트에 어떻게 쓰이는가" 같은 관계 질의 지원
- **3-Phase ETL** — 108K 청크 처리, CPU/GPU 분리 파이프라인, DeepSeek V3.2 기반 엔티티 추출
- **Triple-Store** — PostgreSQL(SSOT) + Elasticsearch(벡터/전문검색) + Neo4j(그래프)
- **95% 비용 절감** — DeepSeek V3.2로 GPT-4o급 품질, 전체 파이프라인 $52 운영
- **AI 가상팀** — Claude Code + 13개 AI 에이전트(PM/TL/Dev/QA)가 실제 개발팀처럼 협업
- **Full Observability** — Prometheus / Grafana / Kibana / Jaeger / Loki, Docker Compose 18개 컨테이너

---

<details>
<summary><b>English</b></summary>

> **[Project Completed]** 2026-01-12 ~ 2026-02-18 (38 days, 12 sprints) | Intelligent knowledge search system powered by Graph RAG — 4-Way Hybrid Search + Knowledge Graph + 13 AI Agents

An enterprise knowledge platform that automatically processes internal documents through a **3-Phase ETL** pipeline (parsing → chunking → embedding → entity extraction) and delivers optimal search results via **4-Way Hybrid Search** (Dense + Sparse + BM25 + Graph) unified with RRF. The Knowledge Graph visualizes hidden relationships between documents and supports relationship-based queries.

**Key Features:**
- **4-Way Hybrid Search** — Dense Vector + Sparse Vector + BM25 (Nori Korean analyzer) + Graph Search, RRF fusion + BGE-Reranker
- **Knowledge Graph** — 92K entities, 775K relationships enabling queries like "How is Technology A used in Project B?"
- **3-Phase ETL** — 108K chunks processed, CPU/GPU split pipeline, DeepSeek V3.2-powered entity extraction
- **Triple-Store Architecture** — PostgreSQL (SSOT) + Elasticsearch (vector/full-text) + Neo4j (graph)
- **95% Cost Reduction** — GPT-4o-level quality via DeepSeek V3.2, entire pipeline operated at $52
- **AI Virtual Team** — Claude Code + 13 AI agents (PM/TL/Dev/QA) collaborating like a real development team
- **Full Observability** — Prometheus / Grafana / Kibana / Jaeger / Loki on Docker Compose (18 containers)

</details>

---

| 항목 | 내용 |
|------|------|
| **Version** | 5.4 (Enhancement) |
| **프로젝트 기간** | 2026-01-12 ~ 진행중 (Sprint 09 고도화) |
| **Status** | **고도화** — UAT 18/18 PASS, SCRUM-101 수정, Chat API 튜닝, RRF 후보 수 제한 |
| **Test Coverage** | 97% avg across 5 core modules (Docker mode) |
| **CI/CD** | 8 GitHub Actions workflows |
| **AI Model** | Claude Opus 4.6 / Sonnet 4.6 + Agent Teams (13 agents, tiered) |

---

## 📁 폴더 구조

```
.
├── knowledge_service/             # Python AI Service (핵심)
│   ├── src/app/                   # 소스코드 (services, api, models)
│   ├── scripts/                   # ETL/배치 스크립트
│   ├── docs/                      # 프로젝트 문서 (01~08)
│   └── frontend/                  # React 18 프론트엔드
│
├── docs/                          # 프로젝트 산출물 (01~14)
├── infrastructure/docker/         # Docker Compose + Nginx
├── scripts/                       # 공통 유틸 (send_slack.sh 등)
├── work_logs/                     # 작업 일지 (01~07 번호 체계)
│   ├── 01_daily_logs/             # 일일 작업 일지
│   ├── 02_session_logs/           # 세션 로그
│   ├── 03_standups/               # 스탠드업 미팅
│   ├── 04_meetings/               # 회의록
│   ├── 05_vibe_logs/              # 바이브 코딩 일지
│   ├── 06_insights/               # 인사이트
│   └── 07_retrospectives/         # 회고
│
├── CLAUDE.md                      # Claude Code 규칙 (v2.29)
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
| **LLM** | DeepSeek V3.2 (런타임), Claude Opus 4.6 + Sonnet 4.6 (개발) |
| **Embedding** | BGE-M3 (Dense + Sparse) |
| **문서 파싱** | Docling 2.x (PDF, DOCX, HWP, MD, TXT, HTML) |
| **Infra** | Docker Compose (18 컨테이너), Nginx |
| **Observability** | Prometheus, Grafana, Kibana, Loki, Jaeger |

## 📊 데이터 현황

| 항목 | 수치 |
|------|------|
| 문서 | 1,437개 |
| 청크 | 42,612개 (쓰레기 청크 13,601건 정리 후) |
| 엔티티 노드 | 91,673 (Entity + Technology + Person) |
| 관계 | 746,667 (MENTIONS + RELATED_TO + HAS_ENTITY + PART_OF) |
| Dense + Sparse 임베딩 | 100% 완료 |
| Entity Extraction | 100% 완료 (23,074건 처리) |
| 3-Store 정합성 | ES = PG = Neo4j 100% |

## 📅 최종 완료 현황

### Sprint 12 — Final (2026-02-16 ~ 02-18)

| 상태 | 작업 | 설명 |
|:----:|------|------|
| ✅ | ETL Phase 1 | 파싱+청킹 → 1,437 docs → 56,063 chunks |
| ✅ | ETL Phase 2 | Colab GPU 임베딩 (Dense+Sparse 100%) |
| ✅ | Phase 3 Round 1 | Entity Extraction (tc>=100) → 16,185건 |
| ✅ | Phase 3 Round 2 | Entity Extraction (tc>=50) → 23,074건 완료 |
| ✅ | 쓰레기 청크 삭제 | tc<50 청크 13,601건 ES/Neo4j/PG 정리 |
| ✅ | 4-Way RRF 검색 | Dense+Sparse+BM25+Graph 통합 |
| ✅ | BGE-Reranker 적용 | Post-RRF Cross-encoder 재순위 |
| ✅ | RAGAS v11 평가 | **A- 등급** (51쿼리, 7도메인, 산술평균 0.711) |

### 주요 마일스톤

| 날짜 | 마일스톤 |
|------|----------|
| 01-16 | 설계 문서 6종 완성 (종합 9.1/10) |
| 01-24 | 인프라 18개 컨테이너 + CI/CD 구축 |
| 01-30 | Backend API 12개 + 테스트 626/627 |
| 02-05 | Phase 5 배포, 테스트 97%, Opus 4.6 전환 |
| 02-10 | ETL Phase 1+2 완료 (56,063건 100%) |
| 02-15 | Phase 3 Entity Extraction Round 1 + RAGAS v9 |
| 02-16 | Phase 3 Round 2 + Reranker + RAGAS v11 A- 달성 |
| 02-18 | **프로젝트 종료 — 사용자 테스트 완료, 산출물 v1.1, 문서 현행화** |
| 03-09 | **고도화 — UAT 18/18, Chat API 튜닝, SCRUM-101 수정, RRF 후보 수 제한** |

## 📈 프로젝트 성과

### 검색 품질 (RAGAS v11 — Reranker 적용)

| 지표 | v11 점수 | v10 점수 | 변화 | 의미 |
|------|:----:|:----:|:---:|------|
| **Faithfulness** | **0.935** | 0.919 | +0.016 | 환각 6.5% — 역대 최고 |
| **Answer Relevancy** | **0.621** | 0.647 | -0.026 | 소폭 하락 (트레이드오프) |
| **Context Precision** | **0.618** | 0.489 | **+0.129** | **+26.4%** Reranker 효과 |
| **Context Recall** | **0.672** | 0.474 | **+0.198** | **+41.8%** Reranker 효과 |
| **종합** | **A-** | B+ | | HIGH 33건(65%), PARTIAL 12건, NONE 6건 |

### 핵심 성과

**"데이터의 양이 아닌 구조화의 질이 검색 성능을 결정한다"** 는 것을 수치로 입증했다.

v8 시스템은 108,000개 청크를 무차별 인덱싱했다 (산술평균 0.632).
v11은 그 중 61%를 제거하고 42,462개만 남겼음에도
**산술평균 0.711로 +12.5% 향상**을 달성했다.
92,209개 엔티티와 775,366개 관계를 Knowledge Graph로 구축하고,
BGE-Reranker로 정밀 재순위하여 달성한 결과다.

- **entity_relation 도메인**: 7건 전부 HIGH, **Faithfulness 1.000** — 엔티티 관계 질의 완벽 대응
- **multi_hop 도메인**: 7건 중 6건 HIGH (86%) — 여러 문서에 걸친 추론 경로 제공
- **semantic 도메인**: v10 D등급 → v11 **C등급 승격** (+0.152) — Reranker 효과
- **v8→v9→v10→v11**: "양으로 밀어붙이기" → "품질 정제" → "Knowledge Graph 보강" → "Reranker로 정밀도 향상"

### 기술적 의의

1. **4-Way RRF + Reranker 검증**: Dense + Sparse + BM25(Nori) + Graph Search를 RRF로 결합하고
   BGE-Reranker(ONNX)로 재순위 — 한국어 1,437문서 / 7도메인 51쿼리에서 체계적으로 평가한 실무 사례
2. **3-Phase ETL 확립**: GPU 없는 환경에서도 Colab 무료 GPU를 활용한 대규모 RAG 구축 가능 —
   소규모 팀/개인 프로젝트에서 현실적으로 적용 가능한 아키텍처
3. **Post-RRF 엔티티 보강**: RRF 퓨전 후 chunk_id로 Neo4j MENTIONS 직접 조회하여
   검색 재현율을 유지하면서 답변 관련성을 높이는 패턴 적용
4. **Reranker ROI 최고**: 코드 변경량 대비 효과가 가장 큰 개선 — Context Precision +26%, Recall +42%

### 비용 효율

전체 파이프라인(Entity Extraction + RAGAS 평가 + 운영)을
**DeepSeek V3.2로 약 $52(~75,000원)** 에 완료했다.

| 비교 대상 | 예상 비용 | 배수 |
|----------|:---------:|:----:|
| **DeepSeek V3.2** (실측) | **$52** | 1x |
| GPT-4o | $775 | 15x |
| Claude Sonnet 4.6 | $1,063 | 20x |
| Claude Opus 4.6 | $5,314 | 102x |

$52로 92,209개 엔티티 추출 + 775,366개 관계 구축 + A- 등급 달성 —
DeepSeek V3.2의 비용 효율은 "실험적으로 재미있는 수준"이 아니라
**"실용 시스템 구축을 가능하게 하는 수준"** 이다.

> 상세 평가: [RAGAS v10/v11 종합 보고서](./knowledge_service/docs/04_testing/13_etl_v2_reprocessing/05_ragas_v10_post_entity_evaluation.md)

## 📚 문서

| 문서 | 설명 |
|------|------|
| [CLAUDE.md](./CLAUDE.md) | Claude Code 규칙 v2.29 |
| [PLAN.md](./PLAN.md) | 프로젝트 계획 |
| [플랫폼 상세 설계서](./knowledge_service/docs/02_design/01_hybrid_rag_platform_detailed_design.md) | Gleaning 포함 핵심 설계 |
| [ETL 배치 설계서](./knowledge_service/docs/03_implementation/etl_batch_pipeline_design.md) | 3-Phase 분리 전략 |
| [ETL 운영 가이드](./knowledge_service/docs/07_maintenance/22_etl_3phase_operations_guide.md) | 3-Phase 실행/모니터링 |
| [RAGAS v10/v11 종합 보고서](./knowledge_service/docs/04_testing/13_etl_v2_reprocessing/05_ragas_v10_post_entity_evaluation.md) | v10 B+ → v11 A- 달성 + 총평 + LLM 비용 비교 |
| [Entity Extraction 보고서](./knowledge_service/docs/04_testing/13_etl_v2_reprocessing/06_entity_extraction_report_2026-02-15.md) | 실측 비용 + 타 LLM 비교 |
| [운영 매뉴얼](./knowledge_service/docs/08_deliverables/03_operator_manual.md) | 시스템 운영/ETL/모니터링 가이드 |
| [프로젝트 완료 보고서 (PPT)](./knowledge_service/docs/08_deliverables/00_project_completion_report.pptx) | 13슬라이드, Tech Innovation 테마 |
| [개발자 에이전트 가이드](./knowledge_service/docs/05_development/01_developer_agent_guide.md) | AI 에이전트 도구 사용법 |
| [Agent Teams 가이드 v3.1](./docs/12_Agent_Teams_활용_가이드.md) | 멀티-에이전트 협업 + 모델 티어링 |
| [프로젝트 사업 방법론](./docs/13_프로젝트_사업_방법론.md) | Claude Code 기반 AI 가상팀 사업 수행 방법론 |
| [프로젝트 개발 방법론](./docs/14_프로젝트_개발_방법론.md) | Claude Code 기반 AI 가상팀 개발 방법론 |

## 🔐 보안

- API 키는 `.env` 파일에서 관리 (git 제외)
- PostgreSQL / Neo4j 기본 비밀번호 변경 권장
- 프로덕션 환경에서는 Elasticsearch 보안 활성화

## 📝 라이선스

[MIT License](./LICENSE)

---

**Made with Claude Code (Opus 4.6 + Sonnet 4.6) & DeepSeek V3.2**

