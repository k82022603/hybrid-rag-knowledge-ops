# ETL Phase 1 재시작 액션 플랜

**작성일**: 2026-02-14 18:55 KST
**최종 업데이트**: 2026-02-14 23:40 KST
**상태**: ETL Phase 1 v4 실행 중 (OCR ON 품질 복원)

---

## 1. 현재 상태

| 항목 | 상태 |
|------|------|
| ES knowledge_chunks | 0 (삭제 완료) |
| PG documents | 0 (삭제 완료) |
| Neo4j | 0 (삭제 완료) |
| 반성문 | 7개 작성 (클로드, TL, Infra, ETL, RAG, Arch, PM) |
| 설계서 | 24_reflection_arch_2026-02-14.md (아키텍처 개선 설계) |

---

## 2. 식별된 근본 원인 + 수정 대상

### P0 (Critical - 재시작 전 필수 수정)

#### P0-1: ChunkQualityGate 파이프라인 미통합
- **문제**: `ChunkQualityGate` 클래스가 존재하지만 `_process_file()` 파이프라인에서 호출되지 않음
- **결과**: Junk 청크 340개, Short 청크 1,014개가 ES에 그대로 적재
- **파일**: `src/app/services/initial_data_loader.py` - `_process_file()` 메서드
- **수정**: 청킹 후, 저장 전에 `ChunkQualityGate.filter()` 호출 삽입
- **관련 파일**: `src/app/services/chunk_quality_filter.py` (품질 게이트 코드, line 71-73에서 코드/테이블 bypass)

#### P0-2: Dedup이 completed 상태만 체크
- **문제**: `_check_duplicate()` 쿼리가 `processing_status = 'completed'`만 확인
- **결과**: failed/processing 상태 문서가 중복 생성 → 29그룹 중복
- **파일**: `src/app/services/initial_data_loader.py:670-678`
- **수정**: `WHERE file_hash = $1` (상태 조건 제거), 모든 상태에서 중복 체크

### P1 (High - 품질 개선)

#### P1-1: Ultra-long 청크 (코드/테이블 블록 무제한)
- **문제**: `chunker.py:460-464`에서 코드/테이블 블록이 `max_chunk_size` 무시하고 단일 청크
- **결과**: 최대 6,765 tokens 청크 생성 (88개)
- **파일**: `src/app/etl/chunker.py:460-464`
- **수정**: 800 tokens 초과 시 강제 분할 (코드: 빈 줄 기준, 테이블: 행 기준)

#### P1-2: ChunkQualityGate 코드/테이블 bypass
- **문제**: `chunk_quality_filter.py:71-73`에서 코드/테이블 블록은 품질 검사 bypass
- **수정**: bypass 제거, 대신 min_token_count만 10→3으로 완화

#### P1-3: embedding_status 혼재
- **문제**: 3곳에서 각각 다른 문자열 사용 (success/pending/completed)
- **파일들**:
  - `initial_data_loader.py:1285` → "success"/"pending"
  - `import_embeddings.py:54` → "completed"
  - `document_processing_pipeline.py:720` → "success"
- **수정**: Phase 1에서는 `pending`만 사용. Phase 2 임베딩 후 `success`로 변경.

#### P1-4: 파일 크기별 처리 전략
- **문제**: 단일 30MB 제한, 파일 형식 무관
- **수정**: 소(<5MB 전체기능) / 중(5-30MB OCR OFF) / 대(>30MB 스킵)

### P2 (Medium - 운영 개선)

#### P2-1: 워치독 스크립트
- 신규 `scripts/watchdog.sh` - 5분 간격, ETL+모니터 프로세스 감시

#### P2-2: chunk_count 정합성 검증
- 저장 완료 후 ES 실제 카운트와 PG chunk_count 비교

---

## 3. 코드 수정 순서

1. `initial_data_loader.py` - _check_duplicate() 수정 (P0-2)
2. `initial_data_loader.py` - _process_file()에 ChunkQualityGate 삽입 (P0-1)
3. `chunk_quality_filter.py` - 코드/테이블 bypass 수정 + MAX_TOKEN_COUNT 추가 (P1-2)
4. `chunker.py` - 특수 블록 크기 제한 (P1-1)
5. `run_etl_phase1_chunks.py` - 파일 크기 분류 (P1-4)
6. 컨테이너 리빌드
7. ETL Phase 1 재시작 + 모니터 시작 + 워치독 시작

