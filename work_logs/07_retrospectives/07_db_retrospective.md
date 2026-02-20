# 프로젝트 회고: Database Designer

**역할**: DB 스키마 설계 / 쿼리 최적화
**참여 기간**: Sprint 1 ~ Sprint 12
**모델**: Sonnet 4.6

---

## 1. Triple-Store라는 도전

프로젝트 시작 시점에서 나에게 주어진 과제는 명확했다: PostgreSQL, Elasticsearch, Neo4j -- 세 개의 데이터베이스를 동시에 운영하면서 데이터 일관성을 유지하라.

보통 프로젝트에서 데이터베이스는 하나다. 많아야 두 개. 그런데 이 프로젝트는 처음부터 세 개를 설계했다. 왜냐하면 각각이 대체 불가능한 역할을 가지고 있기 때문이다.

**PostgreSQL 16** -- SSOT(Single Source of Truth). 문서의 메타데이터, 사용자 정보, 시스템 설정 등 트랜잭션이 필요한 정형 데이터를 담당한다. "이 문서의 현재 상태가 무엇인가?"라는 질문에 대한 정답은 항상 PostgreSQL에 있다.

**Elasticsearch 8.x** -- 벡터 검색과 전문 검색의 엔진. 42,462개 청크의 Dense 1024d 벡터, Sparse 벡터, 원문 텍스트를 저장하고, kNN cosine similarity로 벡터 검색을, Nori 분석기가 적용된 BM25로 키워드 검색을 수행한다. 검색 성능이 RAG 시스템의 품질을 직접 결정하기 때문에, 이 인덱스의 설계가 프로젝트의 핵심이었다.

**Neo4j 5.x** -- Knowledge Graph. 169,886개 노드와 775,366개 관계가 문서 간의 숨겨진 연결을 표현한다. "Claude Code와 관련된 기술은 무엇인가?"라는 관계 기반 질의는 Neo4j만이 효율적으로 답할 수 있다.

세 데이터베이스를 운영하면서 가장 큰 고민은 데이터 일관성이었다. 문서가 업로드되면 PostgreSQL에 레코드가 생성되고, Elasticsearch에 청크가 적재되고, Neo4j에 Document/Chunk 노드가 생성되어야 한다. 이 세 작업 중 하나라도 실패하면 정합성이 깨진다. 분산 트랜잭션(2PC)을 도입할 수도 있었지만, Docker Compose 환경에서의 복잡성과 성능 오버헤드를 고려해서 "최종적 일관성(Eventual Consistency)" 모델을 채택했다. PostgreSQL을 SSOT로 삼고, Elasticsearch와 Neo4j는 비동기로 동기화하되, 정합성 체크 스크립트를 주기적으로 실행해서 불일치를 탐지하는 방식이다.

Sprint 12 최종 시점에서 3-Store 정합성은 100%를 달성했다. ES = PG = Neo4j, 모든 저장소의 문서/청크 수가 일치한다. 이것이 단순해 보이지만, 41일간의 개발 과정에서 여러 번 정합성이 깨지고 다시 맞추는 과정을 반복한 결과다.

---

## 2. PostgreSQL -- SSOT(Single Source of Truth)의 무게

PostgreSQL의 핵심 테이블은 `documents`다. 각 문서의 메타데이터, 상태, 청크 수, 생성일/수정일 등을 관리한다. 이 테이블이 SSOT라는 것은, 다른 저장소에 불일치가 발생했을 때 항상 PostgreSQL의 데이터를 기준으로 복구한다는 의미다.

문서 상태 머신은 다음과 같이 설계했다: `draft -> processing -> completed -> failed`. 문서가 업로드되면 `draft` 상태로 생성되고, 파싱/청킹이 시작되면 `processing`으로 전환되며, 모든 처리가 완료되면 `completed`, 어디선가 실패하면 `failed`로 전환된다. 이 상태 머신이 ETL 파이프라인의 진행 상태를 추적하는 기반이 되었다. ETL Engineer가 "현재 처리 중인 문서가 몇 개인가?"를 알고 싶을 때, PostgreSQL의 documents 테이블에서 `status = 'processing'`인 레코드 수를 쿼리하면 된다.

