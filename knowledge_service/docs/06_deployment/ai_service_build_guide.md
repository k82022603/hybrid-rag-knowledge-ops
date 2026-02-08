# AI Service BuildKit Build Guide

**DevOps Engineer** | Updated: 2026-02-08

---

## 1. BuildKit Overview

### BuildKit이란

BuildKit은 Docker의 차세대 빌드 엔진으로, 기존 빌드 엔진 대비 다음과 같은 이점을 제공합니다.

| 항목 | 기존 빌드 엔진 | BuildKit |
|------|---------------|----------|
| 빌드 캐시 | 레이어 캐시만 지원 | 레이어 캐시 + 마운트 캐시 |
| 병렬 빌드 | 순차 실행 | 독립 스테이지 병렬 실행 |
| 시크릿 지원 | 없음 | `--mount=type=secret` |
| 캐시 내보내기 | 로컬만 | 레지스트리, S3, GitHub Actions Cache |
| 빌드 출력 | stdout만 | 구조화된 진행 표시 |

### 왜 BuildKit을 사용하는가

ai-service는 PyTorch CPU (~700MB), Docling, LangGraph 등 대용량 Python 패키지를 포함합니다. 일반적인 Docker 레이어 캐시만으로는 `pyproject.toml`이 변경될 때마다 모든 패키지를 처음부터 다시 다운로드해야 합니다. BuildKit의 **캐시 마운트(`--mount=type=cache`)**를 사용하면 pip 다운로드 캐시를 빌드 간에 유지하여, 의존성 변경 시에도 변경된 패키지만 새로 다운로드합니다.

### Docker 29.x에서의 활성화 상태

본 프로젝트의 런타임 환경은 **Docker 29.2.0**입니다. Docker 23.0 이상에서는 BuildKit이 기본 활성화되어 있으므로 별도의 설정 없이 사용할 수 있습니다.

```bash
# 현재 Docker 버전 확인
docker --version
# Docker version 29.2.0, build 0b9d198

# BuildKit 활성화 여부 확인
docker buildx version
# docker buildx는 BuildKit 기반이므로 정상 출력되면 BuildKit 사용 가능
```

만약 BuildKit이 비활성화된 환경이라면 환경변수로 강제 활성화할 수 있습니다.

```bash
export DOCKER_BUILDKIT=1
```

---

## 2. Build Commands

### 2.1 일반 빌드 (권장)

docker-compose를 통해 빌드합니다. 작업 디렉토리는 `infrastructure/docker/`입니다.

```bash
# infrastructure/docker/ 디렉토리에서 실행
cd infrastructure/docker

# ai-service만 빌드
docker compose build ai-service

# 빌드 후 즉시 실행
docker compose up -d --build ai-service
```

### 2.2 캐시를 무시하는 빌드

pip 캐시나 Docker 레이어 캐시가 꼬였다고 판단될 때 사용합니다.

```bash
# Docker 레이어 캐시 무시 (BuildKit 캐시 마운트는 유지)
docker compose build --no-cache ai-service

# BuildKit 캐시 마운트까지 완전히 초기화 후 빌드
docker builder prune --filter type=exec.cachemount -f
docker compose build --no-cache ai-service
```

### 2.3 빌드 로그 상세 확인

BuildKit은 기본적으로 진행 표시줄 형태로 출력합니다. 상세 로그를 보려면 `--progress=plain` 옵션을 사용합니다.

```bash
# 상세 빌드 로그 출력
docker compose build --progress=plain ai-service

# 특정 스테이지의 로그만 확인 (빌드 후)
docker compose build --progress=plain ai-service 2>&1 | grep -A 20 "pip wheel"
```

### 2.4 이미지 크기 확인

```bash
# 빌드된 이미지 크기 확인
docker images | grep ai-service

# 레이어별 크기 분석
docker history knowledge-platform/ai-service:latest
```

---

## 3. Dockerfile 구조 설명

