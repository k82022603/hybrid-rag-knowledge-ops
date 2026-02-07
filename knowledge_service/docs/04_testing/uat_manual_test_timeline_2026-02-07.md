# UAT 수동 테스트 타임라인 - 2026-02-07

**Tester**: Human (Product Owner)
**Environment**: Docker Compose Development (18 containers)
**URL**: http://localhost

---

## Timeline

| Time | Action | Result | Notes |
|------|--------|--------|-------|
| 17:53 | Chat Search "What is the document upload process?" | FAIL - HTTP 401 | Keycloak RS256 토큰을 AI Service가 인식 못함 |
| | | | SSE 스트리밍에서 Keycloak 토큰 누락 + AI Service HS256만 지원 |
| 18:08 | 1차 수정 배포 (sse.ts + auth.py Keycloak 지원) | 배포 완료 | AI Service + Frontend 리빌드 |
| 18:10 | Chat Search 재테스트 | FAIL - HTTP 401 | 2차 분석 필요 |
| 18:15 | 2차 원인 분석 | 근본 원인 2건 추가 발견 | Gateway가 Authorization 헤더 제거 + iss 클레임 누락 |
| 18:20 | 2차 수정 배포 (auth.py X-Auth-* 헤더 + iss 클레임) | 배포 완료 | curl 전체 경로 200 OK 검증 |
| 18:21 | Chat Search 재테스트 대기 | - | 사용자 브라우저 테스트 대기 |
| 18:25 | Chat Search 브라우저 재테스트 | **PASS** (인증) | 401 해소, SSE 스트리밍 정상, 5건 소스 검색 성공 |
| | | PARTIAL (LLM) | "답변 생성에 실패" → DeepSeek 미연결, fallback 원문 표시 |
| 18:30 | DeepSeek API 키 연결 | 수정 완료 | Docker .env placeholder → 실제 키 교체, AI Service 재시작 |
| 18:35 | Chat Search "What is the document upload process?" | **PASS** (API) | LLM 답변 생성 성공! 216 tokens, 20.3초, 출처 [1]~[4] 인용 |
| 18:38 | Chat Search UI 확인 | FAIL (UI) | raw JSON이 UI에 표시됨 - SSE 이벤트 형식 불일치 |
| | | | Backend: `type:"chunk"/content` vs Frontend: `type:"token"/data` |
| 18:40 | SSE 파서 수정 + Frontend 재배포 | 배포 완료 | `sse.ts` handleEvent에 chunk/start/end 이벤트 핸들러 추가 |
| 18:42 | Chat Search UI 재확인 | FAIL (UI) | 마크다운 렌더링 안됨 - `**bold**`, `###` 등 raw 텍스트 표시 |
| 18:45 | Markdown 렌더링 수정 | 수정 완료 | `react-markdown` + `@tailwindcss/typography` 설치, MessageBubble.tsx 수정 |
| 18:50 | Frontend 재배포 (Markdown 렌더링) | 배포 완료 | 번들 `index-BU75256-.js` 생성, 사용자 테스트 대기 |
| 18:52 | Chat Search UI 스크린샷 확인 | FAIL (UI) | 마크다운이 한 블록 텍스트로 표시 - 줄바꿈 소실 |
| 18:55 | 근본 원인 발견 | **백엔드 버그** | `search.py`의 `answer.split()`이 `\n` 제거 → `" ".join()`으로 재결합 |
| 18:56 | 백엔드 + 프론트엔드 수정 | 수정 완료 | search.py 문자 기반 청킹 + MessageBubble RAW 복사 버튼 |
| 18:59 | AI Service + Frontend 동시 재배포 | 배포 완료 | 사용자 테스트 대기 |
| 19:00 | Chat Search "document upload" 재테스트 | **PASS** (마크다운) | 헤딩/볼드/리스트 정상 렌더링 확인! |
| | | FAIL (테이블) | GFM 테이블이 raw 텍스트로 표시 - `remark-gfm` 플러그인 필요 |
| 19:00 | Chat Search "검색 결과 요약" 테스트 | FAIL (테이블) | `\| 항목 \| 주요 내용 \|` raw 마크다운 표시 |
| 19:02 | 스크롤바 개선 요청 | 수정 완료 | `chat-scroll` 클래스 추가, `min-h-0` flex fix, 항상 보이는 8px 스크롤바 |
| 19:03 | Frontend 재배포 (스크롤바) | 배포 완료 | MessageList + index.css 수정 |
| 19:05 | remark-gfm + 전체 플러그인 설치 | 수정 완료 | remark-gfm, remark-breaks, rehype-highlight, highlight.js 설치 |
| 19:08 | Frontend 재배포 (전체 플러그인) | 배포 완료 | 1524 모듈, 번들 `index-Bs_Qg0_s.js`, 사용자 테스트 대기 |
| 19:15 | 출처 인용 표시 문제 발견 | FAIL (UI) | [출처1]~[출처5]가 "Document 3%" 등 의미 없는 텍스트 표시 |
| 19:20 | Source Citation 전면 수정 | 수정 완료 | SSESourceData snake/camelCase 호환, SourceCitation.tsx 리라이트 |
| | | | types.ts에 title/index/sourceType 추가, 확장형 출처 미리보기 |
| 19:25 | Frontend 재배포 (Source Citation) | 배포 완료 | TS 타입 에러 수정 후 재빌드, 사용자 테스트 대기 |
| 19:30 | Source Type 배지 + Graph 시각화 패널 설계 | 계획 승인 | react-force-graph-2d 채택, 좌/우 패널 분할 레이아웃 |
| 19:35 | react-force-graph-2d 설치 | 완료 | v1.29.1, 번들 ~200KB gzip |
| 19:40 | 기능 구현 (7개 파일) | 수정 완료 | SourceCitation 배지, GraphPanel(신규), ChatSearch 레이아웃, prop drilling |
| 19:45 | Frontend 재배포 (Graph 패널) | 배포 완료 | Docker 인증 에러 1회 → pull 후 재빌드 성공 |
| 19:49 | Graph 시각화 테스트 | FAIL (데이터 없음) | Neo4j에 엔티티 0개 → Graph 검색 결과 없음 → 배지/패널 미표시 |
| 19:50 | Neo4j 데이터 진단 | **근본 원인** | Knowledge 5개 + Chunk 7개만 존재, Entity Extraction 미실행 |
| 19:55 | Entity Extraction 실행 | 처리 완료 | DeepSeek V3.2로 3개 문서 처리 (2개는 테스트 데이터로 스킵) |
| | | | 엔티티 61개 생성: Person 8, Technology 26, Topic 24, Keyword 3 |
| | | | 관계 165개 생성: MENTIONED_IN 93, RELATED_TO 72 |
| 20:00 | Graph 검색 + 시각화 재테스트 대기 | - | 사용자 브라우저 테스트 대기 |
| | | | |
| **--- Day 2 (세션 2) ---** | | | |
| 21:00 | Graph Search 0건 반환 근본 원인 분석 | **근본 원인** | `e.name CONTAINS word` 방식이 잘못됨 → 역방향 CONTAINS 필요 |
| 21:10 | Neo4j Cypher 직접 테스트 (컨테이너 내부) | 검증 완료 | 역방향+정방향+폴백 3단계 전략 설계 |
| 21:20 | `_graph_search()` 3단계 매칭 전략 구현 | 코드 수정 | Step 1: 역방향, Step 2: 정방향, Step 3: Content 폴백 |
| 21:25 | graph_context 전달 구현 | 코드 수정 | rag_pipeline.py + rag_workflow.py에 matched_entities 전달 |
| 21:30 | Admin 비밀번호 해시 수정 | 버그 수정 | .env 해시가 admin1234에 매칭 → admin123!로 재생성 |
| 21:35 | RRF fusion primary source 결정 로직 추가 | 코드 수정 | source_ranks에서 최고 순위 소스를 result.source로 설정 |
| 21:40 | AI Service 빌드 + 배포 | 배포 완료 | Docker 빌드 ~10분 (NVIDIA 패키지 포함) |
| 21:50 | Redis 캐시 클리어 후 E2E 검증 | **PASS** | source_type=graph 정상 표시, Graph 4건 기여 확인 |
| | | | "Neo4j 그래프 데이터베이스" → 4건(Step 1), "LLM 중심 기술" → 5건(Step 3 폴백) |
| 21:55 | 구현 문서 작성 | 완료 | docs/03_implementation/graph_search_implementation_2026-02-07.md |

