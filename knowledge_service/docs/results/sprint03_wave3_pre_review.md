# Sprint 03 Wave 3 Pre-Implementation Tech Review

**Reviewer**: TechLead Agent  
**Date**: 2026-01-28  
**Sprint**: Sprint 03, Wave 3  
**Review Type**: Pre-Implementation Architecture + Code Quality + Integration Risk + Tech Debt  
**Stories**: STORY-033 (LangGraph Workflow, 8SP) + STORY-043 (SSE Streaming, 3SP)

---

## Executive Summary

| 검토 영역 | 상태 | 요약 |
|-----------|------|------|
| LangGraph 통합 포인트 | **REVIEW** | VIPAgent 스켈레톤 존재, 실질 구현 필요 |
| SSE 스트리밍 아키텍처 | **PARTIAL** | Backend SSE 구현 완료, Frontend 기초 패턴 존재, 강화 필요 |
| HybridRetriever 품질 | **PASS (A)** | 3-source RRF + Reranking, 견고한 에러 핸들링 |
| Frontend Search 품질 | **PASS (B+)** | 기본 SSE 패턴 동작, 누락 기능 식별됨 |
| 통합 리스크 | **MEDIUM** | Backend-Frontend SSE 프로토콜 불일치 발견 |
| 기술 부채 | **12 -> 16건** | 신규 4건 (TECH-DEBT-013~016) |

**전체 판정**: Wave 3 구현 **조건부 진행 가능(Proceed with Caution)** - 아래 권고사항 반영 필수

---

## 1. Architecture Analysis

### 1.1 LangGraph Integration Points (STORY-033)

#### 현재 상태

VIPAgent (`knowledge_service/src/app/agents/vip_agent.py`) 스켈레톤이 존재하며 아래 구조를 가짐:

```
VIPAgent.build_graph()
  -> extract_entities (Stage 1: Value)      # TODO - 스켈레톤
  -> gleaning (Stage 1: Value)              # TODO - 스켈레톤
  -> hybrid_search (Stage 2: Intelligent)   # TODO - 스켈레톤
  -> rrf_fusion (Stage 2: Intelligent)      # TODO - 스켈레톤
  -> synthesize_answer (Stage 3: Planning)  # TODO - 스켈레톤
```

**AgentState** (`knowledge_service/src/app/agents/state.py`):
- TypedDict 기반 상태 스키마 정의 완료 (100줄)
- VIP 3단계 필드 전부 포함: query, entities, search_results, fused_results, reranked_results, answer, sources
- LangGraph `StateGraph(AgentState)` 호환 확인됨

#### STORY-033 설계서 vs 현재 구현 Gap Analysis

| 설계서 노드 | 현재 구현 | Gap |
|------------|----------|-----|
| **Planner** (전략 결정) | VIPAgent._extract_entities (스켈레톤) | Planner 노드가 VIPAgent에 없음. 별도 노드 분리 필요 |
| **Retriever** (검색 실행) | VIPAgent._hybrid_search (스켈레톤) | HybridRetriever.retrieve() 호출로 연결 필요 |
| **Generator** (답변 생성) | VIPAgent._synthesize_answer (스켈레톤) | RAGPipeline.generate_answer() 위임 필요 |
| **Validator** (품질 검증) | **미존재** | STORY-033 AC에 Faithfulness/Relevance 검증 명시 - 신규 노드 필요 |
| **스트리밍** | StateGraph.astream() 미사용 | workflow.astream() 활용 필요 |

#### 아키텍처 일관성 검증

```
설계서 흐름:
  Planner -> Retriever -> Generator -> Validator -> (실패) Retriever 재검색
                                                  -> (성공) END

현재 VIPAgent 흐름:
  extract_entities -> [gleaning|search] -> hybrid_search -> rrf_fusion -> synthesize_answer -> END
```

**불일치 사항**:

1. **Planner 노드 부재**: 설계서는 Planner가 검색 전략을 결정하지만, VIPAgent는 항상 hybrid 고정.
2. **Validator 노드 부재**: STORY-033 AC에 Faithfulness/Relevance 검증이 명시되었으나 현재 그래프에 없음.
3. **Reranking 미연결**: reranked_results 필드는 있으나 HybridRetriever.retrieve(use_reranking=True) 위임으로 해결 가능.
4. **AgentState 이중 정의 위험**: 설계서가 ai_service에 신규 state.py 지시하나, knowledge_service에 이미 존재.

#### 권고사항 (LangGraph)

