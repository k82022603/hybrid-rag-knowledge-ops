# STORY-002 Docling 파서 - 재테스트 보고서

**테스트 일시**: 2026-01-27
**테스트 담당**: QA Engineer
**테스트 유형**: 재테스트 (Regression) - regex 버그 수정(3b0328d) 이후
**테스트 환경**: Python 3.12.3, pytest 9.0.2, Linux (WSL2)

---

## 1. 테스트 대상

| 파일 | 설명 |
|------|------|
| `knowledge_service/src/app/etl/parser.py` | 통합 문서 파서 |
| `knowledge_service/src/app/etl/docling_adapter.py` | Docling 어댑터 |
| `knowledge_service/src/app/models/parsed_document.py` | 파싱 결과 모델 |
| `knowledge_service/src/tests/unit/test_document_parser.py` | 단위 테스트 (37개) |

---

## 2. Regex 버그 수정 확인

### 2.1 커밋 정보

- **Commit**: `3b0328d` - [FIX] parser.py regex 버그 수정 - 다중 컬럼 테이블 구분자 인식
- **파일**: `knowledge_service/src/app/etl/parser.py` (line 486)
- **변경**: `_parse_markdown_table()` 메서드의 구분선 인식 regex

### 2.2 변경 내용

```python
# Before (buggy)
if re.match(r"^\|[\s\-:]+\|$", line):

# After (fixed)
if re.match(r"^\|[\s\-:|]+$", line):
```

### 2.3 버그 원인 분석

이전 패턴 `^\|[\s\-:]+\|$`은 다음과 같이 해석됩니다:
- `^\|` : 줄 시작에 파이프(`|`) 문자
- `[\s\-:]+` : 공백, 대시, 콜론이 1개 이상
- `\|$` : 줄 끝에 파이프(`|`) 문자

**문제점**: 다중 컬럼 구분선(예: `|---|---|`)의 **중간 파이프 문자**가 character class `[\s\-:]`에 포함되지 않아, 2개 이상의 컬럼을 가진 테이블의 구분선을 인식하지 못했습니다.

### 2.4 수정 후 패턴 분석

새 패턴 `^\|[\s\-:|]+$`은 다음과 같이 해석됩니다:
- `^\|` : 줄 시작에 파이프(`|`) 문자
- `[\s\-:|]+` : 공백, 대시, 콜론, **파이프**가 1개 이상
- `$` : 줄 끝

파이프(`|`)를 character class에 포함시켜 중간 구분자도 정상 매칭합니다.

### 2.5 Regex 패턴 검증 결과

| 테스트 입력 | Old (buggy) | New (fixed) | 기대값 |
|-------------|:-----------:|:-----------:|:------:|
| `\|---\|---\|` | False | True | True |
| `\|---\|---\|---\|` | False | True | True |
| `\| --- \| --- \|` | False | True | True |

**결과**: 수정된 regex 패턴이 모든 다중 컬럼 구분선을 정확히 인식합니다.

---

## 3. 테스트 실행 결과

### 3.1 요약

| 항목 | 값 |
|------|-----|
| 전체 테스트 | 37개 |
| 통과 (PASSED) | 36개 |
| 스킵 (SKIPPED) | 1개 |
| 실패 (FAILED) | 0개 |
| 에러 (ERROR) | 0개 |
| 통과율 | 97.3% (36/37) |
| 실행 시간 | 6.86초 |

### 3.2 스킵된 테스트

| 테스트 | 사유 |
|--------|------|
| `TestDoclingAdapter::test_parse_pdf_with_tables` | Docling 라이브러리 설치 필요 (`@pytest.mark.skip`) |

이 테스트는 실제 Docling 라이브러리와 테스트용 PDF 파일이 필요한 통합 테스트로, 단위 테스트 환경에서는 정상적으로 스킵됩니다.

### 3.3 테스트 클래스별 결과

