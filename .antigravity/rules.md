# Antigravity Rules & Development Workflow

🚀 Hybrid RAG Knowledge Operations Workspace

## 📋 목차

1. [프로젝트 구조](#프로젝트-구조)
2. [개발 워크플로우](#개발-워크플로우)
3. [서비스별 규칙](#서비스별-규칙)
4. [협업 가이드](#협업-가이드)

---

## 프로젝트 구조

### Workspace 레벨

```
hybrid-rag-knowledge-ops/          (Root Workspace)
├── knowledge_service/             # Python 지식 검색 서비스
├── frontend/                      # React UI (향후)
├── backend/                       # SpringBoot API (향후)
├── infrastructure/                # Docker, DB 설정
├── storage/                       # 실제 데이터 (git 무시)
└── scripts/                       # 공통 유틸
```

### 각 서비스는 독립적으로 운영

- **knowledge_service**: Python/LangGraph
- **frontend**: React/TypeScript
- **backend**: SpringBoot/Java

---

## 개발 워크플로우

### 1. 새 기능 추가

```bash
# Workspace 루트에서 시작
cd hybrid-rag-knowledge-ops

# 작업 브랜치 생성
git checkout -b feature/new-feature

# 해당 서비스로 이동
cd knowledge_service

# 기능 개발 (Claude Code 사용 권장)
claude-code "기능 설명"

# 테스트 & 커밋
poetry run pytest
git add .
git commit -m "[FEAT] Add new feature"

# Push (CI/CD 트리거)
git push origin feature/new-feature
```

### 2. 버그 수정

```bash
git checkout -b fix/bug-description
cd knowledge_service
claude-code "버그 설명"
# ... 수정 후
git commit -m "[FIX] Fix bug description"
git push origin fix/bug-description
```

### 3. 문서 작성

```bash
# Root 레벨 문서
cd hybrid-rag-knowledge-ops
claude-code "문서 작성 요청"

# 또는 서비스별 문서
cd knowledge_service/docs
claude-code "서비스 문서 작성"
```

---

## 서비스별 규칙

### Knowledge Service (Python)

**위치**: `knowledge_service/`

**기술 스택**:
- Python 3.11+
- LangGraph, LangChain
- FastAPI
- PostgreSQL, Neo4j, Elasticsearch

**개발 환경**:
```bash
cd knowledge_service
poetry install
poetry shell
```

**테스트**:
```bash
poetry run pytest
poetry run pytest --cov=src/app
```

**규칙**: [knowledge_service/CLAUDE.md](../knowledge_service/CLAUDE.md)

---

### Frontend (React) - TBD

**위치**: `frontend/`

**기술 스택**:
- React 18
- TypeScript
- Vite
- TailwindCSS

**개발 환경**:
```bash
cd frontend
npm install
npm run dev
```

**규칙**: `frontend/CLAUDE.md` (작성 예정)

---

### Backend (SpringBoot) - TBD

**위치**: `backend/`

**기술 스택**:
- Java 17+
- SpringBoot 3.x
- Maven/Gradle
- MySQL/PostgreSQL

**개발 환경**:
```bash
cd backend
mvn clean install
mvn spring-boot:run
```

**규칙**: `backend/CLAUDE.md` (작성 예정)

---

## 협업 가이드

### Branch 전략

```
main (프로덕션)
  ↑
develop (개발 통합)
  ↑
feature/* (기능)
fix/*     (버그)
chore/*   (기타)
```

### 커밋 메시지 형식

```
[TYPE] Brief description (50 chars max)

Detailed explanation if needed (wrap at 72 chars)
- Change 1
- Change 2

Related Issues: #123
```

**TYPE**:
- `[FEAT]`: 새 기능
- `[FIX]`: 버그 수정
- `[REFACTOR]`: 코드 재구성
- `[TEST]`: 테스트 추가
- `[DOCS]`: 문서
- `[CHORE]`: 빌드, 의존성 등

### Code Review

- 모든 PR은 최소 1명 리뷰 필수
- 60줄 이상은 2명 리뷰
- 자동 테스트 통과 필수
- CI/CD 파이프라인 모두 성공

---

## 주요 파일 위치

| 항목 | 위치 |
|------|------|
| 전체 규칙 | `CLAUDE.md` |
| 프로젝트 소개 | `README.md` |
| Claude Code 설정 | `.claude/settings.json` |
| Antigravity 규칙 | `.antigravity/rules.md` |
| 워크플로우 | `.agent/workflows/` |
| 인프라 | `infrastructure/` |
| 지식서비스 | `knowledge_service/` |

---

## 🤝 협업 팁

### 동시 작업 피하기

```bash
# 다른 팀원이 작업 중이면 알림
git branch -a | grep feature

# 충돌 방지: 작은 단위로 자주 push
git push origin feature/... (매일)
```

### 의존성 관리

```bash
# Python
cd knowledge_service
poetry add new-package
poetry lock

# Frontend (TBD)
cd frontend
npm install new-package
npm ci  # CI/CD에서 사용
```

### 문서 동기화

모든 변경 후 관련 문서 업데이트:
- `CLAUDE.md` (규칙 변경)
- `README.md` (구조 변경)
- `docs/` (기술 문서)

---

**Last Updated**: 2026-01-12
**Version**: 1.0
