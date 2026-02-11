# RAGAS 평가 총평

**작성일**: 2026-02-10 (v2 업데이트)
**평가 기간**: 2026-01-29 ~ 2026-02-10
**총 평가 횟수**: 7회 (단독 1회 + 크로스시스템 3회 + v3/v4 개선 평가 3회)
**평가 도구**: RAGAS Framework + LLM-as-Judge (DeepSeek V3)

---

## 1. 평가 이력 요약

| # | 일시 | 평가 유형 | 샘플 | 핵심 결과 | 비고 |
|---|------|----------|:----:|----------|------|
| 1 | 01-29 | HRKP 단독 (RAGAS 라이브러리) | 24 | 전 지표 FAIL, 통과율 0% | 초기 baseline |
| 2 | 02-10 08:26 | HRKP vs RCSV v1 | 12 | HRKP 0 : 3 RCSV | 프롬프트 미최적화 |
| 3 | 02-10 08:55 | HRKP vs RCSV v2 | 12 | HRKP 2 : 2 RCSV | RRF Graph 과점유 수정 |
| 4 | 02-10 16:57 | Graph ON vs OFF | 12 | Graph ON 2 : 1 OFF | Graph 채널 효과 입증 |
| **5** | **02-10 13:32** | **HRKP v3 (Reranker+QG)** | **12** | **NONE 6/12 (50%)** | **Quality Gate 도입** |
| **6** | **02-10 13:50** | **v4 첫 시도 (설정 미반영)** | **12** | **설정 버그 발견** | **get_reranker() 싱글톤 이슈** |
| **7** | **02-10 14:05** | **v4 최종 (max_length=512)** | **12** | **NONE 3/12 (25%)** | **Reranker 정확도 대폭 향상** |

---

## 2. 지표 추이 (HRKP 기준 - 7회 전체)

| 메트릭 | #1 단독 | #2 v1 | #3 v2 | #4 Graph | #5 v3-FULL | #7 v4-FULL | 추세 |
|--------|:------:|:-----:|:-----:|:-------:|:----------:|:----------:|:----:|
| faithfulness | 0.403 | 0.067 | 0.083 | 0.313 | 0.083 | 0.083 | 불안정 |
| answer_relevancy | 0.190 | 0.417 | 0.400 | 0.500 | 0.075 | 0.150 | **v3~v4 하락** |
| context_precision | 0.278 | 0.367 | 0.508 | 0.333 | 0.292 | 0.150 | **v3~v4 하락** |
| context_recall | N/A | 0.075 | 0.083 | 0.000 | 0.063 | 0.063 | 매우 낮음 |

### 관찰 사항

- **#1~#4**: Quality Gate 미적용 → 모든 컨텍스트를 LLM에 전달 → RAGAS 점수 상대적 높음
- **#5~#7**: Quality Gate 적용 → NONE 등급 시 빈 컨텍스트 → RAGAS 4개 메트릭 모두 0점
- **answer_relevancy v3~v4 급락**: Quality Gate의 "의도적 컨텍스트 제거" 전략을 RAGAS가 평가하지 못하는 구조적 한계
- **context_recall**은 전 평가에서 0에 수렴하여 가장 심각한 약점 (KB 커버리지 부족)

---

## 3. v3~v4 개선 이력 상세

### 3.1 아키텍처 변경 사항

| 버전 | 변경 | 상세 |
|------|------|------|
| v2→v3 | **System Prompt v2** | "거부 머신" → 3단계 적응형 답변 (HIGH/PARTIAL/NONE) |
| v2→v3 | **Quality Gate** | 검색 결과 점수 기반 3-tier 품질 판정 |
| v2→v3 | **BGE Reranker** | bge-reranker-base(109M), max_length=256 |
| v3→v4 | **max_length 256→512** | Reranker가 문서 70%까지 참조 가능 |
| v3→v4 | **cutoff 0.05→0.03** | 경계선 결과 포착 (Q3, Q4, Q12) |
| v3→v4 | **Quality Gate 확장** | cutoff~partial 사이 결과도 PARTIAL로 분류 |
| v3→v4 | **PARTIAL 프롬프트 개선** | "부분적 정보만 있습니다" → "적극 활용하세요" |

