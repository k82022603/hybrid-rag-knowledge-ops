# Project Claude Code Commands

이 프로젝트에 설치된 커스텀 Claude Code 명령어 모음입니다.

## 설치된 명령어

### Daily Commands (5개) - `/daily:명령어`

| 명령어 | 설명 |
|--------|------|
| `/daily:standup` | 🆕 데일리 스탠드업 (팀원 인사 + 상태 공유) |
| `/daily:daily-close` | 전체 마무리 (작업일지+바이브로그+문서현행화+푸시) |
| `/daily:daily-log` | 작업일지 작성/업데이트 |
| `/daily:vibe-log` | 바이브 코딩 일지 작성/업데이트 |
| `/daily:sync-docs` | README/CLAUDE/PLAN 문서 현행화 |

### Tools (13개) - `/tools:명령어`

| 명령어 | 설명 | 이 프로젝트 활용 |
|--------|------|-----------------|
| `/tools:ai-review` | AI/ML 코드 리뷰 | RAG 엔진 코드 리뷰 |
| `/tools:code-explain` | 코드 설명 및 문서화 | 온보딩 문서 생성 |
| `/tools:context-save` | 프로젝트 컨텍스트 저장 | 세션 간 연속성 |
| `/tools:context-restore` | 저장된 컨텍스트 복원 | 작업 재개 |
| `/tools:debug-trace` | 디버깅 추적 분석 | 버그 추적 |
| `/tools:deps-audit` | 의존성 보안 감사 | Python 패키지 보안 |
| `/tools:doc-generate` | 문서 자동 생성 | API 문서화 |
| `/tools:error-analysis` | 에러 분석 | 장애 분석 |
| `/tools:issue` | GitHub 이슈 처리 | 이슈 기반 개발 |
| `/tools:pr-enhance` | PR 품질 개선 | 코드 리뷰 품질 |
| `/tools:refactor-clean` | 리팩토링 & 클린코드 | 코드 품질 유지 |
| `/tools:security-scan` | 보안 취약점 스캔 | OWASP Top 10 |
| `/tools:tech-debt` | 기술 부채 분석 | 코드 품질 관리 |

### PM Commands (2개) - `/pm:명령어`

| 명령어 | 설명 | 활용 시나리오 |
|--------|------|---------------|
| `/pm:backlog-sync` | Story 상태 동기화 | Sprint/Story/Jira/Slack 동시 업데이트 |
| `/pm:jira-sync` | Jira 일괄 동기화 | Sprint 전체 상태 동기화 |

### Workflows (6개) - `/workflows:명령어`

| 명령어 | 설명 | 활용 시나리오 |
|--------|------|---------------|
| `/workflows:feature-development` | 기능 개발 전체 사이클 | 새 기능 구현 |
| `/workflows:smart-fix` | 지능형 문제 해결 | 복잡한 버그 수정 |
| `/workflows:tdd-cycle` | TDD 자동화 | 테스트 주도 개발 |
| `/workflows:security-hardening` | 보안 강화 | 보안 리뷰 |
| `/workflows:full-review` | 종합 코드 리뷰 | 코드 품질 점검 |
| `/workflows:incident-response` | 장애 대응 | 프로덕션 장애 |

### Antigravity Commands (2개) - `/antigravity:명령어` (개인 실험용)

> **주의**: ToS 위반 가능성 - 개인 실험/학습 용도로만 사용

| 명령어 | 설명 | 활용 시나리오 |
|--------|------|---------------|
| `/antigravity:setup` | 초기 설정 가이드 | Antigravity Proxy 설정 |
| `/antigravity:workflow` | UI 개발 워크플로우 | Stitch MCP 연동 UI 생성 |

## 사용 예시

### PM 백로그 관리
```bash
# Story 완료 처리 (Sprint 문서 + Story 파일 + Jira + Slack)
/pm:backlog-sync STORY-010 SCRUM-10 Done 01

# Sprint 전체 Jira 동기화
/pm:jira-sync 01

# 스크립트 직접 실행
./scripts/backlog-sync.sh STORY-010 SCRUM-10 Done 01
```

### 개발 워크플로우
```bash
# 새 기능 개발 시작
/workflows:feature-development "Neo4j 그래프 쿼리 최적화"

# AI 코드 리뷰
/tools:ai-review knowledge_service/src/app/services/

# 기술 부채 분석
/tools:tech-debt

# 하루 마무리
/daily:daily-close
```

### 문제 해결
```bash
# 복잡한 문제 해결
/workflows:smart-fix "검색 결과가 비어있는 문제"

# 디버깅
/tools:debug-trace src/app/services/search_service.py

# 보안 스캔
/tools:security-scan
```

