# UAT 종합 테스트 시나리오 - 2026-02-06

**Version**: 2.0.0
**Date**: 2026-02-06
**Environment**: Development (Docker Compose, 18 containers)
**Prepared By**: Claude (Opus 4.6)

---

## Table of Contents

1. [테스트 환경 사전 점검](#1-테스트-환경-사전-점검)
2. [테스트 계정 정보](#2-테스트-계정-정보)
3. [Part A: UI 기반 브라우저 테스트](#3-part-a-ui-기반-브라우저-테스트)
   - A-01: Keycloak SSO 로그인
   - A-02: 대시보드 확인
   - A-03: 문서 업로드 (단건/다건)
   - A-04: 문서 처리 상태 확인
   - A-05: 검색 (키워드/시맨틱)
   - A-06: 로그아웃 & 세션
4. [Part B: 대량 파일 청킹 + 임베딩 파이프라인 테스트](#4-part-b-대량-파일-청킹--임베딩-파이프라인-테스트)
   - B-01: 테스트 데이터 준비 (대량 파일)
   - B-02: 대량 업로드 + 자동 처리 트리거
   - B-03: 청킹 검증 (PostgreSQL)
   - B-04: 임베딩 검증 (Elasticsearch)
   - B-05: 터미널 Retriever 테스트 (Hybrid Search)
   - B-06: 성능 측정
5. [테스트 결과 기록 템플릿](#5-테스트-결과-기록-템플릿)
6. [이슈 리포팅 템플릿](#6-이슈-리포팅-템플릿)

---

## 1. 테스트 환경 사전 점검

### 1.1 서비스 Health Check

```bash
# 전체 컨테이너 상태 확인
docker ps --format "table {{.Names}}\t{{.Status}}" | grep "^kp-"

# 개별 서비스 확인
curl -s http://localhost:8080/actuator/health | python3 -m json.tool  # Gateway
curl -s http://localhost:8081/actuator/health | python3 -m json.tool  # Backend
curl -s http://localhost:8000/api/v1/health | python3 -m json.tool   # AI Service
curl -s http://localhost:9200/_cluster/health | python3 -m json.tool  # Elasticsearch
```

### 1.2 필수 서비스 상태

| 서비스 | URL | 기대 상태 | 확인 |
|--------|-----|-----------|------|
| Frontend (Nginx) | http://localhost | 200 OK | [ ] |
| API Gateway | http://localhost:8080/actuator/health | UP | [ ] |
| Backend | http://localhost:8081/actuator/health | UP | [ ] |
| AI Service | http://localhost:8000/api/v1/health | healthy | [ ] |
| Keycloak | http://localhost:8180 | 페이지 로드 | [ ] |
| Elasticsearch | http://localhost:9200/_cluster/health | green/yellow | [ ] |
| PostgreSQL | `docker exec kp-postgresql pg_isready` | accepting | [ ] |
| MinIO | http://localhost:9001 | 콘솔 페이지 | [ ] |
| Neo4j | http://localhost:7474 | 브라우저 로드 | [ ] |

### 1.3 초기 데이터 현황

```bash
# PostgreSQL 문서 수
docker exec kp-postgresql psql -U knowledge -d knowledge \
  -c "SELECT processing_status, count(*) FROM documents GROUP BY processing_status;"

# Elasticsearch 청크 수
curl -s "http://localhost:9200/knowledge_chunks/_count" | python3 -m json.tool

# PostgreSQL 청크 수
docker exec kp-postgresql psql -U knowledge -d knowledge \
  -c "SELECT count(*) FROM chunks;"
```

---

## 2. 테스트 계정 정보

### 2.1 Keycloak SSO 계정 (브라우저 테스트용)

| 필드 | 값 |
|------|------|
| **URL** | http://localhost → "SSO 로그인" 버튼 클릭 |
| **Realm** | hybrid-rag |
| **Client** | knowledge-frontend (public) |

| 계정 | Username | Password | 역할 |
|------|----------|----------|------|
| **관리자** | admin | admin123 | admin, user, viewer |
| **테스트 사용자** | test | password123 | user |
| **읽기 전용** | test-user | test-password | viewer |

### 2.2 AI Service 직접 로그인 (터미널 테스트용)

| 필드 | 값 |
|------|------|
| **Email** | admin@example.com |
| **Password** | admin1234 |
| **Auth** | HS256 JWT |

```bash
# 토큰 발급
AI_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin1234"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['accessToken'])")
echo $AI_TOKEN
```

### 2.3 기타 서비스 계정

| 서비스 | URL | ID / Password |
|--------|-----|---------------|
| Keycloak Admin | http://localhost:8180/admin | admin / keycloak_admin_2026! |
| Grafana | http://localhost:3001 | admin / grafana_dev_2026! |
| Neo4j | http://localhost:7474 | neo4j / neo4j_dev_2026! |
| MinIO Console | http://localhost:9001 | minioadmin / minio_dev_2026! |
| PostgreSQL | localhost:5432 | knowledge / knowledge_dev_2026! |

---

## 3. Part A: UI 기반 브라우저 테스트

### A-01: Keycloak SSO 로그인

**Test ID**: A-01 | **Priority**: P0 (Critical)

| Step | 액션 | 기대 결과 | Pass/Fail | 비고 |
|------|------|-----------|-----------|------|
| 1.1 | http://localhost 접속 | 로그인 페이지 표시 | [ ] | |
| 1.2 | "SSO 로그인" 버튼 확인 | SSO 버튼 존재 | [ ] | |
| 1.3 | "SSO 로그인" 버튼 클릭 | Keycloak 로그인 페이지로 리다이렉트 | [ ] | URL: localhost:8180/realms/hybrid-rag/... |
| 1.4 | Username: `admin`, Password: `admin123` 입력 | 입력 수락됨 | [ ] | |
| 1.5 | "Sign In" 클릭 | 로딩 후 대시보드로 이동 | [ ] | |
| 1.6 | 사용자 정보 확인 | 상단 헤더에 "Admin User" 또는 이메일 표시 | [ ] | |
| 1.7 | F12 > Application > Local Storage 확인 | accessToken 저장됨 (RS256 JWT) | [ ] | |
| 1.8 | Network 탭에서 API 호출 확인 | Authorization: Bearer ... 헤더 포함 | [ ] | |

**API 검증 (선택)**:
```bash
# Keycloak 토큰 발급 테스트
curl -s -X POST "http://localhost:8180/realms/hybrid-rag/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "grant_type=password" \
  --data-urlencode "client_id=knowledge-frontend" \
  --data-urlencode "username=admin" \
  --data-urlencode "password=admin123" | python3 -m json.tool
```

---

### A-02: 대시보드 확인

**Test ID**: A-02 | **Priority**: P1 (High) | **선행**: A-01 PASS

| Step | 액션 | 기대 결과 | Pass/Fail | 비고 |
|------|------|-----------|-----------|------|
| 2.1 | 대시보드 페이지 확인 | 통계 카드 표시 | [ ] | |
| 2.2 | 전체 문서 수 확인 | 숫자 표시 (현재 2건) | [ ] | |
| 2.3 | 처리 완료 문서 수 확인 | 표시됨 | [ ] | |
| 2.4 | 최근 업로드 목록 확인 | 파일명, 상태 표시 | [ ] | |

---

### A-03: 문서 업로드 (단건/다건)

**Test ID**: A-03 | **Priority**: P0 (Critical) | **선행**: A-01 PASS

**준비물**: 테스트 파일 3개 이상 (PDF, PPTX, TXT 등)

| Step | 액션 | 기대 결과 | Pass/Fail | 비고 |
|------|------|-----------|-----------|------|
| 3.1 | 네비게이션에서 "Upload" 또는 "문서 관리" 클릭 | 업로드 페이지 표시 | [ ] | |
| 3.2 | 드래그 & 드롭 영역 확인 | 업로드 존 표시 | [ ] | |
| 3.3 | **단건**: PDF 파일 1개 드래그 & 드롭 | 파일명, 크기 표시 | [ ] | |
| 3.4 | "Upload" 클릭 | 진행바 표시, 업로드 완료 | [ ] | |
| 3.5 | 업로드 결과 확인 | "Completed" 또는 성공 메시지 | [ ] | |
| 3.6 | **다건**: PPTX + TXT 2개 동시 선택 | 2개 파일 목록 표시 | [ ] | |
| 3.7 | "Upload All" 클릭 | 2개 모두 업로드 완료 | [ ] | |
| 3.8 | F12 Network에서 API 호출 확인 | `POST /api/v1/documents/upload` → 200/201 | [ ] | Gateway → AI Service |

**지원 파일 형식**:

| 형식 | 확장자 | 최대 크기 | 테스트 |
|------|--------|-----------|--------|
| PDF | .pdf | 50MB | [ ] |
| PPTX | .pptx | 50MB | [ ] |
| DOCX | .docx | 50MB | [ ] |
| TXT | .txt | 50MB | [ ] |
| Markdown | .md | 50MB | [ ] |

---

### A-04: 문서 처리 상태 확인

**Test ID**: A-04 | **Priority**: P1 (High) | **선행**: A-03 PASS

| Step | 액션 | 기대 결과 | Pass/Fail | 비고 |
|------|------|-----------|-----------|------|
| 4.1 | 문서 목록 페이지 이동 | 업로드한 문서 목록 표시 | [ ] | |
| 4.2 | 처리 상태 컬럼 확인 | uploaded/processing/completed/failed 표시 | [ ] | |
| 4.3 | SSE 실시간 업데이트 확인 | 상태가 자동으로 갱신됨 | [ ] | 구현 여부에 따라 수동 새로고침 |
| 4.4 | 처리 완료 문서 클릭 | 상세 정보 (메타데이터) 표시 | [ ] | |

**처리 상태 참조**:

| Status | 설명 | 시각적 표시 |
|--------|------|------------|
| uploaded | 저장됨, 처리 대기 | 노란색/주황색 |
| processing | 처리 중 (청킹/임베딩) | 파란색/스피너 |
| completed | 검색 가능 | 녹색 |
| failed | 처리 실패 | 빨간색 |

---

### A-05: 검색 (키워드/시맨틱)

**Test ID**: A-05 | **Priority**: P0 (Critical) | **선행**: 처리 완료 문서 존재

| Step | 액션 | 기대 결과 | Pass/Fail | 비고 |
|------|------|-----------|-----------|------|
| 5.1 | 네비게이션에서 "Search" 클릭 | 검색 페이지 표시 | [ ] | |
| 5.2 | 검색어 입력: "MSA" | 검색어 입력됨 | [ ] | |
| 5.3 | Enter 또는 검색 버튼 클릭 | 로딩 후 결과 표시 | [ ] | |
| 5.4 | 검색 결과 확인 | 관련 문서 청크 목록 | [ ] | |
| 5.5 | 결과 항목 클릭 | 상세 내용 표시 | [ ] | |
| 5.6 | 다른 검색어: "Knowledge Graph" | 시맨틱 관련 결과 | [ ] | |
| 5.7 | 한글 검색: "지식 그래프" | 한국어 검색 동작 | [ ] | |
| 5.8 | 빈 검색어 처리 | 에러 메시지 또는 안내 | [ ] | |

---

### A-06: 로그아웃 & 세션

**Test ID**: A-06 | **Priority**: P1 (High) | **선행**: A-01 PASS

| Step | 액션 | 기대 결과 | Pass/Fail | 비고 |
|------|------|-----------|-----------|------|
| 6.1 | 사용자 메뉴/프로필 클릭 | 드롭다운 표시 | [ ] | |
| 6.2 | "로그아웃" 클릭 | 로그인 페이지로 이동 | [ ] | |
| 6.3 | F12 > Local Storage 확인 | accessToken 삭제됨 | [ ] | |
| 6.4 | 직접 URL 입력하여 보호 페이지 접근 | 로그인 페이지로 리다이렉트 | [ ] | |
| 6.5 | 다시 SSO 로그인 | 정상 로그인됨 | [ ] | |

---

## 4. Part B: 대량 파일 청킹 + 임베딩 파이프라인 테스트

> **목적**: 대량 파일을 업로드하고 전체 처리 파이프라인(파싱 → 청킹 → 임베딩 → ES 색인)이
> 정상 동작하는지 검증한 후, 터미널에서 Retriever(Hybrid Search)로 품질을 확인합니다.

### B-01: 테스트 데이터 준비

**Test ID**: B-01 | **Priority**: P0

#### 방법 1: 기존 문서 재처리

```bash
# AI Service 토큰 발급
AI_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin1234"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['accessToken'])")

# 현재 문서 목록 확인
curl -s http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer $AI_TOKEN" | python3 -m json.tool
```

#### 방법 2: 대량 파일 업로드 (curl)

```bash
# 단건 업로드
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer $AI_TOKEN" \
  -F "file=@/path/to/your/document.pdf"

# 다건 업로드 (반복)
for f in /path/to/test/files/*; do
  echo "Uploading: $f"
  curl -s -X POST http://localhost:8000/api/v1/documents/upload \
    -H "Authorization: Bearer $AI_TOKEN" \
    -F "file=@$f" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'  → {d.get(\"document_id\",\"?\")} {d.get(\"status\",\"?\")}')"
  sleep 1
done
```

#### 방법 3: 테스트용 텍스트 파일 자동 생성

```bash
# 테스트 디렉토리 생성
mkdir -p /tmp/uat_test_files

# 대량 테스트 파일 5개 생성
cat > /tmp/uat_test_files/test_msa_architecture.txt << 'EOF'
MSA(Microservice Architecture) 전환 전략

1. 모놀리식에서 마이크로서비스로의 전환
기존 모놀리식 아키텍처의 한계를 극복하기 위해 마이크로서비스 아키텍처로 전환합니다.
각 서비스는 독립적으로 배포 가능하며, API Gateway를 통해 통합됩니다.

2. 도메인 주도 설계(DDD)
바운디드 컨텍스트(Bounded Context)를 기반으로 서비스를 분리합니다.
- 사용자 서비스: 인증, 권한 관리
- 문서 서비스: 문서 업로드, 처리, 저장
- 검색 서비스: 벡터 검색, 키워드 검색, 하이브리드 검색
- 분석 서비스: 통계, 리포트, 대시보드

3. 이벤트 기반 통신
서비스 간 통신은 이벤트 기반으로 처리합니다.
Apache Kafka를 메시지 브로커로 사용하여 비동기 통신을 구현합니다.
EOF

cat > /tmp/uat_test_files/test_rag_pipeline.txt << 'EOF'
RAG(Retrieval-Augmented Generation) 파이프라인 설계

1. 문서 수집 및 전처리
다양한 형식의 문서(PDF, PPTX, DOCX, TXT)를 파싱하여 텍스트를 추출합니다.
메타데이터(작성자, 날짜, 프로젝트)를 자동으로 추출합니다.

2. 청킹(Chunking) 전략
- 기본 청크 크기: 512 토큰
- 오버랩: 50 토큰
- 시맨틱 청킹: 의미 단위로 분할
문서의 구조(제목, 단락, 목록)를 고려한 지능형 청킹을 적용합니다.

3. 임베딩(Embedding)
BGE-M3 다국어 모델을 사용하여 청크를 벡터로 변환합니다.
Dense + Sparse 벡터를 동시에 생성하여 하이브리드 검색을 지원합니다.

4. Knowledge Graph 구축
Neo4j를 사용하여 문서, 엔티티, 관계를 그래프로 구축합니다.
엔티티 추출: 사람, 조직, 기술, 프로젝트 등

5. Hybrid Search
Elasticsearch에서 BM25 키워드 검색과 벡터 검색을 결합합니다.
RRF(Reciprocal Rank Fusion)로 결과를 통합합니다.
EOF

cat > /tmp/uat_test_files/test_kubernetes_migration.txt << 'EOF'
Kubernetes 마이그레이션 가이드

1. 컨테이너화 전략
모든 서비스를 Docker 컨테이너로 패키징합니다.
멀티스테이지 빌드를 사용하여 이미지 크기를 최소화합니다.

2. Kubernetes 클러스터 구성
- Control Plane: 3개 노드 (HA 구성)
- Worker Node: 5개 노드 (Auto-scaling)
- Ingress Controller: Nginx Ingress
- Service Mesh: Istio

3. CI/CD 파이프라인
GitHub Actions → Docker Build → Harbor Registry → ArgoCD → Kubernetes
GitOps 방식으로 선언적 배포를 구현합니다.

4. 모니터링 스택
- Prometheus: 메트릭 수집
- Grafana: 시각화 대시보드
- Loki: 로그 수집
- Jaeger: 분산 추적
- Alertmanager: 알림 관리

5. 보안
- RBAC: 역할 기반 접근 제어
- Network Policy: Pod 간 네트워크 격리
- Secret Management: Vault 연동
- Pod Security Standards: Restricted 정책
EOF

cat > /tmp/uat_test_files/test_elasticsearch_optimization.txt << 'EOF'
Elasticsearch 검색 최적화 가이드

1. 인덱스 설계
knowledge_chunks 인덱스 구조:
- content: text 타입 (nori 한국어 분석기)
- content_vector: dense_vector 타입 (1024 차원, BGE-M3)
- metadata: object 타입 (document_type, project_name, keywords)
- created_at: date 타입

2. 검색 쿼리 최적화
BM25 키워드 검색:
- nori 형태소 분석기로 한국어 토큰화
- multi_match 쿼리로 content + metadata.title 검색
- boost 파라미터로 필드 가중치 조정

벡터 검색:
- kNN 검색으로 코사인 유사도 기반 검색
- num_candidates: 100, k: 10 설정
- 사전 필터링으로 검색 범위 축소

하이브리드 검색:
- BM25 + kNN 결과를 RRF로 통합
- k=60 파라미터로 순위 융합

3. 성능 튜닝
- 샤드 수: 1 (소규모)
- 레플리카: 0 (개발 환경)
- refresh_interval: 5s
- 벌크 인덱싱: 배치 크기 100
EOF

cat > /tmp/uat_test_files/test_project_management.txt << 'EOF'
프로젝트 관리 방법론

1. 애자일 스크럼 프레임워크
2주 단위 스프린트로 반복적 개발을 수행합니다.
- Sprint Planning: 스프린트 시작 시 백로그 아이템 선정
- Daily Standup: 매일 15분 상태 공유
- Sprint Review: 스프린트 결과 데모
- Sprint Retrospective: 프로세스 개선

2. Jira 프로젝트 관리
- Epic → Story → Task 계층 구조
- Kanban 보드: To Do, In Progress, Review, Done
- 번다운 차트로 진행 상황 추적

3. Git 브랜치 전략
- main: 프로덕션 릴리스
- develop: 개발 통합
- feature/*: 기능 개발 브랜치
- fix/*: 버그 수정 브랜치
- release/*: 릴리스 준비

4. 코드 리뷰 프로세스
PR 생성 → 자동 테스트 → 피어 리뷰 → 기술 리드 승인 → 머지
최소 1명의 리뷰어 승인 필요

5. 문서화 전략
- API 문서: OpenAPI/Swagger
- 코드 문서: JSDoc, Docstring
- 아키텍처 문서: ADR (Architecture Decision Record)
- 운영 문서: Runbook, SOP
EOF

echo "테스트 파일 생성 완료"
ls -la /tmp/uat_test_files/
```

| 확인 | 항목 |
|------|------|
| [ ] | 테스트 파일 최소 5개 준비 (txt/pdf/pptx) |
| [ ] | 파일 크기 및 형식 확인 |
| [ ] | AI Service 토큰 발급 확인 |

---

### B-02: 대량 업로드 + 자동 처리 트리거

**Test ID**: B-02 | **Priority**: P0

```bash
# 1. AI Service 토큰 발급
AI_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin1234"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['accessToken'])")

# 2. 대량 업로드 (5개 파일)
echo "=== 대량 업로드 시작 ==="
for f in /tmp/uat_test_files/*.txt; do
  FILENAME=$(basename "$f")
  echo -n "[$FILENAME] 업로드 중... "
  RESULT=$(curl -s -X POST http://localhost:8000/api/v1/documents/upload \
    -H "Authorization: Bearer $AI_TOKEN" \
    -F "file=@$f")
  DOC_ID=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('document_id','ERROR'))" 2>/dev/null)
  STATUS=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','ERROR'))" 2>/dev/null)
  echo "→ ID: $DOC_ID, Status: $STATUS"
  sleep 1
done
echo "=== 업로드 완료 ==="

# 3. 전체 문서 목록 확인
echo ""
echo "=== 문서 목록 ==="
curl -s http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer $AI_TOKEN" \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'총 문서 수: {data[\"total\"]}')
for doc in data['documents']:
    print(f'  [{doc[\"status\"]:12}] {doc[\"filename\"]:50} (ID: {doc[\"document_id\"][:8]}...)')
"
```

| 확인 | 항목 | 기대 |
|------|------|------|
| [ ] | 5개 파일 모두 업로드 성공 | document_id 반환 |
| [ ] | 문서 상태 확인 | uploaded 또는 processing |
| [ ] | 자동 처리 트리거 확인 | 백그라운드 워커 시작 |

---

### B-03: 청킹 검증 (PostgreSQL)

**Test ID**: B-03 | **Priority**: P0

```bash
# 1. 처리 완료 대기 (최대 5분)
echo "=== 처리 상태 모니터링 (30초 간격) ==="
for i in $(seq 1 10); do
  echo "--- Check #$i ($(date +%H:%M:%S)) ---"
  docker exec kp-postgresql psql -U knowledge -d knowledge -c \
    "SELECT processing_status, count(*), sum(chunk_count) as total_chunks
     FROM documents
     GROUP BY processing_status
     ORDER BY processing_status;"

  # 모든 문서가 completed이면 종료
  PENDING=$(docker exec kp-postgresql psql -U knowledge -d knowledge -t -c \
    "SELECT count(*) FROM documents WHERE processing_status NOT IN ('completed','failed');" | tr -d ' ')
  if [ "$PENDING" = "0" ]; then
    echo "✓ 모든 문서 처리 완료!"
    break
  fi
  sleep 30
done

# 2. 청크 상세 확인
echo ""
echo "=== 청크 통계 ==="
docker exec kp-postgresql psql -U knowledge -d knowledge -c "
SELECT
  d.title,
  d.processing_status,
  d.chunk_count,
  count(c.id) as actual_chunks,
  min(length(c.content)) as min_chunk_len,
  max(length(c.content)) as max_chunk_len,
  avg(length(c.content))::int as avg_chunk_len
FROM documents d
LEFT JOIN chunks c ON c.document_id = d.id
GROUP BY d.id, d.title, d.processing_status, d.chunk_count
ORDER BY d.created_at DESC;
"

# 3. 청크 샘플 확인
echo ""
echo "=== 청크 샘플 (첫 3건) ==="
docker exec kp-postgresql psql -U knowledge -d knowledge -c "
SELECT
  c.id,
  left(c.content, 100) as content_preview,
  c.chunk_index,
  length(c.content) as content_length
FROM chunks c
LIMIT 3;
"
```

| 확인 | 항목 | 기대 |
|------|------|------|
| [ ] | 문서당 청크 수 확인 | 1개 이상 생성 |
| [ ] | 청크 크기 범위 확인 | 100~2000자 범위 |
| [ ] | 청크 내용 미리보기 | 원문과 관련 있는 텍스트 |
| [ ] | 총 청크 수 | 문서 5개 기준 15~50개 예상 |

---

### B-04: 임베딩 검증 (Elasticsearch)

**Test ID**: B-04 | **Priority**: P0

```bash
# 1. ES 인덱스 통계
echo "=== ES 인덱스 상태 ==="
curl -s "http://localhost:9200/knowledge_chunks/_count" | python3 -m json.tool

# 2. ES 청크 샘플 확인
echo ""
echo "=== ES 청크 샘플 ==="
curl -s "http://localhost:9200/knowledge_chunks/_search?size=2&pretty" \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
total = data['hits']['total']['value']
print(f'총 청크 수: {total}')
for hit in data['hits']['hits']:
    src = hit['_source']
    content = src.get('content', '')[:100]
    has_vector = 'content_vector' in src
    vector_dim = len(src.get('content_vector', [])) if has_vector else 0
    meta = src.get('metadata', {})
    print(f'')
    print(f'  ID: {hit[\"_id\"]}')
    print(f'  Content: {content}...')
    print(f'  Vector: {\"✓\" if has_vector else \"✗\"} ({vector_dim} dims)')
    print(f'  Metadata: {json.dumps(meta, ensure_ascii=False)[:100]}')
"

# 3. 벡터 필드 존재 확인
echo ""
echo "=== 벡터 필드 매핑 확인 ==="
curl -s "http://localhost:9200/knowledge_chunks/_mapping" \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
mappings = list(data.values())[0]['mappings']['properties']
for field, config in sorted(mappings.items()):
    ftype = config.get('type', 'object')
    extra = ''
    if ftype == 'dense_vector':
        extra = f' (dims={config.get(\"dims\",\"?\")}, similarity={config.get(\"similarity\",\"?\")})'
    print(f'  {field:30} → {ftype}{extra}')
"
```

| 확인 | 항목 | 기대 |
|------|------|------|
| [ ] | ES 청크 수 = PG 청크 수 | 일치 (또는 기존 18 + 신규) |
| [ ] | content_vector 필드 존재 | dense_vector 1024 dims |
| [ ] | 벡터 값이 0이 아님 | 실제 임베딩 값 |
| [ ] | 메타데이터 포함 | document_type, title 등 |

---

### B-05: 터미널 Retriever 테스트 (Hybrid Search)

**Test ID**: B-05 | **Priority**: P0 (Critical)

```bash
# AI Service 토큰
AI_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin1234"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['accessToken'])")

# ─────────────────────────────────────────────
# Test 1: 키워드 검색 - "MSA 마이크로서비스"
# ─────────────────────────────────────────────
echo "=== Test 1: 키워드 검색 - MSA 마이크로서비스 ==="
curl -s -X POST http://localhost:8000/api/v1/search/hybrid \
  -H "Authorization: Bearer $AI_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"MSA 마이크로서비스 전환","top_k":5}' \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
results = data.get('results', [])
print(f'검색 결과: {len(results)}건')
for i, r in enumerate(results, 1):
    content = r.get('content', '')[:120]
    score = r.get('score', 0)
    source = r.get('metadata', {}).get('search_source', '?')
    title = r.get('metadata', {}).get('title', '?')
    print(f'  [{i}] (score={score:.4f}, source={source})')
    print(f'      Title: {title}')
    print(f'      {content}...')
"

echo ""

# ─────────────────────────────────────────────
# Test 2: 시맨틱 검색 - "문서를 벡터로 변환하는 방법"
# ─────────────────────────────────────────────
echo "=== Test 2: 시맨틱 검색 - 문서를 벡터로 변환하는 방법 ==="
curl -s -X POST http://localhost:8000/api/v1/search/hybrid \
  -H "Authorization: Bearer $AI_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"문서를 벡터로 변환하는 방법","top_k":5}' \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
results = data.get('results', [])
print(f'검색 결과: {len(results)}건')
for i, r in enumerate(results, 1):
    content = r.get('content', '')[:120]
    score = r.get('score', 0)
    print(f'  [{i}] (score={score:.4f}) {content}...')
"

echo ""

# ─────────────────────────────────────────────
# Test 3: 한국어 자연어 질문
# ─────────────────────────────────────────────
echo "=== Test 3: 한국어 자연어 질문 - 검색 최적화 방법은? ==="
curl -s -X POST http://localhost:8000/api/v1/search/hybrid \
  -H "Authorization: Bearer $AI_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"Elasticsearch 검색 성능을 최적화하려면 어떻게 해야 하나요?","top_k":5}' \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
results = data.get('results', [])
print(f'검색 결과: {len(results)}건')
for i, r in enumerate(results, 1):
    content = r.get('content', '')[:120]
    score = r.get('score', 0)
    print(f'  [{i}] (score={score:.4f}) {content}...')
"

echo ""

# ─────────────────────────────────────────────
# Test 4: 영어 검색
# ─────────────────────────────────────────────
echo "=== Test 4: 영어 검색 - Kubernetes deployment ==="
curl -s -X POST http://localhost:8000/api/v1/search/hybrid \
  -H "Authorization: Bearer $AI_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"Kubernetes deployment and CI/CD pipeline","top_k":5}' \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
results = data.get('results', [])
print(f'검색 결과: {len(results)}건')
for i, r in enumerate(results, 1):
    content = r.get('content', '')[:120]
    score = r.get('score', 0)
    print(f'  [{i}] (score={score:.4f}) {content}...')
"

echo ""

# ─────────────────────────────────────────────
# Test 5: 관련 없는 검색 (Negative Test)
# ─────────────────────────────────────────────
echo "=== Test 5: Negative - 관련 없는 검색 ==="
curl -s -X POST http://localhost:8000/api/v1/search/hybrid \
  -H "Authorization: Bearer $AI_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"요리 레시피 김치찌개","top_k":3}' \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
results = data.get('results', [])
print(f'검색 결과: {len(results)}건')
if results:
    max_score = max(r.get('score', 0) for r in results)
    print(f'최대 점수: {max_score:.4f} (낮을수록 좋음 - 관련 없는 검색)')
else:
    print('결과 없음 (정상)')
"
```

| Test | 검색어 | 기대 결과 | Pass/Fail |
|------|--------|-----------|-----------|
| Test 1 | "MSA 마이크로서비스 전환" | MSA/아키텍처 관련 청크 상위 | [ ] |
| Test 2 | "문서를 벡터로 변환하는 방법" | 임베딩/RAG 관련 청크 상위 | [ ] |
| Test 3 | "Elasticsearch 검색 성능을 최적화하려면?" | ES 최적화 관련 청크 상위 | [ ] |
| Test 4 | "Kubernetes deployment and CI/CD" | K8s/CI/CD 관련 청크 상위 | [ ] |
| Test 5 | "요리 레시피 김치찌개" | 결과 없음 또는 낮은 점수 | [ ] |

---

### B-06: 성능 측정

**Test ID**: B-06 | **Priority**: P2

```bash
# 검색 응답 시간 측정 (10회 반복)
AI_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin1234"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['accessToken'])")

echo "=== Hybrid Search 응답 시간 (10회 측정) ==="
TOTAL=0
for i in $(seq 1 10); do
  TIME=$(curl -s -o /dev/null -w "%{time_total}" -X POST http://localhost:8000/api/v1/search/hybrid \
    -H "Authorization: Bearer $AI_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"query":"MSA 마이크로서비스 아키텍처 전환 전략","top_k":5}')
  MS=$(echo "$TIME * 1000" | bc | cut -d. -f1)
  TOTAL=$((TOTAL + MS))
  echo "  [$i] ${MS}ms"
done
AVG=$((TOTAL / 10))
echo "  평균: ${AVG}ms"
echo ""

# 성능 기준
echo "=== 성능 기준 ==="
echo "  P0: < 500ms (기본 검색)"
echo "  P1: < 1000ms (복잡한 검색)"
echo "  P2: < 2000ms (대량 데이터)"
```

| 측정 항목 | 기준 | 측정값 | Pass/Fail |
|-----------|------|--------|-----------|
| Hybrid Search 평균 응답시간 | < 500ms | ___ms | [ ] |
| 문서 업로드 응답시간 | < 3s | ___ms | [ ] |
| 문서 처리 시간 (1건) | < 60s | ___s | [ ] |

---

## 5. 테스트 결과 기록 템플릿

### 실행 요약

| 항목 | 값 |
|------|------|
| **테스트 일자** | 2026-02-06 |
| **테스터** | |
| **시작 시간** | |
| **종료 시간** | |
| **환경** | Docker Compose (WSL2) |

### Part A: UI 테스트 결과

| Test ID | 시나리오명 | 스텝 수 | Pass | Fail | Blocked | 결과 |
|---------|-----------|---------|------|------|---------|------|
| A-01 | Keycloak SSO 로그인 | 8 | | | | |
| A-02 | 대시보드 확인 | 4 | | | | |
| A-03 | 문서 업로드 | 8 | | | | |
| A-04 | 문서 처리 상태 | 4 | | | | |
| A-05 | 검색 (키워드/시맨틱) | 8 | | | | |
| A-06 | 로그아웃 & 세션 | 5 | | | | |
| **소계** | | **37** | | | | |

### Part B: 파이프라인 테스트 결과

| Test ID | 시나리오명 | 항목 수 | Pass | Fail | Blocked | 결과 |
|---------|-----------|---------|------|------|---------|------|
| B-01 | 테스트 데이터 준비 | 3 | | | | |
| B-02 | 대량 업로드 + 처리 | 3 | | | | |
| B-03 | 청킹 검증 (PG) | 4 | | | | |
| B-04 | 임베딩 검증 (ES) | 4 | | | | |
| B-05 | Retriever 검색 | 5 | | | | |
| B-06 | 성능 측정 | 3 | | | | |
| **소계** | | **22** | | | | |

### 전체 합산

```
총 테스트 항목: 59개 (Part A: 37 + Part B: 22)
Pass Rate = (_____ / 59) x 100 = _____%
```

---

## 6. 이슈 리포팅 템플릿

```markdown
### Issue #___

**Test ID**: A-XX / B-XX
**Step**: X.X
**심각도**: Critical / High / Medium / Low
**상태**: Open / In Progress / Resolved

**요약**: [한 줄 설명]

**재현 절차**:
1.
2.
3.

**기대 결과**:

**실제 결과**:

**스크린샷**: [해당 시 첨부]

**로그**:
```
docker logs kp-xxx 2>&1 | tail -20
```

**환경**: Chrome/Edge, Docker Compose (WSL2)
**보고자**:
**보고일**: 2026-02-06
```

---

*Document Created: 2026-02-06*
*Author: Claude (Opus 4.6)*
*Environment: Development (Docker Compose, WSL2)*