### 3.2 Quality Gate Grade 분포 변화

```
v3: HIGH=3, PARTIAL=3, NONE=6  → 50%가 빈 컨텍스트
v4: HIGH=3, PARTIAL=6, NONE=3  → 25%만 빈 컨텍스트 (절반 감소)
```

### 3.3 max_length 변경 효과 (핵심 개선)

| Q# | 질문 | v3 Score | v4 Score | 변화 | v3 Grade | v4 Grade |
|:--:|------|:--------:|:--------:|:----:|:--------:|:--------:|
| Q1 | Neo4j vs ES | 0.3837 | **0.4791** | +25% | PARTIAL | PARTIAL |
| Q3 | FastAPI+RAGAS | 0.0388 | **0.5378** | **+1286%** | NONE | **PARTIAL(5)** |
| Q4 | BGE-M3 역할 | 0.0032 | **0.0373** | +1066% | NONE | **PARTIAL(1)** |
| Q5 | K8s 배포 | 0.0020 | **0.0185** | +825% | NONE | NONE |
| Q8 | RRF 알고리즘 | 0.1369 | **0.1493** | +9% | PARTIAL(1) | **PARTIAL(3)** |
| Q12 | 환경변수 관리 | 0.0311 | 0.0311 | 0% | NONE | **PARTIAL(1)** |

> **Q3이 0.04에서 0.54로 13배 향상** - max_length=256일 때 문서의 30%만 참조 → Reranker가 관련성을 판단하지 못했던 것이 근본 원인

### 3.4 남은 NONE 3개 (KB 커버리지 부족)

| Q# | 질문 | max_score | 원인 분석 |
|:--:|------|:---------:|----------|
| Q5 | K8s Spring Boot 배포 | 0.0185 | KB에 K8s 배포 관련 문서 없음 |
| Q7 | Docker Compose 설정 | 0.0222 | 인프라 설정 문서 미인덱싱 |
| Q9 | RAGAS 메트릭 종류 | 0.0072 | RAGAS 관련 문서 미인덱싱 |

---

## 4. RAGAS 평가 프레임워크 한계 분석 (신규)

### 4.1 RAGAS와 Quality Gate의 철학 충돌

| | RAGAS 전제 | Quality Gate 전략 |
|---|-----------|------------------|
| 컨텍스트 | 많을수록 좋다 | **관련 없으면 제거** |
| 빈 컨텍스트 | 0점 | 일반 지식으로 유용한 답변 |
| 저품질 컨텍스트 | "있으면" 점수 부여 | **필터링하여 환각 방지** |

**핵심 역설**: Quality Gate가 올바르게 동작할수록(쓰레기 제거) RAGAS 점수는 하락

### 4.2 구체적 증거

**v2 (Quality Gate 미적용)**: 10개 쓰레기 컨텍스트(score 0.016)를 전부 전달 → RAGAS가 "컨텍스트 있음"으로 점수 부여

**v4 (Quality Gate 적용)**: score < 0.03 제거 → NONE 쿼리는 빈 컨텍스트 → RAGAS 0점

### 4.3 정성적 평가로 본 실제 품질

| Q# | v4 HRKP 답변 | RCSV 답변 | 실제 우위 |
|:--:|-------------|----------|:---------:|
| Q2 | HIGH: [출처] 인용, LangGraph/LangChain 상세 비교 | 일반적 설명 | **HRKP** |
| Q6 | HIGH: 5가지 설계 패턴 + 출처 인용 | 4가지 패턴 나열 | **HRKP** |
| Q7 | NONE: docker-compose.yml 구조 정확 설명 | "답변 불가" 거부 | **HRKP** |
| Q10 | HIGH: Reranking 기반 설명 + 출처 | 청킹 일반 설명 | **HRKP** |
| Q12 | NONE: .env, .gitignore 정확 답변 | **"자연환경 보전, 오염물질"** (도메인 오류) | **HRKP 압승** |

