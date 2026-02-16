# 개발환경 사용자 테스트 가이드

**Version**: 1.0.0
**Last Updated**: 2026-02-04
**Environment**: Development (Docker Compose)

---

## 목차

1. [사전 준비](#1-사전-준비)
2. [서비스 시작](#2-서비스-시작)
3. [헬스체크](#3-헬스체크)
4. [Full Cycle 테스트](#4-full-cycle-테스트)
   - 4.1 [인증 (Login)](#41-인증-login)
   - 4.2 [문서 업로드](#42-문서-업로드)
   - 4.3 [문서 처리 확인](#43-문서-처리-확인)
   - 4.4 [검색 테스트](#44-검색-테스트)
   - 4.5 [RAG 채팅 테스트](#45-rag-채팅-테스트)
   - 4.6 [Knowledge Graph 탐색](#46-knowledge-graph-탐색)
5. [모니터링 확인](#5-모니터링-확인)
6. [API 직접 테스트](#6-api-직접-테스트)
7. [문제 해결](#7-문제-해결)
8. [테스트 체크리스트](#8-테스트-체크리스트)

---

## 1. 사전 준비

### 1.1 시스템 요구사항

| 항목 | 최소 사양 | 권장 사양 |
|------|----------|----------|
| CPU | 4 cores | 8+ cores |
| RAM | 16 GB | 32 GB |
| Disk | 50 GB SSD | 100 GB SSD |
| Docker | 24.x | 최신 |
| Docker Compose | v2.x | 최신 |

### 1.2 필수 포트 확인

다음 포트가 사용 가능한지 확인하세요:

```bash
# 포트 사용 여부 확인 (Windows PowerShell)
netstat -an | findstr "3000 8080 9000 5432 9200 7474 7687 6379 9090 3001"

# 포트 사용 여부 확인 (Linux/WSL)
ss -tuln | grep -E '3000|8080|9000|5432|9200|7474|7687|6379|9090|3001'
```

### 1.3 환경변수 확인

```bash
cd /mnt/d/Users/KTDS/Documents/06.과제/hybrid-rag-knowledge-ops/infrastructure/docker

# .env 파일 존재 확인
ls -la .env

# DeepSeek API Key 설정 확인 (실제 키 필요)
grep DEEPSEEK_API_KEY .env
```

> **중요**: `DEEPSEEK_API_KEY`가 설정되어 있어야 RAG 채팅이 작동합니다.

---

## 2. 서비스 시작

### 2.1 전체 서비스 시작

```bash
cd /mnt/d/Users/KTDS/Documents/06.과제/hybrid-rag-knowledge-ops/infrastructure/docker

# 전체 서비스 시작 (백그라운드)
docker-compose up -d

# 로그 실시간 확인 (선택사항)
docker-compose logs -f
```

### 2.2 서비스 시작 순서

서비스는 의존성에 따라 자동으로 순서대로 시작됩니다:

```
1. 데이터베이스 계층: PostgreSQL, Neo4j, Elasticsearch, Redis
2. 인프라 계층: MinIO, Keycloak
3. 애플리케이션 계층: Backend, AI Service, Gateway
4. 프론트엔드 계층: Frontend (React)
5. 모니터링 계층: Prometheus, Grafana, Loki, Jaeger
```

### 2.3 시작 완료 대기

모든 서비스가 healthy 상태가 될 때까지 대기합니다 (약 2-3분 소요):

```bash
# 컨테이너 상태 확인
docker-compose ps

# 모든 서비스가 'Up' 또는 'healthy' 상태인지 확인
watch -n 5 'docker-compose ps'
```

---

## 3. 헬스체크

### 3.1 자동 헬스체크 스크립트

```bash
# 전체 헬스체크 실행
./scripts/post-deploy-verify.sh

# 또는 프로젝트 루트에서
cd /mnt/d/Users/KTDS/Documents/06.과제/hybrid-rag-knowledge-ops
./infrastructure/scripts/post-deploy-verify.sh
```

### 3.2 개별 서비스 헬스체크

| 서비스 | 헬스체크 URL | 예상 응답 |
|--------|-------------|----------|
| Gateway | http://localhost:8080/actuator/health | `{"status":"UP"}` |
| Backend | http://localhost:8081/actuator/health | `{"status":"UP"}` |
| AI Service | http://localhost:8000/health | `{"status":"healthy"}` |
| Keycloak | http://localhost:9000/health | `{"status":"UP"}` |
| Elasticsearch | http://localhost:9200/_cluster/health | `{"status":"green/yellow"}` |
| Neo4j | http://localhost:7474 | Browser 페이지 |

### 3.3 CLI 헬스체크 명령어

```bash
# Gateway
curl -s http://localhost:8080/actuator/health | jq .

# AI Service
curl -s http://localhost:8000/health | jq .

# Elasticsearch 클러스터
curl -s http://localhost:9200/_cluster/health | jq .

# Neo4j (Bolt 연결 테스트)
curl -s http://localhost:7474/db/neo4j/tx | head -5
```

---

## 4. Full Cycle 테스트

### 4.1 인증 (Login)

#### 4.1.1 Frontend 로그인

1. 브라우저에서 http://localhost:3000 접속
2. Keycloak 로그인 페이지로 리다이렉트됨
3. 테스트 계정으로 로그인:

| 계정 유형 | Username | Password | 권한 |
|----------|----------|----------|------|
| 관리자 | `admin` | `admin123` | 전체 권한 |
| 일반 사용자 | `user` | `user123` | 기본 권한 |
| 테스트 계정 | `test` | `test123` | 읽기 전용 |

> **참고**: 테스트 계정이 없는 경우 Keycloak Admin Console에서 생성

#### 4.1.2 Keycloak Admin Console

1. http://localhost:9000/admin 접속
2. Admin 계정: `admin` / `admin`
3. Realm: `hybrid-rag` 선택
4. Users 메뉴에서 사용자 관리

#### 4.1.3 API 토큰 획득 (CLI 테스트용)

```bash
# Access Token 획득
TOKEN=$(curl -s -X POST "http://localhost:9000/realms/hybrid-rag/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=knowledge-frontend" \
  -d "username=admin" \
  -d "password=admin123" | jq -r '.access_token')

echo $TOKEN
```

---

### 4.2 문서 업로드

#### 4.2.1 UI를 통한 업로드

1. Frontend (http://localhost:3000)에 로그인
2. 좌측 메뉴에서 **"문서 관리"** 또는 **"Documents"** 클릭
3. **"업로드"** 버튼 클릭
4. 테스트 문서 선택 (PDF, TXT, DOCX 지원)
5. 업로드 진행률 확인
6. 업로드 완료 메시지 확인

#### 4.2.2 API를 통한 업로드

```bash
# 테스트 문서 생성
echo "이것은 테스트 문서입니다.
하이브리드 RAG 시스템은 벡터 검색과 그래프 검색을 결합합니다.
DeepSeek LLM을 사용하여 자연어 응답을 생성합니다." > /tmp/test_document.txt

# 문서 업로드 API 호출
curl -X POST "http://localhost:8080/api/v1/documents/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/tmp/test_document.txt" \
  -F "title=테스트 문서" \
  -F "description=Full Cycle 테스트용 문서"
```

#### 4.2.3 지원 파일 형식

| 형식 | 확장자 | 최대 크기 | 비고 |
|------|--------|----------|------|
| PDF | `.pdf` | 50 MB | OCR 지원 |
| Text | `.txt` | 10 MB | UTF-8 권장 |
| Word | `.docx` | 30 MB | 이미지 추출 지원 |
| Markdown | `.md` | 10 MB | 코드 블록 지원 |

---

### 4.3 문서 처리 확인

#### 4.3.1 처리 상태 확인 (UI)

1. **"문서 관리"** 페이지에서 업로드한 문서 확인
2. 처리 상태 컬럼 확인:
   - `PENDING`: 대기 중
   - `PROCESSING`: 처리 중
   - `COMPLETED`: 완료
   - `FAILED`: 실패

#### 4.3.2 처리 상태 확인 (API)

```bash
# 문서 목록 조회
curl -s "http://localhost:8080/api/v1/documents" \
  -H "Authorization: Bearer $TOKEN" | jq .

# 특정 문서 상태 조회 (document_id 필요)
curl -s "http://localhost:8080/api/v1/documents/{document_id}" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

#### 4.3.3 처리 파이프라인 확인

문서 처리 과정:

```
업로드 → 텍스트 추출 → 청킹 → 임베딩 → 벡터 저장 → 엔티티 추출 → 그래프 저장
```

각 단계 확인:

```bash
# Elasticsearch에서 벡터 인덱스 확인
curl -s "http://localhost:9200/knowledge_vectors/_count" | jq .

# Neo4j에서 엔티티 확인 (Cypher 쿼리)
curl -s -X POST "http://localhost:7474/db/neo4j/tx/commit" \
  -H "Content-Type: application/json" \
  -d '{"statements":[{"statement":"MATCH (n) RETURN labels(n) as type, count(*) as count"}]}'
```

---

### 4.4 검색 테스트

#### 4.4.1 UI 검색

1. Frontend에서 **"검색"** 메뉴 클릭
2. 검색창에 쿼리 입력 (예: "RAG 시스템이란?")
3. 검색 결과 확인:
   - 관련 문서 청크
   - 관련성 점수
   - 하이라이팅

#### 4.4.2 하이브리드 검색 API

```bash
# 하이브리드 검색 (벡터 + 키워드 + 그래프)
curl -s -X POST "http://localhost:8080/api/v1/search" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "하이브리드 RAG 시스템",
    "search_type": "hybrid",
    "top_k": 5,
    "filters": {}
  }' | jq .
```

#### 4.4.3 검색 유형별 테스트

```bash
# 1. 벡터 검색만
curl -s -X POST "http://localhost:8080/api/v1/search" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "임베딩 벡터", "search_type": "vector", "top_k": 5}' | jq .

# 2. 키워드 검색만 (BM25)
curl -s -X POST "http://localhost:8080/api/v1/search" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "DeepSeek LLM", "search_type": "keyword", "top_k": 5}' | jq .

# 3. 그래프 검색
curl -s -X POST "http://localhost:8080/api/v1/search" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "관련 기술", "search_type": "graph", "top_k": 5}' | jq .
```

---

### 4.5 RAG 채팅 테스트

#### 4.5.1 UI 채팅

1. Frontend에서 **"채팅"** 또는 **"Ask AI"** 메뉴 클릭
2. 질문 입력 (예: "하이브리드 RAG 시스템의 장점은 무엇인가요?")
3. AI 응답 확인:
   - 자연어 답변
   - 참조된 문서 (Sources)
   - 신뢰도 점수

#### 4.5.2 RAG 채팅 API

```bash
# RAG 채팅 요청
curl -s -X POST "http://localhost:8080/api/v1/chat" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "하이브리드 RAG 시스템의 장점을 설명해주세요.",
    "conversation_id": null,
    "use_rag": true
  }' | jq .
```

#### 4.5.3 대화 이력 테스트

```bash
# 첫 번째 메시지
RESPONSE=$(curl -s -X POST "http://localhost:8080/api/v1/chat" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "RAG란 무엇인가요?", "conversation_id": null}')

CONV_ID=$(echo $RESPONSE | jq -r '.conversation_id')
echo "Conversation ID: $CONV_ID"

# 후속 질문 (같은 대화)
curl -s -X POST "http://localhost:8080/api/v1/chat" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"그것의 장점은?\", \"conversation_id\": \"$CONV_ID\"}" | jq .
```

#### 4.5.4 RAG 품질 확인 포인트

| 확인 항목 | 기대 결과 |
|----------|----------|
| 응답 관련성 | 질문과 관련된 내용 포함 |
| 소스 인용 | 참조 문서 표시 |
| 환각 없음 | 문서에 없는 내용 생성 안함 |
| 응답 시간 | 5초 이내 |

---

### 4.6 Knowledge Graph 탐색

#### 4.6.1 Neo4j Browser 접속

1. http://localhost:7474 접속
2. Connect 정보:
   - Connect URL: `bolt://localhost:7687`
   - Username: `neo4j`
   - Password: `.env` 파일의 `NEO4J_PASSWORD` 값

#### 4.6.2 기본 Cypher 쿼리

```cypher
// 전체 노드 수 확인
MATCH (n) RETURN count(n) as total_nodes;

// 노드 타입별 카운트
MATCH (n) RETURN labels(n) as type, count(*) as count ORDER BY count DESC;

// 관계 타입별 카운트
MATCH ()-[r]->() RETURN type(r) as relationship, count(*) as count ORDER BY count DESC;

// 특정 문서와 관련된 엔티티 조회
MATCH (d:Document)-[r]-(e)
WHERE d.title CONTAINS '테스트'
RETURN d, r, e LIMIT 50;

// 엔티티 간 연결 탐색
MATCH path = (a:Entity)-[*1..3]-(b:Entity)
WHERE a.name CONTAINS 'RAG'
RETURN path LIMIT 20;
```

#### 4.6.3 그래프 시각화

Neo4j Browser에서 쿼리 결과를 그래프로 시각화하여 확인:
- 노드 색상: 타입별 구분
- 관계 방향: 화살표로 표시
- 속성 확인: 노드/관계 클릭

---

## 5. 모니터링 확인

### 5.1 Grafana 대시보드

1. http://localhost:3001 접속
2. 로그인: `admin` / `admin`
3. 대시보드 확인:

| 대시보드 | 내용 |
|----------|------|
| System Overview | CPU, Memory, 컨테이너 상태 |
| Application Metrics | 요청 수, 에러율, 레이턴시 |
| Database Metrics | PostgreSQL, ES, Neo4j, Redis |
| RAG & SLA | RAG 성능, SLA 지표 |

### 5.2 Prometheus 메트릭

1. http://localhost:9090 접속
2. 쿼리 예시:

```promql
# 요청 수
rate(http_server_requests_seconds_count[5m])

# 평균 응답 시간
rate(http_server_requests_seconds_sum[5m]) / rate(http_server_requests_seconds_count[5m])

# 에러율
sum(rate(http_server_requests_seconds_count{status=~"5.."}[5m])) / sum(rate(http_server_requests_seconds_count[5m]))
```

### 5.3 로그 확인 (Kibana)

1. http://localhost:5601 접속
2. Discover 메뉴에서 로그 검색
3. 필터 예시:
   - `container_name: kp-backend`
   - `level: ERROR`
   - `message: *exception*`

### 5.4 분산 추적 (Jaeger)

1. http://localhost:16686 접속
2. Service 선택 후 Trace 검색
3. 요청 흐름 시각화 확인

---

## 6. API 직접 테스트

### 6.1 Swagger UI

- Gateway: http://localhost:8080/swagger-ui.html
- AI Service: http://localhost:8000/docs

### 6.2 주요 API 엔드포인트

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/v1/documents` | 문서 목록 |
| POST | `/api/v1/documents/upload` | 문서 업로드 |
| GET | `/api/v1/documents/{id}` | 문서 상세 |
| DELETE | `/api/v1/documents/{id}` | 문서 삭제 |
| POST | `/api/v1/search` | 하이브리드 검색 |
| POST | `/api/v1/chat` | RAG 채팅 |
| GET | `/api/v1/chat/history` | 대화 이력 |
| GET | `/api/v1/graph/entities` | 엔티티 목록 |
| GET | `/api/v1/graph/relationships` | 관계 목록 |

### 6.3 API 테스트 스크립트

```bash
#!/bin/bash
# api_test.sh - Full Cycle API 테스트

BASE_URL="http://localhost:8080"
TOKEN="YOUR_TOKEN_HERE"

echo "=== 1. Health Check ==="
curl -s "$BASE_URL/actuator/health" | jq .

echo -e "\n=== 2. Document List ==="
curl -s "$BASE_URL/api/v1/documents" -H "Authorization: Bearer $TOKEN" | jq .

echo -e "\n=== 3. Search Test ==="
curl -s -X POST "$BASE_URL/api/v1/search" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "테스트", "search_type": "hybrid", "top_k": 3}' | jq .

echo -e "\n=== 4. Chat Test ==="
curl -s -X POST "$BASE_URL/api/v1/chat" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "안녕하세요?", "use_rag": true}' | jq .

echo -e "\n=== Test Complete ==="
```

---

## 7. 문제 해결

### 7.1 자주 발생하는 문제

#### 서비스가 시작되지 않음

```bash
# 로그 확인
docker-compose logs <service-name>

# 컨테이너 재시작
docker-compose restart <service-name>

# 전체 재시작
docker-compose down && docker-compose up -d
```

#### 포트 충돌

```bash
# 사용 중인 포트 확인
netstat -tuln | grep <port>

# 프로세스 종료 (Linux)
sudo kill $(lsof -t -i:<port>)
```

#### Elasticsearch 메모리 부족

```bash
# vm.max_map_count 증가 (WSL2)
sudo sysctl -w vm.max_map_count=262144
```

#### Keycloak 로그인 실패

1. Keycloak Admin Console 접속
2. Realm Settings → Login 탭
3. "Require SSL" 설정 확인 (개발환경은 `none`)

### 7.2 로그 위치

| 서비스 | 로그 확인 방법 |
|--------|---------------|
| Docker 컨테이너 | `docker-compose logs -f <service>` |
| Backend | Kibana 또는 `docker logs kp-backend` |
| AI Service | `docker logs kp-ai-service` |
| Nginx | `docker logs kp-nginx` |

### 7.3 데이터 초기화

```bash
# 주의: 모든 데이터가 삭제됩니다!
docker-compose down -v  # 볼륨 포함 삭제
docker-compose up -d    # 새로 시작
```

---

## 8. 테스트 체크리스트

### Full Cycle 테스트 체크리스트

아래 항목을 순서대로 테스트하고 체크하세요:

#### 환경 준비
- [ ] Docker Compose 서비스 전체 시작
- [ ] 모든 컨테이너 healthy 상태 확인
- [ ] 헬스체크 스크립트 통과

#### 인증
- [ ] Frontend 로그인 성공
- [ ] Keycloak Admin Console 접속
- [ ] API 토큰 획득 성공

#### 문서 관리
- [ ] PDF 문서 업로드 성공
- [ ] TXT 문서 업로드 성공
- [ ] 문서 처리 완료 확인 (COMPLETED 상태)
- [ ] 문서 목록 조회 성공
- [ ] 문서 삭제 성공

#### 검색
- [ ] 하이브리드 검색 결과 반환
- [ ] 벡터 검색 결과 반환
- [ ] 키워드 검색 결과 반환
- [ ] 검색 결과 관련성 확인

#### RAG 채팅
- [ ] 단일 질문 응답 성공
- [ ] 대화 이력 유지 확인
- [ ] 소스 문서 인용 확인
- [ ] 응답 시간 5초 이내

#### Knowledge Graph
- [ ] Neo4j Browser 접속
- [ ] 노드/관계 생성 확인
- [ ] 그래프 탐색 쿼리 실행

#### 모니터링
- [ ] Grafana 대시보드 확인
- [ ] Prometheus 메트릭 확인
- [ ] Kibana 로그 검색
- [ ] Jaeger 트레이스 확인

---

## 부록: 테스트 데이터

### 샘플 테스트 문서

`/tmp/sample_test.txt` 내용:

```text
하이브리드 RAG (Retrieval-Augmented Generation) 시스템 개요

1. 소개
하이브리드 RAG 시스템은 기존 RAG의 벡터 검색에 지식 그래프(Knowledge Graph)를
결합한 차세대 검색 증강 생성 시스템입니다.

2. 핵심 기술
- 벡터 검색: BGE-M3 임베딩 모델 사용
- 그래프 검색: Neo4j 기반 지식 그래프
- LLM: DeepSeek V3 모델

3. 장점
- 의미론적 검색과 구조적 검색의 결합
- 높은 검색 정확도
- 관계 기반 추론 가능

4. 사용 사례
- 기업 지식 관리
- 기술 문서 검색
- 고객 지원 챗봇
```

### 샘플 테스트 쿼리

| 쿼리 | 예상 결과 |
|------|----------|
| "RAG 시스템이란?" | 시스템 개요 설명 |
| "사용된 임베딩 모델은?" | BGE-M3 언급 |
| "하이브리드 RAG의 장점" | 3가지 장점 나열 |
| "지식 그래프란?" | Neo4j 관련 설명 |

---

*Document Created: 2026-02-04*
*Author: Claude Code (Opus 4.5)*
