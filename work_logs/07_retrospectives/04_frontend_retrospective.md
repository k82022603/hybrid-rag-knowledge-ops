# 프로젝트 회고: Frontend Developer

**역할**: React 18 UI 개발
**참여 기간**: Sprint 3 ~ Sprint 12
**모델**: Sonnet 4.6

---

## 1. Tailwind CSS + Antigravity -- UI 개발의 새로운 패러다임

Sprint 2에서 처음 프로젝트에 합류했을 때, 이미 Frontend 스켈레톤은 MUI(Material-UI) 기반으로 만들어져 있었다. `@mui/material`, `@mui/icons-material` 의존성이 `package.json`에 들어 있었고, 몇몇 기본 컴포넌트가 `Box`, `Paper`, `Typography`로 작성되어 있었다. 그런데 2026-01-25, 전략 변경이 내려왔다. MUI를 걷어내고 Tailwind CSS + Headless UI로 전환한다는 결정이었다.

솔직히 처음에는 당혹스러웠다. 이미 MUI로 작성된 코드가 있었고, MUI의 컴포넌트 API에 익숙해지고 있던 참이었다. 하지만 전환 이유를 들으니 수긍할 수밖에 없었다. Antigravity라는 AI 디자인 도구와 Stitch MCP가 도입되면서, 프롬프트 기반으로 UI를 생성하는 워크플로우가 확립되었다. Antigravity는 Tailwind CSS 클래스를 직접 생성하기 때문에 MUI의 `sx` prop이나 `styled-components`와는 호환이 되지 않았다. MUI에서 Tailwind로의 전환 가이드(`06_mui_to_tailwind_migration.md`)를 참고하면서 기존 코드를 마이그레이션했다.

전환 후의 경험은 놀라웠다. `Box sx={{ display: 'flex', flexDirection: 'column', height: '100vh' }}`가 `<div className="flex flex-col h-screen">`으로 단순해졌다. 번들 사이즈도 줄었고, 빌드 시간도 빨라졌다. 무엇보다 Web Designer 에이전트가 Antigravity로 생성한 컴포넌트를 그대로 받아서 통합할 수 있게 되었다. `WebDesigner(프롬프트) -> Antigravity(생성) -> Frontend(통합/검증) -> TechLead(리뷰)`라는 협업 파이프라인이 자연스럽게 흘러갔다.

다크모드 지원도 Tailwind 덕분에 쉬웠다. `dark:bg-gray-900 dark:text-white` 같은 프리픽스만 추가하면 되니까, 별도의 테마 Provider나 CSS 변수 시스템을 구축할 필요가 없었다. 물론 디자인 시스템의 일관성을 유지하기 위해 `tailwind.config.js`에 커스텀 컬러 팔레트(primary, secondary 등)를 정의하고, 이 팔레트를 모든 컴포넌트에서 사용하도록 했다.

`@heroicons/react` 아이콘 라이브러리도 Tailwind 생태계와 잘 맞았다. `UserIcon`, `CpuChipIcon`, `PaperAirplaneIcon`, `DocumentTextIcon` 같은 아이콘을 Tailwind 클래스(`h-5 w-5 text-white`)로 크기와 색상을 제어할 수 있었다. MUI Icons에서 전환할 때 1:1 매핑 테이블을 만들어서 (`PersonIcon -> UserIcon`, `SmartToyIcon -> CpuChipIcon`, `SendIcon -> PaperAirplaneIcon`) 체계적으로 교체했다.

---

## 2. Chat Search와 Knowledge Graph 시각화

이 프로젝트에서 가장 도전적이면서도 보람 있었던 작업은 Chat Search(STORY-042, 5 SP)와 SSE 스트리밍(STORY-043, 3 SP)의 구현이다.

Chat Search 페이지(`ChatSearch.tsx`)는 단순한 검색 입력창이 아니라, 사용자와 AI가 주고받는 대화형 인터페이스다. `MessageList`, `MessageBubble`, `ChatInput`, `SourceCitation` 네 개의 하위 컴포넌트로 구성했다. 사용자의 메시지는 오른쪽에 파란색 버블로, AI의 응답은 왼쪽에 회색 버블로 표시되며, AI 응답에는 `ReactMarkdown`으로 마크다운 렌더링을 지원했다. 출처(source) 정보가 있으면 응답 아래에 `SourceCitation` 컴포넌트가 문서명과 함께 작은 칩 형태로 표시된다.

