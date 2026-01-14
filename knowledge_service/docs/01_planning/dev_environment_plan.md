# 개발 환경 구축 계획서
## Hybrid RAG Knowledge Platform - Development Environment Setup

---

## 문서 정보

| 항목 | 내용 |
|------|------|
| **문서명** | 개발 환경 구축 계획서 |
| **버전** | 1.0 |
| **작성일** | 2026-01-14 |
| **작성자** | Claude Code (Opus 4.5) |
| **상태** | 초안 |
| **참조 문서** | [상세 설계서](../02_design/hybrid_rag_platform_detailed_design.md), [DevOps 계획서](./devops_alm_plan.md) |

---

## 변경 이력

| 버전 | 일자 | 작성자 | 변경 내용 |
|------|------|--------|----------|
| 1.0 | 2026-01-14 | Claude Code | 초안 작성 |

---

## 목차

1. [개요](#1-개요)
2. [개발 환경 요구사항](#2-개발-환경-요구사항)
3. [로컬 개발 환경](#3-로컬-개발-환경)
4. [Docker 기반 환경](#4-docker-기반-환경)
5. [IDE 설정](#5-ide-설정)
6. [데이터베이스 초기화](#6-데이터베이스-초기화)
7. [환경 변수 관리](#7-환경-변수-관리)
8. [개발 도구](#8-개발-도구)
9. [AI 개발 환경](#9-ai-개발-환경)
10. [문제 해결](#10-문제-해결)

---

## 1. 개요

### 1.1 목적

본 문서는 Hybrid RAG Knowledge Platform 개발을 위한 환경 구축 가이드를 제공합니다. 로컬 개발, Docker 기반 개발, 클라우드 환경까지 다양한 시나리오를 지원합니다.

### 1.2 환경 유형

| 환경 | 용도 | 특징 |
|------|------|------|
| **로컬 개발** | 개별 개발자 | IDE 직접 실행, 빠른 반복 |
| **Docker 개발** | 통합 개발 | 전체 스택 로컬 실행 |
| **Staging** | QA 테스트 | 프로덕션 유사 환경 |
| **Production** | 운영 | 고가용성, 보안 강화 |

### 1.3 환경 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Development Environment                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                     Developer Workstation                            │   │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │   │
│   │  │   IDE    │  │  Docker  │  │   Node   │  │  Python  │            │   │
│   │  │(IntelliJ)│  │ Desktop  │  │  20 LTS  │  │  3.11+   │            │   │
│   │  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │   │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │   │
│   │  │  JDK 21  │  │   Git    │  │  Claude  │  │ VS Code  │            │   │
│   │  │          │  │          │  │   Code   │  │          │            │   │
│   │  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                     │                                        │
│                                     ▼                                        │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                     Docker Environment                               │   │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │   │
│   │  │PostgreSQL│  │   Neo4j  │  │   ES     │  │  Redis   │            │   │
│   │  │   :5432  │  │   :7474  │  │  :9200   │  │  :6379   │            │   │
│   │  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 개발 환경 요구사항

### 2.1 하드웨어 요구사항

| 구성 요소 | 최소 | 권장 | 비고 |
|----------|------|------|------|
| **CPU** | 4 cores | 8+ cores | Intel/AMD x64 |
| **RAM** | 16GB | 32GB | Docker 환경 필수 |
| **Storage** | 50GB SSD | 100GB+ NVMe | DB 데이터 포함 |
| **Network** | 100Mbps | 1Gbps | API 호출, 컨테이너 풀 |

### 2.2 소프트웨어 요구사항

| 소프트웨어 | 버전 | 용도 | 필수 |
|-----------|------|------|------|
| **OS** | Windows 11 / macOS 13+ / Ubuntu 22.04 | 운영체제 | Yes |
| **Docker Desktop** | 24.0+ | 컨테이너 런타임 | Yes |
| **Git** | 2.40+ | 소스 관리 | Yes |
| **JDK** | 21 (Temurin) | Java 백엔드 | Yes |
| **Node.js** | 20 LTS | 프론트엔드 | Yes |
| **Python** | 3.11+ | AI 서비스 | Yes |
| **Poetry** | 1.8+ | Python 패키지 관리 | Yes |
| **IntelliJ IDEA** | 2024.1+ | Java IDE | Recommended |
| **VS Code** | Latest | Python/Frontend IDE | Recommended |
| **Claude Code** | Latest | AI 개발 도우미 | Recommended |

### 2.3 네트워크 요구사항

**필요한 외부 접근:**

| 서비스 | URL | 용도 |
|--------|-----|------|
| GitHub | github.com | 소스 관리 |
| Docker Hub | hub.docker.com | 이미지 풀 |
| npm Registry | registry.npmjs.org | Node 패키지 |
| PyPI | pypi.org | Python 패키지 |
| Maven Central | repo.maven.apache.org | Java 패키지 |
| DeepSeek API | api.deepseek.com | LLM 호출 |
| Anthropic API | api.anthropic.com | Claude 호출 |

---

## 3. 로컬 개발 환경

### 3.1 필수 소프트웨어 설치

#### 3.1.1 Windows

**PowerShell (관리자):**

```powershell
# Chocolatey 설치 (패키지 관리자)
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))

# 필수 소프트웨어 설치
choco install git -y
choco install docker-desktop -y
choco install temurin21 -y
choco install nodejs-lts -y
choco install python311 -y
choco install vscode -y
choco install jetbrainstoolbox -y

# Poetry 설치
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -

# 환경 변수 새로고침
refreshenv
```

#### 3.1.2 macOS

```bash
# Homebrew 설치
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 필수 소프트웨어 설치
brew install git
brew install --cask docker
brew install openjdk@21
brew install node@20
brew install python@3.11
brew install poetry
brew install --cask visual-studio-code
brew install --cask intellij-idea

# Java 환경 변수 설정
echo 'export JAVA_HOME=$(/usr/libexec/java_home -v 21)' >> ~/.zshrc
source ~/.zshrc
```

#### 3.1.3 Ubuntu

```bash
# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# 필수 패키지
sudo apt install -y git curl wget build-essential

# Docker 설치
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# JDK 21 (Temurin)
wget -O- https://apt.adoptium.net/DEB-GPG-KEY-adoptium.asc | sudo tee /etc/apt/keyrings/adoptium.asc
echo "deb [signed-by=/etc/apt/keyrings/adoptium.asc] https://apt.adoptium.net $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/adoptium.list
sudo apt update
sudo apt install -y temurin-21-jdk

# Node.js 20 LTS
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Python 3.11
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt install -y python3.11 python3.11-venv python3.11-dev

# Poetry
curl -sSL https://install.python-poetry.org | python3.11 -

# 환경 변수
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### 3.2 프로젝트 클론 및 설정

```bash
# 프로젝트 클론
git clone https://github.com/your-org/hybrid-rag-knowledge-ops.git
cd hybrid-rag-knowledge-ops

# 브랜치 전략 설정
git config pull.rebase false
git config branch.autoSetupMerge always

# Git Hooks 설정 (Husky 사용 시)
npm install  # frontend 디렉토리에서
```

### 3.3 개별 서비스 실행

#### Frontend (React)

```bash
cd frontend

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev

# 빌드
npm run build

# 테스트
npm run test
```

#### Backend (Spring Boot)

```bash
cd backend

# Gradle Wrapper 권한
chmod +x gradlew

# 빌드
./gradlew build

# 실행
./gradlew bootRun

# 테스트
./gradlew test
```

#### AI Service (Python)

```bash
cd ai-service

# Poetry 환경 설정
poetry install

# 환경 활성화
poetry shell

# 실행
uvicorn app.main:app --reload --port 8000

# 테스트
pytest
```

---

## 4. Docker 기반 환경

### 4.1 Docker Compose 파일

**docker-compose.yml (개발용):**

```yaml
version: '3.8'

services:
  # ========================================
  # 데이터베이스
  # ========================================
  postgres:
    image: postgres:16-alpine
    container_name: hrkp-postgres
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: knowledge
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: secret
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U admin -d knowledge"]
      interval: 10s
      timeout: 5s
      retries: 5

  neo4j:
    image: neo4j:5.15-community
    container_name: hrkp-neo4j
    ports:
      - "7474:7474"  # HTTP
      - "7687:7687"  # Bolt
    environment:
      NEO4J_AUTH: neo4j/password
      NEO4J_PLUGINS: '["apoc"]'
      NEO4J_apoc_export_file_enabled: "true"
      NEO4J_apoc_import_file_enabled: "true"
      NEO4J_dbms_memory_heap_initial__size: 512m
      NEO4J_dbms_memory_heap_max__size: 1G
    volumes:
      - neo4j-data:/data
      - neo4j-logs:/logs
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:7474"]
      interval: 10s
      timeout: 5s
      retries: 5

  elasticsearch:
    image: elasticsearch:8.11.0
    container_name: hrkp-elasticsearch
    ports:
      - "9200:9200"
      - "9300:9300"
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms2g -Xmx2g"
    volumes:
      - es-data:/usr/share/elasticsearch/data
    healthcheck:
      test: ["CMD-SHELL", "curl -s http://localhost:9200 >/dev/null || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: hrkp-redis
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ========================================
  # 서비스 (옵션)
  # ========================================
  ai-service:
    build:
      context: ./ai-service
      dockerfile: Dockerfile.dev
    container_name: hrkp-ai-service
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_HOST=postgres
      - POSTGRES_PORT=5432
      - ELASTICSEARCH_URL=http://elasticsearch:9200
      - NEO4J_URI=bolt://neo4j:7687
      - REDIS_URL=redis://redis:6379
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
    volumes:
      - ./ai-service:/app
    depends_on:
      postgres:
        condition: service_healthy
      elasticsearch:
        condition: service_healthy
      neo4j:
        condition: service_healthy
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

volumes:
  postgres-data:
  neo4j-data:
  neo4j-logs:
  es-data:
  redis-data:

networks:
  default:
    name: hrkp-network
```

### 4.2 Docker Compose 명령어

```bash
# 전체 환경 시작
docker-compose up -d

# 특정 서비스만 시작
docker-compose up -d postgres neo4j elasticsearch

# 로그 확인
docker-compose logs -f
docker-compose logs -f elasticsearch

# 상태 확인
docker-compose ps

# 환경 종료
docker-compose down

# 볼륨 포함 삭제 (주의: 데이터 삭제됨)
docker-compose down -v

# 재빌드
docker-compose up -d --build ai-service
```

### 4.3 개발용 Dockerfile

**ai-service/Dockerfile.dev:**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Poetry 설치
RUN curl -sSL https://install.python-poetry.org | python3 -

ENV PATH="/root/.local/bin:$PATH"

# 의존성 설치
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# 소스 코드 (볼륨 마운트됨)
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

### 4.4 서비스 접속 정보

| 서비스 | URL | 인증 |
|--------|-----|------|
| PostgreSQL | `localhost:5432` | admin / secret |
| Neo4j Browser | http://localhost:7474 | neo4j / password |
| Neo4j Bolt | `bolt://localhost:7687` | neo4j / password |
| Elasticsearch | http://localhost:9200 | - |
| Redis | `localhost:6379` | - |
| AI Service | http://localhost:8000 | - |
| AI Service Docs | http://localhost:8000/docs | - |

---

## 5. IDE 설정

### 5.1 IntelliJ IDEA (Backend)

#### 5.1.1 프로젝트 열기

1. File → Open → `backend/` 디렉토리 선택
2. "Import as Gradle Project" 선택
3. JDK 21 선택

#### 5.1.2 권장 플러그인

| 플러그인 | 용도 |
|---------|------|
| Spring Boot Assistant | Spring 개발 지원 |
| Lombok | Lombok 어노테이션 |
| MapStruct Support | DTO 매핑 |
| CheckStyle-IDEA | 코드 스타일 검사 |
| SonarLint | 코드 품질 |
| Docker | Docker 연동 |
| Database Tools | DB 연동 |

#### 5.1.3 Run Configuration

```
Main class: com.company.knowledge.KnowledgeServiceApplication
VM options: -Dspring.profiles.active=local
Environment variables:
  POSTGRES_HOST=localhost
  POSTGRES_PORT=5432
  ELASTICSEARCH_URL=http://localhost:9200
```

### 5.2 VS Code (Frontend & AI Service)

#### 5.2.1 권장 확장

**settings.json에 추가:**

```json
{
  "recommendations": [
    "dbaeumer.vscode-eslint",
    "esbenp.prettier-vscode",
    "bradlc.vscode-tailwindcss",
    "ms-python.python",
    "ms-python.vscode-pylance",
    "ms-python.black-formatter",
    "charliermarsh.ruff",
    "ms-azuretools.vscode-docker",
    "eamodio.gitlens",
    "usernamehw.errorlens",
    "yoavbls.pretty-ts-errors"
  ]
}
```

#### 5.2.2 Workspace 설정

**.vscode/settings.json:**

```json
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",

  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": "explicit"
    }
  },

  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },

  "[typescriptreact]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },

  "python.analysis.typeCheckingMode": "basic",
  "python.testing.pytestEnabled": true,

  "typescript.preferences.importModuleSpecifier": "relative",
  "typescript.updateImportsOnFileMove.enabled": "always",

  "files.exclude": {
    "**/__pycache__": true,
    "**/.pytest_cache": true,
    "**/node_modules": true,
    "**/dist": true
  }
}
```

### 5.3 Claude Code 설정

#### 5.3.1 설치

```bash
# npm 전역 설치
npm install -g @anthropic-ai/claude-code

# 또는 npx로 실행
npx @anthropic-ai/claude-code
```

#### 5.3.2 프로젝트 설정

**.claude/settings.json:**

```json
{
  "project": {
    "name": "Hybrid RAG Knowledge Operations",
    "version": "2.6",
    "workspace_root": "./",
    "services": ["knowledge_service", "frontend", "backend"]
  },
  "claude_code": {
    "model": "opus",
    "max_tokens": 4000,
    "temperature": 0.7,
    "default_language": "english"
  },
  "development": {
    "default_branch": "main",
    "python_version": "3.11",
    "poetry_enabled": true,
    "docker_compose_path": "infrastructure/docker/docker-compose.yml"
  }
}
```

#### 5.3.3 MCP 연동

**.mcp.json:**

```json
{
  "mcpServers": {
    "postgres": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@bytebase/dbhub", "postgresql"],
      "env": {
        "DSN": "postgresql://admin:secret@localhost:5432/knowledge"
      }
    },
    "elasticsearch": {
      "type": "stdio",
      "command": "python",
      "args": [".claude/mcp/elasticsearch_server.py"],
      "env": {
        "ES_URL": "http://localhost:9200"
      }
    }
  }
}
```

---

## 6. 데이터베이스 초기화

### 6.1 PostgreSQL 초기화

**scripts/init-db.sql:**

```sql
-- 확장 기능 활성화
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- 테이블 생성
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50) UNIQUE NOT NULL,
    start_date DATE,
    end_date DATE,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS persons (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE,
    department VARCHAR(100),
    position VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    document_type VARCHAR(50) NOT NULL,
    project_id UUID REFERENCES projects(id),
    author_id UUID REFERENCES persons(id),
    valid_start_date DATE,
    valid_end_date DATE,
    file_path TEXT,
    file_size BIGINT,
    raw_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    token_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(document_id, chunk_index)
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_documents_project ON documents(project_id);
CREATE INDEX IF NOT EXISTS idx_documents_author ON documents(author_id);
CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(document_type);
CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);

-- 샘플 데이터
INSERT INTO projects (name, code, status) VALUES
    ('Hybrid RAG Platform', 'HRKP', 'active'),
    ('AI Service Development', 'AISD', 'active')
ON CONFLICT (code) DO NOTHING;

INSERT INTO persons (name, email, department, position) VALUES
    ('홍길동', 'hong@example.com', '개발팀', '시니어 개발자'),
    ('김개발', 'kim@example.com', '개발팀', '주니어 개발자')
ON CONFLICT (email) DO NOTHING;
```

### 6.2 Elasticsearch 초기화

**scripts/init-es.py:**

```python
import os
from elasticsearch import Elasticsearch

ES_URL = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
INDEX_NAME = "knowledge-chunks"

es = Elasticsearch([ES_URL])

# 인덱스 삭제 (개발용)
if es.indices.exists(index=INDEX_NAME):
    es.indices.delete(index=INDEX_NAME)

# 인덱스 생성
mapping = {
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
    },
    "mappings": {
        "properties": {
            "chunk_id": {"type": "keyword"},
            "document_id": {"type": "keyword"},
            "text": {
                "type": "text",
                "analyzer": "korean_analyzer"
            },
            "dense_vector": {
                "type": "dense_vector",
                "dims": 1024,
                "index": True,
                "similarity": "cosine"
            },
            "sparse_vector": {"type": "sparse_vector"},
            "metadata": {
                "properties": {
                    "document_type": {"type": "keyword"},
                    "project_name": {"type": "keyword"},
                    "valid_start_date": {"type": "date"},
                    "valid_end_date": {"type": "date"},
                    "author": {"type": "keyword"}
                }
            }
        }
    }
}

es.indices.create(index=INDEX_NAME, body=mapping)
print(f"Index '{INDEX_NAME}' created successfully")
```

### 6.3 Neo4j 초기화

**scripts/init-neo4j.cypher:**

```cypher
// 제약조건 생성
CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
FOR (e:Entity) REQUIRE e.id IS UNIQUE;

CREATE CONSTRAINT textunit_id_unique IF NOT EXISTS
FOR (t:TextUnit) REQUIRE t.id IS UNIQUE;

CREATE CONSTRAINT community_id_unique IF NOT EXISTS
FOR (c:Community) REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT document_id_unique IF NOT EXISTS
FOR (d:Document) REQUIRE d.id IS UNIQUE;

// 인덱스 생성
CREATE INDEX entity_type_idx IF NOT EXISTS
FOR (e:Entity) ON (e.type);

CREATE INDEX entity_name_idx IF NOT EXISTS
FOR (e:Entity) ON (e.name);

CREATE FULLTEXT INDEX entity_fulltext_idx IF NOT EXISTS
FOR (e:Entity) ON EACH [e.name, e.description];

// 샘플 데이터
CREATE (e1:Entity {id: 'sample_001', name: 'React', type: 'Technology', description: 'JavaScript UI Library'});
CREATE (e2:Entity {id: 'sample_002', name: 'Spring Boot', type: 'Technology', description: 'Java Web Framework'});
MATCH (e1:Entity {id: 'sample_001'}), (e2:Entity {id: 'sample_002'})
CREATE (e1)-[:RELATED_TO {type: 'INTEGRATES_WITH'}]->(e2);
```

### 6.4 초기화 스크립트 실행

**scripts/init_all.sh:**

```bash
#!/bin/bash

echo "=== Database Initialization ==="

# PostgreSQL
echo "Initializing PostgreSQL..."
docker exec -i hrkp-postgres psql -U admin -d knowledge < scripts/init-db.sql

# Elasticsearch
echo "Initializing Elasticsearch..."
python scripts/init-es.py

# Neo4j
echo "Initializing Neo4j..."
docker exec -i hrkp-neo4j cypher-shell -u neo4j -p password < scripts/init-neo4j.cypher

echo "=== Initialization Complete ==="
```

**PowerShell 버전 (scripts/init_all.ps1):**

```powershell
Write-Host "=== Database Initialization ==="

# PostgreSQL
Write-Host "Initializing PostgreSQL..."
Get-Content scripts/init-db.sql | docker exec -i hrkp-postgres psql -U admin -d knowledge

# Elasticsearch
Write-Host "Initializing Elasticsearch..."
python scripts/init-es.py

# Neo4j
Write-Host "Initializing Neo4j..."
Get-Content scripts/init-neo4j.cypher | docker exec -i hrkp-neo4j cypher-shell -u neo4j -p password

Write-Host "=== Initialization Complete ==="
```

---

## 7. 환경 변수 관리

### 7.1 환경 변수 파일 구조

```
project/
├── .env.example           # 템플릿 (Git 추적)
├── .env                   # 로컬 설정 (Git 제외)
├── .env.local             # 로컬 오버라이드 (Git 제외)
├── .env.development       # 개발 환경
├── .env.staging           # 스테이징 환경
└── .env.production        # 프로덕션 환경 (Git 제외)
```

### 7.2 환경 변수 템플릿

**.env.example:**

```bash
# ==============================================
# Database Configuration
# ==============================================
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=knowledge
POSTGRES_USER=admin
POSTGRES_PASSWORD=secret

NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

ELASTICSEARCH_URL=http://localhost:9200

REDIS_URL=redis://localhost:6379

# ==============================================
# AI Service Configuration
# ==============================================
DEEPSEEK_API_KEY=sk-your-deepseek-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key

# ==============================================
# Application Configuration
# ==============================================
APP_ENV=development
APP_DEBUG=true
LOG_LEVEL=DEBUG

# Frontend
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws

# Backend
SPRING_PROFILES_ACTIVE=local
SERVER_PORT=8080

# ==============================================
# Authentication (OAuth)
# ==============================================
OAUTH_CLIENT_ID=knowledge-app
OAUTH_CLIENT_SECRET=secret
OAUTH_ISSUER_URI=http://localhost:8180/realms/company

# JWT
JWT_SECRET=your-super-secret-jwt-key-min-256-bits
JWT_EXPIRATION=3600

# ==============================================
# External Services
# ==============================================
SENTRY_DSN=
SLACK_WEBHOOK_URL=
```

### 7.3 환경별 설정

**.env.development:**

```bash
APP_ENV=development
APP_DEBUG=true
LOG_LEVEL=DEBUG

# 로컬 DB
POSTGRES_HOST=localhost
ELASTICSEARCH_URL=http://localhost:9200

# 개발용 API
VITE_API_BASE_URL=http://localhost:8000
```

**.env.staging:**

```bash
APP_ENV=staging
APP_DEBUG=false
LOG_LEVEL=INFO

# 스테이징 DB
POSTGRES_HOST=staging-db.internal
ELASTICSEARCH_URL=http://staging-es.internal:9200

# 스테이징 API
VITE_API_BASE_URL=https://staging-api.example.com
```

### 7.4 dotenv 로딩

**Python (ai-service/app/config.py):**

```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Database
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "knowledge"
    postgres_user: str = "admin"
    postgres_password: str = "secret"

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"

    elasticsearch_url: str = "http://localhost:9200"
    redis_url: str = "redis://localhost:6379"

    # AI
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"

    # App
    app_env: str = "development"
    app_debug: bool = True
    log_level: str = "DEBUG"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
```

**Spring Boot (application.yml):**

```yaml
spring:
  config:
    import: optional:file:.env[.properties]

  datasource:
    url: jdbc:postgresql://${POSTGRES_HOST:localhost}:${POSTGRES_PORT:5432}/${POSTGRES_DB:knowledge}
    username: ${POSTGRES_USER:admin}
    password: ${POSTGRES_PASSWORD:secret}

  data:
    elasticsearch:
      client:
        reactive:
          endpoints: ${ELASTICSEARCH_URL:http://localhost:9200}

    neo4j:
      uri: ${NEO4J_URI:bolt://localhost:7687}
      authentication:
        username: ${NEO4J_USER:neo4j}
        password: ${NEO4J_PASSWORD:password}
```

---

## 8. 개발 도구

### 8.1 코드 품질 도구

#### 8.1.1 Linting

**Python (ruff):**

```toml
# pyproject.toml
[tool.ruff]
target-version = "py311"
line-length = 100
select = ["E", "F", "W", "I", "N", "UP", "B", "A"]
ignore = ["E501"]

[tool.ruff.isort]
known-first-party = ["app"]
```

**TypeScript (ESLint):**

```json
// frontend/.eslintrc.cjs
module.exports = {
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:react/recommended',
    'plugin:react-hooks/recommended',
    'prettier'
  ],
  rules: {
    'react/react-in-jsx-scope': 'off',
    '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }]
  }
};
```

#### 8.1.2 Formatting

**Python (Black):**

```toml
# pyproject.toml
[tool.black]
line-length = 100
target-version = ['py311']
include = '\.pyi?$'
exclude = '''
/(
    \.git
  | \.venv
  | __pycache__
)/
'''
```

**TypeScript (Prettier):**

```json
// frontend/.prettierrc
{
  "semi": true,
  "singleQuote": true,
  "tabWidth": 2,
  "trailingComma": "es5",
  "printWidth": 100
}
```

### 8.2 Git Hooks (Husky + lint-staged)

**package.json:**

```json
{
  "scripts": {
    "prepare": "husky install"
  },
  "lint-staged": {
    "*.{ts,tsx}": ["eslint --fix", "prettier --write"],
    "*.{json,md}": ["prettier --write"]
  }
}
```

**.husky/pre-commit:**

```bash
#!/bin/sh
. "$(dirname "$0")/_/husky.sh"

# Frontend
cd frontend && npm run lint-staged

# AI Service
cd ../ai-service && poetry run ruff check . && poetry run black --check .
```

### 8.3 데이터베이스 도구

| 도구 | 용도 | 설치 |
|------|------|------|
| **pgAdmin** | PostgreSQL GUI | brew install --cask pgadmin4 |
| **Neo4j Desktop** | Neo4j GUI | brew install --cask neo4j |
| **Elasticvue** | Elasticsearch GUI | Chrome Extension |
| **RedisInsight** | Redis GUI | brew install --cask redisinsight |
| **DBeaver** | Universal DB Client | brew install --cask dbeaver-community |

### 8.4 API 테스트 도구

| 도구 | 용도 | 파일 |
|------|------|------|
| **Postman** | API 테스트 | `docs/postman/` |
| **HTTPie** | CLI API 테스트 | - |
| **Swagger UI** | API 문서 | http://localhost:8000/docs |
| **curl** | 빠른 테스트 | - |

**HTTPie 예시:**

```bash
# 헬스체크
http GET localhost:8000/api/health

# 검색 API
http POST localhost:8000/api/v1/search query="React 아키텍처"

# 인증 포함
http GET localhost:8080/api/v1/knowledge Authorization:"Bearer $TOKEN"
```

---

## 9. AI 개발 환경

### 9.1 BGE-M3 임베딩 모델 설정

```python
# ai-service/app/core/embedding.py
from FlagEmbedding import BGEM3FlagModel
import os

class EmbeddingModel:
    def __init__(self):
        self.model = None

    async def load(self):
        """모델 로드 (시작 시 한 번)"""
        self.model = BGEM3FlagModel(
            'BAAI/bge-m3',
            use_fp16=True  # 메모리 절약
        )

    def embed(self, text: str) -> dict:
        """텍스트 임베딩 생성"""
        output = self.model.encode(
            [text],
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=False
        )
        return {
            "dense": output['dense_vecs'][0].tolist(),
            "sparse": self._sparse_to_dict(output['lexical_weights'][0])
        }

    def _sparse_to_dict(self, sparse_vec) -> dict:
        """Sparse 벡터를 딕셔너리로 변환"""
        return {
            str(idx): float(weight)
            for idx, weight in sparse_vec.items()
        }
```

### 9.2 DeepSeek 클라이언트 설정

```python
# ai-service/app/core/llm_client.py
import os
from langchain_openai import ChatOpenAI

def get_deepseek_chat():
    """DeepSeek Chat 클라이언트 (Non-thinking)"""
    return ChatOpenAI(
        model="deepseek-chat",
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        temperature=0
    )

def get_deepseek_reasoner():
    """DeepSeek Reasoner 클라이언트 (Thinking)"""
    return ChatOpenAI(
        model="deepseek-reasoner",
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        temperature=1  # Thinking 모드 필수
    )
```

### 9.3 Jupyter 노트북 환경

```bash
# Jupyter 설치
poetry add jupyter jupyterlab

# Jupyter 실행
poetry run jupyter lab --port 8888
```

**노트북 구조:**

```
notebooks/
├── 01_data_exploration.ipynb      # 데이터 탐색
├── 02_embedding_test.ipynb        # 임베딩 테스트
├── 03_search_evaluation.ipynb     # 검색 평가
├── 04_llm_prompts.ipynb           # 프롬프트 개발
└── 05_graph_analysis.ipynb        # 그래프 분석
```

---

## 10. 문제 해결

### 10.1 일반적인 문제

#### Docker 관련

| 문제 | 해결 방법 |
|------|----------|
| 포트 충돌 | `lsof -i :5432` 후 프로세스 종료 |
| 볼륨 권한 | `sudo chown -R $USER:$USER ./data` |
| 메모리 부족 | Docker Desktop에서 메모리 할당 증가 |
| 네트워크 오류 | `docker network prune` |

#### Python 관련

| 문제 | 해결 방법 |
|------|----------|
| Poetry 느림 | `poetry config virtualenvs.in-project true` |
| Import 오류 | `poetry install` 재실행 |
| 버전 충돌 | `poetry update` |

#### Node.js 관련

| 문제 | 해결 방법 |
|------|----------|
| node_modules 오류 | `rm -rf node_modules && npm install` |
| 캐시 문제 | `npm cache clean --force` |

### 10.2 DB 연결 문제

```bash
# PostgreSQL 연결 테스트
psql -h localhost -U admin -d knowledge

# Elasticsearch 상태 확인
curl http://localhost:9200/_cluster/health

# Neo4j 연결 테스트
cypher-shell -u neo4j -p password "RETURN 1"

# Redis 연결 테스트
redis-cli ping
```

### 10.3 로그 확인

```bash
# Docker 로그
docker logs hrkp-postgres
docker logs hrkp-elasticsearch

# 애플리케이션 로그
tail -f ai-service/logs/app.log
```

### 10.4 환경 리셋

```bash
# 전체 환경 리셋
docker-compose down -v
docker system prune -a
docker-compose up -d

# DB 초기화
./scripts/init_all.sh
```

---

## 부록

### A. 빠른 시작 가이드

```bash
# 1. 프로젝트 클론
git clone https://github.com/your-org/hybrid-rag-knowledge-ops.git
cd hybrid-rag-knowledge-ops

# 2. 환경 변수 설정
cp .env.example .env
# .env 파일 편집하여 API 키 설정

# 3. Docker 환경 시작
docker-compose up -d

# 4. 헬스체크
curl http://localhost:9200/_cluster/health
curl http://localhost:7474

# 5. DB 초기화
./scripts/init_all.sh

# 6. AI Service 시작
cd ai-service
poetry install
poetry run uvicorn app.main:app --reload

# 7. API 테스트
curl http://localhost:8000/api/health
```

### B. 참고 자료

- [Docker 공식 문서](https://docs.docker.com/)
- [Poetry 문서](https://python-poetry.org/docs/)
- [Spring Boot 문서](https://docs.spring.io/spring-boot/docs/current/reference/html/)
- [LangChain 문서](https://python.langchain.com/docs/)
- [Elasticsearch 문서](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)
- [Neo4j 문서](https://neo4j.com/docs/)

---

**문서 작성 완료: 2026-01-14**
