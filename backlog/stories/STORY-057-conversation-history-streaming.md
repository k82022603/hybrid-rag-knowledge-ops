# STORY-057: Generator 대화이력 전달 + 진정한 스트리밍

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | (미정) |
| **Epic** | EPIC-002 |
| **Status** | To Do |
| **Priority** | High |
| **Story Points** | 5 |
| **Assignee** | RAG |
| **Sprint** | 4 |

---

## User Story

**As a** 지식 검색 사용자,
**I want** 이전 대화 맥락이 유지된 응답을 받고, 응답이 토큰 단위로 실시간 스트리밍,
**So that** 자연스러운 멀티턴 대화가 가능하고 긴 응답도 첫 토큰부터 빠르게 확인할 수 있음.

---

## Acceptance Criteria

- [ ] **Given** 3턴 이상의 대화 이력이 있는 상태에서 새 질문 전송, **When** Generator가 응답 생성, **Then** 이전 대화 맥락을 반영한 응답 생성 (예: "앞서 말씀드린...")
- [ ] **Given** 검색 요청 전송, **When** Generator 응답 시작, **Then** 첫 토큰 응답 시간(TTFT) < 1초
- [ ] **Given** 현재 가짜 스트리밍(전체 생성 후 청크 전송), **When** 진정한 스트리밍으로 전환 완료, **Then** LLM이 토큰을 생성하는 즉시 클라이언트에 전달
- [ ] **Given** conversation_history가 프롬프트에 포함됨, **When** 이력이 길어짐, **Then** 최근 N턴만 포함하여 토큰 한도 초과 방지
- [ ] **Given** 스트리밍 중 LLM 에러 발생, **When** 응답 생성 실패, **Then** 클라이언트에 에러 이벤트 전송 및 graceful 종료

---

## Tasks

- [ ] GeneratorNode 프롬프트 템플릿에 conversation_history 슬롯 추가
- [ ] conversation_history를 LangGraph State에서 GeneratorNode로 전달하는 경로 구현
- [ ] 대화 이력 길이 제한 로직 (최근 5턴 또는 토큰 수 기반 truncation)
- [ ] LLM 호출을 streaming=True 모드로 전환 (DeepSeek V3.2)
- [ ] AsyncGenerator를 통한 토큰 단위 yield 구현
- [ ] SSE 엔드포인트에서 AsyncGenerator 소비하여 실시간 전송
- [ ] 가짜 스트리밍 코드 제거 (전체 생성 후 분할 로직)
- [ ] TTFT(Time To First Token) 측정 로깅 추가
- [ ] 에러 이벤트 핸들링 (LLM 타임아웃, 연결 실패)

---

## 기술 노트

### 문제점 (Sprint 03 리뷰에서 도출)

Sprint 03 RAG 파이프라인에서 두 가지 핵심 문제가 식별됨:

1. **대화 이력 미전달** - Generator 프롬프트에 현재 질문과 검색 결과만 포함, conversation_history 없음. 따라서 멀티턴 대화가 불가능
2. **가짜 스트리밍** - LLM이 전체 응답을 생성한 후 청크로 분할하여 전송. TTFT가 전체 생성 시간과 동일하여 사용자 체감 지연 큼

### 해결 방향

#### 대화 이력 프롬프트

```python
# Before (단일 턴)
prompt = f"""
Context: {retrieved_docs}
Question: {query}
Answer:
"""

# After (멀티턴)
prompt = f"""
대화 이력:
{format_conversation_history(conversation_history[-5:])}

검색된 문서:
{retrieved_docs}

현재 질문: {query}
답변:
"""
```

#### 진정한 스트리밍

```python
# Before (가짜 스트리밍)
async def generate(self, query, docs):
    full_response = await self.llm.generate(prompt)  # 전체 생성 대기
    for chunk in split_chunks(full_response, chunk_size=20):
        yield chunk  # 생성 완료 후 분할 전송

# After (진정한 스트리밍)
async def generate(self, query, docs, conversation_history):
    async for token in self.llm.astream(prompt):  # 토큰 단위 yield
        yield token  # LLM이 생성하는 즉시 전달
```

### 대화 이력 관리

```
conversation_history 길이 제한:
- 방법 1: 최근 5턴만 포함
- 방법 2: 토큰 수 기반 (예: 최대 2000 토큰)
- 방법 3: 하이브리드 (턴 수 + 토큰 수 둘 다 제한)
```

### 영향 범위

- `ai_service/nodes/generator_node.py` - 프롬프트 + 스트리밍 전환
- `ai_service/workflow/langgraph_workflow.py` - State에 conversation_history 추가
- `ai_service/api/routes/search.py` - SSE 엔드포인트 AsyncGenerator 소비
- `ai_service/services/llm_client.py` - streaming=True 설정

---

## 테스트 계획

- [ ] Unit Test: conversation_history가 프롬프트에 포함되는지 확인
- [ ] Unit Test: 대화 이력 truncation 로직 (5턴 제한)
- [ ] Unit Test: AsyncGenerator가 토큰 단위로 yield
- [ ] Performance Test: TTFT < 1초 측정
- [ ] Integration Test: 멀티턴 대화 시나리오 (3턴 이상)
- [ ] E2E Test: Frontend에서 멀티턴 대화 + 실시간 스트리밍

---

## 참고 자료

- Sprint 03 완료 리뷰에서 도출 - 대화 이력 미전달, 가짜 스트리밍
- [STORY-033 LangGraph Workflow](./STORY-033-langgraph-workflow.md)
- [STORY-043 SSE 스트리밍](./STORY-043-sse-streaming.md)
- [DeepSeek API Streaming](https://platform.deepseek.com/docs)
