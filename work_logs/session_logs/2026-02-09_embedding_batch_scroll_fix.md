# Session Log - 2026-02-09 (이어서)

**Session ID**: 2026-02-09_embedding_batch_scroll_fix
**시작 시간**: 17:00 KST (이전 세션 컨텍스트 복원)
**종료 시간**: 진행 중
**모델**: Claude Opus 4.6 (claude-opus-4-6)

---

## 세션 요약

임베딩 배치 모니터링, ES Scroll Timeout 대책 수립 및 구현, 운영매뉴얼 보강

---

## 이전 세션에서 이어받은 상태

- 전체 13,430 청크 중 ~3,612개 임베딩 완료 (26.9%)
- `embedding_full_cycle.py` 구현 완료 (Phase 3)
- 배치 실행 중 (batch_size=4, checkpoint 1000에서 재개)
- 운영매뉴얼 v3.0 전체 재구성 완료

---

## 완료된 작업

### 1. 임베딩 배치 모니터링 및 Slack 보고

- 배치 진행률 지속 모니터링 (17:01 → 17:58 → 18:52 → 19:11)
- Slack `#proj-hrkp-dev` 채널에 진행 보고 3회 전송
- ES 임베딩 현황: 3,612 → 6,524 (48.6%)로 진행

### 2. ES Scroll Context Timeout 대응

#### 문제 분석
- 법률 문서 청크가 CPU에서 170~420초/배치 소요
- `scroll="10m"`, `scroll_size=100` → 페이지당 25배치 = 최대 175분 >> 10분 timeout
- 1,200건마다 반복적으로 scroll timeout 발생

#### 해결 (embedding_full_cycle.py 수정)

| 항목 | 변경 전 | 변경 후 |
|------|---------|---------|
| scroll_timeout | `10m` (하드코딩) | `60m` (기본, CLI 조정 가능) |
| scroll_size | `100` (기본) | `20` (기본) |
| CLI 인자 | `--scroll-size`만 | `--scroll-timeout` 추가 |
| CONFIG 출력 | batch_size만 | scroll_size, scroll_timeout 포함 |

**최악 시나리오**: 5배치 × 420초 = 35분 < 60분 → 안전

### 3. 운영매뉴얼 보강 (v3.0 → v3.1)

`knowledge_service/docs/07_maintenance/data_loading_operations_guide.md`:

- **§13.9 ES Scroll Context 관리** (신규 섹션 추가)
  - Scroll API 동작 방식 (ASCII 다이어그램)
  - 설정값 테이블 (v3.1 변경사항 반영)
  - 한 페이지 처리 시간 계산식
  - Timeout 발생 원인 (Mermaid 시퀀스 다이어그램)
  - 실제 발생 사례 데이터 (2026-02-09)
  - 방어 메커니즘 3가지 설명
  - 복구 절차 명령어
- **§13.6 batch_size 권장값** 수정
  - CPU에서 batch_size=16이 4보다 6배 느린 이유 설명
  - 실측 기반 CPU/GPU 권장값 테이블로 교체
- **§13.4 CLI 옵션** 업데이트
  - `--scroll-size`, `--scroll-timeout` 추가
- **§15 트러블슈팅** 보강
  - Scroll timeout Q&A 상세화 + §13.9 참조

---

## 수정 파일 목록

| 파일 | 변경 내용 |
|------|----------|
| `knowledge_service/scripts/embedding_full_cycle.py` | scroll_timeout/scroll_size 기본값 변경, CLI 인자 추가 |
| `knowledge_service/docs/07_maintenance/data_loading_operations_guide.md` | §13.9 신규, §13.4/13.6/15 업데이트, v3.1 |

---

## 현재 진행 중

### 임베딩 배치 실행 (Task #4)

| 시점 | ES 임베딩 | 진행률 | 비고 |
|------|----------|--------|------|
| 세션 시작 | 3,612 | 26.9% | 이전 세션 종료 시점 |
| 17:01 | 6,316 | 47.0% | 첫 진행 보고 |
| 17:58 | 6,444 | 48.0% | 법률 문서 구간 진입 (속도 저하) |
| 18:05 | 6,452 | 48.1% | Scroll timeout → 체크포인트 1,200건 |
| 18:52 | 6,496 | 48.4% | 재개 후 진행 |
| 19:11 | 6,524 | 48.6% | 현재 |

- 배치 ID: `b4f1f83` (체크포인트 1,200건에서 재개)
- 다음 scroll timeout 시 수정된 코드(60m/20) 반영하여 재개 예정

### 대기 작업

- Task #5: ai-service 버그 수정 배포 (임베딩 배치 진행 중)
- Task #6: QA E2E 테스트 (배포 후)

---

## 핵심 인사이트

### CPU에서의 BGE-M3 임베딩 특성

1. **batch_size=16은 CPU에서 6배 느림**: sentence-transformers는 CPU에서 순차 처리, 큰 배치 = 긴 단일 연산
2. **법률 문서 청크는 수천 토큰**: 일반 기술 문서(5초/배치) 대비 법률(170~420초/배치) = 34~84배 느림
3. **Scroll timeout은 "예상된 동작"**: 체크포인트 + 재개 메커니즘으로 설계됨, 완전 실패가 아님

### Scroll 최적화 전략

```
핵심 공식: 페이지 처리 시간 = (scroll_size / batch_size) × 배치 소요시간

목표: 페이지 처리 시간 < scroll_timeout

변경 전: (100 / 4) × 420초 = 10,500초 >> 600초(10분) → 실패
변경 후: (20 / 4)  × 420초 = 2,100초  << 3,600초(60분) → 성공
```
