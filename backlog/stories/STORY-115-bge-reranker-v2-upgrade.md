# STORY-115: bge-reranker-v2-m3 ONNX 업그레이드

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | - |
| **Epic** | 검색 품질 고도화 |
| **Status** | To Do |
| **Priority** | P1 |
| **Story Points** | 2 |
| **Assignee** | RAG |
| **Sprint** | Sprint 09 |

---

## User Story

**As a** 검색 사용자,
**I want** 더 정확한 reranking 결과를 얻기를,
**So that** 검색 결과의 관련성이 향상된다.

---

## Acceptance Criteria

- [ ] `BAAI/bge-reranker-base` → `BAAI/bge-reranker-v2-m3` 모델 교체
- [ ] ONNX Runtime 최적화 적용
- [ ] 교체 전후 RAGAS Precision 비교 측정
- [ ] 기존 검색 기능 회귀 없음

---

## Tasks

- [ ] `bge_reranker.py` 모델 ID 변경
- [ ] ONNX 변환 및 캐시 볼륨 마운트 확인
- [ ] Reranking 성능 벤치마크 (기존 base vs v2-m3)
- [ ] BGE-M3 캐시 볼륨과 통합 관리

---

## 기술 노트

### 구현 방향
- 모델 파일: `BAAI/bge-reranker-v2-m3`
- ONNX 런타임으로 CPU 추론 최적화
- 기존 볼륨 마운트 경로 재사용 (`bge-m3-cache:/root/.cache/huggingface`)

### 영향 범위
- `knowledge_service/src/app/rag/bge_reranker.py`

---

## 의존성

- **선행**: 없음
- **관련**: STORY-090 (검색 성능), STORY-118 (RAGAS 측정으로 효과 검증)
