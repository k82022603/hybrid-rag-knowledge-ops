# ETL Phase 1 최종 결과 보고서

> **Version**: 1.0
> **Date**: 2026-02-15
> **Author**: Claude Opus 4.6 (AI Service Team)
> **Sprint**: Sprint 10
> **Status**: Phase 1 Complete

---

## 1. Executive Summary

ETL Phase 1은 1,786개 원본 문서를 파싱, 시맨틱 청킹, 메타데이터 추출하여 3-Store(PostgreSQL, Elasticsearch, Neo4j)에 적재하는 파이프라인이다. Sprint 10 기간(2026-02-13~15) 동안 v1~v4 + v3(.md 재처리) 총 5회 실행을 거쳐 최종 완료되었다.

### 최종 결과

| 지표 | 값 |
|------|-----|
| 원본 문서 | 1,786개 |
| 성공 적재 | 1,437개 (80.5%) |
| 중복 스킵 | 1,033개 |
| 실패 | 0건 |
| 총 청크 (ES) | 62,489개 |
| 총 청크 (PG) | 56,063개 |
| ES 인덱스 크기 | 132.3 MB |
| 평균 청크/문서 | 39.0 |

---

## 2. 시스템 아키텍처

### 2.1 ETL Phase 1 파이프라인

```mermaid
flowchart TB
    subgraph Input["📁 Input Layer"]
        FS["File System<br/>/knowledge_data/documents/"]
        FS --> Scanner["Directory Scanner<br/>(8 subdirectories)"]
    end

    subgraph Parse["📄 Document Parsing"]
        Scanner --> Docling["Docling Adapter<br/>OCR ON + TableFormerMode.FAST"]
        Docling --> MD["Markdown 변환"]
        Docling --> Meta["메타데이터 추출"]
    end

    subgraph Chunk["✂️ Semantic Chunking"]
        MD --> SC["Semantic Chunker<br/>(Langchain)"]
        SC --> Merge["Small Chunk Merger<br/>(threshold: 100 tokens)"]
        Merge --> QG["Quality Gate<br/>(min 20 tok, max 1500 tok)"]
    end

    subgraph Dedup["🔍 Deduplication"]
        QG --> Hash["SHA-256 Hash Check"]
        Hash -->|New| Store
        Hash -->|Duplicate| Skip["Skip (1,033건)"]
    end

    subgraph Store["💾 3-Store Persistence"]
        direction LR
        PG["PostgreSQL<br/>(SSOT)<br/>1,437 docs"]
        ES["Elasticsearch<br/>(Vector Index)<br/>62,489 chunks"]
        Neo4j["Neo4j<br/>(Knowledge Graph)<br/>Nodes + Relations"]
    end

    style Input fill:#e3f2fd,stroke:#1565c0
    style Parse fill:#fff3e0,stroke:#e65100
    style Chunk fill:#e8f5e9,stroke:#2e7d32
    style Dedup fill:#fce4ec,stroke:#c62828
    style Store fill:#f3e5f5,stroke:#6a1b9a
```

### 2.2 데이터 흐름 상세

```mermaid
flowchart LR
    subgraph Phase1["Phase 1: Parsing + Chunking"]
        A["1,786 Files"] --> B["Docling Parser<br/>OCR + Table"]
        B --> C["Semantic Chunker"]
        C --> D["Quality Gate"]
        D --> E["3-Store Write"]
    end

    subgraph Phase2["Phase 2: Embedding (GPU)"]
        E --> F["Dense Embedding<br/>BGE-M3 (1024d)"]
        E --> G["Sparse Embedding<br/>BGE-M3 (lexical)"]
        F --> H["ES kNN Index"]
        G --> I["ES Sparse Field"]
    end

    subgraph Phase3["Phase 3: Entity Extraction"]
        E --> J["Gleaning<br/>(DeepSeek V3.2)"]
        J --> K["Neo4j Graph<br/>Entity + Relation"]
    end

    subgraph Phase4["Phase 4: Search Integration"]
        H --> L["4-Way RRF"]
        I --> L
        M["BM25 + Nori"] --> L
        K --> L
    end

    style Phase1 fill:#e8f5e9,stroke:#2e7d32
    style Phase2 fill:#fff3e0,stroke:#e65100
    style Phase3 fill:#e3f2fd,stroke:#1565c0
    style Phase4 fill:#f3e5f5,stroke:#6a1b9a
```

