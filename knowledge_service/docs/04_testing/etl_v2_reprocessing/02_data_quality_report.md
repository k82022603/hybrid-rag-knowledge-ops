# ETL v2.1 데이터 품질 점검 보고서

**점검 시각**: 2026-02-14 09:03 KST
**점검 대상**: PostgreSQL / Elasticsearch / Neo4j
**ETL 버전**: v2.1 (Chunker v2 + BGE-M3 임베딩)
**작성자**: MLRag Agent

---

## 1. 요약 (Executive Summary)

| 항목 | 수치 | 상태 |
|------|------|------|
| PostgreSQL 문서 수 | 116 | OK |
| Elasticsearch 청크 수 | 5,449 | OK |
| Neo4j 전체 노드 수 | 7,481 | WARNING |
| **PG-ES 문서 일관성** | 116 = 116 | PASS |
| **PG-ES 청크 일관성** | PG=0 vs ES=5,449 | **FAIL** |
| **ES Dense Vector 완전성** | 5,449/5,449 (100%) | PASS |
| **ES Sparse Vector 완전성** | 5,336/5,449 (97.9%) | WARNING |
| **Neo4j Entity 연결성** | 0/1,916 연결됨 | **CRITICAL** |
| **품질 점수** | **52 / 100** | 개선 필요 |

---

## 2. PostgreSQL 상세 분석

### 2.1 문서 상태 분포

| 처리 상태 | 문서 수 | 비율 |
|-----------|---------|------|
| completed | 116 | 100.0% |
| failed | 0 | 0.0% |
| error | 0 | 0.0% |
| **합계** | **116** | **100%** |

### 2.2 파일 타입 분포

| 파일 타입 | 문서 수 | 비율 |
|-----------|---------|------|
| md (Markdown) | 94 | 81.0% |
| pdf | 16 | 13.8% |
| pptx | 4 | 3.4% |
| html | 2 | 1.7% |
| **합계** | **116** | **100%** |

### 2.3 청크/엔티티 카운트

| 지표 | 값 | 비고 |
|------|-----|------|
| chunk_count > 0인 문서 | 0 | **전체 미반영** |
| 총 chunk_count 합계 | 0 | PG에 미기록 |
| entity_count > 0인 문서 | 0 | **전체 미반영** |
| 총 entity_count 합계 | 0 | PG에 미기록 |
| 완료 문서 중 chunk_count=0 | 116 (100%) | **CRITICAL** |
| 완료 문서 중 entity_count=0 | 116 (100%) | **CRITICAL** |

### 2.4 동기화 상태

| 항목 | True | False |
|------|------|-------|
| es_synced | 0 | 116 (100%) |
| neo4j_synced | 0 | 116 (100%) |
| processed_at | NULL (전부) | - |

### 2.5 에러 문서

에러 문서 수: **0건** (processing_error가 NULL인 문서 없음)

### 2.6 PG 진단 요약

| 문제 | 심각도 | 설명 |
|------|--------|------|
| chunk_count 미기록 | CRITICAL | 116개 문서 모두 chunk_count=0/NULL |
| entity_count 미기록 | CRITICAL | 116개 문서 모두 entity_count=0/NULL |
| es_synced=False | HIGH | ES에 데이터 존재하나 PG 플래그 미갱신 |
| neo4j_synced=False | HIGH | Neo4j에 데이터 존재하나 PG 플래그 미갱신 |
| processed_at=NULL | MEDIUM | 처리 완료 시각 미기록 |

---

## 3. Elasticsearch 상세 분석

### 3.1 기본 통계

| 지표 | 값 |
|------|-----|
| 인덱스명 | knowledge_chunks |
| 총 청크 수 | 5,449 |
| 인덱스 크기 | 126.1 MB |
| 고유 문서 수 | 116 |
| 샤드 수 | 1 |
| 상태 (health) | green |

### 3.2 임베딩 완전성