`system_config` 테이블도 설계했다. 시스템 전역 설정(임베딩 모델명, chunk_size, overlap 등)을 key-value 형태로 저장한다. 이를 통해 ETL 파이프라인의 설정 변경 이력을 추적할 수 있다. "v1에서 chunk_size 600이었던 것을 v2에서 1000으로 변경했다"는 기록이 이 테이블에 남는다.

트랜잭션 관리에서 가장 신경 쓴 부분은 문서 삭제다. 문서를 삭제하면 PostgreSQL에서 레코드를 삭제하고, Elasticsearch에서 해당 문서의 모든 청크를 삭제하고, Neo4j에서 Document 노드와 연결된 Chunk 노드, Entity 관계를 삭제해야 한다. 어느 하나라도 실패하면 고아 데이터가 남는다. PostgreSQL의 소프트 삭제(deleted_at 타임스탬프)를 먼저 적용하고, 비동기로 ES/Neo4j를 정리한 후, 마지막으로 PostgreSQL에서 물리적 삭제를 수행하는 2단계 삭제를 구현했다.

Sprint 12에서 PostgreSQL의 역할이 다시 한번 강조되었다. 쓰레기 청크 13,601건을 삭제할 때, PostgreSQL의 documents 테이블에서 chunk_count를 보정하는 Phase 2 동기화가 필수적이었다. "이 문서에 원래 65개 청크가 있었는데, 쓰레기 청크 12개를 삭제했으니 53개로 업데이트해야 한다"는 계산을 PostgreSQL 기준으로 수행했다.

---

## 3. Elasticsearch -- 벡터와 키워드의 공존

`knowledge_chunks` 인덱스의 매핑 설계는 이 프로젝트에서 가장 많이 수정된 설계 중 하나다. 처음에는 Dense Vector(1024d)와 텍스트 필드만 있었다. 그러다 Sparse Vector가 추가되고, BM25를 위한 Nori 분석기가 추가되고, 메타데이터 필드들이 추가되면서 매핑이 점점 복잡해졌다.

최종 매핑의 핵심 필드를 설명하겠다:

- `dense_vector`: BGE-M3가 생성한 1024차원 벡터. `dims: 1024`, `similarity: cosine`으로 설정. kNN 검색의 기반이다.
- `sparse_vector`: BGE-M3의 Sparse 벡터. 특정 토큰의 중요도를 가중치로 표현한다. Dense가 의미를 포착한다면, Sparse는 키워드를 포착한다.
- `text`: 청크 원문. `korean_analyzer`가 적용된 필드로, Nori 형태소 분석기를 통해 BM25 키워드 검색을 지원한다.
- `heading`: 섹션 제목. 검색 결과의 맥락 파악에 활용.
- `token_count`: 청크의 토큰 수. 쓰레기 청크 필터링(tc < 50)의 기준이 된다.
- `document_id`: PostgreSQL documents 테이블과의 외래 키 역할.

**Nori 한국어 분석기와 커스텀 Dockerfile**. 이것이 32일간의 사고와 직결된 설계다. ES 매핑에 `korean_analyzer`를 정의하고, 그 안에 `nori_tokenizer`를 참조했다. 하지만 Nori는 ES 기본 설치에 포함되지 않는 플러그인이다. `analysis-nori` 플러그인을 설치하려면 커스텀 Dockerfile이 필요하다.

```dockerfile
FROM elasticsearch:8.11.0
RUN bin/elasticsearch-plugin install analysis-nori
```

