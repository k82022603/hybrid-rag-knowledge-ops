# EPIC-001: Document Processing Pipeline

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-5 |
| **Status** | ready |
| **Priority** | Critical |
| **Owner** | TBD |
| **Target Sprint** | Sprint 2 |
| **Total Story Points** | 34 |

---

## 요약

문서 업로드부터 Knowledge Graph 생성까지의 전체 ETL 파이프라인 구축. Docling 기반 문서 파싱, Semantic Chunking, BGE-M3 임베딩을 통해 다양한 형식의 문서를 처리하고 Neo4j + Elasticsearch에 저장.

---

## 배경 및 목표

### 배경
- 기업 내 다양한 형식의 문서(PDF, DOCX, HWP, PPT)가 산재
- 기존 키워드 검색으로는 의미 기반 검색 불가
- 문서 간 관계 파악이 어려움

### 목표
- 97%+ 정확도의 문서 파싱 (Docling)
- 의미 기반 청킹으로 컨텍스트 보존
- Knowledge Graph 자동 생성으로 문서 간 관계 추출

### 성공 지표
- [ ] 문서 파싱 정확도 >= 97%
- [ ] 평균 처리 시간 < 30초/문서
- [ ] 청크 품질 점수 >= 0.85
- [ ] 고아 노드 비율 < 1%

---

## User Stories

| ID | Jira | 제목 | Points | Status | Sprint |
|----|------|------|--------|--------|--------|
| STORY-001 | SCRUM-6 | 문서 업로드 API | 3 | To Do | 2 |
| STORY-002 | SCRUM-7 | Docling 문서 파싱 | 8 | To Do | 2 |
| STORY-003 | SCRUM-8 | Semantic Chunking | 8 | To Do | 2 |
| STORY-004 | - | BGE-M3 임베딩 생성 | 5 | draft | 3 |
| STORY-005 | - | Knowledge Graph 엔티티 추출 | 5 | draft | 3 |
| STORY-006 | - | Neo4j/ES 저장 | 5 | draft | 3 |

---

## 아키텍처

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Upload    │────▶│   Docling   │────▶│  Semantic   │
│    API      │     │   Parser    │     │  Chunker    │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          │                          │
                    ▼                          ▼                          ▼
            ┌─────────────┐            ┌─────────────┐            ┌─────────────┐
            │   BGE-M3    │            │   Entity    │            │  Metadata   │
            │  Embedding  │            │  Extractor  │            │  Extractor  │
            └──────┬──────┘            └──────┬──────┘            └──────┬──────┘
                   │                          │                          │
                   ▼                          ▼                          ▼
            ┌─────────────┐            ┌─────────────┐            ┌─────────────┐
            │Elasticsearch│            │    Neo4j    │            │ PostgreSQL  │
            │  (Vector)   │            │   (Graph)   │            │   (SSOT)    │
            └─────────────┘            └─────────────┘            └─────────────┘
```

---

## 기술 요구사항

### 지원 문서 형식
| 형식 | 라이브러리 | 우선순위 |
|------|-----------|----------|
| PDF | Docling | P0 |
| DOCX | Docling | P0 |
| HWP | hwp5, pyhwpx | P1 |
| PPTX | python-pptx | P1 |
| Markdown | 직접 처리 | P2 |

### 기술 스택
- **파싱**: Docling (97.9% 정확도)
- **청킹**: Semantic Chunking (LangChain)
- **임베딩**: BGE-M3 (다국어, 1024차원)
- **그래프**: Neo4j 5.x + APOC
- **벡터**: Elasticsearch 8.x (HNSW)
- **메타데이터**: PostgreSQL 16

### 성능 요구사항
| 항목 | 목표 |
|------|------|
| 단일 문서 처리 | < 30초 |
| 배치 처리 (100개) | < 10분 |
| 동시 처리 | 5개 병렬 |

---

## 선행 조건 (Sprint 1 완료 필요)

- [ ] Docker Compose 환경 구축 (STORY-010)
- [ ] 데이터베이스 초기화 (STORY-011)
- [ ] MinIO 스토리지 설정
- [ ] 프로젝트 골격 생성 (STORY-013)

---

## 리스크 및 의존성

### 리스크
| 리스크 | 영향 | 대응 |
|--------|------|------|
| HWP 파싱 정확도 | Medium | pyhwpx 폴백, 수동 검토 |
| 대용량 문서 메모리 | High | 스트리밍 처리, 청크 분할 |
| 임베딩 API 비용 | Medium | 로컬 BGE-M3 모델 사용 |

### 의존성
- [ ] MinIO 스토리지 설정 (인프라)
- [ ] Neo4j 스키마 초기화 (데이터)
- [ ] Elasticsearch 인덱스 생성 (데이터)

---

## 참고 자료

- [상세 설계서 v2.4](../../knowledge_service/docs/02_design/hybrid_rag_platform_detailed_design.md)
- [ETL 파이프라인 설계](../../knowledge_service/docs/02_design/)
- [Docling 공식 문서](https://github.com/DS4SD/docling)