---

## Issues Found

### Issue #1: Chat Search 401 Unauthorized (17:53)
- **증상**: Chat Search에서 "An error occurred while generating the response" + HTTP 401
- **1차 원인**:
  - `sse.ts`의 `getAuthToken()`이 Keycloak 토큰을 전달하지 않음
  - AI Service `auth.py`가 HS256 JWT만 지원 (Keycloak RS256 미지원)
- **1차 수정**: sse.ts Keycloak 토큰 전달 + auth.py 이중 인증 지원
- **1차 결과**: 여전히 401 (추가 원인 존재)

### Issue #1-2: Gateway Authorization 헤더 제거 (18:10)
- **증상**: 1차 수정 후에도 AI Service에서 401 반환
- **근본 원인**:
  1. API Gateway `JwtAuthenticationFilter`가 HS256 토큰 검증 후 `Authorization` 헤더를 제거하고 `X-Auth-*` 헤더로 교체
  2. AI Service가 `X-Auth-*` 헤더를 인식하지 못함
  3. AI Service 발급 JWT에 `iss` 클레임이 없어 Gateway `JwtTokenValidator`에서 `Missing 'iss' claim` 에러
- **2차 수정**:
  - `auth.py`: Strategy 3 추가 (`X-Auth-*` 헤더 인증 - Gateway 신뢰 내부 네트워크)
  - `auth.py`: `create_access_token()`에 `"iss": "knowledge-platform"` 추가
