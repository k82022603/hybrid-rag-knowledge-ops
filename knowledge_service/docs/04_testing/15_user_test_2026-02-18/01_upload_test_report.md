# 문서 업로드 기능 E2E 테스트 보고서

**일시**: 2026-02-18 15:40 ~ 16:30 KST
**환경**: Development (localhost)
**테스터**: QA Engineer (AI Agent)
**승인**: TechLead (AI Agent)

---

## 1. 테스트 개요

Sprint 12 완료 후 UI 기반 사용자 테스트의 일환으로 문서 업로드 기능을 검증.

### 테스트 범위

- 파일 업로드 API (Direct + Nginx 프록시)
- 파일 형식별 처리 (TXT, MD, HTML)
- 인증/인가 검증
- Triple-Store 반영 검증 (PostgreSQL, Elasticsearch, Neo4j)
- 에러 처리 및 입력값 검증

## 2. 테스트 결과 (수정 전)

### 2.1 업로드 기능 테스트 (13개 케이스)

| # | 테스트 케이스 | HTTP | 상태 | 결과 | 비고 |
|---|-------------|:----:|:----:|:----:|------|
| 1 | TXT 업로드 (Direct :8000) | 201 | completed | PASS | 457B, document_id 반환 |
| 2 | MD 업로드 (Direct, 508B) | 201 | failed | WARN | "청크를 생성할 수 없습니다" |
| 3 | HTML 업로드 (Direct, 331B) | 201 | failed | WARN | "품질 기준 미달" |
| 4 | 미지원 형식 (.xyz) | 400 | - | PASS | 에러 메시지 반환 |
| 5 | TXT 업로드 (Nginx :80) | 201 | completed | PASS | 프록시 정상 |
| 6 | MD 업로드 (Nginx, 508B) | 201 | failed | WARN | Direct와 동일 |
| 7 | 문서 목록 조회 | 200 | - | PASS | 전체 표시 |
| 8 | 큰 MD 업로드 (2829B) | 201 | completed | PASS | 정상 처리 |
| 9 | **인증 없이 업로드** | **201** | completed | **FAIL** | 보안 이슈 |
| 10 | 파일 없이 업로드 | 422 | - | PASS | 검증 정상 |
| 11 | 메타데이터 포함 업로드 | 201 | completed | PASS | metadata 저장 |
| 12 | 문서 다운로드 | 200 | - | PASS | 원본 반환 |
| 13 | Nginx 경유 상태 조회 | 200 | - | PASS | 정상 |

**통과율**: PASS 9/13 (69%), WARN 3/13, FAIL 1/13

### 2.2 Triple-Store 반영 검증

| Store | 문서 등록 | 청크 생성 | 상태 |
|-------|:---------:|:---------:|:----:|
| PostgreSQL | 5/5 | chunk_count=0 | 부분 FAIL |
| Elasticsearch | 5/5 | 6건 (임베딩 완료) | PASS |
| Neo4j | 0/5 | 0건 | FAIL |

### 2.3 Triple-Store 반영 검증 (수정 후)

| Store | 문서 등록 | 청크 생성 | 엔티티 | 상태 |
|-------|:---------:|:---------:|:------:|:----:|
| PostgreSQL | OK | chunk_count 갱신 | entity_count 갱신 | PASS |
| Elasticsearch | OK | 청크 + 임베딩 | - | PASS |
| Neo4j | OK | Knowledge+Chunk+CONTAINS | Entity+HAS_ENTITY+RELATED_TO | PASS |

## 3. 발견된 이슈 및 조치

### 이슈 #1: 인증 미적용 [HIGH] -- 수정 완료

- **현상**: `/api/v1/documents/upload` 등 13개 엔드포인트에 JWT 인증 없이 접근 가능
- **영향 범위**: documents.py (7개), extract.py (3개), embed.py (3개)
- **원인**: get_current_user dependency 누락
- **조치**: 3개 라우트 파일 전체에 Depends(get_current_user) 추가
- **검증**: 인증 없이 요청 시 401 반환 확인

### 이슈 #2: Neo4j 미동기화 [HIGH] -- 수정 완료

- **현상**: 실시간 업로드 후 Neo4j에 Document/Chunk 노드 미생성
- **원인**: 업로드 파이프라인에 Neo4j 기본 노드 생성 로직 없음 (ETL Phase 3에만 의존)
- **조치**: 업로드 시 Knowledge 노드 + Chunk 노드 + CONTAINS 관계 즉시 생성
- **설계 판단**: 기본 그래프 구조는 즉시 생성, 엔티티 추출은 Phase 3에서 보강 (2단계 전략)
- **검증**: Neo4j에서 Knowledge->Chunk 관계 확인

### 이슈 #3: PG chunk_count 미갱신 [MED] -- 수정 완료

- **현상**: ES에 청크 존재하나 PG documents.chunk_count = 0
- **원인**: document_repository.update_status()가 chunk_count 파라미터 미지원
- **조치**: update_status() 확장 + 파이프라인 완료 시 chunk_count 전달
- **검증**: 업로드 후 PG chunk_count > 0 확인

