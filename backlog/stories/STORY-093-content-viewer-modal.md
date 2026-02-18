# STORY-093: [FEAT] 검색 결과 청크 내용 전문 조회 (Content Viewer)

## 메타데이터

| 항목 | 값 |
|------|-----|
| **ID** | STORY-093 |
| **Jira ID** | - |
| **Epic** | EPIC-004 Search & Retrieval |
| **Status** | Deferred (Sprint 12 project closure) |
| **Priority** | Medium |
| **Story Points** | 3 |
| **Assignee** | Frontend/RAG |
| **Sprint** | - |

---

## User Story

**As a** 지식 검색 사용자,
**I want** 검색 결과 청크를 클릭하면 전문을 볼 수 있길,
**So that** 검색 결과의 전체 내용을 확인하고 관련성을 판단할 수 있습니다.

---

## Problem Statement

현재 검색 결과는 청크의 일부분만 표시(truncated). 사용자가 청크 전문을 확인하려면 원본 문서를 별도로 찾아야 하는 불편함 존재. 클릭 시 전문을 보여주는 Content Viewer 모달이 필요.

---

## Acceptance Criteria

- [ ] **Given** 검색 결과 카드, **When** 카드 클릭 또는 "더 보기" 버튼 클릭 시, **Then** Content Viewer 모달이 열림
- [ ] **Given** Content Viewer 모달, **When** 열리면, **Then** 해당 청크의 전문 내용이 표시됨
- [ ] **Given** API `/chunks/{document_id}/{chunk_id}`, **When** 유효한 ID로 호출 시, **Then** 청크 전문 반환
- [ ] **Given** Content Viewer, **When** 메타데이터 섹션 확인 시, **Then** 문서명, 페이지, 검색 점수 등 표시
- [ ] **Given** Content Viewer, **When** Escape 키 또는 외부 클릭 시, **Then** 모달이 닫힘

---

## Tasks

- [ ] Backend: `/api/v1/chunks/{document_id}/{chunk_id}` 전문 조회 API 구현
- [ ] Backend: Elasticsearch에서 chunk 전문 조회 서비스
- [ ] Frontend: ContentViewerModal 컴포넌트 구현
- [ ] Frontend: SearchResultCard에 클릭 핸들러 연결
- [ ] Frontend: 모달 내 메타데이터 표시 (문서명, 페이지, 점수, 소스)
- [ ] Frontend: 키보드 접근성 (Escape 닫기, Tab 포커스 관리)
- [ ] Unit Test: 전문 조회 API 테스트
- [ ] E2E Test: 카드 클릭 -> 모달 열림 -> 내용 확인

---

## 기술 노트

### 구현 방향

1. **API 엔드포인트**: `GET /api/v1/chunks/{document_id}/{chunk_id}`
   - Elasticsearch에서 document_id + chunk_id로 청크 전문 조회
   - 메타데이터(문서명, 페이지 번호, 섹션) 포함 반환

2. **Frontend Content Viewer Modal**:
   - Headless UI Dialog 또는 Tailwind Modal 사용
   - 상단: 문서 제목, 소스 타입 배지
   - 본문: 청크 전문 (마크다운 렌더링 지원)
   - 하단: 메타데이터 (페이지, 점수, document_id)
   - 액션: 원본 다운로드 버튼 (STORY-092 연동)

3. **UX 고려사항**:
   - 모달 열 때 로딩 스피너 표시
   - 긴 텍스트 스크롤 처리
   - 코드 블록 syntax highlighting (해당 시)

### 영향 범위
- `knowledge_service/src/app/api/routes/chunks.py` - 새 엔드포인트
- `knowledge_service/frontend/src/components/ContentViewerModal.tsx` - 새 컴포넌트
- `knowledge_service/frontend/src/components/SearchResultCard.tsx` - 클릭 핸들러

### 의존성
- STORY-092 (원본 다운로드 링크) - 모달 내 다운로드 버튼 연동

---

## 테스트 계획

- [ ] Unit Test: chunk 전문 조회 API
- [ ] Unit Test: ContentViewerModal 컴포넌트 렌더링
- [ ] Integration Test: 검색 -> 카드 클릭 -> 전문 조회 흐름
- [ ] E2E Test: 전체 UX 흐름

---

## 참고 자료

- 현재 SearchResultCard 구현: `knowledge_service/frontend/src/components/SearchResultCard.tsx`
- Headless UI Dialog: https://headlessui.com/react/dialog
