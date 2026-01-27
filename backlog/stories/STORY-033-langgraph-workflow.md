# STORY-033: LangGraph 워크플로우

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-28 |
| **Epic** | EPIC-002 |
| **Status** | To Do |
| **Priority** | Critical |
| **Story Points** | 8 |
| **Assignee** | MLRag |
| **Sprint** | 3 |

---

## User Story

**As a** RAG 시스템 개발자,
**I want** LangGraph 기반 RAG 워크플로우를 구축,
**So that** 질의 분석, 검색, 응답 생성의 복잡한 흐름을 유연하게 관리함.

---

## Acceptance Criteria

- [ ] **Given** 사용자 질의, **When** 워크플로우 실행, **Then** Planner -> Retriever -> Generator -> Validator 순서로 실행
- [ ] **Given** 복잡한 질의, **When** Planner 분석, **Then** 검색 전략 결정 (키워드/의미/하이브리드)
- [ ] **Given** 검색 결과, **When** Generator 실행, **Then** 컨텍스트 기반 응답 생성
- [ ] **Given** 스트리밍 모드, **When** 응답 생성, **Then** 토큰 단위 스트리밍 지원
- [ ] **Given** Generator 응답 생성 완료, **When** Validator 실행, **Then** 응답 품질 검증 (Faithfulness, Relevance) 수행
- [ ] **Given** Validator 검증 실패, **When** 품질 기준 미달, **Then** Retriever로 재검색 또는 사용자에게 경고 표시
- [ ] **Given** 워크플로우 실행, **When** 전체 흐름, **Then** 상태 추적 가능

---

## Tasks

- [ ] AgentState 정의
- [ ] Planner 노드 구현
- [ ] Retriever 노드 구현
- [ ] Generator 노드 구현
- [ ] Validator 노드 구현 (Faithfulness/Relevance 검증, 조건부 재검색)
- [ ] 워크플로우 그래프 컴파일 (Validator 조건 분기 포함)
- [ ] 스트리밍 지원
- [ ] 에러 핸들링
- [ ] 단위/통합 테스트 작성

---

## 기술 노트

### AgentState 정의

```python
# ai_service/src/workflows/state.py
from typing import TypedDict, List, Optional, Literal
from dataclasses import dataclass

class AgentState(TypedDict):
    """RAG 워크플로우 상태"""
    # 입력
    query: str
    conversation_history: List[dict]

    # Planner 출력
    search_strategy: Literal["keyword", "semantic", "hybrid"]
    refined_query: str

    # Retriever 출력
    documents: List[dict]
    context: str

    # Generator 출력
    answer: str
    sources: List[dict]

    # 메타
    steps: List[str]
    error: Optional[str]
```

### Planner 노드

```python
# ai_service/src/workflows/nodes/planner.py
from langchain_core.prompts import ChatPromptTemplate

class PlannerNode:
    """
    질의 분석 및 검색 전략 결정
    - 키워드 검색: 특정 용어, 이름 검색
    - 의미 검색: 개념, 설명 검색
    - 하이브리드: 복잡한 질의
    """

    def __init__(self, llm):
        self.llm = llm
        self.prompt = ChatPromptTemplate.from_template("""
당신은 검색 전략을 결정하는 전문가입니다.

사용자 질의: {query}

다음 중 적절한 검색 전략을 선택하세요:
1. keyword: 특정 용어, 이름, 코드명 검색 시
2. semantic: 개념 설명, 방법론, 추상적 질문 시
3. hybrid: 복잡한 질의, 여러 조건 포함 시

출력 형식:
strategy: [keyword|semantic|hybrid]
refined_query: [검색에 최적화된 질의]
""")

    async def __call__(self, state: AgentState) -> AgentState:
        response = await self.llm.ainvoke(
            self.prompt.format(query=state["query"])
        )

        # 응답 파싱
        lines = response.content.strip().split("\n")
        strategy = "hybrid"
        refined_query = state["query"]

        for line in lines:
            if line.startswith("strategy:"):
                strategy = line.split(":")[1].strip()
            elif line.startswith("refined_query:"):
                refined_query = line.split(":")[1].strip()

        return {
            **state,
            "search_strategy": strategy,
            "refined_query": refined_query,
            "steps": state["steps"] + ["planner"]
        }
```

### Retriever 노드