---

## 3. 실행 이력

### 3.1 버전 타임라인

```mermaid
gantt
    title ETL Phase 1 실행 이력
    dateFormat YYYY-MM-DD HH:mm
    axisFormat %m/%d %H:%M

    section v1
    OOM Kill 종료           :crit, v1, 2026-02-13 14:00, 2026-02-13 18:00

    section v2
    속도 최적화 (OCR OFF)   :active, v2, 2026-02-13 20:00, 2026-02-14 02:00

    section v3
    OCR OFF 품질 불량       :crit, v3, 2026-02-14 02:00, 2026-02-14 06:00

    section v4
    OCR ON 최종 실행        :done, v4, 2026-02-14 19:46, 2026-02-15 07:52

    section v3-md
    .md Chunker v3 재처리   :done, v3md, 2026-02-15 07:55, 2026-02-15 09:49
```

### 3.2 버전별 상세

| 버전 | 기간 | 주요 변경 | 결과 | 종료 원인 |
|------|------|----------|------|-----------|
| **v1** | 02-13 14:00~18:00 | 초기 실행 | OOM Kill | 메모리 제한 미설정 |
| **v2** | 02-13 20:00~02-14 02:00 | P0/P1 버그 수정 | 153시간 예상 | 속도 문제 |
| **v3** | 02-14 02:00~06:00 | OCR OFF + 속도 최적화 | 58x 가속 | 58.2% 저품질 청크 |
| **v4** | 02-14 19:46~02-15 07:52 | OCR ON + Fast Table + 10GB | **1,437 docs 완주** | 정상 완료 |
| **v3-md** | 02-15 07:55~09:49 | Chunker v3 (threshold 100) | **.md 품질 개선** | 정상 완료 |

---

## 4. 문서 분석

### 4.1 파일 유형별 분포

```mermaid
pie title 문서 유형별 분포 (1,437건)
    "Markdown (.md)" : 701
    "PDF (.pdf)" : 299
    "PowerPoint (.pptx)" : 234
    "Word (.docx)" : 130
    "Text (.txt)" : 58
    "Other (.html)" : 15
```

### 4.2 파일 유형별 청크 통계

| File Type | 문서 수 | ES 청크 | PG 청크 | 평균 청크/문서 | 평균 토큰/청크 |
|-----------|--------:|--------:|--------:|---------------:|---------------:|
| **md** | 701 | 23,342 | 28,161 | 40.2 | 97.6 |
| **pdf** | 299 | 13,047 | 14,990 | 50.1 | 128.7 |
| **docx** | 130 | 4,407 | 6,653 | 51.2 | 134.9 |
| **pptx** | 234 | 1,751 | 3,145 | 13.4 | 108.9 |
| **txt** | 58 | 2,652 | 2,944 | 50.8 | 231.4 |
| **html** | 15 | 170 | 170 | 11.3 | 270.5 |
| **합계** | **1,437** | **62,489** | **56,063** | **39.0** | **115.0** |

### 4.3 Top 10 대용량 문서

| 순위 | 문서명 | 청크 수 | 평균 토큰 | 유형 |
|------|--------|--------:|----------:|------|
| 1 | holmes_script.txt | 2,601 | 229 | txt |
| 2 | Pearson.Agile.Software.Development.pdf | 1,868 | 131 | pdf |
| 3 | Nike-NPS-Combo_Form-10-K.pdf | 561 | 155 | pdf |
| 4 | 소프트웨어SW-개발방법론_특허청.pdf | 561 | 92 | pdf |
| 5 | 도커기본1.docx | 471 | 153 | docx |
| 6 | Software Development A Practical Approach.pdf | 385 | 152 | pdf |
| 7 | claude-code-antigravity-tailwind-완벽가이드-v2.md | 318 | 96 | md |
| 8 | claude-code-antigravity-tailwind-완벽가이드-v2_1.md | 313 | 97 | md |
| 9 | 사회보장정보원 SW개발방법론.pdf | 312 | 95 | pdf |
| 10 | AI_코딩_도구_통합_개발자_매뉴얼_4.md | 309 | 67 | md |

---

## 5. 청크 품질 분석

### 5.1 토큰 분포 (전체)

