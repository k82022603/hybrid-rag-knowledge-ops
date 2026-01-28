# STORY-059: Frontend 테스트 커버리지 확장 (25% -> 60%)

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | (미정) |
| **Epic** | EPIC-003 |
| **Status** | To Do |
| **Priority** | Medium |
| **Story Points** | 5 |
| **Assignee** | Frontend |
| **Sprint** | 4 |

---

## User Story

**As a** Frontend 개발자,
**I want** 테스트 커버리지를 현재 25%에서 60% 이상으로 확장,
**So that** 코드 변경 시 리그레션을 자동으로 감지하고 안정적인 리팩터링이 가능함.

---

## Acceptance Criteria

- [ ] **Given** 16개 주요 컴포넌트/훅 중 현재 4개만 테스트, **When** 테스트 확장 완료, **Then** 10개 이상 컴포넌트/훅에 테스트 존재
- [ ] **Given** Jest + React Testing Library 테스트 스위트 실행, **When** 커버리지 측정, **Then** 전체 statement 커버리지 60% 이상
- [ ] **Given** 핵심 비즈니스 로직 컴포넌트(SearchChat, MessageBubble, SourceCitation), **When** 테스트 확인, **Then** 해당 컴포넌트 개별 커버리지 80% 이상
- [ ] **Given** 커스텀 훅(useSearchChat, useAuth), **When** 테스트 확인, **Then** 주요 시나리오별 테스트 존재
- [ ] **Given** CI 파이프라인 실행, **When** 테스트 단계, **Then** 커버리지 리포트 자동 생성 및 임계값(60%) 미달 시 경고

---

## Tasks

- [ ] 현재 테스트 커버리지 현황 분석 (어떤 파일이 미테스트인지 파악)
- [ ] SearchChat 컴포넌트 테스트 작성 (메시지 전송, 표시, 스트리밍)
- [ ] MessageBubble 컴포넌트 테스트 작성 (사용자/AI 메시지, 마크다운)
- [ ] SourceCitation 컴포넌트 테스트 작성 (출처 표시, 클릭)
- [ ] ErrorBoundary 테스트 작성 (에러 캐치, fallback 표시)
- [ ] useSearchChat 훅 테스트 작성 (검색 호출, 상태 관리)
- [ ] useAuth 훅 테스트 작성 (로그인, 토큰 관리)
- [ ] Pagination 컴포넌트 테스트 작성
- [ ] Layout/Navigation 컴포넌트 테스트 작성
- [ ] Jest 커버리지 임계값 설정 (jest.config.ts에 coverageThreshold)
- [ ] CI 파이프라인에 커버리지 리포트 추가

---

## 기술 노트

### 문제점 (Sprint 03 리뷰에서 도출)

Sprint 03에서 Frontend 기능 구현에 집중하면서 테스트가 부족한 상태:

1. **낮은 커버리지(25%)** - 16개 주요 unit 중 4개만 테스트
2. **핵심 컴포넌트 미테스트** - SearchChat, MessageBubble 등 핵심 기능 테스트 없음
3. **리팩터링 위험** - 테스트 없이 코드 변경 시 리그레션 감지 불가

### 테스트 현황 (Sprint 03 말)

```
테스트 있음 (4/16):
  [x] LoginForm
  [x] Header
  [x] ThemeToggle
  [x] SearchInput

테스트 없음 (12/16):
  [ ] SearchChat          ← P0 (핵심 기능)
  [ ] MessageBubble       ← P0 (핵심 기능)
  [ ] SourceCitation      ← P0 (핵심 기능)
  [ ] ErrorBoundary       ← P1
  [ ] useSearchChat       ← P1 (핵심 훅)
  [ ] useAuth             ← P1
  [ ] StreamingIndicator  ← P2
  [ ] Pagination          ← P2
  [ ] Sidebar             ← P2
  [ ] ChatInput           ← P2
  [ ] Layout              ← P2
  [ ] NotFound            ← P3
```

### 테스트 전략

```
우선순위별 테스트 작성 순서:
1. P0: SearchChat, MessageBubble, SourceCitation (핵심 비즈니스)
2. P1: ErrorBoundary, useSearchChat, useAuth (안정성/인증)
3. P2: StreamingIndicator, Pagination, ChatInput (보조 기능)
4. P3: Layout, NotFound (낮은 영향도)
```

### 커버리지 설정

```javascript
// jest.config.ts
module.exports = {
  coverageThreshold: {
    global: {
      statements: 60,
      branches: 50,
      functions: 55,
      lines: 60,
    },
  },
};
```

### 영향 범위

- `frontend/src/**/__tests__/` - 테스트 파일 추가
- `frontend/jest.config.ts` - 커버리지 임계값 설정
- `.github/workflows/ci.yml` - 커버리지 리포트 단계

---

## 테스트 계획

- [ ] SearchChat: 메시지 전송, 응답 표시, 스트리밍 상태
- [ ] MessageBubble: 사용자/AI 메시지 렌더링, 마크다운 파싱
- [ ] SourceCitation: 출처 목록 렌더링, 클릭 시 확장
- [ ] ErrorBoundary: 에러 캐치, fallback UI, 리셋
- [ ] useSearchChat: 검색 호출, 상태 전이, 에러 처리
- [ ] useAuth: 토큰 관리, 로그인/로그아웃
- [ ] 커버리지 리포트: 60% 이상 달성 확인

---

## 참고 자료

- Sprint 03 완료 리뷰에서 도출 - 낮은 테스트 커버리지
- [STORY-042 Search UI](./STORY-042-search-ui.md)
- [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/)
