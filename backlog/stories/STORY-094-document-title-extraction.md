# STORY-094: [BUG] 문서 제목이 파일명으로만 표시됨

## 메타데이터

| 항목 | 값 |
|------|-----|
| **ID** | STORY-094 |
| **Jira ID** | - |
| **Epic** | EPIC-003 Document Processing |
| **Status** | To Do |
| **Priority** | Medium |
| **Story Points** | 3 |
| **Assignee** | ETL/RAG |
| **Sprint** | - |

---

## Bug Report

### Summary

검색 결과 및 문서 목록에서 문서 제목이 의미 있는 이름 대신 파일명(예: `test_doc_1.txt`, `report_2024Q3.pptx`)으로만 표시됨. 메타데이터에 의미 있는 제목 정보가 추출되지 않아 사용자가 문서를 식별하기 어려움.

### Current Behavior

- 문서 제목: `test_doc_1.txt` (파일명 그대로)
- 검색 결과에서 어떤 문서인지 빠르게 파악 불가
- 동일 이름의 파일이 여러 개일 경우 구분 불가

### Expected Behavior

- 문서 제목: "2024년 3분기 실적 보고서" (내용 기반 추출)
- 파일 내 첫 번째 제목/헤딩 또는 메타데이터에서 제목 추출
- 추출 실패 시 파일명을 fallback으로 사용

---

## User Story

**As a** 지식 검색 사용자,
**I want** 문서 제목이 파일명이 아닌 의미 있는 제목으로 표시되길,
**So that** 검색 결과에서 문서를 빠르게 식별할 수 있습니다.

---

## Acceptance Criteria

- [ ] **Given** 문서 파싱 시, **When** 파일 내 제목 메타데이터가 존재할 때, **Then** 해당 제목이 document title로 저장됨
- [ ] **Given** PPTX 파일, **When** 첫 슬라이드 제목이 존재할 때, **Then** 첫 슬라이드 제목을 문서 제목으로 사용
- [ ] **Given** PDF 파일, **When** 문서 메타데이터에 title이 있을 때, **Then** 메타데이터 title 사용
- [ ] **Given** 텍스트 파일, **When** 첫 번째 라인이 헤딩 형식일 때, **Then** 첫 번째 라인을 제목으로 사용
- [ ] **Given** 제목 추출 실패 시, **When** fallback 로직 적용, **Then** 파일명을 제목으로 사용
- [ ] **Given** 추출된 제목, **When** 검색 결과 및 문서 목록 표시 시, **Then** 의미 있는 제목이 표시됨

---

## Tasks

- [ ] ETL: Docling 파서에서 문서 제목 추출 로직 추가
- [ ] ETL: 파일 포맷별 제목 추출 전략 구현
  - PPTX: 첫 슬라이드 제목
  - PDF: 문서 메타데이터 title 또는 첫 번째 헤딩
  - DOCX: 문서 속성 title 또는 첫 번째 헤딩
  - TXT/MD: 첫 번째 라인 (# 헤딩 또는 첫 줄)
- [ ] ETL: PostgreSQL documents 테이블에 extracted_title 저장
- [ ] Backend: 문서 조회 API에서 extracted_title 반환
- [ ] Frontend: 문서 목록/검색 결과에서 extracted_title 우선 표시
- [ ] 기존 문서 재처리 마이그레이션 스크립트 (선택)
- [ ] Unit Test: 포맷별 제목 추출 테스트

---

## 기술 노트

### 구현 방향

1. **제목 추출 우선순위**:
   ```
   1. 파일 메타데이터 title (PDF properties, DOCX properties)
   2. 첫 번째 헤딩/제목 요소
   3. 첫 번째 라인 (100자 이내 truncate)
   4. 파일명 (fallback)
   ```

2. **Docling 통합**: Docling 파서 출력에서 구조화된 제목 정보 활용

3. **DB 스키마**: `documents` 테이블에 `extracted_title` 컬럼 추가 (nullable)

### 영향 범위
- `knowledge_service/src/app/services/document_parser.py` - 제목 추출 로직
- `knowledge_service/src/app/models/document.py` - extracted_title 필드
- PostgreSQL documents 테이블 마이그레이션
- 프론트엔드 문서 표시 컴포넌트

---

## 테스트 계획

- [ ] Unit Test: PPTX 제목 추출
- [ ] Unit Test: PDF 제목 추출
- [ ] Unit Test: TXT/MD 제목 추출
- [ ] Unit Test: fallback 로직 (제목 없을 때 파일명 사용)
- [ ] Integration Test: 문서 업로드 -> 제목 추출 -> DB 저장 -> API 조회

---

## 참고 자료

- Docling 파서 구현: `knowledge_service/src/app/services/document_parser.py`
- 현재 문서 모델: `knowledge_service/src/app/models/document.py`