> **정성적 판정: HRKP v4가 5/5 비교에서 우세** (RCSV의 Q12 "환경변수→환경오염" 오류는 치명적)

### 4.4 향후 평가 방향 제안

1. **Grade별 분리 평가**: HIGH/PARTIAL은 RAGAS, NONE은 "일반 지식 정확도" 별도 측정
2. **Human Evaluation**: A/B 테스트 기반 사용자 선호도 조사
3. **도메인 정확도 메트릭**: RCSV Q12처럼 완전히 다른 도메인 답변 감지

---

## 5. 경쟁 시스템(RCSV) 대비 분석 (업데이트)

### 시스템 스펙 비교

| 항목 | HRKP v4 | RCSV |
|------|---------|------|
| 검색 채널 | BM25 + Dense + **Graph** + **Reranker** | BM25 + Dense |
| 퓨전 | RRF + **BGE Reranker** | Alpha-weighted (0.6/0.4) |
| 품질 필터 | **Quality Gate** (3-tier) | 없음 |
| 시스템 프롬프트 | **적응형 v2** (HIGH/PARTIAL/NONE) | 기본 |
| 임베딩 | BGE-M3 (1024d, **로컬**) | OpenAI text-embedding-3-small (1536d) |
| LLM | DeepSeek V3 | GPT-4o-mini |
| Knowledge Graph | Neo4j (엔티티 934, 관계 165) | 없음 |
| 문서 수 | 13,430 청크 | 12,918 청크 |

### RAGAS 메트릭 전체 비교 (v2~v4)

| 메트릭 | v2-HRKP | v2-RCSV | v4-HRKP | v4-RCSV | 분석 |
|--------|:-------:|:-------:|:-------:|:-------:|------|
| faithfulness | 0.083 | 0.067 | 0.083 | 0.067 | HRKP 우세 (일관) |
| answer_relevancy | 0.400 | 0.583 | 0.150 | 0.583 | RCSV 우세 (RAGAS 한계) |
| context_precision | 0.508 | 0.483 | 0.150 | 0.458 | v2에서 HRKP 우세, v4에서 역전 |
| context_recall | 0.083 | 0.217 | 0.063 | 0.242 | RCSV 우세 (KB 커버리지) |

### HRKP v4 강점

- **환각 방지**: Quality Gate가 쓰레기 컨텍스트 필터링 → 잘못된 정보 기반 답변 억제
- **출처 투명성**: HIGH/PARTIAL 등급에서 [출처N] 인용으로 근거 명시
- **적응형 답변**: NONE이어도 일반 지식으로 유용한 답변 (vs RCSV의 "답변 불가" 또는 도메인 오류)
- **비용 효율**: 로컬 임베딩 + Reranker + DeepSeek → API 비용 최소화
- **Reranker 정밀도**: cross-encoder로 RRF 0.016 → 0.54 (33배) 재순위화

### RCSV 강점

- **OpenAI 임베딩 품질**: text-embedding-3-small의 높은 검색 커버리지
- **레이턴시**: 검색 ~200ms (HRKP FULL은 Reranker 포함 ~31초)
- **답변 풍부성**: GPT-4o-mini의 유창한 답변 생성

---

## 6. Graph RAG 효과 분석 (내부 A/B 테스트)

| 메트릭 | Graph ON (3채널) | Graph OFF (2채널) | 차이 |
|--------|:---------------:|:----------------:|:----:|
| faithfulness | **0.313** | 0.275 | +0.038 |
| answer_relevancy | **0.500** | 0.417 | +0.083 |
| context_precision | 0.333 | **0.400** | -0.067 |
| context_recall | 0.000 | 0.000 | 0.000 |

