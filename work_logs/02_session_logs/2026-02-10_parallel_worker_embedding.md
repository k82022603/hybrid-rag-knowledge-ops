# Session Log - 2026-02-10

**Session ID**: 2026-02-10_parallel_worker_embedding
**시작 시간**: 21:00 KST
**모델**: Claude Opus 4.6 (claude-opus-4-6)

---

## 세션 요약

임베딩 배치 hung 상태(9시간+) 해결을 위한 병렬 워커 + 텍스트 절단 + 배치 타임아웃 구현.
실측 튜닝을 거쳐 **1워커 + max_text_length=1500 + batch_size=4**가 CPU 최적값으로 확정.

---

## 이전 상태

- 배치 ba5fe80이 9시간 이상 hung (2,216/6,878에서 정지, 최종 OOM Kill exit 137)
- 법률 문서 청크가 420초/배치로 극도로 느림
- ES 시작 시점: 7,488/13,430 (55.7%)

---

## 완료된 작업

### 1. embedding_full_cycle.py 3개 기능 구현

`knowledge_service/scripts/embedding_full_cycle.py` 수정 (+371줄):

| 기능 | CLI 인자 | 구현 방식 |
|------|---------|----------|
| 텍스트 절단 | `--max-text-length N` | `text[:max_text_length]` 적용 |
| 병렬 워커 | `--workers N` | `multiprocessing.Process` N개 생성, ID 파티셔닝 |
| 배치 타임아웃 | `--batch-timeout N` | `ThreadPoolExecutor` + `future.result(timeout=N)` |

### 2. 실측 튜닝 (4단계 시행착오)

#### Phase 1: 2워커 + max_text_length=4000 (실패)
- 배치 속도: 60~109초/배치
- 문제: **CPU 경합** — 2워커가 동일 CPU를 공유하여 개별 배치가 2배 느려짐
- 결과: 합산 throughput이 싱글 워커와 동일 (0.1 chunks/s)

#### Phase 2: 1워커 + max_text_length=4000 (부분 성공)
- 배치 속도: 60초/배치
- 문제: 4000자도 CPU에서 여전히 느림

#### Phase 3: 1워커 + max_text_length=1500 (성공)
- 배치 속도: **6~35초/배치** (기존 420초 대비 12~70배 개선)
- throughput: 0.3~0.5 chunks/s
- fail=0, 메모리 2.0~2.4GB 안정

#### Phase 4: batch_size=8 시도 (실패 → 4로 복귀)
- 8건 배치: 55초 (7초/건)
- 4건 배치: 7초 (1.75초/건)
- CPU에서 batch_size 증가 = 선형 시간 증가 → **throughput 이득 없음**

### 3. 최종 확정 파라미터 (CPU 환경)

```
--max-text-length 1500  # 1500자 절단 (375토큰)
--batch-size 4          # CPU 최적값
--batch-timeout 120     # 2분 타임아웃
--workers 1             # 싱글 워커 (CPU 경합 방지)
--stop-service          # uvicorn 중지로 메모리 확보
```

### 4. 운영매뉴얼 업데이트 (v3.1 → v3.2)

`knowledge_service/docs/07_maintenance/data_loading_operations_guide.md`:

- **§13.1**: 비교 테이블에 병렬 워커/텍스트 절단/배치 타임아웃 행 추가
- **§13.2**: 병렬 워커 실행 예시 + 변경 배경 설명 추가
- **§13.4**: CLI 옵션에 3개 신규 인자 추가
- **§13.10**: 병렬 워커 모드 신규 섹션 (Mermaid 아키텍처, 메모리 요구사항, **실측 성능 테이블**)
  - 권장 실행 명령 (nohup 방식)
  - 2워커 CPU 경합 경고
  - batch_size=8 역효과 실측 데이터
- **§15**: "배치가 수시간 hung 상태" 트러블슈팅 항목 추가
- 버전: v3.1 → v3.2

### 5. 기타

- 컨테이너 리빌드 (`docker-compose build ai-service`) — scripts/ 볼륨 미마운트 이슈
- `docker cp`로 스크립트 수동 복사 (리빌드 후에도 필요)
- nohup 실행 패턴 확립 (`docker exec -d ... bash -c 'nohup ... &'`)

---

## 수정 파일 목록

| 파일 | 변경 내용 |
|------|----------|
| `knowledge_service/scripts/embedding_full_cycle.py` | --max-text-length, --workers, --batch-timeout 3개 기능 추가 |
| `knowledge_service/docs/07_maintenance/data_loading_operations_guide.md` | §13 전체 보강, 실측 데이터 반영, v3.2 |
| `work_logs/session_logs/2026-02-10_parallel_worker_embedding.md` | 본 세션로그 |

---

## 임베딩 배치 진행 현황

| 시점 (KST) | ES 카운트 | 진행률 | 30분 증분 | 비고 |
|------------|----------|--------|----------|------|
| 21:00 | 7,488 | 55.7% | — | 세션 시작 |
| 21:39 | 7,516 | 56.0% | — | 2워커 시작 |
| 21:45 | 7,548 | 56.2% | +32 | 2워커 CPU 경합 확인 |
| 21:52 | 7,548 | 56.2% | — | 1워커+1500자로 전환 |
| 22:00 | 7,752 | 57.7% | +204 | 안정화 확인 |
| 22:10 | 7,928 | 59.0% | — | batch_size=8 시도→실패→4 복귀 |
| 22:31 | 8,296 | 61.8% | +368 | 안정 진행 |
| 22:41 | 8,400 | 62.5% | +104 | 법률 구간 진입 (속도 저하) |
| 23:07 | 8,684 | 64.7% | +284 | 법률 구간 계속 |

**예상 완료**: 2/11 오전 04:00~06:00 KST (잔여 4,746개 ÷ 0.2~0.3/s)

---

## 핵심 인사이트

### CPU 임베딩 최적화 결론

1. **텍스트 절단이 가장 효과적**: O(n²) 어텐션에서 n을 줄이는 것이 근본 해법
   - 16,000자(420초) → 1,500자(7초) = **60배 속도 향상**
2. **멀티워커는 CPU에서 무의미**: 2워커 = CPU 경합으로 개별 배치 2배 느려짐, 합산 동일
3. **batch_size=4가 CPU 최적**: 8건은 55초(7초/건), 4건은 7초(1.75초/건) = 4배 차이
4. **nohup 필수**: `docker exec -d`는 셸 세션 종료 시 프로세스도 종료됨

### 능동적 대처 교훈

- 실측 데이터로 판단 가능하면 **즉시 전환하고 결과 보고**
- "~할까요?" 질문은 시간 낭비 → "~로 전환 완료" 보고가 올바른 패턴
