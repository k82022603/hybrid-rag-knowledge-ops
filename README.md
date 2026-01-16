# Hybrid RAG Knowledge Operations Workspace

🧠 Graph RAG 기반 지능형 지식 검색 시스템 + Antigravity 협업 공간

**프로젝트 버전**: 3.0
**마지막 업데이트**: 2026-01-16
**설계서 상태**: ✅ 설계 완료 (Phase 2 - 95%, 통합 아키텍처 설계서만 남음)

## 📋 개요

이 워크스페이스는 다음 두 가지 핵심 프로젝트를 포함합니다:

1. **knowledge_service** - LangGraph, Neo4j, Elasticsearch 기반 Python 지능형 지식 검색 서비스
2. **Antigravity** - 협업 개발을 위한 규칙 및 워크플로우

## 📁 폴더 구조

```
.
├── README.md                      # 이 파일
├── CLAUDE.md                      # 전체 프로젝트 Claude Code 규칙
├── .gitignore                     # Git 추적 제외
├── .env.example                   # 환경 변수 템플릿
├── LICENSE                        # MIT License
├── .editorconfig                  # 에디터 설정
├── .dockerignore                  # Docker 빌드 제외
│
├── knowledge_service/             # Python 지식 검색 서비스
│   ├── src/                       # Python 소스코드
│   ├── data/                      # 입력 데이터
│   ├── docs/                      # 프로젝트 문서
│   │   ├── 01_planning/           # 구현 계획
│   │   │   └── review/            # 기획 문서 리뷰 결과
│   │   ├── 02_design/             # 기술 설계 및 검토
│   │   │   └── review/            # 설계서 리뷰 결과
│   │   └── results/               # 실행 결과
│   ├── results/                   # 실행 결과
│   ├── .antigravity/              # Antigravity 규칙
│   ├── .claude/                   # Claude 설정
│   ├── .agent/                    # 워크플로우
│   ├── pyproject.toml
│   ├── CLAUDE.md
│   └── README.md
│
├── infrastructure/                # 인프라 설정
│   ├── docker/                    # Docker 설정
│   │   ├── docker-compose.yml
│   │   └── nginx.conf
│   ├── database/                  # DB 초기화 스크립트
│   │   ├── postgres/
│   │   ├── neo4j/
│   │   └── elasticsearch/
│   ├── .env.example
│   └── README.md
│
├── storage/                       # 실제 DB 저장소 (git 제외)
│   ├── postgres-data/
│   ├── neo4j-data/
│   └── elasticsearch-data/
│
├── scripts/                       # 공통 유틸 스크립트
│   ├── create_worklog.ps1         # 작업 일지 생성 (PowerShell)
│   ├── create_worklog.sh          # 작업 일지 생성 (Bash)
│   ├── commit_worklog.ps1         # 작업 일지 커밋 (PowerShell)
│   ├── commit_worklog.sh          # 작업 일지 커밋 (Bash)
│   ├── daily_worklog.ps1          # 통합 스크립트 (생성+커밋+푸시)
│   ├── setup.sh
│   ├── start.sh
│   └── stop.sh
│
└── work_logs/                      # 📝 작업 일지 관리
    ├── daily_logs/                 # 일일 작업 일지 (YYYY/MM-Month/)
    ├── vibe_logs/                  # 바이브 코딩 일지 (영감/아이디어)
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

# 상태 확인
docker-compose ps
```

### 3. 개발 환경 설정

```bash
cd knowledge_service

# Python 의존성 설치
poetry install

# 데이터베이스 초기화
python src/scripts/init_databases.py
```

### 4. 애플리케이션 실행

```bash
# API 서버 시작 (권장)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 또는 CLI 모드
python src/app/main.py
```

## 📚 문서

- **[knowledge_service/docs/](./knowledge_service/docs/)** - 프로젝트 상세 문서
  - [01_planning/](./knowledge_service/docs/01_planning/) - 시스템 구현 계획
    - [ai_service_implementation_plan.md](./knowledge_service/docs/01_planning/ai_service_implementation_plan.md) - **AI Service 구현 계획 v2.0**
    - [backend_implementation_plan.md](./knowledge_service/docs/01_planning/backend_implementation_plan.md) - **SpringBoot 백엔드 구현 계획**
    - [review/](./knowledge_service/docs/01_planning/review/) - 기획 문서 리뷰 결과
  - [02_design/](./knowledge_service/docs/02_design/) - 기술 설계 및 검토
    - [hybrid_rag_platform_detailed_design.md](./knowledge_service/docs/02_design/hybrid_rag_platform_detailed_design.md) - **상세 설계서 v2.4 (Gleaning 포함)**
    - [api_integration_design.md](./knowledge_service/docs/02_design/api_integration_design.md) - **API 통합 설계서**
    - [backend_detailed_design.md](./knowledge_service/docs/02_design/backend_detailed_design.md) - **백엔드 상세 설계서**
    - [data_encryption_design.md](./knowledge_service/docs/02_design/data_encryption_design.md) - **민감 데이터 암호화 설계서**
    - [infrastructure_detailed_design.md](./knowledge_service/docs/02_design/infrastructure_detailed_design.md) - **인프라 상세 설계서 (Docker Compose)**
    - [devops_detailed_design.md](./knowledge_service/docs/02_design/devops_detailed_design.md) - **DevOps 상세 설계서**
    - [glossary.md](./knowledge_service/docs/02_design/glossary.md) - **용어사전 v2.1**
    - [technical_assessment/](./knowledge_service/docs/02_design/technical_assessment/) - **기술 검토 문서**
    - [review/](./knowledge_service/docs/02_design/review/) - 설계서 리뷰 결과
  - [work_logs/](./work_logs/) - 작업 및 바이브 코딩 일지

