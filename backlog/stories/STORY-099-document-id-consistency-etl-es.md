# STORY-099: [FIX] ETL/ES 문서 ID 정합성 및 다운로드 경로 수정

## 메타데이터

| 항목 | 값 |
|------|-----|
| **ID** | STORY-099 |
| **Epic** | EPIC-003 Data Pipeline |
| **Status** | Done |
| **Priority** | High |
| **Story Points** | 5 |
| **Assignee** | ETL/Backend |
| **Sprint** | - |

---

## User Story

**As a** 지식 검색 사용자,
**I want** 검색 결과에서 원본 문서를 다운로드할 때 실제 파일이 정상적으로 다운로드되길,
**So that** 검색된 청크의 원본 문서를 확인할 수 있습니다.

---

## Problem Statement

현재 다운로드 기능(STORY-092)이 구현되었으나 실제 다운로드가 되지 않는 문제:

1. **document_id 불일치**: ES 청크의 `document_id`와 PostgreSQL `documents.id`가 다름
   - ES: `9dbc5666-...` (ETL 파이프라인에서 생성한 ID)
   - PG: `f1801c3b-...` (업로드 API에서 생성한 ID)
   - 같은 문서인데 ID가 다름 → download API에서 문서 조회 실패

2. **파일명 불일치**: ES 메타데이터에 임시파일명 저장됨
   - ES 메타데이터: `tmpgy5xpae3.pptx` (파이썬 tempfile 이름)
   - 실제 파일명: `K-에듀파인 대참제 해소-기안기 업무관리 구조개선-20260204.pptx`

3. **파일 경로 불일치**: PostgreSQL `file_path`와 실제 컨테이너 내 파일 위치 불일치
   - PG: `2026/02/f1801c3b-.../K-에듀파인...pptx` (상대 경로)
   - 컨테이너: `/app/data/uploads/documents/` 디렉토리가 비어있음

---

## Acceptance Criteria

- [ ] **Given** 문서 업로드 시, **When** ETL 파이프라인이 ES에 청크를 인덱싱할 때, **Then** PostgreSQL의 `documents.id`와 동일한 `document_id`를 사용
- [ ] **Given** ES 청크 메타데이터, **When** `title` 필드 저장 시, **Then** 실제 파일명 사용 (임시파일명 아님)
- [ ] **Given** 다운로드 API 호출 시, **When** 유효한 document_id, **Then** 실제 파일이 존재하고 다운로드 가능

---

## Tasks

- [ ] ETL 파이프라인에서 document_id 생성 로직 확인 및 PG ID와 동기화
- [ ] ES 인덱싱 시 메타데이터에 실제 파일명 저장
- [ ] 문서 업로드 시 실제 파일 저장 경로 확인 및 수정
- [ ] 기존 데이터 마이그레이션 (ES document_id → PG id 매핑)

---

## 기술 노트

### 현재 데이터 상태 (2026-02-08 조사)

```
PostgreSQL documents 테이블:
  id=f1801c3b  title=K-에듀파인...pptx  file_path=2026/02/f1801c3b-.../K-에듀파인...pptx  status=uploaded
  id=d40d3289  title=MSA_차세대플랫폼...pptx  file_path=2026/02/d40d3289-.../MSA_차세대플랫폼...pptx  status=uploaded

ES 청크 (search 결과):
  document_id=9dbc5666  metadata.title=tmpgy5xpae3.pptx  ← PG에 없는 ID + 임시파일명
  document_id=022cb660  metadata.title=tmpgy5xpae3.pptx
```

### 근본 원인
ETL 파이프라인(`ingest_and_index`)이 문서를 처리할 때 새로운 UUID를 생성하여 ES에 저장하는 것으로 추정. PG의 document_id를 전달받지 않거나 무시하고 있을 가능성.
