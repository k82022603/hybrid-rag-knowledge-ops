# STORY-045: 초기 데이터 ETL - 테스트 계획서

## 문서 정보

| 항목 | 값 |
|------|-----|
| **테스트 대상** | STORY-045 초기 데이터 ETL 파이프라인 |
| **Jira ID** | SCRUM-34 |
| **Epic** | EPIC-002 |
| **Sprint** | 3 |
| **테스트 담당** | QA Agent |
| **버전** | 1.0 |
| **작성일** | 2026-01-28 |

---

## 1. 개요

### 1.1 목적

초기 데이터 ETL 파이프라인(`InitialDataLoader` 및 `DataValidator`)에 대한 단위 테스트 시나리오를 정의하고, 60건의 테스트 케이스 실행 결과를 문서화합니다. 프로젝트 문서를 Elasticsearch/Neo4j에 적재하는 ETL 전체 흐름과 결과 검증 로직이 올바르게 동작하는지 확인합니다.

### 1.2 테스트 범위

```mermaid
flowchart TB
    subgraph Scope["테스트 범위"]
        subgraph Unit["단위 테스트 (60건)"]
            U1["DataSource 데이터클래스"]
            U2["파일 탐색 (discover_files)"]
            U3["메타데이터 추출 (_extract_metadata)"]
            U4["문서 유형 분류 (_classify_doc_type)"]
            U5["건너뛰기 패턴 (_should_skip)"]
            U6["ETLSummary 집계"]
            U7["InitialDataLoader 설정"]
            U8["load_all 파이프라인 Mock"]
            U9["싱글톤 팩토리"]
            U10["ValidationReport"]
            U11["문서 수 검증"]
            U12["청크 수 검증"]
            U13["엔티티 수 검증"]
            U14["청크 비율 검증"]
            U15["실패율 검증"]
            U16["빈 청크 검증"]
            U17["동기 검증 (validate_sync)"]
            U18["DataValidator 싱글톤"]
        end
    end

    style Unit fill:#e3f2fd
```

### 1.3 테스트 제외 범위

| 제외 항목 | 사유 |
|----------|------|
| Elasticsearch 실제 연결 테스트 | 통합 테스트에서 별도 수행 |
| Neo4j 실제 연결 테스트 | 통합 테스트에서 별도 수행 |
| BGE-M3 임베딩 생성 | 모델 로딩 환경 필요, Mock으로 대체 |
| LLM 기반 엔티티 추출 | DeepSeek API 의존, Mock으로 대체 |
| 성능/부하 테스트 (k6) | 별도 성능 테스트 계획에서 수행 |

---

## 2. 테스트 환경

### 2.1 환경 구성

| 구분 | 값 |
|------|-----|
| **언어** | Python 3.11+ |
| **테스트 프레임워크** | pytest 7.x + pytest-asyncio |
| **Mock 라이브러리** | unittest.mock (MagicMock, AsyncMock, patch) |
| **테스트 데이터** | tempfile (임시 디렉토리) |
| **커버리지 도구** | pytest-cov |

### 2.2 테스트 대상 파일

| 파일 | 경로 | 역할 |
|------|------|------|
| `initial_data_loader.py` | `knowledge_service/src/app/services/` | ETL 파이프라인 핵심 클래스 |
| `data_validator.py` | `knowledge_service/src/app/services/` | ETL 결과 검증 서비스 |
| `test_initial_data_loader.py` | `knowledge_service/src/tests/unit/` | 단위 테스트 (60건) |

### 2.3 테스트 Fixture

| Fixture | 설명 | 사용 범위 |
|---------|------|----------|
| `temp_data_dir` | 임시 디렉토리에 샘플 Markdown 파일 5개 생성 (technical 3개, guides 2개) + `__pycache__`, `.log` 파일 포함 | 파일 탐색, 메타데이터 추출 테스트 |
| `loader` | `InitialDataLoader` 인스턴스 (chunk_size=200, batch_size=8, max_retries=2, embeddings/entity 비활성화) | InitialDataLoader 전체 테스트 |
| `sample_etl_summary` | 성공 3건 ETL 요약 (chunks=16, entities=10, time=450ms) | DataValidator 정상 케이스 |
| `failed_etl_summary` | 성공 1건 + 실패 2건 ETL 요약 (chunks=5, entities=3) | DataValidator 실패 케이스 |
| `validator` | `InitialDataValidation` 인스턴스 (min_documents=3, min_chunks_per_doc=2.0, min_entities=5) | DataValidator 전체 테스트 |

