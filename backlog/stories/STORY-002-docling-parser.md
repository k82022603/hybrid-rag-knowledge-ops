# STORY-002: Docling 문서 파싱

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-7 |
| **Epic** | EPIC-001 |
| **Status** | In Progress |
| **Priority** | Critical |
| **Story Points** | 8 |
| **Assignee** | MLRag |
| **Sprint** | 2 |

---

## User Story

**As a** 시스템,
**I want** 업로드된 문서를 구조화된 텍스트로 파싱,
**So that** 표, 이미지, 레이아웃 정보가 보존된 고품질 텍스트 추출.

---

## Acceptance Criteria

- [ ] **Given** PDF 문서, **When** Docling 파싱, **Then** 97%+ 정확도로 텍스트 추출
- [ ] **Given** 표가 포함된 문서, **When** 파싱, **Then** 표 구조가 Markdown 테이블로 변환
- [ ] **Given** 이미지가 포함된 문서, **When** 파싱, **Then** 이미지 위치와 캡션 추출
- [ ] **Given** 파싱 실패, **When** 3회 재시도 후 실패, **Then** 에러 로깅 및 수동 검토 플래그

---

## Tasks

- [x] Docling 라이브러리 설치 및 설정 (pyproject.toml에 포함)
- [x] DocumentParser 클래스 구현 (`parser.py`)
- [x] PDF 파서 구현 (DoclingAdapter 통해)
- [x] DOCX 파서 구현 (DoclingAdapter 통해)
- [x] HWP 파서 구현 (pyhwpx/hwp5 폴백)
- [x] Markdown 파서 구현 (추가)
- [x] 파싱 결과 표준화 (`parsed_document.py`)
- [x] 에러 핸들링 및 재시도 로직 (3회 재시도, 수동 검토 플래그)
- [x] 파싱 품질 메트릭 수집 (word_count, char_count, parsing_time_ms)
- [x] 단위 테스트 작성 (`test_document_parser.py`)

---

## 기술 노트

### Docling 설정
```python
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat

converter = DocumentConverter(
    allowed_formats=[
        InputFormat.PDF,
        InputFormat.DOCX,
        InputFormat.PPTX,
    ]
)

result = converter.convert(source_path)
```

### 출력 구조
```python
@dataclass
class ParsedDocument:
    content: str              # 전체 텍스트
    sections: List[Section]   # 섹션별 구조
    tables: List[Table]       # 추출된 표
    images: List[ImageRef]    # 이미지 참조
    metadata: Dict            # 문서 메타데이터
```

### HWP 폴백 처리
```python
try:
    result = docling_parse(file)
except UnsupportedFormat:
    if file.suffix == '.hwp':
        result = hwp_fallback_parse(file)
```

### 영향 범위
- `knowledge_service/src/app/etl/parser.py` (신규)
- `knowledge_service/src/app/etl/docling_adapter.py` (신규)
- `knowledge_service/src/app/models/parsed_document.py` (신규)

---

## 테스트 계획

- [x] Unit Test: 각 포맷별 파싱 (Markdown, Text, HTML 완료)
- [x] Unit Test: 표 추출 정확도
- [ ] Integration Test: 실제 문서 샘플 (10개) - PDF/DOCX 실제 파일 필요
- [ ] Benchmark: 파싱 정확도 측정 (Ground Truth 비교)

### 테스트 데이터
```
tests/fixtures/documents/
├── sample_markdown.md        # 완료
├── sample_text.txt           # 완료
├── sample_html.html          # 완료
├── sample_pdf_with_tables.pdf  # TODO
├── sample_docx_complex.docx    # TODO
├── sample_hwp_korean.hwp       # TODO
└── expected_outputs/
```

---

## 참고 자료

- [Docling GitHub](https://github.com/DS4SD/docling)
- [Docling 정확도 벤치마크](https://github.com/DS4SD/docling#benchmarks)
- [pyhwpx 문서](https://github.com/hanul93/pyhwpx)

---

## 구현 내역 (2026-01-25)

### 생성된 파일

| 파일 | 설명 |
|------|------|
| `src/app/models/parsed_document.py` | ParsedDocument, Table, Section, ImageRef 등 파싱 결과 모델 |
| `src/app/etl/__init__.py` | ETL 모듈 초기화 |
| `src/app/etl/docling_adapter.py` | Docling 라이브러리 래퍼 (PDF/DOCX/PPTX) |
| `src/app/etl/parser.py` | 통합 문서 파서 (모든 형식 지원) |
| `src/tests/unit/__init__.py` | Unit 테스트 패키지 |
| `src/tests/unit/test_document_parser.py` | 문서 파서 단위 테스트 (30+ 테스트 케이스) |
| `src/tests/fixtures/documents/sample_markdown.md` | 테스트용 Markdown 파일 |
| `src/tests/fixtures/documents/sample_text.txt` | 테스트용 텍스트 파일 |
| `src/tests/fixtures/documents/sample_html.html` | 테스트용 HTML 파일 |

### 주요 기능

1. **다중 형식 지원**
   - PDF, DOCX, PPTX: Docling 어댑터
   - HWP: pyhwpx/hwp5 폴백
   - Markdown: 네이티브 파서 (섹션/표/이미지 추출)
   - Text: 다중 인코딩 지원 (UTF-8, CP949, EUC-KR)
   - HTML: 텍스트 추출 (script/style 제외)

2. **표 추출**
   - Docling 표 구조 인식
   - Markdown 테이블 파싱
   - Table → Markdown 변환

3. **재시도 로직**
   - 최대 3회 재시도
   - 지수 백오프
   - 실패 시 수동 검토 플래그

4. **품질 메트릭**
   - word_count, char_count
   - parsing_time_ms
   - parser_version

### 담당자
- **MLRag Agent** (AI/ML Engineer)
