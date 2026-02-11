# Embedding Batch Full Cycle 상세 설계서

---

## 문서 정보

| 항목 | 내용 |
|------|------|
| **문서명** | Embedding Batch Full Cycle 상세 설계서 |
| **버전** | 1.0 |
| **작성일** | 2026-02-09 |
| **작성자** | Architect Agent |
| **상태** | Draft |
| **관련 문서** | [상세 설계서 v2.5](./hybrid_rag_platform_detailed_design.md), [인프라 설계서](./infrastructure_detailed_design.md), [ES 매핑](../../../infrastructure/database/elasticsearch/mappings.json) |

---

## 변경 이력

| 버전 | 일자 | 작성자 | 변경 내용 |
|------|------|--------|----------|
| 1.0 | 2026-02-09 | Architect Agent | 초안 작성 - Full Cycle 파이프라인, OOM 방지, 체크포인트 설계 |

---

## 목차

1. [개요](#1-개요)
2. [시스템 컨텍스트](#2-시스템-컨텍스트)
3. [Full Cycle 파이프라인](#3-full-cycle-파이프라인)
4. [실행 모드 설계](#4-실행-모드-설계)
5. [데이터 모델](#5-데이터-모델)
6. [클래스 설계](#6-클래스-설계)
7. [OOM 방지 전략](#7-oom-방지-전략)
8. [체크포인트/재개 메커니즘](#8-체크포인트재개-메커니즘)
9. [작업 이력](#9-작업-이력)
10. [CLI 인터페이스](#10-cli-인터페이스)
11. [에러 처리 전략](#11-에러-처리-전략)
12. [테스트 계획](#12-테스트-계획)

---

## 1. 개요

### 1.1 배경

현재 시스템에는 전체 13,430개의 ES knowledge_chunks 중 약 9,818개가 임베딩 벡터 없이 저장되어 있습니다. 기존 `add_embeddings_batch.py` 스크립트는 다음과 같은 한계를 가지고 있습니다:

| 문제 | 설명 |
|------|------|
| **PG 미갱신** | ES에만 임베딩을 추가하고, PostgreSQL의 `documents.processing_status`, `es_synced`, `es_synced_at` 컬럼을 갱신하지 않음 |
| **체크포인트 없음** | 중단 시 처음부터 다시 시작해야 하며, 처리 완료된 chunk를 다시 처리하는 낭비 발생 |
| **OOM 취약** | WSL 12GB 환경에서 AI Service 웹 프로세스(~3GB)와 BGE-M3 모델(~2GB)이 동시에 실행되면 OOM Kill 반복 |
| **단일 모드** | 미처리 전체만 대상으로 하며, 특정 문서/파일/시점 기반 재처리가 불가능 |
| **결과 미보존** | 작업 결과를 JSON 파일로 남기지 않아 이력 추적 불가 |

### 1.2 목적

`embedding_full_cycle.py`를 신규 개발하여 다음을 달성합니다:

1. **ES + PG 동기화**: 임베딩 생성 후 ES 업데이트와 PG 상태 갱신을 하나의 사이클로 통합
2. **5가지 실행 모드**: all / document / file / reprocess / force 조합으로 유연한 배치 실행
3. **OOM 방지**: 웹 서비스 중지 옵션, 메모리 모니터링, 자동 일시정지
4. **체크포인트/재개**: 100배치마다 체크포인트를 저장하고, 중단 시 `--resume`로 이어서 처리
5. **작업 이력 보존**: JSON 결과 파일을 자동 저장하여 감사 추적(audit trail) 제공

### 1.3 범위

| 포함 | 제외 |
|------|------|
| ES scroll 기반 chunk 조회 | Sparse 임베딩 생성 (향후 확장) |
| BGE-M3 dense 임베딩 생성 | Neo4j 동기화 |
| ES bulk 업데이트 | 청크 재생성 (re-chunking) |
| PG documents 상태 갱신 | 문서 업로드/삭제 |
| 체크포인트 저장/복원 | 실시간 스트리밍 처리 |
| 작업 결과 JSON 저장 | UI 연동 |

### 1.4 관련 문서

- [상세 설계서 v2.5](./hybrid_rag_platform_detailed_design.md) - 전체 아키텍처, BGE-M3 통합 설계
- [인프라 설계서](./infrastructure_detailed_design.md) - Docker Compose 기반 18개 컨테이너
- [ES 매핑](../../../infrastructure/database/elasticsearch/mappings.json) - knowledge_chunks 인덱스 스키마
- [PG 스키마](../../../infrastructure/database/postgres/schema.sql) - documents 테이블 정의

---

## 2. 시스템 컨텍스트

`embedding_full_cycle.py`는 기존 AI Service 컨테이너(kp-ai-service) 내부에서 CLI로 실행되는 배치 프로그램입니다. 웹 서비스와는 독립적으로 동작하며, ES/PG를 직접 연결합니다.

```mermaid
flowchart TB
    subgraph User["운영자"]
        CLI["CLI<br/>(docker exec)"]
    end

    subgraph DockerHost["Docker Host (WSL 12GB)"]
        subgraph AIService["kp-ai-service 컨테이너"]
            WebProc["uvicorn 웹 프로세스<br/>(~3GB RSS)"]
            BatchProc["embedding_full_cycle.py<br/>(배치 프로세스)"]
            BGEM3["BGE-M3 모델<br/>(~2GB VRAM/RAM)"]
        end

        subgraph DataLayer["데이터 레이어"]
            ES["Elasticsearch<br/>knowledge_chunks 인덱스<br/>(13,430 chunks)"]
            PG["PostgreSQL<br/>documents 테이블<br/>(SSOT)"]
            Redis["Redis<br/>임베딩 캐시<br/>(선택)"]
        end

        subgraph GraphLayer["그래프 레이어"]
            Neo4j["Neo4j<br/>(Knowledge Graph)"]
        end
    end

    subgraph Storage["파일 시스템"]
        CP["체크포인트<br/>checkpoint_*.json"]
        Result["결과 파일<br/>result_*.json"]
    end

    CLI -->|"python embedding_full_cycle.py<br/>--mode all --stop-service"| BatchProc
    BatchProc -->|"pkill -f uvicorn<br/>(--stop-service)"| WebProc
    BatchProc -->|"EmbeddingService.embed_batch()"| BGEM3
    BatchProc -->|"scroll API + bulk update"| ES
    BatchProc -->|"asyncpg UPDATE<br/>processing_status, es_synced"| PG
    BatchProc -.->|"캐시 조회/저장<br/>(선택)"| Redis
    BatchProc -->|"100배치마다 저장"| CP
    BatchProc -->|"완료 시 저장"| Result
    ES -.->|"향후 연동"| Neo4j

    style BatchProc fill:#4CAF50,color:#fff
    style BGEM3 fill:#FF9800,color:#fff
    style WebProc fill:#f44336,color:#fff
    style ES fill:#2196F3,color:#fff
    style PG fill:#3F51B5,color:#fff
```

### 2.1 구성 요소 역할

| 구성 요소 | 역할 | 연결 정보 |
|-----------|------|-----------|
| **embedding_full_cycle.py** | 배치 오케스트레이터. CLI 파싱, 모드 분기, 파이프라인 실행 | - |
| **EmbeddingService** | BGE-M3 모델 로딩 및 embed_batch() 호출 | 내부 모듈 import |
| **Elasticsearch** | 청크 조회(scroll API), 임베딩 저장(bulk update) | `ELASTICSEARCH_URL` (기본: `http://elasticsearch:9200`) |
| **PostgreSQL** | 문서 상태(processing_status) 및 동기화 플래그(es_synced) 갱신 | `PG_DSN` (기본: `postgresql://...`) |
| **Redis** | 임베딩 벡터 캐시 (cache_enabled=False 권장) | `REDIS_URL` |
| **파일 시스템** | 체크포인트 JSON, 결과 JSON 저장 | `/app/data/checkpoints/`, `/app/data/results/` |

### 2.2 네트워크 토폴로지

```
kp-ai-service (172.20.0.x)
  ├── → kp-elasticsearch:9200  (ES scroll/bulk)
  ├── → kp-postgres:5432       (asyncpg)
  └── → kp-redis:6379          (선택, 캐시)
```

모든 통신은 Docker 내부 네트워크(`kp-network`)를 통해 이루어지며, 외부 노출 없이 동작합니다.

---

## 3. Full Cycle 파이프라인

### 3.1 전체 흐름

```mermaid
flowchart LR
    subgraph Phase1["Phase 1: 초기화"]
        A["CLI 파싱<br/>argparse"] --> B{"--stop-service?"}
        B -->|Yes| C["uvicorn 중지<br/>pkill -f uvicorn"]
        B -->|No| D["메모리 확인<br/>psutil"]
        C --> D
    end

    subgraph Phase2["Phase 2: 모델 로딩"]
        D --> E["EmbeddingService<br/>초기화"]
        E --> F["BGE-M3 모델<br/>Lazy Loading"]
        F --> G["모델 로드 확인<br/>(~2GB)"]
    end

    subgraph Phase3["Phase 3: ES 스캔 & 임베딩"]
        G --> H{"--resume?"}
        H -->|Yes| I["체크포인트 로드<br/>processed_ids 복원"]
        H -->|No| J["ES 쿼리 생성<br/>(mode 기반)"]
        I --> J
        J --> K["ES scroll 시작<br/>(5m timeout)"]
        K --> L["배치 임베딩<br/>embed_batch()"]
        L --> M["ES bulk update<br/>dense_vector 저장"]
        M --> N{"100배치마다"}
        N -->|Yes| O["체크포인트 저장<br/>checkpoint_*.json"]
        N -->|No| P{"다음 scroll?"}
        O --> P
        P -->|Yes| L
        P -->|No| Q["scroll 정리"]
    end

    subgraph Phase4["Phase 4: PG 동기화"]
        Q --> R["PG 상태 갱신<br/>processing_status<br/>es_synced = TRUE"]
    end

    subgraph Phase5["Phase 5: 완료"]
        R --> S["결과 JSON 저장<br/>result_*.json"]
        S --> T{"--stop-service?"}
        T -->|Yes| U["uvicorn 재시작"]
        T -->|No| V["결과 출력"]
        U --> V
    end

    style A fill:#9C27B0,color:#fff
    style F fill:#FF9800,color:#fff
    style L fill:#4CAF50,color:#fff
    style M fill:#2196F3,color:#fff
    style R fill:#3F51B5,color:#fff
    style V fill:#4CAF50,color:#fff
```

### 3.2 단계별 상세

#### Phase 1: 초기화

1. `argparse`로 CLI 인자를 파싱합니다.
2. `--stop-service` 옵션이 있으면 `pkill -f uvicorn`으로 웹 프로세스를 중지합니다.
3. `psutil.virtual_memory()`로 현재 메모리 사용량을 확인합니다.
4. 메모리 사용률이 80% 초과이면 경고를 출력하고 사용자 확인을 요청합니다.

```python
def _stop_web_service(self) -> None:
    """uvicorn 웹 프로세스 중지 (OOM 방지)"""
    import subprocess
    result = subprocess.run(
        ["pkill", "-f", "uvicorn"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        logger.info("uvicorn 프로세스 중지 완료")
        time.sleep(2)  # 프로세스 종료 대기
    else:
        logger.warning("uvicorn 프로세스 미발견 또는 이미 중지")
```

#### Phase 2: 모델 로딩

1. `EmbeddingService(cache_enabled=False)`로 인스턴스를 생성합니다 (배치에서는 캐시 불필요).
2. `embedding_svc.model` 프로퍼티 접근으로 BGE-M3 모델을 Lazy Loading합니다.
3. FlagEmbedding -> sentence-transformers 폴백 순서로 로딩을 시도합니다.
4. 로딩 소요 시간과 메모리 변화를 로깅합니다.

#### Phase 3: ES 스캔 & 임베딩

1. `--mode`에 따라 ES 쿼리를 동적으로 생성합니다 (Section 4 참조).
2. ES scroll API (`scroll=5m`, `size=scroll_size`)로 청크를 분할 조회합니다.
3. 각 scroll 페이지를 `batch_size` 단위로 잘라 `embed_batch()`를 호출합니다.
4. 생성된 벡터를 ES bulk update로 `dense_vector` 필드에 저장합니다.
5. `--resume` 시 checkpoint의 `processed_ids`에 포함된 chunk는 건너뜁니다.
6. 100배치(=`batch_size * 100` chunks) 처리마다 체크포인트를 저장합니다.

#### Phase 4: PG 동기화

1. 처리된 chunk들을 `document_id` 기준으로 그룹핑합니다.
2. 각 문서에 대해 다음 PG 업데이트를 수행합니다:

```sql
UPDATE documents
SET processing_status = 'completed',  -- 또는 'failed'
    es_synced = TRUE,
    es_synced_at = NOW(),
    updated_at = NOW()
WHERE id = $1
```

3. 문서 내 일부 chunk만 실패한 경우 `processing_status = 'partial'`로 설정합니다.

#### Phase 5: 완료

1. `EmbeddingBatchSummary`를 JSON 파일로 저장합니다.
2. `--stop-service`였다면 `uvicorn`을 재시작합니다.
3. 콘솔에 최종 결과 요약을 출력합니다.

---

## 4. 실행 모드 설계

### 4.1 모드 분기 다이어그램

```mermaid
flowchart TB
    Start["CLI 실행"] --> Mode{"--mode 파라미터"}

    Mode -->|"all"| AllQuery["ES 쿼리: all 모드"]
    Mode -->|"document"| DocQuery["ES 쿼리: document 모드"]
    Mode -->|"file"| FileQuery["ES 쿼리: file 모드"]
    Mode -->|"reprocess"| ReQuery["ES 쿼리: reprocess 모드"]

    AllQuery --> AllForce{"--force?"}
    AllForce -->|No| AllQ1["bool.must_not:<br/>exists(dense_vector)"]
    AllForce -->|Yes| AllQ2["match_all<br/>(전체 재처리)"]

    DocQuery --> DocForce{"--force?"}
    DocForce -->|No| DocQ1["bool.must:<br/>term(document_id=X)<br/>bool.must_not:<br/>exists(dense_vector)"]
    DocForce -->|Yes| DocQ2["bool.must:<br/>term(document_id=X)<br/>(임베딩 유무 무관)"]

    FileQuery --> FileForce{"--force?"}
    FileForce -->|No| FileQ1["bool.must:<br/>term(metadata.source=X)<br/>bool.must_not:<br/>exists(dense_vector)"]
    FileForce -->|Yes| FileQ2["bool.must:<br/>term(metadata.source=X)<br/>(임베딩 유무 무관)"]

    ReQuery --> ReForce{"--force?"}
    ReForce -->|No| ReQ1["bool.must:<br/>range(created_at >= since)<br/>bool.must_not:<br/>exists(dense_vector)"]
    ReForce -->|Yes| ReQ2["bool.must:<br/>range(created_at >= since)<br/>(임베딩 유무 무관)"]

    AllQ1 --> Scroll["ES Scroll API<br/>실행"]
    AllQ2 --> Scroll
    DocQ1 --> Scroll
    DocQ2 --> Scroll
    FileQ1 --> Scroll
    FileQ2 --> Scroll
    ReQ1 --> Scroll
    ReQ2 --> Scroll

    style Start fill:#9C27B0,color:#fff
    style Scroll fill:#4CAF50,color:#fff
    style AllQ1 fill:#2196F3,color:#fff
    style DocQ1 fill:#2196F3,color:#fff
    style FileQ1 fill:#2196F3,color:#fff
    style ReQ1 fill:#2196F3,color:#fff
    style AllQ2 fill:#FF5722,color:#fff
    style DocQ2 fill:#FF5722,color:#fff
    style FileQ2 fill:#FF5722,color:#fff
    style ReQ2 fill:#FF5722,color:#fff
```

### 4.2 모드별 상세

| 모드 | 필수 인자 | ES 쿼리 | 용도 |
|------|-----------|---------|------|
| `all` | 없음 | `must_not: exists(dense_vector)` | 임베딩 미처리 전체 청크 일괄 처리 |
| `document` | `--doc-id UUID` | `term(document_id=UUID) + must_not exists` | 특정 문서의 미처리 청크만 처리 |
| `file` | `--file-name "파일명"` | `term(metadata.source="파일명") + must_not exists` | 특정 파일명의 미처리 청크만 처리 |
| `reprocess` | `--since YYYY-MM-DD` | `range(created_at >= since) + must_not exists` | 특정 시점 이후 인덱싱된 청크 처리 |

### 4.3 `--force` 플래그

`--force`가 활성화되면 각 모드의 ES 쿼리에서 `must_not: exists(dense_vector)` 조건을 제거합니다. 즉, 이미 임베딩이 있는 청크도 다시 처리합니다.

**사용 시나리오**:
- 모델 버전 교체 후 전체 재임베딩
- 벡터 차원 변경 후 일괄 재생성
- 정규화 설정 변경 후 재처리

### 4.4 쿼리 생성 구현

```python
def _build_es_query(
    self,
    mode: str,
    doc_id: Optional[str] = None,
    file_name: Optional[str] = None,
    since: Optional[str] = None,
) -> dict:
    """실행 모드에 따른 ES 쿼리 생성"""
    must_clauses = []
    must_not_clauses = []

    # --force 미사용 시: 임베딩 없는 것만
    if not self.force:
        must_not_clauses.append({"exists": {"field": "dense_vector"}})

    # 모드별 필터
    if mode == "document" and doc_id:
        must_clauses.append({"term": {"document_id": doc_id}})
    elif mode == "file" and file_name:
        must_clauses.append({"term": {"metadata.source": file_name}})
    elif mode == "reprocess" and since:
        must_clauses.append({"range": {"created_at": {"gte": since}}})
    # mode == "all": 추가 필터 없음

    query = {"bool": {}}
    if must_clauses:
        query["bool"]["must"] = must_clauses
    if must_not_clauses:
        query["bool"]["must_not"] = must_not_clauses
    if not must_clauses and not must_not_clauses:
        query = {"match_all": {}}

    return query
```

---

## 5. 데이터 모델

### 5.1 Elasticsearch 스키마 (knowledge_chunks)

배치 프로그램이 읽고 쓰는 ES 필드:

| 필드 | 타입 | 읽기/쓰기 | 설명 |
|------|------|-----------|------|
| `_id` | keyword | R | ES 문서 고유 ID |
| `chunk_id` | keyword | R | 청크 식별자 |
| `document_id` | keyword | R | 소속 문서 UUID |
| `text` | text | R | 청크 텍스트 (임베딩 입력) |
| `dense_vector` | dense_vector (1024d, cosine) | **W** | BGE-M3 임베딩 벡터 |
| `metadata.source` | keyword | R | 원본 파일명 |
| `created_at` | date | R | 인덱싱 시각 |

### 5.2 PostgreSQL 스키마 (documents)

배치 프로그램이 갱신하는 PG 컬럼:

| 컬럼 | 타입 | 기본값 | 배치 갱신 값 |
|------|------|--------|-------------|
| `processing_status` | VARCHAR(30) | 'pending' | 'embedding' -> 'completed' / 'failed' |
| `processing_error` | TEXT | NULL | 에러 메시지 (실패 시) |
| `es_synced` | BOOLEAN | false | **TRUE** |
| `es_synced_at` | TIMESTAMP | NULL | **NOW()** |
| `updated_at` | TIMESTAMP | CURRENT_TIMESTAMP | **NOW()** (트리거 자동) |

### 5.3 문서 상태 전이

```mermaid
stateDiagram-v2
    [*] --> uploaded : 문서 업로드
    uploaded --> queued : 처리 대기열 등록
    queued --> processing : 파이프라인 시작
    processing --> parsing : 문서 파싱
    parsing --> chunking : 텍스트 분할
    chunking --> embedding : 임베딩 생성
    embedding --> storing : ES/PG 저장
    storing --> completed : 전체 성공
    storing --> failed : 저장 실패

    embedding --> failed : 임베딩 실패

    state embedding {
        [*] --> batch_start : 배치 시작
        batch_start --> es_scroll : ES scroll 조회
        es_scroll --> embed_batch : embed_batch() 호출
        embed_batch --> es_update : ES bulk update
        es_update --> pg_sync : PG 동기화
        pg_sync --> batch_check : 다음 배치 확인
        batch_check --> es_scroll : 계속
        batch_check --> [*] : 완료
    }

    note right of embedding
        embedding_full_cycle.py가
        관여하는 핵심 상태.
        배치 시작 시 'embedding'으로 전이,
        완료 시 'completed'로 전이.
    end note

    note right of failed
        processing_error에
        실패 원인 기록.
        --resume로 재시도 가능.
    end note
```

### 5.4 PG 갱신 로직

```python
async def _update_pg_documents(
    self, doc_results: Dict[str, DocumentResult]
) -> None:
    """문서별 PG 상태 갱신"""
    conn = await asyncpg.connect(self.pg_dsn)
    try:
        for doc_id, result in doc_results.items():
            if result.failed == 0:
                status = "completed"
                error_msg = None
            elif result.processed > 0:
                status = "completed"  # 일부 성공도 completed 처리
                error_msg = f"{result.failed} chunks failed"
            else:
                status = "failed"
                error_msg = result.error_message

            await conn.execute(
                """
                UPDATE documents
                SET processing_status = $2,
                    processing_error = $3,
                    es_synced = TRUE,
                    es_synced_at = NOW(),
                    updated_at = NOW()
                WHERE id = $1::uuid
                """,
                doc_id, status, error_msg,
            )
    finally:
        await conn.close()
```

---

## 6. 클래스 설계

### 6.1 클래스 다이어그램

```mermaid
classDiagram
    class EmbeddingFullCycle {
        -str es_url
        -str pg_dsn
        -int batch_size
        -int scroll_size
        -bool dry_run
        -bool force
        -bool stop_service
        -EmbeddingService embedding_svc
        -AsyncElasticsearch es_client
        +__init__(es_url, pg_dsn, batch_size, dry_run, force, stop_service)
        +run(mode, doc_id, file_name, since, resume_path) EmbeddingBatchSummary
        -_build_es_query(mode, doc_id, file_name, since) dict
        -_process_scroll_page(hits, checkpoint) tuple
        -_embed_and_update_batch(chunks) tuple
        -_update_pg_documents(doc_results) None
        -_save_checkpoint(checkpoint) str
        -_load_checkpoint(path) Checkpoint
        -_stop_web_service() None
        -_start_web_service() None
        -_check_memory() float
        -_maybe_pause_for_memory() None
    }

    class EmbeddingBatchSummary {
        +str started_at
        +str completed_at
        +str mode
        +int total_chunks
        +int processed
        +int skipped
        +int failed
        +Dict~str,DocumentResult~ per_document
        +float elapsed_seconds
        +to_dict() dict
        +save_json(path) None
    }

    class Checkpoint {
        +str scroll_id
        +Set~str~ processed_ids
        +int total_processed
        +int total_skipped
        +int total_failed
        +Dict~str,dict~ per_document
        +str created_at
        +to_dict() dict
        +from_dict(data) Checkpoint$
    }

    class DocumentResult {
        +str document_id
        +str file_name
        +int total_chunks
        +int processed
        +int skipped
        +int failed
        +str status
        +str error_message
    }

    class EmbeddingService {
        +str model_name
        +int batch_size
        +int max_length
        +str device
        +bool normalize
        +embed_batch(texts, return_sparse) List
        +embed_chunks(chunk_ids, texts) List~ChunkEmbedding~
        +health_check() dict
    }

    EmbeddingFullCycle --> EmbeddingService : 사용
    EmbeddingFullCycle --> EmbeddingBatchSummary : 생성
    EmbeddingFullCycle --> Checkpoint : 저장/로드
    EmbeddingBatchSummary --> DocumentResult : 포함 (1..*)
    Checkpoint --> DocumentResult : 참조
```

### 6.2 주요 클래스 상세

#### EmbeddingFullCycle

배치 프로세스의 핵심 오케스트레이터입니다. 생성자에서 설정을 받아 `run()` 메서드로 전체 파이프라인을 실행합니다.

```python
@dataclass
class EmbeddingFullCycle:
    es_url: str = "http://elasticsearch:9200"
    pg_dsn: str = "postgresql://..."
    batch_size: int = 16
    scroll_size: int = 200
    dry_run: bool = False
    force: bool = False
    stop_service: bool = False
```

**주요 메서드**:

| 메서드 | 반환 | 설명 |
|--------|------|------|
| `run()` | `EmbeddingBatchSummary` | 전체 파이프라인 실행 (async) |
| `_build_es_query()` | `dict` | 모드별 ES 쿼리 생성 |
| `_process_scroll_page()` | `(processed, skipped, failed)` | scroll 페이지 처리 |
| `_embed_and_update_batch()` | `(success, failed)` | 단일 배치 임베딩 + ES 업데이트 |
| `_update_pg_documents()` | `None` | PG 상태 일괄 갱신 |
| `_save_checkpoint()` | `str` (파일 경로) | 체크포인트 JSON 저장 |
| `_load_checkpoint()` | `Checkpoint` | 체크포인트 복원 |
| `_check_memory()` | `float` (사용률 %) | 메모리 사용률 확인 |
| `_maybe_pause_for_memory()` | `None` | 85% 초과 시 GC + sleep |

#### EmbeddingBatchSummary

배치 실행 결과를 담는 불변(immutable) 데이터 클래스입니다.

```python
@dataclass
class EmbeddingBatchSummary:
    started_at: str          # ISO 8601
    completed_at: str        # ISO 8601
    mode: str                # all, document, file, reprocess
    total_chunks: int        # 대상 청크 수
    processed: int           # 성공 처리 수
    skipped: int             # 건너뛴 수 (resume 시)
    failed: int              # 실패 수
    per_document: Dict[str, DocumentResult]  # 문서별 결과
    elapsed_seconds: float   # 총 소요 시간
```

#### Checkpoint

중간 진행 상태를 직렬화하는 데이터 클래스입니다. JSON 파일로 저장/로드됩니다.

```python
@dataclass
class Checkpoint:
    scroll_id: str                    # ES scroll cursor
    processed_ids: Set[str]           # 처리 완료된 ES _id 집합
    total_processed: int
    total_skipped: int
    total_failed: int
    per_document: Dict[str, dict]     # 문서별 중간 결과
    created_at: str                   # ISO 8601
```

#### DocumentResult

개별 문서에 대한 처리 결과입니다.

```python
@dataclass
class DocumentResult:
    document_id: str
    file_name: str
    total_chunks: int
    processed: int
    skipped: int
    failed: int
    status: str          # "completed", "failed", "partial"
    error_message: Optional[str] = None
```

---

## 7. OOM 방지 전략

### 7.1 문제 분석

WSL 12GB 환경에서의 메모리 분포:

| 프로세스 | 메모리 | 비고 |
|----------|--------|------|
| WSL 커널 + 시스템 | ~1.5GB | 고정 |
| Docker 데몬 | ~0.5GB | 고정 |
| Elasticsearch | ~2GB | JVM Heap (Xmx=1g) + off-heap |
| PostgreSQL | ~0.5GB | shared_buffers |
| Neo4j | ~1GB | heap + page cache |
| Redis | ~0.2GB | maxmemory |
| AI Service (uvicorn) | **~3GB** | FastAPI + 라이브러리 |
| BGE-M3 모델 | **~2GB** | FP32 가중치 |
| **합계** | **~10.7GB** | 여유 ~1.3GB |

uvicorn과 BGE-M3가 동시에 실행되면 메모리 합계가 12GB에 근접하여 OOM Kill이 발생합니다.

### 7.2 방지 시퀀스

```mermaid
sequenceDiagram
    participant User as 운영자
    participant CLI as embedding_full_cycle.py
    participant Uvicorn as uvicorn 프로세스<br/>(~3GB)
    participant BGE as EmbeddingService<br/>(BGE-M3 ~2GB)
    participant ES as Elasticsearch
    participant PG as PostgreSQL
    participant Mem as psutil<br/>메모리 모니터

    User->>CLI: python embedding_full_cycle.py<br/>--mode all --stop-service

    Note over CLI: Phase 1 - 서비스 중지
    CLI->>Mem: virtual_memory() 확인
    Mem-->>CLI: 사용률 68% (8.2GB/12GB)
    CLI->>Uvicorn: pkill -f uvicorn
    Uvicorn-->>CLI: 프로세스 종료 (~3GB 해제)
    CLI->>Mem: virtual_memory() 재확인
    Mem-->>CLI: 사용률 43% (5.2GB/12GB)

    Note over CLI: Phase 2 - 모델 로딩
    CLI->>BGE: EmbeddingService(cache_enabled=False)
    BGE->>BGE: model 프로퍼티 접근<br/>(Lazy Loading)
    BGE-->>CLI: 모델 로드 완료 (~2GB 사용)
    CLI->>Mem: virtual_memory() 확인
    Mem-->>CLI: 사용률 60% (7.2GB/12GB)

    Note over CLI: Phase 3 - 배치 처리
    loop 각 scroll 페이지
        CLI->>ES: scroll API (size=200)
        ES-->>CLI: 200 chunks

        loop 각 batch (size=16)
            CLI->>BGE: embed_batch(texts[16])
            BGE-->>CLI: dense_vectors[16]
            CLI->>ES: bulk update (16 docs)
            ES-->>CLI: OK

            CLI->>Mem: check_memory()
            alt 사용률 > 85%
                CLI->>CLI: gc.collect()
                CLI->>CLI: time.sleep(30)
                CLI->>Mem: 재확인
            end
        end
    end

    Note over CLI: Phase 4 - PG 동기화
    CLI->>PG: UPDATE documents<br/>SET processing_status='completed',<br/>es_synced=TRUE, es_synced_at=NOW()
    PG-->>CLI: OK

    Note over CLI: Phase 5 - 서비스 복원
    CLI->>Uvicorn: uvicorn app.main:app 재시작
    Uvicorn-->>CLI: 웹 서비스 복원
    CLI->>User: 완료 (result_*.json)
```

### 7.3 방지 기법 요약

| 기법 | 구현 | 효과 |
|------|------|------|
| **서비스 중지** | `--stop-service` -> `pkill -f uvicorn` | ~3GB 해제 |
| **캐시 비활성** | `EmbeddingService(cache_enabled=False)` | Redis 통신 오버헤드 제거 |
| **소형 배치** | `--batch-size 16` (기본값) | 피크 메모리 최소화 |
| **GC 강제 수행** | `gc.collect()` per batch | 가비지 즉시 수거 |
| **메모리 모니터링** | `psutil.virtual_memory().percent` | 실시간 추적 |
| **자동 일시정지** | 85% 초과 시 GC + sleep(30) | OOM 직전 브레이크 |
| **scroll 정리** | `clear_scroll()` 호출 | ES 메모리 해제 |

### 7.4 메모리 모니터링 구현

```python
import gc
import psutil

MEMORY_THRESHOLD = 85.0  # 퍼센트
MEMORY_PAUSE_SECONDS = 30

def _check_memory(self) -> float:
    """현재 메모리 사용률(%) 반환"""
    return psutil.virtual_memory().percent

def _maybe_pause_for_memory(self) -> None:
    """메모리 사용률이 임계값 초과 시 GC + sleep"""
    mem_pct = self._check_memory()
    if mem_pct > MEMORY_THRESHOLD:
        logger.warning(
            "메모리 사용률 %.1f%% (임계값 %.1f%%) - GC 수행 후 %ds 대기",
            mem_pct, MEMORY_THRESHOLD, MEMORY_PAUSE_SECONDS
        )
        gc.collect()
        time.sleep(MEMORY_PAUSE_SECONDS)

        mem_after = self._check_memory()
        logger.info("GC 후 메모리 사용률: %.1f%%", mem_after)
        if mem_after > MEMORY_THRESHOLD:
            logger.error(
                "GC 후에도 메모리 사용률 %.1f%% - 배치 크기 축소 필요",
                mem_after
            )
```

---

## 8. 체크포인트/재개 메커니즘

### 8.1 체크포인트 흐름

```mermaid
flowchart TB
    subgraph NormalExec["정상 실행"]
        A["배치 시작"] --> B["scroll 페이지 처리"]
        B --> C{"batch_count<br/>% 100 == 0?"}
        C -->|No| D["다음 배치"]
        C -->|Yes| E["체크포인트 저장<br/>checkpoint_YYYYMMDD_HHMMSS.json"]
        E --> D
        D --> F{"scroll 완료?"}
        F -->|No| B
        F -->|Yes| G["결과 저장<br/>result_YYYYMMDD_HHMMSS.json"]
    end

    subgraph Interruption["중단 감지"]
        H["OOM Kill / Ctrl+C /<br/>네트워크 장애"] --> I["프로세스 종료"]
        I --> J["마지막 체크포인트<br/>파일 잔존"]
    end

    subgraph Resume["--resume 재개"]
        K["CLI: --resume<br/>checkpoint_*.json"] --> L["체크포인트 로드"]
        L --> M["processed_ids<br/>Set 복원"]
        M --> N["새 ES scroll 시작<br/>(동일 쿼리)"]
        N --> O["각 chunk 확인"]
        O --> P{"_id in<br/>processed_ids?"}
        P -->|Yes| Q["건너뜀<br/>(skipped++)"]
        P -->|No| R["임베딩 처리"]
        Q --> S["다음 chunk"]
        R --> S
        S --> T{"scroll 완료?"}
        T -->|No| O
        T -->|Yes| U["결과 저장<br/>(누적 통계)"]
    end

    G -.->|"정상 종료"| V["완료"]
    J -.->|"수동 재개"| K
    U --> V

    style A fill:#4CAF50,color:#fff
    style E fill:#FF9800,color:#fff
    style H fill:#f44336,color:#fff
    style K fill:#9C27B0,color:#fff
    style V fill:#4CAF50,color:#fff
```

### 8.2 체크포인트 JSON 스키마

```json
{
  "version": "1.0",
  "scroll_id": "FGluY2x1ZGVf...",
  "processed_ids": [
    "es_doc_id_001",
    "es_doc_id_002",
    "..."
  ],
  "total_processed": 3200,
  "total_skipped": 12,
  "total_failed": 3,
  "per_document": {
    "550e8400-e29b-41d4-a716-446655440000": {
      "file_name": "시스템_운영매뉴얼.pdf",
      "processed": 45,
      "skipped": 0,
      "failed": 1
    }
  },
  "mode": "all",
  "batch_size": 16,
  "created_at": "2026-02-09T14:30:00+09:00"
}
```

### 8.3 재개 로직

`--resume` 재개 시 기존 ES scroll ID는 만료(5분)되었으므로 새 scroll을 시작합니다. 대신 `processed_ids` Set를 메모리에 로드하여, 이미 처리된 chunk를 건너뜁니다.

```python
async def _load_checkpoint(self, path: str) -> Checkpoint:
    """체크포인트 파일 로드"""
    with open(path, "r") as f:
        data = json.load(f)
    return Checkpoint(
        scroll_id="",  # 만료됨, 새 scroll 사용
        processed_ids=set(data["processed_ids"]),
        total_processed=data["total_processed"],
        total_skipped=data["total_skipped"],
        total_failed=data["total_failed"],
        per_document=data["per_document"],
        created_at=data["created_at"],
    )

async def _process_scroll_page(
    self, hits: list, checkpoint: Optional[Checkpoint]
) -> tuple:
    """scroll 페이지 내 각 chunk를 배치 단위로 처리"""
    processed = skipped = failed = 0

    for batch_start in range(0, len(hits), self.batch_size):
        batch_hits = hits[batch_start:batch_start + self.batch_size]
        chunks_to_embed = []

        for hit in batch_hits:
            es_id = hit["_id"]
            # 체크포인트에 이미 처리된 ID면 건너뜀
            if checkpoint and es_id in checkpoint.processed_ids:
                skipped += 1
                continue
            chunks_to_embed.append(hit)

        if chunks_to_embed:
            ok, fail = await self._embed_and_update_batch(chunks_to_embed)
            processed += ok
            failed += fail

        self._maybe_pause_for_memory()

    return processed, skipped, failed
```

### 8.4 체크포인트 저장 주기

| 항목 | 값 | 근거 |
|------|------|------|
| 저장 주기 | 100 배치 | batch_size=16 x 100 = 1,600 chunks |
| 저장 위치 | `/app/data/checkpoints/` | 컨테이너 내부 (볼륨 마운트 권장) |
| 파일명 패턴 | `checkpoint_YYYYMMDD_HHMMSS.json` | 시각 기반 고유명 |
| processed_ids 크기 | ~10K entries (약 500KB) | 9,818 미처리 기준 |
| 저장 소요 시간 | < 100ms | JSON 직렬화 + 파일 쓰기 |

---

## 9. 작업 이력

### 9.1 결과 JSON 스키마

배치 완료 시 자동 저장되는 JSON 파일입니다.

```json
{
  "version": "1.0",
  "summary": {
    "started_at": "2026-02-09T10:00:00+09:00",
    "completed_at": "2026-02-09T11:23:45+09:00",
    "mode": "all",
    "force": false,
    "batch_size": 16,
    "scroll_size": 200,
    "dry_run": false,
    "stop_service": true,
    "total_chunks": 9818,
    "processed": 9805,
    "skipped": 0,
    "failed": 13,
    "elapsed_seconds": 5025.3,
    "rate_chunks_per_sec": 1.95,
    "peak_memory_percent": 72.3
  },
  "per_document": {
    "550e8400-e29b-41d4-a716-446655440000": {
      "document_id": "550e8400-e29b-41d4-a716-446655440000",
      "file_name": "시스템_운영매뉴얼.pdf",
      "total_chunks": 127,
      "processed": 127,
      "skipped": 0,
      "failed": 0,
      "status": "completed",
      "error_message": null
    },
    "660e8400-e29b-41d4-a716-446655440001": {
      "document_id": "660e8400-e29b-41d4-a716-446655440001",
      "file_name": "API_설계서_v3.docx",
      "total_chunks": 85,
      "processed": 82,
      "skipped": 0,
      "failed": 3,
      "status": "completed",
      "error_message": "3 chunks failed: empty text"
    }
  },
  "pg_sync": {
    "updated_documents": 42,
    "failed_updates": 0,
    "sync_duration_seconds": 1.2
  },
  "errors": [
    {
      "es_id": "chunk_abc123",
      "document_id": "660e8400-e29b-41d4-a716-446655440001",
      "error": "Empty text for chunk",
      "timestamp": "2026-02-09T10:45:12+09:00"
    }
  ],
  "environment": {
    "es_url": "http://elasticsearch:9200",
    "es_index": "knowledge_chunks",
    "model_name": "BAAI/bge-m3",
    "model_type": "flag_embedding",
    "device": "cpu",
    "vector_dimension": 1024,
    "total_memory_gb": 12.0,
    "hostname": "kp-ai-service"
  }
}
```

### 9.2 저장 위치 및 명명

| 항목 | 값 |
|------|------|
| 디렉토리 | `/app/data/results/` |
| 파일명 패턴 | `embedding_result_YYYYMMDD_HHMMSS.json` |
| 보존 기간 | 무기한 (수동 정리) |
| 용도 | 감사 추적, 문제 분석, 재실행 판단 |

### 9.3 결과 조회

```bash
# 최신 결과 확인
docker exec kp-ai-service ls -lt /app/data/results/ | head -5

# 특정 결과 조회
docker exec kp-ai-service cat /app/data/results/embedding_result_20260209_102300.json | python3 -m json.tool

# 실패 청크만 추출
docker exec kp-ai-service python3 -c "
import json
with open('/app/data/results/embedding_result_20260209_102300.json') as f:
    data = json.load(f)
for err in data['errors']:
    print(f'{err[\"es_id\"]}: {err[\"error\"]}')
"
```

---

## 10. CLI 인터페이스

### 10.1 인자 정의

```
usage: embedding_full_cycle.py [-h]
    --mode {all,document,file,reprocess}
    [--doc-id UUID]
    [--file-name FILENAME]
    [--since YYYY-MM-DD]
    [--batch-size N]
    [--scroll-size N]
    [--dry-run]
    [--force]
    [--resume PATH]
    [--stop-service]
```

| 인자 | 타입 | 기본값 | 필수 | 설명 |
|------|------|--------|------|------|
| `--mode` | choice | - | **필수** | 실행 모드 (all/document/file/reprocess) |
| `--doc-id` | UUID | - | document 모드 시 | 대상 문서 UUID |
| `--file-name` | str | - | file 모드 시 | 대상 파일명 |
| `--since` | date | - | reprocess 모드 시 | 시작 시점 (YYYY-MM-DD) |
| `--batch-size` | int | 16 | - | 한 번에 임베딩할 텍스트 수 |
| `--scroll-size` | int | 200 | - | ES scroll 페이지 크기 |
| `--dry-run` | flag | False | - | 대상 카운트만 수행, 실제 처리 안 함 |
| `--force` | flag | False | - | 기존 임베딩 있어도 재처리 |
| `--resume` | path | - | - | 체크포인트 파일 경로 |
| `--stop-service` | flag | False | - | 배치 전 uvicorn 중지, 완료 후 재시작 |

### 10.2 사용 예시

#### 기본 전체 처리 (임베딩 없는 청크만)

```bash
docker exec kp-ai-service python3 /app/scripts/embedding_full_cycle.py \
    --mode all \
    --batch-size 16 \
    --stop-service
```

#### 특정 문서만 처리

```bash
docker exec kp-ai-service python3 /app/scripts/embedding_full_cycle.py \
    --mode document \
    --doc-id "550e8400-e29b-41d4-a716-446655440000" \
    --batch-size 32
```

#### 특정 파일명으로 처리

```bash
docker exec kp-ai-service python3 /app/scripts/embedding_full_cycle.py \
    --mode file \
    --file-name "시스템_운영매뉴얼.pdf" \
    --batch-size 16
```

#### 특정 시점 이후 재처리

```bash
docker exec kp-ai-service python3 /app/scripts/embedding_full_cycle.py \
    --mode reprocess \
    --since 2026-02-01 \
    --batch-size 16 \
    --stop-service
```

#### 강제 전체 재임베딩 (기존 벡터 덮어쓰기)

```bash
docker exec kp-ai-service python3 /app/scripts/embedding_full_cycle.py \
    --mode all \
    --force \
    --batch-size 8 \
    --stop-service
```

#### Dry-run (카운트만)

```bash
docker exec kp-ai-service python3 /app/scripts/embedding_full_cycle.py \
    --mode all \
    --dry-run
```

**예상 출력**:
```
[CONFIG] mode=all, batch_size=16, dry_run=True
[SCAN] 9,818 chunks without embeddings found
[DRY_RUN] Would process 9,818 chunks. Exiting.
```

#### 체크포인트에서 재개

```bash
docker exec kp-ai-service python3 /app/scripts/embedding_full_cycle.py \
    --mode all \
    --resume /app/data/checkpoints/checkpoint_20260209_103000.json \
    --stop-service
```

### 10.3 환경 변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `ELASTICSEARCH_URL` | `http://elasticsearch:9200` | ES 연결 URL |
| `ELASTICSEARCH_INDEX` | `knowledge_chunks` | ES 인덱스명 |
| `PG_DSN` | `postgresql://postgres:postgres@postgres:5432/knowledge_db` | PG 연결 문자열 |
| `CHECKPOINT_DIR` | `/app/data/checkpoints` | 체크포인트 저장 디렉토리 |
| `RESULT_DIR` | `/app/data/results` | 결과 파일 저장 디렉토리 |

---

## 11. 에러 처리 전략

### 11.1 에러 코드

| 코드 | 이름 | 설명 | 처리 |
|------|------|------|------|
| `E001` | `ES_CONNECTION_ERROR` | ES 연결 실패 | 3회 재시도 후 종료 |
| `E002` | `ES_SCROLL_ERROR` | scroll API 오류 | 현재 scroll 포기, 새 scroll 시작 |
| `E003` | `ES_BULK_ERROR` | bulk update 부분 실패 | 실패 항목만 에러 로그, 계속 진행 |
| `E004` | `EMBEDDING_ERROR` | embed_batch() 실패 | 해당 배치 건너뜀, 계속 진행 |
| `E005` | `PG_CONNECTION_ERROR` | PG 연결 실패 | 3회 재시도 후 경고와 함께 계속 |
| `E006` | `PG_UPDATE_ERROR` | PG UPDATE 실패 | 해당 문서 건너뜀, 에러 로그 |
| `E007` | `MODEL_LOAD_ERROR` | BGE-M3 로드 실패 | 즉시 종료 |
| `E008` | `OOM_WARNING` | 메모리 85% 초과 | GC + sleep(30s) |
| `E009` | `CHECKPOINT_SAVE_ERROR` | 체크포인트 저장 실패 | 경고 후 계속 (데이터 손실 없음) |
| `E010` | `CHECKPOINT_LOAD_ERROR` | 체크포인트 로드 실패 | 즉시 종료 |

### 11.2 재시도 전략

```python
import asyncio
from typing import TypeVar, Callable

T = TypeVar("T")

async def retry_async(
    func: Callable[..., T],
    *args,
    max_retries: int = 3,
    base_delay: float = 1.0,
    backoff_factor: float = 2.0,
    **kwargs,
) -> T:
    """지수 백오프 재시도"""
    last_error = None
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_error = e
            delay = base_delay * (backoff_factor ** attempt)
            logger.warning(
                "재시도 %d/%d (%.1fs 후): %s",
                attempt + 1, max_retries, delay, e
            )
            await asyncio.sleep(delay)
    raise last_error
```

### 11.3 에러별 동작 매트릭스

| 에러 유형 | 배치 중단? | 체크포인트 저장? | PG 갱신? | 결과 JSON? |
|-----------|:----------:|:---------------:|:--------:|:----------:|
| ES 연결 실패 (재시도 초과) | **Yes** | Yes | No | Yes (partial) |
| ES bulk 부분 실패 | No | Yes | Yes (성공분만) | Yes |
| 임베딩 생성 실패 | No | Yes | Yes (성공분만) | Yes |
| PG 연결 실패 | No | Yes | **Skip** | Yes (경고) |
| 모델 로드 실패 | **Yes** | No | No | No |
| OOM 후 미복구 | **Yes** | Yes (마지막) | No | Yes (partial) |
| Ctrl+C (KeyboardInterrupt) | **Yes** | Yes | Yes (처리분만) | Yes (partial) |

### 11.4 로깅 규격

```python
import logging

# 로그 포맷
LOG_FORMAT = (
    "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
)
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 로그 레벨별 용도
# DEBUG : 개별 chunk 처리 상세
# INFO  : 배치 진행률, 단계 시작/완료
# WARNING : 메모리 임계, 빈 텍스트, 재시도
# ERROR : 배치 실패, ES/PG 오류
# CRITICAL : 모델 로드 실패, 복구 불가 오류
```

**로그 출력 예시**:
```
[2026-02-09 10:00:05] [INFO] [batch] 모델 로드 완료: BGE-M3 on cpu (12.3s)
[2026-02-09 10:00:06] [INFO] [batch] 대상 청크: 9,818개 (mode=all, force=False)
[2026-02-09 10:01:23] [INFO] [batch] 진행: 1600/9818 (16.3%) | 성공=1598 실패=2 | 1.8 chunks/s | mem=68.5%
[2026-02-09 10:01:23] [INFO] [batch] 체크포인트 저장: checkpoint_20260209_100123.json
[2026-02-09 10:15:45] [WARNING] [batch] 메모리 사용률 86.2% - GC 수행 후 30s 대기
[2026-02-09 10:16:15] [INFO] [batch] GC 후 메모리 사용률: 71.3%
[2026-02-09 11:23:45] [INFO] [batch] 배치 완료: 9805/9818 성공, 13 실패, 5025.3s
[2026-02-09 11:23:46] [INFO] [batch] PG 동기화: 42 문서 업데이트 (1.2s)
[2026-02-09 11:23:46] [INFO] [batch] 결과 저장: embedding_result_20260209_102300.json
```

---

## 12. 테스트 계획

### 12.1 단계별 테스트

#### Stage 1: Dry-run 검증

**목적**: CLI 파싱, ES 쿼리 생성, 대상 카운트가 정확한지 확인합니다.

```bash
# 전체 미처리 카운트
docker exec kp-ai-service python3 /app/scripts/embedding_full_cycle.py \
    --mode all --dry-run

# 기대 결과: "[SCAN] 9,818 chunks without embeddings found"
```

**검증 항목**:
- [ ] 각 모드에서 ES 쿼리가 올바르게 생성되는지
- [ ] `--force` 플래그에 따른 쿼리 변화 확인
- [ ] `--doc-id`, `--file-name`, `--since` 인자 검증
- [ ] 잘못된 인자 조합 시 에러 메시지 출력

#### Stage 2: 소규모 배치 (10건)

**목적**: 단일 문서에 대해 임베딩 생성 -> ES 업데이트 -> PG 동기화 전체 사이클을 검증합니다.

```bash
# 청크 수가 적은 문서 선택
docker exec kp-ai-service python3 /app/scripts/embedding_full_cycle.py \
    --mode document \
    --doc-id "TARGET_DOC_UUID" \
    --batch-size 4
```

**검증 항목**:
- [ ] ES에 dense_vector 필드가 정상 저장되는지
- [ ] 벡터 차원이 1024인지
- [ ] PG documents.processing_status가 'completed'로 갱신되는지
- [ ] PG documents.es_synced가 TRUE로 변경되는지
- [ ] PG documents.es_synced_at에 시각이 기록되는지
- [ ] 결과 JSON 파일이 정상 생성되는지

**ES 검증 쿼리**:
```bash
curl -s "http://localhost:9200/knowledge_chunks/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {"term": {"document_id": "TARGET_DOC_UUID"}},
    "_source": ["chunk_id", "dense_vector"],
    "size": 1
  }' | python3 -m json.tool
```

#### Stage 3: 체크포인트/재개 테스트

**목적**: 중단 후 재개가 정확히 동작하는지 검증합니다.

```bash
# 1) 소규모 실행 (일부러 batch_size=2, 50개 chunk 문서)
docker exec kp-ai-service python3 /app/scripts/embedding_full_cycle.py \
    --mode document --doc-id "DOC_UUID" --batch-size 2

# 2) 체크포인트 확인
docker exec kp-ai-service ls -la /app/data/checkpoints/

# 3) --resume 재개 (이미 처리된 것은 skip)
docker exec kp-ai-service python3 /app/scripts/embedding_full_cycle.py \
    --mode document --doc-id "DOC_UUID" \
    --resume /app/data/checkpoints/checkpoint_*.json \
    --batch-size 2
```

**검증 항목**:
- [ ] 체크포인트 JSON 파일이 정상 생성되는지
- [ ] 재개 시 processed_ids에 포함된 chunk가 skip되는지
- [ ] skip된 chunk 수가 이전 실행의 processed 수와 일치하는지
- [ ] 최종 결과의 total_processed가 정확한지

#### Stage 4: OOM 방지 테스트

**목적**: 메모리 모니터링과 자동 일시정지가 동작하는지 확인합니다.

```bash
# --stop-service 없이 실행 (메모리 부담 상태)
docker exec kp-ai-service python3 /app/scripts/embedding_full_cycle.py \
    --mode all --batch-size 8

# 로그에서 메모리 모니터링 확인
# [WARNING] 메모리 사용률 86.2% - GC 수행 후 30s 대기
```

**검증 항목**:
- [ ] `psutil.virtual_memory().percent`가 배치마다 로깅되는지
- [ ] 85% 초과 시 GC + sleep 동작하는지
- [ ] `--stop-service` 시 uvicorn 프로세스가 종료되는지
- [ ] 완료 후 uvicorn이 자동 재시작되는지

#### Stage 5: 전체 배치 실행 (9,818건)

**목적**: 실환경 전체 미처리 청크에 대한 Full Cycle을 실행합니다.

```bash
docker exec kp-ai-service python3 /app/scripts/embedding_full_cycle.py \
    --mode all \
    --batch-size 16 \
    --stop-service
```

**검증 항목**:
- [ ] 전체 9,818건 처리 완료 (processed + failed = total)
- [ ] 실패율 1% 미만
- [ ] PG에서 모든 관련 문서의 es_synced = TRUE 확인
- [ ] ES에서 dense_vector 없는 청크 0건 확인
- [ ] 결과 JSON에 모든 문서별 통계 포함
- [ ] 총 소요 시간 기록 (예상: ~80분 @ 2 chunks/s)

**ES 최종 검증**:
```bash
# 임베딩 미처리 청크 수 확인 (0이어야 함)
curl -s "http://localhost:9200/knowledge_chunks/_count" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "must_not": [{"exists": {"field": "dense_vector"}}]
      }
    }
  }'
```

**PG 최종 검증**:
```sql
-- 임베딩 완료된 문서 수 확인
SELECT processing_status, COUNT(*)
FROM documents
WHERE es_synced = TRUE
GROUP BY processing_status;
```

### 12.2 성능 기준

| 항목 | 기준 | 비고 |
|------|------|------|
| 처리 속도 | > 1.5 chunks/s | CPU 환경, batch_size=16 |
| 실패율 | < 1% | 빈 텍스트 제외 |
| 메모리 피크 | < 80% | --stop-service 사용 시 |
| 체크포인트 오버헤드 | < 0.5% | 전체 처리 시간 대비 |
| PG 동기화 시간 | < 5초 | 50개 문서 기준 |

---

## 부록

### A. 기존 스크립트와의 비교

| 항목 | `add_embeddings_batch.py` (기존) | `embedding_full_cycle.py` (신규) |
|------|----------------------------------|----------------------------------|
| ES 임베딩 추가 | O | O |
| PG 상태 갱신 | **X** | O |
| 실행 모드 | all만 | all/document/file/reprocess |
| --force 재처리 | X | O |
| 체크포인트/재개 | **X** | O (100배치마다) |
| OOM 방지 | 수동 batch_size 조절만 | 자동 (GC + sleep + --stop-service) |
| 메모리 모니터링 | cgroup 기반 | psutil 기반 |
| 결과 저장 | 콘솔 출력만 | JSON 파일 자동 저장 |
| Dry-run | O | O |
| 에러 재시도 | X | 지수 백오프 (3회) |

### B. 예상 실행 시간

9,818건 기준 (CPU, batch_size=16):

| 단계 | 소요 시간 | 비고 |
|------|-----------|------|
| 모델 로딩 | ~15초 | FlagEmbedding, CPU |
| 임베딩 생성 | ~82분 | 2 chunks/s, 16개 배치 |
| ES bulk 업데이트 | ~5분 | 614배치 x 0.5s |
| PG 동기화 | ~3초 | ~50 문서 UPDATE |
| 결과 저장 | < 1초 | JSON 직렬화 |
| **합계** | **~88분** | --stop-service 사용 시 |

### C. 볼륨 마운트 권장 설정

`docker-compose.yml`에 다음 볼륨을 추가하여 컨테이너 재시작 시에도 체크포인트/결과가 유지되도록 합니다:

```yaml
services:
  ai-service:
    volumes:
      - ai-data:/app/data    # 체크포인트 + 결과 보존

volumes:
  ai-data:
    driver: local
```
