# STORY-100: ES 벡터 후속 임베딩 배치 스크립트 (10,094 chunks)

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-93 |
| **Epic** | - |
| **Status** | In Progress |
| **Priority** | P0 - Critical |
| **Story Points** | 5 |
| **Assignee** | MLRag/Data |
| **Sprint** | 08 |
| **Origin** | 아이디어 검토 (2026-02-09) |

---

## User Story

**As a** 검색 사용자,
**I want** 모든 문서 chunk에 벡터 임베딩이 생성되어,
**So that** 벡터 기반 시맨틱 검색으로 더 정확한 결과를 받을 수 있다.

---

## Acceptance Criteria

- [ ] **Given** ES에 벡터 없는 10,094 chunks가 있을 때, **When** 배치 스크립트를 실행하면, **Then** 모든 chunks에 BGE-M3 1024d 임베딩이 추가된다
- [ ] **Given** 배치 실행 중 OOM/중단이 발생했을 때, **When** 스크립트를 재실행하면, **Then** 체크포인트부터 이어서 처리한다
- [ ] **Given** 배치가 완료되면, **When** 벡터 검색을 실행하면, **Then** 10,094 chunks가 벡터 검색 결과에 포함된다

---

## Tasks

- [ ] ES scroll API로 vector_embedding=null인 chunks 조회 모듈
- [ ] BGE-M3 batch inference (chunk_size=32) 처리
- [ ] ES bulk update로 벡터 필드 추가
- [ ] 진행률 로깅 + 체크포인트 재시작 기능
- [ ] 메모리 프로파일링 (~4GB peak 검증)
- [ ] 완료 검증 쿼리

---

## 기술 노트

### 구현 방향
- ES에서 텍스트를 읽어 BGE-M3 임베딩만 추가하는 lightweight 스크립트
- 파싱/청킹 단계 건너뛰기 → 메모리 ~4GB peak 예상
- 별도 Python 스크립트 (add_embeddings_batch.py)

### 평가
- **실현 가능성**: High (기존 파이프라인 코드 재활용)
- **ROI**: 매우 높음 (벡터 검색 활성화 → 검색 품질 대폭 개선)
- **리스크**: WSL 메모리 부족 시 OOM (11GB 할당 시 충분)

### 영향 범위
- `knowledge_service/src/app/services/` 또는 별도 스크립트
- Elasticsearch 인덱스 업데이트

---

## 테스트 계획

- [ ] Unit Test: ES 조회/업데이트 모듈
- [ ] Integration Test: BGE-M3 임베딩 생성 + ES 저장
- [ ] E2E Test: 배치 완료 후 벡터 검색 동작 확인

---

## 참고 자료

- [스탠드업 2026-02-09](../../work_logs/standups/2026/02-February/2026-02-09_11-05.md)
- [운영매뉴얼 v2.0](../../knowledge_service/docs/07_maintenance/)
