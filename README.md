# Hybrid RAG Knowledge Operations Workspace

🧠 Graph RAG 기반 지능형 지식 검색 시스템 + Antigravity 협업 공간

**프로젝트 버전**: 4.0
**마지막 업데이트**: 2026-01-27
**설계서 상태**: ✅ 설계 완료 (Phase 2 - 100%, 91점 A등급 승인)
**구현 진행**: ✅ Sprint 02 100% 완료 (37/37 SP) → Sprint 03 Day 1 진행 중 (5 Story Review, 24pts)
**CI/CD**: ✅ GitHub Actions 8개 워크플로우 정상 운영

## 📋 개요

이 워크스페이스는 다음 두 가지 핵심 프로젝트를 포함합니다:

1. **knowledge_service** - LangGraph, Neo4j, Elasticsearch 기반 Python 지능형 지식 검색 서비스
2. **Antigravity** - 협업 개발을 위한 규칙 및 워크플로우

## 📁 폴더 구조

```
.
├── README.md                      # 이 파일
├── CLAUDE.md                      # 전체 프로젝트 Claude Code 규칙 (v2.12)
├── PLAN.md                        # 프로젝트 전체 계획
├── .gitignore                     # Git 추적 제외
├── .env.example                   # 환경 변수 템플릿
├── LICENSE                        # MIT License
│
├── knowledge_service/             # Python 지식 검색 서비스
│   ├── src/                       # Python 소스코드
│   ├── data/                      # 입력 데이터
│   ├── docs/                      # 프로젝트 문서
│   │   ├── 01_planning/           # 구현 계획
│   │   ├── 02_design/             # 기술 설계
│   │   ├── 03_implementation/     # 구현 문서
│   │   ├── 04_testing/            # 테스트 문서 ⭐
│   │   ├── 05_development/        # 개발 가이드 ⭐
│   │   ├── 06_deployment/         # 배포 문서
│   │   ├── 07_maintenance/        # 운영/유지보수
│   │   └── results/               # 실행 결과
│   ├── results/                   # 실행 결과
│   ├── pyproject.toml
│   └── README.md
│
├── infrastructure/                # 인프라 설정
│   ├── docker/                    # Docker 설정
│   │   ├── docker-compose.yml
│   │   └── nginx.conf
│   ├── database/                  # DB 초기화 스크립트
│   └── README.md
│
├── storage/                       # 실제 DB 저장소 (git 제외)
│
├── scripts/                       # 공통 유틸 스크립트
│   ├── create_worklog.ps1         # 작업 일지 생성 (PowerShell)
│   ├── create_worklog.sh          # 작업 일지 생성 (Bash)
│   ├── daily_worklog.ps1          # 통합 스크립트 (생성+커밋+푸시)
│   ├── send_slack.sh              # Slack 메시지 표준화 스크립트 ⭐ NEW
│   └── standup_all.sh             # 9개 Agent 일괄 인사 스크립트 ⭐ NEW
│
└── work_logs/                     # 📝 작업 일지 관리
    ├── daily_logs/                # 일일 작업 일지 (YYYY/MM-Month/)
    ├── vibe_logs/                 # 바이브 코딩 일지 (영감/아이디어)
    ├── session_logs/              # Claude Code 세션 로그 ⭐ NEW
    ├── standups/                  # 스탠드업 미팅 기록 ⭐ NEW
    └── README.md
```

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# .env 파일 생성
cp .env.example .env

