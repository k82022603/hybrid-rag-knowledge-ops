# STORY-091: [BUG] RRF Fusion에서 search_source 메타데이터 유실

## 메타데이터

| 항목 | 값 |
|------|-----|
| **ID** | STORY-091 |
| **Jira ID** | - |
| **Epic** | EPIC-005 RAG Quality & Performance |
| **Status** | Done |
| **Priority** | High |
| **Story Points** | 2 |
| **Assignee** | RAG/Frontend |
| **Sprint** | Sprint 08 |

---

## Bug Report

### Summary

Graph 검색 결과 3건이 프론트엔드에서 모두 "Vector"로 표시되는 버그. RRF Fusion 과정에서 `result.source`는 갱신하지만 `metadata.search_source`는 갱신하지 않아 원본 검색 소스 정보가 유실됨.

### Root Cause

`search.py`의 `_rrf_fusion()` 함수에서 여러 검색 소스(Vector, Keyword, Graph)의 결과를 통합할 때:
- `result.source` 필드는 정상 갱신
- `metadata.search_source` 필드는 갱신되지 않아 기본값 "Vector"가 유지됨
- 프론트엔드에서 `metadata.search_source`를 참조하여 배지를 표시하므로 모두 "Vector"로 표시

### Fix Applied

- `search.py`의 `_rrf_fusion()` 함수에서 `metadata.search_source` 동기화 로직 추가
- API 응답에 `source_type` 필드 명시적 추가
- 프론트엔드 SearchResultCard에서 `source_type` 우선 참조하도록 수정

### Impact

- 사용자가 검색 결과의 실제 소스(Vector/Keyword/Graph)를 구분할 수 없었음
- Graph 검색 결과의 가치를 사용자에게 보여줄 수 없었음

---

## User Story

**As a** 지식 검색 사용자,
**I want** 검색 결과에 정확한 검색 소스(Vector/Keyword/Graph)가 표시되길,
**So that** 어떤 검색 방식으로 찾은 결과인지 구분할 수 있습니다.

---

## Acceptance Criteria

- [x] **Given** RRF Fusion 후 검색 결과, **When** Graph 소스 결과가 포함될 때, **Then** metadata.search_source가 "Graph"로 정확히 표시
- [x] **Given** 혼합 검색 결과, **When** 프론트엔드에서 배지 렌더링 시, **Then** 각 결과의 소스 배지가 정확히 표시
- [x] **Given** API 응답, **When** source_type 필드 확인 시, **Then** 올바른 검색 소스 값이 포함

---

## Tasks

- [x] `search.py` `_rrf_fusion()` 함수에서 metadata.search_source 동기화
- [x] API 응답에 source_type 필드 추가
- [x] 프론트엔드 SearchResultCard source_type 우선 참조
- [x] 회귀 테스트 확인

---

## 기술 노트

### 수정 파일
- `knowledge_service/src/app/services/search.py` - _rrf_fusion() 메타데이터 동기화
- `knowledge_service/src/app/api/routes/search.py` - API 응답 source_type 필드
- `knowledge_service/frontend/src/components/SearchResultCard.tsx` - 배지 렌더링 로직

### 영향 범위
- Hybrid Search 결과 표시 전반
- Graph 검색 결과 소스 식별

---

## 참고 자료

- commit: cf93e02 [FIX] Gateway graph 라우팅 + Neo4j subgraph 양방향 탐색 + Frontend snake_case 매핑
- commit: 3e63561 [FEAT] Graph Search 3단계 매칭 + Source Type 배지 + Graph 시각화 패널
