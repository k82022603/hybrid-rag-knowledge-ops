# STORY-001: 문서 업로드 API

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-6 |
| **Epic** | EPIC-001 |
| **Status** | **Done** ✅ (2026-01-27) |
| **Priority** | High |
| **Story Points** | 3 |
| **Assignee** | RAG |
| **Sprint** | 2 |

---

## User Story

**As a** 지식 관리자,
**I want** 다양한 형식의 문서를 시스템에 업로드,
**So that** 문서가 자동으로 처리되어 검색 가능한 지식으로 변환됨.

---

## Acceptance Criteria

- [ ] **Given** 사용자가 PDF 파일을 선택, **When** 업로드 버튼 클릭, **Then** 파일이 MinIO에 저장되고 처리 대기열에 추가됨
- [ ] **Given** 지원하지 않는 형식(exe 등), **When** 업로드 시도, **Then** 400 에러와 함께 지원 형식 안내
- [ ] **Given** 100MB 초과 파일, **When** 업로드 시도, **Then** 413 에러와 함께 크기 제한 안내
- [ ] **Given** 업로드 완료, **When** 응답 반환, **Then** document_id와 처리 상태 URL 포함

---

## Tasks

- [ ] FastAPI 엔드포인트 구현 (`POST /api/v1/documents`)
- [ ] 파일 검증 로직 (형식, 크기, 바이러스 스캔)
- [ ] MinIO 업로드 서비스 구현
- [ ] PostgreSQL 메타데이터 저장
- [ ] Celery 태스크 트리거
- [ ] 단위 테스트 작성
- [ ] API 문서 (OpenAPI) 업데이트

---

## 기술 노트

### API 스펙
```python
@router.post("/api/v1/documents")
async def upload_document(
    file: UploadFile,
    metadata: DocumentMetadata = None
) -> DocumentResponse:
    """
    Returns:
        - document_id: UUID
        - status: "queued"
        - status_url: "/api/v1/documents/{id}/status"
    """
```

### 지원 형식
| 형식 | MIME Type | 최대 크기 |
|------|-----------|-----------|
| PDF | application/pdf | 100MB |
| DOCX | application/vnd.openxmlformats-officedocument.wordprocessingml.document | 50MB |
| HWP | application/x-hwp | 50MB |
| PPTX | application/vnd.openxmlformats-officedocument.presentationml.presentation | 100MB |

### 영향 범위
- `knowledge_service/src/app/api/routes/documents.py`
- `knowledge_service/src/app/services/storage.py`
- `knowledge_service/src/app/models/document.py`

---

## 테스트 계획

- [ ] Unit Test: 파일 검증 로직
- [ ] Unit Test: MinIO 업로드 mock
- [ ] Integration Test: 전체 업로드 플로우
- [ ] Load Test: 동시 10개 업로드

---

## 참고 자료

- [API 통합 설계서](../../knowledge_service/docs/02_design/api_integration_design.md)
- [MinIO Python SDK](https://min.io/docs/minio/linux/developers/python/API.html)