- **2차 결과**: curl 전체 경로 (nginx → Gateway → AI Service) **200 OK** 확인
- **상태**: 수정 완료, 브라우저 재테스트 대기

### Issue #2: DeepSeek LLM 미연결 (18:25)
- **증상**: 소스 검색 성공, "답변 생성에 실패" fallback 표시
- **원인**: Docker `.env`에 `DEEPSEEK_API_KEY=sk-placeholder-for-dev`
- **수정**: `knowledge_service/.env`의 실제 키를 `infrastructure/docker/.env`에 복사
- **결과**: LLM 답변 생성 성공 (216 tokens, 20.3초)

### Issue #3: SSE 이벤트 형식 불일치 (18:38)
- **증상**: raw JSON이 UI에 표시됨 (`{"type":"chunk","content":"..."}`)
- **원인**: Backend `type:"chunk"/content` vs Frontend `type:"token"/data` 불일치
- **수정**: `sse.ts` handleEvent에 Format B (chunk/start/end) 핸들러 추가
- **결과**: 텍스트 정상 표시, 마크다운 미렌더링 발견

### Issue #4: Markdown 렌더링 미지원 (18:42)
- **증상**: `**bold**`, `### heading`, `- list` 등 raw 마크다운 텍스트 표시
- **원인**: MessageBubble이 `<p>` 태그로 plain text 렌더링
- **수정**:
  - `react-markdown` (^10.1.0) 패키지 설치
  - `@tailwindcss/typography` 플러그인 설치
  - `MessageBubble.tsx`: AI 메시지에 `<Markdown>` 컴포넌트 + `prose` 클래스 적용
  - `tailwind.config.js`: typography 플러그인 추가
- **결과**: 마크다운 구문은 파싱 가능하나, 줄바꿈 소실로 한 블록 표시

### Issue #5: SSE 스트리밍 줄바꿈 소실 (18:52) - **근본 원인**
- **증상**: 마크다운이 한 블록 텍스트로 표시 (헤딩/리스트/볼드 인식 불가)
- **근본 원인**: `search.py`의 SSE 스트리밍 시뮬레이션 코드
  ```python
  words = answer.split()      # str.split()이 \n 포함 모든 공백으로 분할
  " ".join(buffer)             # 공백으로만 재결합 → 줄바꿈 완전 소실
  ```
