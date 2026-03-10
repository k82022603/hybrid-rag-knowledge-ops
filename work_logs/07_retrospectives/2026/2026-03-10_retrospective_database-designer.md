# 프로젝트 회고 — Database Designer

**프로젝트**: Hybrid RAG Knowledge Platform 고도화
**기간**: 2026-01-10 ~ 2026-03-10
**역할**: PostgreSQL SSOT 스키마 설계, Elasticsearch Nori 인덱스 매핑, Neo4j 그래프 스키마, 3-Store 정합성 보장

---

## 1. 내가 기여한 것 (What I Did)

- **PostgreSQL SSOT 스키마 설계**: 문서, 청크, 사용자, 검색 이력 등 핵심 엔티티의 스키마를 설계하고, PostgreSQL을 SSOT(Single Source of Truth)로 확립했습니다. 모든 데이터 변경은 PostgreSQL에서 시작하여 다른 저장소로 동기화되는 구조입니다.
- **Elasticsearch Nori 매핑**: `knowledge_chunks` 인덱스의 매핑을 설계하고, Nori 한국어 분석기를 적용하여 형태소 단위의 정확한 키워드 검색을 가능하게 했습니다. custom analyzer 설정(nori_tokenizer + nori_part_of_speech 필터)을 정의했습니다.
- **Neo4j Entity/Relation 스키마**: Person, Organization, Project, Technology 등 엔티티 노드와 BELONGS_TO, WORKS_ON, USES 등 관계 타입을 설계했습니다. 그래프 탐색 쿼리(Cypher)의 성능을 위한 인덱스도 생성했습니다.
- **3-Store 정합성 보장**: PostgreSQL -> Elasticsearch, PostgreSQL -> Neo4j 간 데이터 정합성을 검증하는 스크립트를 작성하고, 주기적 정합성 체크 메커니즘을 구현했습니다.
- **쿼리 최적화**: EXPLAIN ANALYZE를 활용하여 느린 쿼리를 식별하고, 인덱스 추가/쿼리 재작성으로 응답 시간을 개선했습니다.

## 2. 잘된 점 (What Went Well)

- **SSOT 원칙 견지**: 3개 저장소 간 데이터 불일치가 발생해도 PostgreSQL을 기준으로 복구할 수 있는 구조를 유지하여, 데이터 정합성 문제를 빠르게 해결할 수 있었습니다.
- **Nori 매핑 설계**: "대한민국"을 "대한", "민국"이 아닌 "대한민국" 하나의 토큰으로 처리하도록 한 Nori 설정이 BM25 검색 품질에 크게 기여했습니다.

## 3. 아쉬운 점 (What Could Be Better)

- **Nori 설정 검증 지연**: Nori 매핑을 설계했지만, 실제 Docker 이미지에 플러그인이 설치되었는지 검증하지 않아 32일간 standard analyzer로 동작한 것은 뼈아픈 실수입니다. 설계자로서 구현 검증까지 책임졌어야 합니다.
- **Neo4j 스키마 진화 관리**: 프로젝트 진행 중 엔티티 타입이 추가될 때 마이그레이션 전략이 부재했습니다. 스키마 버전 관리 체계가 필요했습니다.
- **성능 벤치마크 미비**: 3-Store 각각의 읽기/쓰기 성능 벤치마크를 체계적으로 수행하지 못했습니다.

## 4. 배운 점 (What I Learned)

- **Polyglot Persistence의 복잡성**: 하나의 RDBMS가 아닌 3개의 이질적인 저장소를 조합하면 성능은 좋아지지만, 정합성 관리와 운영 복잡도가 기하급수적으로 증가합니다. SSOT 원칙이 없었으면 혼란에 빠졌을 것입니다.
- **분석기 설정은 인덱스 생성 시점에 확정**: Elasticsearch에서 분석기(analyzer)를 변경하려면 인덱스를 재생성해야 합니다. 초기 설계의 중요성을 체감했습니다.
- **그래프 DB의 표현력**: 관계형 DB에서 5-depth JOIN으로 표현해야 할 쿼리를, Neo4j에서는 2줄 Cypher로 해결할 수 있었습니다. "연결된 데이터"에는 그래프가 압도적입니다.

## 5. 다음 프로젝트에 바라는 점

- 스키마 마이그레이션 도구(Flyway/Alembic)를 3-Store 모두에 적용하여, 스키마 변경 이력을 코드로 관리하고 싶습니다.
- 저장소별 성능 벤치마크를 CI/CD에 통합하여, 스키마/인덱스 변경이 성능에 미치는 영향을 자동 감지하고 싶습니다.

## 6. 팀원들에게 한마디

데이터베이스는 보이지 않는 곳에서 묵묵히 일하는 존재입니다. 스키마가 잘 설계되면 아무도 언급하지 않지만, 문제가 생기면 모든 것이 멈춥니다. ETL Engineer와 매일 데이터 정합성을 논의하고, RAG Engineer가 필요로 하는 검색 성능을 충족하기 위해 매핑을 튜닝한 시간들이 의미 있었습니다. Nori 사고의 교훈을 잊지 않겠습니다. "설계했으면 검증하라." 모두 수고하셨습니다.
