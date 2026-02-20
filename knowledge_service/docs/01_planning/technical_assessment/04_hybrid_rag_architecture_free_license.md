# Elasticsearch Basic 라이선스 기반 하이브리드 RAG 아키텍처 [#](https://claude.ai/public/artifacts/01a08f49-fcd4-4056-84db-d9f6609030b7)

> **현행화 정보**
> - **최종 현행화**: 2026-02-20
> - **프로젝트 상태**: 종료 (2026-02-18)
> - **구현 상태**: 구현완료 (주요 변경사항 있음)
> - **주요 변경사항**: 전체 3-DB 아키텍처(PG+Neo4j+ES)와 하이브리드 검색 전략은 구현됨. 임베딩 모델 변경: BGE-M3(1024차원) → `jhgan/ko-sroberta-multitask`(768차원). RRF 구현: ranx 라이브러리 → 자체 구현(`src/app/services/rrf_fusion.py`). Docling 파서 적용. ETL은 3-Phase 분리 전략으로 진화. Nori 플러그인 커스텀 Dockerfile 설치 필수 (2026-02-13 사고 교훈). Neo4j APOC 활용한 그래프 연결 구현. ES 인덱스명: `knowledge_chunks`.

## 검토 결과 요약

제안하신 아키텍처의 핵심 설계는 우수합니다. 다만 **무료 라이선스 제약**을 반영하여 다음 사항을 수정했습니다.

| 항목 | 원본 | 수정 | 이유 |
|------|------|------|------|
| RRF 사용 | ES 내장 RRF | Python ranx 라이브러리 | RRF는 Platinum 전용 |
| Sparse 검색 | ES 내부 처리 | BGE-M3 외부 생성 + ES 저장 | ELSER 불필요, Basic에서 가능 |
| 하이브리드 쿼리 | 단일 ES 쿼리 | 2회 쿼리 + Python 융합 | RRF 제약 우회 |

> ⚠️ **실제 구현**: RRF는 `ranx`가 아닌 Python 자체 구현(`src/app/services/rrf_fusion.py`). 임베딩은 BGE-M3 대신 `jhgan/ko-sroberta-multitask` (768차원). 검색은 Dense + Sparse + BM25 + Graph 4중 융합으로 확장됨. `src/app/services/search.py`, `src/app/rag/retriever.py` 참조.

---

## 수정된 아키텍처 개요