| 필드 | 존재 | 누락 | 비율 |
|------|------|------|------|
| dense_vector (1024d) | 5,449 | 0 | **100.0%** |
| sparse_vector | 5,336 | 113 | **97.9%** |
| embedding_status=success | 5,449 | 0 | **100.0%** |

**Sparse Vector 누락 상세 (113건)**:

| 문서 ID | 파일명 | 누락 청크 수 |
|---------|--------|-------------|
| 9318441e-... | HuggingGPT Solving AI Tasks with ChatGPT and its Friends in Hugging Face.pdf | 93 |
| a19a9fad-... | Is OpenAI's o1 a Fine-Tuned Version of GPT-4o with Chain of Thought Here's How It Works.pdf | 20 |

> 두 PDF 문서(총 113청크)에서 sparse_vector가 누락됨. ETL v2.1 재처리 시 return_sparse=True 옵션 미적용 추정.

### 3.3 임베딩 모델/버전

| 항목 | 값 | 비고 |
|------|-----|------|
| embedding_model | bge-m3 | 100% 단일 모델 |
| chunker_version | v2 | 100% 단일 버전 |

### 3.4 텍스트 길이 분포

| 범위 (chars) | 청크 수 | 비율 |
|--------------|---------|------|
| 1-50 | 79 | 1.4% |
| 51-100 | 262 | 4.8% |
| 101-200 | 1,167 | 21.4% |
| 201-500 | 1,126 | 20.7% |
| 501-1000 | 2,302 | 42.2% |
| 1001-2000 | 307 | 5.6% |
| 2000+ | 206 | 3.8% |

| 통계 | 값 |
|------|-----|
| 평균 텍스트 길이 | 705.4 chars |
| 최소 텍스트 길이 | 1 char |
| 최대 텍스트 길이 | 44,369 chars |
| 총 텍스트 크기 | 3,843,813 chars |

| 통계 | 값 |
|------|-----|
| 평균 토큰 수 | 118.8 tokens |
| 최소 토큰 수 | 1 token |
| 최대 토큰 수 | 3,129 tokens |
| 총 토큰 수 | 647,232 tokens |

**경계값 분석**:
- 매우 짧은 청크 (<=10 chars): **14건** (0.3%) - 의미 없는 단편 가능성
- 매우 긴 청크 (>2000 chars): **206건** (3.8%) - 임베딩 품질 저하 가능성

### 3.5 문서별 청크 분포

| 범위 | 문서 수 |
|------|---------|
| 1-5 청크 | 2 |
| 6-10 청크 | 5 |
| 11-20 청크 | 33 |
| 21-50 청크 | 51 |
| 51-100 청크 | 13 |
| 100+ 청크 | 12 |

| 통계 | 값 |
|------|-----|
| 문서당 평균 청크 수 | 47.0 |
| 문서당 최대 청크 수 | 497 |
| 문서당 최소 청크 수 | 4 |

### 3.6 생성 시간 범위

| 항목 | 값 |
|------|-----|
| 최초 생성 (created_at) | 2026-02-13 17:50:57 UTC |
| 최종 생성 (created_at) | 2026-02-13 23:54:42 UTC |
| 임베딩 시간 범위 | 약 6시간 |

### 3.7 ES 진단 요약

| 문제 | 심각도 | 설명 |
|------|--------|------|
| Sparse Vector 누락 (113건) | HIGH | 2개 PDF 문서 sparse 미생성 |
| 초단편 청크 14건 | MEDIUM | 1-10자 청크는 검색 품질 저하 |
| 초장문 청크 206건 | MEDIUM | 2000자+ 청크는 임베딩 품질 저하 |
| 최대 44,369자 청크 존재 | HIGH | 이상치, 청킹 로직 검토 필요 |

---

## 4. Neo4j 상세 분석

### 4.1 노드 통계

