# Session Log - 2026-02-08 (Session 7)

**Session ID**: 2026-02-08_batch2_document_loading
**시작 시간**: 22:00
**종료 시간**: 00:30 (2/9)
**모델**: Claude Opus 4.6 (claude-opus-4-6)

---

## 세션 요약

2차 배치 문서 적재 (미처리 22건 중 13건 성공), 데일리마감, 중복 방지 검토서 작성

---

## 완료된 작업

### 1. 2차 배치 적재 준비
- ai-service 메모리 8G → 10G (docker-compose.yml)
- 12개 불필요 컨테이너 중지 (~1.75GB 절감)
- ai-service 재생성 (프레시 메모리 369MB/10GB)

### 2. Batch 2-1: 소형 파일 (< 2MB)
| # | 파일명 | 크기 | chunks | entities | 시간 | 결과 |
|---|--------|------|--------|----------|------|------|
| 1 | 대한민국헌법 | 0.2MB | 48 | 30 | 138s | SUCCESS |
| 2 | 형법 | 0.3MB | 140 | 33 | 233s | SUCCESS |
| 3 | 민사소송법 | 0.4MB | 210 | 32 | 316s | SUCCESS |
| 4 | 민법 | 0.5MB | 410 | 41 | 561s | SUCCESS |
| 5 | RAG Approaches | 0.6MB | 16 | 23 | 129s | SUCCESS |
| 6 | 상법 | 0.7MB | 633 | 41 | 817s | SUCCESS |
| 7 | Reranking | 0.8MB | 27 | 29 | 108s | SUCCESS |
| 8 | GPT o1 Reasoning | 0.8MB | - | - | - | CRASH (파일명 특수문자) |

**결과**: 7/11 성공, 파일명 특수문자(`'`, `—`) 이슈로 8번에서 중단

### 3. Batch 2-2: 중형 + 대형 파일
| # | 파일명 | 크기 | chunks | entities | 시간 | 결과 |
|---|--------|------|--------|----------|------|------|
| 1 | GPT o1 Reasoning | 0.8MB | 26 | 25 | 180s | SUCCESS |
| 2 | Reranking (Korean) | 1.0MB | 18 | 24 | 112s | SUCCESS |
| 3 | RL Search Agent | 1.2MB | 156 | 29 | 630s | SUCCESS |
| 4 | 랭체인코리아 밋업 | 1.9MB | 5 | 19 | 442s | SUCCESS |
| 5 | 2015지방자치_관계법령집 | 4.7MB | 576 | 35 | 2183s | SUCCESS |
| 6 | LLM 서비스 만들기 | 6.8MB | 26 | 32 | 895s | SUCCESS |
| 7 | 소방시설법 화재예방법령집 | 8.5MB | - | - | - | OOM Kill |

**결과**: 6/10 성공, 소방시설법 법령집 파싱 중 OOM Kill (10GB 초과)

### 4. 데일리마감
- 작업일지 업데이트 (세션 6, 7 추가)
- 바이브로그 생성 (문서 적재 인사이트)
- PLAN.md, README.md, CLAUDE.md 현행화
- 커밋: `e365405` (12 files, +1,124 / -35)
- Slack 알림: #proj-hrkp-dev

### 5. InitialDataLoader 중복 방지 검토
- `docs/05_development/11_initial_data_loader_dedup_review.md` 작성
- file_hash (SHA-256) 기반 dedup 권장 (P1)

---

## 데이터 현황 (세션 종료 시)

| 스토어 | 값 |
|--------|-----|
| PG documents (completed) | 30건 (고유) |
| PG documents (uploaded) | 2건 (pptx, 이전 수동 업로드) |
| ES chunks | 3,492건 |
| 적재율 | 30/38 (79%) |

### 미처리 파일 (8건)

| 파일명 | 크기 | 미처리 사유 |
|--------|------|------------|
| 소방시설법 화재예방법령집 | 8.5MB | OOM (docling 파싱 중 10GB 초과) |
| LLM 기반 AI 에이전트 기초와 실습 | 10.3MB | 배치 2-2 OOM으로 미도달 |
| 아키텍처팀 AI프로젝트 이해 워크샵 | 11.3MB | 배치 2-2 OOM으로 미도달 |
| 딥러닝과 RAG 기초과정 | 16.3MB | 배치 2-2 OOM으로 미도달 |
| 법령용어한영사전(법령용어부분) | 18.4MB | 초대형 (별도 배치 필요) |
| 법령용어한영사전(부록) | 25.4MB | 초대형 |
| 문화재관계법령집 | 68.1MB | 초대형 (WSL 16GB+ 필요) |
| 알기쉬운법령정비기준-7판 | 78.3MB | 초대형 (WSL 16GB+ 필요) |

