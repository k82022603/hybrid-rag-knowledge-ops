# BGE-M3 임베딩 모델 설치 및 테스트 가이드

**STORY-004** | **Version**: 1.0 | **Updated**: 2026-01-27

---

## 1. 현황 요약

| 항목 | 상태 |
|------|------|
| EmbeddingService 구현 | 855줄, 완료 |
| 단위 테스트 (mock) | 68/68 통과 |
| 실제 모델 로드 테스트 | **미완료** |
| 1024차원 벡터 생성 검증 | **미완료** |
| 원인 | WSL2 환경에서 PyTorch `.so` 로딩 실패 |

### 실패 근본 원인

```
OSError: libtorch_global_deps.so: cannot open shared object file: No such file or directory
```

**원인**: venv이 Windows NTFS 마운트(`/mnt/d/`, 9p 프로토콜)에 있어서
pip이 **Windows용 PyTorch** (`.dll`)를 설치함. Linux에서 `.so`를 찾으므로 실패.

```
확인된 파일 (Windows 바이너리):
  torch.dll, c10.dll, torch_cpu.dll, libiomp5md.dll

필요한 파일 (Linux 바이너리):
  libtorch_global_deps.so, libtorch.so, libc10.so  ← 미존재
```

---

## 2. 해결 방법 (3가지)

### 방법 A: Linux 네이티브 파일시스템에서 venv 재생성 (권장)

WSL2 내부 파일시스템(`/home/`)에 venv을 만들면 pip이 Linux용 패키지를 설치합니다.

```bash
# 1. Linux 네이티브 경로에 venv 생성
cd ~
python3 -m venv ~/embedding-venv

# 2. 활성화
source ~/embedding-venv/bin/activate

# 3. 핵심 의존성 설치 (CPU 전용 torch 권장, ~300MB vs GPU ~2GB)
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install FlagEmbedding sentence-transformers

# 4. 검증
python -c "import torch; print(f'PyTorch {torch.__version__} loaded on {torch.device(\"cpu\")}')"
```

**장점**: 가장 빠르고 간단
**단점**: 프로젝트 venv과 별도 관리 필요

### 방법 B: Docker 컨테이너에서 테스트

프로젝트의 `ai-service` Docker 컨테이너를 활용합니다.

```bash
# 1. 간단한 테스트 컨테이너 실행
docker run -it --rm \
  -v $(pwd)/knowledge_service/src:/app/src \
  python:3.12-slim bash

# 2. 컨테이너 내부에서 설치
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install FlagEmbedding sentence-transformers numpy

# 3. 테스트 실행
cd /app && python -c "
from src.app.services.embedding import EmbeddingService
svc = EmbeddingService()
vec = svc.embed('Knowledge Graph 기반 검색 시스템')
print(f'차원: {len(vec)}, 앞 5개: {vec[:5]}')
"
```

**장점**: 프로젝트 환경 안건드림, 격리된 환경
**단점**: Docker 실행 필요, 컨테이너마다 모델 다운로드

### 방법 C: 기존 venv에서 torch 재설치 (실험적)

```bash
cd /mnt/d/Users/KTDS/Documents/06.과제/hybrid-rag-knowledge-ops/knowledge_service

# 1. 기존 torch 제거
.venv/bin/pip uninstall torch -y

# 2. Linux CPU 전용 wheel로 강제 재설치
.venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cpu \
  --platform manylinux2014_x86_64 --only-binary=:all: --target .venv/lib/python3.12/site-packages/

# 3. 검증
.venv/bin/python -c "import torch; print(torch.__version__)"
```

**장점**: 기존 venv 유지
**단점**: `--platform` + `--target` 조합이 의존성 충돌 가능, NTFS I/O 성능 저하

---

## 3. 모델 다운로드 정보

