# 통합 API 설계서
## External API (Frontend ↔ Backend) + Internal API (Backend ↔ AI Service)

**버전**: 1.4
**작성일**: 2026-01-16
**수정일**: 2026-01-22
**상태**: Draft
**OpenAPI 버전**: 3.0.3

---

## 문서 정보

| 항목 | 내용 |
|------|------|
| **문서명** | 통합 API 설계서 |
| **버전** | 1.4 |
| **작성일** | 2026-01-16 |
| **작성자** | Claude Code (Opus 4.5) |
| **상태** | Draft |
| **관련 문서** | [상세 설계서](./hybrid_rag_platform_detailed_design.md), [백엔드 구현 계획서](../01_planning/backend_implementation_plan.md), [AI 서비스 구현 계획서](../01_planning/ai_service_implementation_plan.md), [인증/권한 설계서](./authentication_authorization_detailed_design.md), [에러 코드 표준](./error_code_standards.md), [용어사전](./glossary.md) |

---

## 변경 이력

| 버전 | 일자 | 작성자 | 변경 내용 |
|------|------|--------|----------|
| 1.0 | 2026-01-16 | Claude Code | 초안 작성 - External/Internal API 통합 |
| 1.1 | 2026-01-17 | Claude Code | 데이터 타입 규약(UUID, Timestamp) 섹션 추가 |
| 1.2 | 2026-01-17 | Claude Code | 장애 대응 및 Circuit Breaker 섹션 추가 (7.5) |
| 1.3 | 2026-01-22 | Claude Code | 에러 응답 필드명 통일 (requestId → traceId), 에러 코드 통일 |
| 1.4 | 2026-01-22 | Claude Code | API 예시의 chunkId/documentId UUID 형식으로 수정 |

---

## 목차

