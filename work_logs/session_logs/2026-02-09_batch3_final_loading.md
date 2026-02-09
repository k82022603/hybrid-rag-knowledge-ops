# Session Log - 2026-02-09 (Session 8)

**Session ID**: 2026-02-09_batch3_final_loading
**시작 시간**: 01:18 KST
**종료 시간**: 10:40 KST
**모델**: Claude Opus 4.6 (claude-opus-4-6)

---

## 세션 요약

미처리 8건 전체 적재 완료 (38/38 = 100%). 임베딩 비활성화 전략으로 OOM 문제 해결.

---

## 완료된 작업

### 1. OOM 원인 분석 및 전략 전환

**문제**: 8.5MB+ 파일이 임베딩 포함 모드에서 RSS 9.3~9.6GB로 OOM Kill
- 소방시설법 (8.5MB): RSS 9.3GB → OOM Kill (임베딩 포함)
- LLM 기반 AI 에이전트 기초와 실습 (11MB): RSS 9.6GB → OOM Kill (임베딩 포함)

**원인 분석**:
- docling 파싱: ~2.6-3.5GB (문서 크기에 비례)
- BGE-M3 임베딩 모델: ~2GB (고정)
- 임베딩 계산 중 데이터: ~3-4GB (chunk 수에 비례)
- 합계: 8-10GB → WSL 11GB 전체 OOM 트리거

**전략 전환**: `enable_embeddings=False`
- BGE-M3 모델 로딩 스킵 (~2GB 절감)
- 임베딩 계산 메모리 제거 (~3-4GB 절감)
- 파싱 + 청킹 + 엔티티 추출 + PG/ES/Neo4j 저장만 수행
- 결과: peak 2.3-3.7GB로 안정적 처리

### 2. Batch 3: 미처리 8건 전체 적재

| # | 파일명 | 크기 | chunks | entities | 시간 | peak | 결과 |
|---|--------|------|--------|----------|------|------|------|
| 1 | 소방시설법 및 화재예방법령집 | 8.5MB | 1,469 | 29 | 46min | 2.9GB | SUCCESS |
| 2 | LLM 기반 AI 에이전트 기초와 실습 | 11MB | 132 | 44 | 34min | 3.7GB | SUCCESS |
| 3 | 아키텍처팀 AI프로젝트 이해 워크샵 | 12MB | 174 | 49 | 42min | 2.3GB | SUCCESS |
| 4 | 딥러닝과 RAG 기초과정 | 17MB | 374 | 59 | 63min | 2.7GB | SUCCESS |
| 5 | 법령용어한영사전(법령용어부분) | 19MB | 2,292 | 29 | 10min | 2.6GB | SUCCESS |
| 6 | 법령용어한영사전(부록) | 26MB | 709 | 38 | 36min | 2.8GB | SUCCESS |
| 7 | 문화재관계법령집 | 69MB | 2,611 | 10 | 76min | 3.0GB | SUCCESS |
| 8 | 알기쉬운법령정비기준-7판 | 79MB | 2,333 | 3 | 82min | 3.2GB | SUCCESS |

**총 처리 시간**: ~6.5시간 (파일 간 ai-service 재시작 포함)
**생성된 chunks**: 10,094건

### 3. OOM 시도 기록 (임베딩 포함 모드)

| 파일 | 모드 | RSS | 결과 |
|------|------|-----|------|
| 소방시설법 | embedding=True | 9.3GB | OOM Kill |
| LLM 에이전트 기초실습 | embedding=True | 9.6GB | OOM Kill |

→ 2건 OOM 후 임베딩 비활성화 전략으로 전환, 이후 8건 전체 성공

---

## 데이터 현황 (세션 종료 시)

| 스토어 | 이전 (세션 7) | 현재 (세션 8) | 변화 |
|--------|-------------|-------------|------|
| PG documents (고유 제목) | 30건 | 40건 | +10 |
| PG documents (총 행) | 32건 | 44건 | +12 |
| ES chunks | 3,492건 | 13,586건 | +10,094 |
| Neo4j documents | 30건 | 40건 | +10 |
| 적재율 | 30/38 (79%) | 38/38 (100%) | +21% |

### PG 행 수 vs 고유 제목 차이 (44 vs 40)

- 40 고유 문서 + 4건의 중복/변형 (이전 세션에서 수동 업로드된 pptx 2건 + 기타 2건)
- batch3에서 적재한 8건은 모두 고유 문서

---

## 기술 이슈 및 해결

### 1. 임베딩 비활성화 전략 (핵심 발견)

