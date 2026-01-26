# UI 디자인 검토 보고서

**날짜**: 2026-01-26
**검토자**: Frontend Developer Agent
**버전**: 1.0
**프로젝트**: Hybrid RAG Knowledge Operations - Knowledge Portal Frontend

---

## 요약 (Executive Summary)

현재 프론트엔드 코드베이스는 **기본적인 레이아웃, 라우팅, 인증 인프라가 잘 갖춰져 있으나**, 설계서에서 요구하는 세부 기능(실제 API 연동, SSE 스트리밍, Tailwind 마이그레이션 등)은 대부분 미구현 상태입니다. 특히 **MUI에서 Tailwind CSS로의 마이그레이션이 50% 진행 중**이며, 레이아웃/인증 컴포넌트는 Tailwind로 전환 완료되었지만 페이지 컴포넌트(Dashboard, Search, Knowledge)는 여전히 MUI를 사용하고 있어 **기술 스택 불일치**가 존재합니다.

### 전체 충족도

| 영역 | 충족도 | 비고 |
|------|--------|------|
| 페이지 구성 | 70% | 주요 페이지 구조 존재, 세부 기능 미구현 |
| 기술 스택 | 65% | MUI/Tailwind 혼재 상태 |
| 인증/권한 | 85% | Keycloak + Direct Login 통합 완료 |
| 검색 UI | 30% | Mock 데이터만 사용, SSE 미구현 |
| 대시보드 | 25% | 기본 레이아웃만 존재, 실제 데이터 미연동 |
| 지식관리 | 20% | 빈 껍데기 상태 |
| 상태관리 | 60% | Redux + React Query 설정 완료, 슬라이스 일부 구현 |
| API 연동 | 40% | 서비스 레이어 구조화 완료, 실제 엔드포인트 미연동 |
| UX/접근성 | 50% | LoginForm은 양호, 나머지 페이지 미흡 |
| 테스트 | 0% | 단위/통합/E2E 테스트 전무 |

---

## 1. 페이지 구성 비교

### 1.1 라우팅 구조

**설계서 요구사항** (STORY-040~043, API 통합 설계서):
- `/login` - 로그인 페이지
- `/dashboard` - 대시보드 (기본 페이지)
- `/search` - 검색 페이지 (채팅형 + 키워드)
- `/knowledge` - 지식관리 페이지 (역할 제한)
- `*` - 404 페이지

**현재 구현** (`App.tsx`):

| 페이지 | 설계서 | 구현 상태 | 충족도 | 비고 |
|--------|--------|----------|--------|------|
| 로그인 (`/login`) | 필수 | 구현 완료 | 90% | Direct Login + Keycloak SSO 지원, Tailwind 사용 |
| 대시보드 (`/dashboard`) | 필수 | 껍데기 구현 | 25% | MUI 사용, Mock 데이터, API 미연동 |
| 검색 (`/search`) | 필수 | 기본 구조 구현 | 30% | MUI 사용, 탭 구조 있으나 Mock 데이터만 |
| 지식관리 (`/knowledge`) | 필수 | 껍데기 구현 | 20% | MUI 사용, 기능 없음 |
| 404 (`*`) | 필수 | 구현 완료 | 70% | MUI 사용, 기본적인 에러 페이지 |
| 문서 상세 | 설계됨 | 미구현 | 0% | 라우트 없음 |
| 설정 | 설계됨 | 미구현 | 0% | 라우트 없음 |
| 프로필 | 암시적 | 미구현 | 0% | Header 메뉴에 링크만 존재 |

### 1.2 라우팅 보안

```
현재 구현:
/ -> ProtectedRoute -> MainLayout
  /dashboard -> DashboardPage (인증 필요)
  /search -> SearchPage (인증 필요)
  /knowledge -> RequireKnowledgeManager -> KnowledgePage (KNOWLEDGE_MANAGER|ADMIN)
/login -> LoginPage (공개)
```

