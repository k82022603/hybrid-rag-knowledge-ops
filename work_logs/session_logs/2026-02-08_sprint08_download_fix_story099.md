# Session Log - 2026-02-08

**Session ID**: 2026-02-08_sprint08_download_fix_story099
**시작 시간**: 16:40 (이전 세션 이어서)
**종료 시간**: 18:02
**모델**: Claude Opus 4.6 (claude-opus-4-6)

---

## 세션 요약

STORY-092 다운로드 기능 수정, Graph 버튼 graphContext 매핑 수정, STORY-099 ETL document_id 정합성 수정 및 데이터 정리

---

## 완료된 작업

### 1. 다운로드 "Page Not Found" 수정 (STORY-092 - 주요)

#### 상세 내용
- **증상**: 다운로드 버튼 클릭 시 브라우저가 `http://localhost/app/data/uploads/...` 경로로 이동 → Page Not Found
- **근본 원인**: Frontend에서 AJAX로 JSON 응답을 받아 URL을 파싱하는 방식이 아닌, 로컬 파일 경로를 브라우저 URL로 열고 있었음
- **Backend 수정** (`documents.py`):
  - MinIO presigned URL → `RedirectResponse(url=download_url, status_code=302)` (기존 JSON → 302 리다이렉트)
  - 로컬 파일 → `FileResponse(path=local_path, filename=filename)` (기존 유지)
- **Frontend 수정** (`KeywordSearch.tsx`, `ChatSearch.tsx`):
  - AJAX `searchService.getDocumentDownloadUrl()` → `window.open(apiUrl, '_blank')` 직접 호출
  - 불필요한 `searchService` import 제거

### 2. Keyword Search Graph 버튼 미동작 수정 (주요)

#### 상세 내용
- **증상**: Graph 소스 타입 검색 결과에서 Graph 버튼 클릭해도 그래프 패널 미표시
- **근본 원인**: Backend `metadata.matched_entities` → Frontend `graphContext.relatedEntities` 매핑 누락
- **수정** (`searchService.ts`): `metadata.matched_entities`를 `graphContext.relatedEntities`로 매핑 추가

### 3. STORY-099 ETL document_id 정합성 수정 (주요)

#### 상세 내용

**근본 원인 분석**:
- `initial_data_loader.py` Line 708: `document_id = str(uuid4())` 자체 UUID 생성
- ES/Neo4j에만 저장, PostgreSQL 미연동 → ES document_id ≠ PG id
- 다운로드 API가 PG에서 문서를 찾지 못해 404 에러

**코드 수정** (`initial_data_loader.py`):
1. `_store_to_postgresql()` 신규 메서드 추가 (Line 1061-1117)
   - `document_repository.save()` 활용하여 PG UPSERT
   - ImportError/Exception graceful 처리
2. `_store_document()` 수정 (Line 998-1059)
   - 저장 순서: PostgreSQL(SSOT) → Elasticsearch → Neo4j
   - PG 저장 결과의 doc_id를 ES/Neo4j에 전달
3. `metadata.title` fallback 추가 (Line 1028-1030)
   - `file_info.file_name` 사용으로 임시파일명 방지

**데이터 정리**:
- 시드 데이터(doc-001~006) 18건 ES 삭제
- 임시/테스트 데이터(tmp*, test_*) 20건 ES 삭제
- PG에 없는 고아 ES 청크 4건 삭제
- 정리 후 PG-ES 정합성 100% (2건 매칭)
- Redis 캐시 FLUSHALL

**검증**: `_store_to_postgresql()` 단위 테스트 성공 (PG 저장 → 조회 → 삭제)

### 4. STORY-098/099 백로그 등록 (부가)

#### 상세 내용
- STORY-098: Administration Redis Cache Reset 기능 (3 SP, Medium)
- STORY-099: ETL/ES Document ID 정합성 수정 (5 SP, High → Done)

### 5. 이슈 보고서 작성 (부가)