### 시스템 구성도

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Hybrid RAG Knowledge Ops                          │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                 │
│  │ PostgreSQL  │    │    Neo4j    │    │Elasticsearch│                 │
│  │   (1GB)     │    │   (2GB)     │    │   (4GB)     │                 │
│  │  ─────────  │    │  ─────────  │    │  ─────────  │                 │
│  │  시계열 SSOT │    │  지식 그래프 │    │ Dense+Sparse│                 │
│  │  프로젝트 정보│    │  관계 탐색   │    │ +BM25+메타  │                 │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘                 │
│         │                  │                  │                         │
│         └──────────────────┼──────────────────┘                         │
│                            │                                            │
│  ┌─────────────────────────┴─────────────────────────┐                 │
│  │              Python Orchestration Layer            │                 │
│  │  ┌─────────────┐  ┌─────────────┐  ┌───────────┐ │                 │
│  │  │   BGE-M3    │  │    ranx     │  │ LangGraph │ │                 │
│  │  │ (2-3GB CPU) │  │  RRF 융합   │  │  에이전트  │ │                 │
│  │  └─────────────┘  └─────────────┘  └───────────┘ │                 │
│  └───────────────────────────────────────────────────┘                 │
└─────────────────────────────────────────────────────────────────────────┘
```

### 메모리 분배 (16GB 기준)

| 컴포넌트 | 할당 | 역할 | 변경사항 |
|---------|------|------|---------|
| Elasticsearch | 4GB | Dense + Sparse + BM25 벡터 저장, 메타데이터 필터링 | 동일 |
| Neo4j | 2GB | Slim 지식 그래프 | 동일 |
| PostgreSQL | 1GB | 시계열 메타데이터 마스터 | 동일 |
| BGE-M3 (CPU) | 2-3GB | Dense + Sparse 임베딩 생성 | 동일 |
| Python + ranx | ~500MB | RRF 융합 처리 | **추가** |
| OS & LangGraph | 5-6GB | 시스템 운영 | 조정 |

---

## Elasticsearch 단일 문서 구조

### 핵심 개념: 하나의 문서에 모든 검색 요소 통합

Elasticsearch의 각 청크 문서는 **Dense Vector + Sparse Vector + BM25 텍스트 + 메타데이터**를 모두 포함합니다. 이를 통해 단일 인덱스에서 다양한 검색 방식을 조합할 수 있습니다.

> ⚠️ **실제 구현**: ES 인덱스명 `knowledge_chunks` 동일하게 사용됨 (alias 아님, v2 아님). 실제 필드 구조는 `dense_vector`, `sparse_vector`, `text`(chunk_text 대신), `heading` 등 일부 필드명 차이 있음. `entities` 필드는 ETL Phase 3 이후 채워짐.

```json
{
  "_index": "knowledge_chunks",
  "_id": "chunk_doc123_001",
  "_source": {
    "chunk_id": "chunk_doc123_001",
    "chunk_index": 1,
    
    "chunk_text": "2025년 1분기 Alpha 프로젝트 진행 보고서입니다. React와 Neo4j를 활용한 지식 관리 시스템을 구축했습니다...",
    
    "dense_vector": [0.0234, -0.1567, 0.0891, ...],
    
    "sparse_vector": {
      "프로젝트": 2.134,
      "보고서": 1.876,
      "react": 1.654,
      "neo4j": 1.543,
      "지식": 1.234,
      "관리": 0.987,
      "시스템": 0.876
    },
    
    "document_id": "doc123",
    "document_type": "프로젝트_보고서",
    "project_name": "Alpha",
    "valid_start_date": "2025-01-01",
    "valid_end_date": "2025-12-31",
    "ingestion_timestamp": "2025-01-15T09:30:00Z",
    
    "entities": {
      "persons": ["김철수", "이영희"],
      "projects": ["Alpha", "Beta"],
      "technologies": ["React", "Neo4j", "Python"],
      "keywords": ["지식관리", "RAG", "하이브리드검색"]
    }
  }
}
```

### 각 필드의 검색 역할

| 필드 | 타입 | 검색 방식 | 용도 |
|------|------|----------|------|
| `chunk_text` | text | BM25 키워드 검색 | 정확한 용어 매칭, 백업 검색 |
| `dense_vector` | dense_vector | kNN 코사인 유사도 | 의미적 유사성 검색 |
| `sparse_vector` | sparse_vector | 토큰 가중치 매칭 | 학습된 키워드 확장 검색 |
| `document_type` | keyword | term 필터 | 문서 유형별 필터링 |
| `project_name` | keyword | term 필터 | 프로젝트별 필터링 |
| `valid_*_date` | date | range 필터 | 시계열 필터링 |
| `entities.*` | keyword | terms 필터 | 엔티티 기반 필터링 |

### 인덱스 매핑 (Basic 라이선스 호환)

> ⚠️ **실제 구현**: 매핑에서 `analyzer: "korean_analyzer"` → `nori_tokenizer` 기반 한국어 분석기 사용. `dense_vector` 차원: 계획 1024차원 → 실제 768차원(ko-sroberta). Nori 플러그인은 커스텀 Dockerfile로 설치 필수. 2026-02-13 이전 32일간 Nori 미설치 상태로 운영된 사고가 있었음.

```json
{
  "mappings": {
    "properties": {
      "chunk_id": { "type": "keyword" },
      "chunk_index": { "type": "integer" },
      
      "chunk_text": { 
        "type": "text",
        "analyzer": "korean_analyzer",
        "fields": {
          "keyword": { "type": "keyword", "ignore_above": 256 }
        }
      },
      
      "dense_vector": {
        "type": "dense_vector",
        "dims": 1024,
        "index": true,
        "similarity": "cosine"
      },
      
      "sparse_vector": {
        "type": "sparse_vector"
      },
      
      "document_id": { "type": "keyword" },
      "document_type": { "type": "keyword" },
      "project_name": { "type": "keyword" },
      "valid_start_date": { "type": "date", "format": "yyyy-MM-dd" },
      "valid_end_date": { "type": "date", "format": "yyyy-MM-dd" },
      "ingestion_timestamp": { "type": "date" },
      
      "entities": {
        "properties": {
          "persons": { "type": "keyword" },
          "projects": { "type": "keyword" },
          "technologies": { "type": "keyword" },
          "keywords": { "type": "keyword" }
        }
      }
    }
  },
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0,
    "analysis": {
      "analyzer": {
        "korean_analyzer": {
          "type": "custom",
          "tokenizer": "nori_tokenizer",
          "filter": ["lowercase", "nori_part_of_speech"]
        }
      }
    }
  }
}
```

---

## PostgreSQL 저장 구조

### 역할: 단일 진실 공급원 (SSOT)

PostgreSQL은 **문서 마스터 정보**와 **시계열 데이터**를 관리합니다. Elasticsearch의 메타데이터가 손상되더라도 PostgreSQL에서 복구할 수 있습니다.

### 테이블 스키마

> ⚠️ **실제 구현**: DB명은 `knowledge` (NOT `knowledge_platform`). 접속: `psql -U knowledge -d knowledge`. 실제 주요 테이블은 설계와 유사하나 일부 차이 있음. `asyncpg` 대신 SQLAlchemy ORM도 혼용됨.

```sql
-- 1. 문서 마스터 테이블 (SSOT)
CREATE TABLE knowledge_master (
    document_id         VARCHAR(64) PRIMARY KEY,
    file_path           TEXT NOT NULL,
    file_hash           VARCHAR(64) NOT NULL,  -- 중복 감지용
    
    -- 분류 정보
    document_type       VARCHAR(50) NOT NULL,
    project_name        VARCHAR(100),
    
    -- 시계열 정보 (핵심)
    valid_start_date    DATE NOT NULL,
    valid_end_date      DATE NOT NULL DEFAULT '9999-12-31',
    
    -- 요약 및 메타
    summary             TEXT,
    total_chunks        INTEGER DEFAULT 0,
    total_tokens        INTEGER DEFAULT 0,
    
    -- 감사 정보
    created_by          VARCHAR(100),
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 상태 관리
    status              VARCHAR(20) DEFAULT 'active',  -- active, archived, deleted
    
    CONSTRAINT valid_date_range CHECK (valid_end_date >= valid_start_date)
);

-- 2. 청크 참조 테이블 (ES 동기화 추적)
CREATE TABLE chunk_references (
    chunk_id            VARCHAR(128) PRIMARY KEY,
    document_id         VARCHAR(64) REFERENCES knowledge_master(document_id),
    chunk_index         INTEGER NOT NULL,
    
    -- ES 동기화 상태
    es_indexed          BOOLEAN DEFAULT FALSE,
    es_indexed_at       TIMESTAMP,
    
    -- 청크 메타
    token_count         INTEGER,
    
    UNIQUE(document_id, chunk_index)
);

