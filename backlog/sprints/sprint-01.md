# Sprint 01: Document Processing 기반 구축

## 스프린트 정보

| 항목 | 값 |
|------|-----|
| **기간** | 2026-01-20 ~ 2026-01-31 (2주) |
| **Velocity (계획)** | 19 pts |
| **Velocity (실제)** | - |
| **Status** | planning |

---

## 스프린트 목표

> **문서 업로드부터 Semantic Chunking까지의 ETL 파이프라인 1단계 완성**

핵심 목표:
1. 다양한 형식의 문서를 업로드하고 저장하는 API 구현
2. Docling 기반 고품질 문서 파싱 (97%+ 정확도)
3. 의미 기반 청킹으로 검색 품질 기반 마련

---

## 백로그

### Committed (19 pts)

| Priority | ID | 제목 | Points | Assignee | Status |
|----------|-----|------|--------|----------|--------|
| P0 | STORY-001 | 문서 업로드 API | 3 | - | To Do |
| P0 | STORY-002 | Docling 문서 파싱 | 8 | - | To Do |
| P0 | STORY-003 | Semantic Chunking | 8 | - | To Do |

### Stretch (여유 시 추가)

| ID | 제목 | Points |
|----|------|--------|
| - | HWP 파서 고도화 (pyhwpx 최적화) | 3 |
| - | 업로드 진행률 WebSocket 알림 | 2 |

---

## 기술 의존성 (사전 준비)

### 인프라 (Sprint 시작 전 완료 필요)
- [ ] MinIO 컨테이너 설정
- [ ] PostgreSQL 스키마 초기화
- [ ] Redis 캐시 설정
- [ ] Celery Worker 설정

### 개발 환경
- [ ] Python 3.11+ 환경 구성
- [ ] Poetry 의존성 설치
- [ ] Docling 모델 다운로드
- [ ] BGE-M3 모델 다운로드 (청킹용)

---

## 일일 계획

### Week 1

#### Day 1 (01-20, Mon)
- [ ] 스프린트 킥오프 미팅
- [ ] 개발 환경 최종 점검
- [ ] STORY-001 착수: API 엔드포인트 설계

#### Day 2 (01-21, Tue)
- [ ] STORY-001: FastAPI 엔드포인트 구현
- [ ] STORY-001: 파일 검증 로직

#### Day 3 (01-22, Wed)
- [ ] STORY-001: MinIO 업로드 서비스
- [ ] STORY-001: 단위 테스트 작성

#### Day 4 (01-23, Thu)
- [ ] STORY-001: 통합 테스트 및 완료
- [ ] STORY-002 착수: Docling 환경 설정

#### Day 5 (01-24, Fri)
- [ ] STORY-002: PDF 파서 구현
- [ ] Week 1 리뷰

### Week 2

#### Day 6 (01-27, Mon)
- [ ] STORY-002: DOCX/HWP 파서 구현
- [ ] STORY-002: 파싱 결과 표준화

#### Day 7 (01-28, Tue)
- [ ] STORY-002: 테스트 및 완료
- [ ] STORY-003 착수: Chunker 설계

#### Day 8 (01-29, Wed)
- [ ] STORY-003: SemanticChunker 구현
- [ ] STORY-003: 한국어 문장 경계 처리

#### Day 9 (01-30, Thu)
- [ ] STORY-003: 특수 블록 보존 로직
- [ ] STORY-003: 테스트 작성

#### Day 10 (01-31, Fri)
- [ ] STORY-003 완료
- [ ] 스프린트 리뷰 & 회고
- [ ] Sprint 2 계획 준비

---

## Definition of Done

각 Story 완료 기준:
- [ ] 모든 Acceptance Criteria 충족
- [ ] 단위 테스트 작성 (커버리지 80%+)
- [ ] 코드 리뷰 완료
- [ ] API 문서 업데이트 (해당 시)
- [ ] 기술 부채 없음

---

## 리스크 및 블로커

| 유형 | 설명 | 영향 | 대응 | 상태 |
|------|------|------|------|------|
| Risk | HWP 파싱 정확도 미달 | Medium | pyhwpx 폴백 준비 | Monitoring |
| Risk | Docling 모델 다운로드 지연 | Low | 사전 다운로드 완료 | Resolved |
| Blocker | MinIO 미설정 | High | 인프라 사전 준비 | Open |

---

## 산출물

### 코드
```
knowledge_service/src/app/
├── api/routes/
│   └── documents.py          # STORY-001
├── services/
│   └── storage.py            # STORY-001
├── etl/
│   ├── parser.py             # STORY-002
│   ├── docling_adapter.py    # STORY-002
│   └── chunker.py            # STORY-003
└── models/
    ├── document.py           # STORY-001
    ├── parsed_document.py    # STORY-002
    └── chunk.py              # STORY-003
```

### 테스트
```
knowledge_service/src/tests/
├── test_document_api.py
├── test_parser.py
└── test_chunker.py
```

### 문서
- [ ] API 문서 (OpenAPI/Swagger)
- [ ] ETL 파이프라인 아키텍처 다이어그램
- [ ] 파싱 정확도 벤치마크 결과

---

## 메트릭 목표

| 메트릭 | 목표 | 측정 방법 |
|--------|------|-----------|
| 문서 파싱 정확도 | ≥ 97% | Ground Truth 비교 |
| 업로드 API 응답시간 | < 500ms | pytest-benchmark |
| 청크 품질 점수 | ≥ 0.85 | 커스텀 평가 함수 |
| 테스트 커버리지 | ≥ 80% | pytest-cov |

---

## 스프린트 리뷰

### 완료된 항목
- (스프린트 종료 후 작성)

### 미완료 항목
- (스프린트 종료 후 작성)

### 데모 노트
- (스프린트 종료 후 작성)

---

## 회고 (Retrospective)

### Keep (계속할 것)
-

### Problem (문제점)
-

### Try (시도할 것)
-

---

## 참고 자료

- [EPIC-001: Document Processing](../epics/EPIC-001-document-processing.md)
- [STORY-001: 문서 업로드 API](../stories/STORY-001-document-upload-api.md)
- [STORY-002: Docling 문서 파싱](../stories/STORY-002-docling-parser.md)
- [STORY-003: Semantic Chunking](../stories/STORY-003-semantic-chunking.md)