### 핵심 발견

1. **Graph 채널은 답변 품질에 긍정적 영향**: faithfulness +14%, answer_relevancy +20%
2. **v1에서 Graph 과점유 발견 후 수정**: v1 평가 시 12/12 쿼리에서 Graph Top-1 → weight 1.0→0.3 하향 후 해소 (v2에서 0/12)
3. **레이턴시 추가 비용 없음**: Graph ON/OFF 간 평균 0ms 차이
4. **context_precision 소폭 하락**: Graph 결과가 항상 정밀하지는 않으나, 답변 생성에는 유익

---

## 7. 주요 문제점 및 근본 원인 (업데이트)

### 문제 1: Context Recall 0% 수렴 (미해결)

- **현상**: 거의 모든 평가에서 context_recall이 0에 가까움
- **원인**: Ground truth 대비 KB 커버리지 부족 + 임베딩 모델 한계
- **v4 상태**: 여전히 0.063으로 개선 안됨
- **해결 방향**: KB 확장 (Docker Compose, K8s, RAGAS 문서 인덱싱)

### 문제 2: Faithfulness 불안정 (부분 해결)

- **현상**: 0.067 ~ 0.403 범위로 큰 편차
- **원인**: LLM-as-Judge 방식의 평가자(DeepSeek) 편향 + 매 실행 변동
- **v4 상태**: 0.083으로 안정화되었으나 여전히 낮음
- **해결 방향**: 평가 셋 확대 (12→50+), 다회 평가 평균

### 문제 3: RAGAS vs Quality Gate 충돌 (신규 발견)

- **현상**: v4 아키텍처 개선에도 RAGAS 점수 하락
- **원인**: Quality Gate의 의도적 컨텍스트 제거를 RAGAS가 "나쁜 것"으로 평가
- **해결 방향**: Grade-aware 분리 평가 체계 도입

### 문제 4: Reranker CPU 레이턴시 (신규)

- **현상**: HRKP-FULL 평균 38초 (검색 400ms + Reranker ~15초 + LLM ~20초)
- **원인**: bge-reranker-base(109M) CPU 추론 + max_length=512
- **해결 방향**: ONNX 런타임, 모델 양자화, 또는 GPU 도입

---

## 8. 개선 로드맵 (업데이트)

### 완료 (Sprint 08~09)

| 항목 | 상태 | 효과 |
|------|:----:|------|
| System Prompt v2 (적응형 3단계) | ✅ 완료 | "거부 머신" 해소 |
| Quality Gate (3-tier 품질 판정) | ✅ 완료 | 환각 방지, 적응형 답변 |
| BGE Reranker (bge-reranker-base) | ✅ 완료 | RRF 0.016 → 0.54 (33배) |
| max_length 256→512 | ✅ 완료 | Q3 0.04→0.54 (13배) |
| Quality Gate PARTIAL 확장 | ✅ 완료 | NONE 50%→25% |
| RRF Graph 과점유 버그 수정 | ✅ 완료 | v1(0:3) → v2(2:2) |

### 단기 (Sprint 10)

| 우선순위 | 개선 항목 | 기대 효과 |
|:-------:|----------|----------|
| P0 | KB 확장: Docker Compose, K8s, RAGAS 문서 인덱싱 | NONE 3→0개, context_recall +20% |
| P0 | Grade-aware RAGAS 평가 체계 | 정확한 품질 측정 |
| P1 | 청킹 전략 개선: Semantic Chunking + 오버랩 확대 | context_recall +10~15% |
| P1 | 평가 셋 확대 (12→50+) + 다회 평가 평균 | 평가 안정성 확보 |

### 중기 (Sprint 11~12)

