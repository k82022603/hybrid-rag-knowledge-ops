# camelCase vs snake_case 불일치 전수 조사 보고서

**조사일**: 2026-02-08
**조사자**: TechLead Agent
**심각도**: Medium (일부 데이터 누락 가능성 확인)

---

## 요약

| 항목 | 건수 |
|------|------|
| 조사 대상 API 엔드포인트 | 14개 |
| 조사 대상 프론트엔드 서비스 | 8개 (services/ 7개 + shared/api/sse.ts 1개) |
| 조사 대상 훅 (hooks) | 4개 |
| **불일치 발견** | **5건** |
| 이미 수정 완료 | 1건 |
| **추가 수정 필요** | **4건** |
| 양쪽 일치 (정상) | 9건 |

---

## API 엔드포인트 매핑

| # | Frontend Service | Endpoint | Backend Route |
|---|-----------------|----------|---------------|
| 1 | searchService.search() | POST /search/hybrid | search.py - SearchRequest |
| 2 | searchService.streamSearch() | POST /search/chat/stream | search.py - ChatRequest |
| 3 | searchService.findExperts() | POST /graph/experts | graph.py - ExpertSearchRequest |
| 4 | authService.login() | POST /auth/login | auth.py - LoginRequest |
| 5 | authService.logout() | POST /auth/logout | auth.py (no body) |
| 6 | authService.refreshToken() | POST /auth/refresh | auth.py - RefreshRequest |
| 7 | authService.validateToken() | GET /auth/me | auth.py (no body) |
| 8 | authService.confirmPasswordReset() | POST /auth/password-reset/confirm | (미구현) |
| 9 | knowledgeService.getDocuments() | GET /documents | documents.py (query params) |
| 10 | knowledgeService.uploadDocument() | POST /documents | documents.py (JSON body) |
| 11 | knowledgeService.uploadFile() | POST /documents/upload | documents.py (FormData) |
| 12 | knowledgeService.retryDocument() | POST /documents/{id}/retry | documents.py (no body) |
| 13 | bookmarkService.* | /bookmarks/* | (미구현 - 프론트엔드 전용) |
| 14 | adminService.* | /admin/* | (미구현 - 프론트엔드 전용) |
| 15 | profileService.* | /users/me/* | (미구현 - 프론트엔드 전용) |
| 16 | dashboardService.* | /dashboard/* | (미구현 - 프론트엔드 전용) |

---

## 상세 분석

### 1. POST /search/hybrid (searchService.search)

**상태: 수정 완료**

Frontend `searchService.ts` (lines 86-100)에서 camelCase -> snake_case 변환 로직이 이미 적용됨.

| 필드 | Frontend (변환 전) | Frontend (전송) | Backend (기대) | 상태 |
|------|-------------------|----------------|----------------|------|
| query | query | query | query | OK |
| top_k | pageSize | top_k | top_k | OK |
| filters.document_type | documentType | document_type | document_type | **수정완료** |
| filters.project_name | projectName | project_name | project_name | **수정완료** |
| filters.date_from | dateFrom | date_from | date_from | **수정완료** |
| filters.date_to | dateTo | date_to | date_to | **수정완료** |
| useGraph | - | useGraph | useGraph | OK (camelCase 일치) |
| useVector | - | useVector | useVector | OK (camelCase 일치) |

**분석**: `SearchRequest` Pydantic 모델의 `useGraph`, `useVector`는 camelCase로 정의되어 있고, frontend도 camelCase로 전송하므로 일치. `filters`는 `Dict[str, Any]` 타입이므로 Pydantic 검증을 거치지 않고 그대로 서비스 레이어로 전달됨. 서비스 레이어(`search.py`)에서 `data.get("document_type")` 등 snake_case 키를 기대하므로, 수정 전에는 필터 값이 누락되었을 것임. **현재는 수정 완료**.

---

### 2. POST /search/chat/stream (searchService.streamSearch / useStreamingSearch)

**상태: 불일치 2건 발견**

Frontend SSE 요청 본문 (`sse.ts` SSERequestBody, lines 87-101):
```typescript
{
  query: string;
  conversation_history?: Array<{role, content}>;
  top_k?: number;
  filters?: {
    documentType?: string;    // camelCase
    projectName?: string;     // camelCase
    dateFrom?: string;        // camelCase
    dateTo?: string;          // camelCase
  };
}
```

Backend `ChatRequest` 모델 (search.py, lines 75-84):
```python
class ChatRequest(BaseModel):
    query: str
    conversationId: Optional[str]   # camelCase
    topK: int = 5                   # camelCase
    useReasoner: bool = False       # camelCase
```

| 필드 | Frontend (전송) | Backend (기대) | 상태 | 영향 |
|------|----------------|----------------|------|------|
| query | query | query | OK | - |
| conversation_history | conversation_history | (필드 없음) | **불일치** | 데이터 무시됨 (Pydantic extra='ignore' 기본) |
| top_k | top_k | topK | **불일치** | top_k 무시, 기본값 5 사용 |
| filters | filters (camelCase 키) | (필드 없음) | **불일치** | 필터 무시됨 |
| conversationId | (미전송) | conversationId | - | 새 세션 생성 |
| useReasoner | (미전송) | useReasoner | - | 기본값 false 사용 |

**Issue #1 (Medium): `top_k` vs `topK` 불일치**
- Frontend는 `top_k` (snake_case)로 전송
- Backend `ChatRequest`는 `topK` (camelCase)로 정의
- `populate_by_name: True` 설정이 있지만, alias가 정의되지 않았으므로 `top_k`는 `topK`로 매핑되지 않음
- **결과**: `topK`는 항상 기본값 5가 사용됨. 사용자가 `topK`를 변경해도 반영되지 않음

**Issue #2 (Low): `filters` 필드 미지원**
- Frontend가 SSE 스트리밍 검색에서 `filters`를 전송하지만, `ChatRequest`에는 `filters` 필드가 없음
- 현재 chat/stream은 RAG workflow를 사용하여 자체 검색을 수행하므로, 이 필터가 의도적으로 무시되는 것일 수 있음
- 그러나 `useStreamingSearch` hook의 `UseStreamingSearchOptions`에 `filters` 옵션이 있고, UI에서 필터를 적용할 수 있는 것처럼 보여 사용자 혼란 가능

**Issue #3 (Info): `conversation_history` 필드 미지원**
- Frontend는 `conversation_history`를 전송하지만, `ChatRequest`에는 해당 필드가 없음
- 대화 이력은 `conversationId`를 통해 서버 측에서 관리되므로 (STORY-057), 이 필드가 무시되어도 기능상 문제없음
- 다만 불필요한 데이터가 전송되고 있어 네트워크 효율성 측면에서 비효율적

---

### 3. POST /graph/experts (searchService.findExperts)

**상태: 정상**

| 필드 | Frontend (전송) | Backend (기대) | 상태 |
|------|----------------|----------------|------|
| topic | topic | topic | OK |
| depth | depth | (필드 없음) | 무시됨 |
| limit | limit | limit | OK |

**분석**: Frontend에서 `{ topic, depth, limit }`을 전송. Backend `ExpertSearchRequest`에는 `topic`과 `limit`만 있고 `depth`는 없음. `depth`는 무시되지만 기능에 영향 없음 (불필요한 필드 전송).

---

### 4. POST /auth/login (authService.login)

**상태: 정상**

| 필드 | Frontend (전송) | Backend (기대) | 상태 |
|------|----------------|----------------|------|
| email | email | email (EmailStr) | OK |
| password | password | password | OK |

---

### 5. POST /auth/refresh (authService.refreshToken)

**상태: 불일치 1건 발견**

| 필드 | Frontend (전송) | Backend (기대) | 상태 | 영향 |
|------|----------------|----------------|------|------|
| refreshToken | refreshToken (camelCase) | refresh_token (snake_case, alias "refreshToken") | **주의** | 작동함 (alias 설정됨) |

**분석**: Backend `RefreshRequest` 모델 정의:
```python
class RefreshRequest(BaseModel):
    refresh_token: str = Field(alias="refreshToken")
    model_config = {"populate_by_name": True}
```

Frontend는 `{ refreshToken }` (camelCase)를 전송하고, Backend는 `alias="refreshToken"`으로 수신.
`populate_by_name: True` 설정 덕분에 `refresh_token`과 `refreshToken` 둘 다 수용.
**현재 정상 작동하지만, alias 설정에 의존하는 점에 주의**.

---

### 6. POST /auth/password-reset/confirm (authService.confirmPasswordReset)

**상태: 불일치 1건 발견 (잠재적)**

Frontend 전송:
```typescript
{ token: string, newPassword: string }  // camelCase
```

Backend: **엔드포인트 미구현**

| 필드 | Frontend (전송) | Backend (기대) | 상태 |
|------|----------------|----------------|------|
| token | token | (미구현) | - |
| newPassword | newPassword (camelCase) | (미구현) | **주의** |

**분석**: Backend에 해당 엔드포인트가 아직 구현되지 않아 현재 실행 시 404 에러. 향후 구현 시 `newPassword` (camelCase)를 수용하도록 alias 설정 필요.

---

### 7. GET /documents (knowledgeService.getDocuments)

**상태: 불일치 1건 발견**

Frontend 전송 (query params):
```typescript
{ page, pageSize, documentType?, projectName? }  // camelCase
```

Backend 기대 (query params):
```python
page: int           # OK
page_size: int      # snake_case (alias 없음)
status: Optional     # alias 설정됨
format: Optional     # alias 설정됨
```

| 필드 | Frontend (전송) | Backend (기대) | 상태 | 영향 |
|------|----------------|----------------|------|------|
| page | page | page | OK | - |
| pageSize | pageSize | page_size | **불일치** | pageSize 무시, 기본값 20 사용 |
| documentType | documentType | (필드 없음) | 무시됨 | 필터 미작동 |
| projectName | projectName | (필드 없음) | 무시됨 | 필터 미작동 |

**Issue #4 (Low): `pageSize` vs `page_size`**
- Frontend는 `pageSize` (camelCase)를 query param으로 전송
- Backend는 `page_size` (snake_case)를 기대
- FastAPI query param에는 Pydantic alias가 자동 적용되지 않으므로, `pageSize`는 인식되지 않음
- **결과**: 항상 기본 page_size=20이 사용됨

**Note**: `documentType`과 `projectName` 필터는 Backend에 해당 query param이 정의되어 있지 않으므로, 이들은 현재 작동하지 않는 것이 정상 (Backend에서 status/format 필터만 지원).

---

### 8. POST /documents (knowledgeService.uploadDocument)

**상태: 불일치 1건 발견**

Frontend 전송:
```typescript
{
  title: string,
  content: string,
  documentType: string,    // camelCase
  projectName: string,     // camelCase
  metadata?: { author?, department?, tags? }
}
```

Backend: **이 엔드포인트는 documents.py에 없음**. `/documents`에는 GET (목록)과 `/documents/upload` (파일 업로드)만 있음. 즉, JSON body로 문서를 생성하는 엔드포인트가 미구현.

**분석**: Frontend의 `uploadDocument` 메서드가 JSON body를 POST하지만, Backend에는 JSON body를 받는 POST /documents 엔드포인트가 없음. 현재 이 서비스 메서드는 호출되면 404 에러가 발생할 것임.

---

### 9. POST /documents/upload (knowledgeService.uploadFile)

**상태: 주의 필요**

Frontend 전송 (FormData):
```typescript
formData.append('file', file);
formData.append('metadata', JSON.stringify({
  projectName?: string,     // camelCase
  documentType?: string,    // camelCase
}));
```

Backend 기대 (FormData):
```python
file: UploadFile
metadata: Optional[str]  # JSON string parsed as DocumentMetadataInput
```

`DocumentMetadataInput` 모델:
```python
class DocumentMetadataInput(BaseModel):
    title: Optional[str]
    description: Optional[str]
    tags: List[str]
    project_name: Optional[str]  # snake_case
```

| 필드 | Frontend (전송, JSON 내) | Backend (기대, 파싱 후) | 상태 | 영향 |
|------|-------------------------|------------------------|------|------|
| projectName | projectName (camelCase) | project_name (snake_case) | **불일치** | projectName 무시 |
| documentType | documentType (camelCase) | (필드 없음) | 무시됨 | - |

**Issue #5 (Medium): `projectName` vs `project_name` in metadata JSON**
- Frontend는 metadata JSON 내에 `projectName` (camelCase)를 전송
- Backend `DocumentMetadataInput` 모델은 `project_name` (snake_case)를 기대
- alias 설정이 없으므로 `projectName`은 무시됨
- **결과**: 파일 업로드 시 프로젝트명이 저장되지 않음

---

### 10. 응답 매핑 분석 (Backend -> Frontend)

searchService.search()의 응답 매핑 (lines 105-128)에서 snake_case -> camelCase 변환이 수행됨:

| Backend 응답 필드 | Frontend 매핑 | 상태 |
|-------------------|--------------|------|
| chunk_id | chunkId (fallback 포함) | OK |
| document_id | documentId (fallback 포함) | OK |
| content | content | OK |
| score | score | OK |
| metadata.document_type | metadata.documentType | OK |
| metadata.project_name | metadata.projectName | OK |
| metadata.title | metadata.title | OK |
| metadata.search_source | sourceType | OK |
| graph_context | graphContext (fallback 포함) | OK |
| total | totalCount (fallback 포함) | OK |

**분석**: 응답 매핑은 양방향 fallback (`r.chunk_id ?? r.chunkId`)으로 처리되어 안전함.

---

### 11. SSE 응답 매핑 (useStreamingSearch)

`mapSSESourcesToSources` 함수 (useStreamingSearch.ts, lines 94-109)에서 양방향 매핑:

| Backend 응답 필드 | Frontend 매핑 | 상태 |
|-------------------|--------------|------|
| chunk_id / chunkId | chunkId | OK (양방향 fallback) |
| document_id / documentId | documentId | OK |
| source_type / sourceType | sourceType | OK |
| graph_context / graphContext | graphContext | OK (nested 변환 포함) |

**분석**: SSE 소스 데이터의 응답 매핑은 양방향 fallback으로 안전하게 처리됨.

---

### 12. Auth 응답 매핑

Backend `TokenResponse` 모델:
```python
access_token: str = Field(serialization_alias="accessToken")
refresh_token: str = Field(serialization_alias="refreshToken")
expires_in: int = Field(serialization_alias="expiresIn")
```

Frontend 기대:
```typescript
{ accessToken, refreshToken, expiresIn }
```

**상태**: 정상. `serialization_alias`를 통해 응답 시 camelCase로 변환됨.

---

## 수정 완료 항목

| # | 위치 | 내용 | PR/커밋 |
|---|------|------|---------|
| 1 | searchService.ts search() | filters 필드 camelCase -> snake_case 변환 로직 추가 | cf93e02 |

---

## 추가 수정 필요 항목

### Issue #1: `/search/chat/stream` - `top_k` vs `topK` (Medium)

| 항목 | 내용 |
|------|------|
| **위치** | Frontend: `sse.ts` SSERequestBody / `useStreamingSearch.ts` |
| **문제** | Frontend가 `top_k` (snake_case)를 전송하지만 Backend `ChatRequest`는 `topK` (camelCase)를 기대 |
| **영향** | 사용자 설정 top_k 값이 무시되고 항상 기본값 5가 사용됨 |
| **수정 방안 A** | Frontend에서 `top_k` 대신 `topK`로 전송 |
| **수정 방안 B** | Backend `ChatRequest`에 `top_k` alias 추가: `topK: int = Field(alias="top_k")` |
| **권장** | 방안 A (Frontend 수정) - ADR 기준 Backend API는 camelCase 채택 |

### Issue #2: `/search/chat/stream` - `filters` camelCase 키 (Medium)

| 항목 | 내용 |
|------|------|
| **위치** | Frontend: `sse.ts` SSERequestBody.filters / `useStreamingSearch.ts` |
| **문제** | Frontend가 `filters`를 camelCase 키로 전송하지만 Backend `ChatRequest`에 `filters` 필드 자체가 없음 |
| **영향** | 스트리밍 검색에서 필터 기능이 작동하지 않음 |
| **수정 방안 A** | Backend `ChatRequest`에 `filters: Optional[Dict[str, Any]]` 필드 추가 + RAG workflow에 필터 전달 |
| **수정 방안 B** | Frontend에서 스트리밍 검색 시 필터 UI를 비활성화 (의도적 미지원이라면) |
| **권장** | 방안 A 또는 B는 제품 요구사항에 따라 결정 필요 |

### Issue #3: `GET /documents` - `pageSize` vs `page_size` (Low)

| 항목 | 내용 |
|------|------|
| **위치** | Frontend: `knowledgeService.ts` getDocuments() |
| **문제** | Frontend가 `pageSize` (camelCase)를 query param으로 전송하지만 Backend는 `page_size` (snake_case)를 기대 |
| **영향** | 문서 목록 조회 시 항상 기본 page_size=20이 사용됨 |
| **수정 방안 A** | Frontend에서 `pageSize` 대신 `page_size`로 전송 |
| **수정 방안 B** | Backend query param에 alias 추가: `Query(alias="pageSize")` |
| **권장** | 방안 B (Backend에 alias 추가) - Frontend 네이밍 컨벤션 유지 |

### Issue #4: `POST /documents/upload` - metadata JSON `projectName` vs `project_name` (Medium)

| 항목 | 내용 |
|------|------|
| **위치** | Frontend: `knowledgeService.ts` uploadFile() |
| **문제** | metadata JSON 내 `projectName` (camelCase) 전송, Backend `DocumentMetadataInput`은 `project_name` (snake_case) 기대 |
| **영향** | 파일 업로드 시 프로젝트명이 저장되지 않음 |
| **수정 방안 A** | Frontend에서 metadata 전송 시 `project_name`으로 변환 |
| **수정 방안 B** | Backend `DocumentMetadataInput`에 alias 추가: `Field(alias="projectName")` |
| **권장** | 방안 B (Backend alias 추가) + `populate_by_name: True` 설정 |

---

## 정상 항목 요약

| # | 엔드포인트 | 사유 |
|---|-----------|------|
| 1 | POST /auth/login | 양쪽 동일 (email, password) |
| 2 | POST /auth/logout | Body 없음 |
| 3 | POST /auth/refresh | alias="refreshToken" 설정으로 정상 작동 |
| 4 | GET /auth/me | Body 없음 |
| 5 | POST /search/hybrid | 수정 완료 (filters 변환 로직 적용) |
| 6 | POST /graph/experts | 주요 필드 일치 (topic, limit) |
| 7 | Backend 응답 -> Frontend | 양방향 fallback 매핑으로 안전 |
| 8 | SSE 소스 응답 매핑 | 양방향 fallback 매핑으로 안전 |
| 9 | Auth 응답 (TokenResponse) | serialization_alias로 camelCase 변환 |

---

## 미구현 엔드포인트 (프론트엔드 전용)

아래 서비스들은 Backend에 해당 엔드포인트가 아직 구현되지 않아 분석 대상에서 제외. 향후 구현 시 네이밍 컨벤션 일치 검토 필요.

| Frontend Service | 엔드포인트 | 비고 |
|-----------------|-----------|------|
| bookmarkService | /bookmarks/* | CRUD 전체 미구현 |
| adminService | /admin/* | 사용자 관리, 시스템 설정 미구현 |
| profileService | /users/me/* | 프로필 수정, 비밀번호 변경 미구현 |
| dashboardService | /dashboard/* | 통계, 트렌드 미구현 |
| authService.requestPasswordReset | /auth/password-reset/request | 미구현 |
| authService.confirmPasswordReset | /auth/password-reset/confirm | 미구현 |
| knowledgeService.uploadDocument | POST /documents (JSON body) | 미구현 (upload만 존재) |
| knowledgeService.updateDocument | PUT /documents/{id} | 미구현 |
| knowledgeService.deleteDocument | DELETE /documents/{id} | 미구현 |

---

## 권장사항

### 단기 조치 (즉시)

1. **Issue #1 수정**: `useStreamingSearch.ts`에서 `top_k`를 `topK`로 변경하거나, Backend `ChatRequest`에 alias 추가
2. **Issue #4 수정**: `DocumentMetadataInput`에 `Field(alias="projectName")` 추가

### 중기 조치 (Sprint 내)

3. **Issue #3 수정**: Backend document list endpoint에 `pageSize` alias 추가
4. **Issue #2 설계 결정**: 스트리밍 검색에서 필터 지원 여부 결정 후 구현

### 장기 조치 (아키텍처)

5. **ADR 문서화**: Frontend-Backend 간 네이밍 컨벤션 규칙 공식화
   - 제안: Backend API의 Request/Response는 camelCase 사용 (현재 ChatRequest, TokenResponse 등에서 이미 채택)
   - 내부 서비스 레이어는 snake_case 유지
   - `filters` 같은 `Dict[str, Any]` 타입 필드는 별도 Pydantic 모델로 정의하여 타입 안전성 확보

6. **미구현 엔드포인트 구현 시 주의**: 위 미구현 목록의 Frontend 인터페이스가 모두 camelCase를 사용하므로, Backend 구현 시 alias 또는 camelCase 필드명 채택 필요

7. **자동 변환 미들웨어 검토**: `humps` 또는 커스텀 미들웨어를 통한 자동 camelCase/snake_case 변환 도입 검토 (단, 기존 코드와의 호환성 주의)

---

## 부록: 파일별 조사 결과 요약

### Frontend 파일

| 파일 | API 호출 | 불일치 여부 |
|------|---------|------------|
| `services/searchService.ts` | /search/hybrid, /search/chat/stream, /graph/experts | hybrid 수정완료, stream 불일치 2건 |
| `services/authService.ts` | /auth/login, /auth/logout, /auth/refresh, /auth/me | 정상 (alias 활용) |
| `services/knowledgeService.ts` | /documents, /documents/upload, /documents/{id}/* | 불일치 2건 (pageSize, projectName) |
| `services/bookmarkService.ts` | /bookmarks/* | Backend 미구현 |
| `services/adminService.ts` | /admin/* | Backend 미구현 |
| `services/profileService.ts` | /users/me/* | Backend 미구현 |
| `services/dashboardService.ts` | /dashboard/* | Backend 미구현 |
| `shared/api/sse.ts` | /search/chat/stream (SSE) | 불일치 (top_k, filters) |
| `features/search/hooks/useStreamingSearch.ts` | /search/chat/stream (SSE) | 불일치 (filters camelCase 키) |
| `features/search/hooks/useKeywordSearch.ts` | (searchService 위임) | 간접 영향 |
| `features/search/hooks/useSearchChat.ts` | (useStreamingSearch 위임) | 간접 영향 |
| `features/dashboard/hooks/useDashboardStats.ts` | (dashboardService 위임) | Backend 미구현 |
| `features/dashboard/hooks/useRecentSearches.ts` | (localStorage only) | API 호출 없음 |

### Backend 파일

| 파일 | 엔드포인트 | 네이밍 스타일 |
|------|-----------|--------------|
| `routes/search.py` | SearchRequest | 혼합 (top_k snake + useGraph camel) |
| `routes/search.py` | ChatRequest | camelCase (topK, conversationId, useReasoner) |
| `routes/auth.py` | LoginRequest | snake_case (email, password) |
| `routes/auth.py` | RefreshRequest | snake_case + alias (refresh_token / refreshToken) |
| `routes/auth.py` | TokenResponse | snake_case + serialization_alias (camelCase 출력) |
| `routes/documents.py` | DocumentMetadataInput | snake_case (project_name) |
| `routes/graph.py` | ExpertSearchRequest | snake_case (topic, limit) |

---

*보고서 끝*