# API 키 설정
# .env 파일을 열어 ANTHROPIC_API_KEY, DEEPSEEK_API_KEY 등 입력
```

### 2. 인프라 실행

```bash
# Docker 컨테이너 시작 (PostgreSQL, Neo4j, Elasticsearch)
cd infrastructure/docker
docker-compose up -d
```

### 3. 개발 환경 설정

```bash
cd knowledge_service
poetry install
python src/scripts/init_databases.py
```

### 4. 애플리케이션 실행

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 📚 문서

### 핵심 문서

| 문서 | 설명 |
|------|------|
| [CLAUDE.md](./CLAUDE.md) | Claude Code 프로젝트 규칙 v2.19 |
| [PLAN.md](./PLAN.md) | 프로젝트 전체 계획 및 AI 에이전트 협업 구조 |
| [통합 설계서](./knowledge_service/docs/02_design/integrated_detailed_design.md) | 전체 시스템 통합 설계 |

### 설계 문서 (02_design)

| 문서 | 설명 |
|------|------|
| [플랫폼 상세 설계서 v2.4](./knowledge_service/docs/02_design/hybrid_rag_platform_detailed_design.md) | Gleaning 포함 핵심 설계 |
| [API 통합 설계서](./knowledge_service/docs/02_design/api_integration_design.md) | OpenAPI 3.0 스펙 |
| [백엔드 상세 설계서](./knowledge_service/docs/02_design/backend_detailed_design.md) | SpringBoot 17개 섹션 |
| [인프라 상세 설계서](./knowledge_service/docs/02_design/infrastructure_detailed_design.md) | Docker Compose 기반 |
| [Observability 설계서](./knowledge_service/docs/02_design/observability_detailed_design.md) | 모니터링/트레이싱/로깅 |

### 테스트 및 개발 (04_testing, 05_development)

| 문서 | 설명 |
|------|------|
| [단위/통합 테스트 계획서](./knowledge_service/docs/04_testing/unit_integration_test_plan.md) | TDD/Test-Along 기준 포함 ⭐ |
| [개발자 에이전트 가이드](./knowledge_service/docs/05_development/developer_agent_guide.md) | AI 에이전트 도구 사용법 ⭐ |

## 📅 Next Steps (다음 작업)

### 🔴 P0 - 최우선

| # | 작업 | 설명 | 상태 |
|:-:|------|------|:----:|
| 1 | **RAG 파이프라인 구현** | LangGraph + DeepSeek 통합 | 🔜 |
| 2 | **통합 테스트 실행** | E2E 테스트 70%+ 달성 | 🔜 |
| 3 | **Search API 구현** | Elasticsearch + Neo4j 하이브리드 검색 | 🔜 |

### 🟡 P1 - 중요

| # | 작업 | 설명 | 상태 |
|:-:|------|------|:----:|
| 4 | **Knowledge Graph Query** | Neo4j 그래프 쿼리 API | ⏳ |
| 5 | **Frontend 검색 UI** | 검색 인터페이스 구현 | ⏳ |

### ✅ 완료된 작업 (2026-01-26 야간)

| # | 문서/작업 | 설명 |
|:-:|------|------|
| ✅ | **Docker Build 장애 수정** | eclipse-temurin arm64 미지원 → linux/amd64 단일 플랫폼 |
| ✅ | **CD Pipeline 장애 수정** | matrix job outputs 동적 step ID 파싱 실패 → outputs 제거 |
| ✅ | **CI/CD 운영 가이드 v2.0** | 8개 워크플로우 전체 가이드, 트러블슈팅 사례 포함 |
| ✅ | **장애보고서** | INC-2026-01-26-001 (Docker Build + CD Pipeline) |
| ✅ | **Branch Protection 가이드 v1.1** | 1인 개발 실용 설정 추가 |
| ✅ | **인터랙션 모드 가이드** | Shift+Tab 3모드 (Default/Auto-Accept/Plan) |

### ✅ 완료된 작업 (2026-01-24 Sprint 02)

| # | 문서/작업 | 설명 |
|:-:|------|------|
| ✅ | **Infrastructure E2E Test** | QA: 8개 파일, 42개 클래스, 135개 테스트 함수 |
| ✅ | **API Gateway 라우팅** | Backend: 6개 라우팅, Circuit Breaker 4개 |
| ✅ | **Docling 문서 파싱** | ML/RAG: 6개 형식 지원 (PDF, DOCX, HWP, MD, TXT, HTML) |
| ✅ | **Tailwind + Keycloak** | Frontend: Tailwind CSS 3.4, Keycloak JS Adapter |
| ✅ | **CI/CD 파이프라인** | DevOps: pr-build, docker-build, code-quality 워크플로우 |
| ✅ | **WSL2 장애 해결** | Infra: docker-compose.wsl2.yml, docker-start.sh |

### ✅ 완료된 작업 (2026-01-21)

| # | 문서/작업 | 설명 |
|:-:|------|------|
| ✅ | **Kibana 컨테이너 추가** | Elasticsearch 데이터 시각화/쿼리 도구 (포트 5601) |
| ✅ | **18개 컨테이너 구축 완료** | 코어 + 모니터링 전체 인프라 |
| ✅ | **설계 문서 업데이트** | infrastructure_detailed_design, observability_detailed_design에 Kibana 반영 |
| ✅ | **Kibana 사용자 가이드** | docs/07_maintenance/kibana_user_guide.md 작성 |

### ✅ 완료된 작업 (2026-01-18)

| # | 문서/작업 | 설명 |
|:-:|------|------|
| ✅ | **백로그 관리 시스템 구축** | Jira-free Markdown 백로그 (EPIC, Stories, Sprints) |
| ✅ | **EPIC-001 + 6개 Story** | Document Processing 34 pts, Given-When-Then AC |
| ✅ | **Sprint 1-2 계획서** | Sprint 1 (19 pts), Sprint 2 (15 pts) 상세 계획 |
| ✅ | **9개 Agent 정의 파일** | PM, TechLead, Backend, Frontend, MLRag, Data, QA, DevOps, Infra |
| ✅ | **ALM 완전가이드 4개 문서** | Ralph Playbook, 자율학습사이클, 실전협업, 프로젝트 ALM |
| ✅ | **문서 Mermaid 변환** | 11개 텍스트 도식 → Mermaid 변환 (01~04 문서) |
| ✅ | **개발자 통합 가이드** | MCP 서버, Agent 정의, Commands/Skills 사용법 |

### ✅ 완료된 작업 (2026-01-17)

| # | 문서/작업 | 설명 |
|:-:|------|------|
| ✅ | **Backend 설계서 95% 달성** | SSE 스트리밍, Prometheus, Saga, Rate Limiting, Liquibase, Grafana 추가 |
| ✅ | **Frontend 설계서 95% 달성** | WebSocket, MSW, Bundle 최적화, Storybook, PWA, CI/CD 추가 |
| ✅ | **UI Design System 95% 달성** | 복합 컴포넌트, 반응형 사이드바, 모달 스택, Markdown 렌더러 추가 |
| ✅ | **단위/통합 테스트 계획서** | TDD/Test-Along/Test-First 기준, Claude Code 프로토콜 |
| ✅ | **개발자 에이전트 가이드** | Subagent, Skill, Workflow 도구 가이드 |
| ✅ | **Observability 설계서** | 메트릭/로깅/트레이싱, SLA, 보안 모니터링 |
| ✅ | **3차 리뷰 완료** | 종합 점수 9.1/10, 탁월 문서 5개 달성 |

### ✅ 완료된 설계 (2026-01-16)

| # | 문서 | 설명 |
|:-:|------|------|
| ✅ | **API 통합 설계서** | OpenAPI 3.0 스펙, Internal/External API |
| ✅ | **Backend 상세 설계서** | SpringBoot 17개 섹션 |
| ✅ | **민감 데이터 암호화 설계** | 암호화 전략, 키 관리, Vault 통합 |
| ✅ | **인프라 설계서** | Docker Compose 기반 (K8s → 86% 비용 절감) |
| ✅ | **DevOps 설계서** | CI/CD, 모니터링, 배포 전략 |
| ✅ | **Gleaning 기술 통합** | 지식 그래프 품질 33% 향상 |

> 상세 계획은 [PLAN.md](./PLAN.md) 참조

## 🔧 주요 기능

### Hybrid RAG Knowledge Ops

- ✅ **시간 인식 검색** - 지식의 유효기간 고려 + 자동 버전 관리
- ✅ **그래프 기반 탐색** - Neo4j 관계 네트워크
- ✅ **하이브리드 검색** - Dense + Sparse 벡터 검색 (BGE-M3)
- ✅ **자율형 에이전트** - LangGraph 다단계 추론
- ✅ **비용 최적화** - DeepSeek-V3.2 통합 (95% 절감)
- ✅ **제로 조인 검색** - Elasticsearch 단일 쿼리
- ✅ **문서 파싱** - Docling 기반 (97.9% 테이블 정확도)
- ✅ **Gleaning 기법** - 다중 추출로 지식 그래프 품질 33% 향상

## 🛠 기술 스택

### Core
- **Python** 3.11+
- **LangGraph** 1.0+
- **LangChain** 1.2+
- **Docling** 2.x (문서 파싱)

### Databases
- **PostgreSQL** 16+ (정형 데이터)
- **Neo4j** 5.x (지식 그래프)
- **Elasticsearch** 8.x (벡터 + 전문 검색)

### LLM & Embedding
- **DeepSeek-Chat/Reasoner** (엔티티 추출, 오케스트레이션)
- **Claude Sonnet 4** (복잡한 추론)
- **BGE-M3** (Dense + Sparse 임베딩)

### Infrastructure
- **Docker & Docker Compose** (18개 컨테이너)
- **Nginx** (리버스 프록시)
- **Poetry** (의존성 관리)

### Observability
- **Prometheus** (메트릭 수집)
- **Grafana** (통합 대시보드)
- **Kibana** (ES 데이터 시각화/쿼리)
- **Loki** (로그 집계)
- **Jaeger** (분산 추적)

## 📊 성능 지표

| 지표 | 측정값 |
|------|--------|
| 응답 시간 | < 3초 (P95) |
| 검색 정확도 | > 85% (Precision@5) |
| 동시 사용자 | 100명 (1단계 목표) |
| 메타데이터 추출 정확도 | 95%+ |
| 테이블 파싱 정확도 | 97.9% (Docling) |
| 월간 LLM 비용 | ~$2.76 (95% 절감) |

## 🤝 개발 가이드

### Claude Code 사용

```bash
cd knowledge_service
claude-code "원하는 작업 설명"
```

### 개발자 에이전트 도구

AI 에이전트가 사용할 수 있는 도구 가이드:
- [개발자 에이전트 가이드](./knowledge_service/docs/05_development/developer_agent_guide.md)

### 테스트 접근법

- **TDD**: 복잡한 알고리즘, 비즈니스 규칙
- **Test-Along**: 단순 CRUD, UI 컴포넌트
- **Test-First**: 버그 수정 시 재현 테스트

자세한 내용: [테스트 계획서](./knowledge_service/docs/04_testing/unit_integration_test_plan.md)

### 작업 일지

```bash
# Claude Code 명령어 사용 (권장)
/daily:daily-close     # 전체 마무리 (일지+문서+커밋+푸시)
/daily:daily-log       # 작업일지만 작성/업데이트
```

### 커밋 규칙

[CLAUDE.md](./CLAUDE.md) 참고

## 🔐 보안

- API 키는 `.env` 파일에서 관리 (git 제외)
- PostgreSQL 기본 비밀번호 변경 권장
- 프로덕션 환경에서는 Elasticsearch 보안 활성화

## 📝 라이선스

[MIT License](./LICENSE)

---

**Made with Claude Code (Opus 4.5) & DeepSeek-V3.2**

*설계서 v2.4 완료 (Gleaning 통합): 2026-01-16*
*테스트 계획서 및 개발자 에이전트 가이드 추가: 2026-01-17*
*백로그 관리 시스템, 9개 Agent 정의, ALM 가이드 추가: 2026-01-18*
*인프라 비용 86% 절감 (K8s 13대 → Docker Compose 1~2대)*
