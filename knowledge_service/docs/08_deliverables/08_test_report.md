# 테스트 결과 보고서

**시스템**: Hybrid RAG Knowledge Platform
**버전**: 1.0
**작성일**: 2026-02-19

---

## 목차

1. [테스트 개요](#1-테스트-개요)
2. [단위 테스트](#2-단위-테스트)
3. [RAGAS 검색 품질 평가](#3-ragas-검색-품질-평가)
4. [사전점검 테스트 (2026-02-18)](#4-사전점검-테스트-2026-02-18)
5. [Sprint 12 사용자 테스트 (2026-02-18)](#5-sprint-12-사용자-테스트-2026-02-18)
6. [성능 테스트](#6-성능-테스트)
7. [종합 평가](#7-종합-평가)

---

## 1. 테스트 개요

### 1.1 목표

Hybrid RAG Knowledge Platform의 품질을 다각도로 검증합니다.

- **단위 테스트**: 핵심 모듈의 코드 품질 및 커버리지
- **RAGAS 평가**: 검색 파이프라인의 정량적 품질 측정
- **사전점검**: 전체 인프라 및 서비스 통합 검증
- **사용자 테스트**: UI 기반 E2E 업로드/검색/대용량 PDF 테스트
- **성능 테스트**: 검색 응답 시간 측정

### 1.2 범위

| 테스트 유형 | 대상 | 도구 | 기간 |
|------------|------|------|------|
| 단위 테스트 | 5개 핵심 Python 모듈 | pytest + Docker 환경 | Sprint 8~12 |
| RAGAS 평가 | 검색 파이프라인 (v8~v11) | RAGAS 0.2.15 + DeepSeek V3.2 | Sprint 10~12 |
| 사전점검 | 18개 컨테이너 + 소스코드 + API | Agent Teams (Infra + DevOps + QA) | 2026-02-18 |
| 사용자 테스트 | 업로드 E2E 13 케이스 + 대용량 PDF 3건 | UI 직접 테스트 + curl | 2026-02-18 |
| 성능 테스트 | Keyword / Hybrid / Semantic 검색 | curl + 응답시간 측정 | 2026-02-18 |

### 1.3 테스트 환경

| 항목 | 사양 |
|------|------|
| 런타임 LLM | DeepSeek V3.2 |
| 임베딩 모델 | BGE-M3 (Dense 1024차원 + Sparse) |
| Reranker | BGE-Reranker-Base (ONNX) |
| 컨테이너 | Docker Compose 18개 |
| 호스트 | WSL2 (Windows 11) |
| RAGAS 라이브러리 | 0.2.15 |

---

## 2. 단위 테스트

### 2.1 테스트 결과 요약

| 모듈 | 파일 | 커버리지 | 테스트 수 | 결과 |
|------|------|:--------:|:---------:|:----:|
| Search Service | `services/search.py` | 97% | 42 | PASS |
| Embedding Service | `services/embedding_service.py` | 96% | 35 | PASS |
| ES Storage | `services/es_storage.py` | 98% | 38 | PASS |
| Conversation History | `services/conversation_history.py` | 100% | 28 | PASS |
| Auth Service | `services/auth_service.py` | 95% | 31 | PASS |
| **합계** | **5 모듈** | **97% (평균)** | **174** | **ALL PASS** |

### 2.2 테스트 방침

- **Mock 모드 금지**: 반드시 `TEST_MODE=docker` 환경에서 실행
- **실제 Docker 컨테이너** (ES, Neo4j, PG, Redis)에 연결하여 통합 검증
- **목표 커버리지**: 80% 이상 (실제 달성: 97%)

### 2.3 테스트 실행 방법

```bash
cd knowledge_service
source .venv/bin/activate
export TEST_MODE=docker

# 전체 단위 테스트
pytest src/tests/unit/ -v --cov=src/app --cov-report=term-missing

# 특정 모듈
pytest src/tests/unit/test_search.py -v
```

### 2.4 CI/CD 연동

8개 GitHub Actions 워크플로우에서 PR 시 자동 실행됩니다.

---

## 3. RAGAS 검색 품질 평가

### 3.1 RAGAS 프레임워크 소개

**RAGAS (Retrieval Augmented Generation Assessment)** 는 RAG 시스템의 품질을 자동으로 평가하는 오픈소스 프레임워크입니다.

**4가지 핵심 메트릭**:

| 메트릭 | 측정 대상 | 의미 |
|--------|----------|------|
| **Faithfulness** | 답변 충실도 | 답변의 각 문장이 제공된 컨텍스트에 근거하는지 (1.0 = 환각 없음) |
| **Answer Relevancy** | 답변 관련성 | 답변이 질문에 얼마나 직접적으로 관련되는지 |
| **Context Precision** | 검색 정밀도 | 검색된 컨텍스트 중 실제 유용한 비율 (순서 가중) |
| **Context Recall** | 검색 재현율 | ground truth 답변을 컨텍스트가 커버하는 비율 |

### 3.2 평가 조건

| 항목 | 내용 |
|------|------|
| 쿼리 수 | 51개 |
| 도메인 수 | 7개 |
| LLM (답변 생성) | DeepSeek V3.2 |
| LLM (RAGAS 평가) | DeepSeek V3.2 |
| 임베딩 (유사도) | BGE-M3 |
| RAGAS 버전 | 0.2.15 |

**7개 도메인 구성**:

| 도메인 | 쿼리 수 | 설명 |
|--------|:------:|------|
| entity_relation | 7 | 기술 엔티티 간 관계 비교 |
| multi_hop | 7 | 다단계 추론 필요 |
| keyword | 7 | 키워드 기반 직접 검색 |
| semantic | 7 | 의미 기반 검색 |
| graph_entity | 8 | Graph/엔티티 트리거 |
| legal | 7 | 법률/규정 도메인 |
| factual | 8 | AI/LLM 심화 + 프로젝트 특화 |

### 3.3 버전별 결과 (v8 ~ v11)

| 메트릭 | v8 (108K) | v9 (56K) | v10 (42K) | v11 (+Reranker) | v8 -> v11 변화 |
|--------|:---------:|:--------:|:---------:|:--------------:|:-------------:|
| **Faithfulness** | 0.919 | 0.913 | 0.919 | **0.935** | +0.016 |
| **Answer Relevancy** | 0.647 | 0.547 | 0.647 | **0.621** | -0.026 |
| **Context Precision** | 0.489 | 0.577 | 0.489 | **0.618** | +0.129 |
| **Context Recall** | 0.474 | 0.600 | 0.474 | **0.672** | +0.198 |
| **산술평균** | 0.632 | 0.659 | 0.632 | **0.711** | **+0.079 (+12.5%)** |

**버전별 시스템 변경사항**:

| 버전 | 청크 수 | 주요 변경 | 등급 |
|------|:------:|----------|:----:|
| **v8** | 108,896 | Dense + BM25(Nori) 2-Way RRF | B |
| **v9** | 56,063 | 4-Way RRF (Dense+Sparse+BM25+Graph), chunk_size 600->1000 | B+ |
| **v10** | 42,462 | Entity Extraction 23,074건 완료, 쓰레기 청크 13,601건 삭제 | B+ |
| **v11** | 42,462 | BGE-Reranker(Post-RRF) 적용 | **A-** |

**Quality Gate 분포**:

| 등급 | v8 | v9 | v10 | v11 | v8 -> v11 |
|:----:|:--:|:--:|:---:|:---:|:---------:|
| **HIGH** (avg >= 0.70) | 24 | 28 | 30 | **33** | **+9** |
| **PARTIAL** (0.40-0.69) | 16 | 12 | 11 | **12** | -4 |
| **NONE** (< 0.40) | 11 | 11 | 10 | **6** | **-5** |

### 3.4 v11 최종 결과 (A- 등급)

```
  RAGAS v11 성적표 (4-Way RRF + Reranker)
  ================================================

  Faithfulness      ====================   0.935  (환각 6.5% - 역대 최고)
  Context Precision ============            0.618  (+26.4% vs v10)
  Context Recall    =============           0.672  (+41.8% vs v10)
  Answer Relevancy  ============            0.621  (소폭 하락, 트레이드오프)

  산술평균: 0.711 (A- 등급)
  Quality Gate: HIGH 33건(65%), PARTIAL 12건(24%), NONE 6건(12%)
```

**핵심 발견**:

1. **Reranker가 Context Precision/Recall을 대폭 개선**
   - Context Precision: 0.489 -> 0.618 (+26.4%)
   - Context Recall: 0.474 -> 0.672 (+41.8%)
   - Cross-encoder가 RRF 퓨전 후 결과를 정밀하게 재순위

2. **Faithfulness 0.935 -- 역대 최고, 환각 6.5% 이하**
   - 관련성 높은 컨텍스트가 상위에 배치되어 LLM이 근거 없는 추측을 하는 빈도 감소
   - 실무 배포 기준 "환각 10% 이하" 충분히 충족

3. **NONE 등급 역대 최저 (6건, 12%)**
   - v8 11건 -> v9 11건 -> v10 10건 -> v11 6건
   - 검색 실패 쿼리가 지속 감소

4. **데이터 질 > 양**
   - v8: 108K 청크, 산술평균 0.632
   - v11: 42K 청크(-61%), 산술평균 0.711(+12.5%)
   - 쓰레기 청크 제거 + 엔티티 구조화 + Reranker가 품질 향상의 핵심

### 3.5 도메인별 분석

| 도메인 | Faithfulness | Answer Rel. | Context Prec. | Context Rec. | 평균 | 등급 |
|--------|:----------:|:----------:|:------------:|:-----------:|:----:|:----:|
| **entity_relation** | 1.000 | 0.877 | 0.960 | 0.786 | **0.906** | A+ |
| **multi_hop** | 0.949 | 0.820 | 0.553 | 0.821 | **0.786** | A- |
| **factual** | 0.886 | 0.708 | 0.631 | 0.562 | **0.697** | B |
| **graph_entity** | 0.924 | 0.622 | 0.539 | 0.688 | **0.693** | B |
| **keyword** | 0.937 | 0.442 | 0.595 | 0.714 | **0.672** | B- |
| **semantic** | 0.992 | 0.377 | 0.612 | 0.571 | **0.638** | C+ |
| **legal** | 0.863 | 0.484 | 0.448 | 0.571 | **0.592** | C |

**도메인별 해석**:

- **entity_relation (0.906)**: Faithfulness **1.000** 달성. 7건 전부 HIGH. Entity Extraction + Reranker가 엔티티 관계 질의에서 완벽에 가까운 성능
- **multi_hop (0.786)**: 7건 중 6건 HIGH (86%). 여러 문서에 걸친 추론 경로를 제공
- **factual / graph_entity (0.69x)**: 안정적인 B등급. 사실 확인 및 그래프 엔티티 질의에서 양호
- **keyword (0.672)**: Nori 형태소 분석기 + BM25가 한국어 키워드 검색을 지원하나, Answer Relevancy가 낮음
- **semantic (0.638)**: v10 D등급에서 v11 C+ 등급으로 상승 (+0.152). Reranker 효과가 가장 큰 도메인
- **legal (0.592)**: 법률/규정 특화 문서가 부족하여 하위 등급 유지

### 3.6 비용 효율

전체 파이프라인(Entity Extraction + RAGAS 평가 + 운영)을 DeepSeek V3.2로 약 $52(~75,000원)에 완료했습니다.

| 비교 대상 | 예상 비용 | DeepSeek 대비 |
|----------|:---------:|:------------:|
| **DeepSeek V3.2** (실측) | **$52** | 1x |
| GPT-4o | $775 | 15x |
| Claude Sonnet 4.6 | $1,063 | 20x |
| Claude Opus 4.6 | $5,314 | 102x |

---

## 4. 사전점검 테스트 (2026-02-18)

### 4.1 점검 개요

UI 사용자 테스트 전 전체 인프라/서비스를 Agent Teams(Infra + DevOps + QA)가 병렬 점검했습니다.

**최종 판정**: UI 사용자 테스트 **진행 가능** (2026-02-18 14:54 KST 확인)

### 4.2 Infra 점검 결과: PASS

| 항목 | 결과 | 상세 |
|------|:----:|------|
| 컨테이너 상태 | **18/18 기동** | 전부 healthy (promtail: healthcheck 없음) |
| 소스코드 동기화 | **27/27 일치** | services(17) + api/routes(8) + core(5) + rag(2) MD5 검증 |
| E2E 엔드포인트 | **6/6 정상** | nginx, health, auth, gateway, backend 전부 HTTP 200 |

### 4.3 DevOps 점검 결과: PASS (기존 이슈 4건)

| 항목 | 결과 | 상세 |
|------|:----:|------|
| Observability 6종 | **정상** | Prometheus, Grafana, Kibana, Jaeger, Loki, Promtail |
| Grafana 대시보드 | **4개 정상** | Application, Database, RAG&SLA, System Overview |
| Prometheus 메트릭 | **966개 수집** | Backend, Gateway, Grafana, Loki, Jaeger 타겟 UP |

**기존 이슈 (비차단)**:
1. ai-service `/metrics` 미구현 (Prometheus 수집 불가)
2. ES Prometheus exporter 미설치
3. Jaeger 서비스 계측 미적용
4. Promtail WSL2 Docker 로그 경로 이슈

### 4.4 QA 점검 결과: CRITICAL 3건 -> 전부 FIXED

| # | 이슈 | 심각도 | 상태 |
|---|------|:------:|:----:|
| 1 | HF 캐시 마운트 실패 (BGE-M3/Reranker 로드 불가) | HIGH | **FIXED** |
| 2 | 기동 순서 문제 (ai-service가 ES/Neo4j 전에 시작) | HIGH | **FIXED** |
| 3 | Nori 필드 매핑 미적용 (text 필드 standard analyzer) | MEDIUM | **FIXED** |

**해결 내역**:
- Issue 1+2: ES/Neo4j/PG healthy 확인 후 ai-service 재시작 + Redis 캐시 FLUSHALL
- Issue 3: Reindex 완료 -- `knowledge_chunks_v2`(korean_analyzer) 생성, 42,462건 복사(실패 0건, 164초), alias 스왑

### 4.5 수정 후 검증 결과

| 검증 항목 | 결과 | 상세 |
|-----------|:----:|------|
| Health endpoint | **PASS** | ES/Neo4j/PG/DeepSeek 전부 healthy |
| JWT 로그인 | **PASS** | accessToken 발급 성공 (268자) |
| Hybrid Search | **PASS** | 5건 반환, score=0.9964 |
| Semantic Search | **PASS** | 5건 반환, score=0.8324 (BGE-M3 로드 확인) |
| Keyword Search | **PASS** | 5건 반환, score=60.27 |
| Redis 캐시 | **PASS** | FLUSHALL 후 fresh 결과 반환 |
| korean_analyzer | **PASS** | `"프로젝트관리시스템구축"` -> 4토큰 (프로젝트, 관리, 시스템, 구축) |

---

## 5. Sprint 12 사용자 테스트 (2026-02-18)

### 5.1 테스트 개요

Sprint 12 완료 후 UI 기반 사용자 테스트를 수행했습니다. 업로드 E2E 테스트, 발견 이슈 수정, Neo4j 스키마 통일, 대용량 PDF 테스트, 대시보드 빠른 검색 버그 수정까지 전 과정을 포함합니다.

**테스트 타임라인**:

| 시간 | 내용 | 결과 |
|------|------|:----:|
| 14:00~15:00 | 사전점검 (인프라 18개 컨테이너) | PASS |
| 15:40~16:30 | 업로드 E2E 테스트 (13 케이스) | 9 PASS, 3 WARN, 1 FAIL |
| 16:30~18:00 | 발견 이슈 6건 수정 (인증, Neo4j, PG, 엔티티) | 6/6 해결 |
| 19:30~20:30 | Neo4j 스키마 통일 코드 수정 + DB 마이그레이션 | 완료 (298K 관계) |
| 20:50~21:15 | 스키마 통일 후 재검증 (4파일 업로드 + 14건 검색) | 전체 PASS |
| 21:05~21:15 | 대용량 PDF 업로드 테스트 (Nike 10-K 3건) | 0/3 FAIL |
| 21:15~21:30 | 타임아웃 증가 적용 (1200s 통일) | 적용 완료 |
| 21:30~21:50 | 대시보드 빠른 검색 버그 수정 | 수정 완료 |

### 5.2 업로드 E2E 테스트 (13 케이스)

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
| 9 | **인증 없이 업로드** | **201** | completed | **FAIL** | 보안 이슈 (수정 완료) |
| 10 | 파일 없이 업로드 | 422 | - | PASS | 검증 정상 |
| 11 | 메타데이터 포함 업로드 | 201 | completed | PASS | metadata 저장 |
| 12 | 문서 다운로드 | 200 | - | PASS | 원본 반환 |
| 13 | Nginx 경유 상태 조회 | 200 | - | PASS | 정상 |

**통과율**: PASS 9/13 (69%), WARN 3/13, FAIL 1/13

### 5.3 발견 이슈 6건 및 조치 결과

| # | 이슈 | 심각도 | 상태 |
|---|------|:------:|:----:|
| 1 | 인증 미적용 (13개 엔드포인트 JWT 없이 접근 가능) | HIGH | **FIXED** |
| 2 | Neo4j 미동기화 (업로드 후 Document/Chunk 노드 미생성) | HIGH | **FIXED** |
| 3 | PG chunk_count 미갱신 (ES에 청크 존재하나 PG에 0) | MEDIUM | **FIXED** |
| 4 | PG es_synced 미갱신 (ES 저장 완료됐으나 false) | MEDIUM | **FIXED** |
| 5 | 소형 파일 안내 부족 (4B 파일 업로드 시 불명확한 에러) | LOW | **FIXED** |
| 6 | 엔티티 추출 온라인 미수행 (배치 ETL Phase 3에만 의존) | HIGH | **FIXED** |

**수정 파일**: `documents.py`, `extract.py`, `embed.py`, `document_repository.py`, `document_processing_pipeline.py`, `neo4j_storage.py` (6개 파일)

### 5.4 Neo4j 스키마 통일 마이그레이션

검색 엔진(search.py)과 온라인 업로드 파이프라인(neo4j_storage.py)의 스키마 불일치를 통일했습니다.

**마이그레이션 결과**:

| 관계 타입 | Before | After | 상태 |
|-----------|-------:|------:|:----:|
| RELATED | 298,579 | 0 | 전량 RELATED_TO로 마이그레이션 |
| RELATED_TO | 57 | 298,636 | 통합 완료 |
| MENTIONS | 404,398 | 404,411 | 통합 완료 (+13 HAS_ENTITY 병합) |
| HAS_ENTITY | 13 | 0 | 전량 MENTIONS로 마이그레이션 |
| Chunk id 누락 | 11 | 0 | 전량 보정 |

**통일된 최종 스키마**:

```
(Knowledge)-[:CONTAINS]->(Chunk {id})          -- 문서->청크
(Chunk)-[:MENTIONS]->(Entity)                  -- 청크->엔티티 (404K)
(Entity)-[:MENTIONED_IN]->(Knowledge)          -- 엔티티->문서
(Entity)-[:RELATED_TO]->(Entity)               -- 엔티티<->엔티티 (298K)
```

마이그레이션 25.7초 완료, 서비스 중단 없음. 코드 5개 파일 수정 (커밋 ebf822b).

### 5.5 스키마 통일 후 재검증

| 검증 카테고리 | 쿼리 수 | 결과 |
|-------------|:-------:|:----:|
| 단일 업로드 파일 검색 | 4 | PASS (3/4 상위 5위 내) |
| 배치 업로드 파일 검색 | 4 | PASS (4/4 상위 2위 내) |
| 기존 배치 데이터 검색 | 3 | PASS (마이그레이션 영향 없음) |
| 검색 타입별 비교 (Keyword/Semantic/Hybrid) | 3 | PASS |
| **합계** | **14** | **전체 PASS** |

### 5.6 대용량 PDF 업로드 테스트

사용자가 직접 UI에서 Nike SEC 공시 PDF 3건을 업로드하여 대용량 PDF 파이프라인 한계를 확인했습니다.

**테스트 파일**:

| 파일명 | 크기 | 유형 |
|--------|:----:|------|
| `414759-1-_5_Nike-NPS-Combo_Form-10-K_WR.pdf` | 3.3MB | Nike 10-K SEC 공시 |
| `nke4278571-ars.pdf` | 4.3MB | Nike Annual Report |
| `Nike-Inc-2025_10K.pdf` | 1.3MB | Nike 10-K |

**테스트 결과**:

| 파일 | 업로드 | 파싱 | 최종 상태 | 실패 원인 |
|------|:------:|:----:|:---------:|----------|
| `414759-...10-K_WR.pdf` (3.3MB) | PASS | FAIL | Processing 50% 멈춤 | Docling `Parsing timed out after 300s` x2 |
| `nke4278571-ars.pdf` (4.3MB) | FAIL | - | timeout | Frontend `timeout of 120000ms exceeded` |
| `Nike-Inc-2025_10K.pdf` (1.3MB) | FAIL | - | timeout | Frontend `timeout of 120000ms exceeded` |

**통과율**: 0/3 (0%) -- 대용량 PDF 전부 실패

**병목 분석 (TOP 4)**:

| 순위 | 병목 | 현재 제한 | 증상 |
|:----:|------|:---------:|------|
| 1 | Docling PDF 파싱 (OCR) | 300s | `Parsing timed out after 300s` |
| 2 | BGE-M3 임베딩 (CPU) | 없음 | 장시간 Processing |
| 3 | DeepSeek LLM 엔티티 추출 | 60s/call | 장시간 Extracting |
| 4 | Frontend axios 타임아웃 | 120s | `timeout of 120000ms exceeded` |

**조치**: 전체 타임아웃 체인을 1200초(20분)로 통일 적용 (Section 5.7 참조)

### 5.7 타임아웃 증가 적용

| # | 파일 | 설정 | 변경 전 | 변경 후 |
|---|------|------|:-------:|:-------:|
| 1 | `frontend/src/services/api.ts` | axios timeout | 120,000ms | 1,200,000ms |
| 2 | `src/app/core/config.py` | docling_parse_timeout | 300s | 1,200s |
| 3 | `nginx/conf.d/default.conf` | proxy_send_timeout (/api/v1/) | 300s | 1,200s |
| 4 | `nginx/conf.d/default.conf` | proxy_read_timeout (/api/v1/) | 300s | 1,200s |
| 5 | `nginx/conf.d/default.conf` | upload proxy_send_timeout | (없음) | 1,200s |
| 6 | `nginx/conf.d/default.conf` | upload proxy_read_timeout | 600s | 1,200s |

kp-frontend, kp-nginx, kp-ai-service 3개 컨테이너 `--no-cache` 재빌드 + 재배포 완료.

**미적용 항목** (후속 검토 필요):
- Spring Cloud Gateway `response-timeout`: 120s (별도 게이트웨이 빌드 필요)
- Resilience4j `ai-service-circuit-breaker`: 120s (TimeLimiter)

### 5.8 대시보드 빠른 검색 버그 수정

**증상**: 대시보드 "빠른 검색"에서 검색어 입력 후 엔터 -> `/search?q=...` URL로 이동하나 검색이 실행되지 않음.

**원인**: `SearchPage.tsx`가 URL의 `?q=` 파라미터를 읽지 않음.

**수정 (3개 파일)**:

| # | 파일 | 수정 내용 |
|---|------|----------|
| 1 | `pages/SearchPage.tsx` | `useSearchParams()`로 `?q=` 읽어서 `ChatSearch`에 `initialQuery` prop 전달 |
| 2 | `features/search/ChatSearch.tsx` | `initialQuery` prop 수신 -> `useChatSearch(initialQuery)` 전달 |
| 3 | `features/search/hooks/useChatSearch.ts` | `initialQuery` 파라미터 추가, `useEffect`로 마운트 시 자동 `sendMessage(initialQuery)` 실행 |

kp-frontend 재배포 완료 (Section 5.7과 동시 배포).

---

## 6. 성능 테스트

### 6.1 검색 응답 시간

사전점검 시 측정된 검색 API 응답 시간입니다 (쿼리: "프로젝트 관리", top_k=5).

| 검색 유형 | 엔드포인트 | 응답 시간 | 결과 수 | 비고 |
|----------|-----------|:---------:|:------:|------|
| **Keyword Search** | `/api/v1/search/keyword` | 19ms | 5건 | BM25(Nori) 단독 |
| **Hybrid Search** | `/api/v1/search/hybrid` | 18,127ms | 5건 | 4-Way RRF + Reranker + Entity Enrichment |
| **Semantic Search** | `/api/v1/search/semantic` | 4,206ms | 5건 | Dense Vector + BGE-M3 임베딩 |

> Hybrid Search의 높은 응답 시간(18초)은 4-Way 병렬 검색 + RRF 퓨전 + BGE-Reranker + Entity Enrichment + DeepSeek RAG 생성의 전체 파이프라인을 포함합니다. CPU 환경에서의 ONNX Reranker 추론이 주요 병목입니다.

### 6.2 검색 품질 스코어

| 검색 유형 | Top-1 Score | 의미 |
|----------|:----------:|------|
| Keyword | 60.27 | BM25 TF-IDF 점수 |
| Hybrid | 0.9964 | RRF 정규화 점수 (0~1) |
| Semantic | 0.8324 | Cosine 유사도 (0~1) |

### 6.3 인프라 헬스체크 응답 시간

| 엔드포인트 | 응답 시간 | 비고 |
|-----------|:---------:|------|
| `/api/v1/health` | <10ms | 의존성 상태 포함 |
| `/api/v1/auth/login` | <50ms | JWT 발급 |
| `/actuator/health` (backend) | <20ms | Spring Boot |
| `/actuator/health` (gateway) | <20ms | Spring Cloud Gateway |

---

## 7. 종합 평가

### 7.1 평가 요약

| 테스트 유형 | 결과 | 핵심 수치 | 판정 |
|------------|:----:|----------|:----:|
| **단위 테스트** | 174건 ALL PASS | 97% 커버리지 (5모듈) | PASS |
| **RAGAS 검색 품질** | A- 등급 | 산술평균 0.711, HIGH 33/51(65%) | PASS |
| **사전점검** | 18/18 컨테이너 정상 | CRITICAL 3건 전부 해결 | PASS |
| **업로드 E2E** | 13 케이스 | 9 PASS, 3 WARN, 1 FAIL -> 이슈 6건 전부 FIXED | PASS |
| **스키마 통일 후 재검증** | 14건 검색 전체 PASS | 298K RELATED_TO + 404K MENTIONS 통합 | PASS |
| **대용량 PDF** | 0/3 실패 | 타임아웃 1200s 통일 적용 | PARTIAL (미검증) |
| **성능** | 검색 정상 작동 | Keyword 19ms, Hybrid 18s, Semantic 4s | PASS (개선 여지) |

### 7.2 검색 파이프라인 진화

```
v8 (2026-02-13)     v9 (2026-02-16)     v10 (2026-02-16)    v11 (2026-02-16)
108K 청크            56K 청크             42K 청크             42K + Reranker
2-Way RRF           4-Way RRF            + Entity 23K         + BGE-Reranker

평균 0.632 (B)      평균 0.659 (B+)      평균 0.632 (B+)     평균 0.711 (A-)
HIGH 24건           HIGH 28건            HIGH 30건            HIGH 33건
NONE 11건           NONE 11건            NONE 10건            NONE 6건
```

**핵심 교훈**: "데이터의 양이 아닌 구조화의 질이 검색 성능을 결정한다"

- v8: 108K 청크 무차별 인덱싱 -> 산술평균 0.632
- v11: 42K 청크(-61%) + 엔티티 구조화 + Reranker -> 산술평균 0.711(+12.5%)

### 7.3 기술적 의의

1. **4-Way RRF + Reranker 검증**: Dense + Sparse + BM25(Nori) + Graph Search를 RRF로 결합하고 BGE-Reranker(ONNX)로 재순위. 한국어 1,437문서 / 7도메인 51쿼리에서 체계적으로 평가한 실무 사례

2. **3-Phase ETL 확립**: GPU 없는 환경에서도 Colab 무료 GPU를 활용한 대규모 RAG 구축 가능. 소규모 팀/개인 프로젝트에서 현실적으로 적용 가능한 아키텍처

3. **Post-RRF 엔티티 보강**: RRF 퓨전 후 chunk_id로 Neo4j MENTIONS 직접 조회하여 검색 재현율을 유지하면서 답변 관련성을 높이는 패턴 적용

4. **Reranker ROI 최고**: 코드 변경량 대비 효과가 가장 큰 개선. Context Precision +26%, Recall +42%

5. **온라인 업로드 파이프라인 완성**: 업로드 -> 파싱 -> 청킹 -> 임베딩 -> Neo4j 기본 그래프 -> 엔티티 추출 -> PG 메타데이터 갱신까지 전 과정 자동화. 3-Store(PG/ES/Neo4j) 일관성 확보

### 7.4 개선 권고사항

| 항목 | 현재 상태 | 개선 방향 | 우선순위 |
|------|----------|----------|:--------:|
| Hybrid Search 응답 시간 | 18초 | GPU 환경 + 비동기 파이프라인 | 높음 |
| 대용량 PDF 처리 | 타임아웃 1200s 적용 (미검증) | 비동기 업로드 + SSE 진행률 + 페이지 분할 파싱 | 높음 |
| Spring Cloud Gateway 타임아웃 | 120초 | 1200초로 통일 (별도 빌드 필요) | 높음 |
| semantic 도메인 | C+ (0.638) | 의미 검색 프롬프트 튜닝, 청크 전략 개선 | 중간 |
| legal 도메인 | C (0.592) | 법률 특화 문서 추가, 도메인 특화 엔티티 | 중간 |
| ai-service /metrics | 미구현 | Prometheus 메트릭 엔드포인트 구현 | 낮음 |
| Answer Relevancy | 0.621 | 프롬프트 최적화, 답변 생성 전략 개선 | 중간 |

### 7.5 결론

Hybrid RAG Knowledge Platform은 4-Way Hybrid Search + Knowledge Graph + BGE-Reranker를 통해 **RAGAS A- 등급(산술평균 0.711)** 을 달성했습니다. 42,462개 청크에서 169,886개 엔티티와 775,366개 관계를 구축하고, 51개 쿼리 중 33건(65%)이 HIGH 등급을 받았습니다.

단위 테스트 97% 커버리지, 18개 컨테이너 전원 정상 기동, 검색 API 3종 정상 작동이 확인되었습니다. Sprint 12 사용자 테스트에서 업로드 E2E 13케이스 중 발견된 이슈 6건을 모두 수정하고, Neo4j 스키마 통일 마이그레이션(298K RELATED_TO + 404K MENTIONS)을 완료했습니다. 스키마 통일 후 14건 검색 재검증에서 전체 PASS를 확인하여 **시스템 품질은 운영 가능 수준** 입니다.

대용량 PDF(Nike 10-K 3건) 테스트에서는 타임아웃 한계가 확인되어 1200초로 통일 적용했으며, 대시보드 빠른 검색 미동작 버그도 수정 완료했습니다.

DeepSeek V3.2 기반 $52 비용으로 전체 파이프라인을 구축한 비용 효율성은 소규모 팀에서 실용 RAG 시스템을 구축할 수 있음을 실증합니다.

---

*작성: Claude Code (Opus 4.6) | 2026-02-19*
