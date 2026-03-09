# OPS-035: Reranker 이중 실행 트러블슈팅

> **분류**: 구현 오류 (Implementation Defect)
> **발견일**: 2026-03-09
> **심각도**: High (Chat API 타임아웃 유발)
> **상태**: 해결 완료
> **커밋**: `9b500a3`

---

## 1. 증상

- Chat API 응답 시간 73초 → Nginx 120초 타임아웃 발생
- UAT TC-07 (RAG Chat) FAIL
- CPU 사용률 100% 구간이 비정상적으로 길게 지속

---

## 2. 원인 분석

### 2.1 호출 흐름 (수정 전)

```
Chat API 요청
  └─ RAGWorkflow._retrieve()
       └─ HybridRetriever.retrieve()
            ├─ SearchService.hybrid_search()
            │    ├─ Vector Search (ES)          ~1초
            │    ├─ Keyword Search (ES)         ~1초
            │    ├─ Sparse Search (ES)          ~1초
            │    ├─ Graph Search (Neo4j)        ~1초
            │    ├─ RRF Fusion                  <1초
            │    └─ ★ Reranker 1차 실행         ~33초  ← 불필요
            │
            └─ ★ Reranker 2차 실행              ~33초  ← 실제 필요
```

### 2.2 근본 원인

STORY-032 (BGE-Reranker 적용) **설계는 `HybridRetriever`에만 Reranker를 통합**하도록 명시:

> **STORY-032 테스트 계획서 (07_STORY-032_bge_reranker_test_plan.md)**
> - 테스트 대상: `bge_reranker.py` (신규) + `hybrid_retriever.py` (수정)
> - `SearchService`는 테스트 대상에 **포함되지 않음**
> - 시나리오 8: "`HybridRetriever` 내에서 Reranker 호출이 정확한지 확인"

그러나 **구현 시 `SearchService.hybrid_search()`에도 Reranker를 중복 구현**:

| 클래스 | 파일 | 설계 | 구현 |
|--------|------|:----:|:----:|
| `HybridRetriever` | `rag/retriever.py` | Reranker 통합 | Reranker 호출 |
| `SearchService` | `services/search.py` | Reranker **없음** | Reranker 호출 (**설계 외 추가**) |

**문제**: `HybridRetriever`가 `SearchService.hybrid_search()`를 내부적으로 호출하는 구조에서, 설계에 없던 `SearchService` 내부 Reranker와 합쳐져 **같은 데이터에 2회 실행**됨.

### 2.3 분류: 구현 오류 (Implementation Defect)

**설계 오류가 아니라 구현 오류**입니다.

- 설계(STORY-032)는 Reranker를 `HybridRetriever`에만 넣도록 명시
- 구현 시 `SearchService`에도 중복 구현 — **설계 범위를 벗어난 추가 구현**
- 단위 테스트는 각 클래스를 독립적으로 검증하여 이중 실행 미발견
- 통합 테스트에서 발견 가능했으나, Mock 기반 테스트로 가려짐

```
분류: 구현 오류 (Implementation Defect)
 ├─ 설계는 명확: HybridRetriever에만 Reranker 통합
 ├─ 구현이 설계를 위반: SearchService에 설계 외 Reranker 추가
 ├─ 성능 결함(Performance Defect): 불필요한 33초 CPU 추론 추가
 └─ 책임: 클로드 (구현 시 설계 범위 미준수)
```

---

## 3. 해결 방안

### 3.1 선택한 방안: `skip_reranking` 플래그

`HybridRetriever`가 `SearchService`를 호출할 때 Reranking을 건너뛰도록 플래그 전달:

```python
# rag/retriever.py — HybridRetriever.retrieve()
result = await self.search_service.hybrid_search(
    query=query,
    top_k=fetch_k,
    skip_reranking=True,  # SearchService 내부 reranking 건너뜀
)
# → HybridRetriever 자체 reranking만 1회 수행
```

### 3.2 호출 경로별 동작

| 호출 경로 | Reranker 실행 위치 | skip_reranking |
|-----------|-------------------|----------------|
| REST API → `SearchService.hybrid_search()` | SearchService 내부 | `False` (기본값) |
| Chat API → `RAGWorkflow` → `HybridRetriever` → `SearchService` | HybridRetriever | `True` (SearchService 건너뜀) |

### 3.3 수정된 호출 흐름

```
Chat API 요청
  └─ RAGWorkflow._retrieve()
       └─ HybridRetriever.retrieve()
            ├─ SearchService.hybrid_search(skip_reranking=True)
            │    ├─ Vector Search (ES)          ~1초
            │    ├─ Keyword Search (ES)         ~1초
            │    ├─ Sparse Search (ES)          ~1초
            │    ├─ Graph Search (Neo4j)        ~1초
            │    ├─ RRF Fusion                  <1초
            │    └─ Reranker 건너뜀             0초  ← skip
            │
            └─ ★ Reranker 1회 실행              ~33초
```