-- 3. 엔티티 테이블 (정규화)
CREATE TABLE entities (
    entity_id           SERIAL PRIMARY KEY,
    entity_type         VARCHAR(50) NOT NULL,  -- person, project, technology, keyword
    entity_value        VARCHAR(255) NOT NULL,
    
    UNIQUE(entity_type, entity_value)
);

-- 4. 문서-엔티티 연결 테이블
CREATE TABLE document_entities (
    document_id         VARCHAR(64) REFERENCES knowledge_master(document_id),
    entity_id           INTEGER REFERENCES entities(entity_id),
    confidence          FLOAT DEFAULT 1.0,  -- DeepSeek 추출 신뢰도
    
    PRIMARY KEY (document_id, entity_id)
);

-- 5. 프로젝트 테이블
CREATE TABLE projects (
    project_id          VARCHAR(64) PRIMARY KEY,
    project_name        VARCHAR(100) NOT NULL UNIQUE,
    description         TEXT,
    start_date          DATE,
    end_date            DATE,
    status              VARCHAR(20) DEFAULT 'active',
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. 인덱스 생성 (검색 최적화)
CREATE INDEX idx_km_project ON knowledge_master(project_name);
CREATE INDEX idx_km_type ON knowledge_master(document_type);
CREATE INDEX idx_km_valid_dates ON knowledge_master(valid_start_date, valid_end_date);
CREATE INDEX idx_km_status ON knowledge_master(status);
CREATE INDEX idx_cr_document ON chunk_references(document_id);
CREATE INDEX idx_entities_type ON entities(entity_type);

-- 7. 시계열 쿼리용 함수
CREATE OR REPLACE FUNCTION get_valid_documents(
    p_project VARCHAR DEFAULT NULL,
    p_as_of_date DATE DEFAULT CURRENT_DATE
)
RETURNS TABLE (
    document_id VARCHAR,
    document_type VARCHAR,
    project_name VARCHAR,
    summary TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        km.document_id,
        km.document_type,
        km.project_name,
        km.summary
    FROM knowledge_master km
    WHERE km.status = 'active'
      AND km.valid_start_date <= p_as_of_date
      AND km.valid_end_date >= p_as_of_date
      AND (p_project IS NULL OR km.project_name = p_project);
END;
$$ LANGUAGE plpgsql;
```

### PostgreSQL 저장 함수

```python
import asyncpg
from datetime import datetime
from typing import Dict, Optional

class PostgreSQLStorage:
    """PostgreSQL 마스터 레코드 관리"""
    
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
    
    async def save_document_master(self, metadata: Dict) -> str:
        """문서 마스터 정보 저장 (Upsert)"""
        
        query = """
        INSERT INTO knowledge_master (
            document_id, file_path, file_hash,
            document_type, project_name,
            valid_start_date, valid_end_date,
            summary, total_chunks, created_by
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        ON CONFLICT (document_id) DO UPDATE SET
            document_type = EXCLUDED.document_type,
            project_name = EXCLUDED.project_name,
            valid_start_date = EXCLUDED.valid_start_date,
            valid_end_date = EXCLUDED.valid_end_date,
            summary = EXCLUDED.summary,
            total_chunks = EXCLUDED.total_chunks,
            updated_at = CURRENT_TIMESTAMP
        RETURNING document_id
        """
        
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                query,
                metadata['document_id'],
                metadata['file_path'],
                metadata['file_hash'],
                metadata['document_type'],
                metadata.get('project_name'),
                metadata['valid_start_date'],
                metadata.get('valid_end_date', '9999-12-31'),
                metadata.get('summary'),
                metadata.get('total_chunks', 0),
                metadata.get('created_by', 'system')
            )
            
            # 엔티티 저장
            await self._save_entities(conn, metadata)
            
            return result
    
    async def _save_entities(self, conn, metadata: Dict):
        """엔티티 추출 결과 저장"""
        
        entities = metadata.get('entities', {})
        document_id = metadata['document_id']
        
        for entity_type, values in entities.items():
            for value in values:
                # 엔티티 Upsert
                entity_id = await conn.fetchval("""
                    INSERT INTO entities (entity_type, entity_value)
                    VALUES ($1, $2)
                    ON CONFLICT (entity_type, entity_value) DO UPDATE
                    SET entity_value = EXCLUDED.entity_value
                    RETURNING entity_id
                """, entity_type, value)
                
                # 문서-엔티티 연결
                await conn.execute("""
                    INSERT INTO document_entities (document_id, entity_id)
                    VALUES ($1, $2)
                    ON CONFLICT DO NOTHING
                """, document_id, entity_id)
    
    async def save_chunk_references(self, chunks: list):
        """청크 참조 정보 저장"""
        
        async with self.pool.acquire() as conn:
            await conn.executemany("""
                INSERT INTO chunk_references (chunk_id, document_id, chunk_index, token_count)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (chunk_id) DO UPDATE SET
                    es_indexed = FALSE
            """, [
                (c['chunk_id'], c['document_id'], c['chunk_index'], c.get('token_count', 0))
                for c in chunks
            ])
    
    async def mark_chunks_indexed(self, chunk_ids: list):
        """ES 인덱싱 완료 표시"""
        
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE chunk_references
                SET es_indexed = TRUE, es_indexed_at = CURRENT_TIMESTAMP
                WHERE chunk_id = ANY($1)
            """, chunk_ids)
    
    async def delete_document(self, document_id: str):
        """문서 삭제 (Soft Delete)"""
        
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE knowledge_master
                SET status = 'deleted', updated_at = CURRENT_TIMESTAMP
                WHERE document_id = $1
            """, document_id)
