# ETL Engineer 반성문 + 코드 품질 개선 분석

**작성일**: 2026-02-14
**작성자**: Data (ETL Engineer)
**관련 이슈**: ETL Phase 1 품질 문제 전면 재시작

---

## 1. 반성

ETL Phase 1 실행 결과 심각한 품질 문제가 발견되었습니다.

- Junk 청크 340개 (<3 tokens): "---" 같은 의미없는 데이터가 ES에 적재됨
- Short 청크 1,014개 (<10 tokens): 검색에 무의미한 짧은 단편들
- Ultra-long 청크 88개 (max 6,765 tokens): chunk_size=1000인데 제어 불가
- 문서 중복 29그룹: dedup 로직 실패
- OOM Kill: 대용량 파일 처리 중 컨테이너 사망

이 문제들은 **ETL 코드를 정밀하게 검토하지 않은 채 실행한 제 책임**입니다.
청킹 파라미터와 필터링 로직의 상호작용을 충분히 분석하지 않았고,
"일단 돌려보자"는 태도로 접근한 결과 전체 데이터를 오염시켰습니다.

---

## 2. 근본 원인 분석

### 2.1 문제 1: Junk 청크 340개 (<3 tokens) - "---" 같은 의미없는 청크

**근본 원인**: 청커의 `_preprocess_section_content()` 노이즈 필터가 **불완전**

**코드 위치**: `/knowledge_service/src/app/etl/chunker.py:666-690`

```python
# 현재 코드 (chunker.py:74-81)
SECTION_NOISE_PATTERNS = [
    re.compile(r'^-{3,}$'),              # --- (수평선)
    re.compile(r'^={3,}$'),              # === (수평선 변형)
    re.compile(r'^```\w*$'),             # ```yaml, ```dockerfile (미닫힘 코드블록)
    re.compile(r'^\*{3,}$'),             # *** (수평선)
    re.compile(r'^_{3,}$'),              # ___ (수평선)
    re.compile(r'^\s*<!--.*?-->\s*$'),   # HTML 주석 (단일 라인만)
]
```

문제점:
1. `re.compile(r'^-{3,}$')` 패턴은 **정확히 "---"만** 매칭한다. 하지만 `_preprocess_section_content()`는 `pattern.match(text)`를 사용하므로 **텍스트 전체가 "---"일 때만** 필터링된다.
2. **섹션 내부에 "---"가 포함된 경우** (예: "some text\n---\nmore text")는 필터링되지 않는다. 이 경우 문장 분리 후 "---"가 독립 청크로 생성된다.
3. Markdown 파서(`parser.py:436-466`)의 `_extract_markdown_sections()`는 **플랫 구조**로 섹션을 생성한다. 헤딩 사이의 콘텐츠가 section.content에 들어가는데, 이때 수평선("---")이 단독 콘텐츠로 남는 섹션이 만들어질 수 있다.

**경로 추적**:
```
parser._extract_markdown_sections()
  → 헤딩 사이 "---\n" 만 있는 섹션 생성
  → chunker._chunk_with_sections()
  → _chunk_section_recursive()
  → _preprocess_section_content("---") → 빈 문자열 반환 (필터링 성공)
  BUT: "---\n\n" (공백/줄바꿈 포함) → strip() 후 "---" → 필터링 성공
  BUT: "---\nsome text" → 필터링 안됨, chunk_text()로 진행 → "---"가 문장으로 분리