| 클래스 | 테스트 수 | 결과 |
|--------|:---------:|:----:|
| TestParsedDocumentModel | 8 | 8 PASSED |
| TestTableModel | 3 | 3 PASSED |
| TestSectionModel | 2 | 2 PASSED |
| TestDocumentParser | 12 | 12 PASSED |
| TestDoclingAdapter | 4 | 3 PASSED, 1 SKIPPED |
| TestMarkdownTableExtraction | 2 | 2 PASSED |
| TestMarkdownSectionExtraction | 1 | 1 PASSED |
| TestParseResult | 2 | 2 PASSED |
| TestBatchParseResult | 1 | 1 PASSED |
| TestConvenienceFunctions | 2 | 2 PASSED |
| **합계** | **37** | **36 PASSED, 1 SKIPPED** |

### 3.4 개별 테스트 상세 결과

```
PASSED  TestParsedDocumentModel::test_create_from_file_path_pdf
PASSED  TestParsedDocumentModel::test_create_from_file_path_docx
PASSED  TestParsedDocumentModel::test_create_from_file_path_hwp
PASSED  TestParsedDocumentModel::test_create_from_file_path_markdown
PASSED  TestParsedDocumentModel::test_create_from_file_path_unknown
PASSED  TestParsedDocumentModel::test_is_successful
PASSED  TestParsedDocumentModel::test_has_tables
PASSED  TestParsedDocumentModel::test_has_images
PASSED  TestTableModel::test_table_to_markdown
PASSED  TestTableModel::test_table_with_existing_markdown
PASSED  TestTableModel::test_empty_table
PASSED  TestSectionModel::test_section_creation
PASSED  TestSectionModel::test_nested_sections
PASSED  TestDocumentParser::test_supports_format
PASSED  TestDocumentParser::test_get_format
PASSED  TestDocumentParser::test_parse_markdown_file
PASSED  TestDocumentParser::test_parse_text_file
PASSED  TestDocumentParser::test_parse_text_file_korean
PASSED  TestDocumentParser::test_parse_html_file
PASSED  TestDocumentParser::test_parse_nonexistent_file
PASSED  TestDocumentParser::test_parse_unsupported_format
PASSED  TestDocumentParser::test_parse_batch
PASSED  TestDocumentParser::test_parse_batch_with_errors
PASSED  TestDocumentParser::test_retry_on_failure
PASSED  TestDocumentParser::test_max_retries_exceeded
PASSED  TestDoclingAdapter::test_supports_format
PASSED  TestDoclingAdapter::test_parse_nonexistent_file
PASSED  TestDoclingAdapter::test_parse_unsupported_format
SKIPPED TestDoclingAdapter::test_parse_pdf_with_tables (Requires Docling installation)
PASSED  TestMarkdownTableExtraction::test_extract_simple_table
PASSED  TestMarkdownTableExtraction::test_extract_multiple_tables
PASSED  TestMarkdownSectionExtraction::test_extract_sections
PASSED  TestParseResult::test_parse_result_success
PASSED  TestParseResult::test_parse_result_with_warnings
PASSED  TestBatchParseResult::test_batch_result
PASSED  TestConvenienceFunctions::test_get_parser
PASSED  TestConvenienceFunctions::test_parse_document
```

---

## 4. Acceptance Criteria 충족 여부

| AC | 설명 | 테스트 커버리지 | 판정 |
|----|------|----------------|:----:|
| AC-1 | PDF -> Docling 파싱 -> 97%+ 정확도 텍스트 추출 | `TestDoclingAdapter` (Docling 미설치로 스킵, 어댑터 구조 검증 완료) | PARTIAL |
| AC-2 | 표 포함 문서 -> 표 구조가 Markdown 테이블로 변환 | `TestMarkdownTableExtraction` (2개 테스트 통과), `TestTableModel::test_table_to_markdown` | PASS |
| AC-3 | 이미지 포함 문서 -> 이미지 위치와 캡션 추출 | `TestDocumentParser::test_parse_markdown_file` (이미지 추출 검증) | PASS |
| AC-4 | 파싱 실패 -> 3회 재시도 후 에러 로깅 + 수동 검토 플래그 | `TestDocumentParser::test_retry_on_failure`, `test_max_retries_exceeded` | PASS |