- ProtectedRoute: 구현 완료 (Keycloak + Direct Login 통합)
- RequireKnowledgeManager: 구현 완료 (역할 기반 접근 제어)
- AccessDenied 컴포넌트: 구현 완료

---

## 2. 컴포넌트 분석

### 2.1 구현된 컴포넌트

#### 공통 컴포넌트 (`src/components/common/`)

| 파일 | 역할 | 기술 | 설계서 충족도 | 비고 |
|------|------|------|-------------|------|
| `MainLayout.tsx` | 앱 레이아웃 | Tailwind | 90% | 반응형 사이드바, 헤더/콘텐츠 분리 |
| `Header.tsx` | 상단 헤더 | Tailwind + Headless UI | 85% | 사용자 메뉴, 로고, 메뉴 토글 |
| `Sidebar.tsx` | 좌측 네비게이션 | Tailwind | 80% | 역할 기반 메뉴 필터링, 반응형 |

#### 인증 컴포넌트 (`src/auth/`, `src/components/auth/`)

| 파일 | 역할 | 기술 | 설계서 충족도 | 비고 |
|------|------|------|-------------|------|
| `KeycloakProvider.tsx` | 인증 Context Provider | Tailwind | 90% | Keycloak + Direct Login 통합 |
| `ProtectedRoute.tsx` | 라우트 보호 | Tailwind | 90% | 역할/리소스 역할 지원 |
| `keycloak.ts` | Keycloak 설정 | - | 85% | PKCE, 토큰 갱신 설정 |
| `LoginForm.tsx` | 로그인 폼 | Tailwind | 95% | 유효성 검사, 접근성 우수 |

#### 검색 컴포넌트 (`src/components/search/`)

| 파일 | 역할 | 기술 | 설계서 충족도 | 비고 |
|------|------|------|-------------|------|
| `ChatSearch.tsx` | 채팅형 검색 | **MUI** | 25% | Mock 데이터만, SSE 미구현 |
| `KeywordSearch.tsx` | 키워드 검색 | **MUI** | 25% | Mock 데이터만, 실제 검색 미연동 |
| `SearchFilters.tsx` | 검색 필터 | **MUI** | 30% | 기본 구조만, 실제 필터 미연동 |

#### 페이지 컴포넌트 (`src/pages/`)

| 파일 | 역할 | 기술 | 설계서 충족도 | 비고 |
|------|------|------|-------------|------|
| `LoginPage.tsx` | 로그인 페이지 | Tailwind | 90% | 완성도 높음 |
| `DashboardPage.tsx` | 대시보드 | **MUI** | 25% | 하드코딩된 Mock 데이터 |
| `SearchPage.tsx` | 검색 페이지 | **MUI** | 30% | 탭 구조만 |
| `KnowledgePage.tsx` | 지식관리 | **MUI** | 20% | 빈 껍데기 |
| `NotFoundPage.tsx` | 404 페이지 | **MUI** | 70% | 기본 기능 구현 |

### 2.2 미구현 컴포넌트 (설계서 요구사항)

#### STORY-041 (Dashboard UI) - Sprint 3 예정

| 컴포넌트 | 설계서 위치 | 우선순위 | 비고 |
|----------|-----------|----------|------|
| `StatCard` (Tailwind) | STORY-041 | High | MUI 버전 존재, Tailwind 전환 필요 |
| `QuickSearch` | STORY-041 | High | 대시보드 빠른 검색 |
| `RecentSearches` | STORY-041 | Medium | 최근 검색 기록 표시 |
| `useDashboardStats` 훅 | STORY-041 | High | 통계 API 연동 |
| `useRecentSearches` 훅 | STORY-041 | Medium | 검색 기록 API 연동 |
| 환영 메시지 | STORY-041 | Low | 사용자 이름 기반 |

#### STORY-042 (Search UI) - Sprint 3 예정