### 3.1 전체 흐름도

```
knowledge_service/Dockerfile
|
+-- syntax=docker/dockerfile:1          # BuildKit 문법 활성화
|
+-- Stage 1: builder (python:3.11-slim)
|   |
|   +-- [Layer 1] System build deps 설치
|   |     gcc, libgl1, libglib2.0-0, libpq-dev, curl
|   |
|   +-- [Layer 2] pip + poetry 설치 (캐시 마운트)
|   |     --mount=type=cache,target=/root/.cache/pip
|   |
|   +-- [Layer 3] pyproject.toml, poetry.lock 복사
|   |     (코드 변경으로 이 레이어가 무효화되지 않음)
|   |
|   +-- [Layer 4] poetry export -> requirements.txt 변환
|   |
|   +-- [Layer 5] PyTorch CPU wheel 사전 빌드 (캐시 마운트)
|   |     pip wheel -> /build/wheels/
|   |
|   +-- [Layer 6] 나머지 의존성 wheel 사전 빌드 (캐시 마운트)
|   |
|   +-- [Layer 7] 추가 패키지 wheel 빌드
|   |     email-validator, python-multipart
|   |
|   +-- [Layer 8] wheel에서 로컬 설치
|   |     pip install --no-index --find-links=/build/wheels/
|   |
|   +-- [Layer 9] Docling 설치 검증
|
+-- Stage 2: runtime (python:3.11-slim)
    |
    +-- [Layer 1] Runtime deps만 설치 (빌드 도구 제외)
    +-- [Layer 2] Non-root 사용자 생성 (appuser:1001)
    +-- [Layer 3] builder에서 site-packages 복사
    +-- [Layer 4] 소스 코드 복사 (src/, pyproject.toml)
    +-- [Layer 5] 디렉토리 생성 + 권한 설정
    +-- Health check + CMD
```

### 3.2 Multi-stage Build 원리

Dockerfile은 두 개의 스테이지로 구성됩니다.

**Stage 1: builder** - 의존성을 빌드하고 설치하는 스테이지입니다. gcc, build-essential 같은 빌드 도구가 포함되지만 최종 이미지에는 포함되지 않습니다.

**Stage 2: runtime** - 실제 배포되는 이미지입니다. builder에서 설치된 Python 패키지(`site-packages`)와 실행 파일(`/usr/local/bin`)만 복사하여 이미지 크기를 최소화합니다.

```dockerfile
# builder 스테이지에서 설치된 패키지를 runtime으로 복사
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
```

이 방식으로 빌드 도구 없이 약 2GB 이상의 이미지 크기 절감 효과를 얻습니다.

### 3.3 BuildKit 캐시 마운트 (`--mount=type=cache`)

캐시 마운트는 BuildKit의 핵심 기능입니다. 일반적인 Docker 빌드에서는 각 `RUN` 명령이 독립적인 레이어를 생성하고, 이전 레이어가 무효화되면 이후 모든 레이어를 다시 실행합니다. 캐시 마운트는 이와 별개로 **빌드 간에 공유되는 디렉토리**를 제공합니다.

```dockerfile
# pip의 다운로드 캐시를 빌드 간에 유지
RUN --mount=type=cache,target=/root/.cache/pip \
    pip wheel --wheel-dir=/build/wheels \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    torch==2.5.1+cpu
```

**동작 원리:**

1. `--mount=type=cache,target=/root/.cache/pip` 는 빌드 시 `/root/.cache/pip` 디렉토리를 BuildKit의 캐시 스토리지에 연결합니다.
2. pip가 패키지를 다운로드하면 `/root/.cache/pip`에 캐시 파일이 저장됩니다.
3. 다음 빌드 시 같은 캐시 마운트를 사용하므로, 이미 다운로드된 패키지는 네트워크 요청 없이 캐시에서 가져옵니다.
4. **이 캐시는 Docker 레이어 캐시와 독립적**이므로, `pyproject.toml`이 변경되어 레이어가 무효화되더라도 pip 다운로드 캐시는 그대로 남아있습니다.

