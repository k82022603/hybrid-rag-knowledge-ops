# STORY-030: HybridRetriever 구현

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-25 |
| **Epic** | EPIC-002 |
| **Status** | Done |
| **Priority** | Critical |
| **Story Points** | 8 |
| **Assignee** | MLRag |
| **Sprint** | 3 |

---

## User Story

**As a** 지식 검색 사용자,
**I want** 벡터 검색과 그래프 검색을 결합한 하이브리드 검색,
**So that** 의미적 유사성과 관계 기반 추론을 모두 활용한 정확한 검색 결과를 얻음.

---

## Acceptance Criteria

- [ ] **Given** 검색 쿼리 입력, **When** HybridRetriever 호출, **Then** ES 벡터 검색 + Neo4j 그래프 검색 병렬 실행
- [ ] **Given** 검색 결과, **When** 두 결과 병합, **Then** 중복 제거 및 통합 결과 반환
- [ ] **Given** top_k=5 설정, **When** 검색 완료, **Then** 상위 5개 문서 반환
- [ ] **Given** 검색 실행, **When** 응답 시간 측정, **Then** 1초 이내 응답
- [ ] **Given** ES 또는 Neo4j 장애, **When** 검색 실행, **Then** 정상 동작하는 검색 엔진 결과만 반환

---

## Tasks

- [ ] ElasticsearchRetriever 클래스 구현
- [ ] Neo4jRetriever 클래스 구현
- [ ] HybridRetriever 통합 클래스 구현
- [ ] 병렬 검색 로직 (asyncio.gather)
- [ ] 결과 병합 및 중복 제거
- [ ] 에러 핸들링 및 fallback
- [ ] 단위 테스트 작성
- [ ] 성능 벤치마크

---

## 기술 노트

### ElasticsearchRetriever

```python
# ai_service/src/retrievers/elasticsearch_retriever.py
from typing import List
from elasticsearch import AsyncElasticsearch

class ElasticsearchRetriever:
    def __init__(self, client: AsyncElasticsearch, index_name: str):
        self.client = client
        self.index_name = index_name

    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 20,
        filters: dict = None
    ) -> List[Document]:
        """벡터 유사도 검색 (HNSW)"""
        knn_query = {
            "field": "embedding",
            "query_vector": query_embedding,
            "k": top_k,
            "num_candidates": top_k * 2
        }

        if filters:
            knn_query["filter"] = filters

        response = await self.client.search(
            index=self.index_name,
            knn=knn_query,
            source=["content", "metadata", "chunk_id"]
        )

        return [
            Document(
                id=hit["_id"],
                content=hit["_source"]["content"],
                metadata=hit["_source"]["metadata"],
                score=hit["_score"]
            )
            for hit in response["hits"]["hits"]
        ]
```

### Neo4jRetriever

```python
# ai_service/src/retrievers/neo4j_retriever.py
from neo4j import AsyncGraphDatabase

class Neo4jRetriever:
    def __init__(self, driver: AsyncGraphDatabase.driver):
        self.driver = driver

    async def search(
        self,
        query: str,
        query_embedding: List[float],
        top_k: int = 20
    ) -> List[Document]:
        """그래프 기반 검색 (관계 탐색 + 벡터 유사도)"""
        cypher = """
        CALL db.index.vector.queryNodes('chunk_embedding', $top_k, $embedding)
        YIELD node AS chunk, score
        MATCH (chunk)-[:PART_OF]->(doc:Document)
        OPTIONAL MATCH (chunk)-[:MENTIONS]->(entity:Entity)
        WITH chunk, doc, score, collect(entity.name) AS entities
        RETURN
            chunk.chunk_id AS chunk_id,
            chunk.content AS content,
            doc.title AS doc_title,
            doc.doc_type AS doc_type,
            entities,
            score
        ORDER BY score DESC
        LIMIT $top_k
        """

        async with self.driver.session() as session:
            result = await session.run(
                cypher,
                embedding=query_embedding,
                top_k=top_k
            )
            records = await result.data()

        return [
            Document(
                id=r["chunk_id"],
                content=r["content"],
                metadata={
                    "doc_title": r["doc_title"],
                    "doc_type": r["doc_type"],
                    "entities": r["entities"]
                },
                score=r["score"]
            )
            for r in records
        ]
```

### HybridRetriever

```python
# ai_service/src/retrievers/hybrid_retriever.py
import asyncio
from typing import List, Optional

class HybridRetriever:
    def __init__(
        self,
        es_retriever: ElasticsearchRetriever,
        neo4j_retriever: Neo4jRetriever,
        embedder: BGEEmbedder
    ):
        self.es_retriever = es_retriever
        self.neo4j_retriever = neo4j_retriever
        self.embedder = embedder

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        es_weight: float = 0.5,
        neo4j_weight: float = 0.5
    ) -> List[Document]:
        """하이브리드 검색: ES + Neo4j 병렬 실행 후 결과 병합"""

        # 1. 쿼리 임베딩 생성
        query_embedding = await self.embedder.embed(query)

        # 2. 병렬 검색
        try:
            es_results, neo4j_results = await asyncio.gather(
                self.es_retriever.search(query_embedding, top_k=20),
                self.neo4j_retriever.search(query, query_embedding, top_k=20),
                return_exceptions=True
            )
        except Exception as e:
            logger.error(f"검색 에러: {e}")
            raise

        # 3. 예외 처리 (한쪽 실패 시 다른 쪽만 사용)
        if isinstance(es_results, Exception):
            logger.warning(f"ES 검색 실패: {es_results}")
            es_results = []
        if isinstance(neo4j_results, Exception):
            logger.warning(f"Neo4j 검색 실패: {neo4j_results}")
            neo4j_results = []

        # 4. 결과 병합 (RRF Fusion은 STORY-031에서 구현)
        merged = self._merge_results(es_results, neo4j_results)

        return merged[:top_k]

    def _merge_results(
        self,
        es_results: List[Document],
        neo4j_results: List[Document]
    ) -> List[Document]:
        """결과 병합 및 중복 제거"""
        seen_ids = set()
        merged = []

        for doc in es_results + neo4j_results:
            if doc.id not in seen_ids:
                seen_ids.add(doc.id)
                merged.append(doc)

        # 점수순 정렬
        return sorted(merged, key=lambda x: x.score, reverse=True)
```

### 영향 범위
- `ai_service/src/retrievers/elasticsearch_retriever.py`
- `ai_service/src/retrievers/neo4j_retriever.py`
- `ai_service/src/retrievers/hybrid_retriever.py`
- `ai_service/src/models/document.py`

---

## 테스트 계획

- [ ] Unit Test: ElasticsearchRetriever.search()
- [ ] Unit Test: Neo4jRetriever.search()
- [ ] Unit Test: HybridRetriever.retrieve()
- [ ] Integration Test: 실제 ES/Neo4j 연동
- [ ] Performance Test: 응답시간 < 1초

---

## 참고 자료

- [상세 설계서 v2.4](../../knowledge_service/docs/02_design/hybrid_rag_platform_detailed_design.md)
- [Elasticsearch Python Client](https://elasticsearch-py.readthedocs.io/en/latest/async.html)
- [Neo4j Python Driver](https://neo4j.com/docs/python-manual/current/)
