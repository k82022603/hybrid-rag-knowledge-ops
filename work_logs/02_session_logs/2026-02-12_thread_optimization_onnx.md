# Session Log - 2026-02-12 (4th Session)

**Session ID**: 2026-02-12_thread_optimization_onnx
**시작 시간**: 22:55
**종료 시간**: 23:52
**모델**: Claude Opus 4.6 (claude-opus-4-6)

---

## 세션 요약

WSL2 8코어 환경에서 스레드 최적화 실험(threads=4/6/8 비교), embedding.py 정규화 코드 수정, ONNX Runtime 전환 계획 문서화

---

## 완료된 작업

### 1. 스레드 최적화 실험 (주요)

#### 상세 내용
- 전문가 3인(Infra/ETL/RAG) + 클로드 분석 수행
- Infra: threads=6 권장, RAG: threads=8 권장, ETL: threads=8 적용(문제 발생)
- **실측 결과**:
  - threads=4 (기준): 1.1 t/s, 30~35초/배치
  - threads=8 (이중 프로세스): 0.2 t/s (-82%)
  - threads=8 (단독): 0.6 t/s (-45%)
  - threads=6 (단독): 0.6 t/s (-45%)
- **결론**: threads=4가 최적. HyperThreading은 GEMM 연산에서 캐시 경합으로 역효과
- threads=4로 복원, 안정 운행 재개 (1.1~1.4 t/s)

### 2. ETL 에이전트 이중 프로세스 사고 처리 (주요)

#### 상세 내용
- ETL 에이전트가 기존 v2 프로세스를 죽이지 않고 v2.1 프로세스를 추가 실행
- 이중 프로세스로 CPU 경합 → 전체 성능 0.2 t/s로 급락
- ETL 에이전트 강제 중단 (TaskStop)
- 모든 중복 프로세스 정리 후 단독 프로세스로 복원

### 3. embedding.py 정규화 코드 수정 (주요)

#### 상세 내용
- `_normalize_vector`: 순수 Python(math.sqrt+list comprehension) → numpy 배치 연산
- `_normalize_vectors`: 개별 루프 → `np.linalg.norm` 배치 처리
- `_encode_sentence_transformers`: `normalize_embeddings=True` → `False` (이중 정규화 제거)
- 소스 파일 + 컨테이너 내 파일 모두 수정 완료

### 4. ONNX Runtime 전환 계획 문서화 (부가)

#### 상세 내용
- Appendix C로 ONNX 전환 계획 상세 작성
- 현재 구조(PyTorch) vs ONNX 비교, 장단점, 변환 절차, 로드맵
- Sparse 임베딩 미지원 대안 (ES BM25 Hybrid)
- Phase 3 완료 후 API 서빙용 전환 권장

### 5. 문서 업데이트 (부가)

#### 상세 내용
- `01_etl_3phase_embedding_report.md` v3.0 → v3.2
  - Appendix B: 스레드 최적화 실험 전문
  - Appendix C: ONNX Runtime 전환 계획
  - 정규화 코드 수정 반영

---

## 주요 결정사항

| 결정 | 내용 | 근거 |
|------|------|------|
| threads=4 확정 | HT 증가 효과 없음, 물리코어 수가 최적 | 실측 threads=6,8 모두 -45% 이상 성능 저하 |
| ETL 에이전트 차단 | 독립적 프로세스 실행 금지 | 이중 프로세스로 -82% 성능 급락 유발 |
| 정규화 numpy 전환 | embedding.py 코드 직접 수정 | API 서빙 경로에서 순수 Python 정규화 사용 중 |
| 이중 정규화 제거 | sentence-transformers normalize=False | embed_batch에서 이미 정규화, 중복 제거 |
| ONNX 현재 미적용 | Phase 3 완료 후 전환 | 배치 중 모델 변경 리스크, Sparse 미지원 |

---

## 변경된 파일 목록

```
knowledge_service/
├── docs/04_testing/embedding_evaluation/
│   ├── 01_etl_3phase_embedding_report.md  # v3.2 (Appendix B+C 추가)
│   └── 02_bge_m3_and_107k_embeddings.md   # v1.2 (WSL2 반영)
├── scripts/
│   ├── embedding_health_check.sh          # 임계치 조정
│   └── run_embedding_backfill_v2.py       # threads 복원
└── src/app/services/
    └── embedding.py                       # numpy 정규화 + 이중 정규화 제거
```

---

## 현재 프로젝트 상태

### 인프라 상태
| 항목 | 값 |
|------|-----|
| 총 컨테이너 | 5개 (ai-service, elasticsearch, neo4j, postgresql, redis) |
| WSL2 | 8코어, 14GB RAM, swap 1GB |
| ai-service CPU | ~250% (threads=4) |
| ai-service MEM | ~1.4 GiB |

### 임베딩 진행 상태
| 항목 | 값 |
|------|-----|
| ES 전체 청크 | 108,896건 |
| 임베딩 완료 | ~38,700건 (35.5%) |
| 남은 청크 | ~70,200건 |
| 현재 속도 | 1.1~1.4 t/s |
| 예상 소요 | ~17시간 |
| 헬스체크 | 30분 간격 자동 실행 중 |

---

## 다음 작업 (Action Items)

### P0 (Critical)
1. Phase 3 임베딩 완료 모니터링 (헬스체크 자동 운영)

### P1 (High)
2. Phase 3 완료 후 ONNX Runtime 전환 (Appendix C 계획 기반)
3. 임베딩 완료 후 벡터 검색 품질 검증

### P2 (Medium)
4. Hybrid 검색 구현 (Dense kNN + BM25 RRF)
5. ONNX INT8 양자화 벤치마크

---

## 리스크 모니터링

| 리스크 | 확률 | 영향 | 상태 | 대응 |
|--------|------|------|------|------|
| 임베딩 프로세스 중단 | Low | High | Monitoring | 헬스체크 자동 재시작 |
| 메모리 부족/OOM | Low | High | Monitoring | swap 1GB + swappiness=10 |
| WSL2 재시작 필요 | Low | Med | Open | post_wsl_restart.sh 준비됨 |

---

## 사용된 도구 및 에이전트

| 도구/에이전트 | 용도 |
|--------------|------|
| Infra Engineer (a5d0dd7) | 스레드 최적화 분석 → threads=6 권장 |
| RAG Engineer (afdf920) | 스레드 최적화 분석 → threads=8 권장 |
| ETL Engineer (a525b7f) | 스레드 최적화 분석 → threads=8 적용 (이중 프로세스 사고) |
| MCP Slack | 실험 결과 dev 채널 보고 |

---

## 세션 통계

| 항목 | 값 |
|------|-----|
| 수정된 파일 | 6개 |
| 신규 생성 파일 | 0개 |
| 문서 추가 분량 | ~480줄 (Appendix B+C) |
| 코드 수정 | embedding.py (numpy 정규화 + 이중 정규화 제거) |
| 에이전트 사용 | 3개 (Infra/RAG/ETL) |

---

*기록자: Claude Code (Opus 4.6)*
*기록 시간: 2026-02-12 23:52 KST*