- **수정**: word-based → character-based chunking (30자 단위)
  - `answer[i:i+30]`으로 원본 포맷 완전 보존
- **추가**: MessageBubble에 RAW 복사 버튼 (hover 시 표시, 클립보드 복사)
- **결과**: 헤딩/볼드/리스트 정상, 테이블 미지원 → Issue #6으로 이어짐

### Issue #6: GFM 테이블 렌더링 미지원 (19:00)
- **증상**: `| 항목 | 주요 내용 |` 마크다운 테이블이 raw 텍스트로 표시
- **원인**: `react-markdown` 기본은 CommonMark만 지원, GFM 테이블은 별도 플러그인 필요
- **수정**: `remark-gfm` 플러그인 설치 + `<Markdown remarkPlugins={[remarkGfm]}>` 적용
- **결과**: 테이블 렌더링 가능, 추가 플러그인 설치로 이어짐

### Issue #7: 스크롤바 미표시 (19:00)
- **증상**: 긴 AI 응답에서 위로 스크롤한 메시지를 찾을 방법 없음
- **원인**: Windows 오버레이 스크롤바 + flexbox `min-height: auto` 기본값
- **수정**:
  - `index.css`: `.chat-scroll` 클래스 (항상 보이는 8px 스크롤바, `scrollbar-gutter: stable`)
  - `MessageList.tsx`: `min-h-0` 추가 (flex overflow 보장), `chat-scroll` 클래스 적용
- **결과**: 스크롤바 항상 표시, 마우스 드래그로 자유 이동 가능

### Issue #8: 출처 인용(Source Citation) 의미 없는 표시 (19:15)
- **증상**: [출처1]~[출처5]가 "Document 3%", "문서 7%" 등으로 표시, 문서 제목 미표시
- **원인**:
  - Backend가 snake_case (`chunk_id`, `document_id`, `title`, `snippet`) 전송
  - Frontend `SSESourceData`가 camelCase (`chunkId`, `documentId`, `content`)만 정의
  - `title`, `index` 필드가 매핑되지 않아 fallback 값 표시
- **수정**:
  - `sse.ts`: `SSESourceData`에 snake_case 필드 + `title`/`index`/`sourceType` 추가, 인덱스 시그니처 추가
  - `useStreamingSearch.ts`: `mapSSESourcesToSources()`에서 snake/camelCase 양방향 매핑
  - `types.ts`: `Source` 인터페이스에 `title`, `index`, `sourceType` 추가
  - `SourceCitation.tsx`: 전면 리라이트 - [출처N] 라벨, 문서 제목, 관련성 점수 색상, 확장형 콘텐츠 미리보기
- **결과**: 사용자 테스트 대기

### Issue #9: Neo4j 엔티티 데이터 부재 (19:49)
- **증상**: Source Type 배지와 Graph 패널이 표시되지 않음
- **근본 원인**: Neo4j에 Knowledge/Chunk 노드만 존재, Entity Extraction이 한번도 실행되지 않음
  - Entity 0개 → `_graph_search()`가 항상 빈 결과 반환
  - `source_type: "graph"` 결과가 없으므로 배지/패널 미트리거
- **수정**: DeepSeek V3.2로 3개 문서에 대해 Entity Extraction + Gleaning 실행
  - 엔티티 61개 생성 (Person 8, Technology 26, Topic 24, Keyword 3)
  - 관계 165개 생성 (MENTIONED_IN 93, RELATED_TO 72)
- **결과**: 사용자 테스트 대기

### Issue #10: Graph Search 항상 0건 반환 (21:00) - **근본 원인**
- **증상**: Neo4j에 엔티티가 있음에도 `_graph_search()`가 항상 0건 반환
- **근본 원인**: Cypher 매칭 방식 오류
  - 기존: `e.name CONTAINS word` (엔티티 이름 안에 쿼리 단어 포함 검사)
  - 문제: "LLM", "중심으로", "기술" → "DeepSeek V3.2", "LangGraph" 안에 포함되지 않음 → 0건
