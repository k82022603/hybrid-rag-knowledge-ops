# RAG Engineer 반성문

**작성일**: 2026-02-14 19:30 KST
**작성자**: RAG Engineer Agent (MLRag)

---

## 무엇을 잘못했는가

### 1. 모니터링 스크립트 방어 코드 부족

`etl_phase1_monitor.sh` 스크립트에서 OOM Kill 발생 후 2시간 동안 감지하지 못했습니다. 근본 원인은 bash 산술 비교에서 개행문자(`\n`)가 포함된 변수 처리 실패입니다.

구체적으로:
- `grep -c` 출력값에 개행이 섞여 `$((SUCCESS + SKIPPED + FAILED))` 산술에서 `bash: value too great for base` 에러 발생
- `set -uo pipefail` (사실 이 스크립트에는 없었지만 embedding_health_check.sh에는 있음) 설정 하에서는 이런 에러 하나로 전체 스크립트가 종료됨
- 정체 감지 로직(`STALE_COUNT >= 3`)을 추가했으나, 스크립트 자체가 크래시하면 감지 자체가 불가능

RAG Engineer로서 모니터 스크립트의 self-health와 에러 복원력을 검증하지 않은 것은 명백한 실수입니다.

### 2. 청크 크기 이상 징후 무시

`chunk_size=1000`으로 설정했는데 6,765 tokens 청크가 발생했다는 보고가 있었습니다. 이 이상 징후를 조사하지 않았습니다.

코드를 분석해보면 원인은 명확합니다:
- `SemanticChunker`의 `max_chunk_size` 기본값은 `2048` (문자 수)
- 코드/테이블 특수 블록(`seg_type in ("code", "table")`)은 `max_chunk_size`를 초과해도 분할하지 않음 (`chunker.py:463`)
- `ChunkQualityGate`에서도 코드/테이블은 bypass (`chunk_quality_filter.py:71-73`)
- 따라서 거대한 코드블록이나 테이블이 통째로 하나의 청크가 될 수 있음

6,765 tokens 청크는 임베딩 모델(BGE-M3)의 max_length=8192 한도에 근접하며, 임베딩 품질이 저하됩니다.

### 3. 임베딩 상태 관리 기준 미비

ES에 저장되는 `embedding_status` 필드가 `success`/`pending` 두 가지만 있는데, 실제 운영에서는 더 세분화된 상태가 필요합니다:
- `pending`: Phase 1에서 생성, 임베딩 대기
- `processing`: 임베딩 진행 중 (backfill 스크립트가 처리 중)
- `success`: 임베딩 완료
- `failed`: 임베딩 실패 (재시도 필요)
- `skipped`: 의도적으로 건너뜀 (너무 큰 청크 등)

현재는 `pending` → `success`만 전환되고, 실패 시 `pending`에 머물러 무한 재시도 위험이 있습니다.

---

## 무엇을 배웠는가

1. **모니터 스크립트는 자체 방어가 필수**: 모니터 스크립트가 크래시하면 모니터링 자체가 사라짐. `trap`, `set +e`, 각 단계별 try-catch 패턴 필요
2. **특수 블록 청크 크기 제한**: 코드/테이블도 임베딩 모델의 max_tokens 한도를 고려한 상한 필요
3. **상태 머신 명확화**: embedding_status의 상태 전이도를 명확히 정의하고 코드에 반영해야 함

---

## 분석 1: 모니터 스크립트 개선

### 현재 문제점

| # | 문제 | 위험도 | 코드 위치 |
|---|------|--------|-----------|
| 1 | `grep -c` 출력 개행 → 산술 오류 | High | `etl_phase1_monitor.sh:27-29` |
| 2 | 스크립트 크래시 시 감지 불가 | Critical | 스크립트 전체 |
| 3 | `docker exec` 실패 시 빈 값 전파 | Medium | `etl_phase1_monitor.sh:23-28` |
| 4 | 정체 감지가 ES 청크 수에만 의존 | Medium | `etl_phase1_monitor.sh:65-76` |
| 5 | ETL 프로세스 사망 감지가 `docker top | grep` 의존 | Medium | `etl_phase1_monitor.sh:80` |

### 개선 방안

#### 1. 에러 복원력 (trap + 개별 단계 방어)

```bash
#!/bin/bash
# set -e를 쓰지 않음 (개별 명령 실패에 스크립트 종료 방지)
# 대신 각 명령을 || echo "default" 패턴으로 방어

# 스크립트 self-health: 자기 PID 기록
echo $$ > /tmp/etl_monitor.pid

# 비정상 종료 시 알림
trap 'echo "[FATAL] Monitor crashed at $(date)" >> /tmp/etl_monitor_crash.log; bash "$SEND_SLACK" alerts "ETL-Monitor" "Monitor script crashed! Manual restart needed." 2>/dev/null' EXIT
```

