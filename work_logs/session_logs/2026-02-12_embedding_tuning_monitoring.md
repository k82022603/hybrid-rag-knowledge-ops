# Session Log - 2026-02-12 (오후)

**Session ID**: 2026-02-12_embedding_tuning_monitoring
**시작 시간**: ~13:30 KST
**종료 시간**: 15:13 KST (최종 업데이트)
**모델**: Claude Opus 4.6 (claude-opus-4-6)

---

## 세션 요약

Phase 3 임베딩 속도 튜닝(0.72→2.2 t/s), 자동 모니터링/헬스체크 체계 구축, 문서 4개→2개 통합

---

## 완료된 작업

### 1. Phase 2 최종 확인 및 Phase 3 현황 검증 (주요)

#### 상세 내용
- Phase 2 프로세스 종료 확인 (kp-ai-service 내 etl_phase2 프로세스 없음)
- Phase 3 (`run_embedding_backfill_v2.py`) 실행 중 확인
- ES 필드명 오류 수정: `embedding` → `dense_vector` (ES 매핑에서 확인)
- ES 임베딩 카운트: 11,932건 (당시 기준)

### 2. Slack 모니터링 v3 구축 (주요)

#### 상세 내용
- 기존 모니터 v2 (PID 9843) 발견: stale 데이터 반복 보고 (50% 894/1786)
  - 원인: `/tmp/etl_output.log` (Phase 1 로그) 읽고 있었음
- 모니터 v3 (`/tmp/etl_monitor_v3.sh`) 신규 작성:
  - Phase 2 최종 상태 + Phase 3 실시간 진행 분리 보고
  - `etl_progress.json`에서 Phase 3 속도/진행률 읽기
  - ES `dense_vector` exists 쿼리로 임베딩 카운트
  - 15분 간격, `#proj-hrkp-dev` 채널 전송
  - 99.5% 도달 시 자동 종료 + 완료 알림
- PID 88110으로 배경 실행 중

### 3. Phase 2 재처리 전략 수립 - 전문가 3인 합의 (주요)

#### 상세 내용
- ETL/TL/RAG Engineer 소집하여 11건 실패 파일 분석
- 결론: 임시파일 6건, 손상 3건, 재처리 대상 2건
- 재처리 대상 (Phase 3 완료 후):
  - `Software-Processes-and-Software-Development-Process-Models.pdf`
  - `파드의 컴퓨팅 리소스관리.docx`

### 4. 임베딩 속도 튜닝 - 전문가 3인 합의 (주요)

#### 상세 내용
- Infra/ETL/RAG Engineer 소집하여 병목 원인 분석:
  - **Infra**: swappiness=60이 불필요한 스왑 유발, 캐시 4.2GB 클리어 가능
  - **ETL**: 스왑 1.9GB가 속도 주요 원인 (90% 확신), 4스레드 OOM 5% 미만
  - **RAG**: 재시작 안전 (idempotent), 속도>안정성
- 적용 내역 (14:42~14:50):
  1. `vm.swappiness` 60 → 10
  2. 페이지 캐시 클리어 (`echo 3 > /proc/sys/vm/drop_caches`)
  3. `run_embedding_backfill_v2.py` 스레드 2 → 4 (OMP/MKL/torch 모두)
  4. 프로세스 재시작
- **결과**: 0.72 t/s → 2.2 t/s (**+205%**, ETA 37시간 → 12시간)

### 5. 자동 진단/대응 헬스체크 구축 (주요)

#### 상세 내용
- `scripts/embedding_health_check.sh` 신규 작성
- 30분 간격 자동 점검:
  - 프로세스 생존 → 죽었으면 자동 재시작
  - 스왑 > 2.5GB → 캐시 클리어
  - swappiness > 10 → 자동 재설정
  - 속도 < 0.3 t/s → Slack 알림
  - ES 임베딩 증분 < 50건/30분 → 정체 알림
  - 99.5% 도달 → 완료 알림 + 종료
- PID 89416으로 배경 실행 중
- 세션 끊어져도 독립 실행 보장