| # | 권고 | 우선순위 | 근거 |
|---|------|---------|------|
| R-01 | Planner 노드 추가: LLM 기반 검색 전략 결정 | **High** | STORY-033 AC2 |
| R-02 | Validator 노드 추가: Faithfulness/Relevance 검증 | **High** | STORY-033 AC5-AC6 |
| R-03 | AgentState 통합: agents/state.py 하나만 사용 | **High** | 이중 정의 방지 |
| R-04 | HybridRetriever 직접 연동: Retriever 노드에서 호출 | **Medium** | ADR-001 위임 패턴 유지 |
| R-05 | astream() 활용: 스트리밍 모드 지원 | **Medium** | STORY-033 AC4 |

### 1.2 SSE Streaming Architecture (STORY-043)

#### Backend SSE (현재 구현 완료)

**파일**: `knowledge_service/src/app/api/routes/search.py` (L325-389)

```
POST /chat/stream
  -> generate() async generator
    -> search_service.hybrid_search()
    -> rag_pipeline.generate_stream()
      -> SSE Events: start, chunk, error, end
  -> StreamingResponse(media_type="text/event-stream")
```

**강점**: FastAPI StreamingResponse + async generator, SSE 이벤트 타입 분리, graceful degradation, 적절한 헤더 설정

**약점**:
- `generate_stream()`이 전체 답변 생성 후 문장 분할하는 "가짜 스트리밍" (L309-323) -> TECH-DEBT-013
- POST 요청이나 Frontend는 GET EventSource 사용 -> **프로토콜 불일치**

#### Frontend SSE (현재 구현 분석)

**STORY-043 설계서 대비 누락 기능**:

| 설계서 AC | 현재 구현 | 누락 |
|----------|----------|------|
| AC1: 토큰 단위 실시간 표시 | 문장 단위 스트리밍 | 토큰 단위 미구현 |
| AC2: 기존 응답에 추가 | msg.content + data 방식 | **구현됨** |
| AC3: [DONE] 시 출처 표시 | [DONE] 감지 완료, 출처 미표시 | 출처 파싱 누락 |
| AC4: 자동 재연결 3회 | **미구현** | SSEClient 재연결 로직 필요 |
| AC5: 사용자 취소 | EventSource.close() 가능 | 취소 UI 버튼 미구현 |

---

## 2. Code Quality Review (Existing)

### 2.1 HybridRetriever (`knowledge_service/src/app/rag/retriever.py`)

| 메트릭 | 평가 | 상세 |
|--------|:----:|------|
| **Docstring** | A | 모든 클래스/메서드에 Google-style docstring |
| **Type Hints** | A | Optional, List, Dict 전수 적용 |
| **에러 핸들링** | A | try/except + fallback 검색 + return_exceptions |
| **로깅** | A | 시작/완료/실패 3단계 로깅 + latency 측정 |
| **DI/테스트** | A | SearchService 주입 + reset_hybrid_retriever() |
| **SOLID** | A- | SRP 우수, OCP는 search_type 확장 시 수정 필요 |

**LangGraph 연동 준비도**: A- (aretrieve() 비동기 인터페이스 제공, entities 어댑터 필요)

### 2.2 BGEReranker (`ai_service/src/reranking/bge_reranker.py`)

| 메트릭 | 평가 | 상세 |
|--------|:----:|------|
| **Docstring** | A | Example 포함 상세 문서화 |
| **Type Hints** | A | RerankResult dataclass 포함 |
| **에러 핸들링** | A | RuntimeError/ValueError 명확 분리 |
| **배치 처리** | A | _batch_process() 메모리 효율적 |
| **호환성** | B+ | SearchResult 직접 처리 가능하나 Any 타입 사용 |

**주의**: _batch_process() 동기 CPU 바운드를 async에서 직접 호출 -> TECH-DEBT-014

### 2.3 RAGPipeline (`knowledge_service/src/app/services/rag_pipeline.py`)

| 메트릭 | 평가 | 상세 |
|--------|:----:|------|
| **Docstring** | A | 모든 메서드 문서화 |
| **스트리밍** | B | 가짜 스트리밍 (전체 생성 후 문장 분할) |
| **프롬프트** | A | 한국어 시스템 프롬프트 + 출처 지시 |
| **컨텍스트 관리** | A | max_length/max_chunks 제한 + 잘림 처리 |

### 2.4 Frontend Search Components

| 컴포넌트 | 파일 | 평가 | 상세 |
|----------|------|:----:|------|
| ChatSearch | ChatSearch.tsx | A- | 컴포지션 패턴 우수, AC 5개 중 4개 충족 |
| MessageList | MessageList.tsx | A | auto-scroll + manual override + a11y |
| MessageBubble | MessageBubble.tsx | A- | dark mode, streaming indicator 포함 |
| useSearchChat | useSearchChat.ts | B+ | 기본 SSE 동작, 재연결/취소 미구현 |
| searchService | searchService.ts | B | GET EventSource, POST 백엔드와 불일치 |
| types.ts | types.ts | A | Source, Message, SearchFilters 명확 |

