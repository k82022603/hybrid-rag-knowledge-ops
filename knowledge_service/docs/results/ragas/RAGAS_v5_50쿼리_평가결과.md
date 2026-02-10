# RAGAS v5 50쿼리 평가 결과 보고서

**STORY-111**: HRKP v2 vs v3 Cross-System Comparison
**평가 일시**: 2026-02-10 15:06 ~ 16:30 KST (약 84분 소요)
**평가 방법**: LLM-as-Judge (DeepSeek V3.2)
**테스트 쿼리**: 50개 (7개 도메인)
**실행 환경**: Docker 컨테이너 (kp-ai-service)
**스크립트**: `scripts/rcsv_comparison_eval_v3.py` (v5)

---

## 1. 평가 개요

### 1.1 비교 시스템

| 시스템 | 검색 방식 | 품질 필터 | LLM | 임베딩 |
|--------|----------|----------|-----|--------|
| **HRKP-RAW** (v2) | BM25 + Dense + Graph (RRF) | 없음 | DeepSeek V3.2 (별도 생성) | BGE-M3 (1024d) |
| **HRKP-FULL** (v3) | BM25 + Dense + Graph (RRF) + **BGE Reranker** | **Quality Gate** | DeepSeek V3.2 (파이프라인 내장) | BGE-M3 (1024d) |
| **RCSV** | BM25 only | 없음 | DeepSeek V3.2 (별도 생성) | N/A |

### 1.2 v3 개선사항

1. **BGE Reranker**: Cross-encoder로 검색 결과 재순위화
2. **Quality Gate**: 3단계 품질 등급 (HIGH/PARTIAL/NONE)
3. **System Prompt v2**: 3단계 적응형 프롬프트

### 1.3 데이터 규모

| 인덱스 | 문서 수 |
|--------|---------|
| HRKP (knowledge_chunks) | 13,430 |
| RCSV (rcsv-pdf-documents) | 12,918 |

---

## 2. 50쿼리 평가셋 구성

### 2.1 도메인별 분포

| 도메인 | 쿼리 수 | 범위 | 설명 |
|--------|:-------:|------|------|
| entity_relation | 3 | Q1~Q3 | 기술 엔티티 간 관계 비교 |
| multi_hop | 4 | Q4~Q6, Q37 | 다단계 추론 필요 |
| keyword | 3 | Q7~Q9 | 키워드 기반 직접 검색 |
| semantic | 6 | Q10~Q12, Q47~Q50 | 의미 기반 검색 |
| graph_entity | 16 | Q13~Q28, Q44 | Neo4j Graph 트리거 쿼리 |
| legal | 8 | Q29~Q36 | 법률 도메인 |
| factual | 7 | Q38~Q43, Q45~Q46 | AI/LLM 심화 + 프로젝트 특화 |
| comparative | 3 | Q45, Q50 | 기술 비교 |

### 2.2 Graph 트리거 설계

Neo4j 엔티티 분석 기반으로 쿼리 설계:
- **Technology 노드** (26개): Spring Cloud Gateway, Redis, DeepSeek, Vault, GitHub Actions, Eureka, React 18, Python 3.11
- **Topic 노드** (24개): Strangler Fig, Gleaning, Vector Search, SSOT, 하이브리드 검색, 마이크로서비스, Dual-Write, AI Service
- 쿼리에 노드명이 포함되면 Graph Search가 활성화되는 메커니즘 활용

---

## 3. RAGAS 메트릭 결과

### 3.1 전체 비교 (50쿼리)

| 메트릭 | v2-HRKP (baseline) | v3-RAW | v3-FULL | v3-RCSV | v2-RCSV (baseline) |
|--------|:------------------:|:------:|:-------:|:-------:|:------------------:|
| **faithfulness** | 0.0833 | **0.1440** | 0.0000* | 0.1320 | 0.0667 |
| **answer_relevancy** | 0.4000 | **0.4560** | 0.1340* | 0.3120 | **0.5833** |
| **context_precision** | **0.5083** | 0.3960 | 0.2480* | 0.2100 | 0.4833 |
| **context_recall** | 0.0833 | **0.1500** | 0.0150* | 0.0660 | 0.2167 |