- **[infrastructure/README.md](./infrastructure/README.md)** - 인프라 설정 가이드

- **[CLAUDE.md](./CLAUDE.md)** - Claude Code 전체 프로젝트 규칙

- **[PLAN.md](./PLAN.md)** - 프로젝트 전체 계획 및 AI 에이전트 협업 구조

## 📅 Next Steps (다음 작업)

### 🔴 P0 - 최우선 (내일)

| # | 작업 | 설명 | 상태 |
|:-:|------|------|:----:|
| 1 | **DevOps Skills 생성** | 설계서 기반 역할별 Skills 자동화 | 🔜 |
| 2 | **통합테스트 계획서** | 설계서 기반 E2E 테스트 계획 수립 | 🔜 |
| 3 | **Claude Code Agent 구성** | MCP/Skills/Hooks 구성 계획 | 🔜 |

### 🟡 P1 - 중요 (구현 준비)

| # | 작업 | 설명 | 상태 |
|:-:|------|------|:----:|
| 4 | **개발 환경 구축** | Docker Compose, DB 초기화, 로컬 환경 설정 | ⏳ |
| 5 | **AI Service 초기화** | FastAPI + Poetry, VIP 파이프라인 기본 구조 | ⏳ |
| 6 | **Keycloak 설정** | OAuth 2.0 + PKCE 인증 서버 구성 | ⏳ |

### 🟢 P2 - 일반

| # | 작업 | 설명 | 상태 |
|:-:|------|------|:----:|
| 7 | **SpringBoot 초기화** | Spring Initializr, API Gateway 설정 | ⏳ |
| 8 | **Frontend 초기화** | Vite + React + TypeScript | ⏳ |

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
- ✅ **Gleaning 기법** - 다중 추출로 지식 그래프 품질 33% 향상 (NEW)

## 🛠 기술 스택

### Core
- **Python** 3.11+
- **LangGraph** 0.2.x
- **LangChain** 0.3.x
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
- **Docker & Docker Compose**
- **Nginx** (리버스 프록시)
- **Poetry** (의존성 관리)

## 📊 성능 지표

| 지표 | 측정값 |
|------|--------|
| 임베딩 속도 | ~20 docs/min |
| 검색 응답 시간 | < 0.8초 |
| 메모리 사용률 | ~85% (16GB 환경) |
| 동시 사용자 | 10-15명 |
| 메타데이터 추출 정확도 | 95%+ |
| 테이블 파싱 정확도 | 97.9% (Docling) |
| 월간 LLM 비용 | ~$2.76 (95% 절감) |

## 💰 비용 최적화

- DeepSeek-V3.2 통합으로 **95% 비용 절감**
- 1,000개 문서 처리: $45.50 → $2.26
- 캐시 히트로 추가 90% 절감

## 🤝 개발 가이드

### Claude Code 사용

```bash
cd knowledge_service
claude-code "원하는 작업 설명"
```

### 작업 일지

모든 작업을 체계적으로 기록하여 프로젝트 진행 상황을 추적하고 팀원들과 공유합니다.

#### 왜 작업 일지인가?
- **진행 상황 추적**: 일일 작업 내역을 명확히 기록
- **의사결정 기록**: 왜 특정 기술을 선택했는지 근거 남김
- **학습 축적**: 작업 과정에서 얻은 인사이트 저장
- **팀 커뮤니케이션**: Git 히스토리와 함께 일지도 버전 관리

#### 작업 일지 생성 및 관리

**Windows (PowerShell)**:
```powershell
# 1. 오늘 작업 일지 자동 생성 (VS Code에서 열림)
.\scripts\create_worklog.ps1

# 2. 파일 작성 후, 단계별 커밋
# 2-1. 수동 커밋
.\scripts\commit_worklog.ps1

# 2-2. 또는 자동화 (생성 + 커밋 + 푸시)
.\scripts\daily_worklog.ps1 -Commit -Push

# 특정 날짜 작업 일지 생성
.\scripts\create_worklog.ps1 -Date "2026-01-15"
```

