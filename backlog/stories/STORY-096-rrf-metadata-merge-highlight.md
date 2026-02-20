# STORY-096: RRF Fusion 메타데이터 병합 + 검색어 하이라이팅

## Story Information

| Item | Value |
|------|-------|
| **ID** | STORY-096 |
| **Type** | FEAT |
| **Priority** | High (P1) |
| **Story Points** | 5 |
| **Sprint** | 08 |
| **Status** | Closed - Project Completed (2026-02-18) |
| **Jira ID** | - |
| **Created** | 2026-02-08 |
| **Primary** | RAG |
| **Secondary** | Frontend |

---

## Summary

RRF Fusion 시 동일 chunk가 여러 소스(Vector, Keyword, Graph)에서 반환될 때 메타데이터를 병합하여 Keyword BM25 하이라이트 정보를 보존하고, 프론트엔드에서 검색어 하이라이팅을 렌더링한다.

---

## Background

### 현재 문제

RRF Fusion에서 동일 `chunk_id`가 Vector + Keyword 양쪽에서 반환될 때:

1. **첫 번째 등장 소스의 metadata만 보존** (`results_map[chunk_id]` 첫 등록 기준)
2. Vector가 먼저 등록되면 Keyword의 **BM25 highlight 정보가 유실**됨
3. 검색 결과에 **검색어 하이라이팅이 불가능**

### 영향 범위

- `rrf_fusion.py`: `fuse_search_results()` 메서드 (line 453-454)
- `search.py`: `_rrf_fusion()` 메서드
- Frontend: `SearchResultCard.tsx` 하이라이트 렌더링

### 사용자 가치

- 임베딩 품질 + Retriever 품질이 모두 높아야 좋은 검색 경험
- 검색어 하이라이팅은 사용자가 결과 관련성을 빠르게 판단하는 핵심 UX 요소

---

## Acceptance Criteria

- [ ] RRF Fusion에서 동일 chunk의 metadata를 소스별로 병합 (덮어쓰기 아닌 merge)
- [ ] Keyword 검색 결과의 BM25 highlight 정보가 fusion 후에도 보존됨
- [ ] API 응답에 `highlight` 필드 포함 (검색어 매칭 구간 정보)
- [ ] Frontend `SearchResultCard`에서 검색어 하이라이팅 렌더링
- [ ] Vector-only 결과 (highlight 없음)도 정상 렌더링 (fallback)
- [ ] 기존 RRF 점수 계산에 영향 없음 (regression 없음)

---

## Technical Design

### 1. Backend - Metadata Merge 로직

```python
# rrf_fusion.py / search.py
# 기존: 첫 등장만 저장
if chunk_id not in results_map:
    results_map[chunk_id] = result

# 변경: metadata 병합
if chunk_id not in results_map:
    results_map[chunk_id] = result
else:
    # highlight, matched_entities 등 유용한 metadata 병합
    existing = results_map[chunk_id]
    if "highlight" not in existing.metadata and "highlight" in result.metadata:
        existing.metadata["highlight"] = result.metadata["highlight"]
    if "matched_entities" not in existing.metadata and "matched_entities" in result.metadata:
        existing.metadata["matched_entities"] = result.metadata["matched_entities"]
```

### 2. Elasticsearch BM25 Highlight 요청

```python
# search.py - _keyword_search() 에서 ES highlight 요청 추가
"highlight": {
    "fields": {"content": {}},
    "pre_tags": ["<mark>"],
    "post_tags": ["</mark>"],
    "number_of_fragments": 3
}
```

### 3. API Response

```python
class SearchResult(BaseModel):
    # ... 기존 필드
    highlight: Optional[List[str]] = Field(default=None, description="검색어 하이라이트 스니펫")
```

### 4. Frontend Rendering

```tsx
// SearchResultCard.tsx
{result.highlight ? (
    <p dangerouslySetInnerHTML={{ __html: result.highlight[0] }} />
) : (
    <p>{result.content}</p>
)}
```

---

## Dependencies

- STORY-091 (RRF Fusion source_type 수정) - Done
- Elasticsearch highlight API 지원 확인

---

## Testing

- [ ] Unit: metadata merge 로직 테스트 (Vector+Keyword 동시 반환 시나리오)
- [ ] Unit: highlight 없는 결과 fallback 테스트
- [ ] E2E: 실제 검색어로 하이라이팅 렌더링 확인
- [ ] Regression: 기존 RRF 점수 계산 영향 없음 확인

---

## References

- TechLead RRF 리뷰 (2026-02-08): Low 이슈 → High로 승격
- `rrf_fusion.py` line 453-454
- `search.py._rrf_fusion()` 메서드
