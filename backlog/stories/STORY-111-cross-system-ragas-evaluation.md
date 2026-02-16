# STORY-111: HRKP vs RAGChatbotServer 크로스 시스템 RAGAS 비교 평가

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-99 |
| **Epic** | EPIC-005 |
| **Status** | ready |
| **Priority** | High |
| **Story Points** | 8 |
| **Assignee** | MLRag |
| **Sprint** | 08 |
| **Origin** | RAGChatbotServer 분석 (2026-02-10) |

---

## User Story

**As a** 기술 리더,
**I want** HRKP와 RAGChatbotServer를 동일한 RAGAS 메트릭으로 비교 평가하여,
**So that** 두 시스템의 RAG 품질 차이를 객관적으로 파악하고 개선 방향을 수립할 수 있다.

---

## Acceptance Criteria

- [ ] **Given** 동일한 테스트 데이터셋(최소 24개 QA)이 준비되면, **When** 양쪽 시스템에서 평가를 실행하면, **Then** 4가지 RAGAS 메트릭(Faithfulness, Answer Relevancy, Context Precision, Context Recall)이 모두 측정된다
- [ ] **Given** 비교 평가가 완료되면, **When** 리포트를 확인하면, **Then** 메트릭별 점수, Latency, 비용 비교표가 포함되어 있다
- [ ] **Given** CrossSystemAdapter가 구현되면, **When** RAGChatbotServer에서 query()를 호출하면, **Then** contexts(검색 원문 텍스트)가 정상 추출된다
- [ ] **Given** 평가 결과가 생성되면, **When** 동일 포맷의 Markdown 리포트로 출력되면, **Then** 기존 HRKP 리포트와 비교 가능한 형식이다

---

## Tasks

### Phase 1: 환경 준비

- [ ] RAGChatbotServer Docker Compose 기동 확인 (PGVector 모드)
- [ ] PGVectorRAG 이중 __init__ 버그 패치 (평가 전 필수)
- [ ] 테스트 문서 세트 선정 (5~10개 PDF)
- [ ] 양쪽 시스템에 동일 문서 적재

### Phase 2: 어댑터 구현

- [ ] `CrossSystemAdapter` 클래스 구현 (`knowledge_service/src/app/evaluation/cross_system_adapter.py`)
- [ ] RAGChatbotServer `query()` → `EvaluationSample` 변환 검증
- [ ] contexts 추출 확인 (`sources[i].page_content`)
- [ ] 단위 테스트 작성

### Phase 3: 평가 실행

- [ ] HRKP Live 평가 실행 (LiveRagasEvaluator)
- [ ] RAGChatbotServer 평가 실행 (CrossSystemAdapter)
- [ ] 개별 리포트 생성 (Markdown + JSON)

### Phase 4: 비교 분석

- [ ] 메트릭별 비교표 생성
- [ ] Latency 비교 (P50/P95/P99)
- [ ] 비용 분석 (로컬 CPU vs OpenAI API)
- [ ] 종합 비교 리포트 작성
- [ ] TechLead 리뷰

---

## 기술 노트

### 구현 방향

- HRKP의 기존 `RagasEvaluator` (범용 엔진)를 그대로 활용
- `LiveRagasEvaluator`는 HRKP 전용 → RAGChatbotServer용 `CrossSystemAdapter` 신규 작성
- RAGChatbotServer API (`/ai/chat`)는 contexts 미반환 → `rag_system.py`의 `query()` 직접 호출로 우회
- `query()` 반환값의 `sources[i].page_content`에서 contexts 추출

### 핵심 블로커 해결

| 블로커 | 해결 방법 |
|--------|----------|
| API contexts 미반환 | `SearchRAG.query()` 직접 호출 (방안 B) |
| PGVectorRAG 버그 | `__init__` 이중 초기화 패치 |
| LLM/임베딩 모델 차이 | 동일 메트릭으로 객관 비교 (공정성 주석) |

### 영향 범위

**신규 파일:**
- `knowledge_service/src/app/evaluation/cross_system_adapter.py` - 외부 시스템 어댑터
- `knowledge_service/scripts/run_cross_eval.py` - 비교 평가 실행 스크립트

**수정 파일:**
- 없음 (기존 코드 수정 없이 어댑터 패턴으로 확장)

---

## 테스트 계획

- [ ] Unit Test: CrossSystemAdapter 단위 테스트 (query → sample 변환)
- [ ] Integration Test: RAGChatbotServer 실제 호출 + 평가
- [ ] Comparison Test: 양쪽 결과 포맷 일치 확인

---

## 선행 조건

- [x] RAGChatbotServer 코드 분석 완료 (2026-02-10)
- [x] RAGAS 호환성 분석 문서 작성 (`ragas_cross_system_evaluation_guide.md`)
- [ ] RAGChatbotServer Docker 환경 정상 기동
- [ ] 임베딩 배치 완료 (HRKP 측, 현재 ~69% 진행 중)

---

## 참고 자료

- [RAGAS 크로스 시스템 평가 가이드](../../knowledge_service/docs/04_testing/11_ragas/04_ragas_cross_system_evaluation_guide.md)
- [RAGAS 평가 파이프라인 가이드](../../knowledge_service/docs/05_development/08_ragas_evaluation_guide.md)
- [STORY-105: RAGAS 평가 기준 문서 확정](./STORY-105-ragas-evaluation-criteria.md)
- [RAGChatbotServer README](../../RAGChatbotServer/README.md)
- [EPIC-005: RAG Quality & Performance](../epics/EPIC-005-rag-quality-performance.md)