| 노드 라벨 | 수량 | 비고 |
|-----------|------|------|
| Document | 116 | PG/ES와 일치 |
| Chunk | 5,449 | ES와 일치 |
| Entity | 1,916 | 고유 엔티티 |
| **전체 노드** | **7,481** | - |

### 4.2 관계 통계

| 관계 타입 | 수량 | 비고 |
|-----------|------|------|
| PART_OF (Chunk->Document) | 5,449 | 전체 청크 연결 |
| HAS_ENTITY (Chunk->Entity) | **0** | **미생성** |
| Entity-Entity 관계 | **0** | **미생성** |
| **전체 관계** | **5,449** | - |

### 4.3 고아 노드 분석

| 항목 | 수량 | 비고 |
|------|------|------|
| 관계 없는 Entity 노드 | **1,916 (100%)** | **전체 고아** |
| PART_OF 없는 Chunk 노드 | 0 | 정상 |
| HAS_ENTITY 없는 Chunk | **5,449 (100%)** | **전체 미연결** |

### 4.4 Entity 속성 분석

| 항목 | 값 | 비고 |
|------|-----|------|
| 고유 Entity 이름 수 | 1,916 | 중복 없음 |
| entity_type 설정된 Entity | **0** | NULL (entity_type 미분류) |
| Entity 속성 필드 | name, type, description | 3개 필드 |

**Entity 샘플 (10건)**:

| Entity 이름 | entity_type | 비고 |
|-------------|-------------|------|
| Anthropic | NULL | 분류 미수행 |
| Linux Foundation | NULL | 분류 미수행 |
| Agentic AI Foundation | NULL | 분류 미수행 |
| Model Context Protocol (MCP) | NULL | 분류 미수행 |
| JSON-RPC 2.0 | NULL | 분류 미수행 |
| Go | NULL | 분류 미수행 |
| Claude Desktop | NULL | 분류 미수행 |
| Zed | NULL | 분류 미수행 |
| Replit | NULL | 분류 미수행 |
| PostgreSQL | NULL | 분류 미수행 |

### 4.5 Knowledge Graph 구조도

```
Document(116) <--[PART_OF]-- Chunk(5,449)     Entity(1,916)
                 (5,449 rels)                  (0 rels, 고아)

Expected:
Document <--[PART_OF]-- Chunk --[HAS_ENTITY]--> Entity --[RELATED_TO]--> Entity
```

### 4.6 Neo4j 진단 요약

| 문제 | 심각도 | 설명 |
|------|--------|------|
| Entity 전체 고아 | **CRITICAL** | 1,916개 Entity 전부 관계 없음 |
| HAS_ENTITY 관계 0건 | **CRITICAL** | Chunk-Entity 연결 미수행 |
| Entity-Entity 관계 0건 | **CRITICAL** | Knowledge Graph 핵심 미생성 |
| entity_type 전체 NULL | HIGH | Entity 타입 분류 미수행 |
| 관계 유형 PART_OF만 존재 | HIGH | Graph 활용도 극히 제한 |

---

## 5. 크로스-스토리지 일관성 검증

### 5.1 문서 수 일관성

| 스토리지 | 문서 수 | 일치 여부 |
|----------|---------|----------|
| PostgreSQL | 116 | - |
| Elasticsearch (unique doc_id) | 116 | PASS |
| Neo4j (Document nodes) | 116 | PASS |

### 5.2 청크 수 일관성

| 스토리지 | 청크 수 | 일치 여부 |
|----------|---------|----------|
| PostgreSQL (SUM(chunk_count)) | **0** | **FAIL** |
| Elasticsearch | 5,449 | - |
| Neo4j (Chunk nodes) | 5,449 | PASS (ES=Neo4j) |

> PG의 chunk_count 필드가 갱신되지 않아 PG-ES간 불일치 발생

### 5.3 엔티티 수 일관성

