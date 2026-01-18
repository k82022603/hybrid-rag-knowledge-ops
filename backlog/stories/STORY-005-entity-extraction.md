# STORY-005: Knowledge Graph 엔티티 추출

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | - |
| **Epic** | EPIC-001 |
| **Status** | ready |
| **Priority** | High |
| **Story Points** | 5 |
| **Assignee** | - |
| **Sprint** | 2 |

---

## User Story

**As a** 시스템,
**I want** 문서에서 엔티티와 관계를 자동 추출,
**So that** 문서 간 연결 관계를 파악하고 그래프 기반 검색이 가능함.

---

## Acceptance Criteria

- [ ] **Given** 텍스트 청크, **When** 엔티티 추출, **Then** 주요 개념/인물/조직 식별
- [ ] **Given** 추출된 엔티티, **When** 관계 추출, **Then** 엔티티 간 관계 유형 식별
- [ ] **Given** 동일 엔티티 다른 표현, **When** 정규화, **Then** 단일 노드로 통합
- [ ] **Given** 추출 결과, **When** 신뢰도 < 0.7, **Then** 수동 검토 플래그

---

## Tasks

- [ ] EntityExtractor 클래스 구현
- [ ] LLM 기반 엔티티 추출 (DeepSeek)
- [ ] 관계 추출 프롬프트 설계
- [ ] 엔티티 정규화/중복 제거
- [ ] 엔티티 타입 분류 (Person, Organization, Concept, etc.)
- [ ] 신뢰도 점수 계산
- [ ] 단위 테스트 작성

---

## 기술 노트

### 엔티티 추출 프롬프트
```python
ENTITY_EXTRACTION_PROMPT = """
다음 텍스트에서 주요 엔티티와 관계를 추출하세요.

텍스트:
{text}

출력 형식 (JSON):
{
  "entities": [
    {"name": "엔티티명", "type": "타입", "confidence": 0.95}
  ],
  "relations": [
    {"source": "엔티티1", "target": "엔티티2", "type": "관계유형", "confidence": 0.9}
  ]
}
"""
```

### 엔티티 타입
| 타입 | 설명 | 예시 |
|------|------|------|
| Person | 인물 | 김철수, Elon Musk |
| Organization | 조직/회사 | 삼성전자, OpenAI |
| Concept | 개념/기술 | RAG, Knowledge Graph |
| Product | 제품/서비스 | ChatGPT, Claude |
| Date | 날짜/기간 | 2024년, Q1 |
| Location | 장소 | 서울, Silicon Valley |

### 관계 타입
| 관계 | 설명 |
|------|------|
| RELATED_TO | 일반 관련 |
| PART_OF | 포함 관계 |
| WORKS_FOR | 소속 관계 |
| CREATED_BY | 생성 관계 |
| DEPENDS_ON | 의존 관계 |
| SIMILAR_TO | 유사 관계 |

### 출력 구조
```python
@dataclass
class ExtractedEntity:
    name: str               # 정규화된 이름
    type: EntityType        # 엔티티 타입
    aliases: List[str]      # 다른 표현들
    confidence: float       # 신뢰도 (0-1)
    source_chunks: List[str]  # 출처 청크 ID

@dataclass
class ExtractedRelation:
    source: str             # 소스 엔티티
    target: str             # 타겟 엔티티
    type: RelationType      # 관계 유형
    confidence: float       # 신뢰도
    evidence: str           # 근거 텍스트
```

### 영향 범위
- `knowledge_service/src/app/graph/entity_extractor.py` (신규)
- `knowledge_service/src/app/graph/relation_extractor.py` (신규)
- `knowledge_service/src/app/models/entity.py` (신규)

---

## 테스트 계획

- [ ] Unit Test: 단일 텍스트 엔티티 추출
- [ ] Unit Test: 관계 추출
- [ ] Unit Test: 엔티티 정규화
- [ ] Integration Test: 실제 문서 처리
- [ ] Quality Test: Precision/Recall 측정

### 테스트 케이스
```python
def test_entity_extraction():
    text = "OpenAI의 CEO Sam Altman이 GPT-4를 발표했다."
    result = extractor.extract(text)

    assert "OpenAI" in [e.name for e in result.entities]
    assert "Sam Altman" in [e.name for e in result.entities]
    assert any(r.type == "WORKS_FOR" for r in result.relations)
```

---

## 참고 자료

- [LangChain Graph Extraction](https://python.langchain.com/docs/use_cases/graph/constructing)
- [Neo4j NLP](https://neo4j.com/labs/neosemantics/)
