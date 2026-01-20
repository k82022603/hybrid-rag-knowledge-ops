# STORY-011: 데이터베이스 초기화

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-11 |
| **Epic** | EPIC-000 Infrastructure |
| **Status** | Done |
| **Priority** | Critical |
| **Story Points** | 3 |
| **Assignee** | Data |
| **Sprint** | 1 |

---

## 사용자 스토리

**As a** 개발자
**I want** 데이터베이스 스키마가 자동으로 초기화되기를
**So that** 별도 설정 없이 개발을 시작할 수 있다

---

## Acceptance Criteria

### AC1: PostgreSQL 스키마
```gherkin
Given PostgreSQL 컨테이너가 시작되면
When 초기화 스크립트가 실행되면
Then knowledge, keycloak 데이터베이스가 생성된다
And 기본 테이블(documents, users, bookmarks)이 생성된다
```

### AC2: Elasticsearch 인덱스
```gherkin
Given Elasticsearch 컨테이너가 healthy 상태일 때
When 인덱스 생성 스크립트가 실행되면
Then knowledge_chunks 인덱스가 생성된다
And 벡터 필드(1024차원)가 설정된다
```

### AC3: Neo4j 제약조건
```gherkin
Given Neo4j 컨테이너가 시작되면
When 초기화 쿼리가 실행되면
Then Document, Chunk, Entity 노드 제약조건이 생성된다
And 필요한 인덱스가 생성된다
```

---

## 기술 명세

### PostgreSQL 스키마
```sql
-- knowledge 데이터베이스
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    file_path VARCHAR(1000),
    doc_type VARCHAR(50),
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id),
    content TEXT NOT NULL,
    chunk_index INTEGER,
    metadata JSONB
);
```

### Elasticsearch 매핑
```json
{
  "mappings": {
    "properties": {
      "content": { "type": "text", "analyzer": "korean" },
      "embedding": { "type": "dense_vector", "dims": 1024, "index": true, "similarity": "cosine" },
      "document_id": { "type": "keyword" },
      "chunk_index": { "type": "integer" },
      "metadata": { "type": "object", "enabled": true }
    }
  }
}
```

### Neo4j 제약조건
```cypher
CREATE CONSTRAINT document_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE;
CREATE CONSTRAINT chunk_id IF NOT EXISTS FOR (c:Chunk) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT entity_name IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE;
CREATE INDEX chunk_document IF NOT EXISTS FOR (c:Chunk) ON (c.document_id);
```

---

## 작업 분해

- [ ] PostgreSQL 초기화 SQL 작성
- [ ] Elasticsearch 인덱스 템플릿 작성
- [ ] Neo4j 제약조건/인덱스 Cypher 작성
- [ ] 초기화 스크립트 작성 (init-db.sh)
- [ ] 자동 실행 설정 (docker-entrypoint)
- [ ] 검증 테스트

---

## 참고 자료

- [인프라 설계서](../../knowledge_service/docs/02_design/infrastructure_detailed_design.md)
