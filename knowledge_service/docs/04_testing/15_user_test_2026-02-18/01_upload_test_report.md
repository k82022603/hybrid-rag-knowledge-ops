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
| Neo4j | OK | Knowledge+Chunk+CONTAINS | Entity+MENTIONS+RELATED_TO | PASS |

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
  - `neo4j_storage.py`: save_chunk_entities() 메서드 추가 (Chunk→Entity MENTIONS 관계 생성)
  - Entity 노드에 `:Entity` 이중 라벨 적용 (Person/Technology 등 + Entity)
- **검증 결과**:
  - 테스트 문서(844B) 업로드 → entity_count=39, MENTIONS 39개, RELATED_TO 25개
  - PG: entity_count 갱신 확인
  - Neo4j: Entity 노드 + MENTIONS + RELATED_TO + MENTIONED_IN 관계 모두 생성 확인

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
Neo4j 엔티티 (Entity + MENTIONS + RELATED_TO + MENTIONED_IN)
    ↓
PG 메타데이터 갱신 (chunk_count, entity_count, es_synced, neo4j_synced)
    ↓
완료 (status = completed)
```

## 8. 스키마 통일 후 재검증 (2026-02-18 20:50~)

> Neo4j 스키마 통일(RELATED_TO + MENTIONS + Chunk.id) 완료 후, 온라인 업로드 → 검색까지 E2E 재검증.
> **커밋**: ebf822b (코드), d7b4945 (문서)

### 8.1 단일 파일 업로드 (UI 시뮬레이션)

| 항목 | 값 |
|------|-----|
| 파일명 | `schema_test_report.txt` (919B) |
| document_id | `0f612a70-a6c2-46b2-b43d-93c59c7d1f4c` |
| 처리 흐름 | queued → embedding → extracting → **completed** |
| 처리 시간 | 약 66초 |
| Neo4j 엔티티 | 김철수 (Person) 노드 확인 |

### 8.2 배치 파일 업로드 (3파일 동시)

| 파일명 | document_id | 상태 | 처리 시간 |
|--------|-------------|:----:|:---------:|
| `batch_test_infra.txt` | `145a4a31-3318-44...` | completed | ~60초 |
| `batch_test_security.txt` | `2aa1fd00-6672-4c...` | completed | ~63초 |
| `batch_test_api.txt` | `bf39dc89-159e-46...` | completed | ~60초 |

3파일 동시 업로드 시 병렬 처리 정상 동작 확인.

### 8.3 업로드 파일 검색 검증 (Hybrid Search)

| 쿼리 | 총 결과 | 업로드 파일 순위 | 점수 | 판정 |
|------|:-------:|:--------------:|:----:|:----:|
| `RAGAS 평가 결과` | 10 | 상위 5 밖 | - | OK (기존 배치 데이터가 더 관련도 높음) |
| `BGE-Reranker 시맨틱 검색` | 10 | **2위** | 0.8868 | PASS |
| `김철수 이영희 박지성` (고유 콘텐츠) | 10 | **1위** | 0.8331 | PASS |
| `Hybrid RAG 지식검색 시스템` | 10 | **4위** | 0.9986 | PASS |

### 8.4 배치 업로드 파일 검색 검증 (Hybrid Search)

| 쿼리 | 배치 업로드 파일 | 순위 | 점수 | 판정 |
|------|:--------------:|:----:|:----:|:----:|
| `WSL2 Docker 메모리 관리` | batch_test_infra.txt | **1위** | 0.9985 | PASS |
| `Keycloak OIDC 인증 RBAC` | batch_test_security.txt | **1위** | 0.9803 | PASS |
| `REST API 하이브리드 검색 엔드포인트` | batch_test_api.txt | **1위** | 0.9951 | PASS |
| `Neo4j pagecache 그래프 데이터` | batch_test_infra.txt | **2위** | 0.9908 | PASS (기존 데이터와 근소 차이) |

### 8.5 기존 배치 데이터 검색 비교

기존 42,458 chunks (배치 ETL) 데이터에 대한 검색도 정상 동작 확인:

| 쿼리 | 기존 데이터 결과 | 업로드 파일 포함 | 판정 |
|------|:---------------:|:---------------:|:----:|
| `엔티티 추출 GraphRAG` | 10건 (배치) | 0건 | PASS |
| `Docker Compose 인프라 구성` | 10건 (배치) | 0건 | PASS |
| `Elasticsearch Nori 한국어 분석기` | 9건 (배치) | 1건 (업로드) | PASS |

기존 데이터 검색에 스키마 마이그레이션 영향 없음.

### 8.6 검색 타입별 비교

쿼리: `프로젝트 성과 보고서 RAGAS Faithfulness`

| 검색 타입 | Latency | 업로드 파일 검색 | 1위 소스 | 판정 |
|----------|--------:|:---------------:|---------|:----:|
| **Keyword** (BM25) | 199ms | X | 기존 배치 데이터 (score=100.99) | OK (키워드 빈도 기반) |
| **Semantic** (Vector) | 302ms | **O** (3위 내) | 기존 배치 데이터 (score=0.81) | PASS |
| **Hybrid** (RRF) | 20,069ms | **O (1위)** | 업로드 파일 (score=0.9986) | PASS |

### 8.7 재검증 결론

| 항목 | 결과 |
|------|------|
| 온라인 업로드 파이프라인 (단일) | **PASS** — 전 과정 정상 |
| 온라인 업로드 파이프라인 (배치 3건) | **PASS** — 병렬 처리 정상 |
| 업로드 파일 Hybrid 검색 | **PASS** — 4개 쿼리 중 3개 상위 5위 내 |
| 기존 배치 데이터 검색 | **PASS** — 마이그레이션 영향 없음 |
| Neo4j 엔티티 생성 (MENTIONS + RELATED_TO) | **PASS** — 통일 스키마로 정상 생성 |
| 검색 타입별 동작 (Keyword/Semantic/Hybrid) | **PASS** — 3종 모두 정상 |

## 9. 대용량 PDF 업로드 테스트 (2026-02-18 21:05~)

> 사용자가 직접 UI에서 Nike SEC 공시 PDF 3건 업로드. 대용량 PDF 파이프라인 한계 확인.

### 9.1 테스트 파일

| 파일명 | 크기 | 유형 |
|--------|:----:|------|
| `414759-1-_5_Nike-NPS-Combo_Form-10-K_WR.pdf` | 3.3MB | Nike 10-K SEC 공시 |
| `nke4278571-ars.pdf` | 4.3MB | Nike Annual Report |
| `Nike-Inc-2025_10K.pdf` | 1.3MB | Nike 10-K |

### 9.2 테스트 결과

| 파일 | 업로드 | 파싱 | 최종 상태 | 실패 원인 |
|------|:------:|:----:|:---------:|----------|
| `414759-...10-K_WR.pdf` (3.3MB) | PASS | **FAIL** | Processing 50% 멈춤 | Docling `Parsing timed out after 300s` x2 |
| `nke4278571-ars.pdf` (4.3MB) | **FAIL** | - | timeout | 프론트엔드 `timeout of 120000ms exceeded` |
| `Nike-Inc-2025_10K.pdf` (1.3MB) | **FAIL** | - | timeout | 프론트엔드 `timeout of 120000ms exceeded` |

**통과율**: 0/3 (0%) — 대용량 PDF 전부 실패

### 9.3 실패 원인 분석

**1) 프론트엔드 업로드 타임아웃 (120초)**
- `nke4278571-ars.pdf`, `Nike-Inc-2025_10K.pdf`: 프론트엔드 axios 120초 타임아웃 초과
- 첫 번째 파일이 Docling OCR 처리 중이라 서버 응답 지연 → 후속 파일 업로드 큐잉

**2) Docling PDF 파싱 타임아웃 (300초)**
- `414759-...10-K_WR.pdf` (3.3MB): 업로드 성공 → Docling 파싱 단계에서 300초 타임아웃
- RapidOCR(ch_PP-OCRv4) 엔진까지 동원 — SEC 공시서류의 표/차트/이미지 때문
- 300초 타임아웃 2회 발생 (자동 재시도 포함)

### 9.4 파이프라인 전체 타임아웃 체인 분석

> **"Docling 300초를 통과해도 다음에 어디서 막히나?"**

Nike 10-K (3.3MB, ~150페이지)가 전 단계를 통과한다고 가정할 때, 예상 청크 수 **200~400개** 기준:

```
단계별 타임아웃/병목 체인 (대용량 PDF 시나리오)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