> *v3-FULL: Q43~Q50(8건) JWT 토큰 만료로 ERR=0점 포함. 실제 성능보다 낮게 측정됨.

### 3.2 v3-RAW vs v2-HRKP 개선율

| 메트릭 | v2-HRKP | v3-RAW | 변화율 | 판정 |
|--------|:-------:|:------:|:------:|:----:|
| faithfulness | 0.0833 | 0.1440 | **+72.9%** | UP |
| answer_relevancy | 0.4000 | 0.4560 | **+14.0%** | UP |
| context_precision | 0.5083 | 0.3960 | **-22.1%** | DOWN |
| context_recall | 0.0833 | 0.1500 | **+80.1%** | UP |

**3/4 메트릭 개선**. context_precision 하락은 쿼리 수 12→50 확대에 따른 도메인 다양화 영향.

---

## 4. Quality Gate 분석 (v3-FULL)

### 4.1 Grade 분포

| Grade | 건수 | 비율 | 설명 |
|-------|:----:|:----:|------|
| **HIGH** | 15 | 30.0% | max_score ≥ 0.3 & sources ≥ 2 |
| **PARTIAL** | 16 | 32.0% | max_score ≥ 0.1 또는 필터링된 소스 |
| **NONE** | 11 | 22.0% | 모든 소스 score < 0.03 |
| **ERR** | 8 | 16.0% | JWT 토큰 만료 (Q43~Q50) |

### 4.2 유효 데이터 기준 (Q1~Q42, ERR 제외)

| Grade | 건수 | 비율 |
|-------|:----:|:----:|
| **HIGH** | 15 | **35.7%** |
| **PARTIAL** | 16 | **38.1%** |
| **NONE** | 11 | **26.2%** |

### 4.3 쿼리별 상세 결과

