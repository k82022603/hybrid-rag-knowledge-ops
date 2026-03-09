# 테스트 전 리소스 정리 가이드

**문서 번호**: DEV-003
**작성일**: 2026-03-09
**적용 대상**: QA 주도 테스트, E2E 테스트, UAT, 부하 테스트 등 메모리 소요가 많은 테스트

---

## 1. 목적

Docker 기반 테스트 환경에서 메모리 부족으로 인한 컨테이너 OOM, 테스트 실패, 시스템 불안정을 사전 방지한다.

### 배경 (2026-03-09 사례)

| 항목 | 정리 전 | 정리 후 |
|------|---------|---------|
| 빌드 캐시 | 18 GB | 62 MB |
| 미사용 이미지 | 36.26 GB | 22.07 GB |
| Free 메모리 | 374 MiB | 924 MiB |

빌드 캐시 + 미사용 이미지가 디스크를 점유하면 Docker의 copy-on-write 레이어와 메모리 매핑에 영향을 주어, 테스트 중 컨테이너 OOM과 Swap 과다 사용을 유발한다.

---

## 2. 적용 기준

아래 조건 중 **하나라도** 해당하면 테스트 전 리소스 정리를 **필수** 수행한다.

| 조건 | 기준값 |
|------|--------|
| Docker 빌드 캐시 | 1 GB 이상 |
| 시스템 Free 메모리 | 1 GiB 미만 |
| Swap 사용률 | 50% 이상 |
| 테스트 유형 | QA 주도 테스트, E2E, UAT, 부하(k6), RAGAS 평가 |
| AI Service 포함 테스트 | 항상 (BGE-M3 + Reranker ONNX 모델이 ~3 GiB 메모리 점유) |

---

## 3. 정리 절차

### Step 1: 현재 상태 확인

```bash
echo "=== 시스템 메모리 ==="
free -h

echo "=== Docker 디스크 사용량 ==="
docker system df

echo "=== 컨테이너 메모리 TOP 5 ==="
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}" | sort -k3 -t'/' -h -r | head -7
```

### Step 2: Linux 파일 캐시 해제 (필수 — 사용자 직접 실행)

> **⚠️ 이 단계는 sudo 권한이 필요하므로 반드시 사용자가 직접 실행해야 합니다.**
> Claude Code/에이전트는 sudo 비밀번호 입력이 불가하므로, **테스트 시작 전에 사용자에게 실행을 요청**하세요.
> **이 단계를 건너뛰고 테스트를 시작하면 리소스 정리의 의미가 없습니다.**

```bash
# WSL2 터미널에서 실행
sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'

# 또는 PowerShell에서 실행 (WSL2 터미널이 없을 때)
wsl -u root sh -c "echo 3 > /proc/sys/vm/drop_caches"
```

```bash
free -h   # buff/cache 감소 확인
```

- Linux 커널이 Docker 이미지 overlay 레이어를 메모리에 캐시 (보통 3~6 GiB)
- WSL2는 이 캐시를 Windows에 자동 반환하지 않아 호스트 메모리 압박 유발
- `drop_caches`는 미사용 캐시만 해제하므로 **실행 중 컨테이너에 영향 없음**
- **회수 효과**: 보통 3~6 GiB (즉시)
- **확인 기준**: buff/cache가 1 GiB 이하로 감소했으면 정상

### Step 3: Docker 빌드 캐시 정리 (필수)

```bash
docker builder prune -f
```

- 빌드 캐시는 이전 빌드의 레이어를 캐싱하여 재빌드 속도를 높이지만, 테스트 전에는 불필요
- 정리 후 첫 번째 빌드만 약간 느려짐 (이후 새 캐시 생성)
- **회수 효과**: 보통 5~20 GB

### Step 4: 미사용 Docker 이미지 정리 (필수)

```bash
docker image prune -a -f
```

- **현재 실행 중인 컨테이너의 이미지는 보존됨** (안전)
- 중지된 컨테이너가 참조하는 old 이미지만 제거됨
- 정리 후 재빌드가 필요할 수 있음 (base 이미지 재다운로드)
- **회수 효과**: 보통 5~15 GB

### Step 5: (선택) 불필요 컨테이너 중지

