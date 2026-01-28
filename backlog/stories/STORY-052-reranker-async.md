# STORY-052: Reranker async 전환 (asyncio.to_thread 래핑)

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-42 |
| **Epic** | EPIC-002 |
| **Status** | To Do |
| **Priority** | Critical |
| **Story Points** | 2 |
| **Assignee** | RAG |
| **Sprint** | 4 |

---

## User Story

**As a** RAG 파이프라인 개발자,
**I want** BGE Reranker의 동기 CPU 작업이 async 이벤트루프를 블로킹하지 않도록 전환,
**So that** 동시 검색 요청이 Reranker 실행 중에도 차단되지 않고 처리될 수 있음.

---

## Acceptance Criteria

- [ ] **Given** Reranker.rerank() 호출 시, **When** CPU-intensive 모델 추론 실행, **Then** asyncio 이벤트루프가 블로킹되지 않음
- [ ] **Given** 동시에 2개 이상의 검색 요청, **When** 첫 번째 요청이 Reranker 실행 중, **Then** 두 번째 요청의 Retriever 단계가 정상 진행
- [ ] **Given** asyncio.to_thread() 래핑 적용 후, **When** Reranker 결과 반환, **Then** 기존과 동일한 reranked document 리스트 반환 (결과 동일성)
- [ ] **Given** 멀티 스레드 환경에서 모델 추론, **When** 동시 접근 발생, **Then** thread-safety가 보장되어 크래시 없음

---

## Tasks

- [ ] RerankerNode.rerank() 메서드를 async로 전환
- [ ] 내부 모델 추론 호출을 asyncio.to_thread()로 래핑
- [ ] ThreadPoolExecutor 설정 (max_workers 조정)
- [ ] thread-safety 검증 (모델 인스턴스 공유 vs 복제)
- [ ] LangGraph workflow에서 async RerankerNode 호출 확인
- [ ] 기존 동기 호출 경로 정리
- [ ] 부하 테스트 (동시 요청 처리 확인)

---

## 기술 노트

### 문제점 (Sprint 03 리뷰에서 도출)

Sprint 03에서 구현한 BGE Reranker(STORY-032)는 **동기 방식**으로 모델 추론을 수행한다. FastAPI의 async 엔드포인트 내에서 이 동기 호출이 발생하면:

1. **이벤트루프 블로킹** - Reranker 추론 시간(수백 ms ~ 수 초) 동안 다른 모든 요청 처리가 중단
2. **동시성 파괴** - 단일 요청이 서버 전체를 멈추는 효과
3. **타임아웃 위험** - 앞선 요청의 Reranker가 완료될 때까지 후속 요청이 대기

### 해결 방향

```python
# Before (동기 - 이벤트루프 블로킹)
class RerankerNode:
    def rerank(self, query: str, documents: list) -> list:
        scores = self.model.compute_score(pairs)  # CPU-blocking!
        return sorted_documents

# After (async - non-blocking)
class RerankerNode:
    async def rerank(self, query: str, documents: list) -> list:
        scores = await asyncio.to_thread(
            self.model.compute_score, pairs
        )  # 별도 스레드에서 실행
        return sorted_documents
```

### Thread-Safety 고려사항

- BGE Reranker 모델은 일반적으로 **read-only inference**이므로 thread-safe
- 단, 모델 내부 상태(batch normalization 등)가 있는 경우 확인 필요
- 안전을 위해 `threading.Lock` 또는 인스턴스 풀 고려

### 영향 범위

- `ai_service/nodes/reranker_node.py` - async 전환
- `ai_service/workflow/langgraph_workflow.py` - async 노드 호출 대응
- `ai_service/config.py` - ThreadPoolExecutor 설정 추가

---

## 테스트 계획

- [ ] Unit Test: async rerank() 정상 반환 확인
- [ ] Unit Test: asyncio.to_thread 래핑 동작 확인
- [ ] Concurrency Test: 동시 2개 요청 시 이벤트루프 블로킹 없음 확인
- [ ] Performance Test: async 전환 전후 지연 시간 비교
- [ ] Thread-Safety Test: 동시 5개 요청 시 크래시 없음

---

## 참고 자료

- Sprint 03 완료 리뷰에서 도출 - Reranker 블로킹 문제
- [STORY-032 BGE Reranker](./STORY-032-bge-reranker.md)
- [Python asyncio.to_thread](https://docs.python.org/3/library/asyncio-task.html#asyncio.to_thread)
