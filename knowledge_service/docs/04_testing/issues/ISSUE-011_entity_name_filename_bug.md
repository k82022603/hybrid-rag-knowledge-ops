# ISSUE-011: Graph Search entity_name에 문서 파일명이 전달되는 버그

**Status**: RESOLVED
**Severity**: Medium
**Reported**: 2026-02-08
**Resolved**: 2026-02-08
**Assignee**: MLRag (RAG Engineer)

---

## 증상

Graph Search에서 entity_name에 문서 파일명(예: "KMS_설계서.pdf")이 전달되어
Neo4j subgraph 탐색이 실패하는 문제.

Graph 패널에서 "Graph" 버튼 클릭 시 파일명이 entity_name으로 전달되어
빈 그래프가 표시됨.

## 근본 원인 분석

### 데이터 흐름 추적

```
1. SearchService._graph_search()
   - entity_names 경로: matched_entities가 RETURN에 미포함 (bug #1)
   - content fallback 경로: matched_entities가 비어 있을 수 있음

2. RAGWorkflow.build_sources_from_results()
   - graph 소스만 graph_context 생성 (bug #2)
   - matched_entities 비어 있으면 graph_context 미생성

3. Frontend ChatSearch.handleGraphSourceClick()
   - graphContext?.relatedEntities 비어 있으면 source.title 폴백
   - source.title = Knowledge 노드 title = 파일명 (bug #3)

4. GraphPanel -> /graph/subgraph API
   - entity_name: "KMS_설계서.pdf" 전달 -> Neo4j 매칭 실패
```

### 버그 포인트

1. **search.py** `_graph_search()`: entity_names 경로에서 `matched_entities`가 RETURN 절에 미포함
2. **rag_workflow.py** `build_sources_from_results()`: graph 소스만 `graph_context` 생성, 파일명 필터링 없음
3. **Frontend fallback**: `source.title`(=파일명)을 entity_name으로 사용

## 수정 내용

### 1. search.py - _graph_search() entity_names 경로 수정

**파일**: `knowledge_service/src/app/services/search.py`

entity_names가 제공된 경우의 Cypher 쿼리에 `matched_entities`를 RETURN에 추가:

```python
# Before: matched_entities 미포함
RETURN c.chunk_id, c.content, k.knowledge_id, k.title, entity_match_count AS score

# After: matched_entities 포함
WITH c, k,
     collect(DISTINCT COALESCE(e.name, e.value)) AS matched_entities,
     count(e) AS entity_match_count
RETURN c.chunk_id, c.content, k.knowledge_id, k.title,
       entity_match_count AS score, matched_entities
```

### 2. rag_workflow.py - build_sources_from_results() 개선

**파일**: `knowledge_service/src/app/agents/rag_workflow.py`

- 모든 소스(graph/vector/keyword)에 대해 `graph_context` 생성
- 파일명 패턴 필터링 (`_is_filename()`) 추가
- 제목에서 유의미한 엔티티명 추출 (`_extract_entities_from_title()`)

```python
# 새로 추가된 유틸 함수
def _is_filename(value: str) -> bool:
    """파일명 패턴 확인 (예: .pdf, .docx, .xlsx)"""
    return bool(re.search(r'\.\w{2,5}$', value))

def _extract_entities_from_title(title: str) -> List[str]:
    """제목에서 엔티티 추출 (파일명 제외)"""
    if not title or _is_filename(title):
        return []
    return [title]
```

## 영향 범위

- Graph Search 결과의 Graph 패널 시각화
- Graph 소스 "Graph" 버튼 클릭 시 subgraph 탐색

## 검증 방법

1. Chat Search에서 질문 후 Graph 소스의 "Graph" 버튼 클릭
2. entity_name이 파일명이 아닌 실제 엔티티명으로 전달되는지 확인
3. Neo4j subgraph 탐색이 정상적으로 작동하는지 확인