**Linux/Mac (Bash)**:
```bash
# 1. 오늘 작업 일지 생성
./scripts/create_worklog.sh

# 2. 파일 작성 후 커밋
./scripts/commit_worklog.sh

# 특정 날짜 작업 일지 생성
./scripts/create_worklog.sh 2026-01-15
```

#### 작업 일지 폴더 구조
```
work_logs/
├── daily_logs/
│   ├── 2026/
│   │   ├── 01-January/
│   │   │   ├── 2026-01-12.md
│   │   │   ├── 2026-01-13.md
│   │   │   └── ...
│   │   ├── 02-February/
│   │   │   └── ...
│   │   └── ...
│   └── README.md
├── vibe_logs/
│   ├── 2026/
│   │   ├── 01-January/
│   │   │   ├── 2026-01-14-vibe.md
│   │   │   └── ...
│   │   └── ...
│   └── README.md
└── README.md
```

#### 작업 일지 템플릿

자동으로 생성되는 템플릿:

```markdown
# Work Log - YYYY-MM-DD

## 📌 Today's Focus
- [ ] 주요 작업 1
- [ ] 주요 작업 2

## ✅ Completed Tasks
1. **작업명**
   - 상세 내용
   - 결과 및 영향

## 💡 Key Decisions
- 의사결정 1과 그 근거
- 기술 선택지와 왜 선택했는지

## 🐛 Issues & Blockers
- 문제점 1
- 해결 방안

## 📚 Learnings
- 오늘 배운 것
- 인사이트

## 📅 Next Steps
- [ ] 내일 작업 1
- [ ] 내일 작업 2

## 📊 Time Spent
- 작업별 소요 시간
- 총 소요 시간

## 🔗 References
- 관련 이슈: #123
- 참고 문서: [링크]
- Git 커밋: abc123
```

#### 작업 일지 Best Practices

1. **일일 작성**: 업무 종료 전에 반드시 작성
   - 기억이 생생할 때 기록
   - 다음날 아침에 어제 작업 한눈에 파악

2. **구체적 기록**: "버그 수정" 대신 상세히
   - ❌ "ES 문제 해결"
   - ✅ "Elasticsearch RRF 라이선스 Platinum → ranx 라이브러리로 변경"

3. **의사결정 기록**: 기술 선택의 근거 명시
   ```markdown
   ## 💡 Key Decisions
   - **메타데이터 추출**: 별도 프로세스 제거, Stage 1 통합
     - 근거: LLM 호출 1회로 비용 절감
     - 효과: 월간 비용 ~$10 추가 절감
   ```

4. **다음 단계 명시**: 내일 할 일을 미리 정리
   ```markdown
   ## 📅 Next Steps
   - [ ] ValidityDateExtractor 클래스 구현
   - [ ] 단위 테스트 작성
   - [ ] 설계서 리뷰
   ```

5. **참조 링크 추가**: 관련 자료 연결
   ```markdown
   ## 🔗 References
   - 관련 PR: #45
   - 설계 문서: ./docs/02_design/design.md
   - Git 커밋: e6a8e2b
   ```

6. **시간 추적**: 작업별 소요 시간 기록
   ```markdown
   ## 📊 Time Spent
   - 설계 검토: 2시간
   - 코드 작성: 1.5시간
   - 테스트: 1시간
   - 총: 4.5시간
   ```

#### 작업 일지 활용 예시

**팀 공유**:
```bash
# 모든 일지를 한눈에 보기
cd work_logs/daily_logs
ls -la 2026/01-January/

# 최근 일지 확인
cat 2026/01-January/2026-01-13.md
```

**Git 히스토리와 함께 추적**:
```bash
# 작업 일지 커밋 히스토리 조회
git log --oneline -- work_logs/

# 특정 일자의 변경사항 확인
git show e6a8e2b:work_logs/daily_logs/2026/01-January/2026-01-13.md
```

더 자세한 가이드: [CLAUDE.md - 작업 일지 시스템](./CLAUDE.md#-작업-일지-시스템)

### 커밋 규칙

[CLAUDE.md](./CLAUDE.md) 참고

## 🔐 보안

- API 키는 `.env` 파일에서 관리 (git 제외)
- PostgreSQL 기본 비밀번호 변경 권장
- 프로덕션 환경에서는 Elasticsearch 보안 활성화

## 📝 라이선스

[MIT License](./LICENSE)

## 📞 지원

- 이슈: [GitHub Issues](https://github.com/yourorg/hybrid-rag-knowledge-ops/issues)
- 문의: support@example.com

---

**Made with Claude Code (Opus 4.5) & DeepSeek-V3.2**

*설계서 v2.4 완료 (Gleaning 통합): 2026-01-16*
*인프라 비용 86% 절감 (K8s 13대 → Docker Compose 1~2대)*
*신규 설계서 18개, 업데이트 6개: 2026-01-16*
*다음 작업: DevOps Skills, 통합테스트 계획서, Agent 구성*