**일반 Docker 캐시와의 차이:**

| 구분 | Docker 레이어 캐시 | BuildKit 캐시 마운트 |
|------|-------------------|---------------------|
| 무효화 조건 | 이전 레이어 변경 시 모두 무효화 | 독립적, 명시적 삭제 전까지 유지 |
| 저장 위치 | Docker 이미지 레이어 | BuildKit 전용 캐시 스토리지 |
| 최종 이미지 포함 | 레이어로 포함 | 포함되지 않음 (빌드 시에만 사용) |
| 활용 예 | `COPY`, `RUN` 결과 | pip cache, apt cache, npm cache |

### 3.4 pip wheel 사전 빌드 + 로컬 설치 흐름

Dockerfile은 2단계 설치 전략을 사용합니다.

**1단계: wheel 파일 사전 빌드**

```dockerfile
# PyTorch CPU wheel을 /build/wheels/ 디렉토리에 빌드
RUN --mount=type=cache,target=/root/.cache/pip \
    pip wheel --wheel-dir=/build/wheels \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    torch==2.5.1+cpu

# 나머지 의존성 wheel도 같은 디렉토리에 빌드
RUN --mount=type=cache,target=/root/.cache/pip \
    pip wheel --wheel-dir=/build/wheels \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements.txt
```

`pip wheel` 명령은 패키지를 설치하지 않고, `.whl` 파일(사전 컴파일된 패키지)만 생성합니다. 캐시 마운트 덕분에 이미 다운로드된 패키지 소스는 재다운로드하지 않습니다.

**2단계: 로컬 wheel에서 설치**

```dockerfile
RUN pip install --no-index --find-links=/build/wheels \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    torch==2.5.1+cpu && \
    pip install --no-index --find-links=/build/wheels \
    -r requirements.txt
```

- `--no-index`: PyPI에서 패키지를 검색하지 않음 (네트워크 요청 없음)
- `--find-links=/build/wheels`: 미리 빌드한 wheel 디렉토리에서만 패키지를 찾음

이 방식의 장점은 **설치 단계에서 네트워크를 사용하지 않는다**는 점입니다. 모든 다운로드는 wheel 빌드 단계에서 캐시 마운트와 함께 처리되므로, 빌드의 재현성과 속도가 모두 향상됩니다.

---

## 4. Build Time Reference

### 4.1 시나리오별 빌드 시간

테스트 환경: WSL2, Docker 29.2.0, 8 vCPU, 16GB RAM

| 시나리오 | 예상 시간 | 캐시 활용 | 설명 |
|---------|----------|----------|------|
| 첫 빌드 (캐시 없음) | ~10분 | 없음 | 모든 패키지 다운로드 + wheel 빌드 |
| 소스 코드만 변경 | ~1-2분 | Docker 레이어 캐시 | `COPY src/` 이후 레이어만 재실행 |
| pyproject.toml 변경 | ~3-5분 | BuildKit 캐시 마운트 | pip 다운로드 캐시 활용, 변경분만 다운로드 |
| 시스템 deps 변경 | ~8-10분 | BuildKit 캐시 마운트 | apt 레이어부터 재빌드, pip 캐시는 유지 |
| `--no-cache` 빌드 | ~10분 | BuildKit 캐시 마운트만 | Docker 레이어 무시, pip 캐시는 유지 |
| 완전 초기화 빌드 | ~10분+ | 없음 | `docker builder prune` 후 빌드 |

### 4.2 캐시 효과가 큰 이유

ai-service의 Python 의존성 구성은 다음과 같습니다.

