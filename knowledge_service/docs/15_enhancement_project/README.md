# 고도화 프로젝트 문서 관리

**시작일**: 2026-03-04
**기간**: Sprint 09~ (2주 단위)
**목표**: Graph RAG 데이터 구축 + 데이터 정합성 + 검색 품질 향상 + Observability 완성

---

## 폴더 구조

```
knowledge_service/docs/15_enhancement_project/
├── README.md                  ← 이 파일 (인덱스)
├── 01_계획/                   ← 고도화 계획, 전략 문서
├── 02_사고보고/               ← 사고 보고서, 인시던트 리포트
├── 03_개선결과/               ← 개선 조치 결과, 테스트 보고
└── 04_스프린트/               ← 스프린트별 산출물
```

---

## 문서 인덱스

### 01_계획

| 문서 | 설명 | 원본 위치 |
|------|------|----------|
| [Sprint 09 계획서](../../../backlog/sprints/sprint-09.md) | 38 SP, 13 Stories, P0~P2 | `backlog/sprints/` |
| [프로젝트 전체 계획](../../../PLAN.md) | 현재 Phase: ENHANCEMENT | 프로젝트 루트 |

### 02_사고보고

| 문서 | 설명 | 원본 위치 |
|------|------|----------|
| [검색 0건 사고 보고서](./02_사고보고/01_검색시스템_안정성_개선.md) | 2026-03-04 시연 장애, 6개 근본 원인, 4계층 방어 | 이 폴더 |

### 03_개선결과

| 문서 | 설명 |
|------|------|
| *(Sprint 09 진행 중 — 완료 시 추가)* | |

### 04_스프린트

| 문서 | 설명 |
|------|------|
| *(Sprint 09 완료 후 회고/결과 추가)* | |

---

## 관련 스토리 (STORY-112 ~ 127)

### P0 - Critical (11 SP)

| ID | 제목 | SP | 담당 |
|----|------|:--:|------|
| STORY-112 | Phase 3 엔티티 추출 배치 (96K 청크) | 3 | ETL/RAG |
| STORY-089 | PG-AI Service 문서 동기화 | 5 | ETL/Backend |
| STORY-113 | Nori 플러그인 자동 검증 | 2 | QA |
| STORY-114 | Init-DB depends_on 전면 적용 | 1 | Infra |

### P1 - High (25 SP)

| ID | 제목 | SP | 담당 |
|----|------|:--:|------|
| STORY-115 | bge-reranker-v2-m3 ONNX 업그레이드 | 3 | RAG |
| STORY-116 | ES 메모리 증설 (512MB→1GB) | 1 | Infra |
| STORY-117 | Prometheus Exporter 활성화 | 2 | DevOps |
| STORY-096 | Backend 비즈니스 로직 (검색/업로드/대시보드) | 5 | Backend |
| STORY-118 | RAGAS CI 통합 (PR 자동 평가) | 3 | QA |
| STORY-119 | RAGAS Context Precision 개선 | 3 | RAG |
| STORY-120 | 전체 PG 동기화 일괄 실행 | 3 | ETL |
| STORY-088 | entity_extraction.py MERGE 버그 수정 | 2 | RAG |
| STORY-121 | Embedding Batch CLI (auto-resume, progress) | 3 | ETL |

### P2 - Medium (28 SP)

| ID | 제목 | SP | 담당 |
|----|------|:--:|------|
| STORY-122 | 동적 검색 전략 선택 | 5 | RAG |
| STORY-123 | Alertmanager 채널 분기 | 3 | DevOps |
| STORY-124 | Neo4j 스키마 통합 (v1.0/v2.6) | 5 | DB |
| STORY-125 | ETL CLI 통합 (7개 스크립트→etl_cli.py) | 5 | ETL |
| STORY-126 | ETL Grafana 대시보드 | 3 | DevOps |
| STORY-127 | Gateway 구조 개선 (65점→75+) | 5 | Backend |
| TD-004 | RAGAS 평가셋 100+ 확대 | 2 | QA |

---

## 관련 원본 문서 위치 참조

| 카테고리 | 경로 | 비고 |
|---------|------|------|
| 스프린트 계획 | `backlog/sprints/sprint-09.md` | 링크 참조 |
| 스토리 상세 | `backlog/stories/STORY-112~127` | 개별 스토리 |
| 운영/사고 보고 | `knowledge_service/docs/07_maintenance/` | 33번 사고 보고서 |
| 일일 작업일지 | `work_logs/01_daily_logs/2026/03-March/` | 날짜별 |
| 세션 로그 | `work_logs/02_session_logs/2026/03-March/` | 세션별 |
| 스탠드업 | `work_logs/03_standups/2026/03-March/` | 킥오프 포함 |
