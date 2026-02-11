# DocumentParser Retry 로직 이슈 보고서

**보고서 유형**: 조치 결과 보고서 (구현 완료 확인)
**작성자**: QA Engineer Agent
**작성일**: 2026-01-28
**관련 Story**: STORY-002 (Docling 문서 파싱 구현)
**요청 사항**: 파싱 실패 -> 3회 재시도 후 에러 로깅 + 수동 검토 플래그

---

## 1. 조사 요약

| 항목 | 결과 |
|------|------|
| **현재 상태** | 구현 완료 + 테스트 PASS |
| **재시도 로직** | `_parse_with_retry()` 메서드로 구현됨 |
| **최대 재시도 횟수** | 기본 3회 (생성자 파라미터 `max_retries=3`) |
| **에러 로깅** | `logger.error()` 및 `logger.warning()` 사용 |
| **수동 검토 플래그** | `metadata["requires_manual_review"] = True` |
| **테스트 결과** | `test_retry_on_failure` PASS, `test_max_retries_exceeded` PASS |
| **최종 판정** | **이슈 없음 - 정상 구현 완료** |

---

## 2. 구현 상태 분석

### 2.1 재시도 로직 위치

- **파일**: `knowledge_service/src/app/etl/parser.py`
- **메서드**: `DocumentParser._parse_with_retry()` (Line 180~230)
- **호출 경로**: `parse()` -> 형식별 분기 -> `_parse_with_retry()` -> 실제 파서 함수

### 2.2 재시도 구현 상세

```
DocumentParser.__init__(max_retries=3, retry_delay=1.0)
                |
                v
        parse(file_path)
                |
                v
    _parse_with_retry(file_path, parser_func, doc_format)
                |
                v
    for attempt in range(max_retries):  <-- 최대 3회 반복
        try:
            result = parser_func(file_path)
            if success: return (retry_count = attempt)
            if fail: 경고 로깅, 다음 시도
        except:
            경고 로깅, 다음 시도
        sleep(retry_delay * (attempt + 1))  <-- 선형 백오프
                |
                v
    모든 시도 실패 시:
        - status = FAILED
        - retry_count = max_retries
        - metadata["requires_manual_review"] = True
        - logger.error() 호출
```

### 2.3 핵심 코드 분석

#### (1) 재시도 횟수 설정 (Line 69~88)

```python
class DocumentParser:
    def __init__(
        self,
        max_retries: int = 3,        # 기본 3회 재시도
        retry_delay: float = 1.0,     # 기본 1초 대기
        ocr_enabled: bool = True,
        table_structure_enabled: bool = True,
    ):
```

- 기본값 `max_retries=3`으로 요구사항의 "3회 재시도" 충족
- `retry_delay`는 선형 백오프 (`retry_delay * (attempt + 1)`)

#### (2) 재시도 루프 (Line 180~230)

```python
def _parse_with_retry(self, file_path, parser_func, doc_format):
    for attempt in range(self.max_retries):
        try:
            result = parser_func(file_path)
            if result.success or result.document.status == ParseStatus.PARTIAL:
                result.document.retry_count = attempt
                return result
            # 실패 시 경고 기록
            warnings.append(f"Attempt {attempt + 1}: {result.message}")
        except Exception as e:
            logger.warning(f"Parse attempt {attempt + 1}/{self.max_retries} failed: {e}")
        # 대기 (마지막 시도 제외)
        if attempt < self.max_retries - 1:
            time.sleep(self.retry_delay * (attempt + 1))
```

#### (3) 에러 로깅 + 수동 검토 플래그 (Line 214~230)

```python
    # 모든 재시도 실패
    doc = ParsedDocument.from_file_path(str(file_path))
    doc.status = ParseStatus.FAILED
    doc.retry_count = self.max_retries
    doc.metadata["requires_manual_review"] = True  # 수동 검토 플래그

    logger.error(
        f"All {self.max_retries} parse attempts failed for {file_path.name}"
    )
```

#### (4) ParsedDocument 모델의 retry_count 필드 (parsed_document.py, Line 133)

```python
class ParsedDocument(BaseModel):
    retry_count: int = Field(default=0, ge=0, description="재시도 횟수")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="추가 메타데이터")
```

### 2.4 tenacity 라이브러리 임포트 (미사용)

`parser.py` Line 16~21에서 `tenacity` 라이브러리의 `retry`, `stop_after_attempt`, `wait_exponential` 등을 임포트하고 있으나, 실제 재시도 로직은 자체 `_parse_with_retry()` 메서드로 구현되어 있습니다. tenacity 데코레이터는 현재 사용되지 않습니다.

- **평가**: 불필요한 임포트이나 기능에 영향 없음. 향후 정리 권장.

---

## 3. 테스트 케이스 분석

### 3.1 test_retry_on_failure (Line 353~366)

```python
def test_retry_on_failure(self, tmp_path):
    """재시도 로직 테스트"""
    parser = DocumentParser(max_retries=3, retry_delay=0.1)
    md_file = tmp_path / "test.md"
    md_file.write_text("# Test", encoding="utf-8")

    result = parser.parse(md_file)
    assert result.success is True
    assert result.document.retry_count == 0  # 첫 시도에서 성공
```

- **테스트 의도**: 정상 파싱 시 재시도 없이 `retry_count == 0` 확인
- **최신 결과**: PASSED (2026-01-27 STORY-002 retest, 2026-01-28 Sprint04 E2E)
- **평가**: 성공 경로 검증 완료. 단, Mock을 사용한 "N번 실패 후 성공" 시나리오는 미구현.

