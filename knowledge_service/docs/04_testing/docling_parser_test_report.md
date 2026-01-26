# Docling Document Parser 테스트 보고서

**날짜**: 2026-01-26
**스토리**: STORY-002
**담당**: QA Engineer
**문서 버전**: 1.0

---

## 테스트 실행 환경

| 항목 | 값 |
|------|-----|
| Python 버전 | 3.12.3 |
| pytest 버전 | 9.0.2 |
| OS | Linux 6.6.87.2 (WSL2) |
| 실행 디렉토리 | `knowledge_service/` |
| 테스트 파일 | `src/tests/unit/test_document_parser.py` |
| 실행 명령 | `pytest src/tests/unit/test_document_parser.py -v --tb=short --noconftest` |
| 총 소요 시간 | 9.42s |

### 환경 참고사항
- `conftest.py`에서 `langgraph` 모듈 의존성으로 인해 `--noconftest` 옵션 사용
- `pytest-cov` 미설치로 커버리지 수치 측정 불가 (코드 리뷰 기반 추정)

---

## 테스트 결과 요약

| 항목 | 값 |
|------|-----|
| 총 테스트 | 37개 |
| 통과 (PASSED) | 35개 |
| 실패 (FAILED) | 1개 |
| 스킵 (SKIPPED) | 1개 |
| 통과율 | **94.6%** (35/37) |
| 실질 통과율 | **97.2%** (35/36, 스킵 제외) |

---

## 테스트 클래스별 상세 결과

### 1. TestParsedDocumentModel (8/8 PASSED)

| # | 테스트 케이스 | 결과 | 설명 |
|---|-------------|------|------|
| 1 | `test_create_from_file_path_pdf` | PASSED | PDF 경로로 문서 생성 |
| 2 | `test_create_from_file_path_docx` | PASSED | DOCX 경로로 문서 생성 |
| 3 | `test_create_from_file_path_hwp` | PASSED | HWP 경로로 문서 생성 |
| 4 | `test_create_from_file_path_markdown` | PASSED | Markdown 경로로 문서 생성 |
| 5 | `test_create_from_file_path_unknown` | PASSED | 미지원 형식 처리 |
| 6 | `test_is_successful` | PASSED | 파싱 성공 여부 판별 |
| 7 | `test_has_tables` | PASSED | 표 포함 여부 판별 |
| 8 | `test_has_images` | PASSED | 이미지 포함 여부 판별 |

### 2. TestTableModel (3/3 PASSED)

| # | 테스트 케이스 | 결과 | 설명 |
|---|-------------|------|------|
| 1 | `test_table_to_markdown` | PASSED | 표 -> Markdown 변환 |
| 2 | `test_table_with_existing_markdown` | PASSED | 기존 Markdown 보존 |
| 3 | `test_empty_table` | PASSED | 빈 표 처리 |

### 3. TestSectionModel (2/2 PASSED)

| # | 테스트 케이스 | 결과 | 설명 |
|---|-------------|------|------|
| 1 | `test_section_creation` | PASSED | 섹션 생성 |
| 2 | `test_nested_sections` | PASSED | 중첩 섹션 |

### 4. TestDocumentParser (12/12 PASSED)

| # | 테스트 케이스 | 결과 | 설명 |
|---|-------------|------|------|
| 1 | `test_supports_format` | PASSED | 형식 지원 여부 확인 |
| 2 | `test_get_format` | PASSED | 파일 형식 반환 |
| 3 | `test_parse_markdown_file` | PASSED | Markdown 파싱 (섹션, 표, 이미지) |
| 4 | `test_parse_text_file` | PASSED | 텍스트 파싱 |
| 5 | `test_parse_text_file_korean` | PASSED | 한글 텍스트 파싱 (인코딩) |
| 6 | `test_parse_html_file` | PASSED | HTML 파싱 (script 태그 제외) |
| 7 | `test_parse_nonexistent_file` | PASSED | 존재하지 않는 파일 처리 |
| 8 | `test_parse_unsupported_format` | PASSED | 미지원 형식 에러 처리 |
| 9 | `test_parse_batch` | PASSED | 배치 파싱 (3개 파일) |
| 10 | `test_parse_batch_with_errors` | PASSED | 배치 파싱 에러 처리 |
| 11 | `test_retry_on_failure` | PASSED | 재시도 로직 (성공 경로) |
| 12 | `test_max_retries_exceeded` | PASSED | 재시도 초과 + 수동 검토 플래그 |