| 컴포넌트 | 설계서 위치 | 우선순위 | 비고 |
|----------|-----------|----------|------|
| `MessageList` | STORY-042 | High | 메시지 목록 렌더링 |
| `MessageBubble` | STORY-042 | High | User/AI 메시지 버블 |
| `ChatInput` (Tailwind) | STORY-042 | High | MUI 버전 존재, Tailwind 전환 필요 |
| `SourceCitation` | STORY-042 | Medium | 출처 문서 링크 |
| `useSearchChat` 훅 | STORY-042 | High | 채팅 검색 상태 관리 |
| ReactMarkdown 통합 | STORY-042 | Medium | AI 응답 마크다운 렌더링 |

#### STORY-043 (SSE Streaming) - Sprint 3 예정

| 컴포넌트 | 설계서 위치 | 우선순위 | 비고 |
|----------|-----------|----------|------|
| `SSEClient` 유틸리티 | STORY-043 | Critical | SSE 연결 관리 클래스 |
| `useStreamingSearch` 훅 | STORY-043 | Critical | 스트리밍 상태 관리 |
| `StreamingIndicator` | STORY-043 | High | 응답 생성 중 표시 |
| 재연결 로직 | STORY-043 | High | 3회 자동 재시도 |
| 취소 기능 | STORY-043 | Medium | 스트리밍 중단 |

#### 기타 미구현

| 컴포넌트 | 관련 설계 | 우선순위 | 비고 |
|----------|----------|----------|------|
| 문서 업로드 다이얼로그 | 상세 설계서 | High | 파일 업로드 UI |
| 문서 상세 페이지 | 상세 설계서 | Medium | 문서 내용 뷰어 |
| 처리 상태 모니터링 | KnowledgePage | Medium | 문서 처리 큐 |
| Knowledge Graph 시각화 | KnowledgePage | Low | 그래프 뷰어 |
| 알림/토스트 시스템 | 상세 설계서 | Medium | 사용자 피드백 |
| 다크 모드 토글 | tailwind.config.js | Low | 'class' 모드 설정 완료 |

---

## 3. 기술 스택 확인

### 3.1 의존성 분석

| 항목 | 설계 | 구현 | 일치 여부 | 비고 |
|------|------|------|----------|------|
| React 18 | 필수 | react@18.3.1 | 일치 | |
| TypeScript 5.4+ | 필수 | typescript@~5.6.3 | 일치 | |
| Tailwind CSS 3.4+ | 필수 | tailwindcss@3.4.17 | 일치 | 설정 완료, 부분 적용 |
| Headless UI | 필수 | @headlessui/react@2.2.9 | 일치 | Header에서만 사용 |
| Heroicons | 필수 | @heroicons/react@2.2.0 | 일치 | Sidebar/Header에서 사용 |
| Redux Toolkit | 필수 | @reduxjs/toolkit@2.3.0 | 일치 | authSlice, searchSlice, uiSlice |
| React Query | 필수 | @tanstack/react-query@5.59.20 | 일치 | 설정 완료, 실제 사용 미미 |
| Keycloak JS | 필수 | keycloak-js@26.2.2 | 일치 | PKCE 설정 완료 |
| Vite 5.x | 필수 | vite@5.4.10 | 일치 | |
| React Router | 필수 | react-router-dom@6.28.0 | 일치 | |
| Axios | 필수 | axios@1.7.7 | 일치 | API 클라이언트 설정 완료 |

### 3.2 불필요한 의존성 (마이그레이션 대상)

| 패키지 | 현재 사용 | 마이그레이션 상태 | 조치 |
|--------|----------|-----------------|------|
| `@mui/material@6.1.6` | 7개 파일 | 제거 예정 | Tailwind로 전환 후 제거 |
| `@mui/icons-material@6.1.6` | 7개 파일 | 제거 예정 | Heroicons로 대체 |
| `@emotion/react@11.13.3` | MUI 의존 | 제거 예정 | MUI 제거 시 함께 제거 |
| `@emotion/styled@11.13.0` | MUI 의존 | 제거 예정 | MUI 제거 시 함께 제거 |