| 모델 | HuggingFace ID | 크기 | 용도 |
|------|----------------|------|------|
| BGE-M3 | `BAAI/bge-m3` | ~1.5GB | Dense(1024d) + Sparse 임베딩 |
| BGE-Reranker-v2-M3 | `BAAI/bge-reranker-v2-m3` | ~1.1GB | 재순위화 (STORY-032) |

### 다운로드 방법

```bash
# 방법 1: 첫 사용 시 자동 다운로드 (HuggingFace Hub)
# EmbeddingService()가 model.encode() 호출 시 자동

# 방법 2: 사전 다운로드 (오프라인 환경용)
pip install huggingface_hub
huggingface-cli download BAAI/bge-m3 --local-dir ./models/bge-m3

# 방법 3: Python에서 직접 다운로드
from huggingface_hub import snapshot_download
snapshot_download("BAAI/bge-m3", local_dir="./models/bge-m3")
```

### 모델 캐시 경로

```
~/.cache/huggingface/hub/models--BAAI--bge-m3/
├── blobs/           # 모델 가중치 (큰 파일)
├── refs/
└── snapshots/
    └── <commit-hash>/
        ├── config.json
        ├── model.safetensors   # ~1.2GB
        ├── tokenizer.json
        └── ...
```

---

## 4. 검증 테스트 스크립트

### 4.1 기본 검증 (1024차원 벡터 생성)

```python
#!/usr/bin/env python3
"""BGE-M3 임베딩 모델 기본 검증 스크립트"""

import sys
import time

def test_basic_embedding():
    """1024차원 Dense 벡터 정상 생성 확인"""
    print("=" * 60)
    print("BGE-M3 Embedding Model - Basic Verification")
    print("=" * 60)

    # Step 1: PyTorch 로드
    print("\n[1/5] PyTorch 로드...")
    try:
        import torch
        print(f"  OK: PyTorch {torch.__version__}")
        print(f"  Device: {torch.device('cpu')}")
        print(f"  CUDA: {'Yes' if torch.cuda.is_available() else 'No (CPU mode)'}")
    except Exception as e:
        print(f"  FAIL: {e}")
        return False

    # Step 2: 모델 로드 (FlagEmbedding 우선)
    print("\n[2/5] BGE-M3 모델 로드...")
    model = None
    model_type = None
    load_start = time.time()

    try:
        from FlagEmbedding import BGEM3FlagModel
        model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=False, device="cpu")
        model_type = "FlagEmbedding"
    except ImportError:
        print("  FlagEmbedding 미설치, sentence-transformers로 폴백...")
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("BAAI/bge-m3", device="cpu")
        model_type = "sentence-transformers"

    load_time = time.time() - load_start
    print(f"  OK: {model_type} 로드 완료 ({load_time:.1f}s)")

    # Step 3: 단일 텍스트 임베딩
    print("\n[3/5] 단일 텍스트 임베딩 생성...")
    test_text = "Knowledge Graph 기반 하이브리드 RAG 검색 시스템의 아키텍처를 설명합니다."
    embed_start = time.time()

    if model_type == "FlagEmbedding":
        result = model.encode([test_text], return_dense=True, return_sparse=False, return_colbert_vecs=False)
        vector = result["dense_vecs"][0].tolist()
    else:
        vector = model.encode([test_text], normalize_embeddings=True)[0].tolist()

    embed_time = time.time() - embed_start
    dim = len(vector)
    print(f"  차원: {dim} {'(OK)' if dim == 1024 else '(UNEXPECTED!)'}")
    print(f"  앞 5개 값: {vector[:5]}")
    print(f"  소요 시간: {embed_time:.3f}s")

    assert dim == 1024, f"Expected 1024, got {dim}"

    # Step 4: 한국어/영어 다국어 테스트
    print("\n[4/5] 다국어 임베딩 테스트...")
    multilingual_texts = [
        "한국어 문서 검색 시스템",
        "English document search system",
        "Knowledge Graph와 Vector Search의 하이브리드 접근",
    ]

    if model_type == "FlagEmbedding":
        result = model.encode(multilingual_texts, return_dense=True, return_sparse=False, return_colbert_vecs=False)
        vectors = result["dense_vecs"].tolist()
    else:
        vectors = model.encode(multilingual_texts, normalize_embeddings=True).tolist()

    for i, (text, vec) in enumerate(zip(multilingual_texts, vectors)):
        print(f"  [{i+1}] '{text[:30]}...' → dim={len(vec)}")

    # 코사인 유사도 (한국어-영어 같은 의미 → 높아야 함)
    import math
    def cosine_sim(a, b):
        dot = sum(x*y for x,y in zip(a,b))
        na = math.sqrt(sum(x*x for x in a))
        nb = math.sqrt(sum(x*x for x in b))
        return dot / (na * nb) if na > 0 and nb > 0 else 0

    sim_ko_en = cosine_sim(vectors[0], vectors[1])
    sim_ko_hybrid = cosine_sim(vectors[0], vectors[2])
    print(f"  한국어↔영어 유사도: {sim_ko_en:.4f} (같은 의미 → 0.7+ 기대)")
    print(f"  한국어↔하이브리드 유사도: {sim_ko_hybrid:.4f}")

    # Step 5: 배치 성능
    print("\n[5/5] 배치 처리 성능...")
    batch_texts = [f"테스트 문서 {i}" for i in range(32)]
    batch_start = time.time()

    if model_type == "FlagEmbedding":
        result = model.encode(batch_texts, batch_size=16, return_dense=True, return_sparse=False, return_colbert_vecs=False)
        batch_vecs = result["dense_vecs"]
    else:
        batch_vecs = model.encode(batch_texts, batch_size=16, normalize_embeddings=True)

    batch_time = time.time() - batch_start
    print(f"  32건 배치: {batch_time:.3f}s ({32/batch_time:.1f} texts/s)")
    print(f"  출력 shape: ({len(batch_vecs)}, {len(batch_vecs[0])})")

    # 결과 요약
    print("\n" + "=" * 60)
    print("RESULT: ALL PASSED")
    print(f"  Model: {model_type} (BAAI/bge-m3)")
    print(f"  Dimension: {dim}")
    print(f"  Load time: {load_time:.1f}s")
    print(f"  Single embed: {embed_time:.3f}s")
    print(f"  Batch (32): {batch_time:.3f}s")
    print(f"  Multilingual: ko↔en sim={sim_ko_en:.4f}")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_basic_embedding()
    sys.exit(0 if success else 1)
```

