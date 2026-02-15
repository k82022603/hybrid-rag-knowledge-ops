# Session Log - 2026-02-15

**Session ID**: 2026-02-15_entity_extraction_batch
**시작 시간**: 15:10 KST
**모델**: Claude Opus 4.6 (claude-opus-4-6)

---

## 세션 요약

Sprint 12 Phase 3 - 배치 엔티티 추출 실행. 인프라 최적화 + 듀얼 API 키 전략으로 3.1배 속도 향상 달성.

---

## 완료된 작업

### 1. Neo4j 메모리 증설 (인프라)

- **문제**: `docker-compose.override.yml`에서 Neo4j 메모리를 1GB로 제한 (본 설정 4GB)
- **결과**: 88.89% 메모리 사용 → OOM 위험 상태로 운영되고 있었음
- **조치**: override에서 1GB → 2GB, heap 512m → 1G, pagecache 256m → 512m
- **효과**: 메모리 사용 88.89% → 48% 안정화

### 2. 불필요 컨테이너 정리

- minio 컨테이너 중지 (엔티티 추출에 불필요)
- 호스트 CPU 97.7% 유휴 확인 → I/O bound 작업이라 CPU 무관

### 3. 동시 처리 수 최적화 (실측 기반)

| Concurrency | 속도 (chunks/min) | 비고 |
|:-----------:|:-----------------:|------|
| 5 | ~8.3 | 초기값 |
| 10 | ~14.3 | **최적값** |
| 20 | ~14.3 | 효과 없음 (API 키 제한) |

- **결론**: DeepSeek API가 per-key 동시 요청 제한 → concurrency=10이 단일 키 최적

### 4. 듀얼 API 키 전략 (핵심 성과)

- 사용자가 DeepSeek API 키 추가 생성
- 배치 스크립트에 파티셔닝 기능 추가 (`ENTITY_PARTITION` 환경변수)
- Worker 0 (키1): 짝수 인덱스 청크 / Worker 1 (키2): 홀수 인덱스 청크

**실측 결과:**
| 구성 | 속도 | ETA |
|------|------|-----|
| 1키 × 10 | 14.3/min | 18.6시간 |
| **2키 × 10** | **44.7/min** | **~5.9시간** |

- **3.1배 속도 향상** 달성
- DeepSeek API는 키 단위 제한 (IP 기반 아님) 확인

---

## 주요 결정사항

| 결정 | 내용 | 근거 |
|------|------|------|
| Neo4j 메모리 증설 | 1GB → 2GB | 88.89% 사용, OOM 위험 |
| concurrency=10 | 단일 키 최적값 | 5→10은 1.7x, 10→20은 0x 향상 |
| 2-key 전략 | 파티셔닝 + 별도 체크포인트 | 3.1x 속도 향상 실측 |

---

## 변경된 파일 목록

```
infrastructure/docker/
└── docker-compose.override.yml   # Neo4j 메모리 1GB→2GB 증설

knowledge_service/scripts/
└── batch_entity_extraction.py    # ENTITY_PARTITION 파티셔닝 기능 추가
```

---

## 현재 프로젝트 상태

### 배치 엔티티 추출 진행 현황 (15:48 KST)
| 항목 | 값 |
|------|------|
| 총 대상 | 16,185 chunks (tc>=100) |
| 처리 완료 | 447건 (2.8%) |
| 속도 | 44.7 chunks/min (2-worker) |
| ETA | ~5.9시간 (21:40 KST 예상) |
| 에러 | 8건 (0.05%) |

### 인프라 상태
| 컨테이너 | CPU | 메모리 |
|----------|-----|--------|
| kp-ai-service | 0.41% | 934MB/9GB |
| kp-neo4j | 0.79% | 1015MB/2GB |
| kp-elasticsearch | - | 1.54GB/2.5GB |
| kp-postgresql | - | 43MB/1GB |
| kp-redis | - | 167MB/1GB |

---

## 다음 작업 (Action Items)

### P0 (Critical)
1. 배치 완료 모니터링 (자동 - 백그라운드 진행)
2. 완료 후 Neo4j 엔티티/관계 통계 리포트

### P1 (High)
3. 장애보고서 작성: Neo4j override 메모리 제한 사고
4. ETL Phase 1 보고서 업데이트

---

## 세션 통계

| 항목 | 값 |
|------|------|
| 수정된 파일 | 2개 |
| 인프라 에이전트 분석 | 1회 |
| 실측 테스트 | 4회 (concurrency 5/10/20, 2-worker) |

---

*기록자: Claude Code (Opus 4.6)*
*기록 시간: 2026-02-15 15:48 KST*
