# STORY-125: ETL CLI 통합 (7개 스크립트 → etl_cli.py)

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | - |
| **Epic** | ETL 안정화 |
| **Status** | To Do |
| **Priority** | P2 |
| **Story Points** | 5 |
| **Assignee** | ETL |
| **Sprint** | Sprint 09 |

---

## 배경

ETL Engineer 발견: 현재 스크립트 7개가 산재 (TD-003 기술 부채).

| 스크립트 | 역할 |
|---------|------|
| `run_etl_phase1.sh` | Phase 1 실행 |
| `run_etl_phase2.sh` | Phase 2 실행 |
| `run_etl_phase3.sh` | Phase 3 실행 |
| `cleanup_orphan_nodes.py` | 고아 노드 정리 |
| `embedding_monitor.sh` | 임베딩 모니터 |
| `etl_phase1_monitor.sh` | Phase 1 모니터 |
| `etl_v2_monitor.sh` | 전체 ETL 모니터 |

개별 스크립트 실행 시 순서 실수, 파라미터 누락 등 인적 오류 발생 가능.

---

## User Story

**As a** ETL 운영자,
**I want** 단일 CLI 명령어로 ETL 파이프라인의 모든 단계를 제어하기를,
**So that** 인적 오류 없이 일관된 방식으로 ETL을 실행할 수 있다.

---

## Acceptance Criteria

- [ ] `etl_cli.py` 단일 진입점 (Click 기반 CLI)
- [ ] 서브커맨드: `phase1`, `phase2`, `phase3`, `all`, `status`, `cleanup`
- [ ] 실행 전 전제조건 체크 (Docker 상태, DB 연결)
- [ ] 진행률 표시 (tqdm 또는 rich.progress)
- [ ] 로그 통합 (`/tmp/etl_cli_{phase}_{timestamp}.log`)
- [ ] `--dry-run` 옵션 지원

---

## Tasks

- [ ] Click 기반 CLI 뼈대 구현 (`knowledge_service/scripts/etl_cli.py`)
- [ ] 기존 7개 스크립트 로직 CLI 서브커맨드로 통합
- [ ] 전제조건 체크 함수 구현 (DB ping, Docker 상태)
- [ ] `etl_cli.py all --phase 1 2 3` 순차 실행 지원
- [ ] 기존 스크립트 deprecated 주석 추가 (삭제는 Sprint 10)

---

## 기술 노트

### CLI 구조

```
etl_cli.py
├── phase1    # 파싱+청킹+저장 (ES/PG/Neo4j)
├── phase2    # GPU 임베딩 (Colab 가이드 포함)
├── phase3    # 엔티티 추출 → Neo4j
├── all       # phase1 → phase2 → phase3 순차
├── status    # 각 Phase 진행률 조회
└── cleanup   # 고아 노드 정리
```

### 영향 범위
- `knowledge_service/scripts/etl_cli.py` (신규)
- 기존 7개 스크립트는 deprecated 처리 (삭제 안 함)

---

## 의존성

- **선행**: STORY-112 (Phase 3 실행 후 전체 흐름 파악)
- **관련**: STORY-120 (ETL 재시도 로직 통합)
