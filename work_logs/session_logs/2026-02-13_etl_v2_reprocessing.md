# Session Log - 2026-02-13/14

**Session ID**: 2026-02-13_etl_v2_reprocessing
**시작 시간**: ~23:30 KST (이전 세션 계속)
**종료 시간**: 03:10 KST (ETL 가동 중)
**모델**: Claude Opus 4.6 (claude-opus-4-6)

---

## 세션 요약

ETL v2 전체 재처리를 위한 코드 수정, 전문가 리뷰, 데이터 초기화, Docker 리빌드, ES 날짜 포맷 이슈 해결, batch_size 최적화를 수행. ETL v2 정상 가동 확인 (02:48 KST 시작).

---

## 완료된 작업

### 1. 전문가 3인 코드 리뷰 (주요)

#### TL 전문가 (Task #1)
- init-db.py 매핑 타입 정렬 (integer→long 통일, date 포맷 명시)
- FIX 5건, INFO 7건

#### ETL 전문가 (Task #2)
- `initial_data_loader.py` v2 추적 필드 5개 누락 발견 + 즉시 수정
  - `original_text_length`, `embedding_status`, `chunker_version`, `embedded_at`, `embedding_model`
- FIX 1건, INFO 7건

#### RAG 전문가 (Task #3)
- `test_embedding_service.py` mock 데이터 키 타입 보정 (int→str) 7건
- FIX 1건, INFO 4건
- 핵심 발견: Sparse 벡터는 저장만 하고 검색에는 아직 미사용 (향후 RRF 4-Channel)

### 2. 설계문서 미반영 항목 식별 + 수정 (주요)

- `run_etl_full.py`: chunk_size **600→1000**, overlap **100→200** (설계문서 §14.5)
- `pyproject.toml`: **FlagEmbedding** 패키지 추가 (Sparse Vector 필수 의존성)

### 3. 데이터 초기화 (주요, 다회 수행)

- ES `knowledge_chunks` 인덱스 삭제 + v2 매핑으로 재생성 (15필드)
- Neo4j 108,412 노드 배치 삭제 (5,000건 단위 OOM 방지)
- PG `documents` 1,449건 삭제 (file_hash dedup 리셋)

### 4. ES 날짜 포맷 이슈 해결 (Critical)

- **문제**: ES bulk 인덱싱 시 `created_at` 필드 날짜 파싱 실패 (silent failure)
- **원인**: `yyyy-MM-dd'T'HH:mm:ss.SSSZ` 매핑에서 `Z`는 timezone offset(`+0000`)을 의미, Python `isoformat()`의 microseconds+리터럴Z와 불일치
- **해결**: `strict_date_optional_time||epoch_millis` 형식으로 ES 매핑 전환 (모든 ISO 8601 형식 수용)
- init-db.py도 동일하게 업데이트

### 5. EmbeddingService batch_size 최적화

- **문제**: config.py 기본값 `batch_size=32` (CPU에서 매우 느림, 0.1 texts/s)
- **해결**: `config.py` default를 `32→4`로 변경 (CPU 확정 최적값)
- run_etl_full.py의 `batch_size=4`와 일치

### 6. Docker 리빌드 + 의존성 해결

- `--no-cache` 빌드 (FlagEmbedding 추가)
- 컨테이너 내 추가 설치: `datasets>=3.0` (4.5.0), `peft` (0.18.1)
- 빌드 성공 후 ai-service 재시작

### 7. ETL v2 시작 + 검증

- 02:48 KST ETL 시작 (nohup)
- 03:05 KST 기준: ES 115 chunks, PG 4 docs, Errors 0
- v2 데이터 품질 확인: chunker_version=v2, embedding_model=bge-m3, sparse_vector 존재

### 8. 문서 작업

- `docs/04_testing/etl_v2_reprocessing/00_work_plan.md` 작성
- Slack dev 채널 상세 진행 보고 2회

---

## 주요 결정사항

| 결정 | 내용 | 근거 |
|------|------|------|
| chunk_size 변경 | 600→1000자 | 설계문서 §14.5 분석표, BM25 TF 개선 |
| chunk_overlap 변경 | 100→200자 | RAGChatbotServer 검증 수치 |
| FlagEmbedding 추가 | pyproject.toml | Sparse Vector 생성 필수, sentence-transformers 폴백 불가 |
| ES 날짜 포맷 | strict_date_optional_time | 모든 ISO 8601 형식 수용, Python isoformat() 호환 |
| batch_size 기본값 | 32→4 | CPU 환경 확정 최적값 (2026-02-10) |
| 전체 리빌드 | --no-cache | FlagEmbedding 추가로 전체 의존성 재빌드 필요 |
| 불필요 컨테이너 중지 | 12개 중지 | ETL 시 CPU/메모리 확보 (6개만 운영) |

