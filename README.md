# Hybrid RAG Knowledge Operations Workspace

🧠 Graph RAG 기반 지능형 지식 검색 시스템 + Antigravity 협업 공간

**프로젝트 버전**: 2.6
**마지막 업데이트**: 2026-01-12

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
│   │   ├── 02_design/             # 기술 설계 및 검토
│   │   └── work_logs/             # 작업 일지 (git 추적)
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
└── scripts/                       # 공통 유틸 스크립트
    ├── create_worklog.ps1         # 작업 일지 생성 (PowerShell)
    ├── create_worklog.sh          # 작업 일지 생성 (Bash)
    ├── commit_worklog.ps1         # 작업 일지 커밋 (PowerShell)
    ├── commit_worklog.sh          # 작업 일지 커밋 (Bash)
    ├── daily_worklog.ps1          # 통합 스크립트 (생성+커밋+푸시)
    ├── setup.sh
    ├── start.sh
    └── stop.sh
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
  - [02_design/](./knowledge_service/docs/02_design/) - 기술 설계 및 검토
  - [work_logs/](./docs/work_logs/) - 작업 일지

- **[infrastructure/README.md](./infrastructure/README.md)** - 인프라 설정 가이드

- **[CLAUDE.md](./CLAUDE.md)** - Claude Code 전체 프로젝트 규칙

## 🔧 주요 기능

### Hybrid RAG Knowledge Ops

- ✅ **시간 인식 검색** - 지식의 유효기간 고려
- ✅ **그래프 기반 탐색** - Neo4j 관계 네트워크
- ✅ **하이브리드 검색** - Dense + Sparse 벡터 검색
- ✅ **자율형 에이전트** - LangGraph 다단계 추론
- ✅ **비용 최적화** - DeepSeek-V3.2 통합 (93% 절감)
- ✅ **제로 조인 검색** - Elasticsearch 단일 쿼리

## 🛠 기술 스택

### Core
- **Python** 3.11+
- **LangGraph** 0.2.x
- **LangChain** 0.3.x

### Databases
- **PostgreSQL** 16+ (정형 데이터)
- **Neo4j** 5.x (지식 그래프)
- **Elasticsearch** 8.x (벡터 + 전문 검색)

### LLM & Embedding
- **DeepSeek-V3.2** (엔티티 추출)
- **OpenAI o1/GPT-4o** (오케스트레이션)
- **Claude 4.5** (답변 합성)
- **BGE-M3** (멀티링구얼 임베딩)

### Infrastructure
- **Docker & Docker Compose**
- **Nginx** (리버스 프록시)
- **Poetry** (의존성 관리)

## 📊 성능 지표

| 지표 | 측정값 |
|------|--------|
| 임베딩 속도 | ~20 docs/min |
| 검색 응답 시간 | < 1초 |
| 메모리 사용률 | ~85% (16GB 환경) |
| 동시 사용자 | 10-15명 |
| 메타데이터 추출 정확도 | 95%+ |
| 월간 LLM 비용 | ~$12 (93% 절감) |

## 💰 비용 최적화

- DeepSeek-V3.2 통합으로 **93% 비용 절감**
- 1,000개 문서 처리: $25.50 → $1.76
- 캐시 히트로 추가 90% 절감

## 🤝 개발 가이드

### Claude Code 사용

```bash
cd knowledge_service
claude-code "원하는 작업 설명"
```

### 작업 일지

일일 작업 내용을 체계적으로 기록하고 관리합니다.

```powershell
# 오늘 작업 일지 생성 (VS Code 자동 오픈)
.\scripts\create_worklog.ps1

# 작성 후 커밋
.\scripts\commit_worklog.ps1

# 또는 한번에 (생성 + 커밋 + 푸시)
.\scripts\daily_worklog.ps1 -Commit -Push
```

상세 가이드: [docs/work_logs/README.md](./docs/work_logs/README.md)

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

**Made with ❤️ using Claude Code & DeepSeek-V3.2**
