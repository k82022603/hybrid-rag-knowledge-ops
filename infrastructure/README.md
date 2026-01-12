# Infrastructure Configuration

데이터베이스 및 Docker 인프라 설정 파일 모음

## 📁 폴더 구조

```
infrastructure/
├── docker/                       # Docker 관련 설정
│   ├── docker-compose.yml        # 컨테이너 오케스트레이션
│   ├── Dockerfile.postgres
│   ├── Dockerfile.neo4j
│   ├── Dockerfile.elasticsearch
│   └── nginx.conf
├── database/                     # DB 초기화 스크립트
│   ├── postgres/
│   │   ├── schema.sql            # 테이블 스키마
│   │   ├── init.sql              # 초기 데이터
│   │   └── migrations/           # 마이그레이션
│   ├── neo4j/
│   │   ├── schema.cypher
│   │   └── constraints.cypher
│   └── elasticsearch/
│       ├── mappings.json
│       └── settings.json
├── .env.example                  # 환경 변수 템플릿
└── README.md
```

## 🐳 Docker 사용

### 컨테이너 시작

```bash
cd infrastructure/docker
docker-compose up -d
```

### 상태 확인

```bash
docker-compose ps
docker-compose logs -f elasticsearch
```

### 컨테이너 중지

```bash
docker-compose down
```

## 🗄️ 데이터베이스 초기화

### PostgreSQL

```bash
docker exec -i postgres psql -U admin -d knowledge < database/postgres/schema.sql
```

### Neo4j

```bash
docker exec -i neo4j cypher-shell -u neo4j -p password < database/neo4j/schema.cypher
```

### Elasticsearch

```bash
curl -X PUT "localhost:9200/pdf-documents" -H 'Content-Type: application/json' \
  -d @database/elasticsearch/mappings.json
```

## 📋 메모리 할당

16GB RAM 최적화 설정:
- PostgreSQL: 1GB
- Neo4j: 2GB
- Elasticsearch: 4GB (JVM Heap)

자세한 내용은 `.env.example` 참고

## ⚠️ 주의사항

- storage 폴더는 git 추적 제외
- .env 파일은 로컬에서만 생성
- 프로덕션 환경에서는 보안 설정 변경 필수
