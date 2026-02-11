# EmbeddingService 실제 파일 테스트 결과

**날짜**: 2026-02-02
**테스트 환경**: WSL2 (Ubuntu), Python 3.12
**테스트 담당**: Claude Code

---

## 1. 테스트 개요

| 항목 | 내용 |
|------|------|
| **목적** | EmbeddingService 실제 파일 임베딩 및 벡터 검색 검증 |
| **모델** | BAAI/bge-m3 (FlagEmbedding) |
| **벡터 차원** | 1024 |
| **저장소** | Elasticsearch (단일 노드, yellow 상태) |
| **캐시** | Redis (TTL: 604800s = 7일) |

---

## 2. 테스트 결과 요약

| 테스트 | 결과 | 비고 |
|--------|:----:|------|
| EmbeddingService 초기화 | ✅ PASS | Redis 캐시 연결 성공 |
| 단일 텍스트 임베딩 | ✅ PASS | 34.2s (모델 최초 로드 포함) |
| 배치 임베딩 | ✅ PASS | 7.5 texts/s |
| Elasticsearch 연결 | ✅ PASS | 클러스터 yellow, 1 node |
| 문서 인덱싱 | ✅ PASS | 3개 문서 인덱싱 |
| 벡터 검색 | ✅ PASS | cosine similarity 기반 |

**전체 결과**: **성공**

---

## 3. 상세 테스트 결과

### 3.1 EmbeddingService 초기화

```
EmbeddingService initialized:
  - model: BAAI/bge-m3
  - device: cpu
  - fp16: True
  - batch_size: 32
  - normalize: True
  - cache: enabled (Redis localhost:6379)
```

### 3.2 임베딩 성능

| 테스트 케이스 | 텍스트 수 | 캐시 히트 | 소요 시간 | 처리량 |
|--------------|:--------:|:---------:|:---------:|:------:|
| 단일 텍스트 (최초) | 1 | 0 | 34.2s | 0.03/s |
| 배치 3개 (2번째) | 3 | 1 | 0.4s | 7.5/s |
| 문서 3개 | 3 | 0 | 1.4s | 2.1/s |
| 검색 쿼리 | 1 | 0 | 0.2s | 4.8/s |

**참고**: 첫 번째 호출은 모델 로딩(33.84s)을 포함하여 시간이 오래 걸림

### 3.3 임베딩 샘플

```python
# 입력: "Hybrid RAG는 벡터 검색과 키워드 검색을 결합한 기술입니다."
# 출력 (처음 5개 값):
[-0.0327, -0.0262, 0.0038, -0.0054, -0.0024]
# 차원: 1024
```

### 3.4 벡터 검색 결과

**쿼리**: "RAG 검색 방법은 무엇인가요?"

| 순위 | 점수 | 문서 제목 | 내용 미리보기 |
|:----:|:----:|----------|--------------|
| 1 | 1.6408 | Hybrid RAG 아키텍처 | 벡터 검색(semantic)과 키워드 검색(lexical)을 결합... |
| 2 | 1.3976 | EmbeddingService 구현 | BGE-M3 모델을 사용하여 다국어 임베딩... |
| 3 | 1.3894 | Knowledge Graph 기반 검색 | Neo4j를 사용하여 문서 간 관계를 그래프로 표현... |

**분석**: RAG 관련 쿼리에 대해 Hybrid RAG 문서가 가장 높은 점수(1.6408)로 정확하게 1위 반환

---

## 4. Elasticsearch 상태

```json
{
  "cluster_name": "knowledge-platform-cluster",
  "status": "yellow",
  "number_of_nodes": 1,
  "active_primary_shards": 29,
  "active_shards": 29
}
```

### 생성된 인덱스

| 인덱스명 | 문서 수 | 용도 |
|----------|:------:|------|
| test-documents | 5 | 기존 테스트 데이터 |
| test-embedding-docs | 3 | 오늘 테스트 데이터 |

---

## 5. 해결한 문제

### WSL2 패키지 호환성 문제

Windows에서 설치된 Python 패키지가 WSL2에서 동작하지 않는 문제 발생.

**재설치한 패키지 (7개)**:

| 패키지 | 문제 증상 | 해결 |
|--------|----------|------|
| safetensors | `_safetensors_rust` 모듈 누락 | 재설치 |
| tokenizers | `tokenizers.tokenizers` 모듈 누락 | 재설치 |
| scikit-learn | `_check_build` 모듈 누락 | 재설치 |
| scipy | `add_dll_directory` 오류 | 재설치 |
| pandas | `add_dll_directory` 오류 | 재설치 |
| numpy | 의존성 충돌 | 재설치 |
| sentencepiece | `_sentencepiece` 모듈 누락 | 재설치 |

**해결 명령어**:
```bash
.venv/bin/pip uninstall -y safetensors tokenizers scikit-learn scipy pandas numpy sentencepiece
.venv/bin/pip install --no-cache-dir safetensors tokenizers scikit-learn scipy pandas numpy sentencepiece
```

**관련 문서**: `wsl2_python_environment_guide.md` (v1.1 업데이트)

---

## 6. 테스트 스크립트

테스트에 사용된 스크립트: `scripts/test_real_embedding.py`

### 주요 기능

1. **EmbeddingService 초기화 테스트**: 모델 로드, 캐시 연결
2. **단일/배치 임베딩 테스트**: 텍스트 → 벡터 변환
3. **Elasticsearch 연결 테스트**: 클러스터 상태, 인덱스 목록
4. **문서 인덱싱 테스트**: 임베딩 생성 → ES 저장
5. **벡터 검색 테스트**: 쿼리 임베딩 → cosine similarity 검색

---

## 7. 결론 및 다음 단계

### 성과

- EmbeddingService가 실제 환경에서 정상 동작 확인
- BGE-M3 모델로 1024차원 다국어 임베딩 생성 성공
- Elasticsearch 벡터 검색 정확도 검증 (RAG 쿼리 → RAG 문서 1위)
- Redis 캐시 동작 확인 (중복 요청 최적화)

### 다음 단계

| 우선순위 | 작업 | 담당 |
|:--------:|------|------|
| P1 | 실제 업로드 문서로 E2E 테스트 | RAG |
| P2 | RAGAS 평가 통합 | RAG |
| P2 | 대용량 문서 배치 처리 성능 테스트 | RAG |

---

**문서 작성**: Claude Code
**작성 시간**: 2026-02-02 10:35 KST
