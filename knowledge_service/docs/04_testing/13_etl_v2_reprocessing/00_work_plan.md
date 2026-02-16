# ETL v2 Re-Processing 작업 계획서

**Version**: 1.0
**작성일**: 2026-02-14
**작성자**: Claude Code + 전문가 팀 (TL/ETL/RAG)
**상태**: 진행 중

---

## 1. 작업 개요

### 1.1 목적

기존 v1 데이터(96,258 청크)를 삭제하고, v2 개선사항을 적용한 전체 재처리를 수행한다.

### 1.2 v2 변경 사항 (설계문서 §14.5 기반)

| 항목 | v1 (기존) | v2 (이번) | 근거 |
|------|-----------|-----------|------|
| chunk_size | 600자 | **1,000자** | 설계문서 §14.5: BM25 TF 개선, RAGChatbotServer 검증 |
| chunk_overlap | 100자 | **200자** | RAGChatbotServer 동일 수치, 문맥 보존 강화 |
| Sparse Vector | 없음 | **BGE-M3 Sparse** | FlagEmbedding `return_sparse=True` |
| Entity Extraction | 없음 | **DeepSeek V3.2** | `enable_entity_extraction=True` |
| QualityGate | 없음 | **적용** | ChunkQualityGate (≤3토큰/쓰레기 필터) |
| v2 추적 필드 | 없음 | **5개 추가** | chunker_version, embedding_model 등 |

### 1.3 예상 결과

```
v1 현황:
  총 청크: 96,258
  평균 토큰: 70.5
  ≤20토큰 비율: ~34.9%
  임베딩 시간: ~38시간

v2 예상:
  총 청크: ~55,000-65,000 (40-50% 감소)
  평균 토큰: 120-150
  ≤20토큰 비율: < 2%
  임베딩 시간: ~20시간
  엔티티 추출: ~2.5시간 (DeepSeek ~$2.7)
```

---

## 2. 작업 단계

### Phase 0: 사전 준비 (완료)

| # | 작업 | 담당 | 상태 |
|---|------|------|------|
| 0.1 | 전문가 코드 리뷰 (TL/ETL/RAG) | 전문가 팀 | :white_check_mark: 완료 |
| 0.2 | `initial_data_loader.py` v2 추적 필드 추가 | ETL 전문가 | :white_check_mark: 완료 |
| 0.3 | `test_embedding_service.py` mock 키 타입 보정 | RAG 전문가 | :white_check_mark: 완료 |
| 0.4 | `run_etl_full.py` chunk_size 600→1000 | 클로드 | :white_check_mark: 완료 |
| 0.5 | `pyproject.toml` FlagEmbedding 추가 | 클로드 | :white_check_mark: 완료 |
| 0.6 | `document_processing_pipeline.py` Sparse 활성화 | 클로드 | :white_check_mark: 완료 (이전 세션) |
| 0.7 | `init-db.py` sparse_vector 매핑 + 타입 정렬 | TL 전문가 | :white_check_mark: 완료 |

### Phase 1: 데이터 초기화 (완료)

| # | 작업 | 상태 |
|---|------|------|
| 1.1 | ES `knowledge_chunks` 인덱스 삭제 | :white_check_mark: 96,258 청크 삭제 |
| 1.2 | Neo4j 전체 노드 삭제 (배치) | :white_check_mark: 108,412 노드 삭제 |
| 1.3 | PG `documents` 테이블 초기화 | :white_check_mark: 1,449 문서 삭제 |
| 1.4 | ES 인덱스 재생성 (v2 매핑) | :white_check_mark: 15필드 (sparse_vector 포함) |

### Phase 2: 컨테이너 리빌드 (완료)

| # | 작업 | 상태 |
|---|------|------|
| 2.1 | FlagEmbedding 의존성 포함 Docker 빌드 | :white_check_mark: 완료 (--no-cache) |
| 2.2 | ai-service 컨테이너 재시작 | :white_check_mark: 완료 |
| 2.3 | FlagEmbedding 설치 확인 | :white_check_mark: (+ datasets 4.5.0, peft) |
| 2.4 | Health check 확인 | :white_check_mark: 완료 |
| 2.5 | ES 날짜 포맷 이슈 해결 | :white_check_mark: strict_date_optional_time |
| 2.6 | batch_size config 32→4 | :white_check_mark: config.py 수정 |

