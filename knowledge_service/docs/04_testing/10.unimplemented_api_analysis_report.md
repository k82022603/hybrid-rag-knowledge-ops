# 미구현 API 엔드포인트 분석 보고서

**작성자**: TechLead Agent  
**작성일**: 2026-01-30  
**분석 범위**: Frontend Services vs Backend Controllers

---

## 1. 분석 개요

### 1.1 조사 범위

| 구분 | 파일 위치 | 파일 수 |
|------|----------|--------|
| Frontend Services | `frontend/src/services/*.ts` | 9개 |
| Backend Controllers | `backend/src/main/java/.../controller/*.java` | 10개 |

### 1.2 조사 방법

1. Frontend 서비스 파일에서 API 호출 패턴 추출 (axios `api.get`, `api.post`, `api.put`, `api.delete`)
2. Backend Controller 파일에서 구현된 엔드포인트 매핑 추출 (`@GetMapping`, `@PostMapping`, `@PutMapping`, `@DeleteMapping`)
3. Frontend 호출 vs Backend 구현 비교
4. 미구현/불일치 API 식별

---

## 2. 미구현 API 현황 요약

| 카테고리 | 미구현 수 | 심각도 |
|----------|---------|--------|
| Dashboard API | **5개** | P0 (Critical) |
| Search API | **1개** | P1 (High) |
| Knowledge/Document API | **2개** | P1 (High) |
| Bookmark API | **1개** | P2 (Medium) |
| Auth API | **2개** | P2 (Medium) |
| Admin API | **1개** | P2 (Medium) |
| **합계** | **12개** | - |

---

## 3. 미구현 API 상세 목록

### 3.1 Dashboard API (P0 - Critical)

| # | Frontend 호출 | Method | Backend 상태 | 불일치 유형 |
|---|--------------|--------|-------------|------------|
| 1 | `/dashboard/stats` | GET | `/dashboard/stats` (구현됨) | **경로 일치** |
| 2 | `/dashboard/health` | GET | **미구현** | 경로 없음 |
| 3 | `/dashboard/activities` | GET | `/dashboard/activity` (구현됨) | **경로 불일치** (`activities` vs `activity`) |
| 4 | `/dashboard/search-trends` | GET | **미구현** | 경로 없음 |
| 5 | `/dashboard/popular-queries` | GET | **미구현** | 경로 없음 |
| 6 | `/dashboard/document-types` | GET | **미구현** | 경로 없음 |

**Frontend (dashboardService.ts)**:
```typescript
getStats(): GET /dashboard/stats
getSystemHealth(): GET /dashboard/health
getRecentActivities(): GET /dashboard/activities?limit=10
getSearchTrends(): GET /dashboard/search-trends?days=7
getPopularQueries(): GET /dashboard/popular-queries?limit=10
getDocumentTypeDistribution(): GET /dashboard/document-types
```

**Backend (DashboardController.java)**:
```java
GET /api/v1/dashboard/stats      - 구현됨
GET /api/v1/dashboard/popular    - 구현됨 (인기 지식, 다른 목적)
GET /api/v1/dashboard/activity   - 구현됨 (단수형)
```

**미구현 목록**:
- `/dashboard/health` - 시스템 헬스체크
- `/dashboard/search-trends` - 검색 트렌드
- `/dashboard/popular-queries` - 인기 검색어
- `/dashboard/document-types` - 문서 유형 분포
- `/dashboard/activities` - 경로명 불일치 (`activity` 단수 vs `activities` 복수)

---

### 3.2 Search API (P1 - High)

| # | Frontend 호출 | Method | Backend 상태 | 불일치 유형 |
|---|--------------|--------|-------------|------------|
| 1 | `/search` (키워드) | POST | `/search` (구현됨) | **경로 일치** (hybridSearch 매핑) |
| 2 | `/search/chat/stream` | POST | `/search/chat/stream` (구현됨) | **경로 일치** |
| 3 | `/graph/experts` | POST | **미구현** | 경로 없음 |

**Frontend (searchService.ts)**:
```typescript
search(): POST /search
streamSearch(): POST /search/chat/stream
findExperts(): POST /graph/experts
```

**미구현 목록**:
- `/graph/experts` - 전문가 검색 (Graph 기반)

---

### 3.3 Knowledge/Document API (P1 - High)