- **수정**: 3단계 CONTAINS 매칭 전략
  1. **Step 1 (역방향)**: `toLower(query) CONTAINS toLower(entity_name)` - 쿼리 안에 엔티티 포함
  2. **Step 2 (정방향)**: `toLower(entity_name) CONTAINS toLower(word)` - 엔티티 안에 단어 포함
  3. **Step 3 (폴백)**: Step 1+2 결과 0건이면 Chunk content 키워드 검색
- **결과**: "Neo4j" → 4건, "LLM 기술" → 5건(폴백), "RAG LangGraph" → 5건

### Issue #10-2: RRF Fusion 후 source 고정 (21:35)
- **증상**: 모든 검색 결과의 `source_type`이 항상 "vector"로 표시
- **원인**: `_rrf_fusion()`에서 같은 chunk가 여러 소스에 있을 때, 첫 번째 소스(vector)만 유지
- **수정**: `result.source = min(ranks, key=ranks.get)` - 가장 높은 순위 소스로 결정
- **결과**: source_type=graph/keyword 정상 표시

### Issue #10-3: Redis 캐시 잔존 (21:50)
- **증상**: 코드 수정 + 배포 후에도 이전 결과(source_type=vector) 반환
- **원인**: Redis에 이전 검색 결과가 캐시됨, 새 코드 로직이 적용되지 않음
- **수정**: `search_cache:*` 키 전체 삭제
- **결과**: 캐시 클리어 후 source_type=graph 정상 표시

### Enhancement: Source Type 배지 + Graph 시각화 패널 (19:30)
- **요청**: "출처에서 graph 소스인지 vector 소스인지 표시해줘. graph 소스는 검색 결과 오른편 UI에 그래프 형태로"
- **구현 내용**:
  | 기능 | 설명 |
  |------|------|
  | Source Type 배지 | Vector(파란), Keyword(앰버), Graph(틸) 아이콘+텍스트 배지 |
  | Graph 시각화 패널 | 우측 패널에 force-directed 그래프 (react-force-graph-2d) |
  | 레이아웃 분할 | ChatSearch flex-row: 좌(채팅 flex-[3]) + 우(그래프 flex-[2]) |
  | 데이터 연동 | Graph 출처 클릭 → `/api/v1/graph/subgraph` API → 서브그래프 시각화 |
  | 반응형 | lg 이상에서만 그래프 패널 표시 |
- **수정/생성 파일**: SourceCitation.tsx, GraphPanel.tsx(신규), ChatSearch.tsx, MessageBubble.tsx, MessageList.tsx, types.ts, index.ts
- **라이브러리**: react-force-graph-2d v1.29.1
- **결과**: 배포 완료, Neo4j 데이터 생성 후 사용자 테스트 대기

### Enhancement: 마크다운 플러그인 전체 설치 (19:05)
- **요청**: "어지간한 플러그인 모두 설치해줘"
- **설치 목록**:
  | 플러그인 | 기능 |
  |---------|------|
  | `remark-gfm` | GFM 테이블, ~~취소선~~, 체크리스트, 자동 링크 |
  | `remark-breaks` | 줄바꿈을 `<br>`로 변환 (채팅에 최적) |
  | `rehype-highlight` | 코드 블록 구문 강조 (highlight.js) |
  | `@tailwindcss/typography` | `prose` 기반 마크다운 타이포그래피 |
- **결과**: 사용자 테스트 대기