① Frontend axios           120s   ← 2/3 파일 여기서 실패
        ↓
② Nginx proxy_send         300s   ← 대용량 파일 전송
        ↓
③ Nginx proxy_read         300s   ← 백엔드 응답 대기
        ↓
④ Docling PDF 파싱         300s   ← 1/3 파일 여기서 실패 ★
   (RapidOCR CPU 집약)            (150페이지 표/이미지 OCR)
        ↓
⑤ 청킹 (Quality Gate)     ~5s    ← 빠름 (CPU only)
        ↓
⑥ BGE-M3 임베딩 (CPU)    ~300s   ← ★★ 두 번째 병목
   batch_size=4                    400 chunks ÷ 4 = 100 batches
   ~3초/batch (CPU)                100 × 3s = 300초 (5분)
        ↓
⑦ ES 벌크 인덱싱          ~10s   ← 빠름
        ↓
⑧ Neo4j 기본 그래프       ~5s    ← 빠름
        ↓
⑨ DeepSeek 엔티티 추출    ~120s  ← ★★★ 세 번째 병목
   (전체 문서 텍스트)              llm_timeout=60s × 2 (추출+관계)
   + Gleaning 1회                  + Gleaning 60s
   = 최대 180s                     텍스트가 LLM max_tokens 초과 시 추가 지연
        ↓
