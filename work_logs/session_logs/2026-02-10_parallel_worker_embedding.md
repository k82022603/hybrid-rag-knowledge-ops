# Session Log - 2026-02-10

**Session ID**: 2026-02-10_parallel_worker_embedding
**시작 시간**: (세션 시작 시점)
**모델**: Claude Opus 4.6 (claude-opus-4-6)

---

## 세션 요약

임베딩 배치 hung 상태 해결을 위한 병렬 워커 + 텍스트 절단 + 배치 타임아웃 구현 (Option C)

---

## 이전 상태

- 배치 ba5fe80이 9시간 이상 hung (2,216/6,878에서 정지)
- 법률 문서 청크가 420초/배치로 극도로 느림
- ES 현재 7,476/13,430 (55.7%), 잔여 5,954개 처리 필요

---

## 완료된 작업

### 1. embedding_full_cycle.py 병렬 워커 튜닝

`knowledge_service/scripts/embedding_full_cycle.py` 수정:

#### 1-1. `--max-text-length` (텍스트 절단)
- CLI 인자: `--max-text-length 4000` (기본 0=무제한)
- 텍스트 추출 후 `text[:max_text_length]`로 절단
- 효과: 법률 문서 420초/배치 → ~5초/배치 (O(n²) 어텐션 감소)
- 싱글 워커 모드 + 멀티 워커 모드 모두 적용

#### 1-2. `--workers N` (멀티프로세스)
- `multiprocessing.Process`로 N개 워커 생성
- 동작 흐름:
  1. ES Scroll로 전체 chunk _id 수집 (본문 없이 빠름)
  2. N등분 파티셔닝
  3. 각 워커가 독립적으로 모델 로드 + mget → embed → bulk update
- 워커별 체크포인트 분리 (`/tmp/embedding_checkpoint_worker_{N}.json`)
- 워커 간 10초 stagger (메모리 피크 방지)
- 메모리: 워커당 BGE-M3 ~2GB → 2워커 = ~6GB (WSL 11GB 내)

#### 1-3. `--batch-timeout` (배치 타임아웃)
- `concurrent.futures.ThreadPoolExecutor`로 구현
- 배치가 지정 초 초과 시 스킵 + 로그 (`[TIMEOUT]`)
- 기본값 300초, 0=무제한
- `FuturesTimeoutError` 별도 catch → failed 카운트

### 2. 운영매뉴얼 업데이트 (v3.1 → v3.2)

`knowledge_service/docs/07_maintenance/data_loading_operations_guide.md`:

- **§13.1**: 비교 테이블에 병렬 워커/텍스트 절단/배치 타임아웃 행 추가
- **§13.2**: "병렬 워커 + 텍스트 절단" 실행 예시 추가 + 변경 배경 설명
- **§13.4**: CLI 옵션에 `--max-text-length`, `--workers`, `--batch-timeout` 추가
- **§13.10**: 병렬 워커 모드 신규 섹션 (Mermaid 아키텍처, 메모리 요구사항, 성능 비교)
- **§15**: "배치가 수시간 hung 상태" 트러블슈팅 항목 추가
- 버전: v3.1 → v3.2

---

## 수정 파일 목록

| 파일 | 변경 내용 |
|------|----------|
| `knowledge_service/scripts/embedding_full_cycle.py` | --max-text-length, --workers, --batch-timeout 3개 기능 추가 |
| `knowledge_service/docs/07_maintenance/data_loading_operations_guide.md` | §13.1/13.2/13.4/13.10/15 업데이트, v3.2 |

---

## 실행 계획 (배치 실행)

```bash
# 1. hung 프로세스 Kill
docker exec kp-ai-service pkill -f embedding_full_cycle || true

# 2. 수정된 코드는 볼륨 마운트로 자동 반영

# 3. 병렬 실행
docker exec kp-ai-service python3 /app/scripts/embedding_full_cycle.py \
  --mode all --workers 2 --max-text-length 4000 --batch-size 4 \
  --batch-timeout 300 --stop-service
```

## 예상 효과

| 항목 | 현재 | 튜닝 후 |
|------|------|---------|
| 법률 문서 배치 | 420초 | ~5초 (텍스트 절단) |
| 워커 수 | 1 | 2 (병렬) |
| 총 속도 | 0.1 chunks/s | ~3-5 chunks/s |
| 잔여 5,954개 예상 시간 | 수일 | 20-30분 |

---

## 핵심 인사이트

1. **O(n²) 어텐션이 근본 원인**: BGE-M3의 self-attention은 토큰 길이의 제곱에 비례. 4000토큰 → 1000토큰은 16배 속도 향상
2. **멀티프로세스 > 스레드**: Python GIL 때문에 임베딩은 스레드 병렬화 불가. Process로 독립 모델 인스턴스 필요
3. **mget이 scroll보다 워커에 적합**: 워커는 미리 할당된 ID로 직접 mget → scroll 경합 없음
