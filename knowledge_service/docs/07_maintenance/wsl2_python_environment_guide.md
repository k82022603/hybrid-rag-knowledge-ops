# WSL2 Python 환경 트러블슈팅 가이드

**Version**: 1.0
**Last Updated**: 2026-01-30
**Author**: Claude Code

---

## 1. 개요

### 1.1 문제 상황

WSL2 환경에서 Python venv를 사용할 때 **Windows/Linux 패키지 호환성 문제**가 발생할 수 있습니다.

| 증상 | 원인 |
|------|------|
| `OSError: libtorch_global_deps.so: cannot open shared object file` | Windows용 torch 패키지 |
| `AttributeError: module 'os' has no attribute 'add_dll_directory'` | Windows용 pyarrow 패키지 |
| `ImportError: DLL load failed` | Windows 바이너리 호환성 |

### 1.2 근본 원인

```
┌─────────────────────────────────────────────────────────────┐
│  Windows 환경에서 pip install 실행                           │
│         ↓                                                   │
│  pip이 Windows wheel (.whl) 다운로드                         │
│         ↓                                                   │
│  WSL2 (Linux)에서 실행 시도                                  │
│         ↓                                                   │
│  Linux에서 Windows 바이너리 실행 불가 → 오류 발생            │
└─────────────────────────────────────────────────────────────┘
```

**핵심**: `pip install`은 실행 환경의 OS를 감지하여 적합한 wheel을 다운로드합니다.
- Windows PowerShell에서 실행 → Windows wheel 설치
- WSL2 터미널에서 실행 → Linux wheel 설치

---

## 2. 영향받는 패키지

다음 패키지들은 플랫폼별 네이티브 바이너리를 포함하여 호환성 문제가 자주 발생합니다.

| 패키지 | 문제 증상 | 해결 방법 |
|--------|----------|----------|
| **torch** | `libtorch_global_deps.so` 오류 | CPU 버전 재설치 |
| **pyarrow** | `add_dll_directory` 오류 | 재설치 (Linux wheel) |
| **numpy** | 간헐적 import 오류 | 재설치 |
| **sentence-transformers** | torch 의존성 오류 | torch 먼저 해결 |

---

## 3. 해결 방법

### 3.1 개별 패키지 재설치 (권장)

문제가 발생한 패키지만 Linux용으로 재설치합니다.

```bash
# torch 재설치 (CPU 버전, Linux wheel)
.venv/bin/pip uninstall torch -y
.venv/bin/pip install torch --no-cache-dir --index-url https://download.pytorch.org/whl/cpu

# pyarrow 재설치 (Linux wheel)
.venv/bin/pip uninstall pyarrow -y
.venv/bin/pip install pyarrow --no-cache-dir

# numpy 재설치 (필요시)
.venv/bin/pip uninstall numpy -y
.venv/bin/pip install numpy --no-cache-dir
```

### 3.2 전체 venv 재생성 (최후 수단)

여러 패키지에 문제가 있으면 venv를 재생성합니다.

```bash
cd /mnt/d/Users/KTDS/Documents/06.과제/hybrid-rag-knowledge-ops/knowledge_service

# 기존 venv 백업 (선택사항)
mv .venv .venv.bak

# 새 venv 생성 (WSL2에서 실행)
python3 -m venv .venv

# 의존성 설치
.venv/bin/pip install -e ".[dev]"

# 또는 requirements.txt가 있다면
.venv/bin/pip install -r requirements.txt
```

### 3.3 Docker 환경 사용 (대안)

환경 문제를 완전히 회피하려면 Docker 컨테이너 내에서 테스트를 실행합니다.

```bash
# AI Service 컨테이너에서 테스트 실행
docker-compose exec kp-ai-service pytest src/tests/unit/ -v
```

---

## 4. 예방 방법

### 4.1 일관된 환경 유지

| 규칙 | 설명 |
|------|------|
| **WSL2 터미널에서만 pip 실행** | Windows PowerShell 사용 금지 |
| **`--no-cache-dir` 옵션 사용** | 캐시된 Windows wheel 방지 |
| **venv 경로 확인** | WSL2 경로 (`/mnt/...`) 확인 |