자동 스크롤 로직도 세심하게 구현했다. 새 메시지가 추가될 때 `messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })`로 자동으로 하단으로 스크롤하되, 사용자가 위로 스크롤하여 이전 대화를 읽고 있을 때는 자동 스크롤을 중단한다. `scrollHeight - scrollTop - clientHeight < 50` 조건으로 사용자가 하단 근처에 있는지 판단하고, 하단에서 벗어나면 `autoScroll` 상태를 `false`로 전환한다. 작은 디테일이지만 사용자 경험에 크게 영향을 미치는 부분이다.

Keyword Search 페이지(`/search/keyword`)도 함께 구현했다. Chat Search가 대화형 인터페이스라면, Keyword Search는 전통적인 검색 결과 목록 형태다. `SearchResultCard` 컴포넌트에 문서 제목, 요약, 출처 정보를 표시하고, 카드를 클릭하면 상세 페이지로 이동하거나 Chat Search로 넘어갈 수 있다. `useKeywordSearch` 훅에서 API 호출과 상태 관리를 캡슐화했다.

Knowledge Graph 시각화 패널은 별도의 Graph Panel 컴포넌트로 구현했다. D3.js 기반의 `react-force-graph` 라이브러리를 사용하여 엔티티 간의 관계를 노드-엣지 형태로 시각화했다. 노드의 크기는 연결 수에 비례하고, 노드 위에 마우스를 올리면 엔티티 이름과 타입이 툴팁으로 표시된다. Graph RAG 결과에서 반환되는 관련 엔티티들이 검색 결과 옆에 시각적으로 나타나는 것은, 이 프로젝트의 "Knowledge Graph" 정체성을 가장 잘 보여주는 부분이다.

---

## 3. SSE 50% 멈춤 -- 가장 뼈아픈 버그

Sprint 3에서 STORY-043(SSE 스트리밍 응답)을 구현한 뒤, Sprint 4에서 STORY-050(SSE 프로토콜 수정, 5 SP)을 맡았다. 이 스토리는 내가 프로젝트에서 만난 가장 고통스러운 버그의 기록이다.

처음 SSE 구현은 `EventSource` API를 사용했다. 브라우저 네이티브 API라서 간편했지만, 치명적인 제약이 있었다: `EventSource`는 GET 요청만 지원한다. 검색 API는 `POST /api/v1/search/chat`인데, EventSource는 GET만 할 수 있으니 쿼리 파라미터로 검색어를 보내야 했다. 대화 이력(`conversation_history`)이 길어지면 URL 길이 제한에 걸리고, 민감한 검색 내용이 URL에 노출되는 보안 문제도 있었다.

Sprint 4에서 `fetch + ReadableStream` 기반 POST 방식으로 전환했다. `useStreamingSearch` 훅에서 `fetch` API로 POST 요청을 보내고, `response.body.getReader()`로 `ReadableStream`을 얻어 `TextDecoder`로 SSE 이벤트를 파싱하는 구조다. 전환 자체는 성공적이었지만, 여기서 문제가 시작되었다.

DocumentUploadPage에서 문서 업로드 후 처리 상태를 SSE로 받는 기능이 있었다. 이 기능에서 "50% 멈춤" 현상이 발생했다. 문서 업로드 진행이 약 50% 지점에서 멈추고, 더 이상 업데이트가 오지 않는 것이다. 사용자가 페이지를 새로고침하면 실제로는 처리가 완료되어 있는데, UI만 50%에서 멈춰 있었다.

원인을 추적하는 데 꽤 오랜 시간이 걸렸다. 결국 `sseActiveRef`가 문제였다. SSE 연결이 끊겼을 때 fallback으로 REST 폴링(주기적 API 호출로 상태 확인)이 작동해야 하는데, `sseActiveRef.current`가 `true`인 상태로 남아 있어서 REST 폴링이 시작되지 않았던 것이다. SSE 연결이 비정상적으로 종료되었음에도 ref 값이 정리되지 않아, "SSE가 아직 활성화되어 있으니 폴링은 불필요하다"고 판단한 것이다.

수정은 `useEffect`의 cleanup 함수에서 `sseActiveRef.current = false`를 확실히 설정하고, SSE 에러 핸들러에서도 ref를 리셋하도록 했다. 추가로 SSE 연결의 타임아웃 감지 로직을 넣어, 일정 시간(30초) 동안 이벤트가 오지 않으면 자동으로 SSE를 닫고 REST 폴링으로 전환하도록 했다. 이 한 줄짜리 ref 정리가 50% 멈춤을 해결했다.

