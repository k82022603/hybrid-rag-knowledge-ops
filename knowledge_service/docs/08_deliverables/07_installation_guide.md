# 설치 및 배포 가이드

**시스템**: Hybrid RAG Knowledge Platform
**버전**: 1.0
**작성일**: 2026-02-18

---

## 목차

1. [사전 요구사항](#1-사전-요구사항)
2. [소스코드 클론](#2-소스코드-클론)
3. [환경 설정](#3-환경-설정)
4. [Docker Compose 기동](#4-docker-compose-기동)
5. [초기 데이터 설정](#5-초기-데이터-설정)
6. [ETL 초기 실행](#6-etl-초기-실행)
7. [기동 검증](#7-기동-검증)
8. [트러블슈팅](#8-트러블슈팅)

---

## 1. 사전 요구사항

### 1.1 소프트웨어

| 소프트웨어 | 최소 버전 | 확인 방법 | 비고 |
|-----------|----------|----------|------|
| **Docker** | 24.0+ | `docker --version` | Docker Desktop 권장 |
| **Docker Compose** | v2.20+ | `docker compose version` | Docker Desktop에 포함 |
| **Git** | 2.30+ | `git --version` | |
| **Python** | 3.11+ | `python3 --version` | ETL 스크립트 실행 시 |
| **WSL2** (Windows) | - | `wsl --status` | Windows에서 필수 |

### 1.2 하드웨어 최소 사양

| 항목 | 최소 | 권장 | 비고 |
|------|------|------|------|
| **RAM** | 16 GB | 32 GB | 18개 컨테이너 Memory Reservation 합계 ~15.5GB |
| **Disk** | 50 GB | 100 GB | Docker 이미지 + ES 데이터 + Neo4j 데이터 |
| **CPU** | 4 Core | 8 Core | CPU Limit 합계 ~19 코어 (실제 동시 사용은 적음) |
| **GPU** | 없음 | NVIDIA T4+ | Phase 2 임베딩은 Google Colab으로 대체 가능 |

### 1.3 WSL2 설정 (Windows)

Windows에서 Docker를 사용하려면 WSL2가 필요합니다.

```powershell
# 1. WSL2 설치 (PowerShell 관리자 모드)
wsl --install

# 2. WSL2 메모리 제한 설정 (필수)
# %USERPROFILE%/.wslconfig 파일 생성/수정
```

`.wslconfig` 내용:

```ini
[wsl2]
memory=16GB
swap=4GB
processors=8
```

> 메모리 16GB 미만에서는 관측(Observability) 서비스를 끄고 핵심 서비스만 기동하는 것을 권장합니다.

### 1.4 네트워크 요구사항

| 대상 | 용도 | 비고 |
|------|------|------|
| Docker Hub | 공식 이미지 Pull | 초기 기동 시 필요 |
| api.deepseek.com | DeepSeek LLM API | 검색/엔티티 추출 시 |
| huggingface.co | BGE-M3, BGE-Reranker 모델 | 최초 ai-service 기동 시 |

---

## 2. 소스코드 클론

```bash
# 프로젝트 클론
git clone https://github.com/<organization>/hybrid-rag-knowledge-ops.git
cd hybrid-rag-knowledge-ops
```

**프로젝트 폴더 구조**:

```
hybrid-rag-knowledge-ops/
├── knowledge_service/          # Python AI Service (핵심)
│   ├── src/app/                # 소스코드
│   ├── scripts/                # ETL/배치 스크립트
│   ├── docs/                   # 프로젝트 문서
│   └── frontend/               # React 18 프론트엔드
├── infrastructure/docker/      # Docker Compose + Nginx
│   ├── docker-compose.yml      # 메인 Compose 파일
│   ├── docker-compose.wsl2.yml # WSL2 오버라이드
│   ├── .env                    # 환경변수
│   └── nginx/                  # Nginx 설정
├── scripts/                    # 공통 유틸 스크립트
├── CLAUDE.md                   # Claude Code 규칙
├── PLAN.md                     # 프로젝트 계획
└── README.md                   # 프로젝트 소개
```

---

## 3. 환경 설정

### 3.1 .env 파일 설정

```bash
cd infrastructure/docker

# 템플릿에서 복사 (템플릿이 없는 경우 직접 생성)
cp .env.example .env
```

`.env` 파일에서 반드시 확인/수정해야 할 항목:

| 변수 | 설명 | 기본값 | 수정 필요 여부 |
|------|------|--------|:------------:|
| `DEEPSEEK_API_KEY` | DeepSeek LLM API 키 | `sk-7c3024...` | 본인 키로 교체 |
| `DB_PASSWORD` | PostgreSQL 비밀번호 | `knowledge_dev_2026!` | 프로덕션 시 변경 |
| `NEO4J_PASSWORD` | Neo4j 비밀번호 | `neo4j_dev_2026!` | 프로덕션 시 변경 |
| `KEYCLOAK_ADMIN_PASSWORD` | Keycloak 관리자 비밀번호 | `keycloak_admin_2026!` | 프로덕션 시 변경 |
| `JWT_SECRET` | JWT 서명 키 | `dev_jwt_secret_key...` | 프로덕션 시 교체 필수 |
| `GRAFANA_ADMIN_PASSWORD` | Grafana 관리자 비밀번호 | `test1234` | 프로덕션 시 변경 |

**DeepSeek API 키 발급**:
1. https://platform.deepseek.com 접속
2. 계정 생성 및 로그인
3. API Keys 메뉴에서 키 생성
4. `.env` 파일의 `DEEPSEEK_API_KEY`에 입력

### 3.2 포트 충돌 확인

기본 포트가 다른 서비스와 충돌하는 경우 `.env` 파일에서 변경할 수 있습니다.

```bash
# 사용 중인 포트 확인 (Linux/WSL2)
ss -tlnp | grep -E ":(80|443|8000|8080|8081|8180|9200|5601|7474|6379|9090|3001|16686) "
```

| 포트 | 서비스 | .env 변수 |
|------|--------|----------|
| 80 | nginx | `NGINX_HTTP_PORT` |
| 8080 | api-gateway | `GATEWAY_PORT` |
| 8180 | keycloak | `KEYCLOAK_PORT` |
| 9200 | elasticsearch | `ELASTICSEARCH_PORT` |
| 5601 | kibana | `KIBANA_PORT` |
| 3001 | grafana | `GRAFANA_PORT` |

### 3.3 Docker 이미지 사전 Pull (선택)

기동 시간을 단축하려면 이미지를 미리 다운로드합니다.

```bash
cd infrastructure/docker
docker compose pull
```

---

## 4. Docker Compose 기동

### 4.1 전체 기동

```bash
cd infrastructure/docker

# 전체 서비스 기동 (백그라운드)
docker compose up -d
```

첫 실행 시 Docker 이미지 빌드와 Pull이 진행되어 10~20분 소요될 수 있습니다.

### 4.2 기동 확인

```bash
# 방법 1: 자동 점검 스크립트 (권장)
bash scripts/startup_check.sh --skip-compose

# 방법 2: 수동 확인
docker compose ps
```

**기대 결과**: 18개 컨테이너 전부 `Up` 상태, 대부분 `(healthy)` 표시

```
NAMES              STATUS
kp-ai-service      Up 5 minutes (healthy)
kp-frontend        Up 5 minutes (healthy)
kp-backend         Up 5 minutes (healthy)
kp-nginx           Up 5 minutes (healthy)
kp-api-gateway     Up 5 minutes (healthy)
kp-postgresql      Up 5 minutes (healthy)
kp-elasticsearch   Up 5 minutes (healthy)
kp-neo4j           Up 5 minutes (healthy)
kp-redis           Up 5 minutes (healthy)
kp-keycloak        Up 5 minutes (healthy)
kp-keycloak-db     Up 5 minutes (healthy)
kp-minio           Up 5 minutes (healthy)
kp-grafana         Up 5 minutes (healthy)
kp-kibana          Up 5 minutes (healthy)
kp-prometheus      Up 5 minutes (healthy)
kp-loki            Up 5 minutes (healthy)
kp-jaeger          Up 5 minutes (healthy)
kp-promtail        Up 5 minutes
```

> `kp-promtail`은 healthcheck가 없으므로 `(healthy)` 표시가 나지 않습니다. 정상입니다.

### 4.3 WSL2 오버라이드 (자동 적용)

`startup_check.sh`는 WSL2 환경을 자동 감지하여 `docker-compose.wsl2.yml` 오버라이드를 적용합니다. 수동으로 적용하려면:

```bash
docker compose -f docker-compose.yml -f docker-compose.wsl2.yml up -d
```

### 4.4 메모리 부족 시 선택적 기동

16GB 미만 환경에서는 핵심 서비스만 기동합니다.

```bash
# 핵심만 (검색 기능 + UI)
docker compose up -d postgresql neo4j elasticsearch redis \
    keycloak keycloak-db ai-service backend frontend api-gateway nginx minio
```

---

## 5. 초기 데이터 설정

### 5.1 DB 스키마 생성

Docker Compose 기동 시 `init-db` 서비스가 자동으로 스키마를 생성합니다. 수동으로 실행하려면:

```bash
# init 프로파일로 초기화 (최초 1회)
cd infrastructure/docker
docker compose --profile init up init-db

# 또는 Python 스크립트 직접 실행
cd knowledge_service
python src/scripts/init_databases.py
```

**생성되는 리소스**:
- PostgreSQL: `documents`, `users`, `sessions` 등 테이블
- Elasticsearch: `knowledge_chunks` 인덱스 (Nori 한국어 분석기 매핑)
- Neo4j: 제약조건 및 인덱스

### 5.2 ES 인덱스 매핑 확인

```bash
# 인덱스 존재 확인
curl -s "http://localhost:9200/_cat/indices?v&s=index" | grep knowledge

# 매핑 확인 (text 필드에 korean_analyzer 적용 여부)
curl -s "http://localhost:9200/knowledge_chunks/_mapping" | python3 -m json.tool | head -30

# Nori 분석기 동작 확인
curl -s -X POST "http://localhost:9200/knowledge_chunks/_analyze" \
  -H "Content-Type: application/json" \
  -d '{"field":"text","text":"프로젝트관리시스템구축"}' | python3 -m json.tool
# 기대: 4토큰 (프로젝트, 관리, 시스템, 구축)
```

> `knowledge_chunks` 인덱스는 Custom Elasticsearch 이미지에 포함된 `analysis-nori` 플러그인을 사용합니다. Nori 플러그인이 미설치된 상태에서는 한국어 형태소 분석이 작동하지 않습니다.

### 5.3 기본 사용자 계정

시스템 기동 시 자동 생성되는 계정:

| 서비스 | ID | Password | 용도 |
|--------|-----|----------|------|
| AI Service | admin@example.com | admin123! | 관리자 로그인 |
| Keycloak SSO | admin | admin123 | SSO 테스트 |
| Keycloak SSO | test | password123 | 일반 사용자 테스트 |

---

## 6. ETL 초기 실행

시스템에 검색할 문서를 넣으려면 3-Phase ETL 파이프라인을 실행해야 합니다.

### 6.1 문서 업로드

MinIO Console(http://localhost:9001)에 접속하여 `documents` 버킷에 문서를 업로드합니다.

- **지원 형식**: PDF, DOCX, HWP, MD, TXT, HTML
- **문서 파싱 엔진**: Docling 2.x

또는 지정된 디렉토리에 문서 파일을 배치합니다.

### 6.2 3-Phase ETL 실행

**Phase 1: 파싱 + 청킹 (CPU, ~6시간)**

```bash
# ai-service 컨테이너에서 실행
docker exec kp-ai-service bash -c \
  "nohup python3 /app/scripts/run_etl_phase1_chunks.py > /tmp/etl_phase1.log 2>&1 &"

# 진행 확인
docker exec kp-ai-service tail -f /tmp/etl_phase1.log
```

**Phase 2: GPU 임베딩 (Colab T4, ~14분)**

GPU가 없는 환경에서는 Google Colab 무료 T4 GPU를 활용합니다.

```bash
# 1. ES에서 pending 청크 추출
python3 knowledge_service/scripts/export_chunks_for_gpu.py

# 2. Google Colab에서 BGE-M3 임베딩 실행 (별도 노트북)

# 3. 임베딩 결과 ES에 임포트
python3 knowledge_service/scripts/import_embeddings.py
```

**Phase 3: 엔티티 추출 (CPU + DeepSeek API, ~43시간)**

```bash
docker exec kp-ai-service bash -c \
  "nohup python3 /app/scripts/run_etl_phase3_entities.py > /tmp/etl_phase3.log 2>&1 &"
```

> Phase 3은 DeepSeek API를 호출하므로 비용이 발생합니다 (약 $52/23,074건).

### 6.3 ETL 완료 확인

```bash
# ES 청크 수
curl -s "http://localhost:9200/knowledge_chunks/_count" | python3 -m json.tool

# PostgreSQL 문서 수
docker exec kp-postgresql psql -U knowledge -d knowledge \
  -c "SELECT count(*) FROM documents WHERE processing_status='completed';"

# Neo4j 노드/관계 수
docker exec kp-neo4j cypher-shell -u neo4j -p 'neo4j_dev_2026!' \
  "MATCH (n) RETURN labels(n) AS label, count(n) AS cnt ORDER BY cnt DESC;"
```

---

## 7. 기동 검증

### 7.1 자동 점검 (startup_check.sh)

가장 확실한 검증 방법입니다.

```bash
bash scripts/startup_check.sh --skip-compose --verbose
```

이 스크립트는 다음을 자동으로 검증합니다:
- 인프라 서비스 4종 (ES, PG, Neo4j, Redis) 헬스체크
- ai-service 헬스체크 및 의존성 연결 확인
- JWT 로그인 -> Keyword/Hybrid/Semantic 3종 검색 테스트
- Nori 한국어 분석기 동작 확인
- 전체 컨테이너 상태 리포트

### 7.2 수동 Health Check

```bash
# ai-service 종합 상태
curl -s http://localhost:8000/api/v1/health | python3 -m json.tool

# 기대 응답:
# {
#   "status": "healthy",
#   "dependencies": {
#     "elasticsearch": {"status": "connected"},
#     "neo4j": {"status": "connected"},
#     "postgresql": {"status": "connected"},
#     "deepseek": {"status": "connected"}
#   }
# }
```

### 7.3 검색 테스트

```bash
# 1. JWT 로그인 (임시 파일 방식 - bash ! 이스케이프 방지)
cat > /tmp/login.json << 'ENDJSON'
{"email":"admin@example.com","password":"admin123!"}
ENDJSON

TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d @/tmp/login.json | python3 -c "import sys,json; print(json.load(sys.stdin).get('accessToken',''))")
rm -f /tmp/login.json

# 2. Hybrid 검색 테스트
curl -s -X POST http://localhost:8000/api/v1/search/hybrid \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query":"프로젝트 관리","top_k":5}' | python3 -m json.tool | head -20
```

---

## 8. 트러블슈팅

### 8.1 Docker Compose 기동 실패

| 증상 | 원인 | 해결 |
|------|------|------|
| `port is already allocated` | 포트 충돌 | `.env`에서 포트 변경 또는 충돌 프로세스 종료 |
| `image not found` | 이미지 빌드 실패 | `docker compose build --no-cache <서비스>` |
| `network not found` | 네트워크 누락 | `docker compose down && docker network prune -f && docker compose up -d` |

### 8.2 ai-service 기동 실패

| 증상 | 원인 | 해결 |
|------|------|------|
| Exit Code 137 | 메모리 부족 (OOM) | WSL2 메모리 증가 또는 불필요 서비스 중지 |
| Exit Code 127 | 명령어 미존재 | Dockerfile 확인, `docker compose build --no-cache ai-service` |
| `ModuleNotFoundError` | Python 패키지 누락 | `docker compose build --no-cache ai-service` |
| 모델 로드 실패 | HuggingFace 캐시 문제 | 컨테이너 재시작 후 모델 재다운로드 대기 (2-3분) |

### 8.3 ES 인덱스 생성 실패

```bash
# 인덱스 수동 생성 (init-db가 실패한 경우)
docker exec kp-ai-service python3 -c "
from app.services.es_storage import ElasticsearchStorage
es = ElasticsearchStorage()
es.create_index()
print('Index created successfully')
"
```

### 8.4 검색 결과 0건

```bash
# 1. ES에 데이터가 있는지 확인
curl -s "http://localhost:9200/knowledge_chunks/_count"

# 2. 데이터 있으면 캐시 문제 -> Redis 플러시
docker exec kp-redis redis-cli FLUSHALL

# 3. ai-service의 ES 연결 확인
curl -s http://localhost:8000/api/v1/health | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(json.dumps(d.get('dependencies',{}),indent=2))
"

# 4. ai-service 재시작
docker compose restart ai-service
```

### 8.5 Nori 분석기 미동작

```bash
# 확인: text 필드의 analyzer가 korean_analyzer인지
curl -s "http://localhost:9200/knowledge_chunks/_mapping" | \
  python3 -c "import sys,json; m=json.load(sys.stdin); print(json.dumps(m,indent=2))" | \
  grep -A3 '"text"'

# analyzer가 standard이면 Reindex 필요:
# 1. 올바른 매핑으로 새 인덱스 생성
# 2. _reindex API로 데이터 복사
# 3. alias 스왑
# 상세: docs/04_testing/15_user_test_2026-02-18/00_pre_check_report.md
```

### 8.6 Windows/WSL2 관련 문제

| 증상 | 해결 |
|------|------|
| Docker Desktop 미시작 | Docker Desktop 실행 -> Settings -> WSL2 기반 엔진 활성화 |
| 볼륨 마운트 실패 | WSL2 경로 형식 확인 (`/mnt/c/...`) |
| 네트워크 느림 | `.wslconfig`에서 `networkingMode=mirrored` 설정 |
| 디스크 부족 | `docker system prune -f`, WSL2 vdisk 축소 (diskpart compact) |

### 8.7 전체 초기화 (최후의 수단)

모든 데이터를 삭제하고 처음부터 시작합니다.

```bash
cd infrastructure/docker

# 전체 종료 + 볼륨 삭제 + 네트워크 삭제
docker compose down -v
docker network prune -f
docker builder prune -f

# 재기동
docker compose up -d

# DB 초기화
docker compose --profile init up init-db
```

> 이 작업은 PostgreSQL, Elasticsearch, Neo4j의 모든 데이터를 삭제합니다. ETL 파이프라인을 처음부터 다시 실행해야 합니다.

---

*작성: Claude Code (Opus 4.6) | 2026-02-18*