**접근성 (a11y)**: MessageList role=log/aria-live/aria-label 적용 우수

---

## 3. Integration Risks

### 3.1 AI Service <-> Knowledge Service

| 리스크 | 심각도 | 설명 | 대응 |
|--------|:------:|------|------|
| AgentState 이중 정의 | **High** | STORY-033이 ai_service에 state.py 신규 생성 지시하나 knowledge_service에 이미 존재 | 하나로 통합 |
| HybridRetriever 서비스 경계 | **Medium** | VIPAgent가 HybridRetriever를 직접 import하면 서비스 경계 침범 | REST API 간접 호출 또는 공유 라이브러리 |
| Reranker 직접 의존 | **Low** | HybridRetriever가 reranker 내장하므로 별도 호출 불필요 | retrieve(use_reranking=True) 활용 |
| LLM 서비스 이중 경로 | **Medium** | VIPAgent.llm (ChatOpenAI) vs RAGPipeline._llm_service (LLMService) | 하나의 경로로 통합 |

### 3.2 Frontend <-> Backend SSE (Critical)

**프로토콜 불일치 발견**:

| 항목 | Backend (FastAPI) | Frontend (React) | 불일치 |
|------|------------------|-----------------|--------|
| HTTP 메서드 | **POST** /chat/stream | **GET** EventSource | **CRITICAL**: EventSource는 GET만 지원 |
| 이벤트 타입 | JSON {type, content} | event.data == [DONE] | **HIGH**: JSON 파싱 미구현 |
| 엔드포인트 경로 | /search/chat/stream | /api/v1/search/stream | **MEDIUM**: 경로 불일치 |
| 완료 시그널 | {type: "end"} | [DONE] 문자열 | **HIGH**: 완료 감지 불일치 |
| 출처 정보 | {type: "start", sources} | 파싱 미구현 | **MEDIUM**: 출처 표시 불가 |

**권고**: **fetch + ReadableStream 방식** 채택 - POST 지원, JWT 토큰 헤더 전달, 본문에 필터/대화 ID 포함 가능

### 3.3 VIPAgent <-> RAGPipeline 통합

| 관심사 | 현재 | Wave 3 이후 |
|--------|------|------------|
| 검색 | RAGPipeline이 SearchService 직접 호출 | VIPAgent Retriever 노드에서 HybridRetriever 호출 |
| 생성 | RAGPipeline.generate_answer() | Generator 노드에서 RAGPipeline.generate_answer() 위임 |
| 스트리밍 | RAGPipeline.generate_stream() | VIPAgent.astream() -> Generator 노드 스트리밍 |
| 검증 | 없음 | Validator 노드 신규 추가 |

**전환 전략**: RAGPipeline 유지 + VIPAgent Generator 노드가 위임 호출하는 점진적 전환.

---

## 4. Tech Debt Update

### Wave 2 기준: 12건

(기존 9건 + Wave 2 신규 3건)

### Wave 3 신규: 4건

| ID | 위치 | 내용 | 순위 | 연관 Story |
|----|------|------|:----:|-----------|
| **013** | rag_pipeline.py L309-323 | 가짜 스트리밍: 전체 생성 후 문장 분할. 토큰 단위 LLM 스트리밍 필요 | **High** | STORY-033/043 |
| **014** | bge_reranker.py L271 | _batch_process() 동기 CPU 바운드를 async에서 직접 호출. asyncio.to_thread() 래핑 권장 | **Medium** | STORY-032 |
| **015** | searchService.ts L70-71 | EventSource GET vs Backend POST 불일치. fetch+ReadableStream 전환 필요 | **High** | STORY-043 |
| **016** | vip_agent.py L43-54 | VIPAgent.llm ChatOpenAI 직접 생성 vs RAGPipeline LLMService 래퍼 - LLM 경로 이중화 | **Medium** | STORY-033 |

### 누적 현황: 16건

| 순위 | 건수 | 변동 |
|------|:----:|:----:|
| **High** | 3 | +2 (013, 015) |
| **Medium** | 9 | +2 (014, 016) |
| **Low** | 4 | - |

### 우선 해결 대상 (Wave 3 블로커)

| ID | 내용 | 블로커 이유 |
|----|------|------------|
| **015** | EventSource/POST 불일치 | STORY-043 구현 불가능 |
| **013** | 가짜 스트리밍 | STORY-033 AC4, STORY-043 AC1 미달 |
| **005** | VIP Agent 오케스트레이션 | STORY-033 핵심 |

---

## 5. Recommendations