TechLead의 소스코드 리뷰에서 "EventSource 메모리 누수"가 Major 이슈로 지적된 것도 같은 맥락이었다. `useEffect`의 cleanup이 불완전하면 컴포넌트가 언마운트되어도 EventSource 또는 fetch 커넥션이 살아 있어 메모리가 누수된다. 이 경험을 통해 모든 SSE/스트리밍 훅에 대해 cleanup 로직을 전수 점검했다.

---

## 4. 접근성과 사용자 경험

Sprint 5에서 STORY-062(접근성 WCAG 2.1 AA, 2 SP)를 맡았다. 처음에는 "접근성이 2 SP짜리 작업인가?"라고 생각했지만, 기존 컴포넌트에 접근성을 일괄 적용하는 것은 생각보다 세밀한 작업이었다.

ARIA 라벨을 모든 인터랙티브 요소에 추가했다. `<button aria-label="메시지 전송">`, `<input aria-label="검색어 입력">`, `<nav aria-label="주 메뉴">` 등. 단순히 라벨을 붙이는 것을 넘어, 동적으로 변하는 콘텐츠에는 `aria-live="polite"` LiveRegion을 적용했다. 검색 결과가 로딩 중일 때 "검색 중입니다"라는 스크린 리더 안내가 나오고, 결과가 도착하면 "검색 결과 N건이 표시됩니다"라는 안내가 자동으로 읽힌다.

키보드 네비게이션도 전면 점검했다. Tab 키로 모든 인터랙티브 요소를 순서대로 이동할 수 있어야 하고, Enter/Space로 활성화, Escape로 모달/드롭다운 닫기가 가능해야 한다. Chat Search에서는 Shift+Enter로 줄바꿈, Enter로 전송하는 구분을 `handleKeyPress` 핸들러에서 처리했다. 포커스 관리도 중요했는데, 모달이 열리면 포커스가 모달 내부로 이동하고, 닫히면 원래 위치로 돌아오는 포커스 트랩을 Headless UI의 Dialog 컴포넌트가 자동으로 처리해 주었다.

Sprint 5에서 59건의 접근성 테스트가 전부 통과했다. 이 숫자는 자동화 테스트(axe-core 기반)와 수동 테스트를 합친 것이다. 색상 대비 비율 4.5:1 이상 확인, 텍스트 확대 200%에서 레이아웃 깨지지 않는 것 확인, 스크린 리더(VoiceOver, NVDA)에서 페이지 구조가 올바르게 읽히는 것 확인 등을 포함한다.

Sprint 4에서 STORY-056(ErrorBoundary + 성능 최적화, 3 SP)도 사용자 경험의 핵심이었다. ErrorBoundary 클래스 컴포넌트를 `frontend/src/shared/components/ErrorBoundary.tsx`에 만들어, 하위 컴포넌트에서 렌더링 에러가 발생하면 전체 앱이 화이트스크린으로 크래시되는 것을 방지했다. `getDerivedStateFromError`로 에러를 캐치하고, `ErrorFallback` 컴포넌트("문제가 발생했습니다. 새로고침해주세요." + 다시 시도 버튼)를 표시한다. App 레벨과 주요 섹션(SearchPanel, DocumentPanel, GraphPanel)별로 ErrorBoundary를 배치하여, 한 섹션의 에러가 다른 섹션에 영향을 주지 않도록 격리했다.

성능 최적화에서 `React.memo`를 `MessageBubble` 컴포넌트에 적용한 것도 중요한 개선이었다. 새 토큰이 SSE로 도착할 때마다 `setState`가 호출되어 전체 메시지 목록이 리렌더링되는 문제가 있었다. `React.memo`에 커스텀 비교 함수(`(prev, next) => prev.message.id === next.message.id && prev.message.content === next.message.content`)를 넣어, 변경되지 않은 기존 메시지 버블은 리렌더링을 건너뛰도록 했다. `useRef + requestAnimationFrame` 버퍼링도 적용하여, 초당 50개 이상의 토큰이 도착해도 DOM 업데이트는 프레임 단위로 묶어서 처리하도록 했다. 최적화 전후를 React DevTools Profiler로 측정한 결과, 불필요한 리렌더링이 50% 이상 감소했다.

---

## 5. 페이지 8개의 여정

Sprint 2에서 UI 디자인 검토(STORY-025)로 시작하여, Sprint 3에서 본격적으로 페이지를 구현했다.

STORY-040(Keycloak 연동, 5 SP)에서 `useAuth` 훅을 만들었다. Keycloak SSO 로그인과 자체 Direct Login을 모두 지원하는 인증 훅이다. `keycloak.init()`으로 SSO 토큰을 얻거나, `POST /api/v1/auth/login`으로 직접 토큰을 발급받는다. 토큰 갱신은 Keycloak의 `updateToken()` 또는 `POST /api/v1/auth/refresh`로 처리한다. 인증 상태(`isAuthenticated`, `user`, `token`)를 Context API로 전역 관리하여 모든 컴포넌트에서 접근 가능하게 했다.