```

---

## Neo4j 저장 구조

### 역할: 지식 간 관계 및 컨텍스트 관리

Neo4j는 **엔티티 간의 관계**를 저장하여 연관 지식 추천, 전문가 찾기, 관계망 탐색을 지원합니다.

> ⚠️ **실제 구현**: Neo4j 그래프 저장은 구현됨(`src/app/storage/neo4j_storage.py`). ETL 3-Phase 중 Phase 3(엔티티 추출)에서 채워짐. APOC 플러그인 활용. 접속: `-u neo4j -p 'neo4j_dev_2026!'`. 2026-02-18 기준 Entity 노드 1,460개, HAS_ENTITY/RELATED_TO 관계 생성 완료.

### 그래프 스키마

```cypher
// ============================================
// 노드 정의
// ============================================

// 1. 지식 문서 노드
CREATE CONSTRAINT knowledge_id IF NOT EXISTS
FOR (k:Knowledge) REQUIRE k.id IS UNIQUE;

// 2. 사람 노드
CREATE CONSTRAINT person_name IF NOT EXISTS
FOR (p:Person) REQUIRE p.name IS UNIQUE;

// 3. 프로젝트 노드
CREATE CONSTRAINT project_name IF NOT EXISTS
FOR (pj:Project) REQUIRE pj.name IS UNIQUE;

// 4. 기술 노드
CREATE CONSTRAINT technology_name IF NOT EXISTS
FOR (t:Technology) REQUIRE t.name IS UNIQUE;

// 5. 토픽/카테고리 노드
CREATE CONSTRAINT topic_name IF NOT EXISTS
FOR (tp:Topic) REQUIRE tp.name IS UNIQUE;

// ============================================
// 관계 정의
// ============================================

// Knowledge 관계
// (Person)-[:CREATED]->(Knowledge)
// (Person)-[:REVIEWED]->(Knowledge)
// (Knowledge)-[:BELONGS_TO]->(Project)
// (Knowledge)-[:TAGGED_WITH]->(Topic)
// (Knowledge)-[:USES]->(Technology)
// (Knowledge)-[:REFERENCES]->(Knowledge)
// (Knowledge)-[:SUPERSEDES]->(Knowledge)  // 버전 관리

// 기타 관계
// (Person)-[:WORKS_ON]->(Project)
// (Person)-[:EXPERT_IN]->(Technology)
// (Project)-[:USES]->(Technology)
```

### 노드 속성 상세

```cypher
// Knowledge 노드 예시
CREATE (k:Knowledge {
    id: 'doc123',
    title: '2025년 1분기 Alpha 프로젝트 보고서',
    type: '프로젝트_보고서',
    summary: '프로젝트 진행 현황 및 기술 스택 정리',
    valid_from: date('2025-01-01'),
    valid_to: date('2025-12-31'),
    created_at: datetime()
})

// Person 노드 예시
CREATE (p:Person {
    name: '김철수',
    department: '개발팀',
    role: 'Tech Lead'
})

// Project 노드 예시
CREATE (pj:Project {
    name: 'Alpha',
    description: '지식 관리 시스템 구축',
    status: 'active',
    start_date: date('2025-01-01')
})

// Technology 노드 예시
CREATE (t:Technology {
    name: 'Neo4j',
    category: 'Database',
    description: '그래프 데이터베이스'
})
```

### Neo4j 저장 클래스

```python
from neo4j import AsyncGraphDatabase
from typing import Dict, List

