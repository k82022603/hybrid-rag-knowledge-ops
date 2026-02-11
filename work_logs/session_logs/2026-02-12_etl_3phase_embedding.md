# Session Log: ETL 3-Phase 파이프라인 + 임베딩 배치

**Date**: 2026-02-12
**Session**: ETL 데이터 처리 + BGE-M3 임베딩 백필
**Status**: 진행중

---

## 작업 요약

새 문서 데이터를 3단계로 나누어 처리하는 전략 수립 및 실행.

### 배경
- 기존 2-worker ETL (임베딩 ON)은 ETA 66시간으로 비현실적
- 전략 변경: **파싱/저장 먼저 → 임베딩 후처리** 분리

---

## Phase 1: 텍스트 파일 ETL (완료)

| 항목 | 값 |
|------|-----|
| 스크립트 | `scripts/run_etl_noembedding.py` |
| 대상 | .md, .txt, .json, .py, .ipynb, .java 등 |
| 워커 | 4개 |
| 결과 | **739 성공 / 0 실패** |
| 소요시간 | 13.6분 (54.4 files/min) |
| 임베딩 | OFF |

## Phase 2: 바이너리 파일 ETL (진행중 ~93%)

| 항목 | 값 |
|------|-----|
| 스크립트 | `scripts/run_etl_phase2.py` |
| 대상 | .pdf, .pptx, .docx, .xlsx |
| 워커 | 2개 |
| 정렬 | 파일 크기순 (작은것→큰것) |
| 현재 | **631 성공 / 216 스킵 / 0 실패** (847/901) |
| 파서 | Docling + RapidOCR |
| 임베딩 | OFF |
| 병목 | 대형 PDF OCR (10~60MB, 파일당 수분~30분) |

## Phase 3: 임베딩 배치 (진행중 ~1.6%)

| 항목 | 값 |
|------|-----|
| 스크립트 | `scripts/run_embedding_backfill.py` |
| 모델 | BAAI/bge-m3 (1024dim, CPU) |
| batch_size | 32 |
| max_text_len | 1000 |
| 전체 | 101,046 chunks |
| 현재 진행 | **1,600 / 101,046** |
| 속도 | 0.4~0.9 texts/s (Phase 2 CPU 경합) |
| 캐시 | Redis (TTL 604800s) |
| ETA | Phase 2 병행: ~47h / 단독: ~31h |

---

## DB 현황 (07:28 기준)

| DB | 항목 | 수량 |
|----|------|------|
| PostgreSQL | Documents | 1,401건 |
| Elasticsearch | Total Chunks | 104,955건 |
| Elasticsearch | With Embedding | 4,028건 |
| Elasticsearch | Without Embedding | ~100,927건 |
| Neo4j | Nodes | 100,829개 |

---

## 리소스 사용량

| 항목 | 값 |
|------|-----|
| CPU | 330~380% (Phase 2 + Phase 3 경합) |
| Memory | 5.5~6.2GiB / 10GiB |
| 활성 컨테이너 | 9개 (ai-service, pg, es, neo4j, redis, nginx, frontend, api-gateway, backend) |

---

## 핵심 기술 결정

1. **3-Phase 분리 전략**: 파싱/저장과 임베딩 분리로 전체 처리 시간 단축
2. **Phase 2 크기순 정렬**: 작은 파일 먼저 → 빠른 성공 축적
3. **ES scroll API**: 메모리 효율적 대량 청크 순회
4. **Phase 2 + 3 병행 실행**: CPU 경합 감수, 총 완료 시간 단축 시도

## 생성된 스크립트

- `knowledge_service/scripts/run_etl_noembedding.py` - Phase 1 (텍스트 전용)
- `knowledge_service/scripts/run_etl_phase2.py` - Phase 2 (바이너리 전용)
- `knowledge_service/scripts/run_embedding_backfill.py` - Phase 3 (임베딩 백필)

## 다음 작업

- [ ] Phase 2 완료 후 임베딩 속도 개선 확인
- [ ] Phase 3 완료 후 전체 임베딩 커버리지 검증
- [ ] 임베딩 후 RAG 검색 품질 테스트
