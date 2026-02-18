# STORY-097: Graph RAG 효과성 A/B 비교 평가

## Story Information

| Item | Value |
|------|-------|
| **ID** | STORY-097 |
| **Type** | TEST |
| **Priority** | Medium (P2) |
| **Story Points** | 5 |
| **Sprint** | Backlog (충분한 데이터 임베딩 후) |
| **Status** | Deferred (Sprint 12 project closure) |
| **Jira ID** | - |
| **Created** | 2026-02-08 |
| **Primary** | QA |
| **Secondary** | RAG |

---

## Summary

기존 BM25 + Vector 검색 대비 Graph RAG 추가의 실질적 효과를 정량적으로 검증한다. 충분한 문서 임베딩 및 NER 엔티티 추출 완료 후 실시한다.

---

## Background

### 현재 상태
- Graph Search 기능 구현 완료 (3단계 매칭 + RRF Fusion)
- **그러나 A/B 비교 데이터 없음** → "향상되었다"는 주장 불가
- Knowledge Graph 엔티티 커버리지 16% (61개 엔티티 / 42개 청크 중 7개 커버)

### 전제 조건 (이 스토리 착수 전 완료 필요)
- [ ] 충분한 문서 임베딩 완료 (최소 100개 문서, 500+ 청크)
- [ ] NER 파이프라인 적용으로 엔티티 커버리지 60% 이상 확보
- [ ] UI 기능 개선 완료 (STORY-092~096)

### 분석 보고서
- [Graph RAG 효과성 분석 보고서](../../knowledge_service/docs/04_testing/11_ragas/03_graph_rag_effectiveness_analysis.md)

---

## Acceptance Criteria

### 실험 1: A/B 비교 테스트
- [ ] 테스트 쿼리셋 30개 이상 구성 (사실 조회 10, 관계 추론 10, Multi-hop 10)
- [ ] `use_graph=false` (Vector + Keyword only) 결과 RAGAS 평가
- [ ] `use_graph=true` (Vector + Keyword + Graph) 결과 RAGAS 평가
- [ ] 쿼리 유형별 차이 분석 (Faithfulness, Answer Relevancy, Context Precision)
- [ ] TEST_MODE=docker 환경에서 실시

### 실험 2: Graph-only 청크 기여도
- [ ] Graph에만 있고 Vector/Keyword에 없는 고유 청크 비율 측정
- [ ] 해당 Graph-only 청크가 정답에 기여하는지 확인

### 실험 3: 쿼리 유형별 소스 기여도
- [ ] 최종 top-5 결과에서 source_ranks 분석
- [ ] Graph가 primary source인 비율 측정
- [ ] 쿼리 유형별 최적 소스 조합 도출

### 결과 보고
- [ ] 정량 비교표 작성 (Graph ON/OFF 차이)
- [ ] 쿼리 유형별 Graph 효과 분석
- [ ] 프로젝트 보고용 권장 표현 도출
- [ ] 기존 분석 보고서 업데이트

---

## Testing

- 환경: TEST_MODE=docker (실 Docker 컨테이너)
- 평가 프레임워크: RAGAS
- 쿼리셋: 수동 구성 + 자동 생성 혼합
- 통계 검증: 쿼리 유형별 평균 차이, 표준편차

---

## Dependencies

- 충분한 문서 임베딩 (100+ 문서)
- NER 엔티티 추출 (커버리지 60%+)
- STORY-094 (문서 제목 추출 개선)

---

## References

- [Graph RAG 효과성 분석 보고서](../../knowledge_service/docs/04_testing/11_ragas/03_graph_rag_effectiveness_analysis.md)
- Microsoft GraphRAG Paper (2024)
- Cormack et al., "Reciprocal Rank Fusion" (2009)