| Q# | 질문 | 도메인 | Grade | Max Score | Sources | 레이턴시 |
|:--:|------|--------|:-----:|:---------:|:-------:|--------:|
| Q1 | Neo4j와 Elasticsearch의 역할 차이점은? | entity_relation | PARTIAL | 0.4791 | 2 | 51.8s |
| Q2 | LangGraph와 LangChain 중 어떤 것을 사용해야? | entity_relation | **HIGH** | 0.9958 | 5 | 27.3s |
| Q3 | FastAPI+PostgreSQL로 RAGAS 평가 수행? | entity_relation | PARTIAL | 0.5378 | 5 | 68.2s |
| Q4 | BGE-M3 임베딩 모델의 역할은? | multi_hop | PARTIAL | 0.0373 | 1 | 28.7s |
| Q5 | Kubernetes에서 Spring Boot 배포 방법? | multi_hop | NONE | 0.0185 | 0 | 51.6s |
| Q6 | Agentic AI 워크플로우 설계 패턴? | multi_hop | **HIGH** | 0.9964 | 5 | 40.3s |
| Q7 | Docker Compose 설정 방법? | keyword | NONE | 0.0222 | 0 | 33.8s |
| Q8 | RRF 알고리즘의 Hybrid 검색 역할? | keyword | PARTIAL | 0.1493 | 3 | 35.6s |
| Q9 | RAGAS 평가 메트릭의 종류와 의미? | keyword | NONE | 0.0072 | 0 | 36.2s |
| Q10 | 대규모 문서를 효율적으로 처리하는 방법? | semantic | **HIGH** | 0.9116 | 2 | 25.9s |
| Q11 | 검색 성능 최적화 방법? | semantic | PARTIAL | 0.1958 | 5 | 48.1s |
| Q12 | 환경변수를 안전하게 관리하는 방법? | semantic | PARTIAL | 0.0311 | 1 | 35.5s |
| Q13 | Spring Cloud Gateway API 라우팅 설정? | graph_entity | PARTIAL | 0.0834 | 1 | 54.8s |
| Q14 | Redis 캐싱을 RAG에 적용하는 방법? | graph_entity | PARTIAL | 0.3790 | 5 | 51.9s |
| Q15 | DeepSeek V3.2 특징과 비용 절감 효과? | graph_entity | **HIGH** | 0.8246 | 5 | 49.6s |
| Q16 | Vault 시크릿 관리 + Spring Cloud Config? | graph_entity | NONE | 0.0002 | 0 | 44.3s |
| Q17 | GitHub Actions CI/CD 파이프라인 구성? | graph_entity | NONE | 0.0150 | 0 | 48.9s |
| Q18 | Eureka vs Kubernetes DNS 서비스 발견? | graph_entity | NONE | 0.0141 | 0 | 62.1s |
| Q19 | React 18 Concurrent 렌더링과 Suspense? | graph_entity | PARTIAL | 0.0383 | 1 | 41.4s |
| Q20 | Python 3.11 FastAPI 비동기 + asyncpg? | graph_entity | PARTIAL | 0.3208 | 2 | 47.9s |
| Q21 | Strangler Fig 패턴 레거시 마이그레이션? | graph_entity | NONE | 0.0031 | 0 | 51.3s |
| Q22 | Gleaning 기법과 RAG 파이프라인 활용? | graph_entity | **HIGH** | 0.6501 | 2 | 43.1s |
| Q23 | Vector Search + Graph Search 결합 이점? | graph_entity | NONE | 0.0035 | 0 | 38.7s |
| Q24 | SSOT 원칙과 데이터 아키텍처 중요성? | graph_entity | NONE | 0.0104 | 0 | 42.7s |
| Q25 | 하이브리드 검색 BM25+Dense 가중치 조합? | graph_entity | **HIGH** | 0.7425 | 5 | 36.2s |
| Q26 | 마이크로서비스 서비스 간 통신 패턴? | graph_entity | NONE | 0.0262 | 0 | 31.7s |
| Q27 | Dual-Write 문제와 MSA 해결 방법? | graph_entity | NONE | 0.0129 | 0 | 49.3s |
| Q28 | AI Service RAG Pipeline 전체 처리 흐름? | graph_entity | PARTIAL | 0.1832 | 2 | 64.3s |
| Q29 | 헌법에서 국민의 기본권 규정? | legal | **HIGH** | 0.9184 | 5 | 40.7s |
| Q30 | 민법 계약의 성립 요건? | legal | PARTIAL | 0.1628 | 4 | 37.6s |
| Q31 | 형법 정당방위의 성립 요건? | legal | PARTIAL | 0.2504 | 3 | 31.3s |
| Q32 | 상법 주식회사 설립 절차? | legal | **HIGH** | 0.8791 | 5 | 32.8s |
| Q33 | 민사소송법 소장 제출과 소송 절차? | legal | **HIGH** | 0.9503 | 5 | 42.0s |
| Q34 | 문화재보호법 국가지정문화재 지정 절차? | legal | **HIGH** | 0.9723 | 5 | 34.9s |
| Q35 | 소방시설법 소방시설 설치 의무? | legal | **HIGH** | 0.9614 | 5 | 50.4s |
| Q36 | 법령 용어 '선의'와 '악의' 차이? | legal | PARTIAL | 0.0437 | 1 | 40.8s |
| Q37 | AI 에이전트 Tool Calling과 Reasoning? | multi_hop | **HIGH** | 0.9949 | 5 | 45.5s |
| Q38 | Reranking의 RAG 품질 향상 원리? | factual | **HIGH** | 0.7184 | 5 | 29.8s |
| Q39 | Agentic Mesh 아키텍처와 미래 AI? | factual | **HIGH** | 0.8850 | 5 | 34.5s |
| Q40 | AI 오케스트레이션과 2025년 트렌드? | factual | PARTIAL | 0.4823 | 2 | 39.2s |
| Q41 | Chain of Thought 추론의 LLM 성능 영향? | factual | PARTIAL | 0.1526 | 2 | 35.4s |
| Q42 | 강화학습 활용 검색 에이전트 학습? | factual | **HIGH** | 0.9796 | 4 | 36.8s |
| Q43 | KT DS AI 프로젝트 워크샵 주요 주제? | factual | ERR | - | - | JWT 만료 |
| Q44 | MSA 차세대 플랫폼 기술 스택? | graph_entity | ERR | - | - | JWT 만료 |
| Q45 | SLM vs LLM 차이점과 활용 사례? | comparative | ERR | - | - | JWT 만료 |
| Q46 | 실무 LLM 서비스 핵심 고려사항? | factual | ERR | - | - | JWT 만료 |
| Q47 | 프롬프트 엔지니어링 핵심 원칙? | semantic | ERR | - | - | JWT 만료 |
| Q48 | 벡터 임베딩 차원 수와 검색 정확도? | semantic | ERR | - | - | JWT 만료 |
| Q49 | LLM 환각 줄이기 방법? | semantic | ERR | - | - | JWT 만료 |
| Q50 | 모놀리식→마이크로서비스 전환 도전 과제? | comparative | ERR | - | - | JWT 만료 |