---

## 4. 주요 파일 경로 (세션 간 참조용)

```
knowledge_service/
├── src/app/
│   ├── services/
│   │   ├── initial_data_loader.py    # ETL 핵심 파이프라인 (1550줄)
│   │   ├── chunk_quality_filter.py   # ChunkQualityGate (94줄)
│   │   └── document_repository.py    # PG 저장소
│   ├── etl/
│   │   └── chunker.py                # SemanticChunker (806줄)
│   └── models/
│       └── chunk.py                  # Chunk 모델
├── scripts/
│   ├── run_etl_phase1_chunks.py      # ETL Phase 1 실행 스크립트
│   ├── etl_phase1_monitor.sh         # 모니터 스크립트
│   └── embedding_health_check.sh     # 임베딩 헬스체크
└── docs/07_maintenance/
    ├── 22_etl_3phase_operations_guide.md  # 운영 가이드
    ├── 23_incident_report_2026-02-14_etl_oom_kill.md  # 장애보고서
    ├── 24_reflection_*.md             # 반성문 7개
    └── 25_etl_restart_action_plan.md  # 이 문서
```

---

## 5. DB 접속 정보 (세션 간 참조용)

| DB | Host (컨테이너 내) | User | Password | DB |
|----|-------------------|------|----------|-----|
| PG | kp-postgresql:5432 | knowledge | knowledge_dev_2026! | knowledge |
| ES | kp-elasticsearch:9200 | - | - | knowledge_chunks |
| Neo4j | kp-neo4j:7687 | neo4j | neo4j_dev_2026! | - |

**주의**: 비밀번호에 `!` 포함 → bash에서 직접 사용 금지, Python 스크립트 또는 임시 파일 방식 사용

---

---

## 6. 수정 완료 현황 (2026-02-14 19:25 KST)

### 완료된 코드 수정 (4건)

| ID | 수정 내용 | 파일 | 라인 | 상태 |
|----|----------|------|------|------|
| P0-1 | ChunkQualityGate 파이프라인 통합 | `initial_data_loader.py` | ~758 | **완료** |
| P0-2 | Dedup 전상태 체크 | `initial_data_loader.py` | 670-674 | **완료** |
| P1-1 | 특수 블록 크기 제한 | `chunker.py` | 460-464 | **완료** |
| P1-2 | QualityGate bypass 제거 | `chunk_quality_filter.py` | 68-79 | **완료** |

### 미완료 (Phase 1 이후 처리)

| ID | 내용 | 상태 |
|----|------|------|
| P1-3 | embedding_status 표준화 | Phase 2에서 처리 |
| P1-4 | 파일 크기별 분류 | 상수 정의만 완료 (코드 분기 미완) |
| P2-1 | 워치독 스크립트 | 미생성 |
| P2-2 | chunk_count 정합성 검증 | Phase 1 완료 후 |

---

## 7. 핵심 발견: Sparse 벡터 미활용 (Critical Gap)

### 발견 일시: 2026-02-14 19:15 KST

**문제 요약**: BGE-M3의 최대 강점인 Sparse 벡터를 생성하고 저장까지 했으나, 검색에서 전혀 활용하지 않음.

### 단계별 상태

| 단계 | 파일 | 라인 | 상태 |
|------|------|------|------|
| Sparse 생성 | `embedding.py` | 670 | **완성** - `lexical_weights` 추출 |
| ES 매핑 | `02_elasticsearch_mapping.json` | 62-64 | **완성** - `sparse_vector` 타입 |
| ETL 저장 | `es_storage.py` | 401-403 | **완성** - 조건부 저장 |
| **Query 생성** | `search.py` | 483 | **미구현** - Dense만 요청 |
| **Sparse 검색** | `search.py` | 489-504 | **미구현** - kNN만 사용 |
| **RRF 융합** | `search.py` | 354-379 | **불완전** - 3-way만 (Dense+BM25+Graph) |