---

## 변경된 파일 목록

```
knowledge_service/
├── scripts/
│   └── run_etl_full.py                 # chunk_size=1000, overlap=200
├── pyproject.toml                       # FlagEmbedding 추가
├── src/app/
│   ├── core/
│   │   └── config.py                    # embedding_batch_size 32→4
│   └── services/
│       ├── initial_data_loader.py       # v2 추적 필드 5개 + bulk 에러 체크 + 날짜 포맷
│       ├── document_processing_pipeline.py  # Sparse 활성화 (이전 세션)
│       └── embedding.py                 # Dict[str,float] (이전 세션)
├── src/tests/unit/
│   └── test_embedding_service.py        # mock str 키 (RAG 전문가)
├── docs/04_testing/etl_v2_reprocessing/
│   └── 00_work_plan.md                  # 작업 계획서
└── docs/03_implementation/
    └── etl_batch_pipeline_design.md     # v1.1 Sparse 섹션 (이전 세션)

infrastructure/
└── docker/scripts/
    └── init-db.py                       # strict_date_optional_time + sparse_vector + 타입 정렬

work_logs/
└── session_logs/
    └── 2026-02-13_etl_v2_reprocessing.md  # 이 파일
```

---

## 현재 프로젝트 상태

### 인프라 상태
| 항목 | 값 |
|------|-----|
| 총 컨테이너 | 6개 운영 (ai-service, ES, Neo4j, PG, Redis, MinIO) |
| ES 인덱스 | knowledge_chunks (v2 매핑, 115+ docs, 증가 중) |
| Neo4j | 증가 중 (Entity Extraction) |
| PG documents | 4+ 레코드 (증가 중) |

### ETL v2 상태
| 항목 | 값 |
|------|-----|
| 시작 시간 | 02:48 KST |
| 총 파일 | 1,786개 |
| 처리 속도 | ~6.8 chunks/min |
| 에러 | 0건 |

### Sprint 상태
| 항목 | 값 |
|------|-----|
| Sprint | 08 |
| 현재 작업 | ETL v2 Full Re-Processing (가동 중) |

---

## 다음 작업 (Action Items)

### P0 (Critical)
1. ~~Docker 빌드 완료 대기 → ai-service 재시작~~ 완료
2. ~~FlagEmbedding 설치 확인~~ 완료
3. ~~ETL v2 시작 (nohup)~~ 완료 (02:48 KST)
4. 모니터링 유지 (10분 간격)

### P1 (High)
5. ETL 진행 중 청크 품질 샘플 검증 (주기적)
6. RAGAS 평가 준비 (ETL 완료 후)

### P2 (Medium)
7. Sparse 벡터 검색 쿼리 구현 (향후)
8. RRF 4-Channel 통합

---

## 리스크 모니터링

| 리스크 | 확률 | 영향 | 상태 | 대응 |
|--------|------|------|------|------|
| FlagEmbedding 빌드 실패 | 중 | 높음 | Resolved | datasets 4.5.0 + peft 수동 설치 |
| ES 날짜 포맷 불일치 | 높 | 높음 | Resolved | strict_date_optional_time 전환 |
| CPU 임베딩 OOM | 낮 | 중 | Monitoring | batch_size=4 config 적용 |
| DeepSeek API 장애 | 낮 | 중 | Open | 재시도 로직 내장 |
| ETL 장시간 소요 | 중 | 낮 | Monitoring | 속도 모니터링, 필요시 entity extraction 비활성화 |

---

## 사용된 도구 및 에이전트

| 도구/에이전트 | 용도 |
|--------------|------|
| tl-reviewer (TL) | 코드 리뷰, init-db.py 타입 정렬 |
| etl-reviewer (ETL) | 파이프라인 흐름 검증, v2 필드 추가 |
| rag-reviewer (RAG) | Sparse/임베딩 검증, 테스트 보정 |
| MCP Slack | dev 채널 진행 보고 |

---

## 세션 통계

| 항목 | 값 |
|------|-----|
| 수정된 파일 | 10개 |
| 신규 생성 파일 | 2개 (작업계획서, 세션로그) |
| ES 삭제 | 96,258 청크 |
| Neo4j 삭제 | 108,412 노드 |
| PG 삭제 | 1,449 문서 |
| 이슈 해결 | 3건 (ES 날짜포맷, batch_size, FlagEmbedding 의존성) |

---

*기록자: Claude Code (Opus 4.6)*
*기록 시간: 2026-02-14 03:10 KST*