| 패키지 그룹 | 크기 (다운로드) | 변경 빈도 |
|------------|----------------|----------|
| PyTorch CPU | ~700MB | 거의 없음 |
| Docling + 관련 | ~500MB | 드물게 |
| LangChain/LangGraph | ~100MB | 가끔 |
| FastAPI/Uvicorn | ~30MB | 드물게 |
| 기타 (DB, 유틸) | ~200MB | 가끔 |

전체 ~1.5GB 중 PyTorch와 Docling만으로 ~1.2GB를 차지합니다. 이 패키지들은 거의 변경되지 않으므로, 캐시 마운트를 통해 대부분의 빌드에서 다운로드를 건너뛸 수 있습니다.

### 4.3 빌드 시간 최적화 팁

**의존성 관련 파일과 소스 코드를 분리하여 COPY합니다.**

```dockerfile
# 의존성 파일 먼저 (변경 빈도 낮음)
COPY pyproject.toml poetry.lock* ./

# ... 의존성 설치 ...

# 소스 코드는 마지막에 (변경 빈도 높음)
COPY src/ /app/src/
```

이 순서 덕분에 소스 코드만 변경했을 때 의존성 설치 레이어를 재사용할 수 있습니다.

---

## 5. Troubleshooting

### 5.1 캐시가 꼬였을 때

**증상**: 패키지 버전 충돌, 이전 버전이 설치되는 현상, 빌드는 성공하나 런타임 에러 발생

```bash
# BuildKit 캐시 마운트만 정리
docker builder prune --filter type=exec.cachemount -f

# 전체 BuildKit 캐시 정리 (더 넓은 범위)
docker builder prune -a -f

# 정리 후 빌드
docker compose build --no-cache ai-service
```

**참고**: `docker builder prune -a -f`는 모든 BuildKit 캐시를 삭제합니다. ai-service뿐 아니라 다른 서비스의 캐시도 삭제되므로 주의해야 합니다.

### 5.2 BuildKit 활성화 확인

**증상**: `--mount=type=cache` 구문에서 빌드 에러 발생

```bash
# BuildKit 활성화 확인
docker info 2>/dev/null | grep -i buildkit
# 출력에 "buildkit" 관련 항목이 있으면 활성화 상태

# 명시적 활성화
export DOCKER_BUILDKIT=1

# Docker 데몬 설정으로 영구 활성화
# /etc/docker/daemon.json에 추가:
# { "features": { "buildkit": true } }
```

Docker 23.0 이상이면 BuildKit이 기본 활성화입니다. 본 프로젝트의 Docker 29.2.0에서는 별도 설정이 필요하지 않습니다.

### 5.3 Dockerfile 첫 줄의 `# syntax=docker/dockerfile:1`

```dockerfile
# syntax=docker/dockerfile:1
```

이 줄은 BuildKit에게 사용할 프론트엔드 파서를 지정합니다. 이를 통해 `--mount=type=cache` 같은 확장 구문을 사용할 수 있습니다. **이 줄은 반드시 Dockerfile의 첫 번째 줄이어야 합니다.** 빈 줄이나 주석이 앞에 있으면 무시됩니다.

### 5.4 WSL2 환경 특이사항

**파일 시스템 성능**

WSL2에서 Windows 파일 시스템(`/mnt/c/`, `/mnt/d/`)에 접근하면 I/O 성능이 크게 저하됩니다. Docker 빌드 컨텍스트가 Windows 경로에 있으므로 `COPY` 명령 시 다소 느릴 수 있습니다. 이는 정상적인 동작입니다.

```
# 빌드 컨텍스트 경로 (docker-compose.yml 기준)
context: ../../knowledge_service    # Windows FS 경로
```

**메모리 사용량**

WSL2에서 Docker를 사용하면 Linux VM이 별도 메모리를 점유합니다. ai-service 빌드 시 pip wheel 단계에서 최대 4-6GB 메모리를 사용할 수 있으므로, WSL2 메모리 제한을 충분히 설정해야 합니다.

```
# %USERPROFILE%/.wslconfig
[wsl2]
memory=16GB
swap=4GB
```

