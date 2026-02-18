# Neo4j 스키마 통일 마이그레이션 보고서

**일시**: 2026-02-18 20:30 ~ 21:00 KST
**수행**: Claude Code (Opus 4.6)
**승인**: 사용자 (직접 지시)
**커밋**: ebf822b

---

## 1. 배경

Sprint 12 최종 기술부채 검토 과정에서 Neo4j 스키마 불일치가 확인되었습니다.
검색 엔진(search.py)이 참조하는 스키마와 온라인 업로드 파이프라인(neo4j_storage.py)이
생성하는 스키마가 달라, 온라인으로 업로드된 문서의 엔티티가 그래프 검색에서 누락되는 문제가 있었습니다.

### 발견 경위

| 시점 | 내용 |
|------|------|
| TechLead 분석 | TD-001 기술부채 리스크 분석 시 Neo4j 스키마 3종 혼재 식별 |
| 사용자 결정 | "검색이 참조하는 스키마로 통일하라" 직접 지시 |
| 스키마 조사 | 검색은 batch_entity_extraction.py 기준 (Batch 스키마) 사용 확인 |
| 방향 결정 | 사용자 피드백: RELATED_TO가 RELATED보다 적절 → RELATED_TO로 통일 |

## 2. 불일치 현황 (수정 전)

| 항목 | 검색 코드 (search.py) | Online (neo4j_storage.py) | Batch Script (batch_entity_extraction.py) |
|------|----------------------|--------------------------|------------------------------------------|
| Chunk 키 필드 | `Chunk {id: cid}` | `Chunk {chunk_id: ...}` | `Chunk {id: ...}` |
| Chunk→Entity | `MENTIONS` | `HAS_ENTITY` | `MENTIONS` |
| Entity↔Entity | `RELATED` | `RELATED_TO` | `RELATED` |

## 3. 코드 수정 (5개 파일)

| 파일 | 변경 내용 | 방향 |
|------|----------|------|
| `src/app/storage/neo4j_storage.py` | Chunk MERGE 키 `chunk_id` → `id`, `HAS_ENTITY` → `MENTIONS` | Online → Batch 스키마 통일 |
| `src/app/services/search.py` | `[:RELATED]` → `[:RELATED_TO]` (3곳) | RELATED_TO로 표준화 |
| `src/app/api/routes/graph.py` | `[:RELATED]` → `[:RELATED_TO]` (2곳) | RELATED_TO로 표준화 |
| `scripts/batch_entity_extraction.py` | `[:RELATED]` → `[:RELATED_TO]` (2곳) | RELATED_TO로 표준화 |
| `src/app/services/document_processing_pipeline.py` | 주석 HAS_ENTITY → MENTIONS (2곳) | 주석 정합성 |

## 4. DB 마이그레이션 실행

### 4.1 소량 마이그레이션 (즉시 실행)

| 작업 | 대상 | 건수 | 결과 |
|------|------|:----:|:----:|
| Chunk.id 필드 보정 | `chunk_id`만 있고 `id` 없는 Chunk | 11 | 완료 |
| HAS_ENTITY → MENTIONS | 오늘 테스트 업로드분 | 13 | 완료 |

### 4.2 대량 마이그레이션 (배치 실행)

| 작업 | 건수 | 배치 크기 | 소요 시간 | 방법 |
|------|:----:|:---------:|:---------:|------|
| RELATED → RELATED_TO | 298,579 | 10,000 | 25.7초 | kp-ai-service 컨테이너 내 Python 드라이버 |

실행 방법: `properties(r)`를 복사하여 새 `RELATED_TO` 관계 생성 후 기존 `RELATED` 삭제

## 5. 마이그레이션 검증

| 관계 타입 | Before | After | 상태 |
|-----------|-------:|------:|:----:|
| RELATED | 298,579 | 0 | 전량 마이그레이션 |
| RELATED_TO | 57 | 298,636 | 통합 완료 |
| MENTIONS | 404,398 | 404,411 | 통합 완료 (+13) |
| HAS_ENTITY | 13 | 0 | 전량 마이그레이션 |
| CONTAINS | 11 | 11 | 변경 없음 |
| MENTIONED_IN | 100 | 100 | 변경 없음 |
| Chunk id 누락 | 11 | 0 | 전량 보정 |

## 6. 통일된 최종 스키마

```
(Knowledge)-[:CONTAINS]->(Chunk {id})          -- 문서→청크
(Chunk)-[:MENTIONS]->(Entity)                  -- 청크→엔티티 (404K)
(Entity)-[:MENTIONED_IN]->(Knowledge)          -- 엔티티→문서
(Entity)-[:RELATED_TO]->(Entity)               -- 엔티티↔엔티티 (298K)
```

### 노드 타입

| 노드 라벨 | 키 필드 | 용도 |
|-----------|---------|------|
| Knowledge | knowledge_id | 문서 단위 (Online 파이프라인) |
| Document | id | 문서 단위 (Batch 파이프라인) |
| Chunk | id (= chunk_id) | 청크 단위 |
| Entity | name | 엔티티 (Person, Technology, Topic, Keyword 이중 라벨) |

## 7. 영향도

- **검색 기능**: 변경 없음 (기존 MENTIONS 404K + RELATED_TO로 통일)
- **온라인 업로드**: 이후 업로드되는 문서의 엔티티가 그래프 검색에서 정상 노출
- **배치 ETL**: 다음 실행부터 RELATED_TO로 생성
- **서비스 중단**: 없음 (마이그레이션 중 서비스 정상 운영)

---

*수행: Claude Code (Opus 4.6) | 2026-02-18*