테스트에 필수가 아닌 Observability 컨테이너를 중지하여 메모리를 확보한다.

```bash
cd /mnt/d/Users/KTDS/Documents/06.과제/hybrid-rag-knowledge-ops/infrastructure/docker

# Observability 서비스 중지 (모니터링/로깅)
docker compose stop grafana prometheus promtail loki jaeger kibana \
  nginx-exporter postgres-exporter redis-exporter
```

| 서비스 | 메모리 절감 |
|--------|:----------:|
| grafana + prometheus + loki | ~200 MiB |
| jaeger + kibana | ~300 MiB |
| exporter 3종 | ~50 MiB |
| **합계** | **~550 MiB** |

### Step 6: 정리 결과 확인

```bash
echo "=== 정리 후 ==="
docker system df
free -h
```

**통과 기준**:
- 빌드 캐시 < 500 MB
- Free 메모리 > 1 GiB
- Swap 사용률 < 50%

---

## 4. 자동화 스크립트

`scripts/pre_test_cleanup.sh` 로 저장하여 테스트 전 실행:

```bash
#!/bin/bash
# Pre-test resource cleanup
# Usage: bash scripts/pre_test_cleanup.sh

set -euo pipefail

echo "=========================================="
echo " Pre-Test Resource Cleanup"
echo "=========================================="

# Step 1: 현재 상태
echo ""
echo "[1/5] 현재 상태 확인..."
FREE_MEM=$(free -m | awk '/^Mem:/{print $4}')
BUFF_CACHE=$(free -m | awk '/^Mem:/{print $6}')
CACHE_SIZE=$(docker system df --format '{{.Size}}' | head -4 | tail -1)
echo "  Free Memory: ${FREE_MEM} MiB"
echo "  Buff/Cache:  ${BUFF_CACHE} MiB"
echo "  Build Cache: ${CACHE_SIZE}"

# Step 2: Linux 파일 캐시 해제 (WSL2 메모리 회수)
echo ""
echo "[2/5] Linux 파일 캐시 해제..."
if sudo -n sh -c 'echo 3 > /proc/sys/vm/drop_caches' 2>/dev/null; then
    BUFF_AFTER=$(free -m | awk '/^Mem:/{print $6}')
    echo "  Buff/Cache: ${BUFF_CACHE} MiB → ${BUFF_AFTER} MiB"
else
    echo "  ⚠ sudo 권한 필요: sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'"
fi

# Step 3: 빌드 캐시 정리
echo ""
echo "[3/5] Docker 빌드 캐시 정리..."
RECLAIMED=$(docker builder prune -f 2>&1 | tail -1)
echo "  ${RECLAIMED}"

# Step 4: 미사용 이미지 정리
echo ""
echo "[4/5] 미사용 Docker 이미지 정리..."
RECLAIMED=$(docker image prune -a -f 2>&1 | tail -1)
echo "  ${RECLAIMED}"

# Step 5: 결과 확인
echo ""
echo "[5/5] 정리 결과..."
FREE_MEM_AFTER=$(free -m | awk '/^Mem:/{print $4}')
echo "  Free Memory: ${FREE_MEM} MiB → ${FREE_MEM_AFTER} MiB"
docker system df
echo ""
echo "=========================================="
echo " Cleanup complete. Ready for testing."
echo "=========================================="
```

---

## 5. 에이전트별 적용 규칙

### 클로드 (Main) — 테스트 위임 전 필수

> **테스트 위임 전에 반드시 사용자에게 `drop_caches` 실행을 요청하세요.**
> 사용자가 실행을 완료한 것을 확인한 후 QA 에이전트에 테스트를 위임하세요.

```
[필수 절차]
1. docker builder prune -f && docker image prune -a -f  ← 클로드가 직접 실행
2. 사용자에게 요청: "테스트 전 캐시 해제가 필요합니다. 실행해주세요:
   sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'"    ← 사용자만 가능
3. 사용자 실행 확인 후 free -h 로 buff/cache < 1 GiB 확인
4. QA 에이전트에 테스트 위임
```

- 메모리 부족 징후(Swap > 50%) 감지 시 즉시 정리 실행

### QA Engineer

