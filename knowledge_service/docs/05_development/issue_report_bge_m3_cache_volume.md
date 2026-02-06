# Issue Report: BGE-M3 Embedding Model Cache Volume Mount

**Date**: 2026-02-06
**Story**: STORY-087 (SCRUM-83)
**Reporter**: Infra Engineer
**Status**: Resolved

---

## Problem

ai-service 컨테이너를 재시작할 때마다 BGE-M3 임베딩 모델(6.4GB)을 HuggingFace Hub에서 다시 다운로드하여 **시작 시간이 약 5분** 소요되었습니다.

### 증상

```
# 컨테이너 재시작 시마다 반복됨
Downloading model files: 100%|##########| 6.4GB/6.4GB [04:32<00:00, 23.5MB/s]
Loading BGE-M3 model into memory...
Model loaded in 38.2 seconds
```

- 총 시작 시간: ~5분 (다운로드 4분30초 + 로딩 30초)
- 네트워크 대역폭 낭비: 매 재시작마다 6.4GB
- 개발 중 빈번한 재시작으로 생산성 저하

### 근본 원인

Docker 컨테이너의 `read_only: true` 보안 설정 + 볼륨 미설정으로 인해 모델 캐시가 컨테이너 재생성 시 유실됨.

```yaml
# 기존 설정 - 캐시 경로에 영구 볼륨 없음
ai-service:
  read_only: true
  environment:
    - HF_HOME=/app/.cache/huggingface
  # volumes에 캐시 마운트 없음
```

---

## Solution

호스트의 HuggingFace 캐시 디렉토리를 컨테이너에 read-only로 바인드 마운트.

### 변경 사항 (docker-compose.yml)

```yaml
ai-service:
  environment:
    # HuggingFace 캐시 경로 지정
    - HF_HOME=/app/.cache/huggingface
    - TRANSFORMERS_CACHE=/app/.cache/huggingface/hub
  volumes:
    # BGE-M3 임베딩 모델 캐시 마운트 (6.4GB, 다운로드 없이 로컬 사용)
    - /home/claude/.cache/huggingface:/app/.cache/huggingface:ro
```

### 핵심 설계 결정

| 결정 | 선택 | 이유 |
|------|------|------|
| 마운트 모드 | `:ro` (read-only) | 보안 - 컨테이너가 호스트 캐시 수정 불가 |
| 캐시 소스 | 호스트 `/home/claude/.cache/huggingface` | WSL2 환경에서 이미 다운로드된 모델 재활용 |
| 환경변수 | `HF_HOME` + `TRANSFORMERS_CACHE` | transformers 라이브러리 버전별 캐시 경로 호환 |

---

## Results

### Before (캐시 없음)

| 항목 | 수치 |
|------|------|
| 컨테이너 시작 시간 | ~5분 (300초) |
| 네트워크 사용량 | 6.4GB / 재시작 |
| 모델 로딩 시간 | ~30초 |
| 첫 검색 가능 시점 | ~5분 30초 |

### After (캐시 마운트)

| 항목 | 수치 |
|------|------|
| 컨테이너 시작 시간 | ~30초 |
| 네트워크 사용량 | 0 (로컬 캐시) |
| 모델 로딩 시간 | ~25초 |
| 첫 검색 가능 시점 | ~30초 |

**개선율**: 시작 시간 90% 단축 (5분 → 30초)

---

## Production 고려사항

1. **Docker Named Volume 사용 권장**: 프로덕션에서는 바인드 마운트 대신 named volume 사용
   ```yaml
   volumes:
     bge-m3-cache:
       name: kp-bge-m3-cache

   ai-service:
     volumes:
       - bge-m3-cache:/app/.cache/huggingface
   ```

2. **초기 모델 프리로드**: 첫 배포 시 init 컨테이너로 모델 다운로드
   ```bash
   docker run --rm -v bge-m3-cache:/cache \
     python:3.11 pip install sentence-transformers && \
     python -c "from FlagEmbedding import BGEM3FlagModel; BGEM3FlagModel('BAAI/bge-m3')"
   ```

3. **캐시 사이즈 모니터링**: BGE-M3 모델 ~6.4GB, 디스크 여유 확인 필요

---

## Commit

```
b491a3e [CHORE] BGE-M3 임베딩 모델 캐시 볼륨 마운트 추가
```