### Phase 3: ETL 실행 (진행 중 - 02:48 KST 시작)

| # | 작업 | 상태 |
|---|------|------|
| 3.1 | `run_etl_full.py` 시작 (nohup) | :white_check_mark: 02:48 KST |
| 3.2 | 문서 파싱 + 청킹 + 임베딩 + 엔티티 동시 | :hourglass: 115+ chunks |
| 3.3 | 모니터링 (Slack + ES count) | :white_check_mark: 설정 완료 |

### Phase 4: 검증

| # | 작업 | 기준 |
|---|------|------|
| 4.1 | ES 청크 수 확인 | 55,000-65,000 범위 |
| 4.2 | Sparse 벡터 존재 확인 | 100% 적재율 |
| 4.3 | v2 추적 필드 확인 | chunker_version="v2" |
| 4.4 | Neo4j 엔티티 노드 확인 | > 0 |
| 4.5 | 토큰 분포 분석 | 평균 120-150, ≤20토큰 < 2% |
| 4.6 | 검색 품질 테스트 (샘플) | kNN + BM25 정상 작동 |

### Phase 5: 평가 (ETL 완료 후)

| # | 작업 | 기준 |
|---|------|------|
| 5.1 | RAGAS 평가 실행 | Context Precision > 0.65 |
| 5.2 | v1 vs v2 비교 리포트 | 청크 수, 토큰 분포, 검색 품질 |
| 5.3 | Sparse 벡터 검색 효과 분석 | 추후 RRF 4-Channel 시 활용 |

---

## 3. 변경 파일 목록

| 파일 | 변경 유형 | 변경자 | 설명 |
|------|----------|--------|------|
| `scripts/run_etl_full.py` | 수정 | 클로드 | chunk_size=1000, overlap=200, entity=True |
| `pyproject.toml` | 수정 | 클로드 | FlagEmbedding 의존성 추가 |
| `src/app/services/document_processing_pipeline.py` | 수정 | 클로드 | Sparse 활성화, v2 필드, QualityGate |
| `src/app/services/embedding.py` | 수정 | 클로드 | Dict[str,float] 타입 힌트 수정 (6곳) |
| `src/app/services/initial_data_loader.py` | 수정 | ETL 전문가 | v2 추적 필드 5개 추가 |
| `infrastructure/docker/scripts/init-db.py` | 수정 | TL 전문가 | sparse_vector 매핑, 타입 정렬 |
| `src/tests/unit/test_embedding_service.py` | 수정 | RAG 전문가 | mock 데이터 키 타입 보정 (7건) |

---

## 4. 리스크

| 리스크 | 확률 | 영향 | 대응 |
|--------|------|------|------|
| FlagEmbedding 설치 실패 | 중 | 높음 | sentence-transformers 폴백 (sparse 없이) |
| CPU 임베딩 20시간 초과 | 중 | 낮음 | 모니터링 + batch_size 조정 |
| DeepSeek API 비용 초과 | 낮 | 낮음 | 예상 $2.7, 상한 $5 |
| Neo4j 메모리 부족 | 낮 | 중 | 배치 커밋 (500건 단위) |
| 중간 장애 (OOM 등) | 중 | 중 | progress 파일 기반 재개 |

---

## 5. 모니터링

### 5.1 임베딩 모니터링 스크립트

```bash
# scripts/embedding_monitor.sh (기존)
# 10분 간격 자동 실행
```

### 5.2 주요 모니터링 지표

| 지표 | 확인 명령 | 정상 범위 |
|------|-----------|-----------|
| ES 청크 수 | `curl ES:9200/knowledge_chunks/_count` | 증가 추세 |
| 처리 속도 | 로그 기반 chunks/sec | > 0.5 c/s |
| 메모리 사용 | `docker stats kp-ai-service` | < 4GB |
| 에러 수 | `grep ERROR /tmp/etl_full_v2.log \| wc -l` | 0 |

---

## 6. 관련 문서

- [ETL Batch Pipeline Design v1.1](../../03_implementation/etl_batch_pipeline_design.md)
- [AI 메타데이터 추출 설계서 §14.5](../../02_design/20_ai_metadata_extraction_design.md)
- [상세 설계서 v2.4](../../02_design/01_hybrid_rag_platform_detailed_design.md)

---

*작성: Claude Code (Opus 4.6) + 전문가 팀*
*최종 수정: 2026-02-14 01:45 KST*