| # | Frontend 호출 | Method | Backend 상태 | 불일치 유형 |
|---|--------------|--------|-------------|------------|
| 1 | `/documents` | GET | 구현됨 (DocumentController) | 경로 일치 |
| 2 | `/documents/{id}` | GET | 구현됨 | 경로 일치 |
| 3 | `/documents` | POST | 구현됨 | 경로 일치 |
| 4 | `/documents/upload` | POST (multipart) | **미구현** | 파일 업로드 미지원 |
| 5 | `/documents/{id}` | PUT | **미구현** (DocumentController에 없음) | 수정 API 없음 |
| 6 | `/documents/{id}` | DELETE | 구현됨 | 경로 일치 |
| 7 | `/documents/{id}/status` | GET | 구현됨 | 경로 일치 |

**Frontend (knowledgeService.ts)**:
```typescript
getDocuments(): GET /documents
getDocument(id): GET /documents/{id}
uploadDocument(): POST /documents
uploadFile(): POST /documents/upload (multipart/form-data)
updateDocument(): PUT /documents/{id}
deleteDocument(): DELETE /documents/{id}
getProcessingStatus(): GET /documents/{id}/status
```

**미구현 목록**:
- `/documents/upload` - 파일 업로드 (multipart)
- `/documents/{id}` - 문서 수정 (PUT) - DocumentController에 없음 (KnowledgeController에는 있음)

---

### 3.4 Bookmark API (P2 - Medium)

| # | Frontend 호출 | Method | Backend 상태 | 불일치 유형 |
|---|--------------|--------|-------------|------------|
| 1 | `/bookmarks` | GET | 구현됨 | 경로 일치 |
| 2 | `/bookmarks` | POST | 구현됨 | 경로 일치 |
| 3 | `/bookmarks/{id}` | DELETE | 구현됨 | 경로 일치 |
| 4 | `/bookmarks/{id}` | PUT | 구현됨 | 경로 일치 |
| 5 | `/bookmarks/counts` | GET | **미구현** | 폴더별 카운트 |

**Frontend (bookmarkService.ts)**:
```typescript
getBookmarks(): GET /bookmarks
createBookmark(): POST /bookmarks
deleteBookmark(): DELETE /bookmarks/{id}
updateBookmark(): PUT /bookmarks/{id}
getFolderCounts(): GET /bookmarks/counts
```

**미구현 목록**:
- `/bookmarks/counts` - 폴더별 북마크 수 조회

---

### 3.5 Auth API (P2 - Medium)

| # | Frontend 호출 | Method | Backend 상태 | 불일치 유형 |
|---|--------------|--------|-------------|------------|
| 1 | `/auth/login` | POST | 구현됨 | 경로 일치 |
| 2 | `/auth/logout` | POST | 구현됨 | 경로 일치 |
| 3 | `/auth/refresh` | POST | 구현됨 | 경로 일치 |
| 4 | `/auth/password-reset/request` | POST | **미구현** | 경로 없음 |
| 5 | `/auth/password-reset/confirm` | POST | **미구현** | 경로 없음 |
| 6 | `/auth/me` | GET | 구현됨 | 경로 일치 |

**Frontend (authService.ts)**:
```typescript
login(): POST /auth/login
logout(): POST /auth/logout
refreshToken(): POST /auth/refresh
requestPasswordReset(): POST /auth/password-reset/request
confirmPasswordReset(): POST /auth/password-reset/confirm
validateToken(): GET /auth/me
```

**미구현 목록**:
- `/auth/password-reset/request` - 비밀번호 재설정 요청
- `/auth/password-reset/confirm` - 비밀번호 재설정 확인

---

### 3.6 Admin API (P2 - Medium)

| # | Frontend 호출 | Method | Backend 상태 | 불일치 유형 |
|---|--------------|--------|-------------|------------|
| 1 | `/admin/users` | GET | 구현됨 | 경로 일치 |
| 2 | `/admin/users/{id}/roles` | PUT | `/admin/users/{id}/role` (구현됨) | **경로 불일치** (`roles` vs `role`) |
| 3 | `/admin/users/{id}/status` | PUT | 구현됨 | 경로 일치 |
| 4 | `/admin/system` | GET | 구현됨 | 경로 일치 |
| 5 | `/admin/system` | PUT | 구현됨 | 경로 일치 |
| 6 | `/admin/audit-logs` | GET | 구현됨 | 경로 일치 |
| 7 | `/admin/stats` | GET | **미구현** | 시스템 통계 |

**Frontend (adminService.ts)**:
```typescript
getUsers(): GET /admin/users
updateUserRoles(): PUT /admin/users/{id}/roles
toggleUserStatus(): PUT /admin/users/{id}/status
getSystemSettings(): GET /admin/system
updateSystemSettings(): PUT /admin/system
getAuditLogs(): GET /admin/audit-logs
getSystemStats(): GET /admin/stats
```

**미구현 목록**:
- `/admin/stats` - 시스템 통계 조회
- `/admin/users/{id}/roles` - 경로 불일치 (`role` 단수 vs `roles` 복수)

---

### 3.7 Profile API (P2 - Medium)

| # | Frontend 호출 | Method | Backend 상태 | 불일치 유형 |
|---|--------------|--------|-------------|------------|
| 1 | `/users/me` | GET | 구현됨 (UserController) | 경로 일치 |
| 2 | `/users/me` | PUT | 구현됨 | 경로 일치 |
| 3 | `/users/me/password` | PUT | 구현됨 | 경로 일치 |
| 4 | `/users/me/activities` | GET | 구현됨 | 경로 일치 |
| 5 | `/users/me/notifications` | GET | 구현됨 | 경로 일치 |
| 6 | `/users/me/notifications` | PUT | 구현됨 | 경로 일치 |

**상태**: 모든 엔드포인트 구현됨

---

## 4. 경로 불일치 목록

| Frontend 경로 | Backend 경로 | 불일치 유형 |
|--------------|-------------|------------|
| `/dashboard/activities` | `/dashboard/activity` | 복수형 vs 단수형 |
| `/admin/users/{id}/roles` | `/admin/users/{id}/role` | 복수형 vs 단수형 |

**권장사항**: Backend 경로를 Frontend에 맞춰 복수형으로 통일하거나, Frontend alias 추가

---

## 5. 미구현 API 우선순위별 정리

### P0 - Critical (즉시 구현 필요)

| # | 엔드포인트 | Method | 설명 | 담당 |
|---|-----------|--------|------|-----|
| 1 | `/api/v1/dashboard/health` | GET | 시스템 헬스체크 | Backend |
| 2 | `/api/v1/dashboard/search-trends` | GET | 검색 트렌드 (7일) | Backend |
| 3 | `/api/v1/dashboard/popular-queries` | GET | 인기 검색어 | Backend |
| 4 | `/api/v1/dashboard/document-types` | GET | 문서 유형 분포 | Backend |

### P1 - High (Sprint 내 구현)

| # | 엔드포인트 | Method | 설명 | 담당 |
|---|-----------|--------|------|-----|
| 5 | `/api/v1/graph/experts` | POST | 전문가 검색 | RAG/Backend |
| 6 | `/api/v1/documents/upload` | POST | 파일 업로드 (multipart) | Backend |
| 7 | `/api/v1/documents/{id}` | PUT | 문서 수정 (DocumentController) | Backend |

### P2 - Medium (다음 Sprint)

| # | 엔드포인트 | Method | 설명 | 담당 |
|---|-----------|--------|------|-----|
| 8 | `/api/v1/bookmarks/counts` | GET | 폴더별 북마크 수 | Backend |
| 9 | `/api/v1/auth/password-reset/request` | POST | 비밀번호 재설정 요청 | Backend |
| 10 | `/api/v1/auth/password-reset/confirm` | POST | 비밀번호 재설정 확인 | Backend |
| 11 | `/api/v1/admin/stats` | GET | 시스템 통계 | Backend |

### P3 - Low (경로 수정)

| # | 엔드포인트 | 수정 내용 | 담당 |
|---|-----------|----------|-----|
| 12 | `/dashboard/activity` | `activities`로 변경 | Backend |
| 13 | `/admin/users/{id}/role` | `roles`로 변경 | Backend |

---

## 6. 구현 권장 사항

### 6.1 Dashboard API 보완

```java
// DashboardController.java에 추가 필요

@GetMapping("/health")
public Mono<SystemHealth> getSystemHealth() { ... }

@GetMapping("/activities")  // 's' 추가
public Flux<ActivityResponse> getActivities(...) { ... }

@GetMapping("/search-trends")
public Flux<SearchTrend> getSearchTrends(@RequestParam int days) { ... }

@GetMapping("/popular-queries")
public Flux<PopularQuery> getPopularQueries(@RequestParam int limit) { ... }

@GetMapping("/document-types")
public Flux<DocumentTypeDistribution> getDocumentTypes() { ... }
```

### 6.2 Search API 보완

```java
// SearchController.java 또는 GraphController.java에 추가 필요

@PostMapping("/graph/experts")
public Flux<ExpertResponse> findExperts(@RequestBody ExpertSearchRequest request) { ... }
```