⑩ Neo4j 엔티티 저장       ~10s   ← 빠름
        ↓
완료까지 총 예상: ~15분+ (파싱 제외)
```

### 9.5 단계별 상세 분석

| # | 단계 | 타임아웃/제한 | 설정 위치 | 대용량 PDF 예상 시간 | 위험도 |
|---|------|:----------:|----------|:------------------:|:------:|
| ① | Frontend axios | **120s** | `frontend/src/` (하드코딩) | 파일 크기에 비례 | HIGH |
| ② | Nginx proxy_send | 300s | `nginx/conf.d/*.conf` | ~5s (업로드 자체) | LOW |
| ③ | Nginx proxy_read | 300s | `nginx/conf.d/*.conf` | 백엔드 처리 전체 | **HIGH** |
| ④ | Docling PDF 파싱 | **300s** | `config.py:docling_parse_timeout` | 150페이지: **300s+** | **CRITICAL** |
| ⑤ | 청킹 | 없음 | - | ~5s | LOW |
| ⑥ | BGE-M3 임베딩 (CPU) | **없음** | `embedding_batch_size=4` | 400 chunks: **~300s** | **HIGH** |
| ⑦ | ES 벌크 인덱싱 | 없음 | - | ~10s | LOW |
| ⑧ | Neo4j 기본 그래프 | 없음 | - | ~5s | LOW |
| ⑨ | DeepSeek 엔티티 추출 | **60s/call** | `config.py:llm_timeout=60` | 3 calls: **~180s** | **HIGH** |
| ⑩ | Neo4j 엔티티 저장 | 없음 | - | ~10s | LOW |

**총 예상 처리 시간**: ④ 300s + ⑥ 300s + ⑨ 180s + 기타 35s = **~815초 (13.6분)**

### 9.6 병목 요약 (TOP 4)

| 순위 | 병목 | 현재 제한 | 대용량 PDF 예상 | 증상 |
|:----:|------|:---------:|:-------------:|------|
| **1** | Docling PDF 파싱 (OCR) | 300s | 300s+ (150p) | `Parsing timed out after 300s` |
| **2** | BGE-M3 임베딩 (CPU) | 없음 | ~300s (400 chunks) | 프론트엔드 "Processing" 장시간 |
| **3** | DeepSeek LLM 엔티티 추출 | 60s/call | ~180s (3 calls) | "Extracting" 장시간 |
| **4** | Frontend axios 타임아웃 | 120s | 즉시 실패 | `timeout of 120000ms exceeded` |

### 9.7 권장 조치

| 우선순위 | 조치 | 상세 |
|:--------:|------|------|
| P0 | Frontend 업로드 비동기화 | 업로드만 빠르게 완료 + 처리는 백그라운드 (SSE로 진행률 수신) |
| P1 | Docling 타임아웃 증가 | `docling_parse_timeout`: 300s → 600s (대용량 PDF용) |
| P1 | 대용량 PDF 페이지 분할 | 50페이지 단위 분할 파싱 → 병렬 처리 |
| P2 | 임베딩 GPU 가속 | CPU → GPU (CUDA) 전환 시 10x 이상 속도 향상 |
| P2 | 엔티티 추출 청크 단위 | 전체 문서 대신 청크별 추출 → 병렬 API 호출 |

---

## 10. 타임아웃 증가 적용 (21:15~21:30)

### 10.1 적용 배경

Section 9 대용량 PDF 테스트에서 파이프라인 전체 타임아웃 체인이 120~300초로 설정되어 있어 SEC 10-K 등 복잡한 PDF 처리 불가 확인. 사용자 지시에 따라 전체 체인을 1200초(20분)로 통일.

### 10.2 변경 내역

| # | 파일 | 설정 | 변경 전 | 변경 후 | 설명 |
|---|------|------|:-------:|:-------:|------|
| 1 | `frontend/src/services/api.ts` | `timeout` | 120,000ms (2분) | 1,200,000ms (20분) | Axios 요청 타임아웃 |
| 2 | `src/app/core/config.py` | `docling_parse_timeout` | 300.0s (5분) | 1,200.0s (20분) | Docling PDF 파싱 |
| 3 | `nginx/conf.d/default.conf` | `proxy_send_timeout` | 300s | 1,200s | Nginx → API Gateway (/api/v1/) |
| 4 | `nginx/conf.d/default.conf` | `proxy_read_timeout` | 300s | 1,200s | API Gateway 응답 대기 (/api/v1/) |
| 5 | `nginx/conf.d/default.conf` | upload `proxy_send_timeout` | (없음) | 1,200s | 업로드 전용 (/api/v1/documents/upload) |
| 6 | `nginx/conf.d/default.conf` | upload `proxy_read_timeout` | 600s | 1,200s | 업로드 전용 (/api/v1/documents/upload) |

### 10.3 컨테이너 재배포

| 서비스 | 빌드 | 재시작 | 상태 |
|--------|:----:|:------:|:----:|
| kp-frontend | `--no-cache` 재빌드 | Recreated | healthy |
| kp-nginx | `--no-cache` 재빌드 | Recreated | healthy |
| kp-ai-service | `--no-cache` 재빌드 | Recreated | healthy |

### 10.4 미적용 항목 (후속 검토 필요)

| 항목 | 현재 값 | 설명 |
|------|:-------:|------|
| Spring Cloud Gateway `response-timeout` | 120s | `application.yml` — 별도 게이트웨이 빌드 필요 |
| Resilience4j `ai-service-circuit-breaker` | 120s | TimeLimiter 타임아웃 |
| BGE-M3 임베딩 (CPU) | 무제한 | 하드웨어 한계, 타임아웃 아닌 성능 문제 |

---

## 11. 대시보드 빠른 검색 버그 수정 (21:30~21:50)

### 11.1 증상

대시보드 "빠른 검색"에서 검색어 입력 후 엔터 → `/search?q=...` URL로 이동하나 **검색이 실행되지 않음**. 검색 페이지의 입력창이 비어있고 Chat Search가 자동 실행되지 않음.

### 11.2 원인

`SearchPage.tsx`가 URL의 `?q=` 파라미터를 읽지 않고, `ChatSearch` 컴포넌트에 전달하지 않음.

### 11.3 수정 내역

| # | 파일 | 수정 내용 |
|---|------|----------|
| 1 | `pages/SearchPage.tsx` | `useSearchParams()`로 `?q=` 읽어서 `ChatSearch`에 `initialQuery` prop 전달 |
| 2 | `features/search/ChatSearch.tsx` | `initialQuery` prop 수신 → `useChatSearch(initialQuery)` 전달 |
| 3 | `features/search/hooks/useChatSearch.ts` | `initialQuery` 파라미터 추가, `useEffect`로 마운트 시 자동 `sendMessage(initialQuery)` 실행 |

### 11.4 데이터 흐름 (수정 후)

```
Dashboard "빠른 검색" → navigate("/search?q=검색어")
  → SearchPage: useSearchParams().get('q') → initialQuery
    → ChatSearch(initialQuery="검색어")
      → useChatSearch("검색어")
        → useEffect: sendMessage("검색어") → Chat Search 자동 실행
```

### 11.5 배포

kp-frontend `--no-cache` 재빌드 + Recreated (Section 10.3과 동시 배포)

---

*테스트: 사용자 (직접 UI 테스트) | 분석/수정: Claude Code (Opus 4.6) | 2026-02-18*