### 3.2 test_max_retries_exceeded (Line 368~379)

```python
def test_max_retries_exceeded(self, tmp_path):
    """최대 재시도 횟수 초과"""
    parser = DocumentParser(max_retries=2, retry_delay=0.01)

    result = parser.parse(tmp_path / "nonexistent.md")

    assert result.success is False
    assert result.document.retry_count == 2
    assert result.document.metadata.get("requires_manual_review") is True
```

- **테스트 의도**: 존재하지 않는 파일로 모든 재시도 실패 -> 수동 검토 플래그 확인
- **최신 결과**: PASSED (2026-01-27 STORY-002 retest, 2026-01-28 Sprint04 E2E)
- **평가**: 실패 경로 및 수동 검토 플래그 검증 완료.

### 3.3 테스트 이력

| 날짜 | 테스트 보고서 | test_retry_on_failure | test_max_retries_exceeded |
|------|-------------|:----:|:----:|
| 2026-01-26 | docling_parser_test_report.md | PASSED | PASSED |
| 2026-01-27 | story-002_retest_report.md | PASSED | PASSED |
| 2026-01-28 | sprint04_day1_e2e_test_results.md | PASSED (41+건 전체 통과) | PASSED (41+건 전체 통과) |

---

## 4. Acceptance Criteria 충족 확인

| AC-4 요구사항 | 구현 여부 | 검증 방법 | 판정 |
|--------------|:---------:|----------|:----:|
| 파싱 실패 시 재시도 | O | `_parse_with_retry()` 메서드, `for attempt in range(max_retries)` | PASS |
| 3회 재시도 | O | `max_retries=3` (기본값), 테스트에서 `max_retries=2`로도 검증 | PASS |
| 에러 로깅 | O | `logger.warning()` (시도별) + `logger.error()` (최종 실패) | PASS |
| 수동 검토 플래그 | O | `doc.metadata["requires_manual_review"] = True` | PASS |
| 재시도 횟수 추적 | O | `doc.retry_count` 필드 (ParsedDocument 모델) | PASS |

---

## 5. 개선 권장 사항

현재 구현은 요구사항을 충족하지만, 테스트 견고성과 코드 품질 향상을 위해 아래 사항을 권장합니다.

### 5.1 테스트 보강 (P2 - 기술 부채)

| # | 권장 사항 | 우선순위 | 설명 |
|---|----------|:--------:|------|
| 1 | **Mock 기반 N번 실패 후 성공 테스트** | P2 | 현재 `test_retry_on_failure`는 정상 파일로 첫 시도 성공만 검증. `unittest.mock.patch`로 파서 함수를 Mock하여 2번 실패 후 3번째 성공하는 시나리오를 테스트하면 재시도 로직의 실질적 작동을 더 정밀하게 검증 가능 |
| 2 | **재시도 간 대기 시간 검증** | P3 | `time.sleep(retry_delay * (attempt + 1))` 호출이 올바른 값으로 이루어지는지 Mock으로 확인 |
| 3 | **경고 메시지 누적 검증** | P3 | `ParseResult.warnings` 리스트에 각 시도의 실패 메시지가 정확히 기록되는지 검증 |

### 5.2 코드 정리 (P3 - 기술 부채)

| # | 권장 사항 | 우선순위 | 설명 |
|---|----------|:--------:|------|
| 4 | **미사용 tenacity 임포트 제거** | P3 | `parser.py` Line 16~21의 `tenacity` 임포트가 실제로 사용되지 않음. 불필요한 의존성 정리 권장 |
| 5 | **retry_delay 백오프 전략 문서화** | P3 | 현재 선형 백오프(`delay * (attempt + 1)`) 사용. docstring에 백오프 전략 명시 권장 |

---

## 6. 결론

**DocumentParser의 재시도 로직은 정상 구현 및 테스트 완료 상태입니다.**

- **재시도 횟수**: 기본 3회 (설정 가능)
- **에러 로깅**: 시도별 `WARNING` + 최종 `ERROR` 2단계 로깅
- **수동 검토 플래그**: `metadata["requires_manual_review"] = True` 설정
- **테스트**: 3회 연속 테스트 보고서 (2026-01-26, 01-27, 01-28) 모두 PASSED
- **판정**: 이슈 없음. 추가 조치 불필요.

---

## 7. 관련 파일 목록

| 파일 | 역할 |
|------|------|
| `knowledge_service/src/app/etl/parser.py` | 재시도 로직 구현 (Line 180~230) |
| `knowledge_service/src/app/models/parsed_document.py` | `retry_count`, `metadata` 필드 정의 |
| `knowledge_service/src/tests/unit/test_document_parser.py` | 재시도 테스트 케이스 (Line 353~379) |
| `knowledge_service/docs/results/story-002_retest_report.md` | STORY-002 재테스트 결과 (AC-4 PASS) |
| `knowledge_service/docs/results/sprint04_day1_e2e_test_results.md` | Sprint04 E2E 결과 (전체 PASS) |
| `knowledge_service/docs/04_testing/analysis/01_docling_parser_test_report.md` | 최초 테스트 보고서 |

---

*Report generated by QA Engineer Agent on 2026-01-28*
*DocumentParser Retry Logic - Investigation & Status Report*