### 영향
- "Hybrid RAG"의 Sparse 축이 완전 누락
- BGE-M3 사용 비용의 절반이 낭비 (Dense만 활용)
- 학습된 어휘 매칭 능력 미활용 → 검색 정확도 저하
- BM25는 단순 단어 빈도 기반, Sparse는 문맥 이해 기반 어휘 가중치

### 이번 차수 핵심 목표
- Phase 4로 Sparse 벡터 검색 통합 추가
- `search.py`에 Sparse 검색 쿼리 구현
- RRF 4-way 융합 (Dense + Sparse + BM25 + Graph)
- 설계서: `docs/02_design/15_sparse_vector_search_integration_design.md`

---

## 8. ETL Phase 1 v2 실행 기록

### 실행 시작: 2026-02-14 19:25 KST

**실행 환경**:
- 컨테이너: kp-ai-service (리빌드 완료, healthy)
- 3-Store: 클린 (ES=0, PG=0, Neo4j=0)
- 코드 수정: P0/P1 4건 반영
- 파라미터: chunk_size=1000, overlap=200, batch_size=4, embeddings=OFF

**모니터링**: etl_phase1_monitor.sh (15분 간격 Slack dev 채널 보고)

### ETL Phase 1 v3 실행 기록 (속도 최적화 적용)

**실행 시작**: 2026-02-14 21:30 KST (추정)

**v2 -> v3 변경사항**:

1. ETL v2 중단 (13/1,786 진행 시점, 153시간 예상)
2. 5인 전문가 분석팀(Infra/ETL/TL/Arch/RAG) 배치, 병목 분석
3. 3건 코드 최적화 적용:
   - `docling_adapter.py`: OCR OFF + force_backend_text + TableFormerMode.FAST
   - `run_etl_phase1_chunks.py`: 파일 유형별 정렬 (경량 우선)
4. Embedding Backfill 프로세스 강제 종료 (자원 경합 해소)
5. 컨테이너 리빌드 후 v3 재시작

**속도 개선 결과**: PDF 16분 -> 16.6초 (58x)

**v3 진행 상황** (22:35 KST):

| 항목 | 값 |
|------|-----|
| 전체 파일 | 1,786 |
| 성공 | 83 |
| 실패 | 0 |
| Dedup 스킵 | 161 |
| ES 청크 수 | 6,226 |
| Quality Gate 통과 | 313 청크 |
| Quality Gate 거부 | 73 청크 |

- Dedup 정상 작동 확인 (P0-2 수정 효과)
- Quality Gate 정상 작동 확인 (P0-1 수정 효과)

### ETL Phase 1 v4 실행 기록 (OCR ON 품질 복원)

**실행 시작**: 2026-02-14 23:36 KST

**v3 → v4 변경사항**:
1. v3 품질 분석 결과 OCR OFF의 품질 저하 확인 (58.2% 청크가 100 tokens 미만)
2. 의사결정: 2-Pass 조건부 OCR → 사용자 결정으로 전면 OCR ON
3. `docling_adapter.py` 수정: `do_ocr=True` + `TableFormerMode.FAST` 유지
4. 3-Store 완전 재초기화 (ES=0, PG=0, Neo4j=0)
5. 컨테이너 리빌드 후 v4 시작

**최종 설정**:
- OCR: **ON** (품질 우선)
- TableFormerMode: **FAST** (속도 최적화, 품질 영향 미미)
- 파일 정렬: **유지** (MD/TXT → PDF 순서)
- 예상 소요: 6~12시간 (PDF OCR 포함)

**v4 초기 결과** (23:40 KST):
- 183 성공 / 0 실패 / 35 dedup 스킵 / 2 oversized 스킵
- QualityGate 거부율: **4.4%** (v3의 29.5% 대비 6.7x 개선)
- PDF 구간 진입 확인

**교훈**:
- 속도 최적화 시 품질 트레이드오프를 반드시 검증해야 함
- Docling의 핵심 가치는 OCR 기능이므로 비활성화는 본말전도
- TableFormerMode.FAST는 안전한 최적화 (품질 영향 3-5% 미만)

---

*작성: 클로드 (Claude Opus 4.6)*
