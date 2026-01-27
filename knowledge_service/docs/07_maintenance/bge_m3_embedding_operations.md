# BGE-M3 임베딩 모델 운영 매뉴얼

**Version**: 1.0 | **Updated**: 2026-01-27

---

## 목차

1. [서비스 개요](#1-서비스-개요)
2. [환경 설정](#2-환경-설정)
3. [모델 관리](#3-모델-관리)
4. [서비스 기동 및 상태 확인](#4-서비스-기동-및-상태-확인)
5. [캐시 운영 (Redis)](#5-캐시-운영-redis)
6. [성능 모니터링](#6-성능-모니터링)
7. [트러블슈팅](#7-트러블슈팅)
8. [백업 및 복구](#8-백업-및-복구)
9. [운영 체크리스트](#9-운영-체크리스트)

---

## 1. 서비스 개요

### 1.1 아키텍처

```
┌──────────────────────────────────────────────────────────┐
│  EmbeddingService (Singleton)                            │
│                                                          │
│  ┌─────────────┐    ┌──────────────┐    ┌────────────┐  │
│  │ API Layer   │───>│ Cache Layer  │───>│ Model Layer│  │
│  │ embed()     │    │ (Redis)      │    │ BGE-M3     │  │
│  │ embed_batch │    │ Hit → Return │    │ 1024d 벡터 │  │
│  │ embed_chunks│    │ Miss → Model │    │ Dense +    │  │
│  │ aembed()    │    │              │    │ Sparse     │  │
│  └─────────────┘    └──────────────┘    └────────────┘  │
└──────────────────────────────────────────────────────────┘
```

### 1.2 핵심 사양

| 항목 | 값 |
|------|-----|
| 모델 | `BAAI/bge-m3` (HuggingFace) |
| 벡터 차원 | 1024 (Dense) |
| 지원 언어 | 100+ 언어 (한국어/영어 포함) |
| 최대 토큰 | 8192 tokens |
| 모델 크기 | ~1.5GB (디스크) |
| 구현 파일 | `src/app/services/embedding.py` (855줄) |
| 싱글턴 | `get_embedding_service()` 함수로 전역 인스턴스 관리 |

### 1.3 모델 로딩 전략 (2단계 폴백)

```
1차 시도: FlagEmbedding (BGEM3FlagModel)
 ├─ Dense + Sparse 벡터 동시 지원
 ├─ BGE-M3에 최적화된 라이브러리
 └─ 실패 시 → 2차 시도

2차 시도: sentence-transformers (SentenceTransformer)
 ├─ Dense 벡터만 지원 (Sparse는 빈 dict 반환)
 ├─ 범용 Transformer 라이브러리
 └─ 실패 시 → EmbeddingModelLoadError 발생
```

---

## 2. 환경 설정

### 2.1 필수 환경 변수

| 변수명 | 기본값 | 설명 |
|--------|--------|------|
| `EMBEDDING_MODEL` | `BAAI/bge-m3` | HuggingFace 모델 ID |
| `EMBEDDING_DIMENSION` | `1024` | 출력 벡터 차원 (고정) |
| `EMBEDDING_DEVICE` | `None` (자동감지) | `cpu` / `cuda` / `None` |
| `EMBEDDING_BATCH_SIZE` | `32` | 배치 처리 단위 |
| `EMBEDDING_MAX_LENGTH` | `8192` | 최대 토큰 길이 |
| `EMBEDDING_USE_FP16` | `true` | GPU에서 FP16 사용 (CPU 시 자동 비활성화) |
| `EMBEDDING_NORMALIZE` | `true` | L2 정규화 적용 |

### 2.2 Redis 캐시 환경 변수

| 변수명 | 기본값 | 설명 |
|--------|--------|------|
| `REDIS_HOST` | `localhost` | Redis 호스트 |
| `REDIS_PORT` | `6379` | Redis 포트 |
| `REDIS_PASSWORD` | `None` | Redis 인증 비밀번호 |
| `REDIS_DB` | `0` | Redis DB 인덱스 |
| `REDIS_EMBEDDING_CACHE_TTL` | `604800` (7일) | 캐시 유효 기간 (초) |

### 2.3 환경별 설정 예시

**개발 환경 (WSL2, CPU)**:
```env
EMBEDDING_MODEL=BAAI/bge-m3
EMBEDDING_DEVICE=cpu
EMBEDDING_BATCH_SIZE=16
EMBEDDING_USE_FP16=false
EMBEDDING_NORMALIZE=true
```

**Docker 컨테이너 (ai-service)**:
```yaml
ai-service:
  environment:
    - EMBEDDING_MODEL=BAAI/bge-m3
    - EMBEDDING_DEVICE=cpu
    - EMBEDDING_BATCH_SIZE=16
    - HF_HOME=/app/models
  volumes:
    - ai-models:/app/models   # 모델 영속 저장
```

**GPU 환경**:
```env
EMBEDDING_DEVICE=cuda
EMBEDDING_USE_FP16=true
EMBEDDING_BATCH_SIZE=64
```

### 2.4 디바이스 자동 감지 순서

```
1. EMBEDDING_DEVICE 환경 변수가 설정된 경우 → 해당 디바이스 사용
2. torch.cuda.is_available() == True → "cuda" 사용 (GPU 모델명 로깅)
3. 그 외 → "cpu" 사용
4. FP16은 CPU에서 자동 비활성화 (use_fp16 and device != "cpu")
```

---

## 3. 모델 관리

### 3.1 모델 다운로드

모델은 최초 사용 시 HuggingFace Hub에서 자동 다운로드됩니다.

```bash
# 자동 다운로드 (서비스 기동 시)
# EmbeddingService()가 model.encode() 호출 시 ~/.cache/huggingface/ 에 저장

# 수동 사전 다운로드 (오프라인 환경)
pip install huggingface_hub
huggingface-cli download BAAI/bge-m3 --local-dir ./models/bge-m3
```

### 3.2 모델 캐시 경로

```
~/.cache/huggingface/hub/models--BAAI--bge-m3/
├── blobs/                    # 모델 가중치 (큰 파일)
├── refs/
│   └── main                  # 현재 사용 커밋 해시
└── snapshots/
    └── <commit-hash>/
        ├── config.json       # 모델 설정
        ├── model.safetensors # ~1.2GB (주요 가중치)
        ├── tokenizer.json    # 토크나이저
        ├── tokenizer_config.json
        └── special_tokens_map.json
```

### 3.3 모델 캐시 확인 및 정리

```bash
# 캐시 크기 확인
du -sh ~/.cache/huggingface/hub/models--BAAI--bge-m3/

# 캐시 위치 변경 (환경 변수)
export HF_HOME=/opt/models
# 또는
export HUGGINGFACE_HUB_CACHE=/opt/models/hub

# 캐시 전체 삭제 (재다운로드 필요)
rm -rf ~/.cache/huggingface/hub/models--BAAI--bge-m3/

# 오래된 스냅샷만 삭제
huggingface-cli scan-cache
huggingface-cli delete-cache --revision <old-hash>
```

### 3.4 오프라인 환경 운영

인터넷이 불가한 환경에서는 모델을 사전 배치해야 합니다.

```bash
# 1. 온라인 환경에서 모델 다운로드
huggingface-cli download BAAI/bge-m3 --local-dir /export/bge-m3

# 2. 오프라인 서버로 복사
scp -r /export/bge-m3 user@offline-server:/opt/models/bge-m3

# 3. 환경 변수 설정 (로컬 경로 지정)
export EMBEDDING_MODEL=/opt/models/bge-m3
export HF_HUB_OFFLINE=1
```

### 3.5 모델 업데이트

BGE-M3 모델이 HuggingFace에서 업데이트된 경우:

```bash
# 1. 현재 버전 확인
cat ~/.cache/huggingface/hub/models--BAAI--bge-m3/refs/main

# 2. 최신 버전 다운로드 (기존 캐시와 별도 스냅샷으로 저장)
huggingface-cli download BAAI/bge-m3

# 3. 서비스 재시작 (Lazy Loading이므로 재시작 시 새 버전 로드)
# Docker의 경우:
docker restart kp-ai-service

# 주의: 모델 업데이트 후 기존 임베딩 벡터와의 호환성 검증 필요
# 벡터 불일치 시 전체 재임베딩 필요
```

---

## 4. 서비스 기동 및 상태 확인

### 4.1 서비스 초기화

EmbeddingService는 Lazy Loading 패턴을 사용합니다.

```
__init__():
 ├─ 설정 로드 (model_name, device, batch_size 등)
 ├─ Redis 캐시 연결 시도
 │   ├─ 성공 → cache enabled 로깅
 │   └─ 실패 → warning 로깅, 캐시 없이 계속
 └─ 모델은 아직 로드하지 않음 (_model = None)

첫 번째 embed() 호출:
 ├─ .model 프로퍼티 접근 → _load_model() 트리거
 ├─ FlagEmbedding 시도 → 성공/실패
 ├─ (실패 시) sentence-transformers 시도 → 성공/실패
 └─ 모델 로드 완료 후 인코딩 수행
```

### 4.2 Health Check API

```python
# 서비스 상태 조회
svc = get_embedding_service()
status = svc.health_check()

# 반환 예시:
{
    "service": "EmbeddingService",
    "model_name": "BAAI/bge-m3",
    "model_loaded": true,
    "model_type": "sentence_transformers",
    "device": "cpu",
    "vector_dimension": 1024,
    "batch_size": 32,
    "normalize": true,
    "cache": {
        "available": true,
        "used_memory_human": "512M",
        "keyspace": { "db0": "keys=1234,expires=1234,avg_ttl=86400" }
    }
}
```

### 4.3 빠른 동작 확인

```bash
# Python에서 직접 확인
PYTHONPATH=src python -c "
from app.services.embedding import get_embedding_service
svc = get_embedding_service()
vec = svc.embed('테스트')
print(f'OK: dim={len(vec)}, model={svc.model_name}, type={svc._model_type}')
"
```

### 4.4 서비스 재시작 (싱글턴 리셋)

```python
from app.services.embedding import reset_embedding_service, get_embedding_service

# 기존 인스턴스 해제
reset_embedding_service()

# 새 인스턴스 생성 (변경된 설정 적용)
svc = get_embedding_service()
```

---

## 5. 캐시 운영 (Redis)

### 5.1 캐시 구조

| 항목 | 값 |
|------|-----|
| 키 접두사 | `emb:` |
| 키 형식 | `emb:` + SHA256(`{model_name}:{text}`)의 앞 16자 |
| 값 형식 | JSON 배열 (1024개 float) |
| TTL | `REDIS_EMBEDDING_CACHE_TTL` (기본 7일) |
| 연결 타임아웃 | 3초 |

### 5.2 캐시 동작 흐름

```
embed_batch(["텍스트A", "텍스트B", "텍스트C"]) 호출:

1. 캐시 일괄 조회 (get_batch)
   ├─ "텍스트A" → 캐시 Hit → 벡터 반환
   ├─ "텍스트B" → 캐시 Miss
   └─ "텍스트C" → 캐시 Hit → 벡터 반환

2. Miss 텍스트만 모델 추론
   └─ "텍스트B" → 모델 encode → 1024d 벡터

3. 결과 병합 + Miss 캐시 저장
   └─ "텍스트B" → Redis에 저장 (TTL 7일)

4. 정규화 후 반환
   └─ [벡터A, 벡터B, 벡터C]
```

### 5.3 캐시 장애 대응

캐시는 **Graceful Degradation** 방식으로 동작합니다.

| 상황 | 동작 | 서비스 영향 |
|------|------|------------|
| Redis 미가동 | 초기화 시 warning 로깅, 캐시 비활성화 | **없음** (모델 직접 추론) |
| Redis 연결 끊김 | 개별 get/set 실패 시 debug 로깅 | **없음** (캐시 미사용) |
| Redis 메모리 부족 | set 실패, 기존 캐시는 유지 | **없음** (새 캐시 미저장) |
| Redis 응답 지연 | 타임아웃(3초) 후 캐시 Skip | **지연** (타임아웃 대기) |

### 5.4 캐시 모니터링

```bash
# Redis CLI로 캐시 상태 확인
redis-cli

# 임베딩 캐시 키 수 확인
KEYS emb:*
DBSIZE

# 메모리 사용량
INFO memory

# 임베딩 캐시가 차지하는 메모리 (샘플링)
DEBUG OBJECT emb:<any-key>

# 특정 키의 TTL 확인
TTL emb:<key>

# 캐시 히트율 확인
INFO stats
# keyspace_hits / (keyspace_hits + keyspace_misses)
```

### 5.5 캐시 정리

```bash
# 만료된 키 정리 (Redis가 자동 처리, 수동 트리거)
redis-cli --scan --pattern "emb:*" | head -100

# 전체 임베딩 캐시 삭제 (재임베딩 필요)
redis-cli --scan --pattern "emb:*" | xargs redis-cli DEL

# 또는 FLUSHDB (전체 DB 초기화, 다른 캐시도 삭제됨)
redis-cli FLUSHDB

# 특정 모델의 캐시만 무효화 (Python)
from app.services.embedding import get_embedding_service
svc = get_embedding_service()
svc._cache.invalidate("특정 텍스트", svc.model_name)
```

### 5.6 캐시 무효화가 필요한 상황

| 상황 | 조치 |
|------|------|
| 모델 업데이트 (새 버전) | 전체 캐시 삭제 + 재임베딩 |
| 정규화 설정 변경 | 전체 캐시 삭제 |
| 문서 내용 수정 | 해당 텍스트 캐시 무효화 |
| TTL 변경 | 기존 키는 원래 TTL 유지, 새 키부터 적용 |

---

## 6. 성능 모니터링

### 6.1 핵심 지표

| 지표 | 정상 범위 | 경고 기준 | 확인 방법 |
|------|-----------|-----------|-----------|
| 모델 로드 시간 | < 30s (CPU) | > 60s | 서비스 로그 (INFO) |
| 단일 임베딩 지연 | < 1s (CPU) | > 3s | 서비스 로그 (INFO) |
| 배치 처리량 | > 10 texts/s (CPU) | < 5 texts/s | 서비스 로그 (INFO) |
| 캐시 히트율 | > 50% (안정기) | < 20% | Redis INFO stats |
| 메모리 사용 | < 4GB (모델+추론) | > 6GB | 시스템 모니터링 |
| Redis 메모리 | < 1GB (캐시) | > 2GB | Redis INFO memory |

### 6.2 로그 기반 모니터링

서비스가 출력하는 주요 로그 메시지:

**INFO 레벨** (정상 운영):
```
EmbeddingService initialized: model=BAAI/bge-m3, device=cpu, ...
Embedding cache connected: host=localhost, port=6379, ttl=604800s
Model loaded: type=sentence_transformers, elapsed=14.2s
Batch embed: 32 texts, 2.5s (12.8 texts/s), cache_hits=20
```

**WARNING 레벨** (주의 필요):
```
FlagEmbedding not available, trying sentence-transformers
Embedding cache not available: ConnectionRefusedError(...)
Empty text detected, replacing with space
```

**ERROR 레벨** (즉시 대응):
```
Failed to load embedding model: EmbeddingModelLoadError(...)
All model loading methods failed
```

### 6.3 성능 기준 (검증 완료)

2026-01-27 테스트 결과 (WSL2, CPU, sentence-transformers):

| 항목 | 측정값 | 기준 | 판정 |
|------|--------|------|------|
| 벡터 차원 | 1024 | 1024 | PASS |
| L2 정규화 | 1.000000 | ~1.0 | PASS |
| 단일 임베딩 | 0.782s | < 1s | PASS |
| 배치 32건 | 2.551s (12.5 texts/s) | < 5s | PASS |
| 한국어↔영어 유사도 | 0.7867 | > 0.7 | PASS |
| Sparse 벡터 | dict 반환 | 지원 여부 확인 | PASS (FlagEmbedding 시 활성) |

### 6.4 성능 튜닝 가이드

**배치 사이즈 조정**:

| 환경 | 권장 batch_size | 이유 |
|------|-----------------|------|
| CPU (4GB RAM) | 8 | 메모리 절약 |
| CPU (16GB RAM) | 16~32 | 기본값 적정 |
| GPU (8GB VRAM) | 32~64 | GPU 활용 최적화 |
| GPU (16GB+ VRAM) | 64~128 | 최대 처리량 |

```bash
# 배치 사이즈 변경
export EMBEDDING_BATCH_SIZE=16
```

**최대 토큰 길이 조정**:

```bash
# 짧은 텍스트 위주인 경우 (메모리 절약)
export EMBEDDING_MAX_LENGTH=512

# 긴 문서 처리가 필요한 경우 (기본값)
export EMBEDDING_MAX_LENGTH=8192
```

---

## 7. 트러블슈팅

### 7.1 모델 로드 실패

**증상**: `EmbeddingModelLoadError: Failed to load model`

**원인 및 해결**:

| 원인 | 확인 방법 | 해결 |
|------|-----------|------|
| PyTorch 미설치 | `python -c "import torch"` | `pip install torch` |
| sentence-transformers 미설치 | `python -c "import sentence_transformers"` | `pip install sentence-transformers` |
| 모델 다운로드 실패 | 네트워크 확인 | 프록시 설정 또는 수동 다운로드 |
| 디스크 공간 부족 | `df -h ~/.cache` | 캐시 정리 또는 디스크 확장 |
| 메모리 부족 | `free -h` | 다른 프로세스 종료 또는 RAM 증설 |

### 7.2 libtorch_global_deps.so 로딩 실패 (WSL2)

**증상**:
```
OSError: libtorch_global_deps.so: cannot open shared object file: No such file or directory
```

**근본 원인**: venv이 Windows NTFS 마운트(`/mnt/d/`, 9p 프로토콜)에 있어서
pip이 Windows용 PyTorch(`.dll`)를 설치함. Linux에서 `.so`를 찾으므로 실패.

**해결**: Linux 네이티브 파일시스템에서 venv 재생성

```bash
# 1. Linux 네이티브 경로에 venv 생성
python3 -m venv ~/embedding-venv
source ~/embedding-venv/bin/activate

# 2. CPU 전용 torch 설치
pip install torch --index-url https://download.pytorch.org/whl/cpu

# 3. 임베딩 의존성 설치
pip install sentence-transformers FlagEmbedding numpy

# 4. 검증
python -c "import torch; print(f'PyTorch {torch.__version__} OK')"
```

> 참고: 상세 내용은 `docs/03_implementation/embedding_model_setup_guide.md` Section 2 참조

### 7.3 FlagEmbedding 폴백 발생

**증상**: 로그에 `FlagEmbedding not available, trying sentence-transformers` 출력

**영향**: Dense 임베딩은 정상 동작. Sparse 임베딩이 빈 dict로 반환됨.

**원인 및 해결**:

| 원인 | 해결 |
|------|------|
| FlagEmbedding 미설치 | `pip install FlagEmbedding` |
| FlagEmbedding 내부 의존성 충돌 | `pip install FlagEmbedding --force-reinstall` |
| C++ 컴파일러 부재 (Windows) | Linux 환경에서 설치 또는 sentence-transformers만 사용 |

**참고**: sentence-transformers 폴백으로도 Dense 임베딩 품질은 동일합니다.
Sparse 임베딩이 필수가 아니라면 sentence-transformers만으로 운영 가능합니다.

### 7.4 OOM (Out of Memory)

**증상**:
```
RuntimeError: [enforce fail at alloc.cpp] DefaultCPUAllocator: not enough memory
```

**해결**:
```bash
# 1. 배치 사이즈 축소
export EMBEDDING_BATCH_SIZE=4

# 2. 최대 토큰 길이 축소
export EMBEDDING_MAX_LENGTH=2048

# 3. 다른 프로세스 메모리 해제
# 4. 시스템 RAM 확인: free -h
# 5. 불가피한 경우 서비스 재시작
```

### 7.5 모델 다운로드 실패

**증상**: `ConnectionError: Cannot reach huggingface.co`

**해결**:
```bash
# 프록시 설정
export HTTPS_PROXY=http://proxy:port

# HuggingFace 미러 사용
export HF_ENDPOINT=https://hf-mirror.com

# 오프라인 모드 (사전 다운로드 필수)
export HF_HUB_OFFLINE=1
export EMBEDDING_MODEL=/opt/models/bge-m3
```

### 7.6 캐시 관련 문제

| 증상 | 원인 | 해결 |
|------|------|------|
| 캐시 비활성 경고 | Redis 미가동 | `redis-server` 기동 확인 |
| 캐시 히트율 0% | TTL 만료 또는 키 불일치 | `redis-cli KEYS emb:*` 확인 |
| Redis 메모리 과다 | 캐시 무한 증가 | `maxmemory` + `maxmemory-policy` 설정 |
| 응답 지연 | Redis 타임아웃 | Redis 서버 상태 점검, 네트워크 확인 |

### 7.7 벡터 품질 이상

정규화 또는 유사도가 비정상인 경우:

```python
import math
from app.services.embedding import get_embedding_service

svc = get_embedding_service()

# L2 정규화 검증
vec = svc.embed("테스트 문서")
norm = math.sqrt(sum(x * x for x in vec))
print(f"L2 norm: {norm:.6f}")  # 1.0에 가까워야 함

# 유사도 검증
vec_ko = svc.embed("한국어 문서 검색")
vec_en = svc.embed("English document search")
dot = sum(a * b for a, b in zip(vec_ko, vec_en))
print(f"한국어↔영어 유사도: {dot:.4f}")  # 0.7+ 기대
```

---

## 8. 백업 및 복구

### 8.1 백업 대상

| 대상 | 경로 | 중요도 | 복구 방법 |
|------|------|--------|-----------|
| 모델 가중치 | `~/.cache/huggingface/hub/models--BAAI--bge-m3/` | 중 | HuggingFace에서 재다운로드 |
| Redis 캐시 | Redis DB 0 (`emb:*` 키) | 하 | 재임베딩으로 자동 복구 |
| 서비스 코드 | `src/app/services/embedding.py` | 상 | Git 저장소에서 복원 |
| 환경 설정 | `.env` 파일 | 상 | 설정 문서 참조하여 재설정 |

### 8.2 모델 백업

```bash
# 모델 캐시 백업 (오프라인 복구용)
tar -czf bge-m3-backup.tar.gz -C ~/.cache/huggingface/hub models--BAAI--bge-m3

# 복원
tar -xzf bge-m3-backup.tar.gz -C ~/.cache/huggingface/hub/
```

### 8.3 Redis 캐시 백업

```bash
# RDB 스냅샷 (Redis 설정에 따라 자동 저장)
redis-cli BGSAVE

# 백업 파일 복사
cp /var/lib/redis/dump.rdb /backup/redis-embedding-$(date +%Y%m%d).rdb

# 복원
cp /backup/redis-embedding-YYYYMMDD.rdb /var/lib/redis/dump.rdb
systemctl restart redis
```

### 8.4 장애 복구 절차

```
1. 서비스 중단 확인
   └─ 로그 확인: ERROR 레벨 메시지 검색

2. 원인 파악
   ├─ 모델 로드 실패? → Section 7.1
   ├─ 메모리 부족? → Section 7.4
   ├─ 네트워크 문제? → Section 7.5
   └─ Redis 장애? → Section 7.6

3. 복구 조치
   ├─ 싱글턴 리셋: reset_embedding_service()
   ├─ 모델 재다운로드: rm -rf ~/.cache/huggingface/hub/models--BAAI--bge-m3/
   ├─ 캐시 초기화: redis-cli FLUSHDB
   └─ 서비스 재시작: docker restart kp-ai-service

4. 복구 확인
   ├─ health_check() 정상 확인
   ├─ 테스트 임베딩 생성 확인
   └─ 로그 ERROR 없음 확인
```

---

## 9. 운영 체크리스트

### 9.1 일일 점검

- [ ] 서비스 로그에 ERROR 메시지 없음
- [ ] `health_check()` 정상 반환
- [ ] Redis 연결 상태 확인 (`redis-cli PING`)

### 9.2 주간 점검

- [ ] Redis 메모리 사용량 확인 (`INFO memory`)
- [ ] 캐시 히트율 확인 (`INFO stats`)
- [ ] 디스크 사용량 확인 (`df -h`)
- [ ] 모델 캐시 디렉토리 상태 확인

### 9.3 월간 점검

- [ ] HuggingFace 모델 업데이트 확인
- [ ] PyTorch / sentence-transformers 보안 패치 확인
- [ ] Redis maxmemory 설정 적정성 검토
- [ ] 임베딩 품질 검증 (유사도 테스트 재실행)

### 9.4 배포 전 점검

- [ ] 모델 파일 존재 확인 (오프라인 환경 시)
- [ ] 환경 변수 설정 확인
- [ ] Redis 연결 가능 확인
- [ ] 테스트 임베딩 생성 성공
- [ ] 벡터 차원 1024 확인
- [ ] L2 정규화 norm ~= 1.0 확인

---

## 관련 문서

| 문서 | 경로 | 설명 |
|------|------|------|
| 설치 및 테스트 가이드 | `docs/03_implementation/embedding_model_setup_guide.md` | 초기 설치, 테스트 스크립트, WSL2 해결법 |
| 기본 검증 스크립트 | `scripts/test_embedding_basic.py` | 5단계 모델 검증 (PyTorch → 모델 로드 → 벡터 → 다국어 → 배치) |
| 통합 검증 스크립트 | `scripts/test_embedding_integration.py` | 7단계 EmbeddingService API 검증 |
| 상세 설계서 | `docs/02_design/hybrid_rag_platform_detailed_design.md` | 전체 아키텍처 내 임베딩 위치 |
| STORY-004 | `backlog/stories/STORY-004-bge-m3-embedding.md` | 백로그 Story (AC, Tasks) |

---

## 변경 이력

| 날짜 | 버전 | 내용 |
|------|------|------|
| 2026-01-27 | 1.0 | 초기 작성 - 환경 설정, 모델 관리, 캐시 운영, 트러블슈팅, 체크리스트 |