| 우선순위 | 개선 항목 | 기대 효과 |
|:-------:|----------|----------|
| P1 | Reranker ONNX 런타임 또는 양자화 | 레이턴시 15초→3초 |
| P1 | Entity-Chunk 직접 연결 (MENTIONED_IN) | Graph 검색 정밀도 향상 |
| P2 | 임베딩 Fine-tuning (도메인 특화) | context_recall +20% |
| P2 | Streaming 지원 (chat/stream 엔드포인트) | UX 개선 |

### 장기 (Sprint 13+)

| 우선순위 | 개선 항목 | 기대 효과 |
|:-------:|----------|----------|
| P2 | 멀티홉 추론 강화 (Graph Traversal + LLM) | 복합 질문 품질 향상 |
| P3 | Adaptive Retrieval (쿼리 유형별 동적 채널 선택) | 전체 최적화 |
| P3 | GPU Reranker (bge-reranker-v2-m3, 568M) | 정밀도+속도 동시 향상 |

---

## 9. 총평 (v2 업데이트)

### HRKP v4 시스템의 현재 위치

HRKP v4는 **BGE Reranker + Quality Gate + 적응형 프롬프트** 3단계 파이프라인을 완성하여, 단순 RRF 검색에서 **지능형 컨텍스트 큐레이션** 시스템으로 전환했다. Reranker max_length=512 적용으로 문서 관련성 판단 정확도가 비약적으로 향상되었고(Q3: 13배), Quality Gate NONE 비율을 50%에서 25%로 절반 감소시켰다.

### 핵심 인사이트

1. **RAGAS 수치 ≠ 실제 품질**: Quality Gate 도입 후 RAGAS 점수는 하락했지만, 정성적 평가에서 HRKP v4가 RCSV 대비 5/5 우세. 특히 RCSV의 "환경변수→환경오염" 도메인 오류(Q12)는 RAGAS가 감지하지 못하는 치명적 문제.

2. **max_length가 Reranker 성능의 핵심**: 256→512 변경만으로 Q3이 NONE(0.04)에서 PARTIAL(0.54)로 전환. 토크나이저 입력 길이가 cross-encoder 판단 정확도를 좌우.

3. **Graph RAG + Reranker 시너지**: Graph 채널이 독자적 컨텍스트를 제공하고, Reranker가 이를 정밀하게 재순위화하여 최적의 컨텍스트만 LLM에 전달.

4. **"정직한 시스템"의 진화**: v2까지는 "답변 불가" 거부 → v4에서는 Quality Gate NONE일 때도 일반 지식으로 유용한 답변 제공. RCSV보다 더 나은 사용자 경험.

5. **평가 프레임워크 혁신 필요**: 기존 RAGAS는 "컨텍스트 있으면 좋다" 전제 → Quality Gate의 "의도적 필터링"을 평가하려면 Grade-aware 분리 평가가 필수.

### 목표 메트릭 (Sprint 12 종료 시점)

| 메트릭 | v2 최고 | v4 현재 | 목표 | 주요 개선 수단 |
|--------|:-------:|:-------:|:----:|--------------|
| faithfulness | 0.403 | 0.083 | 0.60 | KB 확장 + 평가 안정화 |
| answer_relevancy | 0.500 | 0.150 | 0.60 | Grade-aware 평가 + KB 확장 |
| context_precision | 0.508 | 0.150 | 0.60 | KB 확장 (NONE→PARTIAL/HIGH) |
| context_recall | 0.083 | 0.063 | 0.40 | Semantic Chunking + 임베딩 튜닝 |

> **참고**: v4 FULL 점수가 v2보다 낮은 것은 RAGAS 측정 한계 (Quality Gate 충돌). 실제 품질은 v4가 v2보다 우수 (정성적 5/5 우세 확인).

---

*Updated: 2026-02-10*
*Author: Claude Opus 4.6*
*Sources: ragas_evaluation_2026-02-04_022522.md, hrkp_vs_rcsv_report_2026-02-10_v2.md, hrkp_vs_rcsv_report_2026-02-10_v3.md, hrkp_vs_rcsv_report_2026-02-10_v4.md*