class Neo4jStorage:
    """Neo4j 지식 그래프 관리"""
    
    def __init__(self, uri: str, user: str, password: str):
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    
    async def save_knowledge_graph(self, metadata: Dict):
        """문서 메타데이터를 그래프로 저장"""
        
        async with self.driver.session() as session:
            # 1. Knowledge 노드 생성
            await session.run("""
                MERGE (k:Knowledge {id: $doc_id})
                SET k.type = $doc_type,
                    k.summary = $summary,
                    k.valid_from = date($valid_from),
                    k.valid_to = date($valid_to),
                    k.updated_at = datetime()
            """, 
                doc_id=metadata['document_id'],
                doc_type=metadata['document_type'],
                summary=metadata.get('summary', ''),
                valid_from=metadata['valid_start_date'],
                valid_to=metadata.get('valid_end_date', '9999-12-31')
            )
            
            # 2. Project 연결
            if metadata.get('project_name'):
                await session.run("""
                    MERGE (pj:Project {name: $project_name})
                    WITH pj
                    MATCH (k:Knowledge {id: $doc_id})
                    MERGE (k)-[:BELONGS_TO]->(pj)
                """,
                    project_name=metadata['project_name'],
                    doc_id=metadata['document_id']
                )
            
            # 3. 엔티티 연결
            await self._create_entity_relationships(session, metadata)
            
            # 4. 명시적 관계 생성 (DeepSeek 추출)
            await self._create_explicit_relationships(session, metadata)
    
    async def _create_entity_relationships(self, session, metadata: Dict):
        """엔티티별 노드 생성 및 관계 연결"""
        
        entities = metadata.get('entities', {})
        doc_id = metadata['document_id']
        
        # Person 엔티티
        for person in entities.get('persons', []):
            await session.run("""
                MERGE (p:Person {name: $name})
                WITH p
                MATCH (k:Knowledge {id: $doc_id})
                MERGE (p)-[:MENTIONED_IN]->(k)
            """, name=person, doc_id=doc_id)
        
        # Technology 엔티티
        for tech in entities.get('technologies', []):
            await session.run("""
                MERGE (t:Technology {name: $name})
                WITH t
                MATCH (k:Knowledge {id: $doc_id})
                MERGE (k)-[:USES]->(t)
            """, name=tech, doc_id=doc_id)
        
        # Topic/Keyword 엔티티
        for keyword in entities.get('keywords', []):
            await session.run("""
                MERGE (tp:Topic {name: $name})
                WITH tp
                MATCH (k:Knowledge {id: $doc_id})
                MERGE (k)-[:TAGGED_WITH]->(tp)
            """, name=keyword, doc_id=doc_id)
    
    async def _create_explicit_relationships(self, session, metadata: Dict):
        """DeepSeek이 추출한 명시적 관계 생성"""
        
        relationships = metadata.get('relationships', [])
        
        for rel in relationships:
            from_entity = rel['from']
            to_entity = rel['to']
            relation = rel['relation'].upper()
            
            # 동적 관계 생성 (APOC 사용)
            await session.run("""
                MERGE (a {name: $from})
                MERGE (b {name: $to})
                WITH a, b
                CALL apoc.merge.relationship(a, $relation, {}, {}, b, {})
                YIELD rel
                RETURN rel
            """, 
                from_entity=from_entity,
                to_entity=to_entity,
                relation=relation
            )
    
    async def find_related_knowledge(
        self, 
        doc_id: str, 
        max_depth: int = 2,
        limit: int = 10
    ) -> List[Dict]:
        """연관 지식 탐색"""
        
        async with self.driver.session() as session:
            result = await session.run("""
                MATCH (k:Knowledge {id: $doc_id})
                MATCH path = (k)-[*1..$max_depth]-(related:Knowledge)
                WHERE related.id <> $doc_id
                WITH related, 
                     length(path) as distance,
                     [r in relationships(path) | type(r)] as rel_types
                RETURN DISTINCT related.id as id,
                       related.type as type,
                       related.summary as summary,
                       distance,
                       rel_types
                ORDER BY distance
                LIMIT $limit
            """, doc_id=doc_id, max_depth=max_depth, limit=limit)
            
            return [dict(record) async for record in result]
    
    async def find_experts(self, technology: str) -> List[Dict]:
        """특정 기술의 전문가 찾기"""
        
        async with self.driver.session() as session:
            result = await session.run("""
                MATCH (p:Person)-[:CREATED|REVIEWED]->(k:Knowledge)-[:USES]->(t:Technology {name: $tech})
                WITH p, count(k) as doc_count
                RETURN p.name as name,
                       p.department as department,
                       doc_count
                ORDER BY doc_count DESC
                LIMIT 10
            """, tech=technology)
            
            return [dict(record) async for record in result]
    
    async def delete_knowledge(self, doc_id: str):
        """지식 노드 및 관계 삭제"""
        
        async with self.driver.session() as session:
            await session.run("""
                MATCH (k:Knowledge {id: $doc_id})
                DETACH DELETE k
            """, doc_id=doc_id)
    
    async def close(self):
        await self.driver.close()
```

---

## 트랜잭션 안전성 및 동기화

### `asyncio.gather` 동작 방식

```python
await asyncio.gather(
    self._save_to_postgresql(metadata),   # 작업 A
    self._save_to_elasticsearch(chunks),  # 작업 B  
    self._save_to_neo4j(metadata)         # 작업 C
)
```

**특성:**

| 특성 | 설명 |
|------|------|
| ✅ 동시 실행 | 3개 DB에 동시에 요청 전송 |
| ✅ 성능 향상 | 순차 실행 대비 약 3배 빠름 |
| ❌ 원자성 없음 | 하나 실패해도 나머지는 성공할 수 있음 |
| ❌ 자동 롤백 없음 | ES 성공, Neo4j 실패 시 ES는 그대로 유지 |

```
시간 →
────────────────────────────────────────────────
PostgreSQL  │████░░░░████│                      (I/O 대기 중 다른 작업 실행)
ES          │░░████░░░░░░████│
Neo4j       │░░░░░░████░░░░░░████│
────────────────────────────────────────────────
            ↑ 동시에 시작      ↑ 모두 완료 후 반환
```

### 안전한 문서 인제스트 파이프라인

```python
import asyncio
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

class IngestionStatus(Enum):
    SUCCESS = "success"
    PARTIAL_FAILURE = "partial_failure"
    TOTAL_FAILURE = "total_failure"
    ROLLED_BACK = "rolled_back"

@dataclass
class IngestionResult:
    status: IngestionStatus
    document_id: str
    chunks_count: int
    failed_targets: List[str]
    error_message: Optional[str] = None

