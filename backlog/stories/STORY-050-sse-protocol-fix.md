# STORY-050: SSE 프로토콜 수정 (fetch+ReadableStream 전환)

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | (미정) |
| **Epic** | EPIC-003 |
| **Status** | To Do |
| **Priority** | Critical |
| **Story Points** | 5 |
| **Assignee** | Frontend |
| **Sprint** | 4 |

---

## User Story

**As a** 지식 검색 사용자,
**I want** SSE 스트리밍이 POST 방식으로 동작하여 대화 이력과 검색 파라미터를 안전하게 전달,
**So that** conversation_history, topK 등 복잡한 파라미터를 URL 노출 없이 전송하고 멀티턴 대화를 지원할 수 있음.

---

## Acceptance Criteria

- [ ] **Given** 검색 요청 시, **When** POST body에 query, conversation_history, topK 파라미터 포함, **Then** SSE 연결이 정상적으로 수립되고 스트리밍 응답 수신
- [ ] **Given** fetch+ReadableStream 기반 SSE 클라이언트, **When** 기존 useSearchChat 훅에서 호출, **Then** 기존 wrapper 인터페이스와 100% 호환
- [ ] **Given** SSE 연결 중 네트워크 오류 발생, **When** 연결이 끊김, **Then** 자동 재연결 로직이 최대 3회까지 동작
- [ ] **Given** POST SSE 연결 수립 후, **When** AI 응답이 생성됨, **Then** 토큰 단위 스트리밍이 정상 동작하고 [DONE] 이벤트로 완료 처리
- [ ] **Given** EventSource(GET) 코드, **When** fetch+ReadableStream(POST)으로 전환 완료, **Then** 기존 EventSource 코드 완전 제거

---

## Tasks

- [ ] fetch+ReadableStream 기반 SSE 클라이언트 클래스 구현 (SSEPostClient)
- [ ] POST body 직렬화 및 Content-Type 설정
- [ ] ReadableStream TextDecoder를 통한 SSE 이벤트 파싱 로직 구현
- [ ] 재연결(exponential backoff) 로직 구현
- [ ] useSearchChat 훅의 SSEClient 참조를 SSEPostClient로 교체
- [ ] 기존 EventSource 기반 SSEClient 코드 제거 또는 deprecation 처리
- [ ] AbortController를 활용한 취소 기능 구현
- [ ] 단위 테스트 작성 (연결, 파싱, 재연결, 취소)

---

## 기술 노트

### 문제점 (Sprint 03 리뷰에서 도출)

Sprint 03에서 구현한 SSE 스트리밍(STORY-043)은 `EventSource` API를 사용하는데, 이 API는 **GET 요청만 지원**한다. 따라서:

1. **conversation_history를 URL 쿼리 파라미터로 전달 불가** - 대화 이력이 길어지면 URL 길이 제한(약 2048자)에 걸림
2. **topK, filters 등 복잡한 파라미터 전달 제한** - JSON 객체를 URL 인코딩하면 가독성과 디버깅이 어려움
3. **보안 취약점** - JWT 토큰이 URL에 노출되어 서버 로그, 브라우저 히스토리에 기록됨

### 해결 방향

```typescript
// Before (EventSource - GET only)
const url = `/api/v1/search/chat/stream?query=${encodeURIComponent(query)}&token=${token}`;
const eventSource = new EventSource(url);

// After (fetch + ReadableStream - POST 지원)
const response = await fetch('/api/v1/search/chat/stream', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  },
  body: JSON.stringify({
    query,
    conversation_history: messages,
    top_k: topK,
  }),
  signal: abortController.signal,
});

const reader = response.body!.getReader();
const decoder = new TextDecoder();
```

### 영향 범위

- `frontend/src/shared/api/sse.ts` - SSEPostClient 신규 또는 교체
- `frontend/src/features/search/hooks/useSearchChat.ts` - SSE 클라이언트 교체
- `frontend/src/features/search/hooks/useStreamingSearch.ts` - 호환성 유지

---

## 테스트 계획

- [ ] Unit Test: SSEPostClient fetch+ReadableStream 연결/종료
- [ ] Unit Test: SSE 이벤트 파싱 (data:, event:, [DONE])
- [ ] Unit Test: 재연결 로직 (exponential backoff)
- [ ] Unit Test: AbortController 취소
- [ ] Integration Test: POST body에 conversation_history 포함 전송
- [ ] E2E Test: 전체 POST SSE 스트리밍 플로우

---

## 참고 자료

- Sprint 03 완료 리뷰에서 도출 - EventSource GET 제한 문제
- [STORY-043 SSE 스트리밍](./STORY-043-sse-streaming.md) - 기존 구현
- [Fetch API Streaming](https://developer.mozilla.org/en-US/docs/Web/API/Streams_API/Using_readable_streams)
