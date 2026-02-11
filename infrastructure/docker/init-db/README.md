# Database Initialization Scripts

Hybrid RAG Knowledge Platform을 위한 데이터베이스 초기화 스크립트입니다.

## 구성 파일

| 파일 | 설명 |
|------|------|
| `init-db.sh` | 통합 초기화 스크립트 (PostgreSQL, Elasticsearch, Neo4j) |
| `01_postgresql_schema.sql` | PostgreSQL 스키마 DDL |
| `02_elasticsearch_mapping.json` | Elasticsearch 인덱스 매핑 정의 |
| `03_neo4j_constraints.cypher` | Neo4j 제약조건 및 인덱스 |

## 사용법

### Docker Compose 환경에서 자동 실행

`docker-compose.yml`에서 PostgreSQL init script로 마운트:

```yaml
postgresql:
  volumes:
    - ./init-db/init-db.sh:/docker-entrypoint-initdb.d/init-db.sh:ro
```

### 수동 실행

```bash
# 전체 초기화
./init-db.sh

# PostgreSQL만 초기화
./init-db.sh --postgres-only

# Elasticsearch만 초기화
./init-db.sh --elasticsearch-only

# Neo4j만 초기화
./init-db.sh --neo4j-only

# 특정 DB 건너뛰기
./init-db.sh --skip-postgres
./init-db.sh --skip-elasticsearch
./init-db.sh --skip-neo4j
```

### 환경 변수 설정

```bash
# PostgreSQL
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_USER=knowledge
export POSTGRES_PASSWORD=your_password
export POSTGRES_DB=knowledge

# Elasticsearch
export ELASTICSEARCH_HOST=localhost
export ELASTICSEARCH_PORT=9200

# Neo4j
export NEO4J_HOST=localhost
export NEO4J_BOLT_PORT=7687
export NEO4J_HTTP_PORT=7474
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=your_password

# Retry 설정
export MAX_RETRIES=30
export RETRY_INTERVAL=5
```

## PostgreSQL 스키마

### 주요 테이블

| 테이블 | 설명 |
|--------|------|
| `users` | 플랫폼 사용자 (인증/인가) |
| `audit_logs` | 감사 로그 (모든 시스템 활동 기록) |
| `documents` | 문서 마스터 레코드 (SSOT) |
| `chunks` | 문서 청크 (RAG 처리용) |
| `entities` | 추출된 엔티티 |
| `entity_relationships` | 엔티티 간 관계 |
| `projects` | 프로젝트 정보 |
| `persons` | 인물 정보 |
| `categories` | 계층적 카테고리 |
| `search_history` | 검색 이력 |
| `search_feedback` | 검색 피드백 |
| `system_config` | 시스템 설정 |

### 초기 데이터

- 기본 관리자 계정: `admin` / `admin123` (반드시 변경 필요)
- 기본 카테고리: Technical Documentation, Meeting Notes, Reports, Specifications
- 기본 시스템 설정값

## Elasticsearch 인덱스

### 인덱스 템플릿

| 템플릿 | 패턴 | 설명 |
|--------|------|------|
| `knowledge-chunks` | `knowledge-chunks-*` | 문서 청크 + 벡터 |
| `knowledge-documents` | `knowledge-documents-*` | 문서 메타데이터 (비정규화) |
| `knowledge-search-logs` | `knowledge-search-logs-*` | 검색 로그 |

### 벡터 필드

- `dense_vector`: 1024차원 Dense Vector (BGE-M3)
- `sparse_vector`: Sparse Vector (키워드 가중치)

### 초기 인덱스

- `knowledge-chunks-v1` (alias: `knowledge-chunks`)
- `knowledge-documents-v1` (alias: `knowledge-documents`)
- `knowledge-search-logs-v1` (alias: `knowledge-search-logs`)

## Neo4j 스키마

### 노드 타입

| 레이블 | 설명 | 주요 속성 |
|--------|------|----------|
| `Entity` | 추출된 엔티티 | id, name, type, description |
| `Document` | 문서 | id, title, document_type |
| `TextUnit` | 청크 | id, document_id, chunk_index |
| `Community` | 커뮤니티 클러스터 | id, title, summary, level |
| `Project` | 프로젝트 | id, name, code, status |
| `Person` | 인물 | id, name, department |
| `Technology` | 기술 | id, name, category |
| `Category` | 카테고리 | id, name, code, level |

### 관계 타입

| 관계 | 설명 |
|------|------|
| `RELATED_TO` | 엔티티 간 관계 |
| `MENTIONED_IN` | 엔티티가 청크에 언급됨 |
| `BELONGS_TO` | 엔티티가 커뮤니티에 속함 |
| `PART_OF` | 청크가 문서에 속함 |
| `PARENT_OF` | 계층 관계 (커뮤니티, 카테고리) |

### 제약조건

- 모든 노드 타입에 `id` 유니크 제약조건
- `Project.code`, `Category.code` 유니크 제약조건

## 주의사항

1. **초기 비밀번호 변경**: 기본 admin 계정의 비밀번호는 반드시 변경해야 합니다.
2. **Nori 플러그인**: Elasticsearch에서 한국어 분석을 위해 Nori 플러그인이 필요합니다.
3. **멱등성**: 스크립트는 이미 존재하는 스키마를 건너뛰므로 여러 번 실행해도 안전합니다.
4. **순서**: PostgreSQL -> Elasticsearch -> Neo4j 순서로 초기화됩니다.

## 문제 해결

### 연결 실패

```bash
# 서비스 상태 확인
docker-compose ps

# 로그 확인
docker-compose logs postgresql
docker-compose logs elasticsearch
docker-compose logs neo4j
```

### 스키마 재생성

```bash
# PostgreSQL: 데이터베이스 삭제 후 재생성
docker exec -it postgresql psql -U knowledge -c "DROP DATABASE knowledge;"
docker exec -it postgresql psql -U knowledge -c "CREATE DATABASE knowledge;"

# Elasticsearch: 인덱스 삭제
curl -X DELETE "http://localhost:9200/knowledge-*"

# Neo4j: 모든 노드/관계 삭제
docker exec -it neo4j cypher-shell -u neo4j -p password "MATCH (n) DETACH DELETE n"
```

## 참고 문서

- [인프라 상세 설계서](../../../knowledge_service/docs/02_design/10_infrastructure_detailed_design.md)
- [플랫폼 상세 설계서](../../../knowledge_service/docs/02_design/01_hybrid_rag_platform_detailed_design.md)