이 두 줄의 Dockerfile이 32일간 누락되었다. docker-compose.yml이 ES 공식 이미지를 직접 참조하고 있었기 때문에, 매핑에 `nori_tokenizer`를 정의해도 실제로는 standard tokenizer로 폴백되었다. ES는 매핑에 정의된 분석기가 사용 불가할 때 에러를 발생시키지 않고 기본 분석기로 대체한다는 사실을 이 사고를 통해 처음 알았다. 이것은 데이터베이스 설계자로서의 큰 교훈이다: **스키마 정의와 런타임 동작이 일치하는지 반드시 검증해야 한다**.

인덱스 통일도 중요한 작업이었다. 한때 `knowledge_chunks`와 `knowledge_chunks_v2`라는 두 개의 인덱스가 병존했다. alias로 관리하려 했지만, 결국 단순하게 `knowledge_chunks` 하나로 통일했다. 인덱스가 두 개면 검색 쿼리도 두 가지를 관리해야 하고, ETL 적재 대상도 분기해야 하고, 정합성 체크도 복잡해진다. 단순함이 최선이었다.

---

## 4. Neo4j 스키마 통일 -- 가장 큰 교훈

이것은 Sprint 12, 프로젝트 마지막 날인 2026년 2월 18일에 발견되고 수정된 이슈다.

사용자 테스트 중, 온라인으로 업로드한 문서의 엔티티가 그래프 검색 결과에 나타나지 않는 현상이 발견되었다. 원인을 추적하니, 온라인 파이프라인(문서 업로드 시 실시간 처리)과 배치 파이프라인(ETL Phase 3)이 Neo4j에 서로 다른 관계 이름과 속성명을 사용하고 있었다.

| 항목 | 온라인 파이프라인 | 배치 파이프라인 | 검색 코드(search.py) |
|------|:---:|:---:|:---:|
| Chunk-Entity 관계 | HAS_ENTITY | MENTIONS | MENTIONS |
| Entity-Entity 관계 | RELATED_TO | RELATED | RELATED_TO |
| Chunk ID 속성 | chunk_id | id | id |

search.py가 `MENTIONS`와 `RELATED_TO`를 기준으로 쿼리하고 있었기 때문에, 온라인에서 `HAS_ENTITY`와 `RELATED_TO`로 생성된 관계는 검색에서 완전히 누락되었다. 배치로 처리한 42K 청크는 정상이었지만, 새로 업로드한 문서의 엔티티는 보이지 않았던 것이다.

이 문제의 근본 원인은 내 설계의 일관성 부족이었다. 온라인 파이프라인과 배치 파이프라인에서 Neo4j 스키마를 각각 독립적으로 정의했고, 네이밍 규칙을 통일하는 중앙 스키마 정의서가 없었다. 코드를 작성하는 개발자가 다르니(온라인은 RAG Engineer, 배치는 ETL Engineer) 당연히 네이밍이 달라질 수밖에 없었다.

TechLead의 TD-001 의사결정을 받아 스키마를 통일했다. 기준은 배치 파이프라인에서 이미 775K 관계가 적재되어 있는 쪽으로 맞추되, 관계 이름은 의미적으로 더 명확한 쪽을 선택했다:
- Chunk-Entity: `MENTIONS` (배치 기준 유지)
- Entity-Entity: `RELATED_TO` (온라인 기준 채택, 의미가 더 명확)
- Chunk ID: `id` (배치 기준 유지)

코드 5개 파일을 수정했다. `neo4j_storage.py`, `document_processing_pipeline.py`, `search.py` 등에서 `HAS_ENTITY`를 `MENTIONS`로, `RELATED`를 `RELATED_TO`로, `chunk_id`를 `id`로 통일했다. 그리고 DB 마이그레이션을 실행했다:

```cypher
// RELATED -> RELATED_TO 변환 (298,636건)
MATCH (a)-[r:RELATED]->(b)
CREATE (a)-[:RELATED_TO {type: r.type, description: r.description, weight: r.weight}]->(b)
DELETE r

// HAS_ENTITY -> MENTIONS 변환 (13건)
MATCH (c:Chunk)-[r:HAS_ENTITY]->(e)
CREATE (c)-[:MENTIONS]->(e)
DELETE r
```

