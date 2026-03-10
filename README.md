# Hybrid RAG Knowledge Platform

> **[프로젝트 완료]** 2025-12 ~ 2026-03-10 (10 Sprints, 130 Stories, 458 SP) | Graph RAG 기반 지능형 지식 검색 시스템 — 4-Way Hybrid Search + Knowledge Graph + 13 AI Agents

[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)](#) [![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white)](#) [![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](#) [![Docker](https://img.shields.io/badge/Docker_Compose-18_containers-2496ED?logo=docker&logoColor=white)](#) [![RAGAS](https://img.shields.io/badge/RAGAS-A--grade-brightgreen)](#) [![Coverage](https://img.shields.io/badge/Coverage-97%25-success)](#)

**"구글처럼 검색하고, 사람처럼 답변한다"** — 회사 내부 문서를 넣으면 AI가 알아서 읽고 정리해서, 질문하면 근거 있는 답변을 돌려줍니다. 검색 결과 나열이 아니라, "이 문서와 저 문서를 종합하면 답은 이겁니다"라고 말해주는 시스템입니다.

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

> **[Project Completed]** 2025-12 ~ 2026-03-10 (10 Sprints, 130 Stories, 458 SP) | Intelligent knowledge search system powered by Graph RAG — 4-Way Hybrid Search + Knowledge Graph + 13 AI Agents

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
| **Version** | 6.0 (Final) |
| **프로젝트 기간** | 2025-12 ~ 2026-03-10 (10 Sprints 완료) |
| **Status** | **완료** — RAGAS v16 Mean 0.763 (A등급), 테스트 1,197건 0 FAIL, 커버리지 97% |
| **Sprint 실적** | 10개 Sprint, 130 Stories, 458 SP 완수 |
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

## 📅 프로젝트 완료 현황

### 전체 Phase 진행률

```
Phase 1: 기획     ████████████████████ 100% ✅
Phase 2: 설계     ████████████████████ 100% ✅ (91점 A등급)
Phase 3: 구현     ████████████████████ 100% ✅ (15 Stories, 84 SP)
Phase 4: 테스트   ████████████████████ 100% ✅ (커버리지 97%, UAT 18/18)
Phase 5: 배포     ████████████████████ 100% ✅ (TechLead 승인)
Phase 6: 고도화   ████████████████████ 100% ✅ (RAGAS 0.763 A등급)
```

### Sprint 10 — Final (2026-03-07 ~ 03-10)

| 상태 | Story | 설명 |
|:----:|-------|------|
| ✅ | STORY-096 | RRF 하이라이팅 — channel_scores, highlight 필드 API 노출 |
| ✅ | STORY-097 | Graph RAG A/B 비교 — useGraph on/off 프레임워크 + 실측 |
| ✅ | STORY-128 | data_loader 모듈 분리 — 1,583줄 → 8개 모듈, 후방 호환 |
| ✅ | STORY-129 | k6 성능 회귀 테스트 — search/chat/auth 3종 + smoke 실행 |
| ✅ | STORY-130 | Adaptive Gleaning — 동적 횟수 + 수확 체감 조기종료 |
| ✅ | STORY-090 | 임베딩 캐싱 — Sparse-aware cache, 149x speedup |
| ✅ | (Bonus) | HybridRetriever rerank pool 통일, ONNX INT8 전환, GPT-4o Judge |

### 주요 마일스톤

| 날짜 | 마일스톤 |
|------|----------|
| 01-16 | 설계 문서 6종 완성 (종합 91점 A등급) |
| 01-24 | 인프라 18개 컨테이너 + CI/CD 구축 |
| 01-30 | Backend API 12개 + 테스트 626/627 |
| 02-05 | Phase 5 배포, 테스트 97%, Opus 4.6 전환 |
| 02-10 | ETL Phase 1+2 완료 (56,063건 100%) |
| 02-16 | Phase 3 완료 + Reranker + RAGAS v11 A- 달성 |
| 02-18 | 프로젝트 1차 종료 — 산출물 v1.1, 문서 현행화 |
| 03-06 | Nori 적용 재검증 완료, Mock 금지 정책 수립 |
| 03-09 | UAT 18/18 PASS, RAGAS v12~v14 변수 격리 완료 |
| 03-10 | **프로젝트 최종 완료 — Sprint 10 전건, RAGAS v16 Mean 0.763 A등급** |

## 📈 프로젝트 성과

### 검색 품질 (RAGAS v7 → v16 개선 여정)

| 지표 | v7 (최초) | v11 | v16 (최종) | 개선폭 |
|------|:----:|:----:|:----:|:---:|
| **Faithfulness** | 0.706 | 0.935 | **0.859** | +21.7%p |
| **Context Precision** | 0.447 | 0.618 | **0.739** | +65.3%p |
| **Context Recall** | 0.512 | 0.672 | **0.690** | +34.8%p |
| **산술평균** | **0.543** | 0.711 | **0.763** | **+40.5%p** |
| **등급** | C | A- | **A** | C → A |

**18회 실험(v1~v18)** 을 통해 변수를 하나씩 격리하며 최적 파라미터를 확정했다:
- `chunk_size=50`, `graph_search_top_k=10`, Reranker 1-Pass, `rerank_pool=min(top_k*3, 50)`

### 핵심 성과

**"데이터의 양이 아닌 구조화의 질이 검색 성능을 결정한다"** 는 것을 수치로 입증했다.

- **RAGAS v7(0.543) → v16(0.763)**: 40.5%p 개선, 18회 변수 격리 실험으로 달성
- **단위 테스트**: 0건 → 1,197건, 0 FAIL
- **UAT**: 18/18 PASS (100%)
- **테스트 커버리지**: 0% → 97% 평균 (5개 핵심 모듈)
- **설계서 품질**: 91점 A등급
- **OPS 운영 문서**: 35건+

### 핵심 기술 결정

| 결정 | 영향 | 근거 |
|------|------|------|
| **Nori 한국어 분석기 적용** | BM25 검색 품질 정상화 | 32일 미적용 사고 → E2E 검증 필수 |
| **Reranker 1-Pass 전환** | 불필요 연산 제거 | Cross-encoder 수학적 중복 증명 |
| **Graph RRF 후보 10개** | Precision +12%p | 가중치보다 후보 수가 정교 |
| **DeepSeek V3.2** | 95% 비용 절감 | GPT-4o급 품질, $52 운영 |
| **3-Phase ETL 분리** | 장애 격리 + GPU 분리 | 파싱/임베딩/엔티티 독립 실행 |
| **Adaptive Gleaning** | 동적 추출 횟수 | 텍스트 길이별 1~3회 + 체감 조기종료 |

### 기술적 의의

1. **4-Way RRF + Reranker 검증**: Dense + Sparse + BM25(Nori) + Graph Search를 RRF로 결합하고
   BGE-Reranker(ONNX)로 재순위 — 한국어 1,437문서 / 7도메인 51쿼리에서 체계적으로 평가한 실무 사례
2. **RAGAS 18회 반복 실험**: 변수 격리 방법론으로 최적 파라미터를 체계적으로 탐색 — 재현 가능한 RAG 튜닝 프로세스 확립
3. **AI 가상팀 13명 협업**: PM/TL/Dev/QA 역할 분리, Slack 통합, 병렬 실행 — 실제 개발팀 운영 방식 적용
4. **3-Phase ETL**: GPU 없는 환경에서도 Colab 무료 GPU를 활용한 대규모 RAG 구축 가능
5. **Reranker 수학적 분석**: Cross-encoder 2-Pass가 중복임을 증명하여 불필요 연산 제거

### 비용 효율

전체 파이프라인(Entity Extraction + RAGAS 평가 + 운영)을
**DeepSeek V3.2로 약 $52(~75,000원)** 에 완료했다.

| 비교 대상 | 예상 비용 | 배수 |
|----------|:---------:|:----:|
| **DeepSeek V3.2** (실측) | **$52** | 1x |
| GPT-4o | $775 | 15x |
| Claude Sonnet 4.6 | $1,063 | 20x |
| Claude Opus 4.6 | $5,314 | 102x |

> 상세 평가: [RAGAS 종합 평가 보고서](./knowledge_service/docs/04_testing/12_embedding_evaluation/) | [프로젝트 최종 보고서](./knowledge_service/docs/07_maintenance/99_project_final_report.md)

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
| [프로젝트 최종 보고서](./knowledge_service/docs/07_maintenance/99_project_final_report.md) | 12개 섹션, 전체 프로젝트 총정리 |
| [최종 보고서 PPT](./knowledge_service/docs/07_maintenance/고도화프로젝트_최종보고서_TechInnovation.pptx) | 24슬라이드, Tech Innovation 테마 |
| [프로젝트 완료 보고서 (PPT)](./knowledge_service/docs/08_deliverables/00_project_completion_report.pptx) | 13슬라이드, 1차 완료 보고서 |
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

**Made with Claude Code (Opus 4.6 + Sonnet 4.6) & DeepSeek V3.2** | 2025-12 ~ 2026-03-10

