# STORY-002: Docling 문서 파싱

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-7 |
| **Epic** | EPIC-001 |
| **Status** | To Do |
| **Priority** | Critical |
| **Story Points** | 8 |
| **Assignee** | - |
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

- [ ] Docling 라이브러리 설치 및 설정
- [ ] DocumentParser 클래스 구현
- [ ] PDF 파서 구현
- [ ] DOCX 파서 구현
- [ ] HWP 파서 구현 (pyhwpx 폴백)
- [ ] 파싱 결과 표준화 (DoclingDocument → InternalDocument)
- [ ] 에러 핸들링 및 재시도 로직
- [ ] 파싱 품질 메트릭 수집
- [ ] 단위 테스트 작성

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

- [ ] Unit Test: 각 포맷별 파싱
- [ ] Unit Test: 표 추출 정확도
- [ ] Integration Test: 실제 문서 샘플 (10개)
- [ ] Benchmark: 파싱 정확도 측정 (Ground Truth 비교)

### 테스트 데이터
```
tests/fixtures/documents/
├── sample_pdf_with_tables.pdf
├── sample_docx_complex.docx
├── sample_hwp_korean.hwp
└── expected_outputs/
```

---

## 참고 자료

- [Docling GitHub](https://github.com/DS4SD/docling)
- [Docling 정확도 벤치마크](https://github.com/DS4SD/docling#benchmarks)
- [pyhwpx 문서](https://github.com/hanul93/pyhwpx)
