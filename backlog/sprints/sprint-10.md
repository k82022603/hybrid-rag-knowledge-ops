# Sprint 10: 검색 UX 고도화 + 성능 최적화 + 기술부채 해소

## Sprint Information

| Item | Value |
|------|-------|
| **Duration** | 2026-03-07 ~ 2026-03-20 (2 weeks) |
| **Velocity (Planned)** | 24 pts (6 Stories) |
| **Velocity (Actual)** | - |
| **Status** | planning |
| **Jira Sprint ID** | SCRUM-122 ~ SCRUM-127 |
| **Objective** | 검색 결과 UX 개선 + Graph RAG 품질 평가 + 성능 최적화 + 기술부채 해소 |

---

## Sprint Goals

> **검색 품질 가시화 + Graph RAG 검증 + 프로덕션 안정성 강화**

Key Objectives:
1. RRF 하이라이팅 + 소스별 점수로 검색 결과 투명성 확보
2. Graph RAG A/B 비교 평가로 4-Way 검색의 실효성 검증
3. k6 성능 회귀 테스트로 P95 < 3s 자동 검증 체계 구축
4. initial_data_loader.py 1,582줄 분리로 기술부채 해소
5. Adaptive Gleaning으로 RAG 품질 동적 최적화

---

## Backlog

### P0 - Critical (Week 1)

| Priority | ID | Title | Points | Assignee | Status | Depends On |
|----------|-----|-------|--------|----------|--------|------------|
| P0 | STORY-096 | RRF 하이라이팅 + 소스별 점수 메타데이터 (hybrid_search 경로) | 5 | RAG/Backend/Frontend | To Do | Sprint 09 Deferred |
| P0 | STORY-097 | Graph RAG A/B 비교 평가 (4-Way vs 3-Way) | 5 | QA/RAG | To Do | Phase 3 완료 |

**P0 소계**: 2건, 10 SP

### P1 - High (Week 1~2)

| Priority | ID | Title | Points | Assignee | Status | Depends On |
|----------|-----|-------|--------|----------|--------|------------|
| P1 | STORY-129 | k6 성능 회귀 테스트 (P95 < 3s 자동 검증) | 3 | QA/DevOps | To Do | - |
| P1 | STORY-128 | initial_data_loader.py 분리 (1,582줄 -> 모듈화) | 5 | ETL/TechLead | To Do | - |

**P1 소계**: 2건, 8 SP

### P2 - Medium (Week 2)

| Priority | ID | Title | Points | Assignee | Status | Depends On |
|----------|-----|-------|--------|----------|--------|------------|
| P2 | STORY-130 | Adaptive Gleaning 동적 횟수 조절 | 3 | RAG | To Do | - |
| P2 | STORY-090 | 쿼리 임베딩 캐싱 + BGE-M3 비동기 처리 확인 | 3 | RAG/Backend | To Do | Sprint 09 Deferred (GPU 필요) |

**P2 소계**: 2건, 6 SP

### P3 - Low (Sprint 11 이후)

| Priority | ID | Title | Points | Assignee | Status |
|----------|-----|-------|--------|----------|--------|
| P3 | STORY-NEW | Tool Search 기반 동적 검색 전략 메타 레이어 | 5 | RAG/TechLead | Deferred |
| P3 | STORY-NEW | AI-assisted E2E Testing 파일럿 | 5 | QA/Frontend | Deferred |
| P3 | STORY-NEW | 컨텍스트 압축 레이어 (토큰 -25%) | 5 | RAG | Deferred |
| P3 | STORY-NEW | DORA 메트릭 대시보드 | 3 | DevOps | Deferred |
| P3 | STORY-NEW | HWP 파싱 개선 | 3 | ETL | Deferred |
| P3 | STORY-NEW | Frontend MUI -> Tailwind 완전 전환 | 8 | Frontend | Deferred |
| P3 | STORY-NEW | GPU 임베딩 통합 (65.6 vs 0.7 c/s) | 8 | Infra/RAG | Deferred |
| P3 | STORY-NEW | PG 파티셔닝 (audit_logs, search_history) | 3 | DB | Deferred |
| P3 | STORY-NEW | Semantic Chunker v2 (임베딩 기반 청킹) | 5 | ETL | Deferred |

---

## Sprint 09 -> 10 이관 사항

### Deferred Stories (2건)
1. **STORY-096** (5 SP): RRF 하이라이팅 - 멀티컴포넌트 작업, 별도 세션 필요
2. **STORY-090** (3 SP): 쿼리 임베딩 캐싱 - GPU 환경 필요

### GPT-5.4 인사이트 반영 (중기 로드맵)
- Tool Search 기반 동적 검색 전략 -> Sprint 11~12 파일럿
- AI-assisted E2E Testing -> Sprint 12~13 검토

---

## Daily Plan

### Week 1 (2026-03-07 ~ 2026-03-13)

| Day | 주요 작업 | 담당 |
|-----|----------|------|
| Day 1 (금) | Sprint 10 킥오프, STORY-096 착수 | PM, RAG, Backend |
| Day 2~3 | STORY-096 구현 (RAG+Backend+Frontend) | RAG, Backend, Frontend |
| Day 4 | STORY-097 Graph RAG A/B 평가 착수 | QA, RAG |
| Day 5 | STORY-129 k6 성능 테스트 구현 | QA, DevOps |

### Week 2 (2026-03-14 ~ 2026-03-20)

| Day | 주요 작업 | 담당 |
|-----|----------|------|
| Day 6~7 | STORY-128 initial_data_loader 분리 | ETL, TechLead |
| Day 8 | STORY-130 Adaptive Gleaning | RAG |
| Day 9 | STORY-090 임베딩 캐싱 (GPU 가용시) | RAG, Backend |
| Day 10 | QA 테스트 + Sprint 10 마감 | QA, PM |

---

*Created: 2026-03-06*
*PM: Claude Code (Opus 4.6)*