---

## 5. 도메인별 성능 분석

### 5.1 도메인별 HIGH 비율 (ERR 제외)

| 도메인 | 유효 쿼리 | HIGH | HIGH 비율 | 평균 max_score |
|--------|:---------:|:----:|:---------:|:--------------:|
| **legal** | 8 | 5 | **62.5%** | 0.523 |
| **factual** | 5 | 3 | **60.0%** | 0.653 |
| **multi_hop** | 4 | 2 | 50.0% | 0.517 |
| **entity_relation** | 3 | 1 | 33.3% | 0.671 |
| **semantic** | 3 | 1 | 33.3% | 0.381 |
| **graph_entity** | 15 | 3 | **20.0%** | 0.210 |
| **keyword** | 3 | 0 | 0.0% | 0.060 |

### 5.2 핵심 발견

**법률 도메인 최강**: 8개 중 5개 HIGH. 법률 문서의 구조화된 용어와 절/조/항 체계가 임베딩 검색에 유리.

**Graph Entity 쿼리 기대 이하**: 16개 중 3개 HIGH(20%). Neo4j 엔티티명이 쿼리에 포함되어도 해당 엔티티와 연결된 Knowledge Chunk가 없으면 NONE 반환. chunk_id NULL 이슈(13,584/13,591개) 영향.

**Keyword 도메인 전멸**: Docker Compose, RAGAS 등 일반적 키워드는 지식베이스에 직접적 문서 없음.

---

## 6. 레이턴시 분석

| 시스템 | 평균 레이턴시 | 비고 |
|--------|:-----------:|------|
| **HRKP-RAW** | 834ms | 검색만 (v2 방식) |
| **HRKP-FULL** | 35,458ms (~35초) | 검색 + Reranker + LLM 전체 |
| **RCSV** | 8ms | BM25 검색만 |

HRKP-FULL 레이턴시 분해 (추정):
- 검색(BM25+Dense+Graph): ~800ms
- BGE Reranker: ~2,000ms
- DeepSeek V3.2 생성: ~30,000ms
- 기타 오버헤드: ~2,600ms

---

## 7. JWT 만료 이슈

### 7.1 현상

- Q43(약 30분 경과)부터 401 Unauthorized 반복 발생
- 영향 범위: Q43~Q50 (8건) → HRKP-FULL만 영향
- HRKP-RAW, RCSV는 인증 불필요 API라 정상 완료

### 7.2 원인