class DocumentIngestionPipeline:
    """트랜잭션 안전성을 보장하는 문서 인제스트 파이프라인"""
    
    def __init__(
        self,
        es_storage: 'ElasticsearchStorage',
        pg_storage: PostgreSQLStorage,
        neo4j_storage: Neo4jStorage,
        embedder: 'BGE_M3_Embedder',
        metadata_extractor: 'DeepSeekExtractor'
    ):
        self.es = es_storage
        self.pg = pg_storage
        self.neo4j = neo4j_storage
        self.embedder = embedder
        self.extractor = metadata_extractor
    
    async def ingest_document(self, doc_path: str) -> IngestionResult:
        """
        문서 인제스트 (트랜잭션 안전성 보장)
        
        실패 시 모든 DB에서 롤백 수행
        """
        document_id = None
        chunks = []
        
        try:
            # 1. 문서 파싱
            parsed = await self._parse_document(doc_path)
            
            # 2. 메타데이터 추출 (DeepSeek)
            metadata = await self.extractor.extract(parsed.text)
            document_id = metadata['document_id']
            
            # 3. 청킹 및 임베딩
            chunks = await self._create_chunks_with_embeddings(parsed, metadata)
            metadata['total_chunks'] = len(chunks)
            
            # 4. 3개 DB 동시 저장 (예외를 결과로 반환)
            results = await asyncio.gather(
                self.pg.save_document_master(metadata),
                self.es.index_chunks(chunks),
                self.neo4j.save_knowledge_graph(metadata),
                return_exceptions=True
            )
            
            # 5. 실패 확인
            failed_targets = []
            target_names = ['PostgreSQL', 'Elasticsearch', 'Neo4j']
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failed_targets.append(target_names[i])
            
            # 6. 부분 실패 시 롤백
            if failed_targets:
                await self._rollback_all(document_id)
                return IngestionResult(
                    status=IngestionStatus.ROLLED_BACK,
                    document_id=document_id,
                    chunks_count=0,
                    failed_targets=failed_targets,
                    error_message=f"Failed targets: {failed_targets}. Rolled back."
                )
            
            # 7. 청크 인덱싱 완료 표시
            await self.pg.mark_chunks_indexed([c['chunk_id'] for c in chunks])
            
            return IngestionResult(
                status=IngestionStatus.SUCCESS,
                document_id=document_id,
                chunks_count=len(chunks),
                failed_targets=[]
            )
            
        except Exception as e:
            # 전체 실패 시 롤백
            if document_id:
                await self._rollback_all(document_id)
            
            return IngestionResult(
                status=IngestionStatus.TOTAL_FAILURE,
                document_id=document_id or "unknown",
                chunks_count=0,
                failed_targets=['All'],
                error_message=str(e)
            )
    
    async def _rollback_all(self, document_id: str):
        """모든 DB에서 문서 삭제 (보상 트랜잭션)"""
        
        rollback_results = await asyncio.gather(
            self._safe_delete(self.pg.delete_document, document_id),
            self._safe_delete(self.es.delete_by_document_id, document_id),
            self._safe_delete(self.neo4j.delete_knowledge, document_id),
            return_exceptions=True
        )
        
        # 롤백 실패는 로깅만 (추가 조치 필요)
        for i, result in enumerate(rollback_results):
            if isinstance(result, Exception):
                print(f"Rollback failed for target {i}: {result}")
    
    async def _safe_delete(self, delete_func, document_id: str):
        """삭제 시도 (실패해도 예외 발생 안 함)"""
        try:
            await delete_func(document_id)
        except Exception as e:
            return e
        return None
    
    async def _create_chunks_with_embeddings(
        self, 
        parsed, 
        metadata: Dict
    ) -> List[Dict]:
        """청크 생성 및 임베딩"""
        
        # Docling HybridChunker 사용
        chunks = list(self.chunker.chunk(parsed.document))
        
        # 텍스트 추출
        texts = [self.chunker.contextualize(c) for c in chunks]
        
        # BGE-M3 임베딩 (Dense + Sparse)
        dense_vectors, sparse_vectors = self.embedder.encode(texts)
        
        # 청크 데이터 구성
        result = []
        for i, chunk in enumerate(chunks):
            result.append({
                'chunk_id': f"chunk_{metadata['document_id']}_{i:03d}",
                'chunk_index': i,
                'text': texts[i],
                'dense_vector': dense_vectors[i].tolist(),
                'sparse_vector': sparse_vectors[i],
                'document_id': metadata['document_id'],
                'metadata': metadata
            })
        
        return result
```

### Elasticsearch 저장 클래스

```python
from elasticsearch import Elasticsearch, helpers
from datetime import datetime

class ElasticsearchStorage:
    """Elasticsearch 벡터 + 메타데이터 저장"""
    
    def __init__(self, es: Elasticsearch, index_name: str = "knowledge_chunks"):
        self.es = es
        self.index_name = index_name
    
    async def index_chunks(self, chunks: List[Dict]):
        """청크 벌크 인덱싱"""
        
        actions = []
        for chunk in chunks:
            doc = {
                "_index": self.index_name,
                "_id": chunk['chunk_id'],
                "_source": {
                    "chunk_id": chunk['chunk_id'],
                    "chunk_index": chunk['chunk_index'],
                    "chunk_text": chunk['text'],
                    
                    # BGE-M3 벡터
                    "dense_vector": chunk['dense_vector'],
                    "sparse_vector": chunk['sparse_vector'],
                    
                    # 메타데이터
                    "document_id": chunk['document_id'],
                    "document_type": chunk['metadata']['document_type'],
                    "project_name": chunk['metadata'].get('project_name'),
                    "valid_start_date": chunk['metadata']['valid_start_date'],
                    "valid_end_date": chunk['metadata'].get('valid_end_date', '9999-12-31'),
                    "ingestion_timestamp": datetime.utcnow().isoformat(),
                    
                    # 엔티티
                    "entities": chunk['metadata'].get('entities', {})
                }
            }
            actions.append(doc)
        
        # 벌크 인덱싱
        success, failed = helpers.bulk(
            self.es, 
            actions, 
            refresh=True,
            raise_on_error=False
        )
        
        if failed:
            raise Exception(f"Failed to index {len(failed)} chunks")
        
        return success
    
    async def delete_by_document_id(self, document_id: str):
        """문서 ID로 모든 청크 삭제"""
        
        self.es.delete_by_query(
            index=self.index_name,
            query={"term": {"document_id": document_id}},
            refresh=True
        )
```

---

## 하이브리드 검색 구현 (RRF 대체)

### 핵심: 2회 쿼리 + Python 융합

RRF가 Platinum 전용이므로, **Python ranx 라이브러리**로 융합합니다.

> ⚠️ **실제 구현**: ranx 라이브러리 대신 Python 자체 구현 RRF 사용(`src/app/services/rrf_fusion.py`). 4중 융합(Dense + Sparse + BM25 + Graph)으로 확장. BGE-M3 대신 `jhgan/ko-sroberta-multitask` 768차원 벡터 사용.

```python
from elasticsearch import Elasticsearch
from ranx import Run, fuse
from typing import List, Dict, Optional
from datetime import datetime