```mermaid
xychart-beta
    title "청크 토큰 분포 (62,489건)"
    x-axis ["0-19", "20-49", "50-99", "100-199", "200-499", "500+"]
    y-axis "청크 수" 0 --> 20000
    bar [3077, 13146, 15880, 19794, 10496, 96]
```

| 토큰 범위 | 청크 수 | 비율 | 판정 |
|-----------|--------:|-----:|------|
| 0-19 | 3,077 | 4.9% | Junk (너무 짧음) |
| 20-49 | 13,146 | 21.0% | Short (정보 부족) |
| 50-99 | 15,880 | 25.4% | Borderline |
| **100-199** | **19,794** | **31.7%** | **Optimal** |
| 200-499 | 10,496 | 16.8% | Good |
| 500+ | 96 | 0.2% | Long (적정) |

- **적정 범위 (100-499)**: 30,290건 (48.5%)
- **<100토큰**: 32,103건 (51.4%)

### 5.2 .md 청크 품질 개선 (Chunker v2 → v3)

```mermaid
xychart-beta
    title ".md 청크 토큰 분포 비교"
    x-axis ["0-19", "20-49", "50-99", "100-199", "200-499", "500+"]
    y-axis "비율 (%)" 0 --> 35
    bar [4.0, 26.8, 31.7, 27.5, 9.9, 0.1]
```

| 지표 | v2 (threshold 20) | v3 (threshold 100) | 변화 |
|------|:------------------:|:------------------:|:----:|
| .md 청크 수 | 34,747 | 23,342 | **-32.8%** |
| <100토큰 비율 | 74.1% | 62.5% | **-11.6pp** |
| 평균 토큰 | ~55 | 97.6 | **+77%** |
| <20토큰(Junk) | ~15% | 4.0% | **-11pp** |
| 100-199토큰(Optimal) | ~10% | 27.5% | **+17.5pp** |

### 5.3 파일 유형별 품질

```mermaid
xychart-beta
    title "파일 유형별 <100토큰 비율"
    x-axis ["md", "pdf", "pptx", "docx", "txt"]
    y-axis "<100 토큰 비율 (%)" 0 --> 70
    bar [62.5, 43.0, 58.9, 23.6, 0.5]
```

| 유형 | <100tok 비율 | 평균 토큰 | 품질 등급 | 비고 |
|------|:-----------:|:---------:|:---------:|------|
| **txt** | 0.5% | 231.4 | A | 연속 텍스트, 분할 양호 |
| **docx** | 23.6% | 134.9 | B+ | 구조화 문서, 적정 분할 |
| **pdf** | 43.0% | 128.7 | B | OCR 품질 양호 |
| **pptx** | 58.9% | 108.9 | C+ | 슬라이드 특성상 짧은 청크 |
| **md** | 62.5% | 97.6 | C | 코드블록/헤더 구조적 한계 |

---

## 6. 인프라 성능

### 6.1 리소스 사용 현황

```mermaid
flowchart LR
    subgraph Container["kp-ai-service Container"]
        CPU["CPU: 100-395%<br/>(4 vCPU 환경)"]
        MEM["Memory: 2~6.7 GB<br/>(Limit: 10 GB)"]
        DISK["Disk I/O:<br/>Read-heavy (Docling)"]
    end

    subgraph External["External Services"]
        PG_SVC["PostgreSQL<br/>Write: 1,437 rows"]
        ES_SVC["Elasticsearch<br/>Write: 62,489 docs<br/>Index: 132.3 MB"]
        NEO_SVC["Neo4j<br/>Write: Nodes + Relations"]
    end

    Container --> PG_SVC
    Container --> ES_SVC
    Container --> NEO_SVC

    style Container fill:#fff3e0,stroke:#e65100
    style External fill:#e3f2fd,stroke:#1565c0
```

### 6.2 메모리 프로필

| 구간 | 메모리 | 처리 대상 | 비고 |
|------|-------:|-----------|------|
| 초기 (MD/TXT) | 1.5~2.5 GB | 경량 파일 | 안정적 |
| 중형 PDF | 3.0~4.5 GB | 일반 PDF (10~50p) | OCR 활성 |
| 대형 PDF | 5.0~6.7 GB | 200p+ PDF | 피크 메모리 |
| 완료 후 | **334 MB** | IDLE | GC 정상 |
| OOM 임계값 | 10.0 GB | - | v4에서 미도달 |

### 6.3 처리 속도