**Volume 마운트**

docker-compose.yml에서 ai-service는 HuggingFace 모델 캐시를 호스트에서 마운트합니다.

```yaml
volumes:
  # BGE-M3 임베딩 모델 캐시 (6.4GB, 다운로드 없이 로컬 사용)
  - /home/claude/.cache/huggingface:/app/.cache/huggingface:ro
```

이 마운트는 빌드가 아닌 런타임에 적용됩니다. 빌드에는 영향을 주지 않지만, 컨테이너 실행 시 해당 경로에 모델 파일이 없으면 런타임에 모델 다운로드가 발생합니다.

### 5.5 빌드 실패 시 진단 순서

```
1. 에러 메시지 확인
   docker compose build --progress=plain ai-service 2>&1 | tail -50

2. BuildKit 활성화 확인
   docker info | grep -i buildkit

3. 디스크 공간 확인
   docker system df
   df -h

4. 네트워크 확인 (PyPI, PyTorch 인덱스 접근)
   curl -s https://pypi.org/simple/ > /dev/null && echo "PyPI OK"
   curl -s https://download.pytorch.org/whl/cpu/ > /dev/null && echo "PyTorch OK"

5. 캐시 정리 후 재시도
   docker builder prune -a -f
   docker compose build --no-cache ai-service
```

### 5.6 자주 발생하는 에러

**poetry lock 실패**

```
Error: poetry lock failed
```

```bash
# 해결: knowledge_service에서 poetry lock 재실행
cd knowledge_service
source .venv/bin/activate
poetry lock
```

**PyTorch CPU wheel을 찾을 수 없음**

```
ERROR: Could not find a version that satisfies the requirement torch==2.5.1+cpu
```

원인: `--extra-index-url https://download.pytorch.org/whl/cpu`가 누락되었거나 네트워크 문제. PyTorch 공식 CPU 인덱스 URL에 접근 가능한지 확인합니다.

**디스크 공간 부족**

```
Error: no space left on device
```

```bash
# Docker 미사용 리소스 정리
docker system prune -a --volumes -f

# WSL2 vdisk 축소 (Windows PowerShell에서)
wsl --shutdown
# Optimize-VHD -Path "$env:LOCALAPPDATA\Packages\...\ext4.vhdx" -Mode Full
```

---

## 6. Quick Reference

### 일상적 빌드 (코드 변경 후)

```bash
cd infrastructure/docker
docker compose build ai-service && docker compose up -d ai-service
```

### 의존성 변경 후 빌드

```bash
cd knowledge_service
poetry lock
cd ../infrastructure/docker
docker compose build ai-service && docker compose up -d ai-service
```

### 문제 발생 시 클린 빌드

```bash
docker builder prune --filter type=exec.cachemount -f
cd infrastructure/docker
docker compose build --no-cache ai-service
```

### 빌드 결과 검증

```bash
# Docling 임포트 확인
docker compose run --rm ai-service python -c "import docling; print(f'Docling {docling.__version__}')"

# PyTorch CPU 확인
docker compose run --rm ai-service python -c "import torch; print(f'PyTorch {torch.__version__}, CUDA: {torch.cuda.is_available()}')"

# 헬스체크
curl -s http://localhost:8000/api/v1/health
```

---

## Related Files

| File | Description |
|------|-------------|
| `knowledge_service/Dockerfile` | BuildKit 최적화 적용된 Production Dockerfile |
| `infrastructure/docker/docker-compose.yml` | ai-service 서비스 정의 (302-385행) |
| `knowledge_service/pyproject.toml` | Python 의존성 선언 |
| `knowledge_service/poetry.lock` | 의존성 버전 잠금 파일 |
| `knowledge_service/docs/06_deployment/docling_docker_setup.md` | Docling Docker 통합 가이드 (STORY-063) |

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-02-08 | BuildKit 캐시 마운트 빌드 가이드 초판 작성 | DevOps Engineer |