#### 2. Self-Health-Check (watchdog 패턴)

별도 1-liner watchdog를 cron 또는 while loop로 실행:
```bash
# watchdog.sh (5분 간격)
if ! kill -0 "$(cat /tmp/etl_monitor.pid 2>/dev/null)" 2>/dev/null; then
    nohup bash /path/to/etl_phase1_monitor.sh > /tmp/etl_phase1_monitor.log 2>&1 &
    bash /path/to/send_slack.sh alerts "Watchdog" "Monitor was dead, restarted"
fi
```

#### 3. 변수 안전 처리 강화

```bash
# 현재 (위험)
SUCCESS=$(docker exec kp-ai-service grep -c "processed successfully" "$LOG_FILE" 2>/dev/null | tr -d '\n\r ' || echo "0")

# 개선 (더 안전)
_raw=$(docker exec kp-ai-service grep -c "processed successfully" "$LOG_FILE" 2>/dev/null || true)
SUCCESS=$(echo "$_raw" | tr -d '\n\r [:space:][:alpha:]' | grep -E '^[0-9]+$' || echo "0")
# 숫자만 추출 + 빈값/문자 혼입 완전 방어
```

#### 4. 프로세스 생존 확인 강화

```bash
# 현재 (약함): docker top | grep
ETL_ALIVE=$(docker top kp-ai-service 2>/dev/null | grep -c "run_etl" || echo "0")

# 개선: /proc 직접 조회 + PID 파일 확인
ETL_ALIVE=$(docker exec kp-ai-service bash -c '
    for p in /proc/[0-9]*/cmdline; do
        cat "$p" 2>/dev/null | tr "\0" " "
        echo
    done' 2>/dev/null | grep -c "run_etl" || echo "0")

# 또는 PID 파일 기반
ETL_PID=$(docker exec kp-ai-service cat /tmp/etl_phase1.pid 2>/dev/null || echo "")
if [ -n "$ETL_PID" ]; then
    ETL_ALIVE=$(docker exec kp-ai-service kill -0 "$ETL_PID" 2>/dev/null && echo "1" || echo "0")
fi
```

#### 5. 다중 정체 지표

```bash
# ES 청크 수 + PG 문서 수 + 로그 파일 mtime 3가지 모두 확인
LOG_MTIME=$(docker exec kp-ai-service stat -c %Y "$LOG_FILE" 2>/dev/null || echo "0")
MTIME_AGE=$(($(date +%s) - LOG_MTIME))

# 30분 이상 로그 갱신 없으면 추가 경고
if [ "$MTIME_AGE" -gt 1800 ]; then
    STALE_INDICATORS=$((STALE_INDICATORS + 1))
fi
```

### `embedding_health_check.sh` 특이 사항

`embedding_health_check.sh:21`에 `set -uo pipefail`이 있습니다. 이 스크립트에서 어떤 `docker exec` 명령이든 실패하면 (컨테이너 일시 중단, 네트워크 지연 등) 전체 스크립트가 종료됩니다.

개선: `set -uo pipefail`을 제거하고, 각 명령에 `|| default` 패턴을 적용하거나, 최소한 `set +e`로 변경합니다.

---

## 분석 2: 데이터 품질 기준 정의

### 청크 품질 기준 (ETL 재시작 시 적용)

| 기준 | 현재 값 | 권장 값 | 근거 |
|------|---------|---------|------|
| **최소 토큰 수** | 10 (`ChunkQualityGate.MIN_TOKEN_COUNT`) | **10** (유지) | 10 tokens 미만은 의미 단위 불가 |
| **최소 문자 수** | 30 (`ChunkQualityGate.MIN_CHAR_LENGTH`) | **30** (유지) | 한국어 10자 = ~10 tokens |
| **최대 토큰 수** | 없음 (코드/테이블 무제한) | **1500** (신규) | BGE-M3 max_length=8192이지만 1500 이상은 품질 저하 |
| **최대 문자 수** | 2048 (`SemanticChunker.max_chunk_size`) | **4500** (상향) | 한국어 기준 ~1500 tokens |
| **빈 content 감지** | 있음 (`_parse_file` + `ChunkQualityGate`) | **유지** | 빈 text 체크 이미 다단계 적용 |
| **의미있는 문자 비율** | 30% | **30%** (유지) | 특수문자 70% 이상은 노이즈 |

### 구체적 수치 근거

#### 최소 청크 크기: 10 tokens / 30 chars (유지)

현재 `ChunkQualityGate`와 `SemanticChunker._split_text_by_sentences`에서 이미 이 기준을 적용:
- `chunk_quality_filter.py:26-27`: `MIN_TOKEN_COUNT = 10`, `MIN_CHAR_LENGTH = 30`
- `chunker.py:572`: `token_count >= 10 and len(stripped) >= 30`

