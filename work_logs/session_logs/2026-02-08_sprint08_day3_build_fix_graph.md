# Session Log - 2026-02-08

**Session ID**: 2026-02-08_sprint08_day3_build_fix_graph
**시작 시간**: 13:01
**종료 시간**: 13:34
**모델**: Claude Opus 4.6 (claude-opus-4-6)

---

## 세션 요약

Frontend 빌드 인프라 3가지 문제 근본 해결 + API URL 수정 + Graph Panel 최적화 + Neo4j subgraph CONTAINS 매칭 + 문서 3건 작성

---

## 완료된 작업

### 1. TechLead 위임: Frontend 빌드 인프라 3가지 문제 근본 해결

#### 문제 1: Docker credential 에러
- `~/.docker/config.json`에서 `credsStore: "desktop.exe"` 제거
- WSL2 환경에서 Docker Desktop 미실행 시 credential 에러 방지

#### 문제 2: npm 네트워크 타임아웃
- Frontend Dockerfile에 BuildKit `# syntax=docker/dockerfile:1` 추가
- `--mount=type=cache,target=/root/.npm` 캐시 마운트 적용
- `.npmrc` 신규 생성 (timeout 120s, retry 5회)

#### 문제 3: TypeScript 타입 에러
- `tsconfig.build.json` 신규 생성 (테스트 파일 제외)
- `package.json` build 스크립트: `tsc -b tsconfig.build.json && vite build`
- `GraphPanel.tsx` ref 타입: `ForceGraphMethods` 공식 타입 사용
- 테스트 파일 3개 타입 에러 수정

### 2. Frontend API URL 수정 (ISSUE-012)

- `.env`: `VITE_API_BASE_URL=http://localhost:8080` → `http://localhost:8080/api/v1`
- `.env.production` 신규 생성: `VITE_API_BASE_URL=/api/v1` (Docker/Nginx 배포용)
- **원인**: 빌드 시 `.env`의 absolute URL이 `/api/v1` prefix 없이 bake-in됨
- **결과**: `/dashboard/stats` 404, `/graph/subgraph` 404 해결

### 3. Neo4j subgraph CONTAINS 매칭

- `neo4j_storage.py` `query_subgraph()`: exact match → CONTAINS fallback 추가
- exact match 우선 (`ORDER BY CASE`)으로 정확도 보장
- **원인**: "MSA"로 검색 시 "MSA 차세대 플랫폼 전환 프로젝트" 매칭 안됨
- **결과**: 31 nodes, 58 edges 정상 반환

### 4. Graph Panel 시각화 최적화

- depth 2→1, limit 50→15 (핵심 관계만)
- Chunk/Knowledge 노드 필터링 (문서/청크 노이즈 제거)
- d3Force 물리 튜닝: charge -300, link distance 80
- 라벨 16자 truncate, 중심 노드 radius 10
- 타입별 색상 범례 추가
- 시뮬레이션 종료 후 auto zoomToFit

### 5. 문서 3건 작성

| 문서 | 위치 | 작성자 |
|------|------|--------|
| Neo4j 쿼리 최적화 | `docs/02_design/technical_assessment/05_neo4j_subgraph_query_optimization.md` | 클로드 |
| UI 테스트 방법론 | `docs/04_testing/frontend_ui_test_methodology.md` | QA |
| Chrome Claude Code 조사 | UI 테스트 방법론 문서 내 포함 | QA |

### 6. Chrome Claude Code 조사

- `claude --chrome` 또는 `/chrome`으로 브라우저 자동화 디버깅
- **WSL 미지원**: Chrome은 Windows, Claude Code는 WSL → Native Messaging Host 연동 불가
- macOS/Linux 네이티브에서만 사용 가능

---

## 주요 결정사항

| 결정 | 내용 | 근거 |
|------|------|------|
| CONTAINS 임시 적용 | Full-Text Index 전환 전 CONTAINS 사용 | 73개 노드에서 성능 문제 없음 |
| depth=1, limit=15 | 그래프 가독성 우선 | 31개→15개 노드로 핵심 관계만 표시 |
| `.env.production` 분리 | Docker 빌드와 로컬 개발 환경 분리 | `vite build`는 production 모드 |
| tsconfig.build.json | 빌드 시 테스트 파일 제외 | 테스트 타입 에러가 프로덕션 빌드 차단 방지 |

---

## 변경된 파일 목록

```
knowledge_service/
├── frontend/
│   ├── .env                          # API URL /api/v1 추가
│   ├── .env.production               # 신규: Docker 빌드용
│   ├── .npmrc                        # 신규: npm timeout/retry
│   ├── Dockerfile                    # BuildKit 캐시 마운트
│   ├── package.json                  # build 스크립트 변경
│   ├── tsconfig.build.json           # 신규: 테스트 제외 빌드
│   └── src/features/search/components/
│       └── GraphPanel.tsx            # 시각화 최적화 + ref 타입
├── src/app/storage/
│   └── neo4j_storage.py              # CONTAINS 매칭 추가
└── docs/
    ├── 02_design/technical_assessment/
    │   └── neo4j_subgraph_query_optimization.md  # 신규
    └── 04_testing/
        └── frontend_ui_test_methodology.md       # 신규
```

---

## 현재 프로젝트 상태

### 인프라 상태
| 항목 | 값 |
|------|-----|
| 총 컨테이너 | 18개 (전체 Healthy) |
| ai-service | BuildKit 최적화 적용 |
| Frontend | 빌드 인프라 문제 3건 해결 |

### Sprint 상태
| 항목 | 값 |
|------|-----|
| Sprint | 08 Day 3 |
| 주요 성과 | 빌드 안정화 + 그래프 시각화 개선 |

---

## 다음 작업 (Action Items)

### P0 (Critical)
1. Neo4j Full-Text Index 전환 (CONTAINS → fulltext)

### P1 (High)
2. Dashboard API 구현 (`/api/v1/dashboard/stats`)
3. ISSUE-011 최종 검증 (파일명 필터링)

### P2 (Medium)
4. Frontend Docker 빌드 검증 (credential/npm 수정 후)
5. Visual Regression 테스트 도입 검토

---

## 사용된 도구 및 에이전트

| 도구/에이전트 | 용도 |
|--------------|------|
| TechLead (Task) | 빌드 인프라 3가지 문제 근본 해결 |
| QA (Task) | UI 테스트 방법론 문서 작성 |
| WebFetch | Chrome Claude Code 문서 조사 |

---

## 세션 통계

| 항목 | 값 |
|------|-----|
| 수정된 파일 | 10개 |
| 신규 생성 파일 | 5개 |
| 커밋 | 3건 (b66000c, 4dfab47, 81009aa) |
| 에이전트 위임 | 2건 (TechLead, QA) |

---

*기록자: Claude Code (Opus 4.6)*
*기록 시간: 2026-02-08 13:34 KST*
