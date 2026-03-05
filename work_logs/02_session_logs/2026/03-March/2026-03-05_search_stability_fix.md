# Session Log - 2026-03-05 검색 시스템 안정성 긴급 개선

**시간**: 2026-03-05
**모델**: Claude Opus 4.6
**이전 커밋**: `e8f76d1`

---

## 작업 요약

### 배경

2026-03-04 시연에서 AI Service가 ES/Neo4j보다 먼저 기동되어 검색 클라이언트가 `None`으로 초기화 → 모든 검색 0건 반환. Health 엔드포인트는 정상으로 표시되어 문제 발견 불가.

### 근본 원인 (6가지)

1. `main.py` lifespan에서 연결 1회만 시도 → 실패 시 영구 None **(Critical)**
2. ES healthcheck `start_period` 부족 → 조기 healthy 판정
3. Neo4j healthcheck가 HTTP(7474)만 확인 → Bolt(7687) 미검증
4. SearchService에 lazy reconnection 없음 → None이면 영구 빈 결과 **(Critical)**
5. `/health/ready`가 새 연결로 테스트 → SearchService 실제 상태 미반영
6. STORY-114(init-db depends_on)는 이미 적용됨 (정보용)

---

## 구현 내역 (3 Phase, 6개 조치)

### Phase A: 즉시 조치 (P0) — 시연 재발 방지

| 조치 | 파일 | 변경 |
|------|------|------|
| A-1 | `knowledge_service/src/app/main.py` | `_connect_with_retry()` 지수 백오프 함수 추가 (5회, 3s→6s→12s→24s→48s = 총 93초) |
| A-2 | `infrastructure/docker/docker-compose.yml` | ES healthcheck `start_period: 60s` → `90s` |
| A-3 | `infrastructure/docker/docker-compose.yml` | Neo4j healthcheck `wget http://7474` → `cypher-shell 'RETURN 1'` (Bolt 검증) |

### Phase B: 단기 개선 (P1) — 자동 복구

| 조치 | 파일 | 변경 |
|------|------|------|
| B-1 | `knowledge_service/src/app/services/search.py` | `_ensure_es_client()` / `_ensure_neo4j_driver()` lazy reconnection 구현. 검색 실패 시 client=None 초기화 → 다음 호출 시 재연결 유도 |
| B-2 | `knowledge_service/src/app/api/routes/health.py` | `_check_search_service_clients()` 추가 → readiness에 `search_service_es` / `search_service_neo4j` 체크 반영 |

### Phase C: 중기 안정화 (P2) — 모니터링

| 조치 | 파일 | 변경 |
|------|------|------|
| C-1 | `knowledge_service/src/app/services/search.py` | `hybrid_search` 0건 + client=None 조합 시 `[SEARCH_ALERT]` WARNING 로그 |

### 방어 계층 (Defense in Depth)

```
Layer 1: Docker healthcheck (start_period 90s + cypher-shell Bolt 검증)
Layer 2: main.py 지수 백오프 (5회, 최대 93초 대기)
Layer 3: SearchService lazy reconnection (검색 시점에 재연결 시도)
Layer 4: [SEARCH_ALERT] WARNING 로그 + /health/ready=false 반환
```

---

## 문서 산출물

| 문서 | 경로 |
|------|------|
| 사고 보고서 + 개선 계획서 | `knowledge_service/docs/07_maintenance/33_incident_report_2026-03-04_search_zero_results.md` |

- 사고 개요, 근본 원인 분석 (Mermaid 시퀀스 다이어그램 포함)
- 조치 결과 요약 + 코드 변경 diff
- 9개 테스트 시나리오 + 통합 테스트 스크립트

---

## 수정 파일 목록

| 파일 | 유형 | 핵심 변경 |
|------|------|----------|
| `knowledge_service/src/app/main.py` | 코드 | 지수 백오프 retry (asyncio.sleep) |
| `infrastructure/docker/docker-compose.yml` | 인프라 | ES/Neo4j healthcheck 강화 |
| `knowledge_service/src/app/services/search.py` | 코드 | lazy reconnection + 0건 경고 |
| `knowledge_service/src/app/api/routes/health.py` | 코드 | SearchService 상태 readiness 반영 |
| `knowledge_service/docs/07_maintenance/33_*.md` | 문서 | 사고 보고서 + 테스트 계획 |

---

## 교훈

```
"Health 엔드포인트가 정상이라고 실제 서비스가 정상인 것은 아니다."
"단 1회 연결 시도로 영구 장애가 발생할 수 있다."
"Readiness Probe는 실제 서비스 객체의 상태를 반영해야 한다."
```

## 추가 SP

총 8 SP 소요 (A: 3SP, B: 4SP, C: 1SP)