```python
# ai_service/src/workflows/nodes/retriever.py
class RetrieverNode:
    """검색 실행 노드"""

    def __init__(self, hybrid_retriever: HybridRetriever):
        self.retriever = hybrid_retriever

    async def __call__(self, state: AgentState) -> AgentState:
        strategy = state["search_strategy"]
        query = state["refined_query"]

        # 전략에 따른 가중치 조정
        if strategy == "keyword":
            es_weight, neo4j_weight = 0.3, 0.7
        elif strategy == "semantic":
            es_weight, neo4j_weight = 0.8, 0.2
        else:  # hybrid
            es_weight, neo4j_weight = 0.5, 0.5

        documents = await self.retriever.retrieve(
            query=query,
            top_k=5,
            es_weight=es_weight,
            neo4j_weight=neo4j_weight
        )

        # 컨텍스트 구성
        context = "\n\n---\n\n".join([
            f"[문서: {doc.metadata.get('doc_title', 'Unknown')}]\n{doc.content}"
            for doc in documents
        ])

        return {
            **state,
            "documents": [doc.to_dict() for doc in documents],
            "context": context,
            "steps": state["steps"] + ["retriever"]
        }
```

### Generator 노드

```python
# ai_service/src/workflows/nodes/generator.py
class GeneratorNode:
    """응답 생성 노드"""

    def __init__(self, llm):
        self.llm = llm
        self.prompt = ChatPromptTemplate.from_template("""
당신은 지식 검색 시스템의 AI 어시스턴트입니다.

**컨텍스트 (검색된 문서):**
{context}

**사용자 질문:**
{query}

**지침:**
1. 컨텍스트 정보를 기반으로 정확하게 답변하세요.
2. 컨텍스트에 없는 정보는 "관련 정보를 찾을 수 없습니다"라고 답하세요.
3. 출처를 명시하세요.
4. 한국어로 답변하세요.

**답변:**
""")

    async def __call__(self, state: AgentState) -> AgentState:
        response = await self.llm.ainvoke(
            self.prompt.format(
                context=state["context"],
                query=state["query"]
            )
        )

        # 출처 추출
        sources = [
            {
                "title": doc.get("metadata", {}).get("doc_title"),
                "chunk_id": doc.get("id")
            }
            for doc in state["documents"]
        ]

        return {
            **state,
            "answer": response.content,
            "sources": sources,
            "steps": state["steps"] + ["generator"]
        }
```

### 워크플로우 그래프

```python
# ai_service/src/workflows/rag_workflow.py
from langgraph.graph import StateGraph, END

class RAGWorkflow:
    """LangGraph 기반 RAG 워크플로우"""

    def __init__(
        self,
        planner: PlannerNode,
        retriever: RetrieverNode,
        generator: GeneratorNode
    ):
        self.workflow = self._build_graph(planner, retriever, generator)

    def _build_graph(self, planner, retriever, generator) -> StateGraph:
        workflow = StateGraph(AgentState)

        # 노드 추가
        workflow.add_node("planner", planner)
        workflow.add_node("retriever", retriever)
        workflow.add_node("generator", generator)

        # 엣지 연결
        workflow.set_entry_point("planner")
        workflow.add_edge("planner", "retriever")
        workflow.add_edge("retriever", "generator")
        workflow.add_edge("generator", END)

        return workflow.compile()

    async def run(self, query: str) -> dict:
        """워크플로우 실행"""
        initial_state = AgentState(
            query=query,
            conversation_history=[],
            search_strategy="hybrid",
            refined_query="",
            documents=[],
            context="",
            answer="",
            sources=[],
            steps=[],
            error=None
        )

        result = await self.workflow.ainvoke(initial_state)
        return result

    async def stream(self, query: str):
        """스트리밍 실행"""
        initial_state = AgentState(...)
        async for chunk in self.workflow.astream(initial_state):
            yield chunk
```

### 영향 범위
- `ai_service/src/workflows/state.py` (신규)
- `ai_service/src/workflows/nodes/planner.py` (신규)
- `ai_service/src/workflows/nodes/retriever.py` (신규)
- `ai_service/src/workflows/nodes/generator.py` (신규)
- `ai_service/src/workflows/rag_workflow.py` (신규)

---

## 테스트 계획

- [ ] Unit Test: PlannerNode 전략 결정
- [ ] Unit Test: RetrieverNode 검색 실행
- [ ] Unit Test: GeneratorNode 응답 생성
- [ ] Unit Test: ValidatorNode 품질 검증 (통과/실패 시나리오)
- [ ] Integration Test: 전체 워크플로우 실행 (Validator 포함)
- [ ] Integration Test: 스트리밍 동작

---

## 참고 자료

- [LangGraph 공식 문서](https://langchain-ai.github.io/langgraph/)
- [상세 설계서 v2.4](../../knowledge_service/docs/02_design/hybrid_rag_platform_detailed_design.md)