### 5. TestDoclingAdapter (3/3 PASSED, 1 SKIPPED)

| # | 테스트 케이스 | 결과 | 설명 |
|---|-------------|------|------|
| 1 | `test_supports_format` | PASSED | Docling 지원 형식 확인 |
| 2 | `test_parse_nonexistent_file` | PASSED | 존재하지 않는 파일 처리 |
| 3 | `test_parse_unsupported_format` | PASSED | 미지원 형식 처리 |
| 4 | `test_parse_pdf_with_tables` | **SKIPPED** | Docling 설치 필요 (의도적 스킵) |

### 6. TestMarkdownTableExtraction (1/2 - 1 FAILED)

| # | 테스트 케이스 | 결과 | 설명 |
|---|-------------|------|------|
| 1 | `test_extract_simple_table` | **FAILED** | 구분선이 데이터 행으로 파싱됨 |
| 2 | `test_extract_multiple_tables` | PASSED | 여러 표 추출 |

### 7. TestMarkdownSectionExtraction (1/1 PASSED)

| # | 테스트 케이스 | 결과 | 설명 |
|---|-------------|------|------|
| 1 | `test_extract_sections` | PASSED | 섹션 추출 (H1, H2, H3) |

### 8. TestParseResult (2/2 PASSED)

| # | 테스트 케이스 | 결과 | 설명 |
|---|-------------|------|------|
| 1 | `test_parse_result_success` | PASSED | 성공 결과 모델 |
| 2 | `test_parse_result_with_warnings` | PASSED | 경고 포함 결과 모델 |

### 9. TestBatchParseResult (1/1 PASSED)

| # | 테스트 케이스 | 결과 | 설명 |
|---|-------------|------|------|
| 1 | `test_batch_result` | PASSED | 배치 결과 모델 |

### 10. TestConvenienceFunctions (2/2 PASSED)

| # | 테스트 케이스 | 결과 | 설명 |
|---|-------------|------|------|
| 1 | `test_get_parser` | PASSED | 싱글톤 인스턴스 확인 |
| 2 | `test_parse_document` | PASSED | 편의 함수 동작 |

---

## 발견된 이슈

### ISSUE-001: Markdown 표 구분선(separator line) 파싱 버그

- **심각도**: Medium
- **테스트**: `TestMarkdownTableExtraction::test_extract_simple_table`
- **파일**: `knowledge_service/src/app/etl/parser.py` (line 486)
- **증상**: `table.rows`가 기대값 2 대신 3을 반환

**상세 분석**:

`_parse_markdown_table()` 메서드에서 Markdown 표의 구분선(`|---|---|`)을 건너뛰기 위한 정규식이 다중 열(multi-column) 구분선을 올바르게 인식하지 못합니다.

```python
# 현재 정규식 (버그)
if re.match(r"^\|[\s\-:]+\|$", line):
    continue
```

- 이 정규식은 `|---|`(단일 열)은 매칭하지만, `|---|---|`(다중 열)은 매칭하지 못합니다.
- 이유: 문자 클래스 `[\s\-:]`에 파이프 문자(`|`)가 포함되어 있지 않아, 중간의 `|` 구분자를 만나면 매칭에 실패합니다.
- 결과: 구분선이 데이터 행으로 처리되어 `---`가 셀 데이터로 추출됩니다.

**재현 데이터**:

입력:
```markdown
| A | B |
|---|---|
| 1 | 2 |
```

기대 결과: `rows=2` (헤더 + 데이터 1행)
실제 결과: `rows=3` (헤더 + 구분선(데이터로 잘못 파싱) + 데이터 1행)

**권장 수정**:

정규식을 다중 열 구분선도 매칭하도록 변경:
```python
# 수정안 1: 파이프 문자를 문자 클래스에 포함
if re.match(r"^\|[\s\-:|]+$", line):
    continue

# 수정안 2: 보다 정확한 패턴
if re.match(r"^\|(\s*:?-+:?\s*\|)+$", line):
    continue
```

**영향 범위**: Markdown 문서의 다중 열 표 파싱 시 행 수가 과다 집계되며, 구분선 문자(`---`)가 데이터로 오염됩니다. `test_extract_multiple_tables` 테스트는 rows 수가 아닌 표 개수만 검증하므로 통과합니다.

---

### ISSUE-002: conftest.py langgraph 의존성

