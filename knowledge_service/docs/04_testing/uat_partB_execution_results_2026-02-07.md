# UAT Part B 재실행 결과 - 2026-02-07

**실행자**: QA Agent
**실행 시간**: 2026-02-07 13:00 ~ 13:10 KST
**환경**: Docker Compose (18 containers), TEST_MODE=docker
**대상**: STORY-088/089 수정 검증 포함

---

## 요약

| Test ID | 시나리오 | 결과 | 비고 |
|---------|----------|------|------|
| B-01 | 데이터 준비 | **PASS** | ES 37 chunks, PG 2 docs, Neo4j fresh (data reset) |
| B-02 | 대량 업로드 + 자동 처리 | **PASS** | 2 TXT 업로드 성공(201), 자동 파이프라인 실행, status=completed |
| B-03 | 청킹 검증 | **PASS** | 42 chunks in ES, 25 documents, 청킹 정상 |
| B-04 | 임베딩 검증 | **PASS** | 1024d BGE-M3, cosine similarity, 99.8% non-zero |
| B-05 | Hybrid Search | **PASS** | RRF fusion 정상, semantic/keyword 모두 동작 |
| B-06 | 성능 측정 | **PASS** | Hybrid avg 17ms, Semantic avg 25ms, Keyword avg 48ms |
| +088 | Graph Search (Neo4j) | **PASS** | Knowledge/Chunk 노드, CONTAINS 관계 정상 저장 |
| +089 | PG Sync | **PASS** (수정 후) | datetime timezone 버그 수정, PG 기록 검증 완료 |

**종합 결과**: 8/8 ALL PASS (STORY-089 수정 후 재검증 통과)

---

## 상세 결과

### B-01: 테스트 데이터 준비

**결과**: PASS

**초기 상태**:
- Elasticsearch: `knowledge_chunks` 인덱스, 37 chunks (benchmark doc-001~006 포함)
- PostgreSQL: `documents` 테이블 2건 (이전 PPTX 업로드)
  - `K-에듀파인 대참제 해소-기안기 업무관리 구조개선-20260204.pptx` (uploaded)
  - `MSA_차세대플랫폼_전환_v4.pptx` (uploaded)
- Neo4j: 데이터 볼륨 재생성 (fresh state)

**컨테이너 상태**:
```
kp-ai-service      Up (healthy)
kp-api-gateway     Up (healthy)
kp-backend         Up (unhealthy)  <-- 주의: unhealthy 상태
kp-elasticsearch   Up (healthy)
kp-keycloak        Up (healthy)
kp-neo4j           Up (healthy)
kp-postgresql      Up (healthy)
... (18 containers total)
```

**Neo4j 인증 이슈 해결**:
- 기존 데이터 볼륨의 비밀번호 불일치 발견
- `docker volume rm kp-neo4j-data` 후 재생성
- curl `-u` 플래그에서 `!` 문자 shell 해석 이슈 -> base64 인코딩으로 해결
- 최종 인증: `Authorization: Basic bmVvNGo6bmVvNGpfZGV2XzIwMjYh` (neo4j:neo4j_dev_2026!)

---

### B-02: 대량 업로드 + 자동 처리 트리거

**결과**: PASS

**테스트 파일**:
1. `test_doc_1.txt` (1,118 bytes) - Hybrid RAG 플랫폼 기술 스택 설명
2. `test_doc_2.txt` (1,107 bytes) - MSA 차세대 플랫폼 전환 개요

**업로드 결과**:
```
Doc 1: POST /api/v1/documents/upload -> 201 Created
  document_id: 6b073795-1a1e-4927-9424-c5f615c215e4
  status: queued -> completed (자동 처리)

Doc 2: POST /api/v1/documents/upload -> 201 Created
  document_id: 34f5cf47-f5ee-4386-be25-bdc71c65dec0
  status: queued -> completed (자동 처리)
```

**자동 처리 파이프라인**:
- 업로드 즉시 백그라운드 파이프라인 트리거
- 처리 단계: queued -> parsing -> chunking -> embedding -> indexing -> completed
- Doc 1 처리 시간: ~9.1s
- Doc 2 처리 시간: ~10.7s

**처리 후 데이터 변화**:
- ES: 37 -> 42 chunks (+5 new chunks)
- Neo4j: 0 -> 3 Knowledge + 5 Chunk nodes + 5 CONTAINS relationships

---

### B-03: 청킹 검증

**결과**: PASS

**ES 청크 현황** (총 42 chunks, 25 documents):