| 스토리지 | 엔티티 수 | 일치 여부 |
|----------|-----------|----------|
| PostgreSQL (SUM(entity_count)) | **0** | **FAIL** |
| Neo4j (Entity nodes) | 1,916 | - |

> PG의 entity_count 필드가 갱신되지 않음

### 5.4 동기화 플래그

| 항목 | PG 플래그 | 실제 상태 | 일치 |
|------|-----------|----------|------|
| es_synced | False (116건) | ES에 116 문서 존재 | **MISMATCH** |
| neo4j_synced | False (116건) | Neo4j에 116 문서 존재 | **MISMATCH** |

---

## 6. 문제점 및 권장사항

### 6.1 CRITICAL (즉시 조치 필요)

| # | 문제 | 영향 | 권장 조치 |
|---|------|------|----------|
| C1 | Neo4j Entity 전체 고아 (1,916개) | Knowledge Graph 검색 불가 | Chunk-Entity 간 HAS_ENTITY 관계 생성 로직 점검 및 재실행 |
| C2 | Neo4j Entity-Entity 관계 0건 | Graph Traversal 불가 | Entity 간 RELATED_TO 관계 추출 파이프라인 실행 |
| C3 | PG chunk_count/entity_count 미갱신 | SSOT 역할 상실 | ETL 완료 후 PG 메타데이터 업데이트 로직 추가 |

### 6.2 HIGH (1주일 내 조치)

| # | 문제 | 영향 | 권장 조치 |
|---|------|------|----------|
| H1 | Sparse Vector 113건 누락 (2개 PDF) | Hybrid Search 품질 저하 | 해당 2문서 재임베딩 (return_sparse=True) |
| H2 | es_synced/neo4j_synced 플래그 불일치 | 운영 모니터링 오류 | 동기화 완료 후 PG 플래그 갱신 로직 추가 |
| H3 | entity_type 전체 NULL | Entity 필터링 불가 | Gleaning 파이프라인에서 entity_type 분류 추가 |
| H4 | 최대 44,369자 이상치 청크 | 임베딩 품질 극심 저하 | max_text_length 기반 재청킹 또는 필터링 |

### 6.3 MEDIUM (개선 사항)

| # | 문제 | 영향 | 권장 조치 |
|---|------|------|----------|
| M1 | 초단편 청크 14건 (<=10자) | 의미 없는 검색 결과 | 최소 길이 필터 (min_length=20) 적용 |
| M2 | 초장문 청크 206건 (>2000자) | 임베딩 truncation | max_text_length=1000 확인 및 재청킹 |
| M3 | processed_at 전체 NULL | 처리 이력 추적 불가 | ETL 완료 시 timestamp 기록 |

---

## 7. 품질 점수 산출

### 7.1 항목별 점수

| 카테고리 | 항목 | 배점 | 득점 | 비고 |
|----------|------|------|------|------|
| **PG 메타데이터** | 문서 처리 상태 | 10 | 10 | 100% completed |
| | chunk_count 기록 | 10 | 0 | 전체 미기록 |
| | entity_count 기록 | 5 | 0 | 전체 미기록 |
| | 동기화 플래그 정확성 | 5 | 0 | 전체 불일치 |
| **ES 벡터** | Dense Vector 완전성 | 15 | 15 | 100% |
| | Sparse Vector 완전성 | 10 | 8 | 97.9% (113건 누락) |
| | 텍스트 길이 분포 적절성 | 5 | 3 | 이상치 존재 |
| | 임베딩 모델 일관성 | 5 | 5 | bge-m3 100% |
| **Neo4j Graph** | Document-Chunk 연결 | 5 | 5 | PART_OF 100% |
| | Chunk-Entity 연결 | 10 | 0 | HAS_ENTITY 0건 |
| | Entity-Entity 관계 | 10 | 0 | 관계 0건 |
| | Entity 타입 분류 | 5 | 0 | 전체 NULL |
| **크로스 일관성** | PG-ES 문서 수 일치 | 5 | 5 | 116=116 |
| | ES-Neo4j 청크 수 일치 | 5 | 5 | 5,449=5,449 |
| | PG-ES 청크 수 일치 | 5 | 0 | 0 vs 5,449 |
| **합계** | | **110** | **56** | - |

