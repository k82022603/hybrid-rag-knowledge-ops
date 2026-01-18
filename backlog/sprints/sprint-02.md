# Sprint 02: 임베딩 & Knowledge Graph 구축

## 스프린트 정보

| 항목 | 값 |
|------|-----|
| **기간** | 2026-02-03 ~ 2026-02-14 (2주) |
| **Velocity (계획)** | 15 pts |
| **Velocity (실제)** | - |
| **Status** | planning |

---

## 스프린트 목표

> **청크 임베딩 생성 및 Knowledge Graph 구축으로 Hybrid RAG 검색 기반 완성**

핵심 목표:
1. BGE-M3 기반 다국어 벡터 임베딩 생성
2. LLM 기반 엔티티/관계 자동 추출
3. Neo4j + Elasticsearch 이중 저장소 구축

---

## 선행 조건

### Sprint 1 완료 항목 (필수)
- [x] STORY-001: 문서 업로드 API
- [x] STORY-002: Docling 문서 파싱
- [x] STORY-003: Semantic Chunking

### 인프라 준비 (Sprint 시작 전)
- [ ] Neo4j 컨테이너 설정 및 스키마 초기화
- [ ] Elasticsearch 8.x 컨테이너 설정
- [ ] 벡터 인덱스 생성 (HNSW)
- [ ] GPU 환경 확인 (임베딩 가속)

---

## 백로그

### Committed (15 pts)

| Priority | ID | 제목 | Points | Assignee | Status |
|----------|-----|------|--------|----------|--------|
| P0 | STORY-004 | BGE-M3 임베딩 생성 | 5 | - | To Do |
| P0 | STORY-005 | Knowledge Graph 엔티티 추출 | 5 | - | To Do |
| P0 | STORY-006 | Neo4j/ES 저장 | 5 | - | To Do |

### Stretch (여유 시 추가)

| ID | 제목 | Points |
|----|------|--------|
| - | 임베딩 캐싱 (Redis) | 2 |
| - | 엔티티 중복 제거 고도화 | 3 |
| - | 배치 처리 성능 최적화 | 3 |

---

## 기술 의존성

### 모델 준비
```bash
# BGE-M3 모델 사전 다운로드
python -c "from FlagEmbedding import BGEM3FlagModel; BGEM3FlagModel('BAAI/bge-m3')"

# 모델 크기: ~2.3GB
# GPU VRAM 필요: 8GB+
```

### 데이터베이스 스키마

**Neo4j**
```cypher
// 제약조건
CREATE CONSTRAINT entity_name IF NOT EXISTS
FOR (e:Entity) REQUIRE e.name IS UNIQUE;

CREATE CONSTRAINT chunk_id IF NOT EXISTS
FOR (c:Chunk) REQUIRE c.id IS UNIQUE;

// 인덱스
CREATE INDEX entity_type IF NOT EXISTS
FOR (e:Entity) ON (e.type);
```

**Elasticsearch**
```json
PUT /knowledge_chunks
{
  "settings": {
    "index": {
      "number_of_shards": 1,
      "number_of_replicas": 0
    }
  },
  "mappings": {
    "properties": {
      "embedding": {
        "type": "dense_vector",
        "dims": 1024,
        "index": true,
        "similarity": "cosine"
      }
    }
  }
}
```

---

## 일일 계획

### Week 1

#### Day 1 (02-03, Mon)
- [ ] 스프린트 킥오프 미팅
- [ ] Sprint 1 산출물 검증
- [ ] STORY-004 착수: BGE-M3 환경 설정

#### Day 2 (02-04, Tue)
- [ ] STORY-004: EmbeddingService 클래스 구현
- [ ] STORY-004: 단일 텍스트 임베딩 테스트

#### Day 3 (02-05, Wed)
- [ ] STORY-004: 배치 처리 구현
- [ ] STORY-004: GPU 최적화

#### Day 4 (02-06, Thu)
- [ ] STORY-004: 테스트 및 벤치마크
- [ ] STORY-004 완료

#### Day 5 (02-07, Fri)
- [ ] STORY-005 착수: 엔티티 추출 설계
- [ ] STORY-005: LLM 프롬프트 설계
- [ ] Week 1 리뷰

### Week 2

#### Day 6 (02-10, Mon)
- [ ] STORY-005: EntityExtractor 구현
- [ ] STORY-005: 관계 추출 구현

#### Day 7 (02-11, Tue)
- [ ] STORY-005: 엔티티 정규화/중복 제거
- [ ] STORY-005: 테스트 및 완료

#### Day 8 (02-12, Wed)
- [ ] STORY-006 착수: Neo4j 저장 서비스
- [ ] STORY-006: Elasticsearch 저장 서비스