```

4. 핵심 누락: `chunk_text()`의 `_split_text_by_sentences()` 결과로 나온 **개별 청크에 대한 최소 품질 필터가 없다**. `_split_text_by_sentences()`의 마지막 부분(line 568-579)에 `token_count >= 10 and len(stripped) >= 30` 체크가 있지만, 이것은 **전체 텍스트가 너무 짧아서 아무 청크도 안 만들어진 경우에만** 적용된다. 정상적으로 여러 청크가 만들어진 뒤 일부가 매우 짧은 경우에는 필터링하지 않는다.

**수정 방안**:
1. `_assemble_chunks()` 결과에 대해 **post-filtering** 추가: token_count < 3인 청크는 인접 청크에 병합하거나 폐기
2. `_preprocess_section_content()`에 추가 필터: `token_count < 5`인 섹션 콘텐츠도 노이즈로 처리
3. `_split_text_by_sentences()`에서 min_chunk_size 미달 청크를 이전 청크에 병합하는 로직 강화

**예상 효과**: Junk 청크 340개 -> 0개 (100% 제거)

---

### 2.2 문제 2: Short 청크 1,014개 (<10 tokens)

**근본 원인**: `min_chunk_size=100` (문자 수 기준)은 토큰 수 기준이 아님

**코드 위치**: `/knowledge_service/src/app/etl/chunker.py:83-89` (init), `512-513` (체크)

```python
# chunker.py:83-89 - 기본값
def __init__(self, chunk_size=600, chunk_overlap=100, min_chunk_size=100, max_chunk_size=2048):
```

```python
# chunker.py:512-513 - 청크 저장 시 min_chunk_size 체크
if len(chunk_content) >= self.min_chunk_size:
    # ... 청크 저장
```

문제점:
1. `min_chunk_size=100`은 **문자(char) 수** 기준이다. 한국어 100자는 약 33토큰이지만, 영어+특수문자 100자는 약 50~80토큰이다. **토큰 기반 최소 기준이 없다**.
2. `_split_text_by_sentences()`에서 마지막 청크 처리(line 541-566): `len(chunk_content) < self.min_chunk_size`이면 이전 청크에 병합을 **시도**하지만, 이전 청크와 병합 시 `max_chunk_size` 초과하면 **별도 청크로 생성**된다(line 549-557). 이때 min_chunk_size 미달이어도 생성된다.
3. `_merge_small_adjacent_chunks()`(line 692-753)는 `token_count < 20`인 청크를 병합하려 하지만, **섹션 기반 청킹에서만** 호출된다(`_chunk_with_sections()` line 277). 섹션이 없는 문서(txt, 일부 pdf)는 이 병합이 적용되지 않는다.
4. ETL 스크립트에서 `chunk_size=1000`으로 전달했지만, `min_chunk_size`는 기본값 100 그대로이다. chunk_size 대비 min_chunk_size 비율이 10%로 너무 낮다.

**수정 방안**:
1. `min_chunk_size`를 **토큰 기반**으로 변경: `min_token_count=10` 파라미터 추가
2. `chunk_text()` 최종 결과에 대해 토큰 기반 post-filter: `token_count < 10`이면 인접 병합 또는 폐기
3. `_merge_small_adjacent_chunks()`를 **chunk_text() 레벨**에서도 호출 (현재 섹션 기반에서만 호출)
4. ETL 스크립트에서 `min_chunk_size`를 chunk_size의 최소 20%로 설정 (1000 -> min 200)

**예상 효과**: Short 청크 1,014개 -> ~50개 이하 (95% 감소)

---

### 2.3 문제 3: Ultra-long 청크 88개 (max 6,765 tokens)

**근본 원인**: 테이블/코드 블록이 `max_chunk_size` 제한 없이 단일 청크로 보존됨

**코드 위치**: `/knowledge_service/src/app/etl/chunker.py:460-464`

```python
# chunker.py:460-464 - 특수 블록 처리
if seg_type in ("code", "table"):
    # 특수 블록: 그대로 하나의 청크로
    # max_chunk_size 초과해도 분할하지 않음  ← 문제의 주석!
    raw_chunks.append((content.strip(), seg_start, seg_end, seg_type))
```

문제점:
1. **의도적으로 max_chunk_size 제한을 무시**하고 있다. 코드와 테이블의 구조를 보존하기 위한 설계 의도이지만, 실제로 6,765 토큰(약 20,000+ 문자)짜리 테이블이 하나의 청크로 들어간다.
2. `run_etl_phase1_chunks.py`에서 `chunk_size=1000`으로 설정하지만, `max_chunk_size`는 기본값 2048이다. 그러나 테이블/코드 블록은 이 2048 제한도 무시한다.
3. Markdown 테이블이 매우 큰 경우 (수십 행 x 다수 열), 단일 청크의 토큰 수가 폭발한다.
4. 이 청크들은 임베딩 시 `max_text_length=1000`으로 잘리게 되어, 청크의 절반 이상이 임베딩되지 않는 정보 손실이 발생한다.

**수정 방안**:
1. 테이블/코드 블록도 `max_chunk_size` 초과 시 **논리적 분할** 적용:
   - 테이블: 행 단위로 분할 (헤더 행 반복 포함)
   - 코드: 함수/클래스 경계 또는 빈 줄 기준 분할
2. 강제 분할 상한선 추가: `hard_max_chunk_size = max_chunk_size * 2` (4096)
3. 분할 시 `metadata["block_type"] = "table_part"` / `"code_part"` 등 표시

**예상 효과**: Ultra-long 청크 88개 -> 0개 (분할되어 정상 범위 내로)

---

### 2.4 문제 4: 문서 중복 29그룹

**근본 원인**: Dedup 로직이 `processing_status = 'completed'`인 기존 문서만 검사

**코드 위치**: `/knowledge_service/src/app/services/initial_data_loader.py:649-695`

```python
# initial_data_loader.py:670-678 - 중복 검사 쿼리
row = await conn.fetchrow(
    """
    SELECT id, file_path, processing_status
    FROM documents
    WHERE file_hash = $1
      AND processing_status = 'completed'
    LIMIT 1
    """,
    file_hash,
)
```

문제점:
1. `processing_status = 'completed'` 조건: 첫 실행 시 PG에 아직 아무 문서도 'completed'가 아니므로, **동일 배치 내 중복 파일을 감지하지 못한다**.
2. **파일 경로는 다르지만 내용이 동일한 파일**: 예를 들어, `documents/technical/file.md`와 `documents/guides/file.md`가 동일 내용이면, 첫 번째가 처리 중일 때 두 번째도 hash 비교에서 통과한다 (첫 번째가 아직 completed가 아니므로).
3. **런타임 중복 추적 부재**: `_process_file()` 호출 전에 in-memory hash set으로 중복을 추적하는 로직이 없다.
4. PG 연결 실패 시 dedup을 **건너뛴다** (line 693-695): `logger.warning("Dedup check failed (proceeding without): %s", e)` - 이 경우 중복 파일이 그대로 적재된다.

**수정 방안**:
1. **In-memory hash set** 추가: `self._processed_hashes: Set[str] = set()` 를 InitialDataLoader에 추가하고, 파일 처리 성공 시 hash를 추가. 다음 파일 처리 전에 이 set을 먼저 확인.
2. PG 쿼리에서 `processing_status` 조건 완화: `processing_status IN ('completed', 'processing')` 또는 조건 제거
3. `_check_duplicate()` 실패 시 **fallback으로 in-memory hash** 사용
4. 동일 디렉토리 내 심볼릭 링크/하드링크 감지 추가

**예상 효과**: 문서 중복 29그룹 -> 0개 (100% 제거)

---

### 2.5 문제 5: 대용량 파일 OOM

**근본 원인**: 30MB 파일 크기 제한이 불충분하고, 파싱 단계에서 메모리 제어 없음

**코드 위치**: `/knowledge_service/scripts/run_etl_phase1_chunks.py:119, 143-154`

```python
# run_etl_phase1_chunks.py:119
MAX_FILE_SIZE_MB = 30  # 30MB 초과 파일은 OOM 방지를 위해 스킵

# run_etl_phase1_chunks.py:143-154
file_path = Path(file_info.file_path) if hasattr(file_info, 'file_path') else None
if file_path and file_path.exists():
    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        # ... 스킵
```

문제점:
1. 30MB 제한은 **파일 크기** 기준이지 **파싱 후 메모리 사용량** 기준이 아니다. PDF 10MB 파일이 파싱 후 수십 MB의 텍스트+구조 데이터를 생성할 수 있다.
2. `hasattr(file_info, 'file_path')` 체크가 불필요한 방어 코드: FileInfo 데이터클래스는 항상 file_path 필드를 가진다.
3. Docling 파서(`parser.py:244-246`)가 대용량 PDF/PPTX를 파싱할 때 **전체 문서를 메모리에 로드**한다. 스트리밍 파싱이 아니다.
4. **컨테이너 메모리 제한과의 관계**: Docker 컨테이너에 메모리 제한(예: 4GB)이 설정되어 있으면, 30MB PDF도 파싱 중 OOM이 발생할 수 있다.

**수정 방안**:
1. 파일 크기 제한을 **파일 형식별로 차등 적용**:
   - Markdown/TXT: 50MB (텍스트이므로 메모리 효율적)
   - PDF/DOCX/PPTX: 15MB (파싱 시 메모리 팽창)
2. 파싱 단계에서 **콘텐츠 길이 제한**: `parsed_doc.content`가 500,000자 초과 시 잘라내기
3. `resource` 모듈로 프로세스 메모리 사용량 모니터링, 임계치 초과 시 GC 강제 실행
4. 파일 크기 체크를 `_patched_load_source`가 아닌 `_process_file()` 내부로 이동 (monkey-patch 제거)

**예상 효과**: OOM Kill 0건 (안정적 처리)

---

## 3. 추가 발견: chunk_size 불일치

**코드 위치**:
- `run_etl_phase1_chunks.py:193-198`: `chunk_size=1000`
- `chunker.py:83-89`: 기본값 `chunk_size=600`, `max_chunk_size=2048`

ETL 스크립트에서 `chunk_size=1000`을 전달하지만, chunker의 `max_chunk_size` 기본값(2048)은 변경하지 않았다. `chunk_size=1000`이면 `max_chunk_size=2000~2500` 정도가 적절하다.

또한 `chunk_overlap=200`은 chunk_size(1000)의 20%로, 약간 높지만 수용 가능한 수준이다. 다만 오버랩이 클수록 중복 콘텐츠가 많아져 총 청크 수가 증가한다.

---

## 4. 파서의 Markdown 섹션 처리 문제

**코드 위치**: `/knowledge_service/src/app/etl/parser.py:436-466`

`_extract_markdown_sections()`는 **플랫 리스트**로 섹션을 생성한다 (중첩 없음). 모든 헤딩 레벨(H1~H6)이 같은 레벨의 형제 섹션으로 나열된다.

이로 인해:
1. H2 아래의 짧은 H3 섹션들이 각각 독립 청크로 분리 -> Short 청크 발생
2. 섹션의 subsections가 비어있으므로 `_chunk_section_recursive()`의 하위 섹션 재귀 처리가 작동하지 않음
3. 결과적으로 `_merge_small_adjacent_chunks()`가 **각 섹션 내부**에서만 병합하므로, 연속된 짧은 섹션들이 병합되지 않음

**수정 방안**: Markdown 파서에서 **중첩 섹션 구조**를 생성하거나, chunker에서 **연속된 짧은 섹션을 크로스-섹션 병합**하는 옵션 추가

---

## 5. 종합 수정 우선순위

| 우선순위 | 문제 | 수정 위치 | 난이도 | 효과 |
|---------|------|----------|-------|------|
| P0 | In-memory dedup | initial_data_loader.py | 낮음 | 중복 29그룹 제거 |
| P0 | Junk 청크 post-filter | chunker.py | 낮음 | Junk 340개 제거 |
| P1 | 토큰 기반 min filter | chunker.py | 중간 | Short 1,014개 감소 |
| P1 | 특수 블록 분할 | chunker.py | 중간 | Ultra-long 88개 제거 |
| P2 | 형식별 파일 크기 제한 | initial_data_loader.py | 낮음 | OOM 방지 |
| P2 | 섹션 간 병합 강화 | chunker.py | 중간 | Short 청크 추가 감소 |
| P3 | 중첩 섹션 파싱 | parser.py | 높음 | 전반적 품질 향상 |

---

## 6. 다짐

1. ETL 실행 전 반드시 **소규모 샘플 테스트** (10개 파일)로 품질 검증을 하겠습니다
2. 청크 품질 지표(min/max/avg token count, junk ratio)를 **실행 후 자동 리포트**하겠습니다
3. "일단 돌려보자"가 아닌 **코드 리뷰 -> 샘플 테스트 -> 전체 실행** 순서를 지키겠습니다
4. 파라미터 변경 시 **영향 범위를 먼저 분석**하겠습니다 (chunk_size 변경 시 min/max도 연동)