### 4.2 EmbeddingService 통합 검증

```python
#!/usr/bin/env python3
"""EmbeddingService 통합 검증 (STORY-004 완료 기준)"""

import sys
sys.path.insert(0, "src")

def test_embedding_service_integration():
    """EmbeddingService를 통한 전체 파이프라인 검증"""
    from app.services.embedding import EmbeddingService, ChunkEmbedding

    print("EmbeddingService Integration Test")
    print("-" * 40)

    # 1. 서비스 초기화
    svc = EmbeddingService()
    print(f"[1] 서비스 초기화: OK (model={svc.model_name})")

    # 2. 단일 임베딩
    vec = svc.embed("테스트 문서입니다")
    assert len(vec) == 1024
    print(f"[2] 단일 임베딩: OK (dim={len(vec)})")

    # 3. 배치 임베딩
    texts = ["문서 A", "문서 B", "문서 C"]
    vecs = svc.embed_batch(texts)
    assert len(vecs) == 3
    assert all(len(v) == 1024 for v in vecs)
    print(f"[3] 배치 임베딩: OK ({len(vecs)}건, dim={len(vecs[0])})")

    # 4. Sparse 임베딩 (FlagEmbedding만 지원)
    dense, sparse = svc.embed_batch(texts, return_sparse=True)
    print(f"[4] Sparse 임베딩: OK (dense={len(dense)}, sparse={len(sparse)})")

    # 5. 청크 임베딩
    chunk_ids = ["chunk_001", "chunk_002"]
    chunk_texts = ["청크 내용 1", "청크 내용 2"]
    results = svc.embed_chunks(chunk_ids, chunk_texts)
    assert len(results) == 2
    assert all(isinstance(r, ChunkEmbedding) for r in results)
    assert results[0].chunk_id == "chunk_001"
    assert len(results[0].dense_vector) == 1024
    print(f"[5] 청크 임베딩: OK ({len(results)}건)")

    # 6. 비동기 임베딩
    import asyncio
    async def async_test():
        vec = await svc.aembed("비동기 테스트")
        return len(vec)
    dim = asyncio.run(async_test())
    assert dim == 1024
    print(f"[6] 비동기 임베딩: OK (dim={dim})")

    # 7. L2 정규화 검증
    import math
    norm = math.sqrt(sum(x*x for x in vec))
    print(f"[7] L2 정규화: norm={norm:.6f} {'(OK)' if abs(norm - 1.0) < 0.01 else '(WARN)'}")

    print("\n=== ALL 7 CHECKS PASSED ===")
    return True

if __name__ == "__main__":
    success = test_embedding_service_integration()
    sys.exit(0 if success else 1)
```