class HybridSearchEngine:
    """무료 라이선스용 하이브리드 검색 엔진"""
    
    def __init__(
        self,
        es: Elasticsearch,
        embedder: 'BGE_M3_Embedder',
        index_name: str = "knowledge_chunks"
    ):
        self.es = es
        self.embedder = embedder
        self.index_name = index_name
    
    def search(
        self,
        query: str,
        k: int = 10,
        project_filter: Optional[str] = None,
        date_filter: Optional[datetime] = None,
        dense_weight: float = 0.5,
        sparse_weight: float = 0.5
    ) -> List[Dict]:
        """
        하이브리드 검색 수행
        
        검색 순서:
        1. 쿼리 임베딩 생성 (Dense + Sparse)
        2. Dense 검색 (kNN)
        3. Sparse 검색 (sparse_vector query)
        4. Python RRF 융합
        5. 결과 반환
        """
        # 1. 쿼리 임베딩 생성
        dense_query, sparse_query = self.embedder.encode_query(query)
        
        # 2. 필터 조건 구성
        filter_clauses = self._build_filters(project_filter, date_filter)
        
        # 3. Dense 검색 (kNN)
        dense_results = self._dense_search(dense_query, k * 2, filter_clauses)
        
        # 4. Sparse 검색
        sparse_results = self._sparse_search(sparse_query, k * 2, filter_clauses)
        
        # 5. RRF 융합 (ranx 사용)
        fused_results = self._fuse_results(
            dense_results, 
            sparse_results,
            dense_weight,
            sparse_weight,
            k
        )
        
        return fused_results
    
    def _build_filters(
        self, 
        project_filter: Optional[str],
        date_filter: Optional[datetime]
    ) -> List[Dict]:
        """메타데이터 필터 조건 구성"""
        filters = []
        
        if project_filter:
            filters.append({"term": {"project_name": project_filter}})
        
        if date_filter:
            date_str = date_filter.strftime("%Y-%m-%d")
            filters.append({
                "bool": {
                    "must": [
                        {"range": {"valid_start_date": {"lte": date_str}}},
                        {"range": {"valid_end_date": {"gte": date_str}}}
                    ]
                }
            })
        
        return filters
    
    def _dense_search(
        self, 
        query_vector: List[float], 
        k: int,
        filters: List[Dict]
    ) -> Dict[str, float]:
        """kNN Dense 검색"""
        
        knn_query = {
            "field": "dense_vector",
            "query_vector": query_vector,
            "k": k,
            "num_candidates": k * 2
        }
        
        if filters:
            knn_query["filter"] = {"bool": {"must": filters}}
        
        response = self.es.search(
            index=self.index_name,
            knn=knn_query,
            size=k,
            _source=["chunk_id", "chunk_text", "document_type", "project_name"]
        )
        
        # {doc_id: score} 형태로 변환
        return {hit['_id']: hit['_score'] for hit in response['hits']['hits']}
    
    def _sparse_search(
        self, 
        query_vector: Dict[str, float],
        k: int,
        filters: List[Dict]
    ) -> Dict[str, float]:
        """Sparse Vector 검색 (Basic 라이선스 호환)"""
        
        # sparse_vector 쿼리 (query_vector 직접 제공)
        query = {
            "sparse_vector": {
                "field": "sparse_vector",
                "query_vector": query_vector
            }
        }
        
        # 필터 적용
        if filters:
            query = {
                "bool": {
                    "must": [query],
                    "filter": filters
                }
            }
        
        response = self.es.search(
            index=self.index_name,
            query=query,
            size=k,
            _source=["chunk_id", "chunk_text", "document_type", "project_name"]
        )
        
        return {hit['_id']: hit['_score'] for hit in response['hits']['hits']}
    
    def _fuse_results(
        self,
        dense_results: Dict[str, float],
        sparse_results: Dict[str, float],
        dense_weight: float,
        sparse_weight: float,
        k: int
    ) -> List[Dict]:
        """ranx를 사용한 Weighted RRF 융합"""
        
        # ranx Run 객체 생성
        dense_run = Run({"q1": dense_results})
        sparse_run = Run({"q1": sparse_results})
        
        # Weighted RRF 융합
        fused_run = fuse(
            runs=[dense_run, sparse_run],
            method="rrf",
            params={"k": 60},
            weights=[dense_weight, sparse_weight]
        )
        
        # 상위 k개 결과 추출
        fused_scores = fused_run.get_doc_ids_and_scores()["q1"]
        top_k = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)[:k]
        
        # 전체 문서 정보 조회
        doc_ids = [doc_id for doc_id, _ in top_k]
        docs = self.es.mget(index=self.index_name, ids=doc_ids)
        
        results = []
        for (doc_id, score), doc in zip(top_k, docs['docs']):
            if doc['found']:
                results.append({
                    "chunk_id": doc_id,
                    "score": score,
                    "chunk_text": doc['_source']['chunk_text'],
                    "document_type": doc['_source'].get('document_type'),
                    "project_name": doc['_source'].get('project_name'),
                    "dense_score": dense_results.get(doc_id, 0),
                    "sparse_score": sparse_results.get(doc_id, 0)
                })
        
        return results
