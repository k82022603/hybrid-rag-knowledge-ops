# Session Log - 2026-02-12

**Session ID**: 2026-02-12_embedding_speed_tuning
**시작 시간**: 21:30 (이전 세션에서 계속)
**종료 시간**: 22:55
**모델**: Claude Opus 4.6 (claude-opus-4-6)

---

## 세션 요약

Phase 3 임베딩 속도 1.0→3.0~5.0 t/s 목표로 전문가 4인 분석 + 인프라 최적화 Phase 1 실행 + WSL2 재설정 준비

---

## 완료된 작업

### 1. 전문가 4인 속도 최적화 분석 (주요)

목표: 임베딩 속도 1.0 t/s → 3.0~5.0 t/s

#### ETL 엔지니어 분석
- 3-Phase 접근: 스왑 제거 → 파이프라인 스레딩 → ONNX
- Producer-Consumer 패턴으로 ES I/O와 임베딩 연산 오버랩
- Phase A(스왑 제거)만으로 2.0~2.5 t/s 예상

#### RAG 엔지니어 분석 (핵심 발견)
- **`_normalize_vector()`가 순수 Python** — 1024차원을 `math.sqrt + list comprehension`으로 처리. numpy로 100x 개선 가능
- **ONNX Runtime 미적용** — Reranker(`bge_reranker.py`)에는 이미 ONNX 패턴이 있으나 Embedder에는 미적용
- **Dockerfile에 `onnxruntime` 이미 설치됨** — 이미지 리빌드 불필요
- **batch_size=32가 L3 캐시 초과** — CPU에서는 16이 최적
- ONNX + INT8 양자화로 3.0~4.0 t/s 예상

#### Infra 엔지니어 분석
- **CPU 포화**: load avg 4.38/4코어 (100% 포화)
- **스왑 오염**: 1,789MB 중 1,497MB가 컨테이너 (Neo4j 568MB 주범)
- 7개 방안 상세 분석 (컨테이너 중지, WSL2 확장, 스왑 비활성화 등)
- Phase 1(즉시) + Phase 2(WSL2 재설정) + Phase 3(극단적 최적화) 로드맵

#### 클로드 분석
- 메모리 압박이 근본 원인
- 인프라(메모리) + 코드(ONNX) 병행 필요
- BGE-M3 모델 유지 (사용자 지시)

### 2. 인프라 최적화 Phase 1 실행 (주요)

#### 단계별 실행 및 결과

| 단계 | 조치 | 결과 |
|------|------|------|
| 1 | `docker stop kp-backend kp-api-gateway` | RAM +525MB, Swap -310MB |
| 2 | CPU 우선순위: ai-service 4096, 나머지 128 | 적용 완료 |
| 3 | swappiness 10→1 | 적용 완료 |
| 4 | 페이지 캐시 클리어 | 적용 완료 |
| 5 | Windows Chrome+Slack 종료 | Windows 메모리 ~517MB 회수 |
| 6 | `docker stop kp-neo4j kp-redis` | **Swap 1,472→795MB** |
| 7 | `sudo swapoff -a` | **Swap 0MB, 가용 RAM 7GB** |

#### 속도 변화
- Phase 1 전: 0.5~0.7 t/s (하락 추세)
- swapoff 직후: **2.8 t/s 피크** 등장
- 안정화 후: 0.8~1.9 t/s (평균 ~1.2 t/s)
- **CPU 4코어 포화가 남은 병목**으로 확인

### 3. WSL2 재설정 준비 (주요)

#### 호스트 스펙 확인 (작업 관리자 스크린샷)
- CPU: i7-1360P — **12코어 / 16스레드** (WSL2에 4개만 할당 중)
- 물리 RAM: **15.7GB** (WSL2에 12GB만 할당 중)
- L3 캐시: 18MB
- Intel Iris Xe iGPU: 3% 사용 (놀고 있음)

#### .wslconfig 변경 계획
```ini
# 변경 전
[wsl2]
memory=12GB
swap=4GB
processors=4

# 변경 후
[wsl2]
memory=14GB
swap=1GB
processors=8
```

#### 복구 스크립트 생성
- `scripts/post_wsl_restart.sh` — WSL2 재시작 후 자동 복구
- 필수 컨테이너만 시작 (ai-service, elasticsearch, postgresql)
- 임베딩 프로세스 자동 재시작
- 모니터링 스크립트 자동 재시작
- swappiness=1 자동 설정

---

## 주요 결정사항

| 결정 | 내용 | 근거 |
|------|------|------|
| BGE-M3 유지 | 모델 교체 안 함 | 사용자 지시 + 재임베딩 비용 |
| 컨테이너 4개 중지 | backend, gateway, neo4j, redis | 임베딩에 불필요 |
| swapoff -a | 스왑 완전 비활성화 | 가용 RAM 7GB로 충분 |
| WSL2 8코어+14GB | 12코어 중 8개, 15.7GB 중 14GB | CPU 포화 해소 |
| swap=1GB | 4GB→1GB | 최소 안전망 유지 |

---

## 현재 임베딩 상태 (22:54 KST)

| 항목 | 값 |
|------|------|
| 진행률 | 23,840/96,004 (24.8%) |
| 현재 속도 | ~1.2 t/s (recent) |
| ES 임베딩 | ~35,000건 |
| 에러 | 0건 |
| 실행 컨테이너 | 3개 (ai-service, elasticsearch, postgresql) |
| 스왑 | 0MB (swapoff -a) |

---

## 다음 작업 (WSL2 재시작 후)

### P0 (Critical)
1. `.wslconfig` 적용 확인: `nproc` → 8, `free -m` → ~14GB
2. `bash scripts/post_wsl_restart.sh` 실행
3. 임베딩 속도 확인 (목표: 2.0+ t/s)

### P1 (High)
4. ONNX Runtime 전환 (Reranker 패턴 참조)
5. `_normalize_vector()` numpy 교체
6. batch_size 32→16 조정

### P2 (Medium)
7. INT8 양자화 적용
8. OpenVINO 검토 (Intel iGPU 활용)

---

## 리스크 모니터링

| 리스크 | 확률 | 영향 | 상태 | 대응 |
|--------|------|------|------|------|
| WSL2 14GB로 Windows 메모리 부족 | Low | Med | Monitoring | Windows에 1.7GB 남김 |
| swap=1GB로 OOM | Low | High | Monitoring | 컨테이너 3개만 운영 |
| 임베딩 재시작 실패 | Low | High | Open | post_wsl_restart.sh 복구 스크립트 |

---

## 세션 통계

| 항목 | 값 |
|------|------|
| 전문가 분석 | 4건 (ETL, RAG, Infra, Claude) |
| 컨테이너 중지 | 4개 |
| 스크립트 생성 | 1개 (post_wsl_restart.sh) |
| 속도 피크 | 2.8 t/s (swapoff 직후) |
| 핵심 발견 | CPU 4코어 포화가 최종 병목 |

---

*기록자: Claude Code (Opus 4.6)*
*기록 시간: 2026-02-12 22:55 KST*