### 3.3 MUI 사용 현황 (Tailwind 전환 필요)

MUI를 사용하는 파일 **7개** (Tailwind 전환 필요):

| 파일 | MUI 컴포넌트 사용 | 전환 복잡도 |
|------|-----------------|------------|
| `DashboardPage.tsx` | Box, Typography, Grid, Card, CardContent | Medium |
| `SearchPage.tsx` | Box, Typography, Tabs, Tab | Medium |
| `KnowledgePage.tsx` | Box, Typography, Button, Card, Grid | Medium |
| `NotFoundPage.tsx` | Box, Typography, Button | Low |
| `ChatSearch.tsx` | Box, TextField, IconButton, Paper, Typography, CircularProgress | High |
| `KeywordSearch.tsx` | Box, TextField, Button, Paper, Typography, Chip, Pagination | High |
| `SearchFilters.tsx` | Box, FormControl, InputLabel, MenuItem, Select, TextField, Button, Collapse, IconButton | High |

### 3.4 Tailwind CSS 설정 분석

**tailwind.config.js** 분석:

- 커스텀 색상 팔레트: primary(Blue), secondary(Slate), accent(Teal), success(Green), warning(Amber), error(Red) -- 잘 정의됨
- 한글 폰트: Pretendard 설정 완료
- 다크 모드: `class` 전략 설정 (수동 토글 가능)
- 커스텀 애니메이션: fade-in, slide-up, slide-down, pulse-slow
- Typography 플러그인: 설정 완료 (prose 스타일)
- 반응형 컨텐츠 경로: `"./index.html"`, `"./src/**/*.{js,ts,jsx,tsx}"` 정확함

**문제점**: `@tailwindcss/typography` 플러그인이 plugins 배열에 포함되지 않음 (설정은 있으나 활성화 안됨)

### 3.5 빌드 최적화

**vite.config.ts** 분석:

- 코드 스플리팅 설정 완료: vendor, keycloak, ui, redux 청크 분리
- 경로 별칭 설정 완료: @, @/components, @/pages 등
- 프록시 설정: `/api` -> `http://localhost:8080` (API Gateway)
- 소스맵: 활성화 (디버깅 지원)

---

## 4. 상태 관리 분석

### 4.1 Redux Store 구조

```
store/
  index.ts           -- Redux store 설정 (configureStore)
  slices/
    authSlice.ts     -- 인증 상태 관리 (loginAsync, logout, clearError)
    searchSlice.ts   -- 검색 상태 관리 (기본 구조만)
    uiSlice.ts       -- UI 상태 관리 (사이드바, 테마 등)
```

| 슬라이스 | 구현도 | 비고 |
|---------|--------|------|
| authSlice | 85% | loginAsync, token 관리, 에러 처리 완비 |
| searchSlice | 30% | 기본 구조만, 실제 검색 로직 미구현 |
| uiSlice | 40% | 사이드바/테마 기본 상태만 |

### 4.2 React Query 설정

- QueryClient 설정 완료 (staleTime: 5분, retry: 1회)
- 실제 사용하는 쿼리 훅: 없음 (설계서에서 요구하는 useDashboardStats, useRecentSearches 등 미구현)

### 4.3 API 서비스 레이어

| 파일 | 역할 | 구현도 | 비고 |
|------|------|--------|------|
| `api.ts` | Axios 인스턴스 | 70% | 기본 설정, 인터셉터 설정 완료 |
| `searchService.ts` | 검색 API | 30% | 인터페이스 정의, Mock 응답 |
| `knowledgeService.ts` | 문서 관리 API | 25% | 기본 구조만 |
| `authService.ts` | 인증 API | 80% | Direct Login API 연동 완료 |
| `mockAuthInterceptor.ts` | 개발용 Mock | 100% | 개발 환경 Mock 응답 |

---

## 5. UX/접근성 체크

### 5.1 반응형 디자인

