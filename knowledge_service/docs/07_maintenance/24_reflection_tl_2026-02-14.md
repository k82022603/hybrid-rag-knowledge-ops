# TL 반성문: ETL Phase 1 실패 원인 분석

**작성자**: TechLead  
**작성일**: 2026-02-14  
**대상 기간**: ETL Phase 1 실행 (2026-02-11 ~ 2026-02-14)

---

## 요약

ETL Phase 1에서 8개의 심각한 문제가 발생했습니다. 사용자가 "제대로 한 것이 하나도 없다"고 판단할 정도의 실패입니다. Tech Lead로서 코드 리뷰와 아키텍처 검토를 사전에 수행했어야 하지만, 실행 전 충분한 검증 없이 파이프라인을 그대로 돌렸습니다. 아래에 각 문제의 근본 원인을 코드 수준에서 분석합니다.

---

## 문제 1: PG 문서 중복 29그룹

### 증상
PostgreSQL `documents` 테이블에 동일 파일이 여러 번 INSERT되어 29개 중복 그룹이 존재합니다.

### 근본 원인 (코드 위치)

**파일**: `knowledge_service/src/app/services/initial_data_loader.py:649-695`

```python
async def _check_duplicate(self, file_hash: str, file_path: str) -> Optional[str]:
    ...
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

**문제점 3가지**:

1. **`processing_status = 'completed'` 조건이 너무 좁음**: `_store_to_postgresql()`에서 문서를 `status: "completed"`로 저장하지만(line 1201), PG 저장이 실패하면(`return None`, line 1227) file_hash 자체가 DB에 없으므로 다음 실행 시 중복 감지가 불가능합니다. 즉, 부분 실패 → 재실행 시 동일 파일이 다시 처리됩니다.

2. **PG 저장 실패가 "비치명적"으로 처리됨**: `_store_to_postgresql()`(line 1166-1227)에서 예외 발생 시 `logger.warning("PostgreSQL storage failed (non-critical): %s", e)`로만 처리하고 `return None`을 반환합니다. 그러면 `effective_doc_id = pg_doc_id or document_id`(line 1141)에서 PG에 기록되지 않은 UUID가 사용되고, ES/Neo4j에는 저장되지만 PG dedup 테이블에는 file_hash가 없는 상태가 됩니다.

3. **UPSERT의 `ON CONFLICT (id)` 조건**: `document_repository.py:126-139`에서 `ON CONFLICT (id) DO UPDATE`를 사용하지만, 매번 새 UUID를 생성하므로(`document_id = str(uuid4())`, line 805) ID 충돌이 발생하지 않아 UPSERT가 항상 INSERT로 동작합니다. `file_hash`에 UNIQUE 제약이 없으므로 동일 해시의 문서가 복수 INSERT됩니다.

### 수정 방안
- `file_hash`에 UNIQUE 제약 추가 또는 `ON CONFLICT (file_hash)` UPSERT
- dedup 쿼리에서 `processing_status = 'completed'` 조건 제거 (file_hash 존재 자체로 중복 판단)
- PG 저장 실패 시 ES/Neo4j 저장도 중단 (원자성 보장)

---

## 문제 2: Junk 청크 340개 (<3 tokens, "---" 같은 쓰레기)

### 증상
ES에 `---`, `===`, 빈 줄, 단독 마크다운 구분선 등이 하나의 청크로 저장됨.

### 근본 원인 (코드 위치)

**파일**: `knowledge_service/src/app/etl/chunker.py:666-690`

```python
def _preprocess_section_content(self, content: str) -> str:
    ...
    for pattern in self.SECTION_NOISE_PATTERNS:
        if pattern.match(text):  # <-- match()는 문자열 시작만 매칭
            return ""
    return text
```

**문제점 2가지**:

1. **`pattern.match()`는 전체 매칭이 아님**: `re.match()`는 문자열 시작 부분만 매칭합니다. 따라서 `"---\n\n일반 텍스트"`처럼 시작은 노이즈이지만 이후에 실제 내용이 있는 경우, match가 성공하여 전체가 빈 문자열로 처리됩니다. 반대로 `"텍스트\n---"`처럼 노이즈가 중간/끝에 있으면 match가 실패하여 `---`가 청크에 포함됩니다.

2. **Markdown 파서의 섹션 분리 방식**: `parser.py:436-466`의 `_extract_markdown_sections()`에서 `# 헤딩` 라인 기준으로 섹션을 분리합니다. 헤딩과 헤딩 사이에 `---`만 있는 경우, 그것이 하나의 섹션 content가 됩니다. 이 content가 `min_chunk_size=100` 미만(3글자)이므로 `_chunk_section_recursive()`(line 320)에서 걸려야 하지만:

    ```python
    if cleaned and len(cleaned) >= self.min_chunk_size:
    ```
    
    `---`는 3글자로 `min_chunk_size=100` 미만이므로 이 조건에서 걸립니다. 그러나 **섹션 기반 청킹이 아닌 flat text 경로**(`chunk_text()`)로 갔을 때가 문제입니다. `parsed_document.sections`가 비어 있거나 Markdown이 아닌 파일(PDF, DOCX 등)의 경우, `chunk_text()`가 호출되고 이때는 `_preprocess_section_content()`가 호출되지 않습니다.

3. **`chunk_text()`의 fallback 처리**(line 568-579):
    ```python
    if not chunks and text.strip():
        stripped = text.strip()
        token_count = self._estimate_token_count(stripped)
        if token_count >= 10 and len(stripped) >= 30:
            chunks.append(...)
    ```
    이 보호 로직은 `chunk_text()` 전체에서 청크가 0개일 때만 작동합니다. 이미 다른 청크가 있으면, 작은 잔여 텍스트가 `_split_text_by_sentences()`에서 별도 청크로 생성될 수 있고, 이때 `min_chunk_size` 미만이면 이전 청크에 병합을 시도하지만(line 542-556), 이전 청크와 합쳐서 `max_chunk_size`를 초과하면 별도 청크로 남습니다.

### 수정 방안
- `chunk_text()`에서도 노이즈 패턴 전처리 적용
- 최종 청크 목록에서 token_count < 3인 청크를 필터링하는 post-processing 추가
- PDF/DOCX 파서 출력에서 페이지 구분선(`---`) 제거

---

## 문제 3: Short 청크 1,014개 (<10 tokens)

### 증상
의미 없는 짧은 텍스트 조각들이 개별 청크로 ES에 저장됨.

### 근본 원인 (코드 위치)

**파일**: `knowledge_service/src/app/etl/chunker.py:537-566`

```python
# 마지막 청크 처리
if current_sentences:
    chunk_content = "".join(current_sentences).strip()
    if chunk_content:
        if len(chunk_content) < self.min_chunk_size and chunks:
            # 이전 청크와 병합
            prev_content, prev_start, prev_end = chunks[-1]
            merged = prev_content + " " + chunk_content
            if len(merged) <= self.max_chunk_size:
                chunks[-1] = (merged, prev_start, offset + len(text))
            else:
                # 병합하면 max 초과 -> 별도 청크로
                chunks.append(...)
        else:
            chunks.append(...)
```

**문제점**:

1. **`min_chunk_size`가 문자 수 기준이지 토큰 수 기준이 아님**: `min_chunk_size=100`은 100문자입니다. 한국어로 100문자면 약 30토큰이므로 충분히 의미 있지만, 영어 10토큰은 약 40~50문자입니다. 즉 50문자의 영어 텍스트는 `min_chunk_size` 검사를 통과하지 못하지만, `len(chunk_content) < self.min_chunk_size and chunks` 조건에서 `chunks`가 비어 있으면(첫 번째이자 마지막 청크) 그대로 저장됩니다.

2. **섹션 기반 청킹에서 짧은 섹션 처리**: `_chunk_with_sections()`(line 246-292)에서 각 섹션을 개별적으로 청킹한 후 `_merge_small_adjacent_chunks()`(line 692-753)로 후처리합니다. 이 병합 로직은 `token_count < 20`인 청크만 병합 대상으로 삼지만:

    - 인접 청크가 이미 `max_chunk_size`에 가까우면 병합 불가 → 작은 청크가 그대로 남음
    - 섹션의 마지막 청크이고 다음 섹션의 첫 청크와는 병합하지 않음 (ADR-002: 섹션 간 병합 금지)
    - `token_count >= 20`이지만 실제로는 의미 없는 청크(예: 표 헤더만 있는 경우)는 병합 대상에서 제외

3. **PDF 파서가 페이지 헤더/푸터를 별도 섹션으로 추출**: Docling이 반복되는 페이지 번호, 회사명, 날짜 등을 섹션으로 추출하면 각각이 짧은 청크가 됩니다.

### 수정 방안
- 최종 필터링 단계 추가: `token_count < 10` 청크를 드롭 또는 인접 청크에 강제 병합
- `_merge_small_adjacent_chunks()`에서 섹션 간 병합도 허용하되 heading 보존
- 토큰 수 기반 `min_chunk_tokens` 파라미터 추가

---

## 문제 4: Ultra-long 청크 88개 (>500 tokens, 최대 6,765)

### 증상
`chunk_size=1000` (문자)인데 6,765 토큰짜리 청크가 존재.

### 근본 원인 (코드 위치)

**파일**: `knowledge_service/src/app/etl/chunker.py:460-464`

```python
if seg_type in ("code", "table"):
    # 특수 블록: 그대로 하나의 청크로
    # max_chunk_size 초과해도 분할하지 않음
    raw_chunks.append((content.strip(), seg_start, seg_end, seg_type))
```

**문제점**:

1. **특수 블록(코드/테이블)은 크기 제한 없이 통째로 청크가 됨**: 코드 주석에 명시적으로 "max_chunk_size 초과해도 분할하지 않음"이라고 적혀 있습니다. 대형 Markdown 테이블(수백 행)이나 긴 코드 블록이 그대로 하나의 청크가 됩니다.

2. **`chunk_size=1000`과 `max_chunk_size=2048`의 불일치**: `run_etl_phase1_chunks.py:193-196`에서 `chunk_size=1000`을 설정하지만, `SemanticChunker.__init__`의 기본값 `max_chunk_size=2048`이 사용됩니다(line 88). `run_etl_phase1_chunks.py`에서 `max_chunk_size`를 명시적으로 설정하지 않습니다. 그런데 이것도 특수 블록에는 적용되지 않으므로 근본적 해결이 아닙니다.

3. **`chunk_overlap=200`과 `chunk_size=1000`의 설정 불일치**: `run_etl_phase1_chunks.py:196`에서 `chunk_overlap=200`을 설정하지만, `InitialDataLoader.__init__`의 기본값은 `chunk_overlap=100`(line 259)입니다. 이것이 오버랩 처리를 과도하게 만들어 간접적으로 긴 청크를 유발합니다.

4. **PDF의 대형 테이블이 하나의 텍스트 블록으로 파싱됨**: Docling이 PDF 테이블을 Markdown 형태로 변환하면, `TABLE_BLOCK_PATTERN`(line 62-64)이 이를 캐치하여 단일 청크로 보존합니다. 6,765 토큰짜리 청크는 대형 테이블일 가능성이 높습니다.

### 수정 방안
- 특수 블록에 `max_chunk_size` 적용: 초과 시 행/문단 단위로 분할
- `max_chunk_size`를 `run_etl_phase1_chunks.py`에서 명시적으로 설정
- 테이블 청크에 대한 별도 분할 전략 (행 그룹 단위)

---

## 문제 5: 임베딩 상태 혼재 (success=5,336, pending=4,869, completed=465)

### 증상
ES `knowledge_chunks` 인덱스에 `embedding_status` 필드가 3가지 값(`success`, `pending`, `completed`)으로 혼재.

### 근본 원인 (코드 위치)

**3개의 서로 다른 코드 경로가 각각 다른 상태값을 사용**:

| 상태값 | 설정 위치 | 코드 경로 |
|--------|-----------|-----------|
| `"pending"` | `initial_data_loader.py:1285` | Phase 1 ETL (임베딩 OFF) |
| `"success"` | `initial_data_loader.py:1285` / `document_processing_pipeline.py:720` | Phase 1 (임베딩 ON) / 개별 문서 처리 |
| `"completed"` | `import_embeddings.py:54` | GPU 임베딩 결과 임포트 |

```python
# initial_data_loader.py:1285
"embedding_status": "success" if embeddings else "pending",

# document_processing_pipeline.py:720
"embedding_status": "success",

# import_embeddings.py:54
"embedding_status": "completed",
```

**문제점**:

1. **상태 Enum이 정의되지 않음**: `embedding_status`에 대한 공식 Enum이나 상수가 없습니다. 각 스크립트/서비스가 독자적으로 문자열을 사용합니다.

2. **"success"와 "completed"의 의미 차이가 불명확**: `initial_data_loader.py`는 `"success"`를, `import_embeddings.py`는 `"completed"`를 사용합니다. 둘 다 "임베딩 완료"를 의미하지만 문자열이 다릅니다.

3. **Phase 2에서 `"completed"`로 갱신되지만, Phase 1의 `"success"`는 업데이트되지 않음**: Phase 1에서 로컬 임베딩으로 처리된 청크는 `"success"`, Colab GPU 임포트된 청크는 `"completed"`, 아직 처리 안 된 것은 `"pending"`입니다. 검색 쿼리에서 어떤 상태를 기준으로 필터링해야 하는지 혼란이 발생합니다.

### 수정 방안
- `EmbeddingStatus` Enum 정의: `pending`, `processing`, `completed`, `failed`, `skipped`
- 모든 코드 경로에서 동일한 Enum 사용
- `"success"` → `"completed"`로 통일

---

## 문제 6: OOM Kill (46MB PDF)

### 증상
46MB PDF 처리 시 컨테이너 메모리가 폭발하여 OOM Kill 발생.

### 근본 원인 (코드 위치)

**파일**: `knowledge_service/scripts/run_etl_phase1_chunks.py:119,143-154`

```python
MAX_FILE_SIZE_MB = 30  # 30MB 초과 파일은 OOM 방지를 위해 스킵

# 대용량 파일 스킵 (OOM 방지)
file_path = Path(file_info.file_path) if hasattr(file_info, 'file_path') else None
if file_path and file_path.exists():
    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        ...
        continue
```

**문제점**:

1. **30MB 제한이 46MB PDF를 막지 못함**: 코드상 `MAX_FILE_SIZE_MB = 30`이므로 46MB 파일은 스킵되어야 합니다. 그런데 이 코드는 **monkey-patch된 `_patched_load_source`** 안에 있습니다. `hasattr(file_info, 'file_path')` 검사 후 `Path(file_info.file_path)` 로 접근하는데, `FileInfo.file_path`는 이미 `Path` 타입(line 109)이므로 정상 작동해야 합니다. 

    **그러나**: 이 보호 코드가 ETL 실행 **도중에** 추가되었을 가능성이 높습니다. 즉, 46MB PDF가 먼저 처리되고, OOM이 발생한 후에야 이 코드가 추가된 것입니다.

2. **근본적으로 Docling PDF 파싱의 메모리 사용량이 관리되지 않음**: `document_parser.py`(OptimizedDocumentParser)에 `max_memory_mb=512`(line 61) 설정이 있지만, 실제로 ETL에서 사용하는 것은 `DocumentParser`(`parser.py`)이고 `OptimizedDocumentParser`가 아닙니다. `initial_data_loader.py:314`에서 `from app.etl.parser import DocumentParser`를 사용합니다. `DocumentParser`에는 메모리 제한 기능이 없습니다.

3. **대용량 PDF 스트리밍 파싱이 사용되지 않음**: `OptimizedDocumentParser`에 `parse_large_document_stream()`이 있지만 ETL 파이프라인에서 호출하지 않습니다.

### 수정 방안
- `DocumentParser`에 메모리 모니터링 추가
- 20MB 이상 PDF는 페이지 단위 스트리밍 파싱 적용
- Docker 컨테이너 메모리 제한 + OOM 시 graceful 복구

---

## 문제 7: 모니터 스크립트 버그 (grep -c 개행문자)

### 증상
모니터 스크립트가 grep 출력에 개행문자가 포함되어 산술 연산이 실패하고 크래시.

### 근본 원인 (코드 위치)

**파일**: `knowledge_service/scripts/etl_phase1_monitor.sh:27-29`

```bash
SUCCESS=$(docker exec kp-ai-service grep -c "processed successfully" "$LOG_FILE" 2>/dev/null | tr -d '\n\r ' || echo "0")
SKIPPED=$(docker exec kp-ai-service grep -c "Skipping duplicate" "$LOG_FILE" 2>/dev/null | tr -d '\n\r ' || echo "0")
FAILED=$(docker exec kp-ai-service grep -c -E "failed after|Parse error" "$LOG_FILE" 2>/dev/null | tr -d '\n\r ' || echo "0")
```

**문제점**:

1. **`tr -d '\n\r '`로 개행 제거를 시도했지만 부족**: `docker exec` 출력에는 캐리지 리턴(`\r`)이 포함될 수 있으며(Docker Windows/WSL2 환경), `tr -d`가 일부 제어 문자를 놓칠 수 있습니다.

2. **`grep -c`가 파일 미존재 시 에러 반환**: 로그 파일이 아직 생성되지 않았거나, 컨테이너가 재시작된 경우 `grep -c`가 exit code 2(에러)를 반환합니다. `2>/dev/null`로 stderr를 삼키지만 stdout에는 아무것도 출력되지 않고, `|| echo "0"` 이 `docker exec ... | tr -d ...` 전체 파이프라인이 아닌 `tr -d` 만의 실패에 대해 작동합니다.

3. **실제 크래시 원인**: line 56에서 `PROCESSED=$((SUCCESS + SKIPPED + FAILED))`를 계산할 때, `SUCCESS` 등에 빈 문자열이나 비숫자 문자가 포함되면 bash 산술 연산이 에러를 발생시킵니다. line 65에서 `[ "$PREV_CHUNKS" -gt 0 ]` 비교도 마찬가지입니다. `${SUCCESS:-0}` 폴백(line 31-36)이 있지만, 변수에 이미 비어있지 않은 비숫자 값(예: ANSI 색상 코드, `\r` 잔여)이 들어가면 폴백이 작동하지 않습니다.

### 수정 방안
- 파이프라인 전체를 서브쉘로 감싸기: `SUCCESS=$(... || echo "0")`
- 숫자 검증 추가: `SUCCESS=$(echo "$RAW" | grep -oE '[0-9]+' | head -1)`
- `set -euo pipefail` 대신 각 명령에 개별 에러 처리

---

## 문제 8: 2시간 장애 무감지

### 증상
ETL 프로세스가 OOM으로 죽은 후 2시간 동안 아무도 감지하지 못함. 모니터 스크립트도 함께 죽었거나 비정상 동작.

### 근본 원인 (코드 위치)

**파일**: `knowledge_service/scripts/etl_phase1_monitor.sh:5,17,79-89`

```bash
INTERVAL=900  # 15분

while true; do
    sleep "$INTERVAL"  # <-- 루프 시작이 sleep!
    ...
    # 3회 연속 변화 없으면 ETL 프로세스 생존 확인
    if [ "$STALE_COUNT" -ge 3 ]; then
        ETL_ALIVE=$(docker top kp-ai-service 2>/dev/null | grep -c "run_etl" || echo "0")
        ...
    fi
done
```

**문제점**:

1. **모니터 루프가 `sleep`으로 시작함**: 첫 체크까지 15분 대기. 즉, 모니터 시작 직후 ETL이 죽으면 최소 15분은 감지 불가.

2. **"3회 연속 변화 없음" 조건이 최소 45분 필요**: 15분 간격 x 3회 = 45분 후에야 프로세스 사망 체크를 합니다. OOM은 즉시 프로세스를 죽이므로, 45분 동안 청크 증분이 0인 것을 확인한 후에야 알림을 보냅니다.

3. **모니터 자체가 동일 컨테이너에서 실행되지 않음**: 모니터는 호스트에서 `docker exec`로 컨테이너 상태를 조회합니다. 그런데 모니터 스크립트 자체가 `nohup`으로 실행되었더라도, WSL2 세션이 끊기거나 터미널이 닫히면 모니터도 종료됩니다.

4. **모니터가 문제 7(grep 크래시)로 일찍 죽었을 가능성**: 모니터 스크립트에 `set -uo pipefail` 같은 strict mode가 없지만(실제로 없음), bash 산술 연산 에러가 스크립트를 중단시켰을 수 있습니다.

5. **알림 전달 경로가 불안정**: line 86에서 `bash "$SEND_SLACK" alerts ...`를 호출하지만, `$SEND_SLACK` 경로가 `$PROJECT_ROOT/scripts/send_slack.sh`(line 9)로 설정됩니다. 경로 계산이 `$SCRIPT_DIR` 기준이므로, 모니터 스크립트를 다른 위치에서 실행하면 경로가 틀릴 수 있습니다.

### 수정 방안
- 모니터 간격을 5분으로 줄이고, 1회 변화 없음에 경고, 2회에 알림
- `sleep`을 루프 끝으로 이동 (첫 실행 즉시 체크)
- 별도의 Docker healthcheck 또는 systemd 서비스로 모니터 실행
- 모니터 자체에 watchdog 추가 (heartbeat 파일 + cron 체크)

---

## Tech Lead 반성

### 내가 하지 못한 것

1. **사전 코드 리뷰 부재**: ETL 파이프라인 코드를 실행 전에 리뷰하지 않았습니다. chunker의 특수 블록 무제한 크기, dedup 쿼리의 `processing_status` 조건, embedding_status의 비표준화 등은 코드를 읽기만 해도 발견할 수 있는 문제였습니다.

2. **데이터 품질 게이트 미설정**: "청크 생성 후 ES 저장 전에 품질 검사를 수행한다"는 게이트가 없었습니다. token_count 최소/최대값 체크, 노이즈 패턴 필터링 등 기본적인 검증 단계를 설계에 포함시키지 않았습니다.

3. **모니터링 아키텍처 미검토**: 모니터 스크립트의 장애 감지 로직이 45분이나 걸린다는 것을 검토하지 않았습니다. 프로덕션 모니터링의 기본 원칙(빠른 감지, 빠른 알림)을 ETL 모니터링에도 적용했어야 합니다.

4. **상태 관리 표준화 부재**: `embedding_status` 같은 중요 필드의 값이 3개 코드 경로에서 제각각이라는 것은 표준 Enum을 정의하지 않은 아키텍처 결함입니다. TL로서 이런 표준을 잡는 것이 내 역할이었습니다.

5. **OOM 시나리오 테스트 미요구**: "46MB PDF를 처리하면 어떻게 되는가?"라는 질문을 하지 않았습니다. 경계값 테스트를 QA에게 요청하거나, 직접 메모리 프로파일링을 요구했어야 합니다.

### 앞으로 하겠습니다

1. **ETL 코드 변경 시 반드시 TL 리뷰 거치기**: PR 없는 직접 수정 금지
2. **데이터 품질 게이트 문서화**: 청크 최소/최대 토큰, 노이즈 패턴 목록, 중복 검사 규칙을 ADR로 작성
3. **모니터링 SLA 설정**: 장애 감지 5분 이내, 알림 10분 이내
4. **상태 필드 Enum 표준화**: 모든 상태값을 중앙 Enum으로 관리
5. **대용량 파일 테스트 시나리오 작성**: 10MB, 30MB, 50MB, 100MB 파일에 대한 메모리/시간 프로파일링

---

## 코드 위치 요약

| 문제 | 파일 | 라인 |
|------|------|------|
| PG 중복 | `initial_data_loader.py` | 649-695 (dedup), 1166-1227 (PG저장), 805 (uuid) |
| Junk 청크 | `chunker.py` | 666-690 (노이즈필터), 460-464 (특수블록) |
| Short 청크 | `chunker.py` | 537-566 (마지막청크), 692-753 (병합) |
| Ultra-long | `chunker.py` | 460-464 (특수블록 무제한) |
| 상태 혼재 | `initial_data_loader.py:1285`, `import_embeddings.py:54`, `document_processing_pipeline.py:720` | 각각 다른 값 |
| OOM Kill | `run_etl_phase1_chunks.py` | 119,143-154 (사후방어), `parser.py` (메모리무관리) |
| 모니터 버그 | `etl_phase1_monitor.sh` | 27-29 (grep), 56 (산술), 65 (비교) |
| 장애 무감지 | `etl_phase1_monitor.sh` | 5 (간격), 17 (sleep먼저), 79-89 (3회조건) |

---

*TechLead는 "코드는 거짓말하지 않는다"고 말하면서, 정작 코드를 읽지 않았습니다. 이번 실패의 가장 큰 원인은 코드 리뷰를 생략한 것입니다.*