---

## 5. 실행 절차 (Step by Step)

### 5.1 빠른 검증 (방법 A: Linux venv)

```bash
# 1. Linux venv 생성 (~1분)
python3 -m venv ~/embedding-test
source ~/embedding-test/bin/activate

# 2. 의존성 설치 (~5분, 네트워크 속도에 따라)
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install FlagEmbedding sentence-transformers numpy

# 3. 프로젝트 경로 설정
export PYTHONPATH=/mnt/d/Users/KTDS/Documents/06.과제/hybrid-rag-knowledge-ops/knowledge_service/src

# 4. 기본 검증 스크립트 실행 (첫 실행 시 모델 다운로드 ~1.5GB)
python /mnt/d/Users/KTDS/Documents/06.과제/hybrid-rag-knowledge-ops/knowledge_service/scripts/test_embedding_basic.py

# 5. EmbeddingService 통합 검증
python /mnt/d/Users/KTDS/Documents/06.과제/hybrid-rag-knowledge-ops/knowledge_service/scripts/test_embedding_integration.py

# 6. 정리
deactivate
```

### 5.2 Docker 검증 (방법 B)

```bash
# 1. 테스트 컨테이너 빌드 및 실행
docker run -it --rm \
  -v /mnt/d/Users/KTDS/Documents/06.과제/hybrid-rag-knowledge-ops/knowledge_service:/app \
  -w /app \
  python:3.12-slim bash -c "
    pip install torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install FlagEmbedding sentence-transformers numpy && \
    PYTHONPATH=src python scripts/test_embedding_basic.py
  "
```

---

## 6. 기대 결과

### 정상 출력 예시

```
==============================================================
BGE-M3 Embedding Model - Basic Verification
==============================================================

[1/5] PyTorch 로드...
  OK: PyTorch 2.x.x
  Device: cpu
  CUDA: No (CPU mode)

[2/5] BGE-M3 모델 로드...
  OK: FlagEmbedding 로드 완료 (15.3s)

[3/5] 단일 텍스트 임베딩 생성...
  차원: 1024 (OK)
  앞 5개 값: [0.0234, -0.0156, 0.0089, ...]
  소요 시간: 0.045s

[4/5] 다국어 임베딩 테스트...
  [1] '한국어 문서 검색 시스템...' → dim=1024
  [2] 'English document search ...' → dim=1024
  [3] 'Knowledge Graph와 Vector...' → dim=1024
  한국어↔영어 유사도: 0.8234 (같은 의미 → 0.7+ 기대)
  한국어↔하이브리드 유사도: 0.8567

[5/5] 배치 처리 성능...
  32건 배치: 0.892s (35.9 texts/s)
  출력 shape: (32, 1024)

==============================================================
RESULT: ALL PASSED
==============================================================
```

