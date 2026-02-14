# Sprint 10 이슈 발견 및 현황 보고서 (업데이트 중)

**작성일**: 2026-02-14 20:33 KST
**최종 업데이트**: 2026-02-14 23:40 KST
**작성자**: Documenter Agent
**상태**: 업데이트 중 (ETL Phase 1 v4 실행 중 - OCR ON 품질 복원)
**스프린트**: Sprint 10

---

## 목차

1. [Sparse 벡터 미활용 GAP](#1-sparse-벡터-미활용-gap-critical)
2. [ES 유료 기능 사용 금지 원칙](#2-es-유료-기능-사용-금지-원칙-critical)
3. [Reranker 모델 버전 불일치](#3-reranker-모델-버전-불일치-critical)
4. [Gleaning 현황](#4-gleaning-현황-구현-완료-설정-확인-필요)
5. [Nori 한국어 분석기 적용 확인](#5-nori-한국어-분석기-적용-확인-결과)
6. [P0/P1 코드 수정 4건](#6-p0p1-코드-수정-4건-완료)
7. [ETL Phase 1 속도 최적화](#7-etl-phase-1-속도-최적화-58x-개선)

---

## 요약

| # | 이슈 | 심각도 | 상태 | 조치 |
|---|------|--------|------|------|
| 1 | Sparse 벡터 미활용 GAP | Critical | Phase 4 예정 | 설계서 완료 |
| 2 | ES 유료 기능 사용 금지 원칙 | Critical | 확인 완료 | 무료 대안 확정 |
| 3 | Reranker 모델 버전 불일치 | Critical | 수정 필요 | base -> v2-m3 교체 예정 |
| 4 | Gleaning 현황 | Info | 구현 완료 | 실행 시 검증 필요 |
| 5 | Nori 한국어 분석기 | Info | 정상 | 추가 조치 불필요 |
| 6 | P0/P1 코드 수정 4건 | P0/P1 | 완료 | ETL Phase 1 v2 실행 중 |
| 7 | ETL Phase 1 속도 최적화 + 품질 롤백 | P0 | 완료 | OCR OFF→ON 롤백, FAST 유지, v4 실행 중 |

---

## 1. Sparse 벡터 미활용 GAP (Critical)

### 문제

BGE-M3가 Sparse 벡터(lexical_weights)를 생성하고 Elasticsearch에 저장까지 완료하지만, **검색 단계에서 전혀 활용하지 않고 있음**. BGE-M3의 3-way 출력(Dense + Sparse + ColBERT) 중 Sparse가 완전히 사장됨.

### 원인

검색 파이프라인 구현 시 Dense kNN + BM25 + Graph 3-way RRF만 구현되었고, Sparse 벡터 검색 로직이 누락됨.

### 영향

- BGE-M3 사용 비용의 **절반 낭비** (Sparse 추론 비용 발생하지만 검색에 미반영)
- 학습된 어휘 매칭 능력(Learned Sparse Retrieval) 미활용
- BM25 대비 도메인 특화 키워드 매칭 성능 손실

### 관련 파일

| 단계 | 파일 | 라인 | 상태 |
|------|------|------|------|
| 생성 | `embedding.py` | `:670` | 완성 - FlagEmbedding에서 lexical_weights 추출 |
| 저장 | `es_storage.py` | `:84, :401-403` | 완성 - sparse_vector 필드 정의 및 저장 |
| 검색 | `search.py` | `:452-540` | **미구현** - Dense kNN만 사용 |
| RRF 융합 | `search.py` | `:354-379` | **미포함** - 3-way만 (Dense+BM25+Graph) |

### 조치 상태

- Phase 4로 Sparse 검색 통합 예정
- 설계서 완료: `docs/02_design/15_sparse_vector_search_integration_design.md`

### 비고

4-way RRF (Dense + Sparse + BM25 + Graph)로 확장 시 검색 정밀도 향상 기대.

---

## 2. ES 유료 기능 사용 금지 원칙 (Critical)

### 문제

Architect가 설계한 Sparse 검색 쿼리(`weighted_tokens`, `text_expansion`)가 ES **Platinum/Enterprise 라이선스** 전용 기능이며, 현재 프로젝트는 **ES Basic(무료) 라이선스**를 사용 중.

### 원인

ES 기능 도입 시 라이선스 호환성 확인 프로세스가 누락됨. 이전 차수에서도 동일한 실수가 발생한 바 있어 **반복 방지 필요**.

### 영향

- 설계서대로 구현 시 런타임 라이선스 오류 발생
- 유료 라이선스 전환 불가 (프로젝트 제약)

### 관련 파일

| 항목 | 파일 | 라인 | 내용 |
|------|------|------|------|
| 라이선스 설정 | `docker-compose.yml` | `:624` | `xpack.security.enabled=false` (Basic) |
| 유료 쿼리 (사용 불가) | 설계서 | - | `weighted_tokens`, `text_expansion` |

### 조치 상태

- **무료 대안 확정**: `bool > should > term` + `boost` 쿼리로 Sparse 토큰 가중치 검색
- BGE-M3 출력 예시: `{"금융": 0.82, "정책": 0.71}`
- 변환 쿼리:
  ```json
  {
    "bool": {
      "should": [
        {"term": {"text": {"value": "금융", "boost": 0.82}}},
        {"term": {"text": {"value": "정책", "boost": 0.71}}}
      ]
    }
  }
  ```

### 비고

**원칙 수립**: ES 기능 도입 시 반드시 라이선스 호환성 확인 후 사용. Basic/OSS에서 지원하는 기능만 사용할 것.

---

## 3. Reranker 모델 버전 불일치 (Critical)

### 문제

knowledge_service와 ai_service에서 서로 다른 Reranker 모델을 로딩하고 있으며, 문서/설계서에 기술된 모델과도 불일치.

### 원인

서비스별 독립 개발 과정에서 모델 버전 동기화가 누락됨.

### 영향

- knowledge_service: 소형 모델(base) 사용으로 리랭킹 품질 저하
- ai_service: ONNX Runtime 미구현으로 CPU에서 2~5x 성능 손실
- Docker 재시작 시 모델 캐시 손실, 반복 다운로드 발생

### 관련 파일

| 서비스 | 파일 | 라인 | 모델 | 문제 |
|--------|------|------|------|------|
| knowledge_service | `bge_reranker.py` | `:111` | `BAAI/bge-reranker-base` | 소형 모델, 성능 낮음 |
| ai_service | `bge_reranker.py` | `:108` | `BAAI/bge-reranker-v2-m3` | 다국어, 성능 높음 |
| 설계서/문서 | - | - | `bge-reranker-v2-m3` | 문서 기준 |

### 추가 확인 사항

- ai_service에 ONNX Runtime 미구현 (knowledge_service에만 있음) - CPU 환경에서 성능 손실
- 모델 캐싱 경로 불안정: Docker volume 미매핑으로 재시작 시 캐시 소실
- 유료 서비스(Cohere/Jina) 미사용 확인 완료 (전부 오픈소스 MIT/Apache)

### 조치 상태

- 수정 예정: `bge-reranker-base` -> `bge-reranker-v2-m3` 교체
- ONNX Runtime ai_service 이식 예정
- 캐시 경로 Docker volume 고정 예정

---

## 4. Gleaning 현황 (구현 완료, 설정 확인 필요)

### 문제

Gleaning 기능이 코드 레벨에서 100% 구현 완료되었으나, 실행 시 실제 동작 검증이 필요한 상태.

### 원인

ETL Phase 3 실행 전이므로 실제 Gleaning 동작을 확인할 수 없었음.

### 관련 파일

| 컴포넌트 | 파일 | 라인 | 상태 |
|----------|------|------|------|
| EntityExtractionService | `entity_extraction.py` | `:236-256` | Gleaning 100% 구현 |
| VIP Agent | `vip_agent.py` | `:241-309` | Gleaning 노드 100% 구현 |
| ETL Phase 3 설정 | `document_processing_pipeline.py` | `:751-760` | `enable_gleaning=True` 포함 |

### 구현 세부사항

- DeepSeek 호환: `logit_bias` 미지원 -> 프롬프트 기반 우회 구현 완료
- 기대 효과: 엔티티 +33%, 관계 +37% (Gleaning 1회 기준)

### 확인 필요 항목

- `settings.max_gleanings` 값 확인 (권장: 1)
- Phase 3 실행 시 실제 동작 검증

### 미구현 항목

- 문서 복잡도 판별(선택적 적용) - 향후 검토
- Auto-Tuning - 향후 검토

### 비고

참조 문서: `docs/02_design/technical_assessment/03_gleaning_knowledge_graph_quality_assessment.md`

---

## 5. Nori 한국어 분석기 적용 확인 결과

### 문제

Nori 한국어 분석기 적용 여부 확인 요청에 대한 조사 결과.

### 확인 결과

| 항목 | 파일 | 라인 | 상태 |
|------|------|------|------|
| 플러그인 설치 | `infrastructure/database/elasticsearch/Dockerfile` | `:4` | `analysis-nori` 설치 확인 |
| 인덱스 매핑 | `02_elasticsearch_mapping.json` | `:12-30` | `korean_analyzer` 정의 (nori_tokenizer + nori_part_of_speech) |
| 적용 필드 | 동일 매핑 파일 | - | `text`, `heading`, `metadata.title` 모두 적용 |

### 동작 방식

- BM25 키워드 검색 시 자동으로 Nori 형태소 분석 사용
- `nori_tokenizer`: 한국어 토큰화
- `nori_part_of_speech`: 불용 품사 제거 (stoptags 설정)

### 참고 사항

- `nori_part_of_speech` stoptags가 엄격한 편 - 특정 도메인 키워드가 제외될 가능성 있음
- 향후 도메인별 키워드 분석 후 stoptags 재검토 권장

### 조치 상태

**정상 적용 중, 추가 조치 불필요**

---

## 6. P0/P1 코드 수정 4건 (완료)

### 수정 내역

| 우선순위 | 항목 | 파일 | 라인 | 내용 |
|----------|------|------|------|------|
| P0-1 | ChunkQualityGate 파이프라인 통합 | `initial_data_loader.py` | `:~758` | 품질 게이트를 파이프라인에 통합 |
| P0-2 | Dedup 전상태 체크 | `initial_data_loader.py` | `:670-674` | 중복 제거 전 상태 검증 추가 |
| P1-1 | 코드/테이블 블록 크기 제한 | `chunker.py` | `:460-464` | 코드/테이블 청크 크기 상한 설정 |
| P1-2 | QualityGate 코드/테이블 bypass 제거 | `chunk_quality_filter.py` | `:68-79` | 코드/테이블도 품질 검증 적용 |

### 조치 상태

- 코드 수정: **완료**
- 컨테이너 리빌드: **완료**
- ETL Phase 1 v2: **실행 중**

---

## 7. ETL Phase 1 속도 최적화 (58x 개선)

### 배경

- ETL Phase 1 v2 실행 초기에 처리 속도가 매우 느린 것이 확인됨
- 1,786개 파일 중 13개 처리에 이미 상당한 시간 소요
- 전체 완료 예상 시간: 약 153시간 (6.4일)
- 주요 원인: PDF OCR 처리가 전체 시간의 70% 이상 차지

### 분석 과정

- 5인 전문가 분석팀 배치: Infra(자원 분석), ETL(파이프라인 분석), TL(병목 분석), Architect(최적화 설계), RAG(데이터 품질)
- **Infra 분석 결과**: Embedding Backfill 프로세스(PID 979)가 CPU 395%, 메모리 6.6GB 점유하며 ETL과 자원 경합
- **TL 분석 결과**: PDF 파싱 시간 실측 (MD=1초, PDF=2~23분)
  - 근본 원인: Docling의 RapidOCR이 텍스트 기반 PDF에도 OCR 실행
  - 테이블 인식 `ACCURATE` 모드가 불필요하게 정밀
- **Architect 설계**: 6가지 최적화 전략 제시 (11.4h -> 5.9h 예상)

### 적용된 코드 수정 (3건)

| # | 파일 | 수정 내용 | 효과 |
|---|------|----------|------|
| 1 | `src/app/etl/docling_adapter.py` `:101-102` | `do_ocr=False`, `force_backend_text=True` | PDF 내장 텍스트 레이어 직접 사용, OCR 제거 |
| 2 | `src/app/etl/docling_adapter.py` `:106` | `TableFormerMode.FAST` | 테이블 인식 속도 50-70% 향상 |
| 3 | `scripts/run_etl_phase1_chunks.py` `:125-146` | 파일 유형별 처리 순서 정렬 | MD/TXT -> HTML -> DOCX -> PPTX -> PDF 순서, 경량 파일 우선 처리 |

### 추가 조치

- Embedding Backfill 프로세스(PID 979) 강제 종료 -> CPU 395% -> 8%, 메모리 6.6GB -> 5.4GB로 즉시 개선
- 컨테이너 리빌드 후 ETL Phase 1 v3 재시작

### 결과

- PDF 파싱 속도: **16분 -> 16.6초 (58x 개선)**
- 전체 ETL 예상 시간: 153시간 -> 약 3~4시간
- 관련 설계서: `docs/02_design/18_etl_phase1_speed_optimization_design.md`

### 현재 진행 상황 (2026-02-14 22:35 KST 기준)

| 항목 | 값 |
|------|-----|
| 전체 파일 | 1,786 |
| 성공 | 83 |
| 실패 | 0 |
| Dedup 스킵 | 161 |
| ES 청크 수 | 6,226 |
| Quality Gate 통과 | 313 청크 |
| Quality Gate 거부 | 73 청크 |
| 상태 | 진행 중 |

### 후속 검토: OCR OFF 품질 문제 발견 및 롤백

**발견 시점**: 2026-02-14 23:27 KST

#### 문제 발견

ETL Phase 1 v3 (OCR OFF) 실행 결과물의 청크 품질을 분석한 결과, 심각한 품질 저하가 확인됨.

**청크 품질 분석 결과 (ES 6,676 chunks 기준)**:

| 구간 | 청크 수 | 비율 | 평가 |
|------|---------|------|------|
| 0-30 tokens (junk) | 1,011 | 15.1% | 검색 불가 |
| 30-100 tokens (short) | 2,877 | 43.1% | 정보량 부족 |
| 100-300 tokens (normal) | 2,685 | 40.2% | 적정 |
| 300-600 tokens (good) | 90 | 1.3% | 양호 |
| 600+ tokens (long) | 13 | 0.2% | - |

- 평균 103 tokens/chunk (chunk_size=1000 chars 대비 매우 낮음)
- **전체의 58.2%가 100 tokens 미만**
- Quality Gate 거부율 29.5% (v3)

**파일 유형별 분석**:

| 유형 | 청크 수 | 평균 tokens | 비고 |
|------|---------|------------|------|
| .md | 3,658 | 73 | 가장 낮음 - 과도한 분할 |
| .pdf | 2,638 | 134 | OCR OFF 영향 |
| .pptx | 132 | 191 | 양호 |
| .html | 130 | 228 | 양호 |
| .txt | 123 | 133 | 보통 |

#### 근본 원인

- **OCR OFF는 품질과 속도의 트레이드오프에서 속도를 과도하게 우선한 판단**
- Docling을 사용하는 핵심 이유가 OCR 기능인데, 이를 비활성화하면 본말전도
- 스캔 PDF에서 텍스트 추출 자체가 불가능해져 빈/짧은 청크 다량 생산
- MD 파일의 낮은 평균(73t)은 별도 원인 - 시맨틱 청커의 과도한 분할

#### 의사결정 과정

1. **2-Pass 조건부 OCR 시도** (23:28): 텍스트 기반 PDF는 빠르게, 스캔 PDF만 OCR 적용하는 중간안 구현
2. **사용자 결정: 전면 OCR ON** (23:30): "차라리 모든 파일에 OCR ON 시켜" → 2-Pass 방식 폐기
3. **최종 확정** (23:35): OCR ON + TableFormerMode.FAST 조합

#### TableFormerMode.FAST 영향 평가

- FAST vs ACCURATE 차이: 테이블 셀 경계 인식 정밀도만 다름
- 단순 그리드 테이블 → 정확도 거의 동일 (95%+)
- 복잡한 병합 셀에서만 약간의 차이 (3-5%)
- **속도 50-70% 가속, 품질 영향 미미** → 유지 결정

#### Colab GPU 파싱 검토

- Phase 1 파싱(OCR+TableFormer)도 GPU 가속 가능 → PDF당 16분 → 1~2분
- **현실적 제약**: 문서 업로드, DB 접근(터널링 필요), 네트워크 레이턴시
- **현재 결정**: CPU로 진행 (밤새 돌리면 아침 완료), 향후 필요 시 Colab 파싱 파이프라인 구성 검토

#### 조치 사항

1. ETL Phase 1 v3 중단 (23:28)
2. `docling_adapter.py` 수정: `do_ocr=True` (OCR ON) + `TableFormerMode.FAST` 유지
3. 3-Store 완전 초기화 (ES=0, PG=0, Neo4j=0)
4. 컨테이너 리빌드
5. ETL Phase 1 v4 시작 (23:36 KST)

#### ETL Phase 1 v4 초기 결과 (23:40 KST)

| 항목 | v3 (OCR OFF) | v4 (OCR ON) | 비교 |
|------|-------------|-------------|------|
| QualityGate 거부율 | 29.5% | **4.4%** | 6.7x 개선 |
| 성공 | 83 | 183 | - |
| 실패 | 0 | 0 | 동일 |
| 상태 | 중단 | 진행 중 | - |

---

## 향후 계획

| 이슈 | 다음 단계 | 예상 시기 |
|------|----------|----------|
| Sparse 벡터 GAP | Phase 4에서 4-way RRF 구현 | Sprint 11+ |
| ES 유료 기능 금지 | 라이선스 확인 체크리스트 도입 | 즉시 |
| Reranker 불일치 | base -> v2-m3 교체 + ONNX 이식 | Sprint 11 |
| Gleaning 검증 | Phase 3 실행 시 검증 | ETL Phase 3 |
| Nori stoptags | 도메인 키워드 분석 후 재검토 | 향후 |
| P0/P1 수정 | ETL Phase 1 v4 실행 중 (OCR ON + FAST, 품질 롤백 적용) | 진행 중 |
| Colab GPU 파싱 | Phase 1 파싱을 GPU에서 실행하는 파이프라인 검토 | 향후 |

---

> **NOTE**: 본 문서는 업데이트 중입니다. ETL Phase 1 v3 완료 후 실행 결과 및 추가 발견 사항을 반영하여 최종 업데이트 예정입니다.
>
> **최종 업데이트**: 2026-02-14 23:40 KST (ETL Phase 1 v4 실행 중 - OCR ON 품질 복원)