### 4.2 권장 pip 명령어

```bash
# 항상 WSL2 터미널에서 실행
.venv/bin/pip install <package> --no-cache-dir

# torch는 CPU 전용 인덱스 사용 (CUDA 불필요 시)
.venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### 4.3 환경 검증 스크립트

```bash
#!/bin/bash
# verify_env.sh - 환경 검증 스크립트

echo "=== Python 환경 검증 ==="
echo "Python: $(python3 --version)"
echo "Pip: $(.venv/bin/pip --version)"
echo ""

echo "=== 주요 패키지 플랫폼 확인 ==="
.venv/bin/pip show torch 2>/dev/null | grep -E "^(Name|Version|Location)" || echo "torch: Not installed"
.venv/bin/pip show pyarrow 2>/dev/null | grep -E "^(Name|Version|Location)" || echo "pyarrow: Not installed"
echo ""

echo "=== Import 테스트 ==="
.venv/bin/python -c "import torch; print(f'torch {torch.__version__} OK')" 2>/dev/null || echo "torch: Import FAILED"
.venv/bin/python -c "import pyarrow; print(f'pyarrow {pyarrow.__version__} OK')" 2>/dev/null || echo "pyarrow: Import FAILED"
.venv/bin/python -c "import elasticsearch; print(f'elasticsearch OK')" 2>/dev/null || echo "elasticsearch: Import FAILED"
```

---

## 5. 문제 진단

### 5.1 패키지 플랫폼 확인

```bash
# 설치된 wheel 파일 확인
.venv/bin/pip show torch | grep "Location"
# 결과 예: /mnt/d/.../site-packages

# wheel 파일 직접 확인
ls .venv/lib/python3.12/site-packages/torch*.dist-info/WHEEL
cat .venv/lib/python3.12/site-packages/torch*.dist-info/WHEEL | grep Tag
# Linux: Tag: cp312-cp312-manylinux_2_28_x86_64
# Windows: Tag: cp312-cp312-win_amd64
```

### 5.2 오류 메시지별 진단

| 오류 메시지 | 진단 | 해결 |
|------------|------|------|
| `cannot open shared object file` | Linux 공유 라이브러리 누락 | 패키지 재설치 |
| `add_dll_directory` | Windows 전용 함수 호출 | pyarrow 재설치 |
| `DLL load failed` | Windows DLL 로드 시도 | 해당 패키지 재설치 |

---

## 6. 이 프로젝트 적용 사례

### 6.1 2026-01-30 발생 이슈

**상황**: 단위 테스트 실행 시 5개 실패 (elasticsearch 관련)

**원인 분석**:
1. `pyproject.toml`에 elasticsearch 정의됨
2. venv가 Windows/WSL2 혼합 환경으로 생성됨
3. elasticsearch 패키지 미설치 + pyarrow/torch Windows wheel 문제

**해결 과정**:
```bash
# 1. elasticsearch 설치
.venv/bin/pip install "elasticsearch>=8.12.0,<9.0.0"

# 2. pyarrow 재설치 (Linux wheel)
.venv/bin/pip uninstall pyarrow -y
.venv/bin/pip install pyarrow --no-cache-dir

# 3. torch 재설치 (Linux CPU wheel)
.venv/bin/pip uninstall torch -y
.venv/bin/pip install torch --no-cache-dir --index-url https://download.pytorch.org/whl/cpu
```

**결과**: 환경 호환성 문제 해결

---

## 7. 관련 문서

| 문서 | 경로 |
|------|------|
| Docker 트러블슈팅 | `docs/07_maintenance/docker_troubleshooting.md` |
| DeepSeek API 연동 | `docs/07_maintenance/deepseek_api_integration_guide.md` |
| 개발 환경 가이드 | `docs/05_development/development_environment_setup.md` |

---

## 8. 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 1.0 | 2026-01-30 | 최초 작성 - WSL2 환경 호환성 이슈 해결 가이드 |

---

**문서 끝**