---

## 기술 이슈 및 해결

### 1. 파일명 특수문자 이슈
- **문제**: docker exec + inline python에서 `'`(스마트 아포스트로피), `—`(em dash) 이스케이프 실패
- **해결**: Python 스크립트 파일(.py) 생성 → docker cp → 컨테이너 내 실행
- **교훈**: 특수 유니코드가 포함된 파일명은 inline 스크립트 대신 파일 기반으로

### 2. OOM Kill 패턴
- **1차 OOM** (이전 세션): 17건 연속 후 누적 메모리 (8GB 제한)
- **2차 OOM** (이번 세션): 소방시설법 단일 파일이 10GB 초과 (700+ 페이지 법령집)
- **원인**: docling의 테이블 파싱이 메모리 집약적 (TableItem 수천 개)
- **대응 방안**:
  - 법령집류는 페이지 분할 후 적재 (100페이지 단위)
  - 또는 WSL 메모리 16GB+로 증가

### 3. DB 비밀번호 불일치
- PG 비밀번호: `knowledge_dev_2026!` (env), 컨테이너 내에서 `knowledge`로 접속 불가
- 중복 체크 스크립트에서 DB 연결 실패 → 중복 체크 건너뛰고 진행
- 미처리 파일만 대상으로 했으므로 실제 중복 없음

---

## 주요 결정사항

| 결정 | 내용 | 근거 |
|------|------|------|
| ai-service 10GB | docker-compose.yml memory limit 증가 | 8GB로는 대형 법령집 파싱 불가 |
| 배치 스크립트 방식 | docker cp + python 파일 실행 | 특수문자 파일명 이스케이프 문제 |
| 초대형 파일 보류 | 18MB+ 파일 4건은 다음 세션 | WSL 메모리/분할 전략 필요 |

---

## 다음 세션 Action Items

### P0
1. **미처리 8건 적재 전략 수립**
   - 8.5~16MB: ai-service 메모리 증가 or 개별 재시도 (메모리 프레시 상태)
   - 18~78MB: WSL 메모리 16GB+ 또는 페이지 분할 파싱

### P1
2. Redis FLUSHALL (OOM 후 캐시 정리)
3. InitialDataLoader 중복 방지 구현 (file_hash 기반)
4. 12개 중지 컨테이너 복원 ✅ (이번 세션 완료)

### P2
5. 운영매뉴얼에 2차 배치 실행 로그 추가
6. ES chunk 수 업데이트 (PG documents.chunk_count 동기화)

---

## 변경된 파일 목록

```
infrastructure/docker/
└── docker-compose.yml                    # ai-service memory 8G → 10G

knowledge_service/
├── docs/05_development/
│   └── initial_data_loader_dedup_review.md  # 중복 방지 검토서 (신규)
├── docs/07_maintenance/
│   └── data_loading_operations_guide.md     # 운영매뉴얼 v1.4
├── scripts/
│   └── batch_load.py                        # 배치 적재 스크립트 (신규)

work_logs/
├── daily_logs/2026/02-February/2026-02-08.md     # 작업일지 업데이트
├── vibe_logs/2026/02-February/2026-02-08-vibe.md # 바이브로그 (신규)
├── standups/2026/02-February/2026-02-08_21-20.md # 스탠드업 기록 (이전 세션)
└── session_logs/
    └── 2026-02-08_batch2_document_loading.md     # 이 파일 (신규)

CLAUDE.md   # v2.25
PLAN.md     # Sprint 08 Day 4
README.md   # v4.6
```

---

## 세션 통계

| 항목 | 값 |
|------|-----|
| 적재 성공 | 13건 (배치 2-1: 7, 배치 2-2: 6) |
| OOM Kill | 1회 (소방시설법 8.5MB) |
| 생성된 chunks | ~2,291 (3,492 - 1,201) |
| 커밋 | 1건 (e365405) |
| Slack 메시지 | 6건 (진행 현황 보고) |
| 배치 실행 시간 | ~2.5시간 |

---

*기록자: Claude Code (Opus 4.6)*
*기록 시간: 2026-02-09 00:30 KST*