| 파일 유형 | 평균 처리 시간 | 최대 처리 시간 | 비고 |
|-----------|:-------------:|:-------------:|------|
| .md | ~1초 | 5초 | 파싱 빠름 |
| .txt | ~1초 | 3초 | 파싱 빠름 |
| .docx | ~5초 | 30초 | 테이블 포함 시 증가 |
| .pptx | ~3초 | 20초 | 슬라이드 수 비례 |
| .pdf (일반) | ~12초 | 60초 | OCR ON |
| .pdf (대형) | ~5분 | 16분 | 200p+ 문서 |

---

## 7. 데이터 정합성

### 7.1 3-Store 일관성 검증

```mermaid
flowchart TB
    subgraph Consistency["3-Store 정합성 현황"]
        PG["PostgreSQL<br/>chunk_count SUM = 56,063"]
        ES["Elasticsearch<br/>_count = 62,489"]
        NEO["Neo4j<br/>Chunk nodes"]
    end

    PG -->|"GAP: 6,426"| ES
    PG --> NEO

    subgraph Analysis["GAP 분석"]
        G1["ES에 v2 잔여 청크?"]
        G2["PG chunk_count 미갱신?"]
        G3["Phase 2 조사 필요"]
    end

    ES --> Analysis

    style Consistency fill:#fce4ec,stroke:#c62828
    style Analysis fill:#fff9c4,stroke:#f9a825
```

| Store | 수량 | 비고 |
|-------|-----:|------|
| **PG documents** | 1,437 | 문서 수 (SSOT) |
| **PG chunk_count 합계** | 56,063 | SUM(chunk_count) |
| **ES chunks** | 62,489 | _count API |
| **GAP** | **6,426** | 조사 필요 |

### 7.2 GAP 원인 추정

1. v2 ETL에서 생성된 청크가 ES에 잔존 (v3에서 .md만 삭제/재처리)
2. PG `chunk_count` 필드 갱신 시점과 ES bulk write 시점 차이
3. Phase 2(임베딩) 시작 전 정합성 맞춤 필요

---

## 8. 장애 이력 및 교훈

### 8.1 장애 타임라인

```mermaid
flowchart LR
    I1["v1 OOM Kill<br/>02-13 18:00"] -->|"원인: mem 무제한"| F1["Fix: 10GB 제한"]
    F1 --> I2["v2 153시간 예상<br/>02-13 22:00"]
    I2 -->|"원인: OCR 느림"| F2["Fix: OCR OFF"]
    F2 --> I3["v3 58.2% 저품질<br/>02-14 06:00"]
    I3 -->|"원인: OCR 필수"| F3["Fix: OCR ON 복원"]
    F3 --> S1["v4 정상 완주<br/>02-15 07:52"]
    S1 --> I4[".md 74.1% <100tok"]
    I4 -->|"원인: merge 20tok"| F4["Fix: threshold 100"]
    F4 --> S2["v3-md 품질 개선<br/>02-15 09:49"]

    style I1 fill:#ffcdd2,stroke:#c62828
    style I2 fill:#ffcdd2,stroke:#c62828
    style I3 fill:#ffcdd2,stroke:#c62828
    style I4 fill:#fff9c4,stroke:#f9a825
    style F1 fill:#c8e6c9,stroke:#2e7d32
    style F2 fill:#c8e6c9,stroke:#2e7d32
    style F3 fill:#c8e6c9,stroke:#2e7d32
    style F4 fill:#c8e6c9,stroke:#2e7d32
    style S1 fill:#bbdefb,stroke:#1565c0
    style S2 fill:#bbdefb,stroke:#1565c0
```

### 8.2 교훈 요약

| # | 장애 | 근본 원인 | 해결 | 교훈 |
|---|------|----------|------|------|
| 1 | OOM Kill | 메모리 제한 미설정 | `--memory=10g` | 컨테이너 자원 제한 필수 |
| 2 | 153시간 예상 | OCR + 자원 경합 | Backfill 중단 | 동시 부하 측정 필수 |
| 3 | 58% 저품질 | OCR OFF | OCR ON 복원 | 속도 < 품질 |
| 4 | .md 과분할 | merge threshold 20 | threshold 100 | 파일 유형별 튜닝 |

---

## 9. 후속 작업 (Phase 2~4)

### 9.1 전체 로드맵