- **모든 E2E/UAT/RAGAS 테스트 시작 전** `pre_test_cleanup.sh` 실행 필수
- `drop_caches`는 sudo 필요 → 클로드(Main)을 통해 사용자에게 요청
- 테스트 시작 Slack 알림에 메모리 상태(free -h) 포함

### Infra Engineer

- 컨테이너 리빌드 작업 전 빌드 캐시 정리
- Observability 필수 여부를 테스트 유형에 따라 판단

---

## 6. 주요 메모리 소비 컨테이너 참고

| 컨테이너 | 일반 사용량 | 최대 제한 | 비고 |
|----------|:----------:|:---------:|------|
| kp-ai-service | ~3 GiB | 9 GiB | BGE-M3 임베딩 + Reranker ONNX 모델 상주 |
| kp-elasticsearch | ~1.5 GiB | 2.5 GiB | JVM heap + 42K 청크 인덱스 |
| kp-neo4j | ~800 MiB | 2 GiB | 91K 엔티티 + 746K 관계 그래프 |
| kp-keycloak | ~170 MiB | 640 MiB | 인증 서버 |
| kp-backend | ~150 MiB | 2 GiB | SpringBoot JVM |
| kp-api-gateway | ~140 MiB | 1 GiB | SpringBoot JVM |

**테스트 시 최소 필요 메모리**: ~6 GiB (핵심 서비스만)

---

## 7. drop_caches의 효과 범위와 WSL2 한계

### 검증 결과 (2026-03-09 실측)

`drop_caches` 실행 전후를 WSL2 내부와 Windows 호스트 양쪽에서 측정한 결과:

| 측정 위치 | 항목 | 실행 전 | 실행 후 | 변화 |
|----------|------|---------|---------|------|
| **WSL2 내부** (`free -h`) | buff/cache | 5.6 GiB | 2.4 GiB | **-3.2 GiB 회수** |
| **WSL2 내부** (`free -h`) | free | 707 MiB | 3.2 GiB | **+2.5 GiB 확보** |
| **Windows** (작업 관리자) | 사용 중 | 13.1 GB (83%) | 13.3 GB (85%) | **변화 없음** |
| **Windows** (작업 관리자) | 사용 가능 | 2.6 GB | 2.4 GB | **변화 없음** |

### 원인: WSL2 VM 메모리 반환 불가

```
Windows 물리 메모리: 16.0 GB
├── Windows OS + Docker Desktop        ~2.5 GB
└── WSL2 VM (Hyper-V)                 ~13.0 GB  ← 한번 잡으면 반환 안 함
    ├── Docker 컨테이너 실사용           ~6.0 GB
    ├── buff/cache (Linux 파일 캐시)     ~5.6 GB → drop_caches로 해제 가능
    └── 커널 + Docker 데몬 + 기타        ~1.4 GB
```

- `drop_caches`는 **WSL2 내부에서만** buff/cache를 해제
- WSL2 VM은 해제된 메모리를 **Windows에 반환하지 않음** (Hyper-V VM의 구조적 한계)
- `.wslconfig`의 `autoMemoryReclaim=dropcache`도 컨테이너 실행 중에는 사실상 미작동
- **Windows 메모리를 실제로 회수하는 유일한 방법**: `wsl --shutdown` (전체 재시작 필요)

### 그래서 drop_caches는 의미가 없나?

**아닙니다. WSL2 내부 안정성에는 효과가 있습니다.**

| 효과 | 설명 |
|------|------|
| Swap 압박 감소 | WSL2 내부 free 증가 → Swap 사용 감소 → 컨테이너 OOM 위험 감소 |
| 컨테이너 안정성 | 더 많은 free 메모리 → 테스트 중 피크 메모리 수용 가능 |
| Windows 메모리 | **변화 없음** — 이건 WSL2 구조적 한계 |

### 결론

- **테스트 전 drop_caches**: WSL2 내부 안정화에 유효 → **실행 권장**
- **Windows 메모리 부족 해소**: `wsl --shutdown` 후 재시작 또는 물리 RAM 증설(32GB) 필요
- **현실적 운영**: 16GB 물리 RAM에서 WSL2 14GB 할당 시, Windows에는 항상 2~3GB만 남는 구조적 한계를 인지하고 운영

---

*작성: Claude Code (Opus 4.6) | 2026-03-09*