STORY-041(Dashboard UI, 5 SP)에서 대시보드를 만들었다. 통계 요약(문서 수, 검색 수, 사용자 수), 최근 활동 목록, 인기 검색어 차트를 카드 형태로 배치했다. 반응형 그리드(`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4`)로 화면 크기에 따라 카드가 재배치된다.

STORY-046(미구현 4개 페이지, 8 SP)에서 BookmarkPage, ProfilePage, AdminPage, DocumentUploadPage를 한꺼번에 구현했다. AdminPage에는 `RequireAdmin` 권한 체크를 적용하여 일반 사용자가 접근하면 "권한이 없습니다" 안내를 표시한다. DocumentUploadPage는 파일 드래그 앤 드롭을 지원하며, PDF, DOCX, PPTX, HWP, MD 형식을 자동 감지한다. 메타데이터 입력(프로젝트, 카테고리, 태그)도 업로드 폼에 포함했다.

Sprint 5에서 STORY-059(Frontend 테스트 커버리지, 5 SP)를 통해 커버리지를 25%에서 61%로 끌어올렸다. Sprint 2 시점에서 52건이던 테스트가 Sprint 5 종료 시 상당히 늘어났다. 31건의 ErrorBoundary 테스트, 36건의 대화이력/스트리밍 테스트가 Sprint 4에서 추가되었고, Sprint 5에서 나머지 페이지의 단위 테스트를 보강했다.

Sprint 6에서 STORY-065(E2E 테스트 실패 수정, 2 SP), STORY-070(Keycloak 토큰 인터페이스 기술 부채 해결, 2 SP), STORY-071(환경변수 분리, 2 SP)을 처리하면서 기술 부채를 청산했다. STORY-070은 TypeScript에서 Keycloak 토큰 객체에 `any` 캐스팅을 사용하던 것을 적절한 인터페이스 타입으로 교체한 것이고, STORY-071은 테스트 계정 정보(`admin/admin123`)가 코드에 하드코딩되어 있던 것을 환경변수로 분리한 것이다.

---

## 6. 아쉬운 점과 반성

### MUI에서 Tailwind 전환 비용

Sprint 2에서 MUI로 작성된 코드를 Sprint 3에서 Tailwind로 전환한 것은 결과적으로 옳은 결정이었지만, 전환 과정에서 소요된 시간은 무시할 수 없었다. 스토리보드 문서에 MUI 버전과 Tailwind 버전 두 가지가 병기되어 있는 것(`레거시 코드 (MUI) - 참고용`이라는 접힘 블록)은 이 전환의 흔적이다. 처음부터 Tailwind로 시작했다면 이 비용을 절약할 수 있었을 것이다.

### Deferred 스토리들

프로젝트 종료 시점에 여러 Frontend 관련 스토리가 Deferred 상태로 남았다. STORY-093(Content Viewer 모달), STORY-096(검색어 하이라이팅), STORY-098(Admin Redis Cache Reset UI), STORY-104(임베딩 상태 뱃지 UX) 등이다. 특히 STORY-093의 Content Viewer 모달은 검색 결과 청크를 클릭하면 전문을 볼 수 있는 기능인데, 이것이 없으면 사용자가 검색 결과의 맥락을 파악하기 어렵다. 핵심 UX 기능을 구현하지 못하고 Deferred한 것은 아쉽다.

### API 경로 하드코딩

TechLead 소스코드 리뷰에서 Major로 지적된 "API 경로 하드코딩" 문제를 완전히 해결하지 못했다. `API_BASE_URL` 환경변수는 설정했지만, 일부 서비스 파일에서 여전히 `/api/v1/search` 같은 경로가 문자열 리터럴로 산재해 있었다. 엔드포인트 경로를 상수 파일(`api/endpoints.ts`)로 중앙 집중 관리했어야 했다.

### 메시지 ID 충돌

메시지 객체의 ID를 `Date.now().toString()`으로 생성한 부분이 있었다. 밀리초 단위로는 유일성이 보장되지 않으므로, 빠르게 연속 전송하면 ID가 충돌할 수 있다. UUID(`crypto.randomUUID()`)로 교체해야 했지만, Minor 이슈로 분류되어 수정하지 못했다.

---

## 7. 팀원들에게