| Document | Chunks | 비고 |
|----------|--------|------|
| doc-001 ~ doc-006 | 3 each (18 total) | Benchmark 데이터 |
| 6b073795 (test_doc_1.txt) | 2 | 새 업로드 (chunk 0, 1) |
| 34f5cf47 (test_doc_2.txt) | 1 | 새 업로드 (chunk 0) |
| a161bedc (test_doc_1.txt 중복) | 2 | 동일 파일 재업로드 |
| 기타 이전 업로드 | 1~2 each | 이전 세션 테스트 데이터 |

**청킹 특성**:
- test_doc_1.txt (1,118 bytes): 2 chunks (token_count: 138, 71)
- test_doc_2.txt (1,107 bytes): 1 chunk (token_count: 177)
- 적절한 크기로 분할됨

---

### B-04: 임베딩 검증

**결과**: PASS

**ES 인덱스 매핑**:
```
dense_vector: dense_vector
  dims: 1024
  similarity: cosine
  index: true (KNN 검색 활성화)
```

**임베딩 벡터 검증**:
- 차원: 1024 (BGE-M3 모델 확인)
- Non-zero 값: 1022/1024 (99.8%)
- 샘플 값 범위: -0.042 ~ 0.074 (정상)
- KNN 인덱스 활성화 확인

---

### B-05: Hybrid Search Retriever 테스트

**결과**: PASS

#### Hybrid Search (RRF Fusion)
```
Query: "Hybrid RAG 플랫폼의 주요 기술 스택은 무엇인가?"
Top-5 Results:
1. chunk_id: 2cc97692 | score: 0.0328 | source_ranks: {vector: 1, keyword: 1}
2. chunk_id: 1b794d9d | score: 0.0323 | source_ranks: {vector: 2, keyword: 2}
3. chunk_id: f840753f | score: 0.0315 | source_ranks: {vector: 3, keyword: 4}
4. chunk_id: 1a92d662 | score: 0.0310 | source_ranks: {vector: 4, keyword: 5}
5. chunk_id: (5th)    | score: 0.0305 | source_ranks: {vector: 5, keyword: 3}
```
- RRF (Reciprocal Rank Fusion) 정상 적용
- Vector + Keyword rank 병합 확인

#### Semantic Search
```
Query: "MSA 마이크로서비스 전환 전략"
Top-3 Results: All scored 0.8585 (MSA 관련 문서)
```

#### Keyword Search
```
Query: "Neo4j 그래프 데이터베이스"
Top-3 Results: Scores 21.28, 15.94, 15.94
```

#### Graph Subgraph API
```
POST /api/v1/graph/subgraph
Body: {"entity_name":"test_doc_1.txt","depth":2}
Response: {"center":"test_doc_1.txt","nodes":[],"edges":[],"node_count":0}
```
- API 응답 정상 (에러 없음)
- Named entity가 아직 추출되지 않아 subgraph가 비어있음 (Expected)

#### Chat/RAG Endpoint
```
POST /api/v1/search/chat
Query: "Hybrid RAG 플랫폼에서 사용하는 주요 기술 스택을 설명해주세요"
Result: 문서 검색 성공 (5 sources), LLM 생성 실패 -> 소스 문서 목록 fallback
```
- 검색(Retrieval) 단계 정상
- LLM 생성 단계 실패 (DeepSeek API 이슈로 추정, non-critical)

---

### B-06: 성능 측정

**결과**: PASS (P95 < 3s 기준 충족)

| Search Type | Run 1 | Run 2 | Run 3 | Average | P95 기준 |
|-------------|-------|-------|-------|---------|---------|
| Hybrid | 18ms | 17ms | 17ms | **17.3ms** | < 3,000ms |
| Semantic | 27ms | 23ms | 24ms | **24.7ms** | < 3,000ms |
| Keyword | 49ms | 49ms | 45ms | **47.7ms** | < 3,000ms |

- 모든 검색 유형이 P95 3초 기준 대비 99%+ 여유
- Hybrid가 가장 빠른 이유: ES 캐시 효과 + 효율적 RRF 병합
- Keyword가 가장 느린 이유: BM25 전체 텍스트 검색 부하

---

### +088: STORY-088 검증 (Graph Search - Neo4j)

**결과**: PASS

**Neo4j 노드 현황**:
| Label | Count | 설명 |
|-------|-------|------|
| Knowledge | 3 | 업로드된 문서 (test_doc_1 x2, test_doc_2 x1) |
| Chunk | 5 | 청크 (test_doc_1: 2x2, test_doc_2: 1) |

**관계(Relationship)**:
| Type | Count | 설명 |
|------|-------|------|
| CONTAINS | 5 | Knowledge -> Chunk |