| 컴포넌트 | 반응형 지원 | 비고 |
|----------|-----------|------|
| MainLayout | 구현 완료 | 768px 미만에서 사이드바 자동 닫힘 |
| Header | 구현 완료 | 모바일에서 사용자 이름 숨김 |
| Sidebar | 구현 완료 | 모바일 오버레이, 닫기 버튼 |
| LoginPage | 구현 완료 | 최대 너비 제한, 중앙 정렬 |
| DashboardPage | 부분 구현 | MUI Grid responsive 사용 |
| SearchPage | 미구현 | 반응형 처리 없음 |
| KnowledgePage | 부분 구현 | MUI Grid responsive 사용 |

### 5.2 키보드 네비게이션

| 컴포넌트 | 지원 여부 | 비고 |
|----------|----------|------|
| LoginForm | 양호 | Tab 순서, Enter 제출, aria-label |
| Header (Menu) | 양호 | Headless UI 기반 키보드 지원 |
| Sidebar | 기본적 | 버튼 기반이므로 기본 키보드 지원 |
| ChatSearch | 미흡 | Enter로 전송 가능하나 aria 부족 |
| SearchFilters | 미흡 | 키보드 접근성 고려 부족 |

### 5.3 ARIA 및 접근성

| 항목 | 상태 | 비고 |
|------|------|------|
| `aria-label` | 부분 적용 | LoginForm, Header에 적용, 나머지 미흡 |
| `aria-invalid` | 적용 | LoginForm에 적용 |
| `aria-describedby` | 적용 | LoginForm 에러 메시지 연결 |
| `aria-hidden` | 적용 | 장식적 아이콘에 적용 |
| `role="alert"` | 적용 | LoginForm 에러 메시지 |
| `role="tabpanel"` | 적용 | SearchPage 탭 패널 |
| 색상 대비 4.5:1 | 미확인 | 검증 필요 |
| 스크린 리더 지원 | 부분적 | LoginForm 양호, 나머지 미흡 |

### 5.4 `data-testid` 속성

**현재 상태**: 전체 코드베이스에서 `data-testid` 속성 **0건**

E2E 테스트(Playwright) 설정은 완료되었으나(`playwright.config.ts`), 실제 테스트 파일(`e2e/`)과 테스트 식별자가 없습니다.

### 5.5 에러 핸들링 UI

| 페이지/컴포넌트 | 로딩 상태 | 에러 상태 | 빈 상태 | 비고 |
|----------------|----------|----------|--------|------|
| LoginForm | spinner | 에러 메시지 | - | 완성도 높음 |
| ProtectedRoute | 로딩 화면 | 리다이렉트 | - | 양호 |
| DashboardPage | 없음 | 없음 | 없음 | 미구현 |
| ChatSearch | CircularProgress | console.error | 안내 메시지 | 기본적 |
| KeywordSearch | 텍스트 표시 | console.error | 안내 메시지 | 기본적 |
| KnowledgePage | 없음 | 없음 | 빈 상태 아이콘 | 기본적 |

---

## 6. 설계서 대비 주요 GAP 분석

### GAP 1: MUI에서 Tailwind CSS 마이그레이션 미완료 (CRITICAL)

**현상**: 설계서(2026-01-25 마이그레이션 공지)에서 Tailwind CSS 사용을 필수로 지정했으나, **7개 파일**이 여전히 MUI를 사용하고 있습니다.

```
Tailwind 완료: LoginPage, MainLayout, Header, Sidebar, LoginForm,
              KeycloakProvider, ProtectedRoute (7개 파일)
MUI 잔존:     DashboardPage, SearchPage, KnowledgePage, NotFoundPage,
              ChatSearch, KeywordSearch, SearchFilters (7개 파일)
```

**영향**:
- 번들 크기 증가 (MUI + Tailwind 이중 로드)
- 디자인 일관성 저하
- 유지보수 복잡성 증가

### GAP 2: SSE 스트리밍 미구현 (HIGH)

