# 이슈 보고서: Graph Search 항상 0건 반환

**Issue ID**: ISSUE-010
**Date**: 2026-02-07
**Reporter**: Claude (Opus 4.6)
**Severity**: High (기능 미작동)
**Status**: RESOLVED
**Resolved Date**: 2026-02-07
**Found In**: UAT 수동 테스트

---

## 1. 이슈 요약

| 항목 | 내용 |
|------|------|
| **증상** | Chat Search에서 어떤 쿼리를 입력해도 Graph 소스 검색 결과가 항상 0건 반환. [출처] 표시에 Graph 소스가 없음 |
| **영향 범위** | Graph Search 전체 (`_graph_search()` 메서드) |
| **근본 원인** | Cypher 쿼리의 CONTAINS 매칭 방향이 잘못되어 엔티티 매칭 실패 |
| **긴급도** | High - Hybrid RAG의 핵심 기능인 Graph 검색이 완전 미작동 |

---

## 2. 발견 경위

UAT 수동 테스트 과정에서 Chat Search 기능의 [출처] 표시를 점검하던 중 발견.

```
환경: Docker Compose (WSL2, 18 containers)
발견 방법: UAT 수동 테스트 - Chat Search 결과에서 Graph 소스 부재 확인
발견 일시: 2026-02-07
```

---

## 3. 증상 상세

Chat Search에서 다양한 쿼리를 입력하여 테스트한 결과, Graph 소스 검색 결과가 모든 경우에서 0건 반환됨.

- "Neo4j 그래프 데이터베이스" -> Graph 0건
- "RAG 파이프라인과 LangGraph" -> Graph 0건
- "LLM 중심으로 관련 기술" -> Graph 0건

[출처] 표시에서 Vector, Keyword 소스는 정상적으로 표시되나, Graph 소스는 전혀 나타나지 않음.

---

## 4. 근본 원인 분석

### 4.1 Cypher 쿼리 매칭 방향 오류

`search.py`의 `_graph_search()` 메서드에서 사용하는 Cypher 쿼리의 CONTAINS 매칭 방식이 잘못됨.

**기존 로직 (오류)**:
```
e.name CONTAINS word
```

이 로직은 엔티티 이름 안에 쿼리 단어가 포함되어야 매칭됨.

**문제 시나리오**:
```
쿼리: "LLM 중심으로 기술"
분할 단어: ["LLM", "중심으로", "기술"]

엔티티 이름 예시:
- "DeepSeek V3.2"
- "LangGraph"
- "Neo4j"

결과: "DeepSeek V3.2" CONTAINS "LLM" -> False
       "DeepSeek V3.2" CONTAINS "중심으로" -> False
       "DeepSeek V3.2" CONTAINS "기술" -> False
       ... 모든 조합에서 False -> 0건 반환
```

핵심 문제는 사용자 쿼리의 단어가 엔티티 이름의 부분 문자열이 되는 경우가 거의 없다는 점이다. 오히려 엔티티 이름이 쿼리 문장 안에 포함되는 경우가 훨씬 자연스러움 (예: "Neo4j 그래프 데이터베이스" 쿼리에 "Neo4j" 엔티티 포함).

---

## 5. 해결 방안

### 5.1 3단계 CONTAINS 매칭 전략 도입

| 단계 | 전략 | 설명 | 예시 |
|------|------|------|------|
| **Step 1** | 역방향 매칭 | `toLower(query) CONTAINS toLower(entity_name)` | "neo4j 그래프 데이터베이스" CONTAINS "neo4j" -> True |
| **Step 2** | 정방향 매칭 | `toLower(entity_name) CONTAINS toLower(word)` | 엔티티 이름 안에 쿼리 단어 포함 |
| **Step 3** | 폴백 매칭 | Step 1+2 결과가 0건이면 Chunk content에서 키워드 검색 | 엔티티 매칭 실패 시 문서 내용에서 검색 |

### 5.2 매칭 우선순위

```
Step 1 (역방향) → Step 2 (정방향) → Step 3 (폴백)
         |                |                |
    쿼리에 엔티티     엔티티에 단어     Chunk 내용에서
    이름 포함          포함             키워드 검색
```

---

## 6. 수정 파일

| 파일 | 변경 내용 |
|------|----------|
| `knowledge_service/src/app/services/search.py` | `_graph_search()` 3단계 매칭 전략 적용, `_rrf_fusion()` primary source 결정 로직 추가 |
| `knowledge_service/src/app/services/rag_pipeline.py` | graph_context 전달 로직 추가 |
| `knowledge_service/src/app/agents/rag_workflow.py` | graph_context 전달 로직 추가 |

---

## 7. 검증 결과

### 7.1 수정 전후 비교

| 테스트 쿼리 | 수정 전 | 수정 후 | 매칭 전략 |
|------------|--------|--------|----------|
| "Neo4j 그래프 데이터베이스" | 0건 | 4건 | Step 1 (역방향) |
| "RAG 파이프라인과 LangGraph" | 0건 | 5건 | Step 1+2 |
| "LLM 중심으로 관련 기술" | 0건 | 5건 | Step 3 (폴백) |

### 7.2 검증 상태

- [x] 3가지 대표 쿼리에서 Graph 소스 정상 반환 확인
- [x] [출처] 표시에 Graph 소스 포함 확인
- [x] RRF fusion에서 primary source 정확히 결정 확인

---

## 8. 부수 이슈 (함께 수정)

### 8.1 RRF fusion source 고정 문제

| 항목 | 내용 |
|------|------|
| **증상** | 융합 후 source가 항상 "vector"로 고정됨 |
| **원인** | `_rrf_fusion()` 메서드에서 primary source 결정 로직 부재 |
| **해결** | primary source 결정 로직 추가 - 가장 높은 RRF 점수의 소스를 primary로 설정 |

### 8.2 Admin 비밀번호 해시 불일치

| 항목 | 내용 |
|------|------|
| **증상** | Admin 로그인 실패 |
| **원인** | `.env` 파일의 비밀번호 해시가 `admin1234`에 매칭됨 |
| **해결** | `admin123!`로 비밀번호 해시 재생성 |

### 8.3 Redis 캐시 잔존

| 항목 | 내용 |
|------|------|
| **증상** | 코드 수정 후에도 이전 캐시 결과가 반환됨 |
| **원인** | 코드 변경 후 Redis 캐시가 자동으로 무효화되지 않음 |
| **해결** | 수동 캐시 클리어 수행 |

---

## 9. 향후 조치

| 조치 항목 | 우선순위 | 상태 |
|----------|---------|------|
| 엔티티 1,000건 이상 시 Neo4j Full-text Index 적용 검토 | Medium | 미착수 |
| 배포 후 캐시 자동 무효화 스크립트 추가 고려 | Low | 미착수 |

---

## 10. 참고 정보

- **관련 파일**: `knowledge_service/src/app/services/search.py`
- **관련 기능**: Chat Search, Hybrid RAG Pipeline
- **영향 컴포넌트**: Graph Search, RRF Fusion, RAG Pipeline