### 5.1 STORY-033 (LangGraph Workflow) 구현 권고

**우선순위**: Critical (8SP)

| # | 권고 | 담당 | 설명 |
|---|------|------|------|
| 1 | **AgentState 통합 사용** | RAG Engineer | agents/state.py 하나만 사용, ai_service 별도 정의 금지 |
| 2 | **Planner 노드 추가** | RAG Engineer | 검색 전략 결정 (keyword/semantic/hybrid) |
| 3 | **Validator 노드 추가** | RAG Engineer | Faithfulness/Relevance 검증, 조건부 재검색 (최대 1회) |
| 4 | **HybridRetriever 위임** | RAG Engineer | Retriever 노드에서 HybridRetriever.retrieve() 직접 호출 |
| 5 | **RAGPipeline.generate_answer() 위임** | RAG Engineer | Generator 노드에서 기존 RAGPipeline 활용 |
| 6 | **astream() 통합** | RAG Engineer | LangGraph workflow.astream()으로 SSE 이벤트 전달 |

**제안 그래프 구조**:

```
entry -> planner -> retriever -> generator -> validator
                                                  |
                                          [pass] -> END
                                          [fail] -> retriever (재검색, 최대 1회)
```

### 5.2 STORY-043 (SSE Streaming) 구현 권고

**우선순위**: Medium (3SP)

| # | 권고 | 담당 | 설명 |
|---|------|------|------|
| 1 | **fetch + ReadableStream 방식 채택** | Frontend | EventSource 대신 fetch API 사용 |
| 2 | **SSEClient 유틸리티 구현** | Frontend | 재연결 3회 로직 포함 |
| 3 | **JSON 이벤트 파싱** | Frontend | Backend {type, content, sources} 형식 파싱 |
| 4 | **출처 표시 연동** | Frontend | start 이벤트 sources를 Message.sources에 저장 |
| 5 | **취소 기능 구현** | Frontend | AbortController로 fetch 취소, UI 버튼 추가 |

### 5.3 통합 권고

| # | 권고 | 담당 | 우선순위 |
|---|------|------|----------|
| 1 | LLM 경로 통합 | RAG Engineer | **High** |
| 2 | 엔드포인트 경로 통일 | Backend + Frontend | **High** |
| 3 | SSE 이벤트 스키마 명세서 작성 | TechLead | **Medium** |
| 4 | Reranker asyncio.to_thread() 래핑 | RAG Engineer | **Medium** |

---

## 6. Verdict

### Wave 3 진행 판정: **조건부 진행 가능 (Proceed with Caution)**

#### 필수 선행 조건 (Must-Have)

| # | 조건 | 관련 Story | 블로커 수준 |
|---|------|-----------|:----------:|
| 1 | Frontend SSE를 fetch+ReadableStream으로 전환 | STORY-043 | **BLOCKER** |
| 2 | Backend SSE 이벤트 프로토콜과 Frontend 파싱 로직 일치 확인 | STORY-043 | **BLOCKER** |
| 3 | AgentState 중복 정의 방지 결정 | STORY-033 | **HIGH** |

#### 권장 선행 조건 (Should-Have)

| # | 조건 | 관련 Story | 중요도 |
|---|------|-----------|:------:|
| 1 | 진정한 LLM 토큰 스트리밍 구현 | STORY-033/043 | **HIGH** |
| 2 | Validator 노드 설계 확정 | STORY-033 | **MEDIUM** |
| 3 | SSE 이벤트 스키마 계약 문서 작성 | STORY-043 | **MEDIUM** |

#### 코드 품질 현황

| 영역 | 등급 | Wave 3 영향 |
|------|:----:|-----------|
| AI Service (HybridRetriever, BGEReranker, RRFusion, RAGPipeline) | **A** | LangGraph 노드에서 위임 호출 가능 |
| Frontend (Search Components) | **B+** | SSE 패턴 강화 필요 |
| VIPAgent (LangGraph 스켈레톤) | **C** | 실질 구현 필요 (현재 TODO만 존재) |
| Backend API (SSE 엔드포인트) | **A-** | 가짜 스트리밍 개선 필요 |

#### 기술 부채 추이

```
Wave 1: 9건 (High:1, Medium:4, Low:4)
Wave 2: 12건 (High:1, Medium:7, Low:4)  [+3]
Wave 3: 16건 (High:3, Medium:9, Low:4)  [+4]  <-- 현재
```

High 항목 3건 중 2건(013, 015)은 Wave 3 구현 과정에서 자연스럽게 해결될 것으로 예상. Wave 3 완료 후 예상 잔여: **14건** (High:1, Medium:9, Low:4).

---

*Reviewed by TechLead Agent | 2026-01-28*