**설계서**: STORY-043에서 SSEClient 클래스, useStreamingSearch 훅, StreamingIndicator, 자동 재연결(3회) 등 상세 설계

**현재 구현**: ChatSearch.tsx에 TODO 주석만 존재. SSE 관련 코드 전무.

```typescript
// 현재 상태: ChatSearch.tsx 내부
// TODO: 실제 SSE 스트리밍 API 연결
// const eventSource = new EventSource(...)
```

### GAP 3: 실제 API 연동 없음 (HIGH)

모든 데이터가 하드코딩된 Mock 또는 setTimeout으로 처리되고 있습니다.

| API | 설계서 | 현재 상태 |
|-----|--------|----------|
| `GET /api/v1/stats/dashboard` | 대시보드 통계 | 하드코딩 Mock |
| `POST /api/v1/search` | 키워드 검색 | setTimeout Mock |
| `GET /api/v1/search/stream` | SSE 스트리밍 | 미구현 |
| `GET /api/v1/documents` | 문서 목록 | 미구현 |
| `POST /api/v1/documents` | 문서 업로드 | 미구현 |
| `GET /api/v1/search/recent` | 최근 검색 | 미구현 |

### GAP 4: 대시보드 핵심 기능 미구현 (MEDIUM)

STORY-041 요구사항 대비:

| 기능 | 상태 | 비고 |
|------|------|------|
| 사용자 환영 메시지 | 미구현 | 현재 "Dashboard" 텍스트만 |
| 통계 위젯 (4종) | 부분 구현 | MUI StatCard 존재, Mock 데이터 |
| 빠른 검색 입력창 | 미구현 | QuickSearch 컴포넌트 없음 |
| 최근 검색 기록 | 미구현 | RecentSearches 컴포넌트 없음 |
| 실제 API 연동 | 미구현 | useDashboardStats 훅 없음 |

### GAP 5: 검색 세부 기능 미구현 (MEDIUM)

STORY-042 요구사항 대비:

| 기능 | 상태 | 비고 |
|------|------|------|
| MessageBubble (User/AI 구분) | 부분 구현 | 인라인으로 존재, 별도 컴포넌트 아님 |
| MessageList | 미구현 | 인라인 렌더링 |
| ChatInput (Tailwind) | 미구현 | MUI TextField 사용 중 |
| SourceCitation (출처 표시) | 미구현 | AI 응답에 출처 표시 없음 |
| ReactMarkdown 통합 | 미구현 | 패키지 미설치 |
| 자동 스크롤 | 구현 완료 | scrollIntoView 사용 |

### GAP 6: 테스트 전무 (HIGH)

| 테스트 유형 | 설계서 요구 | 현재 상태 | 비고 |
|------------|-----------|----------|------|
| Unit Test | 각 STORY에 테스트 계획 있음 | 0개 | vitest 설정만 완료 |
| Integration Test | 각 STORY에 포함 | 0개 | |
| E2E Test | Playwright 설정 완료 | 0개 | e2e/ 디렉토리 비어있음 |
| Accessibility Test | STORY-041, 042에 포함 | 0개 | |

---

## 7. 컴포넌트별 상세 분석

### 7.1 LoginPage.tsx - 가장 완성도 높은 페이지

**장점**:
- Tailwind CSS 완전 적용
- Direct Login + Keycloak SSO 이중 지원
- 개발 모드 테스트 계정 표시
- 반응형 디자인 (min-h-screen, max-w-md)
- 다크 모드 지원 (dark: 클래스)
- 그래디언트 배경 (bg-gradient-to-br)

**부족한 점**:
- 비밀번호 찾기 기능 미구현 (TODO 상태)
- silent-check-sso.html 파일 부재 (설계서 요구)

### 7.2 LoginForm.tsx - 접근성 모범 사례

**장점**:
- WCAG 2.1 AA 준수 의도 명시
- `aria-invalid`, `aria-describedby` 적용
- `role="alert"` 에러 메시지
- 비밀번호 표시/숨김 토글 (`aria-label`)
- 폼 유효성 검사 (이메일/비밀번호)
- Remember me 기능 (localStorage)
- Redux async thunk 연동