#### Day 9 (02-13, Thu)
- [ ] STORY-006: 트랜잭션 관리 구현
- [ ] STORY-006: 벌크 저장 최적화

#### Day 10 (02-14, Fri)
- [ ] STORY-006: 통합 테스트
- [ ] STORY-006 완료
- [ ] 스프린트 리뷰 & 회고
- [ ] E2E 파이프라인 데모

---

## Definition of Done

각 Story 완료 기준:
- [ ] 모든 Acceptance Criteria 충족
- [ ] 단위 테스트 작성 (커버리지 80%+)
- [ ] 통합 테스트 통과
- [ ] 코드 리뷰 완료
- [ ] 성능 벤치마크 충족

---

## 리스크 및 블로커

| 유형 | 설명 | 영향 | 대응 | 상태 |
|------|------|------|------|------|
| Risk | GPU 미사용 시 임베딩 속도 저하 | Medium | CPU 배치 크기 조정, 비동기 처리 | Monitoring |
| Risk | LLM API 비용 증가 | Medium | DeepSeek 사용 (저비용) | Monitoring |
| Risk | Neo4j/ES 동시 저장 실패 | High | 2PC 패턴, 보상 트랜잭션 | Open |
| Blocker | Sprint 1 미완료 | Critical | Sprint 1 완료 필수 | Monitoring |

---

## 산출물

### 코드
```
knowledge_service/src/app/
├── services/
│   └── embedding.py           # STORY-004
├── graph/
│   ├── entity_extractor.py    # STORY-005
│   └── relation_extractor.py  # STORY-005
├── storage/
│   ├── neo4j_storage.py       # STORY-006
│   ├── es_storage.py          # STORY-006
│   └── transaction.py         # STORY-006
└── models/
    ├── embedding.py           # STORY-004
    └── entity.py              # STORY-005
```

### 테스트
```
knowledge_service/src/tests/
├── test_embedding.py
├── test_entity_extractor.py
├── test_neo4j_storage.py
├── test_es_storage.py
└── test_etl_pipeline.py       # E2E
```

### 문서
- [ ] 임베딩 서비스 API 문서
- [ ] Knowledge Graph 스키마 문서
- [ ] ETL 파이프라인 E2E 가이드

---

## 메트릭 목표

| 메트릭 | 목표 | 측정 방법 |
|--------|------|-----------|
| 임베딩 처리량 (GPU) | ≥ 100 chunks/s | pytest-benchmark |
| 임베딩 처리량 (CPU) | ≥ 10 chunks/s | pytest-benchmark |
| 엔티티 추출 Precision | ≥ 0.85 | 수동 검증 |
| 엔티티 추출 Recall | ≥ 0.80 | 수동 검증 |
| Neo4j 저장 (1000 노드) | < 5초 | pytest-benchmark |
| ES 벌크 저장 (1000 청크) | < 3초 | pytest-benchmark |
| 고아 노드 비율 | < 1% | Neo4j 쿼리 |
| 테스트 커버리지 | ≥ 80% | pytest-cov |

---

## E2E 파이프라인 데모

Sprint 2 완료 시점에 전체 파이프라인 데모:

```
[문서 업로드] → [Docling 파싱] → [Semantic Chunking]
      │                                    │
      ▼                                    ▼
[MinIO 저장]                    [BGE-M3 임베딩]
      │                                    │
      │                         ┌──────────┴──────────┐
      │                         ▼                     ▼
      │                  [엔티티 추출]         [ES 벡터 저장]
      │                         │
      ▼                         ▼
[PostgreSQL]              [Neo4j 그래프]
(메타데이터)              (Knowledge Graph)
```

### 데모 시나리오
1. PDF 문서 업로드 (sample.pdf)
2. 파싱 → 청킹 → 임베딩 자동 처리
3. Neo4j Browser에서 그래프 확인
4. Elasticsearch에서 벡터 검색 테스트

---

## 스프린트 리뷰

### 완료된 항목
- (스프린트 종료 후 작성)

### 미완료 항목
- (스프린트 종료 후 작성)

### 데모 노트
- (스프린트 종료 후 작성)

---

## 회고 (Retrospective)

### Keep (계속할 것)
-

### Problem (문제점)
-

### Try (시도할 것)
-

---

## 참고 자료

- [EPIC-001: Document Processing](../epics/EPIC-001-document-processing.md)
- [STORY-004: BGE-M3 임베딩](../stories/STORY-004-bge-m3-embedding.md)
- [STORY-005: 엔티티 추출](../stories/STORY-005-entity-extraction.md)
- [STORY-006: Neo4j/ES 저장](../stories/STORY-006-neo4j-es-storage.md)
- [Sprint 01 계획서](./sprint-01.md)