### AC 상세 분석

**AC-1 (PARTIAL)**: Docling 라이브러리가 설치되지 않은 환경에서는 실제 PDF 파싱 정확도를 측정할 수 없습니다. 그러나 DoclingAdapter의 구조, 에러 핸들링, 형식 지원 확인은 모두 통과했습니다. 실제 PDF 정확도 테스트는 Docling이 설치된 통합 테스트 환경에서 수행해야 합니다.

**AC-2 (PASS)**: regex 버그 수정(3b0328d) 이후 다중 컬럼 테이블 구분선 인식이 정상 작동합니다.
- `test_extract_simple_table`: 2x2 테이블 정상 추출
- `test_extract_multiple_tables`: 복수 테이블 정상 추출
- `test_table_to_markdown`: Table 모델의 Markdown 변환 정상

**AC-3 (PASS)**: Markdown 파일의 이미지 참조(`![alt](url)`) 패턴 추출이 정상 작동합니다.

**AC-4 (PASS)**: 재시도 로직이 정상 작동합니다.
- 성공 시 `retry_count = 0`
- 실패 시 `retry_count = max_retries` (설정값)
- 모든 재시도 실패 후 `requires_manual_review = True` 메타데이터 설정

---

## 5. 코드 품질 경고 사항

pytest 실행 중 발견된 경고 (테스트 실패와 무관):

| 경고 | 위치 | 심각도 |
|------|------|:------:|
| PydanticDeprecatedSince20: class-based config deprecated | `models/document.py` (5건) | Low |
| PydanticDeprecatedSince20: class-based config deprecated | `models/parsed_document.py` (1건) | Low |
| DeprecationWarning: datetime.utcnow() deprecated | `parsed_document.py:151` (41건) | Low |

이 경고들은 Pydantic V2 마이그레이션과 Python 3.12 datetime API 변경에 따른 것으로, 기능에는 영향이 없으나 향후 Pydantic V3 업그레이드 시 수정이 필요합니다.

---

## 6. 최종 판정

### STORY-002 Done 전환 가능 여부: CONDITIONAL PASS

| 판정 기준 | 결과 |
|----------|:----:|
| 전체 단위 테스트 통과 | PASS (36/36, 1 스킵은 환경 의존) |
| Regex 버그 수정 검증 | PASS (3b0328d 커밋 정상) |
| AC-2 표 추출 | PASS |
| AC-3 이미지 추출 | PASS |
| AC-4 재시도/에러 핸들링 | PASS |
| AC-1 PDF 97% 정확도 | PENDING (통합 테스트 환경 필요) |

**조건**: AC-1(PDF 97%+ 정확도)은 Docling이 설치된 통합 테스트 환경에서 별도 검증이 필요합니다. 나머지 3개 AC는 모두 충족되었으며, regex 버그 수정이 올바르게 적용되었습니다.

**권고사항**:
1. STORY-002를 Done으로 전환 가능 (AC-1 통합 테스트는 별도 티켓으로 추적)
2. Pydantic V2 deprecation 경고는 기술 부채로 등록 권장
3. `datetime.utcnow()` -> `datetime.now(datetime.UTC)` 마이그레이션 권장

---

## 7. 테스트 실행 로그

```
platform linux -- Python 3.12.3, pytest-9.0.2, pluggy-1.6.0
rootdir: /mnt/d/.../hybrid-rag-knowledge-ops/knowledge_service
configfile: pyproject.toml
plugins: anyio-4.12.1

36 passed, 1 skipped, 50 warnings in 6.86s
```