**부족한 점**:
- `data-testid` 미적용
- 비밀번호 강도 표시 없음

### 7.3 Header.tsx - Headless UI 활용

**장점**:
- Headless UI Menu 컴포넌트 사용 (접근성 자동 지원)
- Transition 애니메이션 적용
- 사용자 이니셜 아바타 생성
- 역할 태그 표시 (최대 3개)
- Keycloak/Direct 로그인 구분 로그아웃

**부족한 점**:
- 알림 아이콘/배지 미구현
- 검색 바 없음 (설계서 일부에서 요구)

### 7.4 Sidebar.tsx - 역할 기반 메뉴

**장점**:
- 역할 기반 메뉴 필터링 구현
- 활성 메뉴 하이라이트 (location.pathname 비교)
- 모바일 오버레이 + 닫기 버튼
- 다크 모드 지원
- 버전 정보 표시

**부족한 점**:
- 메뉴 아이템이 3개뿐 (설정, 프로필 등 추가 필요)
- 접이식 서브메뉴 미지원
- 아이콘 애니메이션 없음

---

## 8. 다음 단계 권장사항

### 8.1 우선순위 P0 (즉시 처리 필요)

| 순번 | 작업 | 관련 스토리 | 예상 공수 | 비고 |
|------|------|-----------|----------|------|
| 1 | MUI -> Tailwind 마이그레이션 (DashboardPage) | STORY-041 | 2SP | 기존 MUI StatCard를 Tailwind로 전환 |
| 2 | MUI -> Tailwind 마이그레이션 (SearchPage, ChatSearch, KeywordSearch) | STORY-042 | 3SP | 검색 관련 컴포넌트 전체 전환 |
| 3 | MUI -> Tailwind 마이그레이션 (KnowledgePage, NotFoundPage) | - | 1SP | 나머지 페이지 전환 |
| 4 | MUI 패키지 제거 (@mui/*, @emotion/*) | - | 0.5SP | 번들 크기 최적화 |

### 8.2 우선순위 P1 (Sprint 3 핵심)

| 순번 | 작업 | 관련 스토리 | 예상 공수 | 비고 |
|------|------|-----------|----------|------|
| 5 | SSEClient 유틸리티 구현 | STORY-043 | 2SP | 재연결, 취소 로직 포함 |
| 6 | useStreamingSearch 훅 구현 | STORY-043 | 1SP | SSEClient 기반 |
| 7 | ChatSearch Tailwind + SSE 통합 | STORY-042/043 | 3SP | MessageBubble, ChatInput 포함 |
| 8 | Dashboard 실제 API 연동 | STORY-041 | 2SP | useDashboardStats, QuickSearch 구현 |
| 9 | data-testid 속성 추가 (전체) | QA 요구 | 1SP | E2E 테스트 준비 |

### 8.3 우선순위 P2 (Sprint 3 보조)

| 순번 | 작업 | 관련 스토리 | 예상 공수 | 비고 |
|------|------|-----------|----------|------|
| 10 | 키워드 검색 API 연동 | STORY-042 | 2SP | 페이지네이션 포함 |
| 11 | 검색 필터 Tailwind 전환 + API 연동 | STORY-042 | 1SP | 문서유형, 날짜 필터 |
| 12 | SourceCitation 컴포넌트 구현 | STORY-042 | 1SP | 출처 문서 링크 |
| 13 | ReactMarkdown 패키지 추가 + 통합 | STORY-042 | 0.5SP | AI 응답 렌더링 |
| 14 | 단위 테스트 작성 (핵심 컴포넌트) | 전체 | 3SP | LoginForm, ChatSearch 등 |

### 8.4 우선순위 P3 (Sprint 4 이후)

| 순번 | 작업 | 관련 스토리 | 예상 공수 | 비고 |
|------|------|-----------|----------|------|
| 15 | 문서 업로드 기능 구현 | STORY-044(예정) | 3SP | 드래그 앤 드롭 |
| 16 | 문서 상세 페이지 구현 | - | 2SP | 문서 뷰어 |
| 17 | Knowledge Graph 시각화 | - | 5SP | D3.js 또는 vis.js |
| 18 | 다크 모드 토글 UI | - | 1SP | 설정에 추가 |
| 19 | 알림/토스트 시스템 | - | 1SP | react-hot-toast 등 |
| 20 | E2E 테스트 작성 | - | 3SP | Playwright 기반 |
| 21 | silent-check-sso.html 추가 | STORY-040 | 0.5SP | public/ 디렉토리 |

---

## 9. 기술적 권장사항

### 9.1 @tailwindcss/typography 플러그인 활성화

`tailwind.config.js`에 typography 설정은 있으나 plugins에 미포함:

```javascript
// 현재
plugins: [],

// 수정 필요
plugins: [
  require('@tailwindcss/typography'),
],
```

### 9.2 Headless UI 활용 확대

현재 Header.tsx의 Menu 컴포넌트만 사용. 설계서에서 권장하는 추가 활용:

| 컴포넌트 | 적용 대상 | 비고 |
|----------|----------|------|
| Dialog | 문서 업로드 모달, 삭제 확인 | 접근성 자동 지원 |
| Listbox | SearchFilters 드롭다운 | MUI Select 대체 |
| Tab | SearchPage 탭 | MUI Tabs 대체 |
| Disclosure | SearchFilters 확장/접기 | MUI Collapse 대체 |
| Transition | 전체 | 부드러운 전환 효과 |

### 9.3 번들 크기 최적화 예상 효과

MUI 제거 시 예상 번들 크기 절감:

| 패키지 | 예상 크기 (gzipped) |
|--------|-------------------|
| @mui/material | ~90KB |
| @mui/icons-material | ~40KB |
| @emotion/react | ~15KB |
| @emotion/styled | ~10KB |
| **총 절감** | **~155KB** |

### 9.4 React Query 활용 계획

실제 API 연동 시 다음 쿼리 키 구조 권장:

```typescript
['dashboard', 'stats']           // 대시보드 통계
['search', 'recent']             // 최근 검색 기록
['search', 'keyword', { query, filters, page }]  // 키워드 검색 결과
['documents', { page, filters }] // 문서 목록
['documents', documentId]        // 문서 상세
```

---

## 10. 결론

현재 프론트엔드 코드베이스는 **인프라(인증, 라우팅, 상태 관리, 빌드 설정)가 견고하게 구축**되어 있으며, 특히 **Keycloak + Direct Login 이중 인증 체계**와 **LoginPage/LoginForm의 완성도**가 높습니다.

그러나 **핵심 비즈니스 기능(검색, 대시보드, 지식관리)**은 아직 **껍데기 수준**이며, **MUI에서 Tailwind로의 마이그레이션이 절반만 완료**된 상태입니다. Sprint 3에서 이 GAP을 해소하기 위해 **MUI 전환 완료 -> SSE 구현 -> API 연동 -> 테스트** 순서로 진행하는 것을 권장합니다.

### 핵심 액션 아이템 (Top 5)

1. **[P0]** MUI -> Tailwind 전체 마이그레이션 완료 (7개 파일)
2. **[P1]** SSEClient + useStreamingSearch 구현 (STORY-043)
3. **[P1]** ChatSearch 재구현 with Tailwind + SSE (STORY-042)
4. **[P1]** Dashboard 실제 API 연동 + QuickSearch (STORY-041)
5. **[P1]** data-testid 속성 추가 + 핵심 단위 테스트 작성

---

*이 보고서는 Frontend Developer Agent에 의해 2026-01-26에 작성되었습니다.*
*설계서 기준 문서: STORY-040, STORY-041, STORY-042, STORY-043, API Integration Design, Hybrid RAG Platform Detailed Design*
