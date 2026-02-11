# STORY-006: Neo4j/Elasticsearch 저장

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-36 |
| **Epic** | EPIC-001 |
| **Status** | Done |
| **Priority** | High |
| **Story Points** | 5 |
| **Assignee** | Data |
| **Sprint** | 3 |

---

## User Story

**As a** 시스템,
**I want** 처리된 데이터를 Neo4j와 Elasticsearch에 저장,
**So that** Graph 검색과 Vector 검색이 모두 가능함.

---

## Acceptance Criteria

- [ ] **Given** 엔티티/관계 데이터, **When** Neo4j 저장, **Then** 노드와 엣지가 올바르게 생성
- [ ] **Given** 청크와 임베딩, **When** ES 저장, **Then** 벡터 인덱스에 저장되고 검색 가능
- [ ] **Given** 중복 엔티티, **When** 저장 시도, **Then** 기존 노드에 병합 (MERGE)
- [ ] **Given** 저장 실패, **When** 트랜잭션 롤백, **Then** 데이터 일관성 유지

---

## Tasks

- [ ] Neo4j 저장 서비스 구현
- [ ] Elasticsearch 저장 서비스 구현
- [ ] 트랜잭션 관리 (2PC 패턴)
- [ ] 벌크 저장 최적화
- [ ] 인덱스 최적화 쿼리
- [ ] 데이터 검증 로직
- [ ] 단위 테스트 작성

---

## 기술 노트

### Neo4j 스키마
```cypher
// 노드 생성
CREATE CONSTRAINT entity_name IF NOT EXISTS
FOR (e:Entity) REQUIRE e.name IS UNIQUE;

CREATE CONSTRAINT document_id IF NOT EXISTS
FOR (d:Document) REQUIRE d.id IS UNIQUE;

CREATE CONSTRAINT chunk_id IF NOT EXISTS
FOR (c:Chunk) REQUIRE c.id IS UNIQUE;

// 인덱스
CREATE INDEX entity_type IF NOT EXISTS
FOR (e:Entity) ON (e.type);
```

### Neo4j 저장 로직
```python
from neo4j import GraphDatabase

class Neo4jStorage:
    def save_entity(self, entity: Entity):
        query = """
        MERGE (e:Entity {name: $name})
        SET e.type = $type,
            e.aliases = $aliases,
            e.updated_at = datetime()
        RETURN e
        """

    def save_relation(self, relation: Relation):
        query = """
        MATCH (s:Entity {name: $source})
        MATCH (t:Entity {name: $target})
        MERGE (s)-[r:RELATED_TO {type: $rel_type}]->(t)
        SET r.weight = $weight,
            r.evidence = $evidence
        """
```

### Elasticsearch 인덱스
```json
{
  "mappings": {
    "properties": {
      "chunk_id": { "type": "keyword" },
      "document_id": { "type": "keyword" },
      "content": {
        "type": "text",
        "analyzer": "korean"
      },
      "embedding": {
        "type": "dense_vector",
        "dims": 1024,
        "index": true,
        "similarity": "cosine"
      },
      "metadata": { "type": "object" }
    }
  }
}
```

### Elasticsearch 저장 로직
```python
from elasticsearch import Elasticsearch, helpers

class ESStorage:
    def bulk_save_chunks(self, chunks: List[ChunkWithEmbedding]):
        actions = [
            {
                "_index": "knowledge_chunks",
                "_id": chunk.id,
                "_source": {
                    "chunk_id": chunk.id,
                    "document_id": chunk.document_id,
                    "content": chunk.content,
                    "embedding": chunk.embedding,
                    "metadata": chunk.metadata
                }
            }
            for chunk in chunks
        ]
        helpers.bulk(self.client, actions)
```

### 트랜잭션 관리
```python
async def save_document_data(
    document_id: str,
    entities: List[Entity],
    relations: List[Relation],
    chunks: List[ChunkWithEmbedding]
):
    try:
        # 1. PostgreSQL 메타데이터 저장
        await pg_storage.save_document_meta(document_id)

        # 2. Neo4j 그래프 저장
        await neo4j_storage.save_entities(entities)
        await neo4j_storage.save_relations(relations)

        # 3. Elasticsearch 벡터 저장
        await es_storage.bulk_save_chunks(chunks)

        # 4. 상태 업데이트
        await pg_storage.update_status(document_id, "completed")

    except Exception as e:
        # 롤백 처리
        await rollback_all(document_id)
        raise
```

### 영향 범위
- `knowledge_service/src/app/storage/neo4j_storage.py` (신규)
- `knowledge_service/src/app/storage/es_storage.py` (신규)
- `knowledge_service/src/app/storage/transaction.py` (신규)

---

## 테스트 계획

- [ ] Unit Test: Neo4j CRUD
- [ ] Unit Test: Elasticsearch CRUD
- [ ] Unit Test: 벌크 저장
- [ ] Integration Test: 전체 저장 플로우
- [ ] Integration Test: 롤백 시나리오

### 테스트 환경
```yaml
# docker-compose.test.yml
services:
  neo4j-test:
    image: neo4j:5-community
    environment:
      - NEO4J_AUTH=none

  elasticsearch-test:
    image: elasticsearch:8.12.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
```

---

## 참고 자료

- [Neo4j Python Driver](https://neo4j.com/docs/python-manual/current/)
- [Elasticsearch Python Client](https://elasticsearch-py.readthedocs.io/)
- [인프라 설계서](../../knowledge_service/docs/02_design/10_infrastructure_detailed_design.md)