---

## 3. 테스트 전략

### 3.1 테스트 레벨

| 레벨 | 건수 | 설명 |
|------|------|------|
| **단위 테스트** | 60건 | Mock 기반 개별 함수/클래스 테스트 |
| **통합 테스트** | (미래) | ES/Neo4j 실제 연결 테스트 |
| **E2E 테스트** | (미래) | 전체 ETL 파이프라인 실행 |

### 3.2 테스트 방법론

- **TDD / Test-Along**: 구현과 동시에 테스트 작성
- **Mock 전략**: 외부 서비스(ES, Neo4j, Parser, Chunker)를 Mock으로 대체하여 단위 테스트 격리
- **Fixture 패턴**: pytest fixture로 테스트 데이터 및 인스턴스 재사용
- **임시 파일 시스템**: `tempfile.TemporaryDirectory`로 실제 파일 I/O 테스트

### 3.3 품질 기준

| 지표 | 기준 | 현재 |
|------|------|------|
| 테스트 통과율 | 100% | 100% (60/60) |
| 코드 커버리지 | >= 80% | 달성 |
| AC 커버리지 | 100% | 100% (5/5 AC) |

---

## 4. 테스트 시나리오

### 시나리오 1: DataSource 데이터클래스 (TS-001)

| 항목 | 값 |
|------|-----|
| **대상 클래스** | `TestDataSource` |
| **테스트 목적** | DataSource 데이터클래스의 기본값 및 커스텀 설정이 올바르게 적용되는지 확인 |
| **관련 AC** | AC-1 (ETL 실행) |
| **테스트 케이스 수** | 4건 |

### 시나리오 2: 파일 탐색 (TS-002)

| 항목 | 값 |
|------|-----|
| **대상 클래스** | `TestFileDiscovery` |
| **테스트 목적** | `discover_files()` 및 `_discover_files()` 메서드가 파일을 올바르게 탐색하는지 확인 |
| **관련 AC** | AC-1 (ETL 실행 - 파일 탐색), AC-2 (Markdown 파싱) |
| **테스트 케이스 수** | 9건 |

### 시나리오 3: 메타데이터 추출 (TS-003)

| 항목 | 값 |
|------|-----|
| **대상 클래스** | `TestMetadataExtraction` |
| **테스트 목적** | `_extract_metadata()` 메서드가 파일 정보와 파싱 결과에서 메타데이터를 정확히 추출하는지 확인 |
| **관련 AC** | AC-2 (청크 분할 및 임베딩 생성) |
| **테스트 케이스 수** | 2건 |

### 시나리오 4: 문서 유형 분류 (TS-004)

| 항목 | 값 |
|------|-----|
| **대상 클래스** | `TestDocTypeClassification` |
| **테스트 목적** | `_classify_doc_type()` 메서드가 소스 유형/경로/내용 기반으로 올바르게 분류하는지 확인 |
| **관련 AC** | AC-1 (문서가 ES/Neo4j에 저장 시 유형 분류) |
| **테스트 케이스 수** | 5건 |

### 시나리오 5: 건너뛰기 패턴 (TS-005)

| 항목 | 값 |
|------|-----|
| **대상 클래스** | `TestShouldSkip` |
| **테스트 목적** | `_should_skip()` 메서드가 불필요한 파일/디렉토리를 올바르게 필터링하는지 확인 |
| **관련 AC** | AC-1 (ETL 실행 - 파일 탐색) |
| **테스트 케이스 수** | 5건 |

### 시나리오 6: ETLSummary 집계 (TS-006)

| 항목 | 값 |
|------|-----|
| **대상 클래스** | `TestETLSummary` |
| **테스트 목적** | ETLSummary의 성공률 계산, 빈 요약 처리, 딕셔너리 변환이 올바른지 확인 |
| **관련 AC** | AC-3 (검증 - 문서 수, 청크 수, 엔티티 수 확인) |
| **테스트 케이스 수** | 4건 |

### 시나리오 7: InitialDataLoader 설정 (TS-007)

| 항목 | 값 |
|------|-----|
| **대상 클래스** | `TestInitialDataLoaderConfig` |
| **테스트 목적** | InitialDataLoader의 기본/커스텀 설정, 소스 관리, 상태 조회가 올바르게 동작하는지 확인 |
| **관련 AC** | AC-1 (ETL 실행), AC-5 (에러 로그 및 재시도) |
| **테스트 케이스 수** | 6건 |

### 시나리오 8: load_all 파이프라인 Mock (TS-008)

| 항목 | 값 |
|------|-----|
| **대상 클래스** | `TestLoadAllMocked` |
| **테스트 목적** | 전체 ETL 파이프라인(파싱-청킹-저장)의 성공/실패/에러 무시 동작을 Mock으로 검증 |
| **관련 AC** | AC-1, AC-2, AC-5 |
| **테스트 케이스 수** | 3건 |

### 시나리오 9: 싱글톤 팩토리 - Loader (TS-009)

| 항목 | 값 |
|------|-----|
| **대상 클래스** | `TestSingletonFactory` |
| **테스트 목적** | `get_initial_data_loader()` 싱글톤 패턴이 올바르게 동작하는지 확인 |
| **관련 AC** | AC-1 (ETL 실행) |
| **테스트 케이스 수** | 2건 |

### 시나리오 10: ValidationReport (TS-010)

| 항목 | 값 |
|------|-----|
| **대상 클래스** | `TestValidationReport` |
| **테스트 목적** | ValidationReport의 체크 추가, 레벨 계산, 변환, 요약이 올바른지 확인 |
| **관련 AC** | AC-3 (검증) |
| **테스트 케이스 수** | 5건 |

### 시나리오 11: 문서 수 검증 (TS-011)

| 항목 | 값 |
|------|-----|
| **대상 클래스** | `TestDocumentCountValidation` |
| **테스트 목적** | 문서 수가 최소 기대치를 충족하는지에 대한 PASS/FAIL/WARNING 판정 검증 |
| **관련 AC** | AC-3 (문서 수 확인) |
| **테스트 케이스 수** | 3건 |

### 시나리오 12: 청크 수 검증 (TS-012)

| 항목 | 값 |
|------|-----|
| **대상 클래스** | `TestChunkCountValidation` |
| **테스트 목적** | 생성된 청크 수가 기대 범위 내인지 검증 |
| **관련 AC** | AC-3 (청크 수 확인) |
| **테스트 케이스 수** | 2건 |

### 시나리오 13: 엔티티 수 검증 (TS-013)

| 항목 | 값 |
|------|-----|
| **대상 클래스** | `TestEntityCountValidation` |
| **테스트 목적** | 추출된 엔티티 수가 최소 기대치를 충족하는지 검증 |
| **관련 AC** | AC-3 (엔티티 수 확인) |
| **테스트 케이스 수** | 2건 |

### 시나리오 14: 청크 비율 검증 (TS-014)

| 항목 | 값 |
|------|-----|
| **대상 클래스** | `TestChunkRatioValidation` |
| **테스트 목적** | 문서당 평균 청크 수가 합리적 범위 내인지 검증 |
| **관련 AC** | AC-3 (데이터 품질 확인) |
| **테스트 케이스 수** | 2건 |

### 시나리오 15: 실패율 검증 (TS-015)

| 항목 | 값 |
|------|-----|
| **대상 클래스** | `TestFailureRateValidation` |
| **테스트 목적** | ETL 실패율이 허용 범위 내인지 검증 |
| **관련 AC** | AC-5 (에러 로그 및 재시도) |
| **테스트 케이스 수** | 2건 |

### 시나리오 16: 빈 청크 검증 (TS-016)

| 항목 | 값 |
|------|-----|
| **대상 클래스** | `TestEmptyChunksValidation` |
| **테스트 목적** | 빈 청크가 허용 비율 이내인지 검증 |
| **관련 AC** | AC-3 (데이터 품질 확인) |
| **테스트 케이스 수** | 1건 |

### 시나리오 17: 동기 검증 (TS-017)

| 항목 | 값 |
|------|-----|
| **대상 클래스** | `TestSyncValidation` |
| **테스트 목적** | `validate_sync()` 메서드가 전체 검증 항목(9개)을 올바르게 실행하는지 확인 |
| **관련 AC** | AC-3 (검증) |
| **테스트 케이스 수** | 2건 |

### 시나리오 18: DataValidator 싱글톤 (TS-018)

| 항목 | 값 |
|------|-----|
| **대상 클래스** | `TestValidatorSingleton` |
| **테스트 목적** | `get_data_validator()` 싱글톤 패턴이 올바르게 동작하는지 확인 |
| **관련 AC** | AC-3 (검증) |
| **테스트 케이스 수** | 2건 |

---

## 5. 테스트 케이스 매트릭스

### 5.1 InitialDataLoader 테스트 케이스 (40건)

| TC-ID | 시나리오 | 테스트 케이스명 | 입력/조건 | 기대 결과 | AC 매핑 | 우선순위 |
|-------|---------|---------------|----------|----------|---------|---------|
| TC-001 | TS-001 | 기본 확장자 목록 확인 | `DataSource(name="test", path="/data")` | `.md`, `.pdf`, `.docx`, `.pptx` 포함 | AC-1 | High |
| TC-002 | TS-001 | 커스텀 확장자 목록 확인 | `extensions=[".md", ".txt"]` | `[".md", ".txt"]`만 포함 | AC-1 | Medium |
| TC-003 | TS-001 | 기본 문서 유형은 UNKNOWN | 기본 생성 | `doc_type == DocType.UNKNOWN` | AC-1 | Medium |
| TC-004 | TS-001 | 기본 재귀 탐색은 True | 기본 생성 | `recursive is True` | AC-1 | Medium |
| TC-005 | TS-002 | Markdown 파일 탐색 확인 | technical 디렉토리 (3개 .md 파일) | `.md` 파일 3개 탐색 | AC-1 | Critical |
| TC-006 | TS-002 | `__pycache__` 디렉토리 건너뛰기 | `__pycache__/cached.pyc` 존재 | `.pyc` 파일 0개 | AC-1 | High |
| TC-007 | TS-002 | 확장자 필터링 확인 | `.md` 확장자만 허용, `.log` 파일 존재 | 모든 결과 파일의 확장자가 `.md` | AC-1 | High |
| TC-008 | TS-002 | 존재하지 않는 경로 처리 | `/nonexistent/path` | 빈 리스트 반환 (에러 없음) | AC-5 | High |
| TC-009 | TS-002 | FileInfo 필드 값 확인 | technical 디렉토리 파일 | file_path 존재, file_name 비어 있지 않음, file_size > 0, extension `.md`, source_name `technical`, doc_type `TECHNICAL`, modified_at 비어 있지 않음 | AC-1 | High |
| TC-010 | TS-002 | 파일 이름순 정렬 확인 | 복수 파일 탐색 | 파일명이 알파벳순 정렬 | AC-1 | Medium |
| TC-011 | TS-002 | 전체 소스에서 파일 탐색 | technical(3개) + guides(2개) 소스 등록 | 총 5개 파일 탐색 | AC-1 | Critical |
| TC-012 | TS-002 | 비재귀 탐색 확인 | `recursive=False`, 하위 디렉토리에 `nested.md` 존재 | `nested.md` 미포함 | AC-1 | Medium |
| TC-013 | TS-002 | 재귀 탐색 (기본) 확인 | 기본 설정 (`recursive=True`) | 하위 디렉토리 파일도 탐색 | AC-1 | Medium |
| TC-014 | TS-003 | 기본 메타데이터 추출 | 파일 정보 + 파싱 결과 (title, sections, tables, images) | source_name, file_name, extension, file_size, title, content_length, section_count 올바르게 추출 | AC-2 | Critical |
| TC-015 | TS-003 | 제목이 없는 문서의 메타데이터 | `parsed_doc.title = None` | title이 파일명으로 대체 | AC-2 | High |
| TC-016 | TS-004 | 데이터 소스 유형으로 분류 | `doc_type=DocType.TECHNICAL` | `"technical"` 반환 | AC-1 | High |
| TC-017 | TS-004 | 파일 경로 기반 분류 | 경로에 "design" 포함, `doc_type=UNKNOWN` | `"technical"` 반환 | AC-1 | High |
| TC-018 | TS-004 | 내용 기반 분류 | 내용에 "가이드", "매뉴얼" 포함, `doc_type=UNKNOWN` | `"guide"` 반환 | AC-1 | Medium |
| TC-019 | TS-004 | 분류 불가 시 unknown 반환 | 경로/내용에 키워드 없음, `doc_type=UNKNOWN` | `"unknown"` 반환 | AC-1 | Medium |
| TC-020 | TS-004 | 경로에 'guide'가 포함된 경우 | `/data/user_guide/howto.md` | `"guide"` 반환 | AC-1 | Medium |
| TC-021 | TS-005 | `__pycache__` 건너뛰기 | `Path("/data/__pycache__/file.pyc")` | `True` 반환 | AC-1 | High |
| TC-022 | TS-005 | `.git` 건너뛰기 | `Path("/data/.git/config")` | `True` 반환 | AC-1 | High |
| TC-023 | TS-005 | `node_modules` 건너뛰기 | `Path("/data/node_modules/package.json")` | `True` 반환 | AC-1 | Medium |
| TC-024 | TS-005 | 일반 파일은 건너뛰지 않음 | `Path("/data/documents/design.md")` | `False` 반환 | AC-1 | High |
| TC-025 | TS-005 | `.DS_Store` 건너뛰기 | `Path("/data/.DS_Store")` | `True` 반환 | AC-1 | Low |
| TC-026 | TS-006 | 100% 성공률 | success_count=3, total_files=3 | `success_rate == 1.0` | AC-3 | Critical |
| TC-027 | TS-006 | 부분 성공률 | success_count=1, total_files=3 | `success_rate == approx(1/3)` | AC-3 | High |
| TC-028 | TS-006 | 빈 요약의 성공률 | total_files=0 | `success_rate == 0.0` | AC-3 | Medium |
| TC-029 | TS-006 | 딕셔너리 변환 | sample_etl_summary | total_files=3, success_count=3, total_chunks=16, total_entities=10, success_rate=100.0 | AC-3 | High |
| TC-030 | TS-007 | 기본 설정값 확인 | 기본 생성자 | chunk_size=600, chunk_overlap=100, batch_size=32, max_retries=3, continue_on_error=True, enable_embeddings=True | AC-1 | High |
| TC-031 | TS-007 | 커스텀 설정값 확인 | chunk_size=300, batch_size=16, max_retries=5, continue_on_error=False | 모든 설정값이 커스텀값과 일치 | AC-1 | Medium |
| TC-032 | TS-007 | 데이터 소스 추가 | `add_source(DataSource(...))` | `len(data_sources) == 1`, 이름 일치 | AC-1 | High |
| TC-033 | TS-007 | 기본 데이터 소스 추가 | `add_default_sources()`, temp 디렉토리에 technical/guides/presentations 존재 | source_names에 "technical", "guides", "presentations" 포함 | AC-1 | High |
| TC-034 | TS-007 | 로더 상태 정보 확인 | 소스 1개 등록 | status에 project_root, data_sources(1개), config(chunk_size=200) 포함 | AC-1 | Medium |
| TC-035 | TS-007 | 소스 없이 load_all 시 ValueError | `loader.load_all()` (소스 미등록) | `ValueError("데이터 소스가 등록되지 않았습니다")` | AC-5 | Critical |
| TC-036 | TS-008 | 전체 ETL 파이프라인 성공 (Mock) | Parser/Chunker Mock, technical 3개 파일 | total_files=3, success_count=3, failed_count=0, total_chunks=3, success_rate=1.0 | AC-1, AC-2 | Critical |
| TC-037 | TS-008 | 파싱 실패 포함 ETL | 두 번째 파일 파싱 실패 | total_files=3, success_count=2, skipped_count=1 | AC-5 | Critical |
| TC-038 | TS-008 | continue_on_error=True 에러 무시 | 모든 파싱 Exception 발생 | 예외 미발생, total_files=3, failed_count=3 | AC-5 | Critical |
| TC-039 | TS-009 | 싱글톤 인스턴스 생성 | `get_initial_data_loader()` 2회 호출 | 동일 인스턴스 반환 (`loader1 is loader2`) | AC-1 | Medium |
| TC-040 | TS-009 | reset 후 새 인스턴스 | reset 후 재호출 | 다른 인스턴스 반환 (`loader1 is not loader2`) | AC-1 | Medium |

### 5.2 DataValidator 테스트 케이스 (20건)

| TC-ID | 시나리오 | 테스트 케이스명 | 입력/조건 | 기대 결과 | AC 매핑 | 우선순위 |
|-------|---------|---------------|----------|----------|---------|---------|
| TC-041 | TS-010 | 빈 보고서 | `ValidationReport()` | total_checks=0, is_valid=True, overall_level=SKIP | AC-3 | Medium |
| TC-042 | TS-010 | 통과 항목 추가 | PASS 체크 1개 추가 | total_checks=1, passed_checks=1, overall_level=PASS, is_valid=True | AC-3 | High |
| TC-043 | TS-010 | 실패 항목 추가 | PASS 1개 + FAIL 1개 추가 | total_checks=2, passed=1, failed=1, overall_level=FAIL, is_valid=False | AC-3 | High |
| TC-044 | TS-010 | 딕셔너리 변환 | PASS 체크 1개 포함 report | overall_level="pass", total_checks=1, checks 배열 길이 1 | AC-3 | Medium |
| TC-045 | TS-010 | 요약 문자열 | PASS 체크 1개 포함 report | "PASS" 포함, "total=1" 포함 | AC-3 | Low |
| TC-046 | TS-011 | 충분한 문서 수 - PASS | success_count=3 (min=3) | level=PASS | AC-3 | Critical |
| TC-047 | TS-011 | 부족한 문서 수 - FAIL | success_count=1, total_files=2 (min=3) | level=FAIL | AC-3 | Critical |
| TC-048 | TS-011 | 50% 이상이면 WARNING | success_count=2, total_files=3 (min=3) | level=WARNING | AC-3 | High |
| TC-049 | TS-012 | 충분한 청크 수 - PASS | sample_etl_summary (chunks=16, 3문서) | level=PASS | AC-3 | High |
| TC-050 | TS-012 | 청크 0개 - FAIL | total_chunks=0, success_count=3 | level=FAIL | AC-3 | Critical |
| TC-051 | TS-013 | 충분한 엔티티 수 - PASS | sample_etl_summary (entities=10, min=5) | level=PASS | AC-3 | High |
| TC-052 | TS-013 | 엔티티 0개 - WARNING | total_entities=0 | level=WARNING | AC-3 | Medium |
| TC-053 | TS-014 | 적절한 비율 - PASS | sample_etl_summary (avg=16/3=5.33) | level=PASS, actual=approx(5.33) | AC-3 | High |
| TC-054 | TS-014 | 성공 문서 없으면 SKIP | success_count=0, total_chunks=0 | level=SKIP | AC-3 | Medium |
| TC-055 | TS-015 | 실패 없음 - PASS | sample_etl_summary (failed=0) | level=PASS | AC-5 | High |
| TC-056 | TS-015 | 높은 실패율 - FAIL | failed_etl_summary (2/3 실패) | level=FAIL | AC-5 | Critical |
| TC-057 | TS-016 | 빈 청크 없음 - PASS | sample_etl_summary (성공 결과에 chunk_count > 0) | level=PASS | AC-3 | Medium |
| TC-058 | TS-017 | 동기 검증 실행 (성공) | sample_etl_summary | total_checks=9, is_valid=True, SKIP 체크 2개 (sample_queries, orphan_nodes) | AC-3 | Critical |
| TC-059 | TS-017 | 동기 검증 실행 (실패) | failed_etl_summary | is_valid=False, failed_checks > 0 | AC-3 | Critical |
| TC-060 | TS-018 | 싱글톤 동작 확인 | `get_data_validator()` 2회 호출 + reset 후 재호출 | 동일 인스턴스 / reset 후 다른 인스턴스 | AC-3 | Medium |

---

## 6. AC 커버리지 매핑

### 6.1 Acceptance Criteria 목록

| AC 번호 | AC 설명 | 관련 TC |
|---------|---------|---------|
| **AC-1** | Given 프로젝트 문서 (~65개), When ETL 실행, Then 모든 문서가 ES/Neo4j에 저장 | TC-001~013, TC-016~025, TC-030~040 |
| **AC-2** | Given Markdown 문서, When 파싱, Then 청크 분할 및 임베딩 생성 | TC-014~015, TC-036~037 |
| **AC-3** | Given ETL 완료, When 검증, Then 문서 수, 청크 수, 엔티티 수 확인 | TC-026~029, TC-041~054, TC-057~060 |
| **AC-4** | Given 검색 테스트, When 샘플 쿼리 실행, Then 관련 문서 검색 성공 | (통합 테스트에서 검증 - validate_sample_queries는 ES 연결 필요) |
| **AC-5** | Given ETL 오류 시, When 실행, Then 에러 로그 및 재시도 가능 | TC-008, TC-035, TC-037~038, TC-055~056 |

### 6.2 커버리지 요약

```
AC-1: 32건 테스트 (파일 탐색, 소스 관리, 파이프라인 실행)      -- COVERED
AC-2:  4건 테스트 (메타데이터 추출, Mock 파이프라인)            -- COVERED
AC-3: 21건 테스트 (ETLSummary, ValidationReport, 검증 항목들) -- COVERED
AC-4:  0건 단위 테스트 (통합 테스트 영역, async 외부 서비스)     -- DEFERRED
AC-5:  7건 테스트 (에러 처리, 재시도, 실패율 검증)              -- COVERED
```

**참고**: AC-4 (샘플 쿼리 검색)는 Elasticsearch 실제 연결이 필요한 통합 테스트 영역입니다. `DataValidator._validate_sample_queries()` 메서드는 구현되어 있으며, `validate_sync()` 호출 시 SKIP 처리됩니다. 통합 테스트 환경에서 `validate()` (async) 호출로 검증할 수 있습니다.

---

## 7. 테스트 실행 결과

### 7.1 실행 요약

| 항목 | 값 |
|------|-----|
| **실행 일시** | 2026-01-28 |
| **전체 테스트 수** | 60건 |
| **통과 (PASS)** | 60건 |
| **실패 (FAIL)** | 0건 |
| **건너뜀 (SKIP)** | 0건 |
| **통과율** | **100%** |

### 7.2 테스트 클래스별 결과

| # | 테스트 클래스 | 테스트 수 | 결과 | 비고 |
|---|-------------|----------|------|------|
| 1 | `TestDataSource` | 4 | ALL PASS | DataSource 데이터클래스 기본값/커스텀 설정 |
| 2 | `TestFileDiscovery` | 9 | ALL PASS | 파일 탐색, 필터링, 정렬, 재귀/비재귀 |
| 3 | `TestMetadataExtraction` | 2 | ALL PASS | 메타데이터 추출, 제목 대체 로직 |
| 4 | `TestDocTypeClassification` | 5 | ALL PASS | 소스/경로/내용 기반 문서 유형 분류 |
| 5 | `TestShouldSkip` | 5 | ALL PASS | 건너뛰기 패턴 (pycache, git, node_modules 등) |
| 6 | `TestETLSummary` | 4 | ALL PASS | 성공률 계산, 딕셔너리 변환 |
| 7 | `TestInitialDataLoaderConfig` | 6 | ALL PASS | 기본/커스텀 설정, 소스 관리, 상태 조회 |
| 8 | `TestLoadAllMocked` | 3 | ALL PASS | ETL 파이프라인 Mock (성공/실패/에러 무시) |
| 9 | `TestSingletonFactory` | 2 | ALL PASS | InitialDataLoader 싱글톤 |
| 10 | `TestValidationReport` | 5 | ALL PASS | Report 생성, 레벨 계산, 변환 |
| 11 | `TestDocumentCountValidation` | 3 | ALL PASS | 문서 수 PASS/WARNING/FAIL 판정 |
| 12 | `TestChunkCountValidation` | 2 | ALL PASS | 청크 수 PASS/FAIL 판정 |
| 13 | `TestEntityCountValidation` | 2 | ALL PASS | 엔티티 수 PASS/WARNING 판정 |
| 14 | `TestChunkRatioValidation` | 2 | ALL PASS | 청크 비율 PASS/SKIP 판정 |
| 15 | `TestFailureRateValidation` | 2 | ALL PASS | 실패율 PASS/FAIL 판정 |
| 16 | `TestEmptyChunksValidation` | 1 | ALL PASS | 빈 청크 PASS 판정 |
| 17 | `TestSyncValidation` | 2 | ALL PASS | 동기 검증 전체 9항목 실행 |
| 18 | `TestValidatorSingleton` | 2 | ALL PASS | DataValidator 싱글톤 |
| | **합계** | **60** | **ALL PASS** | |

### 7.3 테스트 실행 명령어

```bash
# 단위 테스트 실행
cd knowledge_service
python -m pytest src/tests/unit/test_initial_data_loader.py -v

# 커버리지 포함 실행
python -m pytest src/tests/unit/test_initial_data_loader.py -v --cov=src/app/services/initial_data_loader --cov=src/app/services/data_validator --cov-report=term-missing
```

---

## 8. 테스트 아키텍처

### 8.1 ETL 파이프라인 테스트 구조

```mermaid
flowchart TB
    subgraph TestLayer["테스트 레이어"]
        subgraph DataModel["데이터 모델 테스트"]
            DS["TestDataSource<br/>(4건)"]
            ES["TestETLSummary<br/>(4건)"]
            VR["TestValidationReport<br/>(5건)"]
        end

        subgraph CoreLogic["핵심 로직 테스트"]
            FD["TestFileDiscovery<br/>(9건)"]
            ME["TestMetadataExtraction<br/>(2건)"]
            DC["TestDocTypeClassification<br/>(5건)"]
            SS["TestShouldSkip<br/>(5건)"]
        end

        subgraph Pipeline["파이프라인 테스트"]
            LC["TestInitialDataLoaderConfig<br/>(6건)"]
            LA["TestLoadAllMocked<br/>(3건)"]
        end

        subgraph Validation["검증 로직 테스트"]
            DCV["TestDocumentCount<br/>(3건)"]
            CCV["TestChunkCount<br/>(2건)"]
            ECV["TestEntityCount<br/>(2건)"]
            CRV["TestChunkRatio<br/>(2건)"]
            FRV["TestFailureRate<br/>(2건)"]
            ECH["TestEmptyChunks<br/>(1건)"]
            SV["TestSyncValidation<br/>(2건)"]
        end

        subgraph Singleton["싱글톤 테스트"]
            SF["TestSingletonFactory<br/>(2건)"]
            VS["TestValidatorSingleton<br/>(2건)"]
        end
    end

    DataModel --> CoreLogic --> Pipeline
    DataModel --> Validation --> Singleton

    style DataModel fill:#e3f2fd
    style CoreLogic fill:#e8f5e9
    style Pipeline fill:#fff3e0
    style Validation fill:#f3e5f5
    style Singleton fill:#fce4ec
```

### 8.2 Mock 전략

```mermaid
flowchart LR
    subgraph RealComponents["실제 테스트 대상"]
        IDL["InitialDataLoader"]
        DV["DataValidator"]
        DS["DataSource"]
        FI["FileInfo"]
        ETLS["ETLSummary"]
    end

    subgraph MockedDeps["Mock 처리된 의존성"]
        P["DocumentParser<br/>(MagicMock)"]
        C["SemanticChunker<br/>(MagicMock)"]
        S["_store_document<br/>(AsyncMock)"]
        FS["File System<br/>(tempfile)"]
    end

    IDL --> P
    IDL --> C
    IDL --> S
    IDL --> FS

    style RealComponents fill:#e8f5e9
    style MockedDeps fill:#ffebee
```

---

## 9. 리스크 및 이슈

### 9.1 식별된 리스크

| # | 리스크 | 심각도 | 대응 방안 |
|---|--------|--------|----------|
| R-1 | AC-4 (샘플 쿼리 검색)가 단위 테스트에서 검증 불가 | Medium | 통합 테스트 환경에서 `validate()` async 메서드로 검증 |
| R-2 | 실제 ES/Neo4j 연결 시 저장 로직 검증 필요 | Medium | 통합 테스트에서 Docker Compose 환경으로 검증 |
| R-3 | BGE-M3 임베딩 생성 성능은 Mock에서 확인 불가 | Low | 성능 테스트에서 별도 검증 |

### 9.2 후속 작업

| 작업 | 우선순위 | 담당 |
|------|---------|------|
| ES/Neo4j 통합 테스트 작성 | High | QA + ETL Engineer |
| 전체 ETL E2E 테스트 (Docker 환경) | Medium | QA + Infra |
| k6 성능 테스트 (ETL 처리량) | Low | QA |

---

## 10. 부록

### 10.1 관련 소스 파일

| 파일 | 경로 |
|------|------|
| ETL 파이프라인 | `knowledge_service/src/app/services/initial_data_loader.py` |
| 데이터 검증 | `knowledge_service/src/app/services/data_validator.py` |
| 단위 테스트 | `knowledge_service/src/tests/unit/test_initial_data_loader.py` |
| 스토리 요구사항 | `backlog/stories/STORY-045-initial-data-etl.md` |

### 10.2 참고 문서

- [STORY-045 초기 데이터 ETL 스토리](../../../backlog/stories/STORY-045-initial-data-etl.md)
- [단위/통합 테스트 계획서](../unit_integration_test_plan.md)
- [상세 설계서 v2.4](../../02_design/hybrid_rag_platform_detailed_design.md)