**문제**: WSL 11GB 메모리에서 ai-service 10GB 컨테이너 한도
- 파싱(~3GB) + BGE-M3 모델(~2GB) + 임베딩 계산(~4GB) = ~9GB+ → OOM

**해결**: `InitialDataLoader(enable_embeddings=False)`
- 파싱 + 청킹 + 엔티티 추출(DeepSeek API) + PG/ES/Neo4j 저장만 수행
- ES에 텍스트 chunk만 저장 (벡터 없음)
- peak 2.3~3.7GB로 안정적 처리

**후속 작업 필요**:
- batch3으로 적재한 8건에 대한 벡터 임베딩 후속 생성 (P1)
- 별도 임베딩 배치 스크립트 필요 (파싱 없이 ES에서 텍스트 읽어 임베딩만 추가)
- 또는 WSL 메모리 16GB+ 후 full mode 재적재

### 2. 파일별 처리 시간 패턴

| 유형 | 예시 | 시간/MB |
|------|------|---------|
| 사전/텍스트 | 법령용어사전 19MB | 0.5min/MB (매우 빠름) |
| 법령집 (테이블 많음) | 소방시설법 8.5MB | 5.4min/MB |
| 프레젠테이션 (이미지 많음) | LLM 에이전트 11MB | 3.1min/MB |
| 대형 법령집 | 문화재관계 69MB | 1.1min/MB |

- 사전형 텍스트가 가장 빠름 (OCR 불필요)
- 테이블 많은 법령집이 가장 느림 (TableItem 파싱 집약적)

### 3. 각 파일 간 ai-service 재시작 전략

- 각 대형 파일 처리 후 `docker compose restart ai-service` 실행
- 프레시 메모리(~300MB)에서 시작하여 누적 메모리 문제 방지
- 스크립트 재복사 필요: `docker cp load_single_noembedding.py kp-ai-service:/app/`

---

## 주요 결정사항

| 결정 | 내용 | 근거 |
|------|------|------|
| 임베딩 비활성화 | batch3 전체에 적용 | OOM 회피, 텍스트 검색은 가능 |
| 파일별 재시작 | 각 파일 처리 후 ai-service restart | 메모리 누적 방지 |
| 순차 처리 | 한 번에 1파일씩 | 메모리 안정성 최우선 |

---

## 다음 세션 Action Items

### P0
1. **batch3 임베딩 후속 생성** (8건, 10,094 chunks)
   - ES에서 텍스트 읽어 BGE-M3 임베딩 추가
   - 별도 lightweight 배치 스크립트 필요
   - 또는 WSL 메모리 증가 후 full mode 재적재

### P1
2. Redis FLUSHALL (캐시 정리)
3. InitialDataLoader 중복 방지 구현 (file_hash 기반)
4. 데일리 마감 (일지, 바이브로그, 문서 현행화)

### P2
5. 운영매뉴얼에 batch3 실행 로그 추가
6. 임베딩 비활성화 전략을 운영매뉴얼에 문서화

---

## 변경된 파일 목록

```
knowledge_service/scripts/
├── load_single.py                    # 단일 파일 로더 (임베딩 포함)
├── load_single_noembedding.py        # 단일 파일 로더 (임베딩 비활성화) ⭐

work_logs/session_logs/
└── 2026-02-09_batch3_final_loading.md  # 이 파일 (신규)
```

---

## 세션 통계

| 항목 | 값 |
|------|-----|
| 적재 성공 | 8건 (batch3 전체) |
| OOM Kill | 2회 (소방시설법, LLM 에이전트 - 임베딩 포함 모드) |
| 생성된 chunks | 10,094건 |
| 총 처리 시간 | ~6.5시간 |
| ai-service 재시작 | 8회 |
| Slack 메시지 | 7건 |

---

## 전체 적재 누적 통계 (Batch 1~3)

| 배치 | 세션 | 파일 수 | 성공 | chunks | 기간 |
|------|------|---------|------|--------|------|
| Batch 1 | Session 6 | 17건 | 17 | 1,201 | ~2시간 |
| Batch 2-1 | Session 7 | 11건 | 7 | ~1,334 | ~1시간 |
| Batch 2-2 | Session 7 | 10건 | 6 | ~957 | ~1.5시간 |
| Batch 3 | Session 8 | 8건 | 8 | 10,094 | ~6.5시간 |
| **합계** | | **38건** | **38** | **13,586** | **~11시간** |

---

*기록자: Claude Code (Opus 4.6)*
*기록 시간: 2026-02-09 10:40 KST*