- **심각도**: Low
- **파일**: `knowledge_service/src/tests/conftest.py` (line 11)
- **증상**: `langgraph` 모듈이 설치되지 않은 환경에서 `conftest.py` 로드 실패
- **영향**: `--noconftest` 옵션 없이는 모든 단위 테스트 실행 불가
- **권장 수정**: conftest.py에서 `langgraph` 의존 import를 조건부로 변경하거나, 단위 테스트용 별도 conftest를 분리

---

### NOTICE-001: Pydantic Deprecation 경고 (47건)

- **심각도**: Low (향후 Pydantic V3에서 문제 가능)
- **경고 내용**:
  - `class Config` -> `ConfigDict` 마이그레이션 필요 (5건)
  - `datetime.utcnow()` -> `datetime.now(datetime.UTC)` 변경 필요 (41건)
- **해당 파일**:
  - `src/app/models/document.py` (5건 - class Config 관련)
  - `src/app/models/parsed_document.py` (1건 - class Config, parsed_at 필드)

---

## 테스트 커버리지 추정

> `pytest-cov` 미설치로 정확한 커버리지 측정 불가. 코드 리뷰 기반 추정치입니다.

### 파일별 커버리지 추정

| 파일 | 추정 커버리지 | 비고 |
|------|-------------|------|
| `parsed_document.py` | ~90% | 모든 모델, from_file_path, to_markdown, 프로퍼티 테스트 완료 |
| `parser.py` | ~75% | Markdown/Text/HTML 파싱 완료. HWP는 미실행 (pyhwpx 미설치). Docling 경로는 어댑터로 위임만 테스트 |
| `docling_adapter.py` | ~30% | supports_format, 파일 미존재/미지원 형식만 테스트. 실제 Docling 파싱 미테스트 (외부 의존성) |

### 미테스트 영역

| 영역 | 사유 |
|------|------|
| `_parse_hwp()` | pyhwpx/hwp5 미설치 환경 |
| `_parse_with_docling()` | Docling 미설치 환경 |
| `_convert_result()` (DoclingAdapter) | 실제 Docling 결과 객체 필요 |
| `_extract_text/metadata/sections/tables/images` (DoclingAdapter) | 실제 Docling 문서 객체 필요 |

---

## Acceptance Criteria 충족 여부

| 기준 | 상태 | 비고 |
|------|------|------|
| PDF 파싱 97%+ 정확도 | **검증 불가** | Docling 미설치 환경. 코드상 Docling 어댑터 구조는 정상 구현됨 |
| 표 구조 Markdown 변환 | **부분 충족** | Markdown 표 -> Table 모델 변환 동작 확인. 단, 구분선 파싱 버그 존재 (ISSUE-001) |
| 이미지 위치/캡션 추출 | **코드 구현 확인** | Markdown 이미지 참조 추출 정상. Docling 기반 이미지 추출은 미테스트 |
| 실패 시 3회 재시도 + 수동 검토 플래그 | **충족** | `test_max_retries_exceeded` 통과. `requires_manual_review=True` 확인 |

---

## 경고 목록

총 47건의 Deprecation Warning 발생:

1. **PydanticDeprecatedSince20** (5건): `class Config` -> `ConfigDict` 마이그레이션 필요
   - `models/document.py` (4건: Chunk, Document, DocumentResponse, DocumentStatusResponse, DocumentListItem)
   - `models/parsed_document.py` (1건: ParsedDocument)

2. **DeprecationWarning: datetime.utcnow()** (41건): `datetime.utcnow()` -> `datetime.now(datetime.UTC)`
   - `parsed_document.py`의 `parsed_at` 필드 기본값에서 발생

---

## 결론

### 종합 평가

STORY-002 Docling Document Parser의 단위 테스트는 전체 37개 중 35개가 통과하여 **94.6%** 통과율을 보였습니다. 1개 실패 케이스는 Markdown 표 구분선 정규식 버그(ISSUE-001)이며, 1개 스킵은 Docling 미설치로 인한 의도적 스킵입니다.

### 우선순위 조치 사항

1. **[High]** ISSUE-001 수정: `_parse_markdown_table()` 구분선 정규식 패치
2. **[Medium]** `pytest-cov` 설치 및 정확한 커버리지 측정
3. **[Low]** conftest.py 의존성 분리 (langgraph 없이도 단위 테스트 가능하도록)
4. **[Low]** Pydantic V2 Deprecation 경고 해소

### 다음 단계

- ISSUE-001 버그 수정 후 재테스트
- Docling 설치 환경에서 PDF/DOCX/PPTX 통합 테스트 실행
- 커버리지 80% 달성 목표로 추가 테스트 케이스 작성