#### 상세 내용
- `docs/03_implementation/story099_document_id_consistency_report.md` 작성
- 데이터 흐름도(Mermaid), 근본 원인 분석, 데이터 현황, 수정 내역, 영향 분석 포함

---

## 주요 결정사항

| 결정 | 내용 | 근거 |
|------|------|------|
| RedirectResponse 방식 | MinIO URL은 302 리다이렉트로 제공 | JWT 인증 유지 + 브라우저 직접 다운로드 |
| PG SSOT 저장 순서 | PG → ES → Neo4j 순서 | PG가 SSOT이므로 가장 먼저 저장해야 ID 정합성 보장 |
| ES 불일치 데이터 삭제 | PG에 없는 ES 청크 전체 삭제 | 정합성 확보가 불완전 데이터보다 우선 |
| metadata.title fallback | file_info.file_name 사용 | 임시파일명(tmpXXX) 방지 |

---

## 변경된 파일 목록

```
knowledge_service/
├── src/app/
│   ├── api/routes/documents.py              # RedirectResponse/FileResponse 분기
│   └── services/initial_data_loader.py      # _store_to_postgresql() 추가, 저장 순서 수정
├── frontend/src/
│   ├── services/searchService.ts            # graphContext 매핑 추가
│   └── features/search/
│       ├── KeywordSearch.tsx                 # window.open 다운로드
│       └── ChatSearch.tsx                    # window.open 다운로드
├── docs/03_implementation/
│   └── story099_document_id_consistency_report.md  # 이슈 보고서 (신규)
backlog/stories/
├── STORY-098-admin-redis-cache-reset.md     # 신규
└── STORY-099-document-id-consistency-etl-es.md  # 신규 → Done
```

---

## 현재 프로젝트 상태

### 인프라 상태
| 항목 | 값 |
|------|-----|
| 총 컨테이너 | 18개 (전체 Running) |
| AI Service | Healthy (STORY-099 리빌드 배포) |
| Frontend | Healthy (다운로드 수정 배포) |
| Redis | Healthy (FLUSHALL 후) |
| PG-ES 정합성 | 100% (2건 매칭) |

### Sprint 상태
| 항목 | 값 |
|------|-----|
| Sprint | 08 (Day 4) |
| STORY-092 | Done (다운로드 기능 수정) |
| STORY-099 | Done (document_id 정합성) |
| STORY-098 | To Do (Redis Cache Reset) |

---

## 다음 작업 (Action Items)

### P1 (High)
1. knowledge_data 볼륨 마운트 추가 → 시드 데이터 InitialDataLoader 재적재

### P2 (Medium)
2. STORY-098: Administration Redis Cache Reset 기능
3. STORY-093: Content Viewer 모달
4. STORY-094: 문서 제목 추출 개선

### P3 (Low)
5. PG es_synced 플래그 업데이트 (InitialDataLoader 완료 후)
6. 기존 uploaded 문서(2건)의 ES 재색인

---

## 리스크 모니터링

| 리스크 | 확률 | 영향 | 상태 | 대응 |
|--------|------|------|------|------|
| knowledge_data 미마운트 | Med | Med | Open | Docker Compose 볼륨 추가 예정 |
| 대량 문서 임베딩 시 PG 부하 | Low | Med | Monitoring | UPSERT 사용으로 중복 방지 |

---

## 사용된 도구 및 에이전트

| 도구/에이전트 | 용도 |
|--------------|------|
| Explore | 다운로드 흐름 분석, ES/PG 데이터 조사 |
| Plan | STORY-099 구현 계획 수립 |
| Docker Compose | AI Service 리빌드/배포 |

---

## 세션 통계

| 항목 | 값 |
|------|-----|
| 수정된 파일 | 5개 (Python 2, TypeScript 3) |
| 신규 생성 파일 | 3개 (보고서 1, 백로그 2) |
| 배포 횟수 | 2회 (Frontend 1, AI Service 1) |
| ES 데이터 정리 | 42건 삭제 |
| PG-ES 정합성 | 100% 달성 |

---

*기록자: Claude Code (Opus 4.6)*
*기록 시간: 2026-02-08 18:02 KST*