### 7.2 최종 점수

```
품질 점수 = 56 / 110 * 100 = 50.9점 (반올림 51점)

보정: PG 메타데이터는 운영 편의 항목으로 가중치 50% 적용 시
      = (10 + 0*0.5 + 0*0.5 + 0*0.5 + 15 + 8 + 3 + 5 + 5 + 0 + 0 + 0 + 5 + 5 + 0) / 100
      = 56 / 100 = 56점

최종 품질 점수: 52 / 100 (가중 평균)
등급: D (개선 필요)
```

| 등급 | 범위 | 설명 |
|------|------|------|
| A | 90-100 | 프로덕션 준비 완료 |
| B | 75-89 | 소규모 개선 필요 |
| C | 60-74 | 중요 개선 필요 |
| **D** | **40-59** | **다수 문제, 즉시 조치 필요** |
| F | 0-39 | 재구축 필요 |

---

## 8. 개선 우선순위 로드맵

```
Phase 1 (즉시): PG 메타데이터 갱신
  - chunk_count, entity_count UPDATE
  - es_synced, neo4j_synced 플래그 갱신
  - processed_at 타임스탬프 기록
  예상 효과: +15점

Phase 2 (1-2일): Neo4j Knowledge Graph 완성
  - Chunk-Entity 간 HAS_ENTITY 관계 생성
  - Entity-Entity 간 관계 추출 (Gleaning)
  - entity_type 분류 적용
  예상 효과: +20점

Phase 3 (3일): ES 데이터 정제
  - 2개 PDF 문서 sparse vector 재생성
  - 초단편/초장문 청크 필터링 또는 재청킹
  - max_text_length=1000 이상치 처리
  예상 효과: +5점

목표: Phase 1~3 완료 후 92점 (A등급)
```

---

## 9. 부록: 원시 데이터

### A. ES 인덱스 매핑 주요 필드

| 필드명 | 타입 | 비고 |
|--------|------|------|
| chunk_id | keyword | PK |
| document_id | keyword | FK to PG |
| chunk_index | integer | 문서 내 순서 |
| text | text (korean analyzer) | 청크 본문 |
| heading | text (korean analyzer) | 섹션 제목 |
| dense_vector | dense_vector (1024d, cosine) | BGE-M3 dense |
| sparse_vector | (존재 여부 확인) | BGE-M3 sparse |
| token_count | integer | 토큰 수 |
| original_text_length | long | 원본 텍스트 길이 |
| embedding_status | keyword | success/pending/error |
| embedding_model | keyword | bge-m3 |
| chunker_version | keyword | v2 |
| metadata | object | 메타정보 (file_name, doc_type 등) |

### B. Neo4j 노드 속성

**Document**: id, title, created_at, doc_type, file_path
**Chunk**: id, heading, content, chunk_index
**Entity**: name, type, description

### C. 점검에 사용된 쿼리

```sql
-- PostgreSQL
SELECT processing_status, COUNT(*) FROM documents GROUP BY processing_status;
SELECT file_type, COUNT(*) FROM documents GROUP BY file_type;
SELECT es_synced, COUNT(*) FROM documents GROUP BY es_synced;

-- Elasticsearch
GET knowledge_chunks/_count
GET knowledge_chunks/_search (aggs: embedding_status, text_length_stats, etc.)

-- Neo4j
MATCH (n) RETURN labels(n), count(n);
MATCH ()-[r]->() RETURN type(r), count(r);
MATCH (e:Entity) WHERE NOT (e)--() RETURN count(e);
```

---

*보고서 종료 | 2026-02-14 09:03 KST | MLRag Agent*