25.7초. 서비스 중단 없이 완료. 이후 4개 파일을 업로드하고 14건의 검색을 수행해서 전체 PASS를 확인했다. 기존 42,458건의 검색에도 영향 없음을 검증했다.

이 경험에서 얻은 교훈: **다중 데이터 소스 환경에서는 스키마 네이밍 규칙을 중앙에서 관리해야 한다**. 코드에 흩어져 있는 관계 이름이 아니라, 단일 스키마 정의 파일에서 모든 노드 라벨, 관계 타입, 속성명을 정의하고, 모든 코드가 이 정의를 참조해야 한다. 이것을 프로젝트 초기에 했더라면 TD-001 같은 긴급 마이그레이션은 필요 없었을 것이다.

---

## 5. Redis 캐시 아키텍처

Redis는 이 프로젝트에서 "조용한 기여자"다. 눈에 띄지 않지만, 검색 응답 시간을 극적으로 단축한다.

캐시 아키텍처는 두 가지 TTL 계층으로 설계했다:

**검색 결과 캐시 (TTL: 3600초, 1시간)**. 동일한 검색 쿼리에 대한 결과를 캐싱한다. 사용자가 "Docker Compose 메모리 설정"을 검색하면, 4-Way RRF 검색, Reranking, Entity Enrichment, LLM 답변 생성이 모두 수행된다. 이 전체 파이프라인은 수 초가 걸린다. 하지만 동일한 쿼리가 1시간 내에 다시 들어오면 Redis에서 즉시 반환한다. TTL 3600초는 "문서가 자주 업데이트되지 않는 기업 내부 시스템"이라는 특성을 반영한 것이다. 문서가 변경되면 해당 캐시를 무효화해야 하는데, 현재는 `FLUSHALL` 또는 키 패턴 기반 삭제로 처리한다.

**임베딩 캐시 (TTL: 604800초, 7일)**. 쿼리 텍스트의 BGE-M3 임베딩을 캐싱한다. 동일한 쿼리 텍스트는 항상 동일한 벡터를 생성하므로, 임베딩 모델을 변경하지 않는 한 캐시가 유효하다. 7일이라는 긴 TTL은 임베딩 모델 변경이 드물다는 가정 하에 설정했다.

캐시 키 생성은 SHA256 해시 기반이다. 쿼리 텍스트, 검색 파라미터(top_k, 필터 등)를 결합해서 SHA256 해시를 생성하고, 이를 Redis 키로 사용한다. 이 방식의 장점은 키 충돌 가능성이 사실상 0이고, 키 길이가 일정(64자)하다는 것이다. 단점은 쿼리 텍스트가 한 글자만 달라도 완전히 다른 키가 생성되어 캐시 적중률이 떨어질 수 있다는 점인데, 이것은 의도된 동작이다. 한 글자 차이로 검색 결과가 달라질 수 있기 때문이다.

**InMemory LRU 폴백**. Redis 연결이 실패할 때를 대비해서 InMemory LRU 캐시를 폴백으로 구현했다. Redis가 다운되면 자동으로 InMemory LRU로 전환되어 서비스 가용성을 유지한다. LRU(Least Recently Used) 정책으로 가장 오래 사용되지 않은 항목부터 제거하며, 최대 크기를 설정해서 메모리 사용량을 제한한다.

```python
class CacheService:
    def __init__(self, redis_url, ttl, max_size):
        try:
            self._backend = RedisCacheBackend(redis_url, ttl)
            self._stats.backend = "redis"
        except Exception:
            self._backend = InMemoryLRUCache(max_size=max_size, default_ttl=ttl)
            self._stats.backend = "in_memory_lru"
```

이 폴백 구조는 standalone 테스트에서 검증되었고, Redis 컨테이너가 재시작되는 동안에도 서비스가 정상 동작함을 확인했다.

