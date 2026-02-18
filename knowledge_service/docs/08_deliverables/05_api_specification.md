# API 명세서

**시스템**: Hybrid RAG Knowledge Platform
**Base URL**: `http://localhost:8000/api/v1`
**인증**: Bearer Token (JWT)
**API 문서 (Swagger UI)**: `http://localhost:8000/docs`
**작성일**: 2026-02-19
**버전**: 1.1

---

## 목차

1. [공통 사항](#1-공통-사항)
2. [인증 API](#2-인증-api)
3. [검색 API](#3-검색-api)
4. [문서 API](#4-문서-api)
5. [Knowledge Graph API](#5-knowledge-graph-api)
6. [임베딩 API](#6-임베딩-api)
7. [추출 API](#7-추출-api)
8. [캐시 API](#8-캐시-api)
9. [시스템 API](#9-시스템-api)

---

## 1. 공통 사항

### 1.1 인증 헤더 형식

인증이 필요한 엔드포인트는 요청 헤더에 JWT 토큰을 포함해야 합니다.

```
Authorization: Bearer <access_token>
```

3가지 인증 전략이 지원됩니다:

| 전략 | 방식 | 용도 |
|------|------|------|
| 자체 JWT (HS256) | `POST /auth/login`으로 발급 | 직접 로그인 |
| Keycloak SSO (RS256) | Keycloak 토큰 | SSO 인증 |
| API Gateway 헤더 | `X-Auth-*` 헤더 | Gateway 경유 |

### 1.2 에러 응답 형식

모든 API 에러는 다음 형식으로 반환됩니다.

```json
{
  "detail": "에러 메시지"
}
```

**HTTP 상태 코드**:

| 코드 | 설명 |
|------|------|
| `200` | 성공 |
| `201` | 생성 성공 (문서 업로드) |
| `202` | 수락됨 (비동기 처리 시작) |
| `400` | 잘못된 요청 (입력 검증 실패) |
| `401` | 인증 실패 (토큰 없음/만료/무효) |
| `404` | 리소스를 찾을 수 없음 |
| `409` | 충돌 (이미 처리 중/완료된 문서) |
| `413` | 파일 크기 초과 |
| `422` | 유효성 검증 실패 (Pydantic) |
| `429` | Rate Limit 초과 |
| `500` | 서버 내부 오류 |
| `502` | 외부 서비스 연결 실패 |
| `504` | 타임아웃 |

### 1.3 페이지네이션

문서 목록 등 페이지네이션이 적용되는 API의 응답 형식:

```json
{
  "documents": [...],
  "total": 1437,
  "page": 1,
  "page_size": 20,
  "total_pages": 72
}
```

### 1.4 curl 공통 설정

본 문서의 모든 curl 예제는 다음 사전 준비가 필요합니다.

```bash
# 로그인 (비밀번호에 !가 포함되므로 임시 파일 방식 사용)
cat > /tmp/login.json << 'ENDJSON'
{"email":"admin@example.com","password":"admin123!"}
ENDJSON

TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d @/tmp/login.json | python3 -c "import sys,json; print(json.load(sys.stdin).get('accessToken',''))")
```

---

## 2. 인증 API

### 2.1 POST /auth/login

이메일/비밀번호로 로그인하여 JWT 토큰을 발급합니다.

**인증**: 불필요

**Request Body**:

| 필드 | 타입 | 필수 | 설명 |
|------|------|:----:|------|
| `email` | string (email) | Y | 이메일 주소 |
| `password` | string | Y | 비밀번호 (최소 6자) |

**Response** (`200 OK`):

| 필드 | 타입 | 설명 |
|------|------|------|
| `accessToken` | string | JWT 액세스 토큰 |
| `refreshToken` | string | 리프레시 토큰 |
| `tokenType` | string | 토큰 타입 (Bearer) |
| `expiresIn` | integer | 액세스 토큰 만료 시간 (초) |

**에러**:

| 코드 | 설명 |
|------|------|
| `401` | 이메일 또는 비밀번호가 올바르지 않습니다 |

**curl 예제**:

```bash
cat > /tmp/login.json << 'ENDJSON'
{"email":"admin@example.com","password":"admin123!"}
ENDJSON

curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d @/tmp/login.json
```

**응답 예시**:

```json
{
  "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refreshToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "tokenType": "Bearer",
  "expiresIn": 1800
}
```

### 2.2 POST /auth/refresh

리프레시 토큰으로 새 액세스 토큰을 발급합니다.

**인증**: 불필요

**Request Body**:

| 필드 | 타입 | 필수 | 설명 |
|------|------|:----:|------|
| `refreshToken` | string | Y | 리프레시 토큰 |

**Response** (`200 OK`): `TokenResponse`와 동일

**에러**:

| 코드 | 설명 |
|------|------|
| `401` | 유효하지 않거나 만료된 리프레시 토큰입니다 |

**curl 예제**:

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/refresh \
  -H 'Content-Type: application/json' \
  -d '{"refreshToken":"eyJhbGci..."}'
```

### 2.3 POST /auth/logout

현재 세션을 로그아웃합니다 (리프레시 토큰 무효화).

**인증**: Bearer Token

**Response** (`200 OK`):

```json
{
  "message": "로그아웃 되었습니다",
  "success": true
}
```

**curl 예제**:

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/logout \
  -H "Authorization: Bearer $TOKEN"
```

### 2.4 GET /auth/me

인증된 사용자의 프로필 정보를 조회합니다.

**인증**: Bearer Token

**Response** (`200 OK`):

| 필드 | 타입 | 설명 |
|------|------|------|
| `id` | string | 사용자 ID |
| `email` | string | 이메일 주소 |
| `name` | string | 사용자 이름 |
| `role` | string | 사용자 역할 (admin, user) |
| `createdAt` | string | 계정 생성일 |

**curl 예제**:

```bash
curl -s http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

**응답 예시**:

```json
{
  "id": "user-admin",
  "email": "admin@example.com",
  "name": "System Administrator",
  "role": "admin",
  "createdAt": "2026-01-01T00:00:00Z"
}
```

---

## 3. 검색 API

### 3.1 POST /search/keyword

Elasticsearch BM25 기반 키워드 매칭 검색을 수행합니다.

**인증**: Bearer Token

**Request Body**:

| 필드 | 타입 | 필수 | 기본값 | 설명 |
|------|------|:----:|:------:|------|
| `query` | string | Y | - | 검색 질의 (1~1000자) |
| `top_k` | integer | N | 10 | 반환할 결과 수 (1~100) |
| `filters` | object | N | null | 필터 조건 |
| `useGraph` | boolean | N | true | Graph 검색 사용 여부 |
| `useVector` | boolean | N | true | Vector 검색 사용 여부 |

**Response** (`200 OK`) - `SearchResponse`:

| 필드 | 타입 | 설명 |
|------|------|------|
| `query` | string | 원본 질의 |
| `results` | SearchResult[] | 검색 결과 목록 |
| `total` | integer | 총 결과 수 |
| `search_type` | string | 검색 유형 (`keyword`) |
| `latency_ms` | number | 검색 소요 시간 (ms) |
| `from_cache` | boolean | 캐시 히트 여부 |

**SearchResult 항목**:

| 필드 | 타입 | 설명 |
|------|------|------|
| `chunk_id` | string | 청크 UUID |
| `document_id` | string | 문서 UUID |
| `title` | string | 문서 제목 |
| `content` | string | 청크 내용 |
| `score` | number | BM25 관련성 점수 |
| `source_type` | string | 검색 소스 (`keyword`) |
| `contributing_sources` | string[] | 기여 소스 목록 |
| `metadata` | object | 메타데이터 (파일명, 하이라이트 등) |
| `has_embedding` | boolean | 임베딩 벡터 존재 여부 |

**curl 예제**:

```bash
curl -s -X POST http://localhost:8000/api/v1/search/keyword \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"프로젝트 관리","top_k":5}'
```

**응답 예시**:

```json
{
  "query": "프로젝트 관리",
  "results": [
    {
      "chunk_id": "5669acd8-0379-4f2c-965b-297a3d1160cc",
      "document_id": "93f276f2-da66-42ae-81e1-ed04a8b4afae",
      "title": "FTBS-PP-02-프로젝트추진계획서_v1.0_20230524",
      "content": "Contents\n\n1. 프로젝트 관리 방안\n\nIII. 프로젝트 수행 방안...",
      "score": 29.181835,
      "source_type": "keyword",
      "contributing_sources": null,
      "metadata": {
        "file_name": "FTBS-PP-02-프로젝트추진계획서_v1.0_20230524.pptx",
        "extension": ".pptx",
        "highlight": {
          "text": ["<em>프로젝트</em> <em>관리</em> 방안..."]
        }
      },
      "has_embedding": true
    }
  ],
  "total": 2,
  "search_type": "keyword",
  "latency_ms": 45.2,
  "from_cache": false
}
```

### 3.2 POST /search/semantic

BGE-M3 벡터 기반 시맨틱 검색을 수행합니다 (Elasticsearch kNN).

**인증**: Bearer Token

**Request Body**:

| 필드 | 타입 | 필수 | 기본값 | 설명 |
|------|------|:----:|:------:|------|
| `query` | string | Y | - | 검색 질의 (1~1000자) |
| `top_k` | integer | N | 10 | 반환할 결과 수 (1~100) |
| `filters` | object | N | null | 필터 조건 |

> **참고**: 시맨틱 검색은 `useGraph`, `useVector` 파라미터를 지원하지 않습니다.
> 키워드/하이브리드 검색만 이 파라미터를 사용합니다.

**Response** (`200 OK`): `SearchResponse`와 동일 구조. `search_type`은 `semantic`.

**curl 예제**:

```bash
curl -s -X POST http://localhost:8000/api/v1/search/semantic \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"시스템 성능 개선 방법","top_k":5}'
```

### 3.3 POST /search/hybrid

4-Way Hybrid Search (Dense + Sparse + BM25 + Graph) + RRF + BGE-Reranker.

**인증**: Bearer Token

**Request Body**:

| 필드 | 타입 | 필수 | 기본값 | 설명 |
|------|------|:----:|:------:|------|
| `query` | string | Y | - | 검색 질의 (1~1000자) |
| `top_k` | integer | N | 10 | 반환할 결과 수 (1~100) |
| `filters` | object | N | null | 필터 조건 |
| `useGraph` | boolean | N | true | Graph 검색 사용 여부 |
| `useVector` | boolean | N | true | Vector 검색 사용 여부 |

**Response** (`200 OK`): `SearchResponse` 구조. `search_type`은 `hybrid`.

하이브리드 검색 결과의 `metadata`에는 추가 필드가 포함됩니다:

| 필드 | 설명 |
|------|------|
| `rrf_score` | RRF 융합 점수 |
| `rerank_score` | BGE-Reranker 재순위 점수 |
| `source_ranks` | 소스별 순위 (예: `{"vector": 3, "keyword": 2, "sparse": 4}`) |
| `source_scores` | 소스별 점수 |
| `contributing_sources` | 기여 소스 목록 |
| `matched_entities` | Graph Search에서 매칭된 엔티티 |

**curl 예제**:

```bash
curl -s -X POST http://localhost:8000/api/v1/search/hybrid \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"프로젝트 관리","top_k":5,"useGraph":true,"useVector":true}'
```

**응답 예시** (축약):

```json
{
  "query": "프로젝트 관리",
  "results": [
    {
      "chunk_id": "84e3e879-8b45-47c9-b499-f35800c2ccc9",
      "document_id": "5bc903f1-8439-494c-936e-8f81d6d2fab1",
      "title": "FTBS-PP-01-사업수행계획서_v1.0_20230501",
      "content": "## 4 프로젝트 관리\n\n프로젝트 수행 관리 체계...",
      "score": 0.991225,
      "source_type": "keyword",
      "contributing_sources": ["vector", "keyword", "sparse"],
      "metadata": {
        "rrf_score": 0.04294,
        "rerank_score": 0.991225,
        "source_ranks": {"vector": 3, "keyword": 2, "sparse": 4},
        "matched_entities": ["역할 조정 체계", "협업 체계", "후속 대책"]
      },
      "has_embedding": true
    }
  ],
  "total": 2,
  "search_type": "hybrid",
  "latency_ms": 1250.5,
  "from_cache": false
}
```

### 3.4 POST /search/chat

LangGraph RAG Workflow 기반 대화형 검색. 자연어 질문에 대해 답변을 생성합니다.

**인증**: Bearer Token

**Request Body**:

| 필드 | 타입 | 필수 | 기본값 | 설명 |
|------|------|:----:|:------:|------|
| `query` | string | Y | - | 사용자 질문 (1~2000자) |
| `conversationId` | string | N | null | 대화 세션 ID (기존 대화 이어가기) |
| `topK` | integer | N | 5 | 검색 결과 수 (1~20) |
| `useReasoner` | boolean | N | false | Reasoner 모델 사용 여부 |

**Response** (`200 OK`) - `ChatResponse`:

| 필드 | 타입 | 설명 |
|------|------|------|
| `answer` | string | 생성된 답변 |
| `sources` | object[] | 출처 정보 (문서명, 청크 등) |
| `conversationId` | string | 대화 세션 ID |
| `latencyMs` | number | 처리 소요 시간 (ms) |
| `turnCount` | integer | 대화 턴 수 |
| `pipelineStages` | object | 파이프라인 단계별 정보 |

**에러**:

| 코드 | 설명 |
|------|------|
| `400` | 입력 검증 실패 |
| `429` | Rate Limit 초과 (DeepSeek API) |
| `502` | 외부 서비스 연결 실패 |
| `504` | 타임아웃 |

**curl 예제**:

```bash
curl -s -X POST http://localhost:8000/api/v1/search/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"프로젝트 품질 관리 방법은?","topK":5}'
```

### 3.5 POST /search/chat/stream

SSE 스트리밍 방식의 대화형 검색. 토큰 단위로 실시간 응답합니다.

**인증**: Bearer Token

**Request Body**: `ChatRequest`와 동일

**Response**: `text/event-stream` (Server-Sent Events)

**SSE 이벤트 유형**:

| 이벤트 | 필드 | 설명 |
|--------|------|------|
| `start` | `conversationId`, `sources`, `contextLength`, `turnCount` | 검색 시작 |
| `chunk` | `content`, `tokenIndex` | 답변 텍스트 청크 |
| `error` | `message` | 오류 발생 |
| `end` | `conversationId`, `totalTokens`, `latencyMs` | 스트리밍 종료 |

**curl 예제**:

```bash
curl -N -X POST http://localhost:8000/api/v1/search/chat/stream \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"프로젝트 품질 관리 방법은?","topK":5}'
```

### 3.6 GET /search/conversations/{conversation_id}

대화 세션 요약 정보를 조회합니다.

**인증**: Bearer Token

**Path Parameter**:

| 필드 | 타입 | 설명 |
|------|------|------|
| `conversation_id` | string | 대화 세션 ID |

**Response** (`200 OK`) - `ConversationSummary`:

| 필드 | 타입 | 설명 |
|------|------|------|
| `sessionId` | string | 세션 ID |
| `userId` | string | 사용자 ID |
| `turnCount` | integer | 대화 턴 수 |
| `createdAt` | string | 생성 시간 |
| `updatedAt` | string | 마지막 업데이트 시간 |
| `lastQuery` | string | 마지막 질문 |

**에러**:

| 코드 | 설명 |
|------|------|
| `404` | 대화 세션을 찾을 수 없음 |

### 3.7 DELETE /search/conversations/{conversation_id}

대화 세션을 삭제합니다.

**인증**: Bearer Token

**Response** (`200 OK`):

```json
{
  "deleted": true,
  "conversationId": "session-id-here"
}
```

**에러**:

| 코드 | 설명 |
|------|------|
| `404` | 대화 세션을 찾을 수 없음 |

---

## 4. 문서 API

### 4.1 GET /documents

문서 목록을 페이지네이션으로 조회합니다.

**인증**: 불필요 (인증 없이 접근 가능)

**Query Parameters**:

| 필드 | 타입 | 기본값 | 설명 |
|------|------|:------:|------|
| `page` | integer | 1 | 페이지 번호 (1 이상) |
| `page_size` | integer | 20 | 페이지당 문서 수 (1~100) |
| `status` | string | null | 상태 필터 (queued, processing, parsing, chunking, embedding, storing, extracting, completed, failed) |
| `format` | string | null | 형식 필터 (pdf, docx, hwp, pptx, md, txt, log, html, svg, ipynb) |

**Response** (`200 OK`) - `DocumentListResponse`:

| 필드 | 타입 | 설명 |
|------|------|------|
| `documents` | DocumentListItem[] | 문서 목록 |
| `total` | integer | 전체 문서 수 |
| `page` | integer | 현재 페이지 |
| `page_size` | integer | 페이지 크기 |
| `total_pages` | integer | 전체 페이지 수 |

**DocumentListItem**:

| 필드 | 타입 | 설명 |
|------|------|------|
| `document_id` | string (UUID) | 문서 고유 ID |
| `filename` | string | 원본 파일명 |
| `format` | string | 문서 형식 (pdf, docx, pptx 등) |
| `size_bytes` | integer | 파일 크기 (바이트) |
| `status` | string | 처리 상태 |
| `created_at` | string | 업로드 시간 (ISO 8601) |

**curl 예제**:

```bash
curl -s "http://localhost:8000/api/v1/documents?page=1&page_size=5" \
  -H "Authorization: Bearer $TOKEN"
```

**응답 예시**:

```json
{
  "documents": [
    {
      "document_id": "9ef52538-cfd0-4193-b36d-23d47a596d02",
      "filename": "How_to_Build_AI_Agents_with_LangGraph",
      "format": "pdf",
      "size_bytes": 900541,
      "status": "completed",
      "created_at": "2026-02-12T02:08:33.983126"
    }
  ],
  "total": 1437,
  "page": 1,
  "page_size": 5,
  "total_pages": 288
}
```

### 4.2 POST /documents/upload

문서를 업로드합니다. 업로드 후 자동으로 처리 파이프라인이 트리거됩니다.

**인증**: Bearer Token

**Request**: `multipart/form-data`

| 필드 | 타입 | 필수 | 설명 |
|------|------|:----:|------|
| `file` | file | Y | 업로드할 파일 |
| `metadata` | string (JSON) | N | 메타데이터 JSON (title, description, tags, project_name) |

**지원 형식 및 최대 크기**:

| 형식 | 확장자 | 최대 크기 |
|------|--------|----------|
| PDF | `.pdf` | 100MB |
| PPTX | `.pptx` | 100MB |
| DOCX | `.docx` | 50MB |
| HWP | `.hwp` | 50MB |
| IPYNB | `.ipynb` | 50MB |
| Markdown | `.md` | 10MB |
| TXT | `.txt` | 10MB |
| LOG | `.log` | 10MB |
| HTML | `.html`, `.htm` | 10MB |
| SVG | `.svg` | 10MB |

**Response** (`201 Created`) - `DocumentResponse`:

| 필드 | 타입 | 설명 |
|------|------|------|
| `document_id` | string (UUID) | 문서 고유 ID |
| `filename` | string | 보안 처리된 파일명 |
| `format` | string | 감지된 문서 형식 |
| `size_bytes` | integer | 파일 크기 (바이트) |
| `status` | string | 처리 상태 (`queued`) |
| `status_url` | string | 상태 조회 URL |
| `created_at` | string | 업로드 시간 (ISO 8601) |
| `metadata` | object | 메타데이터 (제공된 경우) |

**에러**:

| 코드 | 설명 |
|------|------|
| `400` | 지원하지 않는 파일 형식, 빈 파일, 파일 크기 너무 작음 (<100B), 잘못된 메타데이터 |
| `413` | 파일 크기 초과 |

**curl 예제**:

```bash
curl -s -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/document.pdf" \
  -F 'metadata={"title":"프로젝트 계획서","tags":["프로젝트","계획"]}'
```

### 4.3 GET /documents/{document_id}/status

특정 문서의 처리 상태를 조회합니다. PostgreSQL fallback을 지원하여 컨테이너 재시작 후에도 조회 가능합니다.

**인증**: 불필요

**Path Parameter**:

| 필드 | 타입 | 설명 |
|------|------|------|
| `document_id` | string (UUID) | 문서 ID |

**Response** (`200 OK`) - `DocumentStatusResponse`:

| 필드 | 타입 | 설명 |
|------|------|------|
| `document_id` | string (UUID) | 문서 ID |
| `status` | string | 처리 상태 (queued, processing, parsing, chunking, embedding, storing, extracting, completed, failed) |
| `progress_percent` | integer | 진행률 (0~100) |
| `error_message` | string | 에러 메시지 (실패 시) |
| `updated_at` | string | 마지막 업데이트 시간 |

**에러**:

| 코드 | 설명 |
|------|------|
| `404` | 문서를 찾을 수 없음 |

**curl 예제**:

```bash
curl -s http://localhost:8000/api/v1/documents/9ef52538-cfd0-4193-b36d-23d47a596d02/status
```

### 4.4 POST /documents/{document_id}/process

문서 처리를 수동으로 트리거합니다 (파싱, 청킹, 임베딩, 저장). 처리는 비동기로 진행됩니다.

**인증**: Bearer Token

**Response** (`202 Accepted`):

```json
{
  "document_id": "9ef52538-...",
  "status": "accepted",
  "message": "문서 처리가 시작되었습니다",
  "status_url": "/api/v1/documents/9ef52538-.../status"
}
```

**에러**:

| 코드 | 설명 |
|------|------|
| `404` | 문서를 찾을 수 없음 |
| `409` | 이미 처리 중인 문서 |

**curl 예제**:

```bash
curl -s -X POST http://localhost:8000/api/v1/documents/9ef52538-cfd0-4193-b36d-23d47a596d02/process \
  -H "Authorization: Bearer $TOKEN"
```

### 4.5 POST /documents/{document_id}/retry

실패한 문서를 재처리합니다. 상태를 queued로 초기화하고 파이프라인을 다시 실행합니다. `failed` 또는 `completed` 상태의 문서만 재시도 가능합니다.

**인증**: Bearer Token

**Response** (`202 Accepted`):

```json
{
  "document_id": "9ef52538-...",
  "status": "accepted",
  "message": "문서 재처리가 시작되었습니다",
  "previous_status": "failed",
  "status_url": "/api/v1/documents/9ef52538-.../status"
}
```

**에러**:

| 코드 | 설명 |
|------|------|
| `404` | 문서를 찾을 수 없음 |
| `409` | 재시도할 수 없는 상태 (failed 또는 completed만 가능) |

**curl 예제**:

```bash
curl -s -X POST http://localhost:8000/api/v1/documents/9ef52538-cfd0-4193-b36d-23d47a596d02/retry \
  -H "Authorization: Bearer $TOKEN"
```

### 4.6 POST /documents/process-pending

대기 중인 모든 문서를 일괄 처리합니다.

**인증**: Bearer Token

**Query Parameters**:

| 필드 | 타입 | 기본값 | 설명 |
|------|------|:------:|------|
| `batch_size` | integer | 5 | 한 번에 처리할 문서 수 (1~20) |

**Response** (`202 Accepted`):

```json
{
  "count": 3,
  "status": "accepted",
  "message": "3개 문서 처리가 시작되었습니다",
  "document_ids": ["uuid-1", "uuid-2", "uuid-3"]
}
```

**curl 예제**:

```bash
curl -s -X POST "http://localhost:8000/api/v1/documents/process-pending?batch_size=10" \
  -H "Authorization: Bearer $TOKEN"
```

### 4.7 GET /documents/{document_id}/download

원본 문서 다운로드 URL을 조회합니다. MinIO presigned URL 또는 로컬 파일로 리다이렉트합니다.

**인증**: 불필요

**Response**: `302 Redirect` (MinIO presigned URL) 또는 `FileResponse` (로컬 파일)

**에러**:

| 코드 | 설명 |
|------|------|
| `404` | 문서를 찾을 수 없음 또는 파일이 서버에 존재하지 않음 |

**curl 예제**:

```bash
curl -s -L http://localhost:8000/api/v1/documents/9ef52538-cfd0-4193-b36d-23d47a596d02/download \
  -o downloaded_document.pdf
```

### 4.8 GET /documents/{document_id}/status/stream

문서 처리 상태를 SSE 스트리밍으로 모니터링합니다. 1초 간격으로 상태를 전송하며, `completed` 또는 `failed` 시 스트림이 종료됩니다. 최대 5분 타임아웃.

**인증**: 불필요

**Response**: `text/event-stream`

**SSE 이벤트 유형**:

| 이벤트 | 설명 |
|--------|------|
| `status` | 상태 업데이트 (document_id, status, progress_percent, error_message, updated_at) |
| `done` | 처리 완료 (final_status) |
| `error` | 오류 발생 |
| `timeout` | 5분 타임아웃 |

**curl 예제**:

```bash
curl -N http://localhost:8000/api/v1/documents/9ef52538-cfd0-4193-b36d-23d47a596d02/status/stream
```

---

## 5. Knowledge Graph API

### 5.1 GET /graph/entities/{name}

엔티티 이름으로 상세 정보를 조회합니다.

**인증**: Bearer Token

**Path Parameter**:

| 필드 | 타입 | 설명 |
|------|------|------|
| `name` | string | 엔티티 이름 |

**Response** (`200 OK`) - `EntityResponse`:

| 필드 | 타입 | 설명 |
|------|------|------|
| `name` | string | 엔티티 이름 |
| `type` | string | 엔티티 유형 |
| `description` | string | 엔티티 설명 |
| `labels` | string[] | Neo4j 라벨 |
| `properties` | object | 추가 속성 |

**에러**:

| 코드 | 설명 |
|------|------|
| `404` | 엔티티를 찾을 수 없음 |

**curl 예제**:

```bash
curl -s "http://localhost:8000/api/v1/graph/entities/Kubernetes" \
  -H "Authorization: Bearer $TOKEN"
```

### 5.2 POST /graph/subgraph

중심 엔티티를 기준으로 서브그래프를 탐색합니다.

**인증**: Bearer Token

**Request Body**:

| 필드 | 타입 | 필수 | 기본값 | 설명 |
|------|------|:----:|:------:|------|
| `entity_name` | string | Y | - | 중심 엔티티 이름 (1~200자) |
| `depth` | integer | N | 2 | 탐색 깊이 (1~5) |
| `limit` | integer | N | 50 | 최대 노드 수 (1~200) |

**Response** (`200 OK`) - `SubgraphResponse`:

| 필드 | 타입 | 설명 |
|------|------|------|
| `center` | string | 중심 엔티티 |
| `nodes` | object[] | 노드 목록 |
| `edges` | object[] | 엣지 목록 |
| `node_count` | integer | 노드 수 |

**curl 예제**:

```bash
curl -s -X POST http://localhost:8000/api/v1/graph/subgraph \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"entity_name":"Kubernetes","depth":2,"limit":20}'
```

### 5.3 POST /graph/experts

토픽/기술 키워드에 대한 전문가를 검색합니다.

**인증**: Bearer Token

**Request Body**:

| 필드 | 타입 | 필수 | 기본값 | 설명 |
|------|------|:----:|:------:|------|
| `topic` | string | Y | - | 검색할 토픽/기술 키워드 (1~200자) |
| `limit` | integer | N | 10 | 반환할 전문가 수 (1~50) |

**Response** (`200 OK`) - `ExpertSearchResponse`:

| 필드 | 타입 | 설명 |
|------|------|------|
| `topic` | string | 검색 토픽 |
| `experts` | Expert[] | 전문가 목록 |
| `total` | integer | 검색된 전문가 수 |
| `latency_ms` | number | 검색 소요 시간 (ms) |

**Expert 항목**:

| 필드 | 타입 | 설명 |
|------|------|------|
| `name` | string | 전문가 이름 |
| `expertise` | string[] | 전문 분야 목록 (최대 10개) |
| `score` | number | 관련성 점수 (0~1) |
| `description` | string | 전문가 설명 |
| `related_projects` | string[] | 관련 프로젝트 (최대 5개) |

**curl 예제**:

```bash
curl -s -X POST http://localhost:8000/api/v1/graph/experts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"topic":"클라우드","limit":5}'
```

---

## 6. 임베딩 API

### 6.1 POST /embed

단일 텍스트에 대한 임베딩 벡터를 생성합니다 (BGE-M3 모델).

**인증**: Bearer Token

**Request Body**:

| 필드 | 타입 | 필수 | 설명 |
|------|------|:----:|------|
| `text` | string | Y | 임베딩할 텍스트 (1~10000자) |

**Response** (`200 OK`) - `EmbedResponse`:

| 필드 | 타입 | 설명 |
|------|------|------|
| `embedding` | float[] | Dense 임베딩 벡터 |
| `dimension` | integer | 벡터 차원 (1024) |

**curl 예제**:

```bash
curl -s -X POST http://localhost:8000/api/v1/embed \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text":"프로젝트 관리 방법론"}'
```

### 6.2 POST /embed/batch

여러 텍스트에 대한 배치 임베딩을 수행합니다.

**인증**: Bearer Token

**Request Body**:

| 필드 | 타입 | 필수 | 설명 |
|------|------|:----:|------|
| `texts` | string[] | Y | 임베딩할 텍스트 목록 (1~100개) |

**Response** (`200 OK`) - `EmbedBatchResponse`:

| 필드 | 타입 | 설명 |
|------|------|------|
| `embeddings` | float[][] | 임베딩 벡터 목록 |
| `dimension` | integer | 벡터 차원 (1024) |
| `count` | integer | 처리된 텍스트 수 |

**curl 예제**:

```bash
curl -s -X POST http://localhost:8000/api/v1/embed/batch \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"texts":["프로젝트 관리","품질 보증","테스트 전략"]}'
```

---

## 7. 추출 API

### 7.1 POST /extract/entities

텍스트에서 엔티티 및 관계를 추출합니다 (DeepSeek V3.2 기반, Gleaning 지원).

**인증**: Bearer Token

**Request Body**:

| 필드 | 타입 | 필수 | 기본값 | 설명 |
|------|------|:----:|:------:|------|
| `text` | string | Y | - | 추출 대상 텍스트 (10~50000자) |
| `enable_gleaning` | boolean | N | true | Gleaning 활성화 여부 |
| `document_id` | string | N | null | 문서 ID (선택) |

**Response** (`200 OK`) - `ExtractEntitiesResponse`:

| 필드 | 타입 | 설명 |
|------|------|------|
| `entities` | Entity[] | 추출된 엔티티 목록 |
| `relationships` | Relationship[] | 추출된 관계 목록 |
| `gleaning_passes` | integer | Gleaning 수행 횟수 |
| `entity_count` | integer | 추출된 엔티티 수 |
| `relationship_count` | integer | 추출된 관계 수 |

**curl 예제**:

```bash
curl -s -X POST http://localhost:8000/api/v1/extract/entities \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text":"Kubernetes는 컨테이너 오케스트레이션 플랫폼입니다...","enable_gleaning":true}'
```

### 7.2 POST /extract/metadata

텍스트에서 메타데이터를 추출합니다 (문서 유형, 카테고리, 요약 등).

**인증**: Bearer Token

**Request Body**:

| 필드 | 타입 | 필수 | 설명 |
|------|------|:----:|------|
| `text` | string | Y | 추출 대상 텍스트 (10~50000자) |
| `filename` | string | N | 원본 파일명 (힌트용) |

**Response** (`200 OK`) - `ExtractMetadataResponse`:

| 필드 | 타입 | 설명 |
|------|------|------|
| `metadata` | DocumentMetadata | 추출된 메타데이터 (문서 유형, 프로젝트명, 유효 기간, 카테고리, 핵심 요약) |

**curl 예제**:

```bash
curl -s -X POST http://localhost:8000/api/v1/extract/metadata \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text":"본 문서는 2026년 프로젝트 추진 계획을 기술합니다...","filename":"계획서_v1.0.docx"}'
```

### 7.3 POST /extract/full

엔티티 + 관계 + 메타데이터를 한 번의 요청으로 통합 추출합니다.

**인증**: Bearer Token

**Request Body**:

| 필드 | 타입 | 필수 | 기본값 | 설명 |
|------|------|:----:|:------:|------|
| `text` | string | Y | - | 추출 대상 텍스트 (10~50000자) |
| `enable_gleaning` | boolean | N | true | Gleaning 활성화 여부 |
| `filename` | string | N | null | 원본 파일명 |
| `document_id` | string | N | null | 문서 ID (선택) |

**Response** (`200 OK`) - `FullExtractionResponse`:

| 필드 | 타입 | 설명 |
|------|------|------|
| `entities` | Entity[] | 추출된 엔티티 목록 |
| `relationships` | Relationship[] | 추출된 관계 목록 |
| `metadata` | DocumentMetadata | 추출된 메타데이터 |
| `entity_count` | integer | 추출된 엔티티 수 |
| `relationship_count` | integer | 추출된 관계 수 |

**curl 예제**:

```bash
curl -s -X POST http://localhost:8000/api/v1/extract/full \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text":"Kubernetes 기반 마이크로서비스 아키텍처...","enable_gleaning":true,"filename":"아키텍처_설계서.pdf"}'
```

---

## 8. 캐시 API

### 8.1 GET /cache/stats

캐시 통계를 조회합니다 (히트율, 미스율 등).

**인증**: Bearer Token

**Response** (`200 OK`) - `CacheStatsResponse`:

| 필드 | 타입 | 설명 |
|------|------|------|
| `hits` | integer | 캐시 히트 수 |
| `misses` | integer | 캐시 미스 수 |
| `total_requests` | integer | 총 요청 수 |
| `hit_rate` | number | 캐시 히트율 (0.0~1.0) |
| `miss_rate` | number | 캐시 미스율 (0.0~1.0) |
| `size` | integer | 현재 캐시 크기 (-1: 측정 불가) |
| `max_size` | integer | 최대 캐시 크기 |
| `backend` | string | 캐시 백엔드 유형 |
| `last_reset` | string | 마지막 통계 초기화 시간 |
| `enabled` | boolean | 캐시 활성화 여부 |
| `ttl_seconds` | integer | 기본 TTL (초) |

**curl 예제**:

```bash
curl -s http://localhost:8000/api/v1/cache/stats \
  -H "Authorization: Bearer $TOKEN"
```

**응답 예시**:

```json
{
  "hits": 142,
  "misses": 58,
  "total_requests": 200,
  "hit_rate": 0.71,
  "miss_rate": 0.29,
  "size": 85,
  "max_size": 1000,
  "backend": "redis",
  "last_reset": "2026-02-19T00:00:00Z",
  "enabled": true,
  "ttl_seconds": 3600
}
```

### 8.2 GET /cache/status

캐시 서비스 상태를 확인합니다.

**인증**: Bearer Token

**Response** (`200 OK`) - `CacheStatusResponse`:

| 필드 | 타입 | 설명 |
|------|------|------|
| `enabled` | boolean | 캐시 활성화 여부 |
| `backend` | string | 캐시 백엔드 유형 |
| `status` | string | 상태 (`available`, `disabled`, `error`) |
| `message` | string | 상태 메시지 |

**curl 예제**:

```bash
curl -s http://localhost:8000/api/v1/cache/status \
  -H "Authorization: Bearer $TOKEN"
```

**응답 예시**:

```json
{
  "enabled": true,
  "backend": "redis",
  "status": "available",
  "message": "캐시 서비스 정상 작동 중 (redis)"
}
```

### 8.3 DELETE /cache/clear

전체 캐시를 삭제합니다.

**인증**: Bearer Token

**Response** (`200 OK`) - `CacheClearResponse`:

| 필드 | 타입 | 설명 |
|------|------|------|
| `deleted_count` | integer | 삭제된 캐시 엔트리 수 |
| `message` | string | 결과 메시지 |

**curl 예제**:

```bash
curl -s -X DELETE http://localhost:8000/api/v1/cache/clear \
  -H "Authorization: Bearer $TOKEN"
```

### 8.4 DELETE /cache/invalidate

패턴에 매칭되는 캐시 엔트리를 삭제합니다.

**인증**: Bearer Token

**Query Parameters**:

| 필드 | 타입 | 필수 | 설명 |
|------|------|:----:|------|
| `pattern` | string | N | 삭제할 키 패턴 (예: `prefix*`). 미지정 시 전체 삭제 |

**Response** (`200 OK`) - `CacheInvalidateResponse`:

| 필드 | 타입 | 설명 |
|------|------|------|
| `deleted_count` | integer | 삭제된 캐시 엔트리 수 |
| `pattern` | string | 적용된 패턴 |
| `message` | string | 결과 메시지 |

**curl 예제**:

```bash
curl -s -X DELETE "http://localhost:8000/api/v1/cache/invalidate?pattern=search:*" \
  -H "Authorization: Bearer $TOKEN"
```

### 8.5 POST /cache/stats/reset

캐시 통계 (히트/미스 카운터)를 초기화합니다. 캐시 데이터는 삭제되지 않습니다.

**인증**: Bearer Token

**Response** (`200 OK`):

```json
{
  "success": true,
  "message": "캐시 통계가 초기화되었습니다"
}
```

**curl 예제**:

```bash
curl -s -X POST http://localhost:8000/api/v1/cache/stats/reset \
  -H "Authorization: Bearer $TOKEN"
```

---

## 9. 시스템 API

### 9.1 GET /health

전체 시스템 Health Check를 수행합니다.

**인증**: 불필요

**Response** (`200 OK`) - `HealthResponse`:

| 필드 | 타입 | 설명 |
|------|------|------|
| `status` | string | 서비스 상태 (`healthy`, `degraded`, `unhealthy`) |
| `version` | string | 서비스 버전 |
| `environment` | string | 실행 환경 |
| `timestamp` | string | 체크 시간 (ISO 8601) |
| `dependencies` | object | 의존성 상태 |

**curl 예제**:

```bash
curl -s http://localhost:8000/api/v1/health
```

**응답 예시**:

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "environment": "development",
  "timestamp": "2026-02-19T06:25:21.586289Z",
  "dependencies": {
    "deepseek_api": "healthy",
    "elasticsearch": "healthy",
    "neo4j": "healthy",
    "postgresql": "healthy"
  }
}
```

### 9.2 GET /health/live

Kubernetes Liveness Probe용 엔드포인트입니다.

**인증**: 불필요

**Response** (`200 OK`):

```json
{"status": "alive"}
```

### 9.3 GET /health/ready

Kubernetes Readiness Probe용 엔드포인트입니다.
모든 의존성(ES, Neo4j, PG)이 정상인 경우에만 `ready: true`를 반환합니다.

**인증**: 불필요

**Response** (`200 OK`) - `ReadinessResponse`:

| 필드 | 타입 | 설명 |
|------|------|------|
| `ready` | boolean | 서비스 준비 상태 |
| `checks` | object | 개별 체크 결과 (config_loaded, llm_api_key_set, elasticsearch, neo4j, postgresql) |

### 9.4 GET /health/circuit-breaker

모든 Circuit Breaker의 상태를 조회합니다.

**인증**: 불필요

**Response** (`200 OK`) - `CircuitBreakerAllStatusResponse`:

| 필드 | 타입 | 설명 |
|------|------|------|
| `circuit_breakers` | object | 모든 Circuit Breaker 메트릭 |
| `total_count` | integer | 등록된 Circuit Breaker 수 |
| `healthy_count` | integer | CLOSED 상태인 수 |
| `degraded_count` | integer | OPEN/HALF_OPEN 상태인 수 |

### 9.5 GET /health/circuit-breaker/{name}

특정 Circuit Breaker의 상태를 조회합니다.

**인증**: 불필요

**Response** (`200 OK`) - `CircuitBreakerStatusResponse`:

| 필드 | 타입 | 설명 |
|------|------|------|
| `name` | string | Circuit Breaker 이름 |
| `state` | string | 현재 상태 (closed, open, half_open) |
| `failure_count` | integer | 현재 연속 실패 횟수 |
| `success_count` | integer | HALF_OPEN 상태에서 성공 횟수 |
| `total_calls` | integer | 총 호출 횟수 |
| `total_successes` | integer | 총 성공 횟수 |
| `total_failures` | integer | 총 실패 횟수 |
| `success_rate` | number | 성공률 (%) |
| `last_failure_time` | string | 마지막 실패 시간 (ISO 8601) |
| `last_state_change` | string | 마지막 상태 변경 시간 (ISO 8601) |
| `open_count` | integer | Circuit이 OPEN된 총 횟수 |

**에러**:

| 코드 | 설명 |
|------|------|
| `404` | Circuit Breaker를 찾을 수 없음 |

---

## 엔드포인트 전체 목록

| Method | Path | 인증 | 상태 코드 | 설명 |
|:------:|------|:----:|:---------:|------|
| `POST` | `/auth/login` | - | 200 | 로그인 |
| `POST` | `/auth/refresh` | - | 200 | 토큰 갱신 |
| `POST` | `/auth/logout` | Y | 200 | 로그아웃 |
| `GET` | `/auth/me` | Y | 200 | 현재 사용자 정보 |
| `POST` | `/search/keyword` | Y | 200 | 키워드 검색 |
| `POST` | `/search/semantic` | Y | 200 | 시맨틱 검색 |
| `POST` | `/search/hybrid` | Y | 200 | 하이브리드 검색 |
| `POST` | `/search/chat` | Y | 200 | 대화형 검색 |
| `POST` | `/search/chat/stream` | Y | 200 | 스트리밍 대화형 검색 |
| `GET` | `/search/conversations/{id}` | Y | 200 | 대화 세션 조회 |
| `DELETE` | `/search/conversations/{id}` | Y | 200 | 대화 세션 삭제 |
| `GET` | `/documents` | - | 200 | 문서 목록 조회 |
| `POST` | `/documents/upload` | Y | 201 | 문서 업로드 |
| `GET` | `/documents/{id}/status` | - | 200 | 문서 상태 조회 |
| `GET` | `/documents/{id}/status/stream` | - | 200 | 문서 상태 SSE |
| `POST` | `/documents/{id}/process` | Y | 202 | 문서 처리 트리거 |
| `POST` | `/documents/{id}/retry` | Y | 202 | 실패 문서 재시도 |
| `POST` | `/documents/process-pending` | Y | 202 | 대기 문서 일괄 처리 |
| `GET` | `/documents/{id}/download` | - | 302 | 원본 다운로드 |
| `GET` | `/graph/entities/{name}` | Y | 200 | 엔티티 조회 |
| `POST` | `/graph/subgraph` | Y | 200 | 서브그래프 탐색 |
| `POST` | `/graph/experts` | Y | 200 | 전문가 검색 |
| `POST` | `/embed` | Y | 200 | 단일 임베딩 |
| `POST` | `/embed/batch` | Y | 200 | 배치 임베딩 |
| `POST` | `/extract/entities` | Y | 200 | 엔티티 추출 |
| `POST` | `/extract/metadata` | Y | 200 | 메타데이터 추출 |
| `POST` | `/extract/full` | Y | 200 | 통합 추출 |
| `GET` | `/cache/stats` | Y | 200 | 캐시 통계 |
| `GET` | `/cache/status` | Y | 200 | 캐시 상태 |
| `DELETE` | `/cache/clear` | Y | 200 | 캐시 전체 삭제 |
| `DELETE` | `/cache/invalidate` | Y | 200 | 캐시 무효화 |
| `POST` | `/cache/stats/reset` | Y | 200 | 캐시 통계 초기화 |
| `GET` | `/health` | - | 200 | Health Check |
| `GET` | `/health/live` | - | 200 | Liveness Probe |
| `GET` | `/health/ready` | - | 200 | Readiness Probe |
| `GET` | `/health/circuit-breaker` | - | 200 | Circuit Breaker 전체 |
| `GET` | `/health/circuit-breaker/{name}` | - | 200 | Circuit Breaker 개별 |

---

## 변경 이력

| 날짜 | 버전 | 변경 내용 |
|------|------|----------|
| 2026-02-18 | 1.0 | 최초 작성 |
| 2026-02-19 | 1.1 | 실제 코드 기반 현행화 - 아래 항목 수정 |

### v1.1 변경 상세 (2026-02-19)

1. **인증 정보 수정**: 실제 코드의 `Depends(get_current_user)` 기반으로 인증 필요 여부 정정
   - `/documents/upload`: 불필요 -> **Bearer Token**
   - `/documents/{id}/process`: 불필요 -> **Bearer Token**
   - `/documents/{id}/retry`: 불필요 -> **Bearer Token**
   - `/documents/process-pending`: 불필요 -> **Bearer Token**
   - `/embed`, `/embed/batch`: 불필요 -> **Bearer Token**
   - `/extract/entities`, `/extract/metadata`, `/extract/full`: 불필요 -> **Bearer Token**
2. **문서 목록 API 파라미터 수정**: `limit`/`offset` -> `page`/`page_size` (실제 코드 반영), `format` 필터 추가
3. **문서 업로드 Request 수정**: `source_name`/`doc_type` -> `metadata` (JSON 문자열), 상태 코드 `201 Created`
4. **문서 처리 상태 코드 수정**: `process`, `retry`, `process-pending` -> `202 Accepted`
5. **임베딩/추출 API 분리**: 기존 "임베딩/추출 API" 섹션을 "임베딩 API", "추출 API"로 분리하여 상세화
6. **캐시 API 상세화**: 모든 엔드포인트에 Request/Response 필드 명세 추가, curl 예제 추가
7. **시맨틱 검색 파라미터 차이 명시**: `useGraph`, `useVector` 미지원 주석 추가
8. **에러 코드 추가**: `201`, `202`, `409`, `413` 공통 에러 코드 추가
9. **엔드포인트 전체 목록에 상태 코드 열 추가**
10. **변경 이력 섹션 추가**

---

*작성: Claude Code (Opus 4.6) | 2026-02-19*