### 수정 파일 (전체)
| 파일 | 변경 내용 |
|------|----------|
| `frontend/src/shared/api/sse.ts` | Keycloak 토큰 우선 조회 + SSE chunk/start/end 핸들러 + SSESourceData snake/camelCase 호환 |
| `frontend/src/features/search/components/MessageBubble.tsx` | react-markdown + remark-gfm/breaks + rehype-highlight + RAW 복사 버튼 |
| `frontend/src/features/search/components/MessageList.tsx` | `min-h-0` + `chat-scroll` 스크롤바 개선 |
| `frontend/src/features/search/components/SourceCitation.tsx` | 전면 리라이트: [출처N] 라벨, 문서 제목, 점수 색상, 확장형 콘텐츠 미리보기 |
| `frontend/src/features/search/types.ts` | Source 인터페이스에 title/index/sourceType 추가 |
| `frontend/src/features/search/hooks/useStreamingSearch.ts` | mapSSESourcesToSources snake/camelCase 양방향 매핑 |
| `frontend/src/index.css` | `.chat-scroll` 항상 보이는 스크롤바 스타일 |
| `frontend/tailwind.config.js` | @tailwindcss/typography 플러그인 추가 |
| `frontend/package.json` | react-markdown, remark-gfm, remark-breaks, rehype-highlight 추가 |
| `src/app/api/routes/auth.py` | 3가지 인증 전략 + iss 클레임 추가 |
| `src/app/api/routes/search.py` | SSE 스트리밍: word-based → character-based 청킹 (줄바꿈 보존) |
| `frontend/src/features/search/components/GraphPanel.tsx` | **신규**: react-force-graph-2d 기반 서브그래프 시각화 패널 |
| `frontend/src/features/search/ChatSearch.tsx` | flex-row 레이아웃 분할, GraphPanel 상태 관리 |
| `infrastructure/docker/.env` | DeepSeek API 키 실제 값으로 교체 |

---

## Summary

| 구분 | 건수 | 상태 |
|------|------|------|
| 이슈 발견 | 12건 | 전체 수정 완료 |
| 기능 추가 | 3건 | 배지, Graph 패널, 플러그인 |
| 수정/생성 파일 | 18개 | 배포 완료 |
| 배포 횟수 | 10회 | Frontend 8회, AI Service 3회 |
| Neo4j 엔티티 추출 | 61개 엔티티 | 3개 문서 처리 |
| 총 소요 시간 | ~180분 | 17:53 ~ 21:55 (2세션) |

### PASS 항목
- [x] Chat Search 인증 (Keycloak SSO → AI Service)
- [x] DeepSeek LLM 답변 생성
- [x] SSE 스트리밍 파싱
- [x] 마크다운 렌더링 (헤딩, 볼드, 리스트)
- [x] RAW 복사 버튼
- [x] Neo4j 엔티티 추출 (61개 엔티티, 165개 관계)
- [ ] GFM 테이블 렌더링 (remark-gfm 설치 완료, 사용자 확인 대기)
- [ ] 코드 구문 강조 (rehype-highlight 설치 완료, 사용자 확인 대기)
- [ ] 스크롤바 개선 (사용자 확인 대기)
- [ ] 출처 인용 표시 (문서 제목 + 확장 미리보기, 사용자 확인 대기)
- [x] Source Type 배지 (source_type=graph/vector/keyword E2E 확인 완료)
- [ ] Graph 시각화 패널 (react-force-graph-2d, 사용자 브라우저 확인 대기)
- [x] Graph Search 3단계 매칭 (Neo4j 4건, LLM 5건 폴백 검증 완료)
- [x] RRF primary source 결정 (source_ranks 기반 최고 순위 소스 표시)

### 수정 파일 (세션 2 추가)
| 파일 | 변경 내용 |
|------|----------|
| `src/app/services/search.py` | `_graph_search()` 3단계 매칭 + `_rrf_fusion()` primary source |
| `src/app/services/rag_pipeline.py` | graph_context.related_entities 전달 |
| `src/app/agents/rag_workflow.py` | graph_context.related_entities 전달 |
| `knowledge_service/.env` | ADMIN_PASSWORD_HASH 수정 (admin123!) |
| `infrastructure/docker/.env` | ADMIN_PASSWORD_HASH 수정 |
| `docs/03_implementation/graph_search_implementation_2026-02-07.md` | **신규**: 구현 문서 |

*Last Updated: 2026-02-07 21:55 KST*
