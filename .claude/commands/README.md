# Project Claude Code Commands

이 프로젝트에 설치된 커스텀 Claude Code 명령어 모음입니다.

## 설치된 명령어

### Daily Commands (4개) - `/daily:명령어`

| 명령어 | 설명 |
|--------|------|
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

### Workflows (6개) - `/workflows:명령어`

| 명령어 | 설명 | 활용 시나리오 |
|--------|------|---------------|
| `/workflows:feature-development` | 기능 개발 전체 사이클 | 새 기능 구현 |
| `/workflows:smart-fix` | 지능형 문제 해결 | 복잡한 버그 수정 |
| `/workflows:tdd-cycle` | TDD 자동화 | 테스트 주도 개발 |
| `/workflows:security-hardening` | 보안 강화 | 보안 리뷰 |
| `/workflows:full-review` | 종합 코드 리뷰 | 코드 품질 점검 |
| `/workflows:incident-response` | 장애 대응 | 프로덕션 장애 |

## 사용 예시

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

## 출처

- **Daily Commands**: 프로젝트 자체 개발
- **Tools & Workflows**: [wshobson/commands](https://github.com/wshobson/commands) (MIT License)

---

**설치일**: 2026-01-16
**총 명령어**: 23개 (Daily 4개 + Tools 13개 + Workflows 6개)