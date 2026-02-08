# STORY-095: [BUG] camelCase/snake_case 불일치 잔여 4건

## 메타데이터

| 항목 | 값 |
|------|-----|
| **ID** | STORY-095 |
| **Jira ID** | - |
| **Epic** | EPIC-006 API Quality & Consistency |
| **Status** | To Do |
| **Priority** | Medium |
| **Story Points** | 3 |
| **Assignee** | Backend/Frontend |
| **Sprint** | - |

---

## Bug Report

### Summary

API 엔드포인트 간 camelCase/snake_case 네이밍 컨벤션이 일관되지 않은 잔여 이슈 4건. 감사 보고서에서 식별됨.

### 잔여 불일치 목록

| # | 엔드포인트 | 파라미터 | 현재 | 기대 | 비고 |
|---|-----------|---------|------|------|------|
| 1 | `/search/chat/stream` | `top_k` vs `topK` | 혼재 | snake_case 통일 | 요청 파라미터 |
| 2 | `/search/chat/stream` | filters 내부 키 | camelCase | snake_case | 필터 객체 키 |
| 3 | `GET /documents` | `pageSize` vs `page_size` | camelCase | snake_case | 쿼리 파라미터 |
| 4 | `POST /documents/upload` | `projectName` vs `project_name` | camelCase | snake_case | 메타데이터 필드 |

### Convention Decision

- **API 응답/요청 (Python FastAPI)**: `snake_case` 표준
- **프론트엔드 내부**: `camelCase` (JavaScript 표준)
- **경계 (API 호출)**: snake_case로 통일, 프론트엔드에서 변환

---

## User Story

**As a** API 소비자 (프론트엔드 개발자),
**I want** 모든 API 파라미터가 일관된 네이밍 컨벤션을 따르길,
**So that** API 통합 시 혼란 없이 파라미터를 사용할 수 있습니다.

---

## Acceptance Criteria

- [ ] **Given** `/search/chat/stream` 요청, **When** top_k 파라미터 전송 시, **Then** snake_case `top_k`만 허용
- [ ] **Given** `/search/chat/stream` 요청, **When** filters 객체 전송 시, **Then** 내부 키가 모두 snake_case
- [ ] **Given** `GET /documents` 요청, **When** 페이지네이션 파라미터 전송 시, **Then** `page_size` (snake_case) 사용
- [ ] **Given** `POST /documents/upload` 요청, **When** 메타데이터 전송 시, **Then** `project_name` (snake_case) 사용
- [ ] **Given** 프론트엔드 API 호출, **When** 요청 전송 시, **Then** camelCase -> snake_case 자동 변환
- [ ] **Given** 기존 camelCase 파라미터, **When** 하위호환 기간, **Then** 양쪽 모두 허용 (deprecation warning)

---

## Tasks

- [ ] Backend: `/search/chat/stream` top_k 파라미터 통일
- [ ] Backend: `/search/chat/stream` filters 키 snake_case 정규화
- [ ] Backend: `GET /documents` page_size 파라미터 통일
- [ ] Backend: `POST /documents/upload` metadata 키 snake_case 정규화
- [ ] Backend: 하위호환 alias 추가 (camelCase -> snake_case 매핑)
- [ ] Frontend: API 호출 시 camelCase -> snake_case 변환 유틸리티
- [ ] Frontend: 응답 수신 시 snake_case -> camelCase 변환
- [ ] API 문서 업데이트 (OpenAPI spec)
- [ ] Unit Test: 양쪽 케이스 모두 동작 확인
- [ ] Integration Test: 프론트엔드 -> 백엔드 통합 테스트

---

## 기술 노트

### 구현 방향

1. **Backend (FastAPI)**:
   - Pydantic model에 `alias` 설정으로 양쪽 허용
   - 내부적으로는 snake_case로 처리
   ```python
   class SearchRequest(BaseModel):
       top_k: int = Field(default=5, alias="topK")

       class Config:
           populate_by_name = True
   ```

2. **Frontend (React/TypeScript)**:
   - API 클라이언트 레이어에서 자동 변환
   ```typescript
   // request: camelCase -> snake_case
   // response: snake_case -> camelCase
   ```

3. **Deprecation Strategy**:
   - Phase 1: 양쪽 모두 허용 (현재)
   - Phase 2: camelCase 사용 시 deprecation warning 로그
   - Phase 3: snake_case만 허용 (다음 major 버전)

### 영향 범위
- `knowledge_service/src/app/api/routes/search.py`
- `knowledge_service/src/app/api/routes/documents.py`
- `knowledge_service/frontend/src/services/api.ts`
- `knowledge_service/frontend/src/hooks/useSearch.ts`

### 감사 보고서
- `knowledge_service/docs/results/camelcase_snake_case_audit_report.md`

---

## 테스트 계획

- [ ] Unit Test: snake_case 파라미터 정상 동작
- [ ] Unit Test: camelCase alias 하위호환 동작
- [ ] Integration Test: 프론트엔드 API 호출 전체 흐름
- [ ] Regression Test: 기존 기능 정상 동작 확인

---

## 참고 자료

- 감사 보고서: `knowledge_service/docs/results/camelcase_snake_case_audit_report.md`
- FastAPI Pydantic alias: https://docs.pydantic.dev/latest/concepts/fields/#field-aliases