### 3.4 검토했으나 선택하지 않은 방안

| 방안 | 불채택 사유 |
|------|------------|
| HybridRetriever에서 Reranker 제거 | REST API가 HybridRetriever를 직접 사용할 가능성 |
| SearchService에서 Reranker 제거 | REST API 경로에서 Reranking 불가 |
| Reranker를 별도 레이어로 분리 | 리팩토링 범위 과대, 현재 구조에서 플래그로 충분 |

---

## 4. 결과

### 4.1 성능 개선

| 항목 | 수정 전 | 수정 후 | 개선 |
|------|---------|---------|------|
| Reranker 실행 횟수 | 2회/요청 | 1회/요청 | -50% |
| Chat API 응답 시간 | ~73초 (타임아웃) | ~47초 | -36% |
| CPU Reranker 점유 | ~66초 (33초 x 2) | ~33초 | -50% |
| UAT TC-07 | FAIL | PASS | 해소 |

### 4.2 검색 품질

변화 없음. 이미 reranked된 결과를 다시 rerank해도 순서 변화가 미미하므로, 이중 실행은 순수하게 **성능 낭비**였습니다.

---

## 5. 영향도 분석

| 영향 영역 | 수준 | 설명 |
|-----------|:----:|------|
| Chat API (RAGWorkflow 경유) | **High** | 이중 실행 → 타임아웃 직접 유발 |
| REST Search API (`/api/v1/search`) | 없음 | SearchService 직접 호출, HybridRetriever 미경유 |
| 검색 품질 (순위 정확도) | 없음 | reranked 결과의 재rerank은 순서 변화 미미 |
| CPU 리소스 | **High** | BGE-Reranker ONNX 추론이 전체 CPU 2회 점유 |
| 메모리 | Low | Reranker 모델은 싱글톤, 추가 메모리 사용 없음 |
| 다른 서비스 | **Medium** | CPU 100% 점유로 Healthcheck 지연 → 컨테이너 재시작 위험 |

---

## 6. 재발 방지

### 6.1 교훈

```
┌──────────────────────────────────────────────────────────────┐
│  "설계에 명시된 범위를 벗어나는 구현을 하지 않는다."          │
│  "구현 시 설계 문서를 반드시 참조하고, 추가 구현이 필요하면   │
│   설계를 먼저 변경한다."                                      │
│                                                              │
│  Reranking은 파이프라인에서 딱 한 곳에서만 실행되어야 한다.  │
└──────────────────────────────────────────────────────────────┘
```

### 6.2 체크리스트

- [ ] 구현 전 설계 문서에서 해당 클래스의 수정 범위 확인
- [ ] 새로운 검색 경로 추가 시, Reranker 호출 지점이 1곳인지 확인
- [ ] `SearchService`와 `HybridRetriever`의 책임 경계 문서화
- [ ] 통합 테스트에서 Reranker 호출 횟수 검증 (E2E 경로)

### 6.3 관련 수정 (동일 세션)

| 수정 | 파일 | 내용 |
|------|------|------|
| P0-2 후보 수 제한 | `search.py`, `retriever.py` | Reranker 입력 50→15건 제한 |
| P1-2 ONNX 코어 제한 | `bge_reranker.py` | ONNX Runtime 2코어 제한 (CPU 독점 방지) |
| Reranker timeout | `search.py` | 60초 타임아웃 설정 |

---

## 7. 타임라인

| 시점 | 이벤트 |
|------|--------|
| STORY-032 설계 | Reranker를 `HybridRetriever`에만 통합하도록 설계 |
| STORY-032 구현 | 설계 외로 `SearchService`에도 Reranker 중복 구현 (구현 오류) |
| UAT 이전 | 개별 단위 테스트 통과, 이중 실행 미발견 (Mock 기반) |
| 2026-03-09 UAT | TC-07 RAG Chat FAIL (73초 타임아웃) |
| 2026-03-09 분석 | TechLead 에이전트가 호출 흐름 추적 → 이중 실행 발견 |
| 2026-03-09 수정 | `skip_reranking=True` 플래그 적용, 47초로 개선 |

---

## 8. 관련 문서

- [OPS-034: Graph 검색 RRF 튜닝](./34_graph_search_rrf_tuning.md) — 동일 세션에서 수행한 RRF 관련 수정
- [DEV-003: 테스트 전 리소스 정리](../05_development/03_pre_test_resource_cleanup.md) — drop_caches 후 47초 달성
- [UAT 보고서](../04_testing/13_user_acceptance_test/01_uat_2026-03-09.md) — TC-07 FAIL→PASS 기록

---

*작성자: Claude Code (Opus 4.6)*
*작성일: 2026-03-09*
*문서 번호: OPS-035*
