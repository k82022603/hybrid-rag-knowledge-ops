# STORY-052: Reranker async 전환 (asyncio.to_thread 래핑)

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-42 |
| **Epic** | EPIC-002 |
| **Status** | In Review |
| **Priority** | Critical |
| **Story Points** | 2 |
| **Assignee** | RAG |
| **Sprint** | 4 |
| **Completed** | 2026-01-28 |

---

## User Story

**As a** RAG 파이프라인 개발자,
**I want** BGE Reranker의 동기 CPU 작업이 async 이벤트루프를 블로킹하지 않도록 전환,
**So that** 동시 검색 요청이 Reranker 실행 중에도 차단되지 않고 처리될 수 있음.

---

## Acceptance Criteria

- [x] **Given** Reranker.rerank() 호출 시, **When** CPU-intensive 모델 추론 실행, **Then** asyncio 이벤트루프가 블로킹되지 않음
- [x] **Given** 동시에 2개 이상의 검색 요청, **When** 첫 번째 요청이 Reranker 실행 중, **Then** 두 번째 요청의 Retriever 단계가 정상 진행
- [x] **Given** asyncio.to_thread() 래핑 적용 후, **When** Reranker 결과 반환, **Then** 기존과 동일한 reranked document 리스트 반환 (결과 동일성)
- [x] **Given** 멀티 스레드 환경에서 모델 추론, **When** 동시 접근 발생, **Then** thread-safety가 보장되어 크래시 없음

---

## Tasks

- [x] BGEReranker.rerank() 메서드를 asyncio.to_thread()로 래핑
- [x] _sync_rerank() 동기 전용 메서드 분리
- [x] arerank_with_timeout() 15초 타임아웃 보호 + fallback 추가
- [x] _fallback_results() 타임아웃 시 원본 순서 유지 fallback
- [x] RerankerAdapter 타임아웃 지원 추가
- [x] 기존 65개 단위 테스트 통과 확인 (하위 호환성)
- [x] 신규 33개 async 전용 테스트 작성 및 통과

---

## 구현 상세

### 변경된 파일

| 파일 | 변경 내용 |
|------|----------|
| `ai_service/src/reranking/bge_reranker.py` | rerank() asyncio.to_thread 래핑, _sync_rerank/arerank_with_timeout/_fallback_results 추가 |
| `ai_service/src/adapters/reranker_adapter.py` | 타임아웃 파라미터 추가, arerank_with_timeout 호출 |
| `ai_service/tests/test_reranker_async.py` | 33개 async 전용 테스트 (신규) |
| `backlog/stories/STORY-052-reranker-async.md` | 스토리 파일 업데이트 |

### 핵심 구현 패턴

```python
# Before (동기 - 이벤트루프 블로킹)
async def rerank(self, query, documents, top_k):
    scores = self._batch_process(pairs, self.batch_size)  # CPU-blocking!
    return sorted_results

# After (async - non-blocking via asyncio.to_thread)
async def rerank(self, query, documents, top_k):
    results = await asyncio.to_thread(
        self._sync_rerank, query, documents, top_k
    )  # 별도 스레드에서 실행, 이벤트루프 비블로킹
    return results

# 타임아웃 보호
async def arerank_with_timeout(self, query, documents, top_k, timeout=15.0):
    try:
        return await asyncio.wait_for(
            self.rerank(query, documents, top_k),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        return self._fallback_results(documents, top_k)
```

### Thread-Safety 검증 결과

- BGE Reranker 모델은 `model.eval()` + `torch.no_grad()` 상태에서 read-only inference 수행
- batch normalization은 eval 모드에서 running stats 사용 (thread-safe)
- 동시 5개 요청 테스트 통과: 크래시 없음

---

## 테스트 결과

### 기존 테스트 (65개 - 하위 호환성)
```
ai_service/tests/test_bge_reranker.py - 65 passed in 0.77s
```

### 신규 async 테스트 (33개)
```
ai_service/tests/test_reranker_async.py - 33 passed in 9.34s
```

### 테스트 범주
| 범주 | 테스트 수 | 결과 |
|------|----------|------|
| asyncio.to_thread 래핑 검증 | 4 | PASS |
| _sync_rerank 결과 동일성 | 5 | PASS |
| arerank_with_timeout 타임아웃 | 5 | PASS |
| _fallback_results 동작 | 6 | PASS |
| 이벤트루프 비블로킹 | 3 | PASS |
| RerankerAdapter 타임아웃 통합 | 6 | PASS |
| Thread-Safety (동시 5요청) | 2 | PASS |
| 성능 벤치마크 | 2 | PASS |
| **합계** | **33** | **ALL PASS** |

---

## 기술 노트

### 문제점 (Sprint 03 리뷰에서 도출)

Sprint 03에서 구현한 BGE Reranker(STORY-032)는 **동기 방식**으로 모델 추론을 수행한다. FastAPI의 async 엔드포인트 내에서 이 동기 호출이 발생하면:

1. **이벤트루프 블로킹** - Reranker 추론 시간(수백 ms ~ 수 초) 동안 다른 모든 요청 처리가 중단
2. **동시성 파괴** - 단일 요청이 서버 전체를 멈추는 효과
3. **타임아웃 위험** - 앞선 요청의 Reranker가 완료될 때까지 후속 요청이 대기

### 해결 방향

`asyncio.to_thread()`를 사용하여 CPU-intensive 모델 추론을 별도 스레드에서 실행합니다.
Python의 기본 ThreadPoolExecutor를 활용하며, GIL 영향은 PyTorch C++ 확장 실행 시 해제되므로 실질적 병렬성이 확보됩니다.

### 영향 범위

- `ai_service/src/reranking/bge_reranker.py` - async 전환 (핵심)
- `ai_service/src/adapters/reranker_adapter.py` - 타임아웃 지원
- `knowledge_service/src/app/rag/retriever.py` - 변경 불필요 (이미 await reranker.rerank_search_results 사용)

---

## 참고 자료

- Sprint 03 완료 리뷰에서 도출 - Reranker 블로킹 문제
- [STORY-032 BGE Reranker](./STORY-032-bge-reranker.md)
- [Python asyncio.to_thread](https://docs.python.org/3/library/asyncio-task.html#asyncio.to_thread)