---

## 7. 성능 기준 (Acceptance Criteria)

| 항목 | 기준 | 비고 |
|------|------|------|
| Dense 벡터 차원 | **1024** | BGE-M3 기본 출력 |
| L2 정규화 | norm ~= 1.0 | `normalize=True` |
| 모델 로드 시간 | < 30s (CPU) | 첫 로드, 이후 캐시 |
| 단일 임베딩 | < 0.1s | CPU 기준 |
| 배치 (32건) | < 2s | CPU 기준 |
| 한국어↔영어 유사도 | > 0.7 | 같은 의미 기준 |
| Sparse 벡터 | dict{token_id: weight} | FlagEmbedding만 |

---

## 8. 트러블슈팅

### 문제 1: `libtorch_global_deps.so` 로딩 실패

```
OSError: libtorch_global_deps.so: cannot open shared object file
```

**원인**: Windows 마운트(`/mnt/d/`)에서 pip이 Windows용 torch 설치
**해결**: 위 Section 2 방법 A 또는 B 사용

### 문제 2: 모델 다운로드 실패

```
ConnectionError: Cannot reach huggingface.co
```

**해결**:
```bash
# 미러 사용
export HF_ENDPOINT=https://hf-mirror.com
# 또는 프록시
export HTTPS_PROXY=http://proxy:port
```

### 문제 3: OOM (Out of Memory)

```
RuntimeError: [enforce fail at alloc.cpp] DefaultCPUAllocator: not enough memory
```

**해결**:
```bash
# batch_size 줄이기
export EMBEDDING_BATCH_SIZE=4  # 기본 16 → 4

# 또는 코드에서
svc = EmbeddingService()
svc.batch_size = 4
```

### 문제 4: FlagEmbedding 설치 실패

```
error: Microsoft Visual C++ 14.0 is required
```

**해결**:
```bash
# FlagEmbedding 없이 sentence-transformers만 사용 (자동 폴백)
pip install sentence-transformers
# Sparse 임베딩은 불가, Dense만 지원
```

---

## 9. 관련 파일

| 파일 | 역할 |
|------|------|
| `src/app/services/embedding.py` | EmbeddingService 메인 코드 (855줄) |
| `src/app/core/config.py` | 임베딩 관련 설정 (model_name, batch_size 등) |
| `src/app/core/exceptions.py` | EmbeddingError, EmbeddingModelLoadError |
| `src/tests/unit/test_embedding_service.py` | 단위 테스트 (68개, mock 기반) |
| `pyproject.toml` | 의존성 정의 (torch, FlagEmbedding, sentence-transformers) |

---

## 10. 환경별 설정

### 개발 환경 (WSL2)

```env
# .env
EMBEDDING_MODEL_NAME=BAAI/bge-m3
EMBEDDING_DEVICE=cpu
EMBEDDING_BATCH_SIZE=16
EMBEDDING_MAX_LENGTH=8192
EMBEDDING_USE_FP16=false
EMBEDDING_NORMALIZE=true
EMBEDDING_DIMENSION=1024
```

### Docker 컨테이너 (ai-service)

```yaml
# docker-compose.yml
ai-service:
  environment:
    - EMBEDDING_MODEL_NAME=BAAI/bge-m3
    - EMBEDDING_DEVICE=cpu
    - EMBEDDING_BATCH_SIZE=16
    - HF_HOME=/app/models  # 모델 캐시 경로
  volumes:
    - ai-models:/app/models  # 모델 영속 저장
```

### GPU 환경 (향후)

```env
EMBEDDING_DEVICE=cuda
EMBEDDING_USE_FP16=true
EMBEDDING_BATCH_SIZE=64
```

---

## 변경 이력

| 날짜 | 버전 | 내용 |
|------|------|------|
| 2026-01-27 | 1.0 | 초기 작성 - 설치 가이드, 테스트 스크립트, 트러블슈팅 |
