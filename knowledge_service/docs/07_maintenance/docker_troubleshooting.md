# Docker Compose 트러블슈팅 가이드

**Version**: 1.0 | **Updated**: 2026-01-20

---

## 목차

1. [포트 매핑 문제](#1-포트-매핑-문제)
2. [컨테이너 시작 실패](#2-컨테이너-시작-실패)
3. [네트워크 연결 문제](#3-네트워크-연결-문제)
4. [볼륨 마운트 문제](#4-볼륨-마운트-문제)

---

## 1. 포트 매핑 문제

### 1.1 증상: localhost에서 Connection Refused

**증상**:
```
requests.exceptions.ConnectionError: HTTPConnectionPool(host='localhost', port=9200):
Max retries exceeded with url: /
(Caused by NewConnectionError: Failed to establish a new connection: [Errno 111] Connection refused)
```

**영향받는 서비스**:
- Neo4j (7474, 7687)
- Elasticsearch (9200)
- MinIO (9000, 9001)

**원인**:
`docker-compose.yml`에서 `database` 네트워크가 `internal: true`로 설정되어 있어
외부(localhost)에서 컨테이너로 접근이 차단됨.

```yaml
# 문제가 되는 설정
networks:
  database:
    driver: bridge
    internal: true  # 이 설정이 localhost 접근을 차단
    name: kp-database
```

**해결 방법**:

1. `infrastructure/docker/docker-compose.yml` 수정:
```yaml
networks:
  database:
    driver: bridge
    # internal: true  # 개발 환경에서 localhost 포트 접근을 위해 비활성화
    name: kp-database
```

2. 컨테이너 재시작:
```bash
cd infrastructure/docker
docker compose down
docker compose up -d postgresql neo4j elasticsearch redis minio keycloak keycloak-db prometheus grafana loki promtail jaeger
```

3. 포트 접근성 확인:
```bash
# Neo4j
curl -s -o /dev/null -w "%{http_code}" http://localhost:7474
# 예상 결과: 200

# Elasticsearch
curl -s http://localhost:9200 | head -5
# 예상 결과: 클러스터 정보 JSON

# MinIO
curl -s -o /dev/null -w "%{http_code}" http://localhost:9000/minio/health/live
# 예상 결과: 200
```

**참고 사항**:
- `internal: true` 설정은 보안상 Production 환경에서 권장됨
- 개발 환경에서는 디버깅과 테스트를 위해 비활성화 가능
- 테스트 코드에서 `test_database_network_exists`가 `Internal: False`를 실패로 처리하므로,
  개발 환경용 테스트 설정 분리 권장

---

## 2. 컨테이너 시작 실패

### 2.1 증상: Dockerfile not found

**증상**:
```
target ai-service: failed to solve: failed to read dockerfile: open Dockerfile: no such file or directory
```

**원인**:
Application Layer 서비스 (frontend, backend, api-gateway, ai-service)의 Dockerfile이 아직 생성되지 않음.

**해결 방법**:

인프라 서비스만 먼저 시작:
```bash
docker compose up -d postgresql neo4j elasticsearch redis minio \
  keycloak keycloak-db prometheus grafana loki promtail jaeger
```

### 2.2 증상: Neo4j 볼륨 마운트 오류

**증상**:
```
Error response from daemon: invalid mount config for type "bind":
bind source path does not exist: /var/lib/neo4j/init/schema.cypher
```

**원인**:
Neo4j 컨테이너 내부 경로가 잘못 지정됨.

**해결 방법**:
```yaml
# Before (잘못된 경로)
volumes:
  - ../database/neo4j/schema.cypher:/var/lib/neo4j/init/schema.cypher:ro

# After (올바른 경로)
volumes:
  - ../database/neo4j/schema.cypher:/import/schema.cypher:ro
```

### 2.3 증상: MinIO 이미지 태그 오류

**증상**:
```
pull access denied for minio/minio:RELEASE.2024-01-01T00-00-00Z
```

**원인**:
특정 릴리즈 태그가 존재하지 않거나 접근 불가.

**해결 방법**:
```yaml
# Before
image: minio/minio:RELEASE.2024-01-01T00-00-00Z

# After
image: minio/minio:latest
```

---

## 3. 네트워크 연결 문제

### 3.1 컨테이너 간 통신 확인

```bash
# 네트워크 목록 확인
docker network ls | grep kp

# 특정 네트워크의 컨테이너 확인
docker network inspect kp-database

# 컨테이너 간 연결 테스트 (예: ai-service → elasticsearch)
docker exec kp-ai-service curl -s http://elasticsearch:9200
```

### 3.2 DNS 해결 문제

**증상**: 서비스 이름으로 연결 실패

**해결 방법**:
1. 같은 네트워크에 있는지 확인
2. 서비스 이름이 docker-compose.yml의 서비스명과 일치하는지 확인
3. 컨테이너 재시작

---

## 4. 볼륨 마운트 문제

### 4.1 권한 문제

**증상**:
```
Permission denied: '/var/lib/postgresql/data'
```

**해결 방법**:
```bash
# 볼륨 삭제 후 재생성
docker volume rm kp-postgresql-data
docker compose up -d postgresql
```

### 4.2 볼륨 데이터 초기화

```bash
# 특정 볼륨 삭제
docker volume rm kp-neo4j-data

# 모든 프로젝트 볼륨 삭제
docker compose down -v

# 볼륨 확인
docker volume ls | grep kp
```

---

## 빠른 진단 명령어

```bash
# 1. 전체 컨테이너 상태 확인
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# 2. 특정 컨테이너 로그 확인
docker logs kp-neo4j --tail 50

# 3. 컨테이너 헬스체크 상태
docker inspect --format='{{.State.Health.Status}}' kp-elasticsearch

# 4. 네트워크 연결 확인
docker network inspect kp-database --format='{{range .Containers}}{{.Name}} {{end}}'

# 5. 포트 바인딩 확인
docker port kp-neo4j
```

---

## 관련 파일

| 파일 | 설명 |
|------|------|
| `infrastructure/docker/docker-compose.yml` | 메인 Docker Compose 설정 |
| `infrastructure/docker/.env` | 환경 변수 설정 |
| `infrastructure/database/` | 데이터베이스 초기화 스크립트 |
| `knowledge_service/src/tests/e2e/infrastructure/` | E2E 인프라 테스트 |

---

## 변경 이력

| 날짜 | 버전 | 변경 내용 |
|------|------|----------|
| 2026-01-20 | 1.0 | 초기 문서 작성 (포트 매핑 문제 해결) |
