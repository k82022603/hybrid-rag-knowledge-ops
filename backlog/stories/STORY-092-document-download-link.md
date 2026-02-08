# STORY-092: [FEAT] 검색 결과에 원본 문서 다운로드 링크 제공

## 메타데이터

| 항목 | 값 |
|------|-----|
| **ID** | STORY-092 |
| **Jira ID** | - |
| **Epic** | EPIC-004 Search & Retrieval |
| **Status** | Done |
| **Priority** | High |
| **Story Points** | 5 |
| **Assignee** | Backend/Frontend |
| **Sprint** | - |

---

## User Story

**As a** 지식 검색 사용자,
**I want** 검색 결과에서 원본 문서를 다운로드할 수 있길,
**So that** 검색된 청크의 전체 문맥을 원본 파일로 확인할 수 있습니다.

---

## Problem Statement

현재 검색 결과에 `document_id`는 포함되어 있지만 원본 문서에 접근할 수 있는 방법이 없음. MinIO에 원본 파일이 저장되어 있으며, presigned URL 생성이 가능한 상태.

---

## Acceptance Criteria

- [ ] **Given** 검색 결과 카드, **When** 다운로드 버튼 클릭 시, **Then** 원본 문서가 다운로드됨
- [ ] **Given** `/documents/{document_id}/download` API 호출 시, **When** 유효한 document_id, **Then** MinIO presigned URL 반환
- [ ] **Given** presigned URL, **When** 브라우저에서 접근 시, **Then** 원본 파일이 다운로드됨
- [ ] **Given** 존재하지 않는 document_id, **When** 다운로드 요청 시, **Then** 404 오류 반환
- [ ] **Given** 만료된 presigned URL, **When** 접근 시, **Then** 적절한 오류 메시지 표시

---

## Tasks

- [ ] Backend: `/documents/{document_id}/download` API 엔드포인트 구현
- [ ] Backend: MinIO presigned URL 생성 서비스 구현
- [ ] Backend: document_id -> MinIO object_key 매핑 조회
- [ ] Frontend: SearchResultCard에 다운로드 버튼 추가
- [ ] Frontend: 다운로드 버튼 클릭 핸들러 구현
- [ ] Unit Test: 다운로드 API 테스트
- [ ] Integration Test: MinIO presigned URL 생성 테스트

---

## 기술 노트

### 구현 방향

1. **API 엔드포인트**: `GET /api/v1/documents/{document_id}/download`
   - PostgreSQL에서 document_id로 MinIO object_key 조회
   - MinIO Client로 presigned URL 생성 (유효기간: 1시간)
   - presigned URL을 응답으로 반환

2. **MinIO Presigned URL**:
   ```python
   from minio import Minio

   url = minio_client.presigned_get_object(
       bucket_name="documents",
       object_name=object_key,
       expires=timedelta(hours=1)
   )
   ```

3. **Frontend**: SearchResultCard에 다운로드 아이콘 버튼 추가
   - 클릭 시 API 호출 -> presigned URL 수신 -> window.open() 또는 anchor download

### 영향 범위
- `knowledge_service/src/app/api/routes/documents.py` - 새 엔드포인트
- `knowledge_service/src/app/services/document_service.py` - MinIO URL 생성
- `knowledge_service/frontend/src/components/SearchResultCard.tsx` - 다운로드 버튼
- MinIO 버킷 접근 권한 확인 필요

### 의존성
- MinIO 컨테이너 정상 동작
- PostgreSQL documents 테이블에 minio_object_key 컬럼 존재 확인

---

## 테스트 계획

- [ ] Unit Test: presigned URL 생성 로직
- [ ] Integration Test: MinIO 연동 다운로드 흐름
- [ ] E2E Test: 검색 결과에서 다운로드 버튼 클릭 -> 파일 다운로드

---

## 참고 자료

- MinIO Python SDK: presigned_get_object
- 현재 문서 업로드 구현: `knowledge_service/src/app/services/document_service.py`