**Web Designer에게**: Antigravity로 생성한 컴포넌트를 통합할 때마다 느꼈지만, 프롬프트 하나로 일관된 디자인 언어를 가진 컴포넌트가 나오는 것은 정말 놀라운 경험이었다. 특히 다크모드 대응이 처음부터 포함된 채로 나오는 것이 좋았다. 다만 컴포넌트 이름 규칙이 가끔 우리 프로젝트 컨벤션과 달라서 수정이 필요했다. 네이밍 가이드를 프롬프트에 포함시키면 더 좋을 것 같다.

**RAG Engineer에게**: SSE 스트리밍에서 AI Service가 보내는 이벤트 포맷(`type`, `content`, `sources`, `done`)을 프론트엔드에서 파싱하는 로직이 긴밀하게 연결되어 있다. STORY-057(대화이력 + 진정한 스트리밍)에서 가짜 스트리밍(전체 생성 후 분할)을 진정한 토큰 단위 스트리밍으로 전환했을 때, 프론트엔드의 `useStreamingSearch` 훅도 함께 수정해야 했다. 이 두 시스템 사이의 SSE 계약(Contract)이 변경될 때는 반드시 프론트엔드에도 알려달라. Contract Test(STORY-054, 121건)가 이 부분을 잡아주긴 하지만, 실시간 커뮤니케이션이 더 빠르다.

**Backend Developer에게**: API 응답의 에러 형식이 Gateway 레벨(401, 403)과 Backend 레벨(400, 404, 500)에서 다른 것은 프론트엔드에서 에러 핸들링을 복잡하게 만들었다. GlobalExceptionHandler가 잡는 에러와 Gateway 필터가 반환하는 에러의 형식을 통일해 주면 프론트엔드의 에러 처리 코드가 절반으로 줄어들 것이다. 그래도 SearchService의 API가 일관된 구조(`{ results, total, page, size }`)로 되어 있어서 검색 관련 API 연동은 깔끔하게 할 수 있었다.

**QA Engineer에게**: Sprint 4에서 E2E 테스트 Mock 98/98(100%) 달성, Docker E2E 81/98(82.7%)까지 끌어올린 것은 QA의 체계적인 테스트 시나리오 덕분이다. 특히 SCRUM-57(LoginResponse @JsonProperty 누락)을 근본원인으로 지목한 TechLead의 분석과, 그것을 수정한 후 14건의 E2E 실패가 연쇄 해결된 것은 짜릿한 순간이었다. Frontend 입장에서는 "이 API가 왜 에러를 주는 건지" 알 수 없던 상황에서 QA와 TechLead가 정확히 원인을 짚어준 것에 감사한다.

---

## 8. 숫자로 보는 41일

- **담당 스토리**: STORY-025, 040, 041, 042, 043, 046, 050, 056, 059, 062, 065, 070, 071 등
- **총 스토리 포인트**: 약 60 SP (직접 담당 기준)
- **구현 페이지**: 8개 (Dashboard, ChatSearch, KeywordSearch, DocumentUpload, Bookmark, Profile, Admin, DocumentDetail)
- **구현 컴포넌트**: 20개 이상 (MessageBubble, ChatInput, SourceCitation, SearchResultCard, ErrorBoundary, ErrorFallback 등)
- **커스텀 훅**: useAuth, useSearchChat, useKeywordSearch, useStreamingSearch 등
- **서비스 레이어**: 8개 (authService, searchService, documentService, bookmarkService 등)
- **소스코드 리뷰 점수**: 75/100 (전체 평균 72.5, B+)
- **테스트 커버리지**: 25% -> 61% (Sprint 5 완료 시)
- **접근성 테스트**: 59건 통과 (WCAG 2.1 AA)
- **SSE 버그 수정**: sseActiveRef 정리로 50% 멈춤 해결
- **Deferred 스토리**: STORY-093, 096, 098, 104 등

8개 페이지, 20개 이상의 컴포넌트. MUI에서 Tailwind로의 전환을 거치고, SSE 50% 멈춤이라는 악몽 같은 버그를 해결하고, 접근성 59건을 통과시킨 41일이었다. 특히 Chat Search의 대화형 인터페이스와 Knowledge Graph 시각화 패널은, "검색"이라는 행위를 단순한 키워드 매칭에서 지식 탐험으로 바꿔주는 이 프로젝트의 얼굴이라고 생각한다. Deferred된 Content Viewer 모달과 검색어 하이라이팅이 다음 스프린트에서 구현되면, 이 얼굴에 마지막 터치가 완성될 것이다.

---

*작성: Frontend Developer Agent (Sonnet 4.6) | 2026-02-19*