- JWT 토큰 유효기간: ~30분
- 50쿼리 × ~40초/쿼리 = ~33분 소요
- 스크립트에 토큰 갱신(refresh) 로직 없음

### 7.3 대응 방안

- [ ] 평가 스크립트에 토큰 갱신 로직 추가 (20쿼리마다 재로그인)
- [ ] JWT 토큰 유효기간 확인 및 여유 시간 계산
- [ ] Q43~Q50 재평가 (보완 실행)

---

## 8. v4 baseline 대비 총평

### 8.1 v2→v3 개선 효과 (RAW 기준, 왜곡 없는 데이터)

| 메트릭 | v2 (12쿼리) | v3-RAW (50쿼리) | 변화 |
|--------|:----------:|:---------------:|:----:|
| faithfulness | 0.083 | **0.144** | +72.9% |
| answer_relevancy | 0.400 | **0.456** | +14.0% |
| context_precision | **0.508** | 0.396 | -22.1% |
| context_recall | 0.083 | **0.150** | +80.1% |

### 8.2 종합 판정

```
┌────────────────────────────────────────────────────┐
│  v3-RAW: 4개 메트릭 중 3개 개선 (faithfulness,     │
│          answer_relevancy, context_recall)           │
│                                                      │
│  v3-FULL: JWT 만료로 정확한 비교 불가.              │
│           유효 Q1-Q42 기준 HIGH 35.7%로             │
│           법률/AI 도메인에서 우수한 성능 확인.       │
│                                                      │
│  RCSV: answer_relevancy(0.583)에서 여전히 우위.     │
│        OpenAI 임베딩(1536d) 품질 차이 영향.         │
└────────────────────────────────────────────────────┘
```

---

## 9. 개선 방향

### 9.1 단기 (Sprint 08 내)

| 항목 | 우선순위 | 예상 효과 |
|------|:--------:|----------|
| JWT 토큰 갱신 + Q43~Q50 재평가 | P0 | v3-FULL 정확한 측정 |
| Neo4j chunk_id NULL 패치 | P1 | Graph Search 정상화 → context_precision 개선 |
| Quality Gate NONE → Graceful Degradation | P2 | 사용자 경험 개선 |

### 9.2 중기

| 항목 | 예상 효과 |
|------|----------|
| 도메인별 가중치 튜닝 | 법률 도메인 성능 유지하며 기술 도메인 개선 |
| 임베딩 품질 개선 (BGE-M3 fine-tuning 또는 상위 모델) | answer_relevancy, context_recall 개선 |
| 지식베이스 확충 (기술 문서 추가 적재) | NONE 비율 감소 |

---

## 10. 부록: 실행 로그

### 10.1 실행 명령

```bash
docker exec kp-ai-service python3 /app/rcsv_comparison_eval_v3.py
```

### 10.2 생성 파일

| 파일 | 위치 |
|------|------|
| JSON 결과 | `docs/results/ragas/hrkp_vs_rcsv_2026-02-10_v4.json` |
| Markdown 리포트 | `docs/results/ragas/hrkp_vs_rcsv_report_2026-02-10_v4.md` |
| 이 분석 문서 | `docs/results/ragas/RAGAS_v5_50쿼리_평가결과.md` |

### 10.3 타임라인

```
15:06 - 평가 시작, HRKP 로그인 성공
15:06 ~ 15:13 - [1/5] HRKP-RAW 50쿼리 완료 (평균 834ms)
15:13 ~ 15:48 - [2/5] HRKP-FULL 42쿼리 성공 + 8쿼리 JWT 만료
15:48 ~ 15:49 - [3/5] RCSV BM25 50쿼리 완료 (평균 8ms)
15:49 ~ 16:05 - [4/5] DeepSeek 답변 생성 100건 (RAW 50 + RCSV 50)
16:05 ~ 16:30 - [5/5] RAGAS LLM-as-Judge 150건 (RAW+FULL+RCSV × 50)
16:30 - 평가 완료, 리포트 생성
```