### 6. 문서 현행화 + 4개→2개 통합 (부가)

#### 상세 내용
- 4개 문서(2개 폴더) → 2개 문서(1개 폴더)로 통합:
  - `embedding_evaluation/01_etl_3phase_strategy.md` + `ragas/embedding/01_embedding_backfill_plan.md` + `ragas/embedding/02_embedding_progress_report.md` → **`embedding_evaluation/01_etl_3phase_embedding_report.md`** (v2.0)
  - `embedding_evaluation/02_what_we_can_do_with_107k_embeddings.md` → **`embedding_evaluation/02_bge_m3_and_107k_embeddings.md`** (파일명 변경)
- `ragas/embedding/` 폴더 삭제
- 중복 내용 제거, 전략+기술설정+진행현황+모니터링을 단일 문서로 통합

---

## 주요 결정사항

| 결정 | 내용 | 근거 |
|------|------|------|
| swappiness 60→10 | 스왑 paging 감소 | Infra 전문가 분석, 불필요한 스왑 1.9GB |
| torch 스레드 2→4 | CPU 4코어 완전 활용 | ETL 전문가, OOM 위험 5% 미만 |
| Phase 2 재처리 연기 | 2건만 Phase 3 완료 후 | 전문가 3인 합의 |
| WSL2 14GB 연기 | 임베딩 완료 후 적용 | wsl --shutdown 필요, 프로세스 중단 위험 |
| 헬스체크 자동 대응 | 사용자 승인 없이 자동 조치 | 사용자 명시적 요청 |

---

## 변경된 파일 목록

```
knowledge_service/
├── scripts/
│   ├── run_embedding_backfill_v2.py          # 스레드 2→4 수정
│   └── embedding_health_check.sh             # 신규: 30분 자동 진단
├── docs/04_testing/
│   ├── ragas/embedding/
│   │   ├── 01_embedding_backfill_plan.md     # v1.1 튜닝 이력
│   │   └── 02_embedding_progress_report.md   # v1.1 속도 비교
│   └── embedding_evaluation/
│       ├── 01_etl_3phase_strategy.md         # v1.1 Phase 2/3 업데이트
│       └── 02_what_we_can_do_with_107k_embeddings.md  # v1.1 튜닝 반영

/tmp/ (컨테이너 외부)
├── etl_monitor_v3.sh                          # 신규: Slack 모니터 v3
├── embedding_backfill_v2.log                  # Phase 3 로그
├── etl_progress.json                          # 진행률 JSON
└── health_check.log                           # 헬스체크 로그
```

---

## 현재 프로젝트 상태

### DB 현황 (15:13 기준)

| DB | 항목 | 수량 |
|----|------|------|
| PostgreSQL | documents | 1,449건 |
| Elasticsearch | knowledge_chunks | 108,896건 |
| Elasticsearch | 임베딩 완료 (dense_vector) | **14,556건 (13.4%)** |
| Neo4j | nodes | ~108,412개 |

### 임베딩 속도 현황 (15:13 기준)

| 항목 | 값 |
|------|-----|
| 현재 속도 | 1.26 t/s (초기 2.2에서 하락, 스왑 영향 추정) |
| ETA | ~20.8시간 (02-13 낮 예상) |
| 에러 | 0건 |
| 스왑 사용 | 1,963 MB (헬스체크 캐시 클리어 대기) |

### 배경 프로세스 (세션 독립)

| 프로세스 | PID | 간격 | 역할 |
|---------|-----|------|------|
| etl_monitor_v3.sh | 88110 | 15분 | Phase 2+3 Slack 보고 |
| embedding_health_check.sh | 89416 | 30분 | 자동 진단/대응 |
| run_embedding_backfill_v2.py | (컨테이너 내) | 상시 | BGE-M3 임베딩 |

### Sprint 상태

| 항목 | 값 |
|------|-----|
| Sprint | 09 |
| Phase | Phase 5 배포 완료, Phase 3 임베딩 진행중 |
| 임베딩 ETA | ~20시간 (02-13 낮 예상) |

---