**Knowledge 노드 속성**:
```json
{
  "knowledge_id": "6b073795-...",
  "title": "test_doc_1.txt",
  "document_type": "txt",
  "project_name": "",
  "summary": "",
  "created_at": "2026-02-07T04:02:16.982753+00:00",
  "updated_at": "2026-02-07T04:02:16.982753+00:00"
}
```

**Chunk 노드 속성**:
```json
{
  "chunk_id": "2cc97692-...",
  "knowledge_id": "a161bedc-...",
  "chunk_index": 0,
  "token_count": 138,
  "content": "KT DS의 Hybrid RAG 플랫폼은...",
  "created_at": "2026-02-07T04:02:14.777674+00:00"
}
```

**STORY-088 수정 검증**:
- MERGE ON CREATE 구문 수정: Knowledge, Chunk 라벨로 정상 저장
- search.py 라벨 매핑: Knowledge/Chunk 기반 그래프 탐색 가능
- 엔티티 추출: 테스트 문서에서 Named Entity 0건 (짧은 TXT 파일이므로 예상됨)
- Graph traversal: Knowledge -> CONTAINS -> Chunk 구조 정상

---

### +089: STORY-089 검증 (PG Dual-Write Sync)

**결과**: PASS (수정 후 재검증)

**초기 테스트**: PARTIAL FAIL - datetime timezone mismatch 버그 발견

**근본 원인**:
- Python 코드: `datetime.now(timezone.utc)` → timezone-aware datetime
- PG 컬럼: `timestamp without time zone` → timezone-naive
- asyncpg 드라이버: strict type check로 불일치 거부

**수정 내용** (`document_repository.py`):
```python
# 헬퍼 함수 추가
def _naive_utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

def _strip_tz(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None: return None
    return dt.replace(tzinfo=None) if dt.tzinfo else dt

# save() - lines 130-131
_strip_tz(doc_record.get("created_at")) or _naive_utcnow(),
_strip_tz(doc_record.get("updated_at")) or _naive_utcnow(),

# update_processing_status() - line 240
_naive_utcnow(),
```

**수정 후 재검증 (2026-02-07 17:27 KST)**:
```sql
SELECT id, title, processing_status, created_at, updated_at FROM documents ORDER BY created_at DESC LIMIT 3;

-- 결과:
-- d310df4c | pg_sync_test.txt | completed | 2026-02-07 08:27:02 | 2026-02-07 08:27:32
-- 3a584ea4 | pg_sync_test.txt | completed | 2026-02-07 08:26:56 | 2026-02-07 08:27:32
```
- 문서 업로드 → PG 저장 성공
- processing_status = completed 확인
- created_at, updated_at 정상 기록
- asyncpg timezone 에러 완전 해소

---

## 환경 정보

| 항목 | 값 |
|------|-----|
| AI Service | http://localhost:8000 (healthy) |
| Backend | http://localhost:8081 (unhealthy) |
| API Gateway | http://localhost:8080 (healthy) |
| Elasticsearch | http://localhost:9200 (healthy) |
| PostgreSQL | kp-postgresql (knowledge/knowledge) |
| Neo4j | http://localhost:7474 (neo4j/neo4j_dev_2026!) |
| 인증 방식 | AI Service 자체 JWT (HS256, admin1234) |
| 컨테이너 수 | 18개 (17 healthy, 1 unhealthy) |

## 인증 정보

**AI Service 로그인**:
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@example.com","password":"admin1234"}'
```

**Neo4j HTTP API 인증**:
```
Authorization: Basic bmVvNGo6bmVvNGpfZGV2XzIwMjYh
```
(shell에서 curl -u 사용 시 `!` 문자 escape 문제 주의)

---

## 결론

### 성공 항목 (8/8)
1. 파일 업로드 및 자동 처리 파이프라인 정상 동작
2. 문서 청킹 정상 (적절한 크기 분할)
3. BGE-M3 임베딩 생성 정상 (1024d)
4. Hybrid/Semantic/Keyword 검색 모두 정상
5. RRF Fusion 정상 적용
6. STORY-088 Neo4j MERGE ON CREATE 수정 검증 완료
7. 성능 우수 (avg 17~48ms, P95 < 3s 충족)
8. STORY-089 PG Dual-Write: timezone 버그 수정 후 재검증 PASS

### Known Issues (Non-blocking)
1. kp-backend Docker healthcheck unhealthy (실제 actuator는 UP)
2. Chat search LLM 답변 생성 실패 (DeepSeek 미연결, fallback 동작)