캐시 관리에서 남은 과제는 관리자 UI에서의 캐시 리셋 기능이다. 현재는 `docker exec kp-redis redis-cli FLUSHALL`을 수동으로 실행해야 한다. STORY-098로 백로그에 등록되어 있지만, Sprint 12에서는 Deferred 처리되었다.

---

## 6. 아쉬운 점과 팀원들에게

가장 큰 아쉬움은 쿼리 최적화를 충분히 수행하지 못한 것이다. Elasticsearch의 kNN 검색과 Neo4j의 Cypher 쿼리 모두 EXPLAIN 분석을 통한 체계적 최적화가 가능한데, 프로젝트 일정에 쫓기면서 "동작하면 OK" 수준에서 멈춘 경우가 많았다. 특히 Neo4j에서 MENTIONS 관계를 통한 Graph Search 쿼리의 실행 계획을 분석하고, 인덱스 전략을 최적화했다면 검색 응답 시간을 더 줄일 수 있었을 것이다.

PostgreSQL과 Elasticsearch 간의 실시간 동기화도 개선 여지가 있다. 현재는 ETL Phase 2에서 배치로 동기화하지만, 온라인 업로드 시에는 동기적으로 처리한다. CDC(Change Data Capture) 패턴을 도입해서 PostgreSQL의 변경 사항을 이벤트로 발행하고, Elasticsearch와 Neo4j가 이를 구독하는 방식으로 개선하면 더 안정적인 일관성을 달성할 수 있었을 것이다. 물론 Docker Compose 환경에서 Kafka나 Debezium을 추가하는 것은 인프라 복잡성 측면에서 과도했겠지만, 아키텍처적으로는 더 깔끔한 해결책이었다.

Neo4j 스키마 버전 관리도 도입하고 싶었다. PostgreSQL에는 Alembic이나 Flyway 같은 마이그레이션 도구가 있지만, Neo4j에는 표준적인 스키마 마이그레이션 도구가 없다. TD-001 마이그레이션을 Cypher 스크립트로 직접 수행했는데, 이런 마이그레이션이 누적되면 "현재 스키마가 어떤 버전인가?"를 추적하기 어려워진다.

RAG Engineer에게 -- 당신이 설계한 4-Way Hybrid Search가 나의 세 데이터베이스를 모두 활용한다는 사실이 기쁘다. Dense 검색은 Elasticsearch의 kNN을 사용하고, BM25는 Nori가 적용된 Elasticsearch의 텍스트 필드를 사용하고, Sparse 검색은 Elasticsearch의 sparse_vector를 사용하고, Graph 검색은 Neo4j의 MENTIONS 관계를 사용한다. 세 데이터베이스가 각각의 강점을 발휘하는 설계. 이것이 Triple-Store 아키텍처를 선택한 이유를 가장 잘 보여준다.

ETL Engineer에게 -- 42K 청크와 170K 엔티티를 세 저장소에 정합성 있게 적재해준 것에 감사한다. 특히 Phase 2의 PG 동기화 과정에서 chunk_count 보정을 꼼꼼히 해준 덕분에, PostgreSQL과 Elasticsearch 간의 정합성이 100%를 달성할 수 있었다. 스키마 불일치(TD-001)는 내가 중앙 스키마 정의를 만들지 않은 탓이 크다. 다음 프로젝트에서는 반드시 Schema Registry 패턴을 도입하겠다.

세 개의 데이터베이스, 169,886개 노드, 775,366개 관계, 42,462개 청크, 100% 정합성. 숫자로 보면 대단해 보이지만, 이 숫자들 뒤에는 수많은 정합성 깨짐과 복구, 스키마 수정과 마이그레이션, 인덱스 재생성과 검증이 있었다. Triple-Store는 한번 제대로 동작하면 강력하지만, 그 "제대로"까지 가는 길이 멀었다.

---

*작성: Database Designer Agent (Sonnet 4.6) | 2026-02-19*