### 문서화
```bash
# 코드 설명
/tools:code-explain src/app/models/

# API 문서 생성
/tools:doc-generate

# 프로젝트 문서 동기화
/daily:sync-docs
```

## 💡 일상 워크플로우 팁

### 세션 시작 시

| 상황 | 추천 방법 | 비고 |
|------|----------|------|
| 어제 작업 이어서 | `git log -5` + 작업일지 확인 | 가볍고 빠름 |
| 오랜만에 복귀 | `/tools:context-restore` | 전체 맥락 파악 |
| 여러 프로젝트 병행 | `/tools:context-save` → 전환 → `/tools:context-restore` | 컨텍스트 스위칭 |
| 새 팀원 온보딩 | `CLAUDE.md` + `PLAN.md` 읽기 | 자동 로드됨 |

### 하루 마무리 시

| 상황 | 추천 방법 | 비고 |
|------|----------|------|
| 빠른 마무리 | `/daily:daily-log` | 일지만 작성 |
| 전체 마무리 | `/daily:daily-close` | 일지+문서+커밋+푸시 |
| 아이디어 기록 | `/daily:vibe-log` | 영감/인사이트 저장 |
| 문서만 동기화 | `/daily:sync-docs` | README/CLAUDE/PLAN |

### 코드 리뷰 & 품질

| 상황 | 추천 방법 | 비고 |
|------|----------|------|
| AI/RAG 코드 작성 후 | `/tools:ai-review` | LLM/Vector DB 특화 |
| 일반 코드 점검 | `/workflows:full-review` | 종합 리뷰 |
| PR 올리기 전 | `/tools:pr-enhance` | PR 품질 개선 |
| 보안 점검 필요 | `/tools:security-scan` | OWASP Top 10 |
| 기술 부채 파악 | `/tools:tech-debt` | 리팩토링 우선순위 |

### 문제 해결

| 상황 | 추천 방법 | 비고 |
|------|----------|------|
| 버그 원인 모를 때 | `/tools:debug-trace` | 근본 원인 분석 |
| 복잡한 문제 | `/workflows:smart-fix` | 자동 에이전트 선택 |
| 에러 메시지 분석 | `/tools:error-analysis` | 해결책 제시 |
| GitHub 이슈 처리 | `/tools:issue` | 이슈 분석 및 수정 |

---

## 출처

- **Daily Commands**: 프로젝트 자체 개발
- **Tools & Workflows**: [wshobson/commands](https://github.com/wshobson/commands) (MIT License)

---

---

## Agent Skills (6개)

Agent Skills는 Claude.ai, Claude Desktop, Claude Code **모든 플랫폼**에서 사용 가능합니다.

### 설치된 Skills

| 스킬명 | 설명 | 용도 |
|--------|------|------|
| **layered-architecture-enforcer** | 계층형 아키텍처 원칙 강제 | Controller→Service→Repository 패턴 준수 |
| **rag-pipeline-patterns** | RAG 파이프라인 패턴 | Hybrid Search, RRF, RAGAS 품질 기준 |
| **korean-api-documentation** | 한글 API 문서화 표준 | OpenAPI, Docstring, 에러 코드 문서화 |
| **mermaid-diagrams** | Mermaid 다이어그램 표준 | flowchart, sequenceDiagram, stateDiagram |
| **presentation-maker** | 프레젠테이션 생성 | Marp 기반 슬라이드 생성 |
| **web-design-system** | UI/UX 디자인 시스템 | 색상, 타이포그래피, 컴포넌트 표준 |

### Skills vs Commands 차이점

| 항목 | Skills | Slash Commands |
|------|--------|----------------|
| **플랫폼** | 모든 Claude 플랫폼 | Claude Code만 |
| **Hot-Reload** | 지원 (v2.1.0+) | 지원 |
| **위치** | `.claude/skills/` | `.claude/commands/` |
| **Context Fork** | 지원 | 미지원 |

### Skills 파일 구조

```
.claude/skills/
├── layered-architecture-enforcer/
│   ├── SKILL.md
│   └── README.md
├── rag-pipeline-patterns/
│   ├── SKILL.md
│   └── README.md
├── korean-api-documentation/
│   ├── SKILL.md
│   └── README.md
├── mermaid-diagrams/
│   ├── SKILL.md
│   └── README.md
├── presentation-maker/
│   ├── SKILL.md
│   └── README.md
└── web-design-system/
    ├── SKILL.md
    └── README.md
```

---

**설치일**: 2026-01-16
**최종 업데이트**: 2026-02-06
**총 명령어**: 28개 (Daily 5개 + Tools 13개 + PM 2개 + Workflows 6개 + Antigravity 2개)
**총 Skills**: 6개