# Neo4j Knowledge Graph 조회 가이드

**Version**: 1.0 | **Created**: 2026-02-04 | **Author**: DevOps Team

---

## 목차

1. [접속 정보](#1-접속-정보)
2. [Neo4j Browser 사용법](#2-neo4j-browser-사용법)
3. [Cypher 쿼리 기본](#3-cypher-쿼리-기본)
4. [Knowledge Graph 조회](#4-knowledge-graph-조회)
5. [유용한 쿼리 모음](#5-유용한-쿼리-모음)
6. [데이터 관리](#6-데이터-관리)
7. [성능 최적화](#7-성능-최적화)
8. [트러블슈팅](#8-트러블슈팅)

---

## 1. 접속 정보

### 1.1 Neo4j Browser (웹 UI)

| 항목 | 값 |
|------|-----|
| **URL** | http://localhost:7474 |
| **Bolt URL** | bolt://localhost:7687 |
| **Username** | neo4j |
| **Password** | `password` (또는 환경변수 설정값) |

### 1.2 컨테이너 정보

```bash
# 컨테이너 상태 확인
docker ps --filter name=kp-neo4j

# 로그 확인
docker logs kp-neo4j --tail 50

# Cypher Shell 접속
docker exec -it kp-neo4j cypher-shell -u neo4j -p password
```

---

## 2. Neo4j Browser 사용법

### 2.1 접속

1. 브라우저에서 http://localhost:7474 접속
2. **Connect URL**: `bolt://localhost:7687`
3. **Username**: `neo4j`
4. **Password**: 설정된 비밀번호
5. **Connect** 클릭

### 2.2 UI 구성

```
┌─────────────────────────────────────────────────────────────┐
│  ⚡ Neo4j Browser                                            │
├─────────────────────────────────────────────────────────────┤
│  [Query Editor - Cypher 쿼리 입력]                           │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ MATCH (n) RETURN n LIMIT 25                             ││
│  └─────────────────────────────────────────────────────────┘│
│  [▶ Run] [↺ Reset] [💾 Save]                                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  [Graph Visualization / Table / Text / Code]                 │
│                                                              │
│      (Document)───[HAS_CHUNK]───▶(Chunk)                    │
│           │                         │                        │
│           └────[MENTIONS]───▶(Entity)                       │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│  📊 Stats: 150 nodes, 320 relationships                     │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 결과 보기 모드

| 모드 | 설명 | 단축키 |
|------|------|--------|
| **Graph** | 노드/관계 시각화 | - |
| **Table** | 테이블 형식 | - |
| **Text** | 텍스트 출력 | - |
| **Code** | JSON/Cypher | - |

---

## 3. Cypher 쿼리 기본

### 3.1 기본 문법

```cypher
// 노드 조회
MATCH (n:Label)
WHERE n.property = 'value'
RETURN n

// 관계 조회
MATCH (a)-[r:RELATIONSHIP]->(b)
RETURN a, r, b

// 패턴 매칭
MATCH (d:Document)-[:HAS_CHUNK]->(c:Chunk)-[:MENTIONS]->(e:Entity)
RETURN d, c, e
```

### 3.2 주요 키워드

| 키워드 | 설명 | 예제 |
|--------|------|------|
| `MATCH` | 패턴 검색 | `MATCH (n:Document)` |
| `WHERE` | 조건 필터 | `WHERE n.title CONTAINS '로깅'` |
| `RETURN` | 결과 반환 | `RETURN n.title, n.id` |
| `CREATE` | 노드/관계 생성 | `CREATE (n:Document {title: 'test'})` |
| `DELETE` | 삭제 | `DELETE n` |
| `SET` | 속성 설정 | `SET n.status = 'completed'` |
| `ORDER BY` | 정렬 | `ORDER BY n.created_at DESC` |
| `LIMIT` | 결과 제한 | `LIMIT 10` |
| `SKIP` | 건너뛰기 | `SKIP 10` |
| `WITH` | 중간 결과 | `WITH n, count(*) as cnt` |

### 3.3 연산자

```cypher
// 비교
WHERE n.count > 10
WHERE n.name = 'value'
WHERE n.name <> 'value'

// 문자열
WHERE n.title CONTAINS '검색어'
WHERE n.title STARTS WITH '차세대'
WHERE n.title ENDS WITH '.md'
WHERE n.title =~ '.*정규식.*'

// 리스트
WHERE n.id IN ['id1', 'id2']
WHERE 'tag' IN n.tags

// NULL
WHERE n.property IS NULL
WHERE n.property IS NOT NULL

// 논리
WHERE n.a = 1 AND n.b = 2
WHERE n.a = 1 OR n.b = 2
WHERE NOT n.deleted
```

---

## 4. Knowledge Graph 조회

### 4.1 스키마 확인

```cypher
// 노드 레이블 목록
CALL db.labels()

// 관계 유형 목록
CALL db.relationshipTypes()

// 속성 키 목록
CALL db.propertyKeys()

// 전체 스키마 시각화
CALL db.schema.visualization()
```

### 4.2 Knowledge Graph 노드 유형

| 레이블 | 설명 | 주요 속성 |
|--------|------|----------|
| `Document` | 문서 | id, title, file_path, status |
| `Chunk` | 문서 청크 | id, content, chunk_index, embedding |
| `Entity` | 추출된 엔티티 | id, name, type, description |
| `Topic` | 토픽/주제 | id, name, keywords |
| `Project` | 프로젝트 | id, name, description |

### 4.3 관계 유형

| 관계 | 설명 | 방향 |
|------|------|------|
| `HAS_CHUNK` | 문서 → 청크 | Document → Chunk |
| `MENTIONS` | 청크 → 엔티티 | Chunk → Entity |
| `RELATED_TO` | 엔티티 간 관계 | Entity → Entity |
| `BELONGS_TO` | 문서 → 프로젝트 | Document → Project |
| `HAS_TOPIC` | 문서 → 토픽 | Document → Topic |

---

## 5. 유용한 쿼리 모음

### 5.1 문서 조회

```cypher
// 모든 문서 조회 (최근 10개)
MATCH (d:Document)
RETURN d.id, d.title, d.status, d.created_at
ORDER BY d.created_at DESC
LIMIT 10

// 특정 상태의 문서
MATCH (d:Document)
WHERE d.status = 'completed'
RETURN d

// 제목으로 검색
MATCH (d:Document)
WHERE d.title CONTAINS '로깅'
RETURN d
```

### 5.2 청크 조회

```cypher
// 문서의 청크 조회
MATCH (d:Document {id: 'document-uuid'})-[:HAS_CHUNK]->(c:Chunk)
RETURN c.chunk_index, c.content
ORDER BY c.chunk_index

// 청크 수가 많은 문서
MATCH (d:Document)-[:HAS_CHUNK]->(c:Chunk)
WITH d, count(c) as chunk_count
WHERE chunk_count > 10
RETURN d.title, chunk_count
ORDER BY chunk_count DESC
```

### 5.3 엔티티 조회

```cypher
// 모든 엔티티 유형
MATCH (e:Entity)
RETURN DISTINCT e.type, count(e) as count
ORDER BY count DESC

// 특정 유형의 엔티티
MATCH (e:Entity)
WHERE e.type = 'TECHNOLOGY'
RETURN e.name, e.description

// 가장 많이 언급된 엔티티
MATCH (c:Chunk)-[:MENTIONS]->(e:Entity)
WITH e, count(c) as mention_count
RETURN e.name, e.type, mention_count
ORDER BY mention_count DESC
LIMIT 10
```

### 5.4 관계 탐색

```cypher
// 엔티티 간 관계
MATCH (e1:Entity)-[r:RELATED_TO]->(e2:Entity)
RETURN e1.name, type(r), e2.name
LIMIT 20

// 특정 엔티티와 연결된 문서
MATCH (d:Document)-[:HAS_CHUNK]->(c:Chunk)-[:MENTIONS]->(e:Entity {name: 'Java'})
RETURN DISTINCT d.title

// 2홉 이내 연결된 엔티티
MATCH (e1:Entity {name: 'Spring'})-[:RELATED_TO*1..2]-(e2:Entity)
RETURN e1, e2
```

### 5.5 통계 쿼리

```cypher
// 전체 노드 수
MATCH (n) RETURN count(n) as total_nodes

// 레이블별 노드 수
MATCH (n)
RETURN labels(n)[0] as label, count(n) as count
ORDER BY count DESC

// 관계 수
MATCH ()-[r]->() RETURN count(r) as total_relationships

// 관계 유형별 수
MATCH ()-[r]->()
RETURN type(r) as relationship_type, count(r) as count
ORDER BY count DESC

// 문서별 엔티티 수
MATCH (d:Document)-[:HAS_CHUNK]->(c:Chunk)-[:MENTIONS]->(e:Entity)
WITH d, count(DISTINCT e) as entity_count
RETURN d.title, entity_count
ORDER BY entity_count DESC
LIMIT 10
```

### 5.6 그래프 시각화 쿼리

```cypher
// 문서-청크-엔티티 관계 시각화 (샘플)
MATCH path = (d:Document)-[:HAS_CHUNK]->(c:Chunk)-[:MENTIONS]->(e:Entity)
RETURN path
LIMIT 50

// 특정 문서의 Knowledge Graph
MATCH path = (d:Document {title: '차세대 컨택센터 고도화 프로젝트-로깅 표준 가이드 v4.0.md'})-[*1..3]-(n)
RETURN path

// 엔티티 네트워크
MATCH path = (e1:Entity)-[:RELATED_TO]-(e2:Entity)
RETURN path
LIMIT 100
```

---

## 6. 데이터 관리

### 6.1 데이터 삽입

```cypher
// 문서 노드 생성
CREATE (d:Document {
    id: 'doc-001',
    title: 'Sample Document',
    file_path: '/path/to/file.md',
    status: 'uploaded',
    created_at: datetime()
})
RETURN d

// 관계 생성
MATCH (d:Document {id: 'doc-001'}), (c:Chunk {id: 'chunk-001'})
CREATE (d)-[:HAS_CHUNK]->(c)
```

### 6.2 데이터 수정

```cypher
// 속성 업데이트
MATCH (d:Document {id: 'doc-001'})
SET d.status = 'completed',
    d.updated_at = datetime()
RETURN d

// 속성 추가
MATCH (d:Document {id: 'doc-001'})
SET d.processed_by = 'pipeline-v1'
RETURN d
```

### 6.3 데이터 삭제

```cypher
// 특정 노드 삭제 (관계도 함께)
MATCH (d:Document {id: 'doc-001'})
DETACH DELETE d

// 관계만 삭제
MATCH (d:Document)-[r:HAS_CHUNK]->(c:Chunk)
WHERE d.id = 'doc-001'
DELETE r

// 오래된 데이터 삭제 (주의!)
MATCH (d:Document)
WHERE d.created_at < datetime() - duration('P30D')
DETACH DELETE d
```

---

## 7. 성능 최적화

### 7.1 인덱스 관리

```cypher
// 인덱스 생성
CREATE INDEX document_id FOR (d:Document) ON (d.id)
CREATE INDEX chunk_id FOR (c:Chunk) ON (c.id)
CREATE INDEX entity_name FOR (e:Entity) ON (e.name)

// 인덱스 목록
SHOW INDEXES

// 인덱스 삭제
DROP INDEX document_id
```

### 7.2 제약조건

```cypher
// 유니크 제약조건
CREATE CONSTRAINT document_unique_id FOR (d:Document) REQUIRE d.id IS UNIQUE

// 제약조건 목록
SHOW CONSTRAINTS
```

### 7.3 쿼리 최적화 팁

```cypher
// EXPLAIN으로 실행 계획 확인
EXPLAIN MATCH (d:Document)-[:HAS_CHUNK]->(c:Chunk)
RETURN d, c

// PROFILE로 실제 실행 통계 확인
PROFILE MATCH (d:Document)-[:HAS_CHUNK]->(c:Chunk)
RETURN d, c
```

---

## 8. 트러블슈팅

### 8.1 연결 문제

| 증상 | 원인 | 해결 |
|------|------|------|
| 연결 거부 | 컨테이너 미실행 | `docker compose up -d neo4j` |
| 인증 실패 | 비밀번호 오류 | 환경변수 확인 |
| 타임아웃 | 네트워크 문제 | 방화벽 확인 |

### 8.2 쿼리 문제

| 증상 | 원인 | 해결 |
|------|------|------|
| 느린 쿼리 | 인덱스 미설정 | 인덱스 생성 |
| 메모리 부족 | 대량 데이터 반환 | LIMIT 추가 |
| 빈 결과 | 잘못된 조건 | WHERE 조건 확인 |

### 8.3 운영 명령어

```bash
# Neo4j 상태 확인
docker exec kp-neo4j neo4j status

# 헬스체크
curl http://localhost:7474

# 데이터베이스 크기
docker exec kp-neo4j du -sh /data

# 로그 확인
docker logs kp-neo4j --tail 100
```

---

## 부록: 빠른 참조

### Cypher 치트시트

```cypher
// 기본 패턴
MATCH (n)                    // 모든 노드
MATCH (n:Label)              // 레이블로 필터
MATCH (n)-[r]->(m)           // 관계 포함
MATCH (n)-[r:TYPE]->(m)      // 관계 유형 지정
MATCH (n)-[*1..3]->(m)       // 가변 길이 경로

// 집계
count(), sum(), avg(), min(), max()
collect()   // 리스트로 수집
size()      // 크기

// 문자열
toLower(), toUpper()
substring(), replace()
split(), trim()

// 날짜/시간
datetime(), date(), time()
duration()
```

---

*Document Version: 1.0*
*Last Updated: 2026-02-04*
*Maintainer: DevOps Team*