1. [개요](#1-개요)
2. [아키텍처 개요](#2-아키텍처-개요)
3. [공통 사항](#3-공통-사항)
   - [3.5 데이터 타입 규약](#35-데이터-타입-규약) ← **ID/Timestamp 표준**
4. [Part 1: External API (Frontend ↔ Backend)](#4-part-1-external-api-frontend--backend)
5. [Part 2: Internal API (Backend ↔ AI Service)](#5-part-2-internal-api-backend--ai-service)
6. [Part 3: 공통 스키마](#6-part-3-공통-스키마)
7. [에러 코드 정의](#7-에러-코드-정의)
   - [7.5 장애 대응 및 Circuit Breaker](#75-장애-대응-및-circuit-breaker) ← **Resilience4j 연동**
8. [보안 고려사항](#8-보안-고려사항)
9. [버전 관리 전략](#9-버전-관리-전략)

---

## 1. 개요

### 1.1 목적

본 문서는 사내 지식 검색 시스템의 전체 API를 정의합니다:

- **External API**: Frontend(React)와 Backend(SpringBoot) 간의 REST API
- **Internal API**: Backend(SpringBoot)와 AI Service(FastAPI) 간의 내부 통신 API

### 1.2 범위

| 구분 | 설명 | Base URL |
|------|------|----------|
| **External API** | 외부 클라이언트(Frontend)가 호출하는 API | `/api/v1/*` |
| **Internal API** | Backend 서비스만 호출하는 내부 API | `/internal/v1/*` |

### 1.3 설계 원칙

| 원칙 | 설명 |
|------|------|
| **RESTful** | 리소스 중심 URL, HTTP 메서드 활용 |
| **Stateless** | 서버에 클라이언트 상태 저장 안함 (JWT 토큰 사용) |
| **Versioned** | URL 경로에 버전 포함 (`/api/v1/`) |
| **Consistent** | 일관된 응답 형식 및 에러 처리 |
| **Documented** | OpenAPI 3.0 스펙 준수 |

---

## 2. 아키텍처 개요

### 2.1 API 호출 흐름

```mermaid
sequenceDiagram
    participant F as Frontend<br/>(React)
    participant G as API Gateway<br/>(Spring Cloud)
    participant B as Backend<br/>(SpringBoot)
    participant A as AI Service<br/>(FastAPI)

    F->>G: 1. /api/v1/search

    Note over G: 2. JWT 검증
    Note over G: 3. Rate Limit 체크

    G->>B: 4. 라우팅
    B->>A: 5. /internal/v1/search/hybrid
    A-->>B: 6. 검색 결과
    B-->>G: 7. 응답 반환
    G-->>F: 8. 최종 응답
```

### 2.2 서비스 구성

| 서비스 | 포트 | 역할 | API 유형 |
|--------|------|------|----------|
| **API Gateway** | 8080 | 인증, 라우팅, Rate Limit | - |
| **Backend Service** | 8081 | 비즈니스 로직, CRUD | External |
| **AI Service** | 8000 | 검색, 추출, 임베딩 | Internal |

### 2.3 API 분류

```
External API (Frontend ↔ Backend)
├── /api/v1/auth/*          # 인증
├── /api/v1/knowledge/*     # 지식 관리
├── /api/v1/search/*        # 검색
├── /api/v1/users/*         # 사용자
├── /api/v1/bookmarks/*     # 북마크
├── /api/v1/dashboard/*     # 대시보드
├── /api/v1/export/*        # 내보내기
└── /api/v1/admin/*         # 관리자

Internal API (Backend ↔ AI Service)
├── /internal/v1/search/*   # 검색 파이프라인
├── /internal/v1/extract/*  # 엔티티/메타데이터 추출
├── /internal/v1/embed/*    # 임베딩 생성
├── /internal/v1/parse/*    # 문서 파싱
└── /health                 # 헬스체크
```

---

## 3. 공통 사항

### 3.1 인증

#### 3.1.1 External API 인증

| 항목 | 값 |
|------|-----|
| **방식** | Bearer Token (JWT) |
| **헤더** | `Authorization: Bearer {access_token}` |
| **토큰 발급** | Keycloak OAuth 2.0 + PKCE |

```yaml
# 인증 헤더 예시
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### 3.1.2 Internal API 인증

| 항목 | 값 |
|------|-----|
| **방식** | 내부 네트워크 신뢰 + API Key (선택) |
| **헤더** | `X-Internal-Api-Key: {api_key}` (옵션) |
| **접근 제한** | 내부 네트워크에서만 접근 가능 |

```yaml
# 내부 API 헤더 예시 (선택적)
X-Internal-Api-Key: internal-service-key-xxx
X-Request-Id: uuid-for-tracing
X-User-Id: user-uuid-from-jwt
```

### 3.2 공통 요청 헤더

| 헤더 | 필수 | 설명 |
|------|:----:|------|
| `Content-Type` | ✅ | `application/json` |
| `Accept` | ✅ | `application/json` |
| `Authorization` | ✅* | Bearer Token (*Public 엔드포인트 제외) |
| `Accept-Language` | ❌ | `ko-KR`, `en-US` |
| `X-Request-Id` | ❌ | 요청 추적 ID (UUID) |

### 3.3 공통 응답 형식

#### 3.3.1 성공 응답

```json
{
  "success": true,
  "data": {
    // 응답 데이터
  },
  "message": "요청이 성공적으로 처리되었습니다.",
  "timestamp": "2026-01-16T10:30:00Z",
  "traceId": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### 3.3.2 에러 응답

```json
{
  "success": false,
  "error": {
    "code": "DOC100",
    "message": "요청한 지식을 찾을 수 없습니다.",
    "details": {
      "knowledgeId": "123e4567-e89b-12d3-a456-426614174000"
    }
  },
  "timestamp": "2026-01-16T10:30:00Z",
  "traceId": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### 3.3.3 페이지네이션 응답

```json
{
  "success": true,
  "data": {
    "items": [...],
    "pagination": {
      "page": 1,
      "size": 20,
      "totalPages": 10,
      "totalElements": 195,
      "hasNext": true,
      "hasPrevious": false
    }
  }
}
```

### 3.4 HTTP 상태 코드

| 코드 | 의미 | 사용 상황 |
|------|------|----------|
| `200` | OK | 조회 성공, 수정 성공 |
| `201` | Created | 생성 성공 |
| `202` | Accepted | 비동기 작업 수락 |
| `204` | No Content | 삭제 성공 |
| `400` | Bad Request | 잘못된 요청 파라미터 |
| `401` | Unauthorized | 인증 실패 |
| `403` | Forbidden | 권한 부족 |
| `404` | Not Found | 리소스 없음 |
| `409` | Conflict | 리소스 충돌 |
| `422` | Unprocessable Entity | 유효성 검증 실패 |
| `429` | Too Many Requests | Rate Limit 초과 |
| `500` | Internal Server Error | 서버 오류 |
| `503` | Service Unavailable | 서비스 불가 (AI Service 장애 등) |

### 3.5 데이터 타입 규약

#### 3.5.1 ID 타입 (UUID)

모든 엔티티의 식별자(ID)는 **UUID v4** 형식을 사용합니다.

| 항목 | 형식 | 예시 |
|------|------|------|
| **표준 UUID** | `xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx` | `550e8400-e29b-41d4-a716-446655440000` |
| **길이** | 36자 (하이픈 포함) | - |
| **정규식** | `^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$` | - |

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "authorId": "123e4567-e89b-12d3-a456-426614174000",
  "categoryId": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "projectId": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
}
```

> **참고**: 본 문서의 예시에서는 가독성을 위해 `"k-001"`, `"user-001"` 등 축약 형태를 사용할 수 있으나, 실제 구현에서는 반드시 UUID 형식을 사용합니다.

#### 3.5.2 Timestamp 타입

모든 날짜/시간 필드는 **ISO 8601** 형식을 사용합니다.

| 필드 유형 | 형식 | 예시 | 설명 |
|----------|------|------|------|
| **DateTime** | `YYYY-MM-DDTHH:mm:ssZ` | `"2026-01-17T10:30:00Z"` | UTC 시간대 |
| **Date** | `YYYY-MM-DD` | `"2026-01-17"` | 날짜만 |
| **Unix Timestamp** | 정수 (JWT 전용) | `1705485000` | JWT exp, iat 필드 |

```json
{
  "createdAt": "2026-01-17T10:30:00Z",
  "updatedAt": "2026-01-17T15:45:30Z",
  "validStartDate": "2026-01-01",
  "validEndDate": "2026-12-31"
}
```

#### 3.5.3 ID 타입별 용도

| ID 타입 | 용도 | 생성 방식 |
|---------|------|----------|
| **Entity ID (PK)** | 데이터베이스 레코드 식별 | `UUID.randomUUID()` |
| **Trace ID (X-Request-Id)** | 요청 추적/로깅 | `UUID.randomUUID()` 또는 축약 |
| **Session ID** | 세션/토큰 관리 | Keycloak 생성 UUID |

---

## 4. Part 1: External API (Frontend ↔ Backend)

### 4.1 인증 API (`/api/v1/auth`)

#### 4.1.1 OAuth 2.0 로그인 시작

```yaml
GET /api/v1/auth/login
Description: OAuth 2.0 Authorization Code Flow 시작 (Keycloak 리다이렉트)

Query Parameters:
  - redirect_uri: string (optional) - 로그인 후 리다이렉트 URL

Response (302 Redirect):
  Location: https://keycloak/realms/knowledge/protocol/openid-connect/auth?
    client_id=knowledge-frontend&
    redirect_uri={redirect_uri}&
    response_type=code&
    scope=openid profile email&
    code_challenge={code_challenge}&
    code_challenge_method=S256
```

#### 4.1.2 토큰 교환

```yaml
POST /api/v1/auth/token
Description: Authorization Code를 Access Token으로 교환

Request:
  Content-Type: application/json
  {
    "code": "authorization_code_from_keycloak",
    "codeVerifier": "pkce_code_verifier",
    "redirectUri": "http://localhost:5173/callback"
  }

Response (200 OK):
  {
    "success": true,
    "data": {
      "accessToken": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
      "refreshToken": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
      "tokenType": "Bearer",
      "expiresIn": 900,
      "refreshExpiresIn": 604800,
      "scope": "openid profile email"
    }
  }

Response (401 Unauthorized):
  {
    "success": false,
    "error": {
      "code": "INVALID_AUTH_CODE",
      "message": "유효하지 않은 인증 코드입니다."
    }
  }
```

#### 4.1.3 토큰 갱신

```yaml
POST /api/v1/auth/refresh
Description: Refresh Token으로 새 Access Token 발급

Request:
  Content-Type: application/json
  {
    "refreshToken": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
  }

Response (200 OK):
  {
    "success": true,
    "data": {
      "accessToken": "new_access_token...",
      "refreshToken": "new_refresh_token...",
      "tokenType": "Bearer",
      "expiresIn": 900
    }
  }

Response (401 Unauthorized):
  {
    "success": false,
    "error": {
      "code": "REFRESH_TOKEN_EXPIRED",
      "message": "Refresh Token이 만료되었습니다. 다시 로그인해주세요."
    }
  }
```

#### 4.1.4 로그아웃

```yaml
POST /api/v1/auth/logout
Description: 로그아웃 (토큰 무효화)
Authorization: Bearer {access_token}

Request:
  Content-Type: application/json
  {
    "refreshToken": "current_refresh_token..."
  }

Response (200 OK):
  {
    "success": true,
    "message": "로그아웃되었습니다."
  }
```

#### 4.1.5 현재 사용자 정보

```yaml
GET /api/v1/auth/me
Description: 현재 로그인한 사용자 정보 조회
Authorization: Bearer {access_token}

Response (200 OK):
  {
    "success": true,
    "data": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "user@company.com",
      "name": "홍길동",
      "department": "개발팀",
      "roles": ["USER", "KNOWLEDGE_MANAGER"],
      "profileImage": "https://storage/images/profile.jpg",
      "createdAt": "2026-01-01T00:00:00Z",
      "lastLoginAt": "2026-01-16T09:00:00Z"
    }
  }
```

---

### 4.2 지식 관리 API (`/api/v1/knowledge`)

#### 4.2.1 지식 목록 조회

```yaml
GET /api/v1/knowledge
Description: 지식 목록 조회 (페이지네이션, 필터링, 정렬)
Authorization: Bearer {access_token}

Query Parameters:
  - page: integer (default: 1) - 페이지 번호
  - size: integer (default: 20, max: 100) - 페이지 크기
  - sort: string (default: "createdAt,desc") - 정렬 기준
  - documentType: string (optional) - 문서 유형 필터
  - categoryId: string (optional) - 카테고리 ID
  - projectId: string (optional) - 프로젝트 ID
  - authorId: string (optional) - 작성자 ID
  - status: string (optional) - 상태 (DRAFT, PUBLISHED, ARCHIVED)
  - q: string (optional) - 제목/내용 검색어

Response (200 OK):
  {
    "success": true,
    "data": {
      "items": [
        {
          "id": "550e8400-e29b-41d4-a716-446655440000",
          "title": "React 아키텍처 가이드",
          "summary": "React 기반 프론트엔드 아키텍처 설계 지침",
          "documentType": "기술문서",
          "category": {
            "id": "cat-001",
            "name": "기술 > 프론트엔드"
          },
          "author": {
            "id": "user-001",
            "name": "홍길동",
            "department": "개발팀"
          },
          "project": {
            "id": "proj-001",
            "name": "프로젝트 A"
          },
          "tags": ["React", "TypeScript", "프론트엔드"],
          "status": "PUBLISHED",
          "visibility": "PUBLIC",
          "viewCount": 150,
          "likeCount": 23,
          "commentCount": 5,
          "validStartDate": "2026-01-01",
          "validEndDate": "2027-12-31",
          "createdAt": "2026-01-10T10:00:00Z",
          "updatedAt": "2026-01-15T14:30:00Z"
        }
      ],
      "pagination": {
        "page": 1,
        "size": 20,
        "totalPages": 5,
        "totalElements": 95,
        "hasNext": true,
        "hasPrevious": false
      }
    }
  }
```

#### 4.2.2 지식 상세 조회

```yaml
GET /api/v1/knowledge/{knowledgeId}
Description: 지식 상세 정보 조회
Authorization: Bearer {access_token}

Path Parameters:
  - knowledgeId: string (required) - 지식 ID (UUID)

Response (200 OK):
  {
    "success": true,
    "data": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "React 아키텍처 가이드",
      "content": "# React 아키텍처\n\n## 1. 개요\n...(마크다운 전체 내용)",
      "summary": "React 기반 프론트엔드 아키텍처 설계 지침",
      "documentType": "기술문서",
      "category": {
        "id": "cat-001",
        "level1": "기술",
        "level2": "프론트엔드",
        "level3": null
      },
      "author": {
        "id": "user-001",
        "name": "홍길동",
        "email": "hong@company.com",
        "department": "개발팀",
        "profileImage": "https://storage/images/hong.jpg"
      },
      "project": {
        "id": "proj-001",
        "name": "프로젝트 A",
        "code": "PROJ-A"
      },
      "tags": ["React", "TypeScript", "프론트엔드"],
      "attachments": [
        {
          "id": "file-001",
          "filename": "architecture.pdf",
          "size": 1024000,
          "mimeType": "application/pdf",
          "url": "/api/v1/files/file-001"
        }
      ],
      "metadata": {
        "entities": {
          "persons": ["홍길동", "김철수"],
          "technologies": ["React", "TypeScript", "Redux"]
        },
        "processingStatus": "completed",
        "chunksCount": 15,
        "embeddingStatus": "completed"
      },
      "status": "PUBLISHED",
      "visibility": "PUBLIC",
      "version": 3,
      "viewCount": 151,
      "likeCount": 23,
      "isBookmarked": true,
      "isLiked": false,
      "validStartDate": "2026-01-01",
      "validEndDate": "2027-12-31",
      "createdAt": "2026-01-10T10:00:00Z",
      "updatedAt": "2026-01-15T14:30:00Z",
      "publishedAt": "2026-01-10T12:00:00Z"
    }
  }

Response (404 Not Found):
  {
    "success": false,
    "error": {
      "code": "DOC100",
      "message": "요청한 지식을 찾을 수 없습니다."
    }
  }
```

#### 4.2.3 지식 등록

```yaml
POST /api/v1/knowledge
Description: 새 지식 등록
Authorization: Bearer {access_token}

Request:
  Content-Type: multipart/form-data

  # Form Fields
  - title: string (required, max: 500) - 제목
  - content: string (required) - 본문 (마크다운)
  - documentType: string (optional) - 문서 유형
  - categoryId: string (required) - 카테고리 ID
  - projectId: string (optional) - 프로젝트 ID
  - tags: string[] (optional) - 태그 목록
  - validStartDate: string (optional) - 유효 시작일 (YYYY-MM-DD)
  - validEndDate: string (optional) - 유효 종료일 (YYYY-MM-DD)
  - visibility: string (optional, default: "PUBLIC") - 공개 범위
  - status: string (optional, default: "DRAFT") - 상태 (DRAFT, PUBLISHED)
  - files: File[] (optional) - 첨부 파일

Response (201 Created):
  {
    "success": true,
    "data": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "새로운 지식 제목",
      "status": "DRAFT",
      "processingStatus": "pending",
      "message": "지식이 등록되었습니다. AI 분석이 진행 중입니다."
    },
    "message": "지식이 성공적으로 등록되었습니다."
  }

Response (400 Bad Request):
  {
    "success": false,
    "error": {
      "code": "VALIDATION_ERROR",
      "message": "입력값이 유효하지 않습니다.",
      "details": {
        "title": "제목은 필수 입력 항목입니다.",
        "categoryId": "유효하지 않은 카테고리 ID입니다."
      }
    }
  }
```

#### 4.2.4 지식 수정

```yaml
PUT /api/v1/knowledge/{knowledgeId}
Description: 지식 수정
Authorization: Bearer {access_token}
Required Role: Owner or KNOWLEDGE_MANAGER

Path Parameters:
  - knowledgeId: string (required) - 지식 ID

Request:
  Content-Type: application/json
  {
    "title": "수정된 제목",
    "content": "수정된 내용...",
    "documentType": "기술문서",
    "categoryId": "cat-002",
    "tags": ["React", "TypeScript"],
    "validStartDate": "2026-01-01",
    "validEndDate": "2027-12-31",
    "visibility": "DEPARTMENT"
  }

Response (200 OK):
  {
    "success": true,
    "data": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "수정된 제목",
      "version": 4,
      "processingStatus": "processing",
      "message": "지식이 수정되었습니다. AI 재분석이 진행 중입니다."
    }
  }

Response (403 Forbidden):
  {
    "success": false,
    "error": {
      "code": "ACCESS_DENIED",
      "message": "이 지식을 수정할 권한이 없습니다."
    }
  }
```

#### 4.2.5 지식 삭제

```yaml
DELETE /api/v1/knowledge/{knowledgeId}
Description: 지식 삭제 (소프트 삭제)
Authorization: Bearer {access_token}
Required Role: Owner or KNOWLEDGE_MANAGER

Path Parameters:
  - knowledgeId: string (required) - 지식 ID

Response (204 No Content):
  # 응답 본문 없음

Response (403 Forbidden):
  {
    "success": false,
    "error": {
      "code": "ACCESS_DENIED",
      "message": "이 지식을 삭제할 권한이 없습니다."
    }
  }
```

#### 4.2.6 지식 상태 변경 (발행/보관)

```yaml
PATCH /api/v1/knowledge/{knowledgeId}/status
Description: 지식 상태 변경
Authorization: Bearer {access_token}
Required Role: Owner or KNOWLEDGE_MANAGER

Path Parameters:
  - knowledgeId: string (required) - 지식 ID

Request:
  Content-Type: application/json
  {
    "status": "PUBLISHED"  # DRAFT | PUBLISHED | ARCHIVED
  }

Response (200 OK):
  {
    "success": true,
    "data": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "PUBLISHED",
      "publishedAt": "2026-01-16T10:30:00Z"
    }
  }
```

#### 4.2.7 좋아요 토글

```yaml
POST /api/v1/knowledge/{knowledgeId}/like
Description: 지식 좋아요 토글 (좋아요/취소)
Authorization: Bearer {access_token}

Path Parameters:
  - knowledgeId: string (required) - 지식 ID

Response (200 OK):
  {
    "success": true,
    "data": {
      "knowledgeId": "550e8400-e29b-41d4-a716-446655440000",
      "isLiked": true,
      "likeCount": 24
    }
  }
```

#### 4.2.8 버전 이력 조회

```yaml
GET /api/v1/knowledge/{knowledgeId}/versions
Description: 지식 버전 이력 조회
Authorization: Bearer {access_token}

Path Parameters:
  - knowledgeId: string (required) - 지식 ID

Query Parameters:
  - page: integer (default: 1)
  - size: integer (default: 10)

Response (200 OK):
  {
    "success": true,
    "data": {
      "items": [
        {
          "version": 3,
          "title": "현재 버전 제목",
          "changeType": "CONTENT_UPDATE",
          "changedBy": {
            "id": "user-001",
            "name": "홍길동"
          },
          "changedAt": "2026-01-15T14:30:00Z",
          "changeDescription": "내용 보완 및 오타 수정"
        },
        {
          "version": 2,
          "title": "이전 버전 제목",
          "changeType": "METADATA_UPDATE",
          "changedBy": {
            "id": "user-001",
            "name": "홍길동"
          },
          "changedAt": "2026-01-12T10:00:00Z",
          "changeDescription": "카테고리 변경"
        }
      ],
      "pagination": {
        "page": 1,
        "size": 10,
        "totalPages": 1,
        "totalElements": 3
      }
    }
  }
```

#### 4.2.9 내 지식 목록

```yaml
GET /api/v1/knowledge/my
Description: 내가 작성한 지식 목록 조회
Authorization: Bearer {access_token}

Query Parameters:
  - page: integer (default: 1)
  - size: integer (default: 20)
  - status: string (optional) - 상태 필터
  - sort: string (default: "updatedAt,desc")

Response (200 OK):
  # /api/v1/knowledge와 동일한 응답 형식
```

#### 4.2.10 지식 처리 상태 조회

```yaml
GET /api/v1/knowledge/{knowledgeId}/processing-status
Description: 지식 AI 처리 상태 조회
Authorization: Bearer {access_token}

Path Parameters:
  - knowledgeId: string (required) - 지식 ID

Response (200 OK):
  {
    "success": true,
    "data": {
      "knowledgeId": "550e8400-e29b-41d4-a716-446655440000",
      "status": "processing",  # pending | processing | completed | failed
      "progress": {
        "chunking": "completed",
        "entityExtraction": "processing",
        "embeddingGeneration": "pending",
        "indexing": "pending"
      },
      "chunksCount": 15,
      "entitiesCount": 8,
      "error": null,
      "startedAt": "2026-01-16T10:30:00Z",
      "estimatedCompletion": "2026-01-16T10:32:00Z"
    }
  }
```

---

### 4.3 검색 API (`/api/v1/search`)

#### 4.3.1 Hybrid 검색

```yaml
POST /api/v1/search
Description: Hybrid 검색 (Vector + Graph)
Authorization: Bearer {access_token}

Request:
  Content-Type: application/json
  {
    "query": "2024년 프로젝트 A의 React 아키텍처는?",
    "filters": {
      "projectName": "프로젝트 A",
      "documentType": "기술문서",
      "dateRange": {
        "start": "2024-01-01",
        "end": "2024-12-31"
      },
      "categories": {
        "level1": "기술",
        "level2": "프론트엔드"
      },
      "author": "홍길동",
      "tags": ["React"]
    },
    "searchType": "hybrid",  # vector | graph | hybrid (default)
    "topK": 10,
    "includeAnswer": true,
    "includeGraphContext": true
  }

Response (200 OK):
  {
    "success": true,
    "data": {
      "query": "2024년 프로젝트 A의 React 아키텍처는?",
      "answer": "프로젝트 A의 React 아키텍처는 Atomic Design 패턴을 기반으로 ...",
      "results": [
        {
          "id": "550e8400-e29b-41d4-a716-446655440001",
          "knowledgeId": "550e8400-e29b-41d4-a716-446655440010",
          "title": "프로젝트 A 기술 문서",
          "text": "React 아키텍처는 컴포넌트 기반 설계로...",
          "score": 0.92,
          "highlightedText": "React <mark>아키텍처</mark>는 컴포넌트 기반...",
          "metadata": {
            "documentType": "기술문서",
            "projectName": "프로젝트 A",
            "author": "홍길동",
            "validStartDate": "2024-01-01",
            "validEndDate": "2025-12-31",
            "categories": {
              "level1": "기술",
              "level2": "프론트엔드"
            },
            "summary": "React 기반 프론트엔드 아키텍처 설계 가이드"
          },
          "graphContext": {
            "relatedEntities": [
              {"name": "홍길동", "type": "Person"},
              {"name": "React", "type": "Technology"},
              {"name": "TypeScript", "type": "Technology"}
            ],
            "community": "프론트엔드 개발팀"
          }
        }
      ],
      "searchMetadata": {
        "searchType": "hybrid",
        "totalResults": 10,
        "vectorResultsCount": 8,
        "graphResultsCount": 5,
        "fusionMethod": "rrf",
        "latencyMs": 450
      },
      "sources": [
        {
          "knowledgeId": "knowledge-001",
          "title": "프로젝트 A 기술 문서",
          "author": "홍길동"
        }
      ]
    }
  }
```

#### 4.3.2 채팅 검색 (스트리밍)

```yaml
POST /api/v1/search/chat
Description: 대화형 검색 (SSE 스트리밍)
Authorization: Bearer {access_token}

Request:
  Content-Type: application/json
  {
    "query": "React와 Vue의 차이점은?",
    "conversationId": "conv-001",  # 새 대화면 null
    "history": [  # 이전 대화 컨텍스트
      {
        "role": "user",
        "content": "프론트엔드 프레임워크에 대해 알려줘"
      },
      {
        "role": "assistant",
        "content": "프론트엔드 프레임워크는..."
      }
    ],
    "filters": {
      "documentType": "기술문서"
    }
  }

Response (200 OK - SSE Stream):
  Content-Type: text/event-stream

  # 토큰 스트리밍
  data: {"type": "token", "content": "React"}
  data: {"type": "token", "content": "와 "}
  data: {"type": "token", "content": "Vue"}
  data: {"type": "token", "content": "의 "}
  ...

  # 소스 문서
  data: {"type": "sources", "content": [{"knowledgeId": "k-001", "title": "프레임워크 비교"}]}

  # 완료
  data: {"type": "done", "conversationId": "conv-001"}
```

#### 4.3.3 대화 이력 조회

```yaml
GET /api/v1/search/conversations/{conversationId}
Description: 특정 대화 이력 조회
Authorization: Bearer {access_token}

Path Parameters:
  - conversationId: string (required) - 대화 ID

Response (200 OK):
  {
    "success": true,
    "data": {
      "id": "conv-001",
      "title": "React와 Vue 비교",
      "messages": [
        {
          "id": "msg-001",
          "role": "user",
          "content": "React와 Vue의 차이점은?",
          "timestamp": "2026-01-16T10:30:00Z"
        },
        {
          "id": "msg-002",
          "role": "assistant",
          "content": "React와 Vue의 주요 차이점은...",
          "sources": [
            {"knowledgeId": "k-001", "title": "프레임워크 비교"}
          ],
          "timestamp": "2026-01-16T10:30:05Z"
        }
      ],
      "createdAt": "2026-01-16T10:30:00Z",
      "updatedAt": "2026-01-16T10:30:05Z"
    }
  }
```

#### 4.3.4 내 대화 목록

```yaml
GET /api/v1/search/conversations
Description: 내 대화 목록 조회
Authorization: Bearer {access_token}

Query Parameters:
  - page: integer (default: 1)
  - size: integer (default: 20)

Response (200 OK):
  {
    "success": true,
    "data": {
      "items": [
        {
          "id": "conv-001",
          "title": "React와 Vue 비교",
          "lastMessage": "React와 Vue의 주요 차이점은...",
          "messageCount": 4,
          "createdAt": "2026-01-16T10:30:00Z",
          "updatedAt": "2026-01-16T10:35:00Z"
        }
      ],
      "pagination": {...}
    }
  }
```

#### 4.3.5 대화 삭제

```yaml
DELETE /api/v1/search/conversations/{conversationId}
Description: 대화 삭제
Authorization: Bearer {access_token}

Response (204 No Content)
```

#### 4.3.6 검색어 자동완성

```yaml
GET /api/v1/search/suggestions
Description: 검색어 자동완성 제안
Authorization: Bearer {access_token}

Query Parameters:
  - q: string (required) - 검색어 prefix
  - limit: integer (default: 5, max: 10)

Response (200 OK):
  {
    "success": true,
    "data": {
      "suggestions": [
        "React 아키텍처",
        "React 성능 최적화",
        "React Hook 사용법"
      ]
    }
  }
```

#### 4.3.7 전문가 찾기

```yaml
POST /api/v1/search/experts
Description: 특정 주제의 전문가 검색
Authorization: Bearer {access_token}

Request:
  Content-Type: application/json
  {
    "topic": "React",
    "depth": 2,
    "limit": 5
  }

Response (200 OK):
  {
    "success": true,
    "data": {
      "topic": "React",
      "experts": [
        {
          "id": "user-001",
          "name": "홍길동",
          "department": "개발팀",
          "email": "hong@company.com",
          "profileImage": "https://...",
          "relevanceScore": 0.95,
          "relatedDocuments": 12,
          "expertiseAreas": ["React", "TypeScript", "프론트엔드"]
        }
      ]
    }
  }
```

---

### 4.4 사용자 API (`/api/v1/users`)

#### 4.4.1 내 프로필 조회

```yaml
GET /api/v1/users/me
Description: 현재 사용자 프로필 조회
Authorization: Bearer {access_token}

Response (200 OK):
  {
    "success": true,
    "data": {
      "id": "user-001",
      "email": "user@company.com",
      "name": "홍길동",
      "department": "개발팀",
      "position": "선임개발자",
      "profileImage": "https://storage/images/profile.jpg",
      "roles": ["USER", "KNOWLEDGE_MANAGER"],
      "preferences": {
        "language": "ko-KR",
        "theme": "light",
        "emailNotification": true,
        "searchResultSize": 20
      },
      "stats": {
        "knowledgeCount": 15,
        "searchCount": 234,
        "bookmarkCount": 45
      },
      "createdAt": "2026-01-01T00:00:00Z",
      "lastLoginAt": "2026-01-16T09:00:00Z"
    }
  }
```

#### 4.4.2 프로필 수정

```yaml
PUT /api/v1/users/me
Description: 프로필 정보 수정
Authorization: Bearer {access_token}

Request:
  Content-Type: multipart/form-data
  - name: string (optional) - 이름
  - department: string (optional) - 부서
  - position: string (optional) - 직책
  - profileImage: File (optional) - 프로필 이미지

Response (200 OK):
  {
    "success": true,
    "data": {
      "id": "user-001",
      "name": "홍길동",
      "department": "개발팀",
      "position": "책임개발자",
      "profileImage": "https://storage/images/new-profile.jpg"
    }
  }
```

#### 4.4.3 사용자 설정 수정

```yaml
PUT /api/v1/users/me/preferences
Description: 사용자 설정 수정
Authorization: Bearer {access_token}

Request:
  Content-Type: application/json
  {
    "language": "ko-KR",
    "theme": "dark",
    "emailNotification": false,
    "searchResultSize": 30
  }

Response (200 OK):
  {
    "success": true,
    "data": {
      "language": "ko-KR",
      "theme": "dark",
      "emailNotification": false,
      "searchResultSize": 30
    }
  }
```

#### 4.4.4 검색 기록 조회

```yaml
GET /api/v1/users/me/search-history
Description: 내 검색 기록 조회
Authorization: Bearer {access_token}

Query Parameters:
  - page: integer (default: 1)
  - size: integer (default: 20)

Response (200 OK):
  {
    "success": true,
    "data": {
      "items": [
        {
          "id": "sh-001",
          "query": "React 아키텍처",
          "searchType": "hybrid",
          "resultCount": 15,
          "searchedAt": "2026-01-16T10:30:00Z"
        }
      ],
      "pagination": {...}
    }
  }
```

#### 4.4.5 검색 기록 삭제

```yaml
DELETE /api/v1/users/me/search-history
Description: 검색 기록 전체 삭제
Authorization: Bearer {access_token}

Response (204 No Content)
```

#### 4.4.6 사용자 검색 (관리자)

```yaml
GET /api/v1/users
Description: 사용자 목록 조회
Authorization: Bearer {access_token}
Required Role: ADMIN

Query Parameters:
  - page: integer (default: 1)
  - size: integer (default: 20)
  - q: string (optional) - 이름/이메일 검색
  - department: string (optional) - 부서 필터
  - role: string (optional) - 역할 필터

Response (200 OK):
  {
    "success": true,
    "data": {
      "items": [
        {
          "id": "user-001",
          "email": "user@company.com",
          "name": "홍길동",
          "department": "개발팀",
          "roles": ["USER"],
          "status": "ACTIVE",
          "lastLoginAt": "2026-01-16T09:00:00Z"
        }
      ],
      "pagination": {...}
    }
  }
```

---

### 4.5 북마크 API (`/api/v1/bookmarks`)

#### 4.5.1 북마크 목록 조회

```yaml
GET /api/v1/bookmarks
Description: 내 북마크 목록 조회
Authorization: Bearer {access_token}

Query Parameters:
  - page: integer (default: 1)
  - size: integer (default: 20)
  - folderId: string (optional) - 폴더 ID 필터

Response (200 OK):
  {
    "success": true,
    "data": {
      "items": [
        {
          "id": "bm-001",
          "knowledge": {
            "id": "k-001",
            "title": "React 아키텍처 가이드",
            "summary": "React 기반 프론트엔드...",
            "author": {"name": "홍길동"},
            "documentType": "기술문서"
          },
          "folder": {
            "id": "folder-001",
            "name": "프론트엔드"
          },
          "note": "나중에 다시 읽기",
          "createdAt": "2026-01-15T10:00:00Z"
        }
      ],
      "pagination": {...}
    }
  }
```

#### 4.5.2 북마크 추가

```yaml
POST /api/v1/bookmarks
Description: 북마크 추가
Authorization: Bearer {access_token}

Request:
  Content-Type: application/json
  {
    "knowledgeId": "k-001",
    "folderId": "folder-001",  # optional
    "note": "중요한 내용"       # optional
  }

Response (201 Created):
  {
    "success": true,
    "data": {
      "id": "bm-001",
      "knowledgeId": "k-001",
      "folderId": "folder-001"
    }
  }
```

#### 4.5.3 북마크 삭제

```yaml
DELETE /api/v1/bookmarks/{bookmarkId}
Description: 북마크 삭제
Authorization: Bearer {access_token}

Path Parameters:
  - bookmarkId: string (required) - 북마크 ID

Response (204 No Content)
```

#### 4.5.4 폴더 목록 조회

```yaml
GET /api/v1/bookmarks/folders
Description: 북마크 폴더 목록 조회
Authorization: Bearer {access_token}

Response (200 OK):
  {
    "success": true,
    "data": {
      "folders": [
        {
          "id": "folder-001",
          "name": "프론트엔드",
          "bookmarkCount": 12,
          "createdAt": "2026-01-10T10:00:00Z"
        }
      ]
    }
  }
```

#### 4.5.5 폴더 생성

```yaml
POST /api/v1/bookmarks/folders
Description: 북마크 폴더 생성
Authorization: Bearer {access_token}

Request:
  Content-Type: application/json
  {
    "name": "백엔드"
  }

Response (201 Created):
  {
    "success": true,
    "data": {
      "id": "folder-002",
      "name": "백엔드"
    }
  }
```

#### 4.5.6 폴더 삭제

```yaml
DELETE /api/v1/bookmarks/folders/{folderId}
Description: 북마크 폴더 삭제 (북마크는 미분류로 이동)
Authorization: Bearer {access_token}

Path Parameters:
  - folderId: string (required) - 폴더 ID

Response (204 No Content)
```

---

### 4.6 대시보드 API (`/api/v1/dashboard`)

#### 4.6.1 대시보드 데이터 조회

```yaml
GET /api/v1/dashboard
Description: 대시보드 종합 데이터 조회
Authorization: Bearer {access_token}

Response (200 OK):
  {
    "success": true,
    "data": {
      "summary": {
        "totalKnowledge": 1250,
        "totalUsers": 150,
        "todaySearches": 342,
        "todayUploads": 12
      },
      "recentActivity": [
        {
          "type": "KNOWLEDGE_CREATED",
          "knowledgeId": "k-001",
          "title": "새로운 문서",
          "user": {"name": "홍길동"},
          "timestamp": "2026-01-16T10:00:00Z"
        }
      ],
      "popularKnowledge": [...],
      "trendingSearches": [...]
    }
  }
```

#### 4.6.2 인기 지식 조회

```yaml
GET /api/v1/dashboard/popular
Description: 인기 지식 목록 조회
Authorization: Bearer {access_token}

Query Parameters:
  - period: string (default: "week") - 기간 (day, week, month)
  - limit: integer (default: 10)

Response (200 OK):
  {
    "success": true,
    "data": {
      "period": "week",
      "items": [
        {
          "id": "k-001",
          "title": "React 아키텍처 가이드",
          "author": {"name": "홍길동"},
          "viewCount": 450,
          "likeCount": 32,
          "trend": "up"  # up, down, stable
        }
      ]
    }
  }
```

#### 4.6.3 검색 트렌드 조회

```yaml
GET /api/v1/dashboard/trends
Description: 검색어 트렌드 조회
Authorization: Bearer {access_token}

Query Parameters:
  - period: string (default: "week")
  - limit: integer (default: 10)

Response (200 OK):
  {
    "success": true,
    "data": {
      "period": "week",
      "trends": [
        {
          "keyword": "React",
          "count": 156,
          "changePercent": 23.5
        }
      ]
    }
  }
```

#### 4.6.4 통계 조회

```yaml
GET /api/v1/dashboard/stats
Description: 상세 통계 조회
Authorization: Bearer {access_token}

Query Parameters:
  - period: string (default: "month") - 기간
  - groupBy: string (default: "day") - 그룹핑 (day, week, month)

Response (200 OK):
  {
    "success": true,
    "data": {
      "period": "month",
      "groupBy": "day",
      "knowledgeStats": {
        "total": 1250,
        "created": [
          {"date": "2026-01-15", "count": 5},
          {"date": "2026-01-16", "count": 12}
        ],
        "byDocumentType": [
          {"type": "기술문서", "count": 450},
          {"type": "업무매뉴얼", "count": 320}
        ]
      },
      "searchStats": {
        "total": 5420,
        "daily": [
          {"date": "2026-01-15", "count": 342},
          {"date": "2026-01-16", "count": 298}
        ],
        "averageLatency": 450
      },
      "userStats": {
        "totalUsers": 150,
        "activeUsers": 89,
        "newUsers": 5
      }
    }
  }
```

---

### 4.7 내보내기 API (`/api/v1/export`)

#### 4.7.1 Excel 내보내기

```yaml
POST /api/v1/export/excel
Description: 검색 결과를 Excel로 내보내기
Authorization: Bearer {access_token}

Request:
  Content-Type: application/json
  {
    "knowledgeIds": ["k-001", "k-002", "k-003"],
    "columns": ["title", "author", "documentType", "createdAt", "summary"]
  }

Response (200 OK):
  Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
  Content-Disposition: attachment; filename="knowledge_export_20260116.xlsx"

  # Binary file content
```

#### 4.7.2 PDF 내보내기

```yaml
POST /api/v1/export/pdf
Description: 지식을 PDF로 내보내기
Authorization: Bearer {access_token}

Request:
  Content-Type: application/json
  {
    "knowledgeId": "k-001",
    "includeMetadata": true,
    "includeComments": false
  }

Response (200 OK):
  Content-Type: application/pdf
  Content-Disposition: attachment; filename="knowledge_k-001.pdf"

  # Binary file content
```

---

### 4.8 관리자 API (`/api/v1/admin`)

#### 4.8.1 시스템 상태 조회

```yaml
GET /api/v1/admin/health
Description: 시스템 전체 상태 조회
Authorization: Bearer {access_token}
Required Role: ADMIN

Response (200 OK):
  {
    "success": true,
    "data": {
      "status": "healthy",
      "components": {
        "postgresql": {
          "status": "healthy",
          "latencyMs": 5,
          "connections": {"active": 10, "max": 100}
        },
        "elasticsearch": {
          "status": "healthy",
          "latencyMs": 12,
          "indices": {"count": 3, "docsCount": 15000}
        },
        "neo4j": {
          "status": "healthy",
          "latencyMs": 8,
          "nodes": 5000,
          "relationships": 12000
        },
        "redis": {
          "status": "healthy",
          "latencyMs": 2,
          "memory": {"used": "256MB", "max": "1GB"}
        },
        "aiService": {
          "status": "healthy",
          "latencyMs": 150,
          "version": "1.0.0"
        }
      },
      "system": {
        "cpu": {"usage": 45.5},
        "memory": {"total": "16GB", "used": "12.5GB", "percentage": 78},
        "disk": {"total": "500GB", "used": "120GB", "percentage": 24}
      },
      "timestamp": "2026-01-16T10:30:00Z"
    }
  }
```

#### 4.8.2 재인덱싱 요청

```yaml
POST /api/v1/admin/reindex
Description: Elasticsearch/Neo4j 재인덱싱
Authorization: Bearer {access_token}
Required Role: ADMIN

Request:
  Content-Type: application/json
  {
    "target": "all",  # all | elasticsearch | neo4j
    "force": false,
    "batchSize": 100
  }

Response (202 Accepted):
  {
    "success": true,
    "data": {
      "jobId": "job-001",
      "status": "started",
      "target": "all",
      "estimatedDocuments": 15000,
      "message": "재인덱싱 작업이 시작되었습니다."
    }
  }
```

#### 4.8.3 재인덱싱 상태 조회

```yaml
GET /api/v1/admin/reindex/{jobId}
Description: 재인덱싱 작업 상태 조회
Authorization: Bearer {access_token}
Required Role: ADMIN

Path Parameters:
  - jobId: string (required) - 작업 ID

Response (200 OK):
  {
    "success": true,
    "data": {
      "jobId": "job-001",
      "status": "running",  # pending | running | completed | failed
      "progress": {
        "total": 15000,
        "processed": 7500,
        "percentage": 50
      },
      "startedAt": "2026-01-16T10:30:00Z",
      "estimatedCompletion": "2026-01-16T11:00:00Z"
    }
  }
```

#### 4.8.4 사용자 역할 변경

```yaml
PUT /api/v1/admin/users/{userId}/role
Description: 사용자 역할 변경
Authorization: Bearer {access_token}
Required Role: ADMIN

Path Parameters:
  - userId: string (required) - 사용자 ID

Request:
  Content-Type: application/json
  {
    "roles": ["USER", "KNOWLEDGE_MANAGER"]
  }

Response (200 OK):
  {
    "success": true,
    "data": {
      "userId": "user-001",
      "roles": ["USER", "KNOWLEDGE_MANAGER"]
    }
  }
```

#### 4.8.5 카테고리 관리

```yaml
GET /api/v1/admin/categories
Description: 카테고리 목록 조회
Authorization: Bearer {access_token}
Required Role: ADMIN

Response (200 OK):
  {
    "success": true,
    "data": {
      "categories": [
        {
          "id": "cat-001",
          "name": "기술",
          "level": 1,
          "children": [
            {
              "id": "cat-002",
              "name": "프론트엔드",
              "level": 2,
              "children": []
            }
          ]
        }
      ]
    }
  }
```

```yaml
POST /api/v1/admin/categories
Description: 카테고리 생성
Authorization: Bearer {access_token}
Required Role: ADMIN

Request:
  Content-Type: application/json
  {
    "name": "백엔드",
    "parentId": "cat-001"
  }

Response (201 Created):
  {
    "success": true,
    "data": {
      "id": "cat-003",
      "name": "백엔드",
      "level": 2,
      "parentId": "cat-001"
    }
  }
```

---

## 5. Part 2: Internal API (Backend ↔ AI Service)

> **중요**: Internal API는 Backend(SpringBoot)에서만 호출합니다. 외부(Frontend, Gateway)에서 직접 호출할 수 없습니다.

### 5.1 헬스체크

```yaml
GET /health
Description: AI Service 상태 확인

Response (200 OK):
  {
    "status": "healthy",
    "version": "1.0.0",
    "components": {
      "elasticsearch": "healthy",
      "neo4j": "healthy",
      "deepseek": "healthy",
      "embedding_model": "loaded"
    },
    "uptime": "2d 5h 30m"
  }
```

```yaml
GET /health/ready
Description: AI Service 준비 상태 확인 (모든 모델 로드 완료 여부)

Response (200 OK):
  {
    "ready": true,
    "embedding_model": "loaded",
    "llm_client": "connected"
  }

Response (503 Service Unavailable):
  {
    "ready": false,
    "embedding_model": "loading",
    "llm_client": "connected"
  }
```

---

### 5.2 검색 API (`/internal/v1/search`)

#### 5.2.1 Hybrid 검색 (VIP 파이프라인)

```yaml
POST /internal/v1/search/hybrid
Description: Vector + Graph Hybrid 검색 실행
Content-Type: application/json

Request Headers:
  X-Request-Id: string - 요청 추적 ID
  X-User-Id: string - 사용자 ID (권한 필터링용)

Request:
  {
    "query": "2024년 프로젝트 A의 React 아키텍처는?",
    "filters": {
      "projectName": "프로젝트 A",
      "documentType": "기술문서",
      "dateRange": {
        "start": "2024-01-01",
        "end": "2024-12-31"
      },
      "categories": {
        "level1": "기술"
      }
    },
    "searchType": "hybrid",
    "topK": 10,
    "includeAnswer": true,
    "includeGraphContext": true,
    "userId": "user-001"
  }

Response (200 OK):
  {
    "success": true,
    "data": {
      "query": "2024년 프로젝트 A의 React 아키텍처는?",
      "intentAnalysis": {
        "intent": "fact_retrieval",
        "timeConstraints": {
          "startDate": "2024-01-01",
          "endDate": "2024-12-31"
        },
        "entityFilters": {
          "projectName": "프로젝트 A"
        },
        "searchStrategy": "hybrid",
        "complexity": "simple"
      },
      "answer": "프로젝트 A의 React 아키텍처는 Atomic Design 패턴을 기반으로...",
      "results": [
        {
          "chunkId": "550e8400-e29b-41d4-a716-446655440001",
          "documentId": "550e8400-e29b-41d4-a716-446655440010",
          "text": "React 아키텍처는 컴포넌트 기반 설계로...",
          "score": 0.92,
          "vectorScore": 0.88,
          "graphScore": 0.95,
          "metadata": {
            "title": "프로젝트 A 기술 문서",
            "documentType": "기술문서",
            "projectName": "프로젝트 A",
            "author": "홍길동",
            "validStartDate": "2024-01-01",
            "validEndDate": "2025-12-31",
            "summary": "React 기반 아키텍처 설계 가이드"
          },
          "graphContext": {
            "relatedEntities": [
              {"id": "e-001", "name": "홍길동", "type": "Person"},
              {"id": "e-002", "name": "React", "type": "Technology"}
            ],
            "paths": [
              ["홍길동", "CREATED", "프로젝트 A 기술 문서"],
              ["React", "MENTIONED_IN", "프로젝트 A 기술 문서"]
            ],
            "community": {
              "id": "comm-001",
              "name": "프론트엔드 개발팀",
              "summary": "React/TypeScript 기반 프론트엔드 기술 커뮤니티"
            }
          }
        }
      ],
      "searchMetadata": {
        "searchType": "hybrid",
        "vectorResultsCount": 8,
        "graphResultsCount": 5,
        "fusionMethod": "rrf",
        "stages": {
          "intentAnalysis": {"latencyMs": 120, "model": "deepseek-chat"},
          "vectorSearch": {"latencyMs": 45},
          "graphSearch": {"latencyMs": 35},
          "fusion": {"latencyMs": 5},
          "answerSynthesis": {"latencyMs": 200, "model": "deepseek-chat"}
        },
        "totalLatencyMs": 405,
        "tokenUsage": {
          "input": 1250,
          "output": 350,
          "cost": 0.0004
        }
      }
    }
  }

Response (400 Bad Request):
  {
    "success": false,
    "error": {
      "code": "INVALID_QUERY",
      "message": "검색어가 유효하지 않습니다."
    }
  }

Response (503 Service Unavailable):
  {
    "success": false,
    "error": {
      "code": "AI_SERVICE_UNAVAILABLE",
      "message": "AI 서비스를 일시적으로 사용할 수 없습니다.",
      "details": {
        "component": "deepseek",
        "reason": "rate_limit_exceeded"
      }
    }
  }
```

#### 5.2.2 채팅 검색 (스트리밍)

```yaml
POST /internal/v1/search/chat/stream
Description: 대화형 검색 (SSE 스트리밍)
Content-Type: application/json
Accept: text/event-stream

Request:
  {
    "query": "React와 Vue의 차이점은?",
    "conversationId": "conv-001",
    "history": [
      {"role": "user", "content": "프론트엔드 프레임워크에 대해 알려줘"},
      {"role": "assistant", "content": "프론트엔드 프레임워크는..."}
    ],
    "filters": {},
    "userId": "user-001"
  }

Response (200 OK - SSE Stream):
  Content-Type: text/event-stream

  event: intent
  data: {"intent": "comparison", "entities": ["React", "Vue"]}

  event: search_start
  data: {"message": "관련 문서를 검색 중..."}

  event: search_complete
  data: {"resultsCount": 5}

  event: token
  data: {"content": "React"}

  event: token
  data: {"content": "와 "}

  event: token
  data: {"content": "Vue"}

  event: token
  data: {"content": "의 "}

  ...

  event: sources
  data: {"sources": [{"id": "doc-001", "title": "프레임워크 비교"}]}

  event: usage
  data: {"inputTokens": 500, "outputTokens": 200, "cost": 0.0002}

  event: done
  data: {"conversationId": "conv-001", "messageId": "msg-003"}
```

#### 5.2.3 Vector 검색만 실행

```yaml
POST /internal/v1/search/vector
Description: Elasticsearch Vector 검색만 실행
Content-Type: application/json

Request:
  {
    "query": "React 컴포넌트 설계",
    "queryVector": [0.123, 0.456, ...],  # optional (없으면 내부에서 생성)
    "filters": {
      "documentType": "기술문서"
    },
    "topK": 10
  }

Response (200 OK):
  {
    "success": true,
    "data": {
      "results": [
        {
          "chunkId": "550e8400-e29b-41d4-a716-446655440001",
          "documentId": "550e8400-e29b-41d4-a716-446655440010",
          "text": "...",
          "score": 0.92,
          "metadata": {...}
        }
      ],
      "latencyMs": 45
    }
  }
```

#### 5.2.4 Graph 검색만 실행

```yaml
POST /internal/v1/search/graph
Description: Neo4j Graph 탐색만 실행
Content-Type: application/json

Request:
  {
    "query": "React 관련 전문가",
    "entityName": "React",
    "traversalDepth": 2,
    "relationshipTypes": ["CREATED", "USES", "RELATED_TO"],
    "limit": 10
  }

Response (200 OK):
  {
    "success": true,
    "data": {
      "entities": [
        {
          "id": "e-001",
          "name": "홍길동",
          "type": "Person",
          "properties": {"department": "개발팀"},
          "relatedDocuments": 12,
          "path": ["React", "USES", "홍길동"]
        }
      ],
      "communities": [
        {
          "id": "comm-001",
          "name": "프론트엔드 개발팀",
          "memberCount": 15
        }
      ],
      "latencyMs": 35
    }
  }
```

---

### 5.3 추출 API (`/internal/v1/extract`)

#### 5.3.1 엔티티 추출

```yaml
POST /internal/v1/extract/entities
Description: 텍스트에서 엔티티 및 관계 추출
Content-Type: application/json

Request:
  {
    "text": "홍길동이 React와 TypeScript로 프로젝트 A를 개발했습니다.",
    "documentId": "550e8400-e29b-41d4-a716-446655440010",
    "chunkId": "550e8400-e29b-41d4-a716-446655440001",
    "options": {
      "extractRelationships": true,
      "entityTypes": ["Person", "Project", "Technology", "Organization"],
      "enableGleaning": true,       // Gleaning 활성화 여부 (기본값: false)
      "maxGleanings": 1             // 최대 Gleaning 횟수 (기본값: 1)
    }
  }

Response (200 OK):
  {
    "success": true,
    "data": {
      "entities": [
        {
          "id": "e-001",
          "name": "홍길동",
          "type": "Person",
          "confidence": 0.95,
          "positions": [{"start": 0, "end": 3}]
        },
        {
          "id": "e-002",
          "name": "React",
          "type": "Technology",
          "confidence": 0.98,
          "positions": [{"start": 5, "end": 10}]
        },
        {
          "id": "e-003",
          "name": "TypeScript",
          "type": "Technology",
          "confidence": 0.97,
          "positions": [{"start": 12, "end": 22}]
        },
        {
          "id": "e-004",
          "name": "프로젝트 A",
          "type": "Project",
          "confidence": 0.92,
          "positions": [{"start": 24, "end": 31}]
        }
      ],
      "relationships": [
        {
          "source": "홍길동",
          "target": "프로젝트 A",
          "type": "CREATED",
          "confidence": 0.90
        },
        {
          "source": "프로젝트 A",
          "target": "React",
          "type": "USES",
          "confidence": 0.95
        },
        {
          "source": "프로젝트 A",
          "target": "TypeScript",
          "type": "USES",
          "confidence": 0.95
        }
      ],
      "processingMetadata": {
        "model": "deepseek-chat",
        "latencyMs": 150,
        "tokenUsage": {"input": 200, "output": 150},
        "gleaningPasses": 1           // 수행된 Gleaning 횟수 (0=비활성화)
      }
    }
  }
```

#### 5.3.2 메타데이터 생성

```yaml
POST /internal/v1/extract/metadata
Description: 텍스트에서 메타데이터 자동 생성
Content-Type: application/json

Request:
  {
    "text": "본 문서는 2024년 프로젝트 A의 React 기반 프론트엔드 아키텍처를 설명합니다...",
    "documentId": "doc-001",
    "filename": "프로젝트A_아키텍처.pdf"
  }

Response (200 OK):
  {
    "success": true,
    "data": {
      "documentType": "기술문서",
      "categories": {
        "level1": "기술",
        "level2": "프론트엔드",
        "level3": "아키텍처"
      },
      "projectName": "프로젝트 A",
      "validStartDate": "2024-01-01",
      "validEndDate": "2025-12-31",
      "summary": "프로젝트 A의 React 기반 프론트엔드 아키텍처 설계 가이드",
      "suggestedTags": ["React", "아키텍처", "프론트엔드", "프로젝트 A"],
      "language": "ko",
      "confidence": {
        "documentType": 0.92,
        "categories": 0.88,
        "projectName": 0.95
      },
      "processingMetadata": {
        "model": "deepseek-chat",
        "latencyMs": 180,
        "tokenUsage": {"input": 500, "output": 200}
      }
    }
  }
```

#### 5.3.3 배치 엔티티 추출

```yaml
POST /internal/v1/extract/entities/batch
Description: 여러 청크에서 일괄 엔티티 추출
Content-Type: application/json

Request:
  {
    "chunks": [
      {"chunkId": "550e8400-e29b-41d4-a716-446655440001", "text": "홍길동이 React로..."},
      {"chunkId": "550e8400-e29b-41d4-a716-446655440002", "text": "김철수가 Vue를 사용하여..."}
    ],
    "documentId": "550e8400-e29b-41d4-a716-446655440010",
    "options": {
      "extractRelationships": true
    }
  }

Response (200 OK):
  {
    "success": true,
    "data": {
      "results": [
        {
          "chunkId": "550e8400-e29b-41d4-a716-446655440001",
          "entities": [...],
          "relationships": [...]
        },
        {
          "chunkId": "550e8400-e29b-41d4-a716-446655440002",
          "entities": [...],
          "relationships": [...]
        }
      ],
      "aggregatedEntities": [
        {"name": "홍길동", "type": "Person", "mentions": 3},
        {"name": "React", "type": "Technology", "mentions": 5}
      ],
      "processingMetadata": {
        "totalChunks": 2,
        "totalLatencyMs": 300
      }
    }
  }
```

---

### 5.4 임베딩 API (`/internal/v1/embed`)

#### 5.4.1 단일 텍스트 임베딩

```yaml
POST /internal/v1/embed
Description: 텍스트 임베딩 벡터 생성
Content-Type: application/json

Request:
  {
    "text": "React 컴포넌트 기반 아키텍처 설계",
    "returnSparse": true
  }

Response (200 OK):
  {
    "success": true,
    "data": {
      "denseVector": [0.123, 0.456, 0.789, ...],  # 1024 dimensions
      "sparseVector": {
        "indices": [12, 45, 89, 234, ...],
        "values": [0.5, 0.3, 0.8, 0.2, ...]
      },
      "tokenCount": 15,
      "model": "BAAI/bge-m3",
      "latencyMs": 25
    }
  }
```

#### 5.4.2 배치 임베딩

```yaml
POST /internal/v1/embed/batch
Description: 여러 텍스트 일괄 임베딩
Content-Type: application/json

Request:
  {
    "texts": [
      {"id": "550e8400-e29b-41d4-a716-446655440001", "text": "React 컴포넌트..."},
      {"id": "550e8400-e29b-41d4-a716-446655440002", "text": "Vue 컴포지션 API..."}
    ],
    "returnSparse": true
  }

Response (200 OK):
  {
    "success": true,
    "data": {
      "embeddings": [
        {
          "id": "550e8400-e29b-41d4-a716-446655440001",
          "denseVector": [...],
          "sparseVector": {...},
          "tokenCount": 15
        },
        {
          "id": "550e8400-e29b-41d4-a716-446655440002",
          "denseVector": [...],
          "sparseVector": {...},
          "tokenCount": 12
        }
      ],
      "totalTokens": 27,
      "model": "BAAI/bge-m3",
      "latencyMs": 45
    }
  }
```

---

### 5.5 문서 파싱 API (`/internal/v1/parse`)

#### 5.5.1 문서 파싱

```yaml
POST /internal/v1/parse
Description: 문서 파일 파싱 (PDF, DOCX)
Content-Type: multipart/form-data

Request:
  - file: binary (required) - 문서 파일
  - options: JSON string (optional)
    {
      "extractTables": true,
      "extractImages": false,
      "chunkSize": 512,
      "chunkOverlap": 50
    }

Response (200 OK):
  {
    "success": true,
    "data": {
      "filename": "document.pdf",
      "mimeType": "application/pdf",
      "pageCount": 15,
      "content": "전체 텍스트 내용...",
      "chunks": [
        {
          "index": 0,
          "text": "청크 1 내용...",
          "tokenCount": 450,
          "pageNumber": 1,
          "metadata": {
            "heading": "1. 개요",
            "position": {"start": 0, "end": 450}
          }
        },
        {
          "index": 1,
          "text": "청크 2 내용...",
          "tokenCount": 480,
          "pageNumber": 1,
          "metadata": {
            "heading": "1.1 목적",
            "position": {"start": 400, "end": 880}
          }
        }
      ],
      "tables": [
        {
          "pageNumber": 3,
          "rows": [
            ["헤더1", "헤더2", "헤더3"],
            ["값1", "값2", "값3"]
          ]
        }
      ],
      "metadata": {
        "title": "프로젝트 A 기술 문서",
        "author": "홍길동",
        "createdDate": "2024-01-15",
        "modifiedDate": "2024-06-20"
      },
      "processingMetadata": {
        "parser": "docling",
        "version": "2.0",
        "latencyMs": 2500
      }
    }
  }
```

#### 5.5.2 청킹만 수행

```yaml
POST /internal/v1/parse/chunk
Description: 텍스트를 청크로 분할
Content-Type: application/json

Request:
  {
    "text": "긴 텍스트 내용...",
    "chunkSize": 512,
    "chunkOverlap": 50,
    "strategy": "semantic"  # fixed | semantic | paragraph
  }

Response (200 OK):
  {
    "success": true,
    "data": {
      "chunks": [
        {
          "index": 0,
          "text": "청크 1...",
          "tokenCount": 450,
          "startPosition": 0,
          "endPosition": 1200
        }
      ],
      "totalChunks": 15,
      "averageTokenCount": 420
    }
  }
```

---

### 5.6 그래프 동기화 API (`/internal/v1/graph`)

#### 5.6.1 엔티티/관계 저장

```yaml
POST /internal/v1/graph/sync
Description: 추출된 엔티티와 관계를 Neo4j에 동기화
Content-Type: application/json

Request:
  {
    "documentId": "doc-001",
    "entities": [
      {"name": "홍길동", "type": "Person", "properties": {"department": "개발팀"}},
      {"name": "React", "type": "Technology", "properties": {}}
    ],
    "relationships": [
      {"source": "홍길동", "target": "doc-001", "type": "CREATED"},
      {"source": "React", "type": "MENTIONED_IN", "target": "doc-001"}
    ],
    "textUnits": [
      {"chunkId": "550e8400-e29b-41d4-a716-446655440001", "documentId": "550e8400-e29b-41d4-a716-446655440010", "chunkIndex": 0}
    ]
  }

Response (200 OK):
  {
    "success": true,
    "data": {
      "nodesCreated": 2,
      "nodesUpdated": 0,
      "relationshipsCreated": 2,
      "textUnitsCreated": 1,
      "latencyMs": 150
    }
  }
```

---

## 6. Part 3: 공통 스키마

### 6.1 기본 모델

#### 6.1.1 User

```json
{
  "id": "string (UUID)",
  "email": "string",
  "name": "string",
  "department": "string",
  "position": "string | null",
  "profileImage": "string (URL) | null",
  "roles": ["USER", "KNOWLEDGE_MANAGER", "ADMIN"],
  "status": "ACTIVE | INACTIVE | SUSPENDED",
  "createdAt": "string (ISO 8601)",
  "lastLoginAt": "string (ISO 8601) | null"
}
```

#### 6.1.2 Knowledge

```json
{
  "id": "string (UUID)",
  "title": "string (max 500)",
  "content": "string (Markdown)",
  "summary": "string | null",
  "documentType": "string | null",
  "category": {
    "id": "string",
    "level1": "string",
    "level2": "string | null",
    "level3": "string | null"
  },
  "author": "User (embedded)",
  "project": {
    "id": "string",
    "name": "string",
    "code": "string"
  } | null,
  "tags": ["string"],
  "attachments": ["Attachment"],
  "status": "DRAFT | PUBLISHED | ARCHIVED",
  "visibility": "PUBLIC | DEPARTMENT | PRIVATE",
  "version": "integer",
  "viewCount": "integer",
  "likeCount": "integer",
  "validStartDate": "string (YYYY-MM-DD) | null",
  "validEndDate": "string (YYYY-MM-DD) | null",
  "createdAt": "string (ISO 8601)",
  "updatedAt": "string (ISO 8601)",
  "publishedAt": "string (ISO 8601) | null"
}
```

#### 6.1.3 SearchResult

```json
{
  "id": "string (chunk ID)",
  "knowledgeId": "string",
  "title": "string",
  "text": "string",
  "score": "number (0-1)",
  "highlightedText": "string (HTML with <mark>)",
  "metadata": {
    "documentType": "string",
    "projectName": "string | null",
    "author": "string",
    "validStartDate": "string | null",
    "validEndDate": "string | null",
    "categories": {
      "level1": "string",
      "level2": "string | null",
      "level3": "string | null"
    },
    "summary": "string | null"
  },
  "graphContext": {
    "relatedEntities": [{"name": "string", "type": "string"}],
    "community": "string | null"
  } | null
}
```

### 6.2 페이지네이션

```json
{
  "page": "integer (1-based)",
  "size": "integer (default: 20, max: 100)",
  "totalPages": "integer",
  "totalElements": "integer",
  "hasNext": "boolean",
  "hasPrevious": "boolean"
}
```

### 6.3 필터 파라미터

#### 6.3.1 날짜 범위

```json
{
  "dateRange": {
    "start": "string (YYYY-MM-DD)",
    "end": "string (YYYY-MM-DD)"
  }
}
```

#### 6.3.2 정렬

```
sort=field,direction
예: sort=createdAt,desc
예: sort=score,desc&sort=createdAt,desc (다중 정렬)
```

지원 필드: `createdAt`, `updatedAt`, `viewCount`, `likeCount`, `score`, `title`
방향: `asc`, `desc`

---

## 7. 에러 코드 정의

> **참고**: 전체 에러 코드 및 공통 코드 정의는 [에러 코드 표준](./error_code_standards.md) 문서를 참조하세요.
> 본 섹션은 API별 주요 에러 코드 요약입니다.

### 7.1 인증/권한 에러 (AUTH_xxx)

| 코드 | HTTP | 메시지 | 설명 |
|------|------|--------|------|
| `AUTH_001` | 401 | 인증이 필요합니다. | 토큰 없음 |
| `AUTH_002` | 401 | 토큰이 만료되었습니다. | Access Token 만료 |
| `AUTH_003` | 401 | 유효하지 않은 토큰입니다. | 토큰 형식 오류 |
| `AUTH_004` | 401 | Refresh Token이 만료되었습니다. | 재로그인 필요 |
| `AUTH_005` | 403 | 접근 권한이 없습니다. | 역할 부족 |
| `AUTH_006` | 403 | 리소스에 대한 권한이 없습니다. | 소유자가 아님 |

### 7.2 지식 관련 에러 (KNOWLEDGE_xxx)

| 코드 | HTTP | 메시지 | 설명 |
|------|------|--------|------|
| `KNOWLEDGE_001` | 404 | 지식을 찾을 수 없습니다. | ID에 해당하는 지식 없음 |
| `KNOWLEDGE_002` | 400 | 유효하지 않은 요청입니다. | 필수 필드 누락 |
| `KNOWLEDGE_003` | 409 | 이미 존재하는 제목입니다. | 중복 제목 |
| `KNOWLEDGE_004` | 422 | 파일 형식이 지원되지 않습니다. | PDF, DOCX, MD, TXT만 지원 |
| `KNOWLEDGE_005` | 413 | 파일 크기가 제한을 초과했습니다. | 최대 50MB |
| `KNOWLEDGE_006` | 503 | 문서 처리 중 오류가 발생했습니다. | AI 처리 실패 |

### 7.3 검색 관련 에러 (SEARCH_xxx)

| 코드 | HTTP | 메시지 | 설명 |
|------|------|--------|------|
| `SEARCH_001` | 400 | 검색어를 입력해주세요. | 빈 쿼리 |
| `SEARCH_002` | 400 | 유효하지 않은 필터입니다. | 필터 형식 오류 |
| `SEARCH_003` | 503 | 검색 서비스를 일시적으로 사용할 수 없습니다. | ES/Neo4j 장애 |
| `SEARCH_004` | 503 | AI 서비스를 일시적으로 사용할 수 없습니다. | AI Service 장애 |

### 7.4 시스템 에러 (SYSTEM_xxx)

| 코드 | HTTP | 메시지 | 설명 |
|------|------|--------|------|
| `SYSTEM_001` | 500 | 내부 서버 오류가 발생했습니다. | 예상치 못한 오류 |
| `SYSTEM_002` | 503 | 서비스를 일시적으로 사용할 수 없습니다. | 서비스 불가 |
| `SYSTEM_003` | 429 | 요청이 너무 많습니다. | Rate Limit 초과 |

### 7.5 장애 대응 및 Circuit Breaker

> **상세 구현**: [백엔드 상세 설계서](./backend_detailed_design.md#102-resilience4j-설정) 참조

#### 7.5.1 Circuit Breaker 상태 전이

Backend에서 AI Service 호출 시 Resilience4j Circuit Breaker 패턴을 적용하여 장애 전파를 방지합니다.

```mermaid
stateDiagram-v2
    [*] --> CLOSED

    CLOSED --> OPEN: 실패율 ≥ 50%
    OPEN --> HALF_OPEN: 30초 후
    HALF_OPEN --> CLOSED: 복구 성공
    HALF_OPEN --> OPEN: 복구 실패
```

#### 7.5.2 상태별 API 응답

| Circuit Breaker 상태 | API 동작 | HTTP 응답 | 사용자 메시지 |
|---------------------|---------|----------|-------------|
| **CLOSED** | 정상 처리 | 200 | 정상 응답 |
| **OPEN** | Fallback 실행 | 200 (부분) / 503 | "AI 서비스가 일시적으로 응답하지 않습니다" |
| **HALF_OPEN** | 제한적 요청 | 200 / 503 | 복구 시도 중 |

#### 7.5.3 Fallback 전략

| API | Fallback 응답 | 설명 |
|-----|--------------|------|
| `POST /search/chat` | 빈 결과 + fallback 플래그 | `{ "results": [], "fallback": true }` |
| `POST /search/hybrid` | 캐시된 결과 또는 빈 결과 | Redis 캐시 활용 |
| `POST /internal/v1/extract/*` | 빈 메타데이터 | `{ "metadata": {} }` |
| `POST /internal/v1/embed` | 빈 임베딩 | 재시도 필요 안내 |

#### 7.5.4 Resilience4j 설정 요약

| 설정 | 값 | 설명 |
|------|-----|------|
| `failureRateThreshold` | 50% | OPEN 전환 실패율 |
| `slidingWindowSize` | 10 | 집계 윈도우 |
| `waitDurationInOpenState` | 30초 | OPEN 유지 시간 |
| `timeoutDuration` | 30초 | 요청 타임아웃 |
| `maxAttempts` (Retry) | 3회 | 재시도 횟수 |

#### 7.5.5 클라이언트 재시도 가이드

```
HTTP 503 응답 시:
1. Retry-After 헤더 확인
2. 지수 백오프로 재시도 (1s → 2s → 4s)
3. 최대 3회 재시도 후 사용자에게 안내
```

---

## 8. 보안 고려사항

### 8.1 API Gateway 보안

| 항목 | 설정 |
|------|------|
| **HTTPS** | 필수 (HTTP → HTTPS 리다이렉트) |
| **CORS** | 허용된 Origin만 접근 |
| **Rate Limiting** | 10 req/sec (일반), 1 req/sec (검색) |
| **Request Size** | 최대 50MB (파일 업로드) |

### 8.2 인증 보안

| 항목 | 설정 |
|------|------|
| **Access Token** | 15분 만료, RS256 서명 |
| **Refresh Token** | 7일 만료, Rotation 적용 |
| **PKCE** | Authorization Code Flow에 필수 |
| **Token Blacklist** | 로그아웃 시 Redis에 저장 |

### 8.3 Internal API 보안

| 항목 | 설정 |
|------|------|
| **네트워크** | 내부 네트워크에서만 접근 (Docker network) |
| **인증** | X-Internal-Api-Key (선택적) |
| **로깅** | 모든 요청 로깅 (X-Request-Id) |

---

## 9. 버전 관리 전략

### 9.1 URL 버전

```
/api/v1/knowledge      # 현재 버전
/api/v2/knowledge      # 다음 버전 (Breaking Change 시)
```

### 9.2 버전 전환 정책

| 단계 | 기간 | 설명 |
|------|------|------|
| **신버전 출시** | - | v2 API 공개 |
| **병행 운영** | 6개월 | v1, v2 동시 운영 |
| **v1 Deprecated** | 3개월 | v1에 Deprecated 헤더 추가 |
| **v1 종료** | - | v1 API 종료 |

### 9.3 Deprecated 응답 헤더

```
X-API-Deprecated: true
X-API-Deprecated-At: 2026-06-01
X-API-Successor: /api/v2/knowledge
```

---

## 부록

### A. OpenAPI 3.0 스펙 파일

별도 파일: `openapi.yaml` (자동 생성 예정)

### B. Postman Collection

별도 파일: `Knowledge_Platform_API.postman_collection.json` (별도 생성 예정)

### C. 참고 문서

| 문서 | 위치 |
|------|------|
| 상세 설계서 | [hybrid_rag_platform_detailed_design.md](./hybrid_rag_platform_detailed_design.md) |
| 백엔드 구현 계획서 | [backend_implementation_plan.md](../01_planning/backend_implementation_plan.md) |
| AI 서비스 구현 계획서 | [ai_service_implementation_plan.md](../01_planning/ai_service_implementation_plan.md) |
| 인증/권한 설계서 | [authentication_authorization_detailed_design.md](./authentication_authorization_detailed_design.md) |
| 에러 코드 표준 | [error_code_standards.md](./error_code_standards.md) |
| 용어사전 | [glossary.md](./glossary.md) |

---

**문서 작성 완료: 2026-01-16**
**다음 업데이트: OpenAPI 3.0 YAML 파일 생성, Postman Collection 생성**