```

---

## 라이선스 호환성 체크리스트

### ✅ Basic(무료)에서 사용 가능

| 기능 | 사용 방법 |
|------|----------|
| `dense_vector` 필드 | kNN 검색 |
| `sparse_vector` 필드 | `query_vector` 직접 제공 |
| BM25 텍스트 검색 | `match` 쿼리 |
| 메타데이터 필터링 | `bool` 쿼리 |
| 집계 | `aggs` |
| Nori 한국어 분석기 | 플러그인 설치 |

### ❌ Platinum 이상 필요 (사용 불가)

| 기능 | 대안 |
|------|------|
| RRF (Reciprocal Rank Fusion) | Python `ranx` 라이브러리 |
| ELSER 모델 | BGE-M3 외부 임베딩 |
| `inference_id` 기반 쿼리 | `query_vector` 직접 제공 |
| ML 노드 모델 배포 | 외부 Python 서버 |

---

## 데이터 흐름 요약

### 인제스트 플로우

```
PDF/DOCX 문서
    ↓
[Docling] 파싱 + HybridChunker 청킹
    ↓
[DeepSeek-V3.2] 메타데이터/엔티티 추출
    ↓
[BGE-M3] Dense + Sparse 임베딩 생성
    ↓
┌─────────────────────────────────────┐
│     asyncio.gather (동시 저장)       │
├───────────┬───────────┬─────────────┤
│PostgreSQL │   Neo4j   │Elasticsearch│
│  (SSOT)   │  (관계)   │ (검색 최적화)│
│           │           │             │
│ 문서 마스터│ 엔티티 노드│ chunk_text  │
│ 청크 참조 │ 관계 엣지  │ dense_vector│
│ 엔티티 정규화│         │sparse_vector│
│ 시계열 정보│          │ 메타데이터   │
└───────────┴───────────┴─────────────┘
```

### 검색 플로우

```
사용자 쿼리
    ↓
[BGE-M3] 쿼리 임베딩 (Dense + Sparse)
    ↓
┌─────────────────────────────────────┐
│      Elasticsearch (2회 쿼리)        │
├─────────────────┬───────────────────┤
│  Dense Search   │  Sparse Search    │
│  (kNN cosine)   │ (token weights)   │
│  + 메타필터     │  + 메타필터       │
└────────┬────────┴─────────┬─────────┘
         ↓                  ↓
    ┌────────────────────────────┐
    │   Python ranx RRF 융합     │
    │   (가중치 조절 가능)        │
    └────────────┬───────────────┘
                 ↓
         최종 검색 결과
```

---

## 설치 및 실행

### 필수 패키지

```bash
# Python 패키지
pip install elasticsearch==8.12.0
pip install FlagEmbedding
pip install ranx
pip install neo4j
pip install asyncpg
pip install docling

# Elasticsearch Nori 플러그인 (Docker 내부)
docker exec -it elasticsearch \
  bin/elasticsearch-plugin install analysis-nori
```

> ⚠️ **실제 구현**: `FlagEmbedding` (BGE-M3) 미사용. `sentence-transformers`로 `jhgan/ko-sroberta-multitask` 사용. `ranx` 미사용 (자체 RRF 구현). **Nori 플러그인은 runtime 설치가 아닌 커스텀 Dockerfile에서 빌드 시 설치 필수** (runtime 설치 방식은 컨테이너 재시작 시 초기화됨).

### Docker Compose

> ⚠️ **실제 구현**: ES 이미지는 공식 이미지 직접 사용이 아닌 **커스텀 빌드** 필수 (Nori 플러그인 포함). `docker-compose.yml`에서 `build: ./infrastructure/elasticsearch` 방식. 최종 컨테이너 수: 18개.

```yaml
version: '3.8'
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.15.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - ES_JAVA_OPTS=-Xms4g -Xmx4g
      - xpack.license.self_generated.type=basic
    ports:
      - "9200:9200"
    volumes:
      - es_data:/usr/share/elasticsearch/data

  neo4j:
    image: neo4j:5.15.0
    environment:
      - NEO4J_AUTH=neo4j/password
      - NEO4J_PLUGINS=["apoc"]
      - NEO4J_dbms_memory_heap_max__size=2G
    ports:
      - "7474:7474"
      - "7687:7687"
    volumes:
      - neo4j_data:/data

  postgres:
    image: postgres:16
    environment:
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=knowledge
    ports:
      - "5432:5432"
    command: postgres -c shared_buffers=256MB -c effective_cache_size=512MB
    volumes:
      - pg_data:/var/lib/postgresql/data

volumes:
  es_data:
  neo4j_data:
  pg_data:
```

---

## 결론

### 아키텍처 핵심

| 구성 요소 | 역할 | 저장 데이터 |
|----------|------|-----------|
| **PostgreSQL** | 단일 진실 공급원 (SSOT) | 문서 마스터, 시계열, 엔티티 (정규화) |
| **Neo4j** | 관계 탐색 | 노드 (Knowledge, Person, Tech), 엣지 (관계) |
| **Elasticsearch** | Zero-Join 검색 | Dense + Sparse + BM25 + 메타데이터 (비정규화) |

### 트랜잭션 안전성

- `asyncio.gather`로 동시 저장 (성능 3배 향상)
- `return_exceptions=True`로 부분 실패 감지
- 실패 시 보상 트랜잭션으로 롤백

### 무료 라이선스 대응

- RRF → Python `ranx` 라이브러리
- ELSER → BGE-M3 외부 임베딩
- `inference_id` → `query_vector` 직접 제공

---

**문서 작성일**: 2026-01-12
**버전**: 2.0
**참조**: Elastic 공식 문서, BGE-M3 문서, Neo4j Cypher Manual, PostgreSQL 문서

---

## 현행화 이력

| 일자 | 작성자 | 내용 |
|------|--------|------|
| 2026-02-20 | Claude (doc-agent) | 프로젝트 종료 후 현행화 — 실제 구현 반영 (ko-sroberta-multitask 768차원, Python 자체 RRF, 4중 융합 검색, Nori Dockerfile 설치, 3-Phase ETL, Neo4j 엔티티 완료, ES 인덱스명 확인) |