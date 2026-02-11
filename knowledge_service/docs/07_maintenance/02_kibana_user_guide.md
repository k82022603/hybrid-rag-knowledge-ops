# Kibana 사용자 가이드

**Version**: 1.0 | **Updated**: 2026-01-21

---

## 목차

1. [개요](#1-개요)
2. [접속 및 초기 설정](#2-접속-및-초기-설정)
3. [Elasticsearch 연동 테스트](#3-elasticsearch-연동-테스트)
4. [주요 기능 사용법](#4-주요-기능-사용법)
5. [트러블슈팅](#5-트러블슈팅)

---

## 1. 개요

### 1.1 Kibana란?

Kibana는 Elasticsearch 데이터를 시각화하고 탐색하기 위한 오픈소스 도구입니다.

### 1.2 프로젝트 내 역할

| 용도 | 설명 |
|------|------|
| 로그 분석 | Elasticsearch에 저장된 로그 검색 및 분석 |
| 데이터 시각화 | 대시보드를 통한 시스템 모니터링 |
| 개발 도구 | Dev Tools를 통한 Elasticsearch 쿼리 테스트 |
| 인덱스 관리 | 인덱스 생성, 매핑 확인, 데이터 탐색 |

### 1.3 기술 스택

| 항목 | 버전 |
|------|------|
| Kibana | 8.11.0 |
| Elasticsearch | 8.11.0 |
| 컨테이너명 | kp-kibana |
| 포트 | 5601 |

---

## 2. 접속 및 초기 설정

### 2.1 Kibana 접속

**URL**: http://localhost:5601

### 2.2 컨테이너 상태 확인

```bash
# 컨테이너 상태 확인
docker ps --filter name=kp-kibana --format "table {{.Names}}\t{{.Status}}"

# 헬스체크 상태
docker inspect --format='{{.State.Health.Status}}' kp-kibana

# 로그 확인
docker logs kp-kibana --tail 20
```

### 2.3 Elasticsearch 연결 상태 확인

Kibana 접속 후:
1. **Menu** → **Stack Management** → **Stack Monitoring**
2. 또는 **Menu** → **Dev Tools** → Console에서:

```json
GET _cluster/health
```

**정상 응답 예시**:
```json
{
  "cluster_name" : "docker-cluster",
  "status" : "yellow",
  "number_of_nodes" : 1,
  "number_of_data_nodes" : 1,
  "active_primary_shards" : 1,
  "active_shards" : 1
}
```

> **Note**: 단일 노드 환경에서 `status: yellow`는 정상입니다 (replica가 없어서).

---

## 3. Elasticsearch 연동 테스트

### 3.1 테스트 인덱스 생성

**Dev Tools** (Menu → Dev Tools)에서 실행:

```json
PUT test-documents
{
  "mappings": {
    "properties": {
      "title": { "type": "text" },
      "content": { "type": "text" },
      "category": { "type": "keyword" },
      "created_at": { "type": "date" },
      "views": { "type": "integer" }
    }
  }
}
```

### 3.2 샘플 데이터 적재

```json
POST test-documents/_bulk
{"index":{}}
{"title":"Hybrid RAG 시스템 소개","content":"Graph RAG와 Vector RAG를 결합한 하이브리드 검색 시스템입니다.","category":"architecture","created_at":"2025-01-21","views":150}
{"index":{}}
{"title":"Elasticsearch 설정 가이드","content":"Elasticsearch 8.x 버전 설치 및 설정 방법을 안내합니다.","category":"infrastructure","created_at":"2025-01-20","views":89}
{"index":{}}
{"title":"Neo4j Knowledge Graph","content":"지식 그래프 구축을 위한 Neo4j 활용 방안입니다.","category":"data","created_at":"2025-01-19","views":120}
{"index":{}}
{"title":"FastAPI AI Service","content":"LangGraph 기반 AI 서비스 구현 가이드입니다.","category":"backend","created_at":"2025-01-18","views":200}
{"index":{}}
{"title":"React 18 Frontend","content":"MUI v5와 React Query를 활용한 프론트엔드 개발입니다.","category":"frontend","created_at":"2025-01-17","views":75}
```

### 3.3 데이터 확인

```json
# 문서 수 확인
GET test-documents/_count

# 전체 데이터 조회
GET test-documents/_search
{
  "query": { "match_all": {} }
}

# 특정 조건 검색
GET test-documents/_search
{
  "query": {
    "match": {
      "content": "RAG"
    }
  }
}

# 카테고리별 필터링
GET test-documents/_search
{
  "query": {
    "term": {
      "category": "architecture"
    }
  }
}
```

### 3.4 테스트 결과 예시

```json
{
  "took" : 1,
  "hits" : {
    "total" : { "value" : 5 },
    "hits" : [
      {
        "_source" : {
          "title" : "Hybrid RAG 시스템 소개",
          "category" : "architecture",
          "views" : 150
        }
      }
    ]
  }
}
```

---

## 4. 주요 기능 사용법

### 4.1 Data View 생성

인덱스 데이터를 Discover에서 탐색하려면 Data View가 필요합니다.

1. **Menu** → **Stack Management** → **Data Views**
2. **Create data view** 클릭
3. 설정:
   - **Name**: `test-documents`
   - **Index pattern**: `test-documents`
   - **Timestamp field**: `created_at` (또는 선택 안 함)
4. **Save data view to Kibana**

### 4.2 Discover (데이터 탐색)

1. **Menu** → **Discover**
2. 좌측 상단에서 Data View 선택 (`test-documents`)
3. 검색창에 KQL(Kibana Query Language) 입력:

```
# 예시 쿼리
content: "RAG"
category: "architecture"
views > 100
title: "Elasticsearch" AND category: "infrastructure"
```

### 4.3 Visualize (시각화)

1. **Menu** → **Visualize Library** → **Create visualization**
2. 시각화 유형 선택:
   - **Lens**: 드래그 앤 드롭 방식 (권장)
   - **Bar chart**: 카테고리별 문서 수
   - **Pie chart**: 카테고리 분포
   - **Metric**: 총 문서 수

**예시: 카테고리별 문서 수 (Lens)**
1. Lens 선택
2. 좌측에서 `category` 필드를 X축으로 드래그
3. Y축에 `Count` 설정
4. **Save** 클릭

### 4.4 Dashboard (대시보드)

1. **Menu** → **Dashboard** → **Create dashboard**
2. **Add panel** → 저장된 시각화 선택
3. 패널 배치 및 크기 조정
4. **Save** 클릭

### 4.5 Dev Tools (개발 도구)

**Menu** → **Dev Tools** → **Console**

주요 명령어:

```json
# 클러스터 정보
GET /

# 클러스터 상태
GET _cluster/health

# 인덱스 목록
GET _cat/indices?v

# 인덱스 매핑 확인
GET test-documents/_mapping

# 인덱스 설정 확인
GET test-documents/_settings

# 인덱스 삭제 (주의!)
DELETE test-documents
```

---

## 5. 트러블슈팅

### 5.1 Kibana 접속 불가

**증상**: http://localhost:5601 접속 시 연결 거부

**진단**:
```bash
# 컨테이너 상태 확인
docker ps --filter name=kp-kibana

# 포트 확인
docker port kp-kibana

# 로그 확인
docker logs kp-kibana --tail 50
```

**해결 방법**:
```bash
# 컨테이너 재시작
cd infrastructure/docker
docker compose restart kibana

# 또는 컨테이너 재생성
docker compose up -d kibana
```

### 5.2 Elasticsearch 연결 실패

**증상**: Kibana에서 "Kibana server is not ready yet" 메시지

**원인**: Elasticsearch가 준비되지 않음

**해결 방법**:
```bash
# Elasticsearch 상태 확인
curl -s http://localhost:9200/_cluster/health

# Elasticsearch 먼저 시작
docker compose up -d elasticsearch

# Elasticsearch healthy 확인 후 Kibana 시작
docker compose up -d kibana
```

### 5.3 인덱스를 찾을 수 없음

**증상**: `index_not_found_exception`

```json
{
  "error": {
    "type": "index_not_found_exception",
    "reason": "no such index [pdf-documents]"
  }
}
```

**진단**:
```json
# 존재하는 인덱스 확인
GET _cat/indices?v

# 패턴으로 검색
GET _cat/indices/*document*?v
```

**해결 방법**: 인덱스 생성 또는 올바른 인덱스명 사용

### 5.4 Data View 생성 실패

**증상**: "Couldn't find any matching indices"

**원인**: 인덱스에 데이터가 없거나 인덱스가 존재하지 않음

**해결 방법**:
1. 인덱스 존재 확인: `GET _cat/indices?v`
2. 데이터 존재 확인: `GET {index}/_count`
3. 인덱스 패턴 확인 (와일드카드 사용 가능: `logs-*`)

### 5.5 검색 결과 없음

**증상**: 쿼리 실행 시 hits가 0

**진단**:
```json
# 전체 데이터 조회
GET test-documents/_search
{
  "query": { "match_all": {} }
}

# 필드 매핑 확인
GET test-documents/_mapping
```

**확인 사항**:
- `text` 필드는 `match` 쿼리 사용
- `keyword` 필드는 `term` 쿼리 사용
- 대소문자 주의 (keyword는 정확히 일치해야 함)

---

## 유용한 명령어 모음

### Bash (터미널)

```bash
# Kibana 컨테이너 시작
docker compose up -d kibana

# Kibana 로그 실시간 확인
docker logs -f kp-kibana

# Kibana API 상태 확인
curl -s http://localhost:5601/api/status | python3 -m json.tool

# Elasticsearch 인덱스 목록 (터미널에서)
curl -s http://localhost:9200/_cat/indices?v
```

### Dev Tools (Kibana Console)

```json
# 클러스터 정보
GET /
GET _cluster/health
GET _cat/nodes?v

# 인덱스 관리
GET _cat/indices?v
GET {index}/_mapping
GET {index}/_settings
GET {index}/_count

# 검색
GET {index}/_search
POST {index}/_search
{ "query": { "match_all": {} } }

# 데이터 조작
POST {index}/_doc
{ "field": "value" }

DELETE {index}/_doc/{id}
```

---

## 관련 파일

| 파일 | 설명 |
|------|------|
| `infrastructure/docker/docker-compose.yml` | Kibana 컨테이너 설정 |
| `infrastructure/docker/.env` | KIBANA_PORT 환경 변수 |
| `knowledge_service/src/tests/e2e/infrastructure/test_container_health.py` | Kibana 헬스체크 테스트 |

---

## 참고 링크

- [Kibana 공식 문서](https://www.elastic.co/guide/en/kibana/current/index.html)
- [Elasticsearch 공식 문서](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)
- [KQL (Kibana Query Language)](https://www.elastic.co/guide/en/kibana/current/kuery-query.html)

---

## 변경 이력

| 날짜 | 버전 | 변경 내용 |
|------|------|----------|
| 2026-01-21 | 1.0 | 초기 문서 작성 (연동 테스트, 사용법, 트러블슈팅) |
