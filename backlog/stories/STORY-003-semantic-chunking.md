# STORY-003: Semantic Chunking

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-8 |
| **Epic** | EPIC-001 |
| **Status** | To Do |
| **Priority** | Critical |
| **Story Points** | 8 |
| **Assignee** | - |
| **Sprint** | 2 |

---

## User Story

**As a** 시스템,
**I want** 파싱된 문서를 의미 단위로 분할,
**So that** 검색 시 관련성 높은 컨텍스트가 반환됨.

---

## Acceptance Criteria

- [ ] **Given** 긴 문서, **When** Semantic Chunking 적용, **Then** 의미적으로 완결된 청크로 분할
- [ ] **Given** 청크, **When** 크기 검증, **Then** 512-2048 토큰 범위 내
- [ ] **Given** 섹션 경계, **When** 청킹, **Then** 섹션 헤더가 청크 메타데이터에 포함
- [ ] **Given** 표/코드 블록, **When** 청킹, **Then** 분리되지 않고 단일 청크로 유지

---

## Tasks

- [ ] SemanticChunker 클래스 구현
- [ ] 임베딩 기반 유사도 청킹 구현
- [ ] 문장 경계 감지 (KoNLPy 활용)
- [ ] 청크 크기 최적화 로직
- [ ] 오버랩 설정 (10-20%)
- [ ] 특수 블록(표, 코드) 보존 로직
- [ ] 청크 메타데이터 생성 (위치, 섹션, 페이지)
- [ ] 단위 테스트 작성

---

## 기술 노트

### Chunking 전략
```python
from langchain.text_splitter import SemanticChunker
from langchain_community.embeddings import HuggingFaceEmbeddings

embeddings = HuggingFaceEmbeddings(
    model_name="BAAI/bge-m3"
)

chunker = SemanticChunker(
    embeddings=embeddings,
    breakpoint_threshold_type="percentile",
    breakpoint_threshold_amount=95,
)

chunks = chunker.split_text(document_text)
```

### 청크 구조
```python
@dataclass
class Chunk:
    id: str                    # UUID
    content: str               # 청크 텍스트
    document_id: str           # 원본 문서 ID
    position: int              # 문서 내 순서
    start_char: int            # 시작 위치
    end_char: int              # 끝 위치
    section_title: str         # 섹션 헤더
    page_number: int           # 페이지 번호
    token_count: int           # 토큰 수
    metadata: Dict             # 추가 메타데이터
```

### 파라미터 설정
| 파라미터 | 값 | 설명 |
|----------|-----|------|
| chunk_size | 1024 | 목표 청크 크기 (토큰) |
| chunk_overlap | 128 | 오버랩 크기 (토큰) |
| min_chunk_size | 256 | 최소 청크 크기 |
| max_chunk_size | 2048 | 최대 청크 크기 |

### 영향 범위
- `knowledge_service/src/app/etl/chunker.py` (신규)
- `knowledge_service/src/app/models/chunk.py` (신규)

---

## 테스트 계획

- [ ] Unit Test: 기본 청킹 로직
- [ ] Unit Test: 특수 블록 보존
- [ ] Unit Test: 한국어 문장 경계
- [ ] Integration Test: 실제 문서 청킹
- [ ] Quality Test: 청크 품질 점수 측정

### 품질 메트릭
```python
def evaluate_chunk_quality(chunks: List[Chunk]) -> float:
    """
    - 의미 완결성: 문장이 중간에 끊기지 않음
    - 크기 균일성: 청크 크기 분산이 낮음
    - 컨텍스트 보존: 관련 정보가 함께 유지됨
    """
```

---

## 참고 자료

- [LangChain SemanticChunker](https://python.langchain.com/docs/modules/data_connection/document_transformers/semantic-chunker)
- [Chunking 전략 비교](https://www.pinecone.io/learn/chunking-strategies/)