10 tokens 미만의 텍스트는 "제목만", "번호만" 같은 무의미 단편입니다. 이 기준은 적절합니다.

#### 최대 청크 크기: 1500 tokens (신규 추가 필요)

현재 코드/테이블 블록은 크기 제한 없이 통과합니다:
```python
# chunker.py:461-464
if seg_type in ("code", "table"):
    raw_chunks.append((content.strip(), seg_start, seg_end, seg_type))
```

BGE-M3의 max_length는 8192 tokens이지만, 실무에서 1500 tokens 이상 입력은:
- 어텐션 분산으로 의미 해상도 저하
- CPU 임베딩 시 처리 시간 급증 (O(n^2) 어텐션)
- OOM 위험 증가 (batch_size=4 + 1500 tokens도 ~3GB)

**권장**: 코드/테이블도 1500 tokens 초과 시 분할하거나, `embedding_status=skipped`로 처리

#### 빈 content 감지 (이미 다단계 적용)

현재 3단계 방어:
1. `initial_data_loader.py:886`: `parsed_doc.content.strip()` 체크
2. `chunker.py:204`: `text.strip()` 체크
3. `chunk_quality_filter.py:75`: `text = chunk.content.strip()` + `MIN_CHAR_LENGTH` 체크

추가로 ES 저장 시 `text` 필드 빈값 체크가 있으면 완벽합니다:
```python
# _store_to_elasticsearch에서 text 필드 검증
if not chunk.content or not chunk.content.strip():
    logger.warning("Empty chunk content detected, skipping: %s", chunk.id)
    continue
```

#### 중복 문서 감지 (file_hash 기반, 이미 구현)

`initial_data_loader.py:633-695`에 SHA-256 기반 중복 감지 구현:
- `_compute_file_hash()`: 파일 SHA-256 계산
- `_check_duplicate()`: PG `documents.file_hash` 컬럼으로 중복 확인
- 중복 시 `LoadStatus.SKIPPED` 반환

**문제점**: `processing_status = 'completed'` 조건만 체크합니다. 이전 ETL이 `failed`로 남은 문서는 중복으로 안 걸립니다. 재시작 시 전체 삭제하므로 이번에는 문제없지만, 향후 증분 ETL에서는 `completed OR failed` 모두 체크해야 합니다.

#### 임베딩 상태 관리 기준

현재 상태: `pending` | `success` (2가지)

**권장 상태 머신 (5가지)**:
```
pending ──→ processing ──→ success
    │            │
    │            └──→ failed ──→ pending (재시도)
    │
    └──→ skipped (너무 큰 청크, 빈 content 등)
```

| 상태 | 의미 | 전환 조건 |
|------|------|-----------|
| `pending` | 청킹 완료, 임베딩 대기 | Phase 1 저장 시 |
| `processing` | 임베딩 진행 중 | backfill 스크립트가 배치 시작 시 |
| `success` | 임베딩 완료 | dense_vector 저장 완료 시 |
| `failed` | 임베딩 실패 | 예외 발생 시 (retry_count 필드 추가) |
| `skipped` | 의도적 건너뜀 | token_count > 1500 또는 빈 content |

`failed` 상태에는 `retry_count` 필드를 추가하여 3회 이상 실패 시 `skipped`로 전환합니다.

---

## 재발 방지 대책

| # | 대책 | 담당 | 우선순위 |
|---|------|------|----------|
| 1 | 모니터 스크립트 trap + watchdog 추가 | RAG + Infra | P0 |
| 2 | `set -uo pipefail` 제거, 개별 방어로 전환 | RAG | P0 |
| 3 | 코드/테이블 청크 1500 tokens 상한 추가 | RAG + ETL | P1 |
| 4 | embedding_status 5-state 전환 | RAG | P1 |
| 5 | 중복 감지: failed 상태도 포함 | ETL | P2 |
| 6 | ES 저장 시 빈 content 최종 검증 | ETL | P2 |

---

## 반성

모니터링 스크립트가 "스스로를 모니터링하지 못하는" 구조적 문제를 간과했습니다. OOM Kill은 인프라 영역이지만, 그 OOM Kill을 2시간이나 감지 못한 것은 모니터 스크립트의 robustness 문제이며, 이는 RAG Engineer의 책임 영역입니다.

또한, 청크 크기 이상치(6,765 tokens)는 시스템이 보고한 경고 신호였는데, 이를 단순히 "코드 블록은 원래 크다"로 치부하고 조사하지 않았습니다. 이상 징후를 무시하지 않는 습관이 필요합니다.

데이터 품질 기준은 코드 레벨에서 이미 상당히 잘 구현되어 있었지만(ChunkQualityGate, dedup 등), 문서화되지 않아 팀원들이 참조할 수 없었습니다. 이 반성문이 그 문서화의 시작입니다.