```mermaid
flowchart LR
    subgraph Done["✅ Phase 1 (완료)"]
        P1["Document Parsing<br/>+ Chunking<br/>1,437 docs → 62,489 chunks"]
    end

    subgraph Next["🔄 Phase 2 (다음)"]
        P2["GPU Embedding<br/>Colab T4/A100<br/>Dense 1024d + Sparse"]
    end

    subgraph Future1["📋 Phase 3"]
        P3["Entity Extraction<br/>Gleaning (DeepSeek V3.2)<br/>Knowledge Graph"]
    end

    subgraph Future2["📋 Phase 4"]
        P4["Search Integration<br/>4-Way RRF<br/>Dense+Sparse+BM25+Graph"]
    end

    Done --> Next --> Future1 --> Future2

    style Done fill:#c8e6c9,stroke:#2e7d32
    style Next fill:#fff3e0,stroke:#e65100
    style Future1 fill:#e3f2fd,stroke:#1565c0
    style Future2 fill:#f3e5f5,stroke:#6a1b9a
```

### 9.2 Phase별 상세

| Phase | 내용 | 환경 | 예상 소요 | 상태 |
|-------|------|------|----------|:----:|
| **Phase 1** | Parsing + Chunking | Docker (CPU) | 12시간 | ✅ 완료 |
| **Phase 2** | Dense + Sparse Embedding | Colab GPU (T4) | 2~4시간 | 준비 중 |
| **Phase 3** | Gleaning Entity Extraction | DeepSeek API | 4~8시간 | 대기 |
| **Phase 4** | 4-Way RRF Search | Docker (CPU) | 코드 변경 | 대기 |

---

## 10. 결론

ETL Phase 1은 5회 실행(v1~v4 + v3-md)의 반복과 장애 대응을 거쳐 안정적으로 완료되었다.

**핵심 성과**:
- 1,786개 원본 문서 중 1,437개 성공 적재 (80.5%), 실패 0건
- 62,489개 청크 생성, 평균 115 토큰/청크
- Chunker v3으로 .md 품질 개선: 청크 -33%, 평균 토큰 +77%
- OOM Kill → 메모리 제한 10GB + OCR ON + TableFormerMode.FAST 최적 설정 확정

**잔여 과제**:
- ES-PG 청크 수 불일치 (6,426건) 조사
- .md 62.5% <100토큰 구조적 한계 (코드블록/헤더)
- Phase 2 GPU 임베딩으로 검색 품질 확보

---

## Appendix A. 설정 값 레퍼런스

### A.1 Chunker 설정

```python
# knowledge_service/src/app/etl/chunker.py
SEMANTIC_CHUNKER_CONFIG = {
    "chunk_size": 1000,           # 최대 청크 크기 (tokens)
    "chunk_overlap": 200,         # 청크 오버랩
    "merge_threshold": 100,       # 소형 청크 병합 임계값 (v3)
    "min_chunk_tokens": 20,       # Quality Gate 최소
    "max_chunk_tokens": 1500,     # Quality Gate 최대
}
```

### A.2 Docling 설정

```python
# knowledge_service/src/app/etl/docling_adapter.py
DOCLING_CONFIG = {
    "ocr_enabled": True,          # OCR ON (v4부터)
    "table_former_mode": "FAST",  # TableFormerMode.FAST
    "max_pages": None,            # 페이지 제한 없음
}
```

### A.3 컨테이너 설정

```yaml
# docker-compose.yml
ai-service:
  mem_limit: 10g                  # OOM 방지
  environment:
    - EMBEDDING_BATCH_SIZE=4      # CPU 최적값
    - EMBEDDING_MAX_TEXT_LENGTH=1000
    - EMBEDDING_WORKERS=1
```

---

## Appendix B. 관련 문서

| 문서 | 위치 |
|------|------|
| 장애보고서 #27 | `docs/07_maintenance/27_incident_report_2026-02-15_etl_oom_and_md_chunking.md` |
| ETL 3-Phase 운영 가이드 | `docs/07_maintenance/24_etl_3phase_operations_guide.md` |
| Sparse 검색 통합 설계서 | `docs/02_design/15_sparse_vector_search_integration_design.md` |
| 상세 설계서 v2.4 | `docs/02_design/01_hybrid_rag_platform_detailed_design.md` |

---

*Document ID: DOC-MAINT-028*
*Created: 2026-02-15*
*Author: Claude Opus 4.6 (AI Service Team)*
*Review Status: Draft*