### 6.3 Document API 보완

```java
// DocumentController.java에 추가 필요

@PostMapping("/documents/upload")
public Mono<DocumentResponse> uploadFile(
    @RequestPart("file") FilePart file,
    @RequestPart(required = false) String metadata
) { ... }

@PutMapping("/documents/{id}")
public Mono<DocumentResponse> updateDocument(
    @PathVariable UUID id,
    @Valid @RequestBody DocumentUpdateRequest request
) { ... }
```

---

## 7. 결론

### 7.1 현황 요약

- **총 미구현 API**: 12개 (경로 불일치 2개 포함)
- **P0 Critical**: 4개 (Dashboard 관련)
- **P1 High**: 3개 (Search, Document 관련)
- **P2 Medium**: 4개 (Bookmark, Auth, Admin 관련)
- **P3 Low**: 2개 (경로명 통일)

### 7.2 권장 조치

1. **즉시 조치 (P0)**: Dashboard API 4개 엔드포인트 구현
2. **Sprint 내 (P1)**: Graph Expert 검색, 파일 업로드, 문서 수정 구현
3. **경로 통일**: `activity` -> `activities`, `role` -> `roles`

### 7.3 E2E 테스트 영향

현재 E2E 테스트에서 404 오류가 발생하는 주요 원인:
- `/api/v1/dashboard/health` - 미구현
- `/api/v1/dashboard/activities` - 경로 불일치
- `/api/v1/search` (키워드) - 실제로는 `/search/hybrid` 또는 `/search`로 매핑됨 (확인 필요)

---

## 부록: Frontend-Backend API 매핑 전체 목록

### A. 구현 완료 API (20개)

| Frontend | Backend | Method | 상태 |
|----------|---------|--------|------|
| `/auth/login` | `/api/v1/auth/login` | POST | OK |
| `/auth/logout` | `/api/v1/auth/logout` | POST | OK |
| `/auth/refresh` | `/api/v1/auth/refresh` | POST | OK |
| `/auth/me` | `/api/v1/auth/me` | GET | OK |
| `/search` | `/api/v1/search` | POST | OK |
| `/search/chat/stream` | `/api/v1/search/chat/stream` | POST | OK |
| `/documents` | `/api/v1/documents` | GET | OK |
| `/documents/{id}` | `/api/v1/documents/{id}` | GET | OK |
| `/documents` | `/api/v1/documents` | POST | OK |
| `/documents/{id}` | `/api/v1/documents/{id}` | DELETE | OK |
| `/documents/{id}/status` | `/api/v1/documents/{id}/status` | GET | OK |
| `/bookmarks` | `/api/v1/bookmarks` | GET | OK |
| `/bookmarks` | `/api/v1/bookmarks` | POST | OK |
| `/bookmarks/{id}` | `/api/v1/bookmarks/{id}` | PUT | OK |
| `/bookmarks/{id}` | `/api/v1/bookmarks/{id}` | DELETE | OK |
| `/users/me` | `/api/v1/users/me` | GET | OK |
| `/users/me` | `/api/v1/users/me` | PUT | OK |
| `/users/me/password` | `/api/v1/users/me/password` | PUT | OK |
| `/users/me/activities` | `/api/v1/users/me/activities` | GET | OK |
| `/users/me/notifications` | `/api/v1/users/me/notifications` | GET/PUT | OK |

### B. 미구현/불일치 API (12개)

| Frontend | Backend | Method | 상태 |
|----------|---------|--------|------|
| `/dashboard/health` | - | GET | **미구현** |
| `/dashboard/activities` | `/dashboard/activity` | GET | **경로 불일치** |
| `/dashboard/search-trends` | - | GET | **미구현** |
| `/dashboard/popular-queries` | - | GET | **미구현** |
| `/dashboard/document-types` | - | GET | **미구현** |
| `/graph/experts` | - | POST | **미구현** |
| `/documents/upload` | - | POST | **미구현** |
| `/documents/{id}` | - | PUT | **미구현** (DocumentController) |
| `/bookmarks/counts` | - | GET | **미구현** |
| `/auth/password-reset/request` | - | POST | **미구현** |
| `/auth/password-reset/confirm` | - | POST | **미구현** |
| `/admin/stats` | - | GET | **미구현** |
| `/admin/users/{id}/roles` | `/admin/users/{id}/role` | PUT | **경로 불일치** |

---

*보고서 끝*
