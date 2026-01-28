# STORY-060: Planner 전략 유효화 + 검색 캐싱

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-50 |
| **Epic** | EPIC-002 |
| **Status** | To Do |
| **Priority** | Medium |
| **Story Points** | 3 |
| **Assignee** | RAG |
| **Sprint** | 4 |

---

## User Story

**As a** RAG 시스템 운영자,
**I want** Planner가 결정한 검색 전략(keyword/semantic/hybrid)이 실제 SearchService에 반영되고, 동일 쿼리 결과가 캐싱,
**So that** 쿼리 유형에 따라 최적의 검색 전략이 적용되고 반복 검색의 응답 시간이 단축됨.

---

## Acceptance Criteria

- [ ] **Given** Planner가 "keyword" 전략을 결정, **When** RetrieverNode 실행, **Then** Elasticsearch keyword search 가중치가 높게 적용
- [ ] **Given** Planner가 "semantic" 전략을 결정, **When** RetrieverNode 실행, **Then** vector similarity search 가중치가 높게 적용
- [ ] **Given** Planner가 "hybrid" 전략을 결정, **When** RetrieverNode 실행, **Then** keyword + semantic + graph를 RRF로 융합
- [ ] **Given** 동일한 쿼리로 두 번째 검색 요청, **When** 캐시에 결과 존재, **Then** DB 검색을 스킵하고 캐시된 결과 반환
- [ ] **Given** 캐시된 결과, **When** TTL(Time To Live) 만료, **Then** 다음 요청 시 DB에서 새로 검색

---

## Tasks

- [ ] Planner 결정(strategy)을 LangGraph State에 전달하는 경로 확인/수정
- [ ] RetrieverNode에서 strategy에 따라 검색 가중치 분기 로직 구현
- [ ] keyword 전략: ES keyword search 위주 (가중치 0.7:0.2:0.1)
- [ ] semantic 전략: ES vector search 위주 (가중치 0.2:0.7:0.1)
- [ ] hybrid 전략: 균등 RRF 융합 (가중치 0.4:0.4:0.2)
- [ ] 검색 결과 캐싱 레이어 구현 (Redis 또는 in-memory LRU)
- [ ] 캐시 키 생성 로직 (query + strategy + top_k 해시)
- [ ] TTL 설정 (기본 5분, 설정 가능)
- [ ] 캐시 히트/미스 메트릭 로깅
- [ ] 캐시 무효화 API (수동 또는 문서 업데이트 시)

---

## 기술 노트

### 문제점 (Sprint 03 리뷰에서 도출)

Sprint 03에서 LangGraph PlannerNode를 구현했으나:

1. **전략 미반영** - Planner가 strategy를 결정하지만 RetrieverNode에서 이를 무시하고 항상 동일한 hybrid 검색 수행
2. **캐싱 부재** - 동일 쿼리 반복 시 매번 ES + Neo4j에 풀 검색하여 불필요한 지연과 리소스 낭비

### 전략 분기 아키텍처

```
PlannerNode
    │
    │ strategy: "keyword" | "semantic" | "hybrid"
    ▼
RetrieverNode
    │
    ├── if strategy == "keyword":
    │       ES keyword (0.7) + ES vector (0.2) + Neo4j (0.1)
    │
    ├── if strategy == "semantic":
    │       ES keyword (0.2) + ES vector (0.7) + Neo4j (0.1)
    │
    └── if strategy == "hybrid":
            ES keyword (0.4) + ES vector (0.4) + Neo4j (0.2)
```

### 캐싱 구현 방향

```python
import hashlib
from functools import lru_cache

class SearchCache:
    def __init__(self, ttl_seconds: int = 300):
        self.cache: dict[str, CacheEntry] = {}
        self.ttl = ttl_seconds

    def _make_key(self, query: str, strategy: str, top_k: int) -> str:
        raw = f"{query}:{strategy}:{top_k}"
        return hashlib.sha256(raw.encode()).hexdigest()

    async def get_or_fetch(self, query, strategy, top_k, fetch_fn):
        key = self._make_key(query, strategy, top_k)
        entry = self.cache.get(key)

        if entry and not entry.is_expired():
            logger.info(f"Cache HIT: {key[:8]}")
            return entry.data

        logger.info(f"Cache MISS: {key[:8]}")
        result = await fetch_fn(query, strategy, top_k)
        self.cache[key] = CacheEntry(data=result, ttl=self.ttl)
        return result
```

### 영향 범위

- `ai_service/nodes/retriever_node.py` - 전략 분기 로직 추가
- `ai_service/nodes/planner_node.py` - strategy를 State에 정확히 기록
- `ai_service/cache/search_cache.py` - 신규: 검색 캐싱 레이어
- `ai_service/config.py` - 캐시 TTL, 가중치 설정

---

## 테스트 계획

- [ ] Unit Test: Planner "keyword" 전략 시 가중치 확인
- [ ] Unit Test: Planner "semantic" 전략 시 가중치 확인
- [ ] Unit Test: Planner "hybrid" 전략 시 가중치 확인
- [ ] Unit Test: 캐시 히트 시 fetch_fn 미호출 확인
- [ ] Unit Test: 캐시 TTL 만료 후 재검색 확인
- [ ] Integration Test: 전략에 따른 검색 결과 차이 확인
- [ ] Performance Test: 캐시 히트 시 응답 시간 단축 측정

---

## 참고 자료

- Sprint 03 완료 리뷰에서 도출 - Planner 전략 미반영
- [STORY-033 LangGraph Workflow](./STORY-033-langgraph-workflow.md)
- [STORY-030 HybridRetriever](./STORY-030-hybrid-retriever.md)
- [STORY-031 RRF Fusion](./STORY-031-rrf-fusion.md)