### 이슈 #4: PG es_synced 미갱신 [MED] -- 수정 완료

- **현상**: ES 저장 + 임베딩 완료됐으나 es_synced = false
- **원인**: 파이프라인 완료 콜백에서 es_synced/neo4j_synced 미갱신
- **조치**: ES 인덱싱 후 es_synced=True, Neo4j 저장 후 neo4j_synced=True 설정
- **검증**: PG es_synced=true + es_synced_at 타임스탬프 확인

### 이슈 #5: 소형 파일 안내 부족 [LOW] -- 수정 완료

- **현상**: 4B 파일 업로드 시 불명확한 에러
- **조치**: 100B 미만 파일 업로드 시 400 + 구체적 안내 메시지 반환
- **검증**: "파일 크기가 너무 작습니다" 메시지 반환 확인

### 이슈 #6: 엔티티 추출 온라인 미수행 [HIGH] -- 수정 완료

- **현상**: 온라인 업로드 시 엔티티 추출이 수행되지 않음 (배치 ETL Phase 3에만 의존)
- **사용자 요구**: "배치는 배치, 온라인은 온라인. 엔티티 추출도 함께 해주세요"
- **조치**:
  - `document_processing_pipeline.py` Step 6b: 엔티티 추출 항상 실행되도록 수정
  - `neo4j_storage.py`: save_chunk_entities() 메서드 추가 (Chunk→Entity HAS_ENTITY 관계 생성)
  - Entity 노드에 `:Entity` 이중 라벨 적용 (Person/Technology 등 + Entity)
- **검증 결과**:
  - 테스트 문서(844B) 업로드 → entity_count=39, HAS_ENTITY 39개, RELATED_TO 25개
  - PG: entity_count 갱신 확인
  - Neo4j: Entity 노드 + HAS_ENTITY + RELATED_TO + MENTIONED_IN 관계 모두 생성 확인

## 4. 수정 파일 목록

| 파일 | 수정 내용 |
|------|----------|
| `src/app/api/routes/documents.py` | JWT 인증 추가 (4개 엔드포인트) + 최소 크기 검증 |
| `src/app/api/routes/extract.py` | JWT 인증 추가 (3개 엔드포인트) |
| `src/app/api/routes/embed.py` | JWT 인증 추가 (3개 엔드포인트) |
| `src/app/services/document_repository.py` | update_status() 확장 (chunk_count, es_synced, neo4j_synced) |
| `src/app/services/document_processing_pipeline.py` | Neo4j 노드 생성 + PG 메타데이터 갱신 + 에러 메시지 개선 + 엔티티 추출 온라인 실행 |
| `src/app/storage/neo4j_storage.py` | Chunk document_id 추가, Entity 이중 라벨, save_chunk_entities() |

## 5. 보안 감사 결과

### 인증 적용 현황 (수정 후)

| 라우트 파일 | 엔드포인트 수 | 인증 적용 | 상태 |
|------------|:----------:|:---------:|:----:|
| auth.py | 4 | 공개 (로그인/등록) | OK |
| search.py | 5 | 전체 적용 | OK |
| graph.py | 3 | 전체 적용 | OK |
| cache.py | 2 | 전체 적용 | OK |
| documents.py | 7 | 전체 적용 (**수정됨**) | OK |
| extract.py | 3 | 전체 적용 (**수정됨**) | OK |
| embed.py | 3 | 전체 적용 (**수정됨**) | OK |

## 6. 교훈 및 권장사항

1. **새 라우트 파일 생성 시 인증 체크리스트 필수**: 향후 새 API 라우트 추가 시 인증 dependency 적용 여부 확인
2. **3-Store 일관성 테스트 자동화**: 업로드 후 PG/ES/Neo4j 동시 검증하는 통합 테스트 추가 권장
3. **최소 파일 크기 정책 문서화**: 100B 최소 기준을 운영 매뉴얼에 반영

## 7. 온라인 업로드 파이프라인 (수정 후)

```
파일 업로드 (POST /upload)
    ↓
파싱 (Docling)
    ↓
청킹 (품질 게이트)
    ↓
ES 저장 (dense + sparse 벡터)
    ↓
임베딩 (BGE-M3)
    ↓
Neo4j 기본 노드 (Knowledge + Chunk + CONTAINS)
    ↓
엔티티 추출 (DeepSeek V3.2)
    ↓
Neo4j 엔티티 (Entity + HAS_ENTITY + RELATED_TO + MENTIONED_IN)
    ↓
PG 메타데이터 갱신 (chunk_count, entity_count, es_synced, neo4j_synced)
    ↓
완료 (status = completed)
```

---

*테스트: QA Engineer (AI Agent) | 분석: TechLead (AI Agent) | 수정: RAG Engineer (AI Agent)*
*문서: Code Documenter (AI Agent) | 2026-02-18*