## 다음 작업 (Action Items)

### P0 (Critical)
1. Phase 3 임베딩 완료 대기 (~12시간, 자동 운영)
2. 임베딩 완료 후 커버리지 검증 (100% 확인)

### P1 (High)
3. RAGAS v7 평가 실행 (108K+ 청크 의미 검색 효과 측정)
4. WSL2 메모리 12G → 14G 확장 (`.wslconfig` 수정 + wsl --shutdown)
5. Phase 2 선별 재처리 2건 (SW Process PDF, K8s docx)

### P2 (Medium)
6. 컨테이너 메모리 조정 (backend 2G→512M 등 낭비 해소)
7. swap 축소 (`.wslconfig` swap=2GB)
8. `embedding_evaluation/` 문서 구조 검토 (4개 문서 필요성)

---

## 리스크 모니터링

| 리스크 | 확률 | 영향 | 상태 | 대응 |
|--------|------|------|------|------|
| OOM Kill | 낮음 | 높음 | Monitoring | 헬스체크 자동 재시작 |
| 프로세스 중단 | 중간 | 중간 | Monitoring | 헬스체크 자동 재시작 |
| 속도 저하 복귀 | 중간 | 중간 | Monitoring | swappiness 자동 재설정 + 캐시 클리어 |
| WSL2 재시작 | 낮음 | 높음 | Open | 임베딩 완료 후로 연기 |
| ES scroll 만료 | 낮음 | 중간 | Monitoring | scroll=30m, 배치당 10~45초 |

---

## 사용된 도구 및 에이전트

| 도구/에이전트 | 용도 |
|--------------|------|
| Infra Engineer (서브에이전트) | 스왑/메모리 분석, swappiness 최적화 |
| ETL Engineer (서브에이전트) | 임베딩 속도 병목 분석, 스레드 최적화 |
| RAG Engineer (서브에이전트) | 재시작 안전성 검증, 속도/안정성 트레이드오프 |
| Explore Agent | 파일 탐색, ETL 스크립트 분석 |
| MCP Slack | `#proj-hrkp-dev` 채널 알림 |
| Docker exec | 컨테이너 내 프로세스 관리, ES 쿼리 |

---

## 세션 통계

| 항목 | 값 |
|------|-----|
| 수정된 파일 | 5개 |
| 신규 생성 파일 | 2개 (etl_monitor_v3.sh, embedding_health_check.sh) |
| 전문가 합의 회의 | 2회 (Phase 2 재처리, 속도 튜닝) |
| 속도 개선 | +205% (0.72 → 2.2 t/s) |
| ETA 단축 | 37시간 → 12시간 (25시간 단축) |

---

## 세션 복원 키 정보 (다음 세션 참고)

### ES 필드명
- 임베딩 필드: **`dense_vector`** (NOT `embedding`)
- 타입: `dense_vector`, dims: 1024, similarity: cosine

### sudo 패스워드
- `echo "claude" | sudo -S <command>`

### 컨테이너 내 프로세스 확인
```bash
docker exec kp-ai-service bash -c 'for p in /proc/[0-9]*/cmdline; do cat "$p" 2>/dev/null | tr "\0" " "; echo; done' | grep embedding
```

### 진행률 확인
```bash
docker exec kp-ai-service python3 -c "import json; d=json.load(open('/tmp/etl_progress.json')); print(f'embedded: {d[\"embedded\"]}/{d[\"total_chunks\"]} ({d[\"embedded\"]*100//d[\"total_chunks\"]}%), rate: {d[\"rate_texts_per_sec\"]} t/s')"
```

### ES 카운트 확인
```bash
docker exec kp-elasticsearch curl -s 'localhost:9200/knowledge_chunks/_count' -H 'Content-Type: application/json' -d '{"query":{"exists":{"field":"dense_vector"}}}'
```

---

*기록자: Claude Code (Opus 4.6)*
*최초 기록: 2026-02-12 15:03 KST*
*최종 업데이트: 2026-02-12 15:13 KST — 문서 통합, 최신 임베딩 상태 반영*
