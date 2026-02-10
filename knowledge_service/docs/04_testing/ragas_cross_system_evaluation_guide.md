# RAGAS 크로스 시스템 평가 가이드

**HRKP vs RAGChatbotServer 성능 비교 평가 프레임워크**

**Version**: 1.1 | **Updated**: 2026-02-10 | **Author**: MLRag

---

## 1. 개요

### 1.1 목적

HRKP(Hybrid RAG Knowledge Platform)에 구현된 RAGAS 평가 프레임워크를 활용하여, 외부 RAG 시스템(RAGChatbotServer)과 **동일한 기준**으로 성능을 비교 측정한다.

### 1.2 대상 시스템

| 항목 | HRKP | RAGChatbotServer |
|------|------|------------------|
| **프레임워크** | FastAPI + LangGraph | FastAPI + LangChain |
| **LLM** | DeepSeek V3.2 (로컬) | OpenAI GPT-4o-mini (클라우드) |
| **임베딩** | BGE-M3 ONNX (로컬) | OpenAI text-embedding-3-small |
| **벡터 DB** | Elasticsearch 8.x | ES / OpenSearch / PGVector (선택) |
| **검색 방식** | Hybrid (BM25 + Dense + Graph) | Hybrid (BM25 + Dense) |
| **비용 모델** | 로컬 추론 (GPU/CPU) | API 과금 ($0.15/1M tokens) |

### 1.3 평가 메트릭 (RAGAS 4종)

| 메트릭 | 설명 | 목표 | 필요 데이터 |
|--------|------|------|------------|
| **Faithfulness** | 답변이 컨텍스트에 충실한지 (환각 방지) | >= 0.9 | question, answer, **contexts** |
| **Answer Relevancy** | 답변이 질문과 관련 있는지 | >= 0.85 | question, answer |
| **Context Precision** | 검색된 컨텍스트가 정확한지 | >= 0.8 | question, **contexts** |
| **Context Recall** | 필요한 정보가 검색되었는지 | >= 0.7 | question, **contexts**, ground_truth |

### 1.4 평가 환경 (확정)

| 항목 | HRKP | RAGChatbotServer |
|------|------|------------------|
| **벡터 DB** | Elasticsearch 8.x | **Elasticsearch 8.x** (동일) |
| **검색 모드** | Hybrid (BM25 + Dense + Graph) | custom-hybrid (BM25 + Dense) |
| **Docker 구성** | kp-elasticsearch (기존) | docker-compose-es.yml |

> **참고**: RAGChatbotServer는 ES/OpenSearch/PGVector 중 선택 가능하나, HRKP와 동일한 **Elasticsearch** 기반으로 평가하여 벡터 DB 변수를 제거한다.

---

## 1.5 예상 성능 비교표

### 1.5.1 시스템 아키텍처 비교

```mermaid
flowchart LR
    subgraph HRKP_Arch["HRKP (로컬 추론)"]
        direction TB
        Q1["Query"] --> S1["Hybrid Search<br/>BM25 + Dense + Graph"]
        S1 --> RRF["RRF Fusion<br/>(3-way merge)"]
        RRF --> R1["Reranker"]
        R1 --> LLM1["DeepSeek V3.2<br/>(API, 저비용)"]
        LLM1 --> A1["Answer"]
    end

    subgraph RCSV_Arch["RAGChatbotServer (클라우드 API)"]
        direction TB
        Q2["Query"] --> S2["Custom Hybrid<br/>BM25 + Dense"]
        S2 --> R2["LangChain<br/>Retriever (alpha=0.6)"]
        R2 --> LLM2["GPT-4o-mini<br/>(OpenAI API)"]
        LLM2 --> A2["Answer"]
    end

    style HRKP_Arch fill:#e3f2fd
    style RCSV_Arch fill:#fff3e0
```

### 1.5.2 전체 파이프라인 상세 비교

#### A. 문서 파싱 (Document Parsing) - RAG 품질의 근본

| 항목 | HRKP (Docling) | RCSV (pdfplumber) | 예상 영향 |
|------|----------------|-------------------|----------|
| **파싱 엔진** | Docling (IBM, AI 기반) | pdfplumber / pypdf / unstructured | Docling이 구조 인식 정확도 우수 |
| **표(Table) 처리** | 구조 보존 (TableCell 모델, 행/열/헤더 분리) | 텍스트 평탄화 (구조 소실) | 표 데이터 질의 시 HRKP 정확도 높음 |
| **섹션 구조** | Section 계층 보존 → 청킹 경계로 활용 | 페이지 단위 평탄 텍스트 | HRKP 청크가 의미 단위로 깨끗 |
| **OCR 지원** | 내장 (스캔 문서 처리) | 미지원 (기본) | 스캔 PDF 처리 시 HRKP만 가능 |
| **이미지 처리** | 추출 + ImageRef 참조 보존 | 무시 (텍스트만) | 이미지 캡션 정보 HRKP만 보존 |
| **지원 형식** | PDF, DOCX, PPTX | PDF only | HRKP 다형식 지원 |

> **영향 체인**: `파싱 품질 → 청킹 품질 → 임베딩 품질 → 검색 품질 → 답변 품질`
>
> Docling의 구조 보존은 Context Precision(+0.05~0.10)과 Context Recall(+0.03~0.07)에 직접적 영향을 미치며, 이는 HRKP 검색 품질 우위의 근본 원인 중 하나이다.

#### B. 청킹 전략

| 항목 | HRKP | RCSV | 예상 영향 |
|------|------|------|----------|
| **청킹 방식** | SemanticChunker (문장/섹션 경계) | RecursiveCharacterTextSplitter (문자 수) | HRKP가 의미 단위 보존, RCSV는 문맥 중간 절단 가능 |
| **청크 크기** | 600자 (100 overlap) | 2000자 (300 overlap) | HRKP 세밀한 검색, RCSV 풍부한 맥락 |
| **특수 블록** | 테이블/코드 블록 보존 | 문자 수 기반 분할 (블록 절단 가능) | HRKP가 구조화 데이터 검색에 유리 |
| **한국어 지원** | 한국어 문장 종결어미 패턴 인식 | 범용 분리자 (언어 무관) | 한국어 문서에서 HRKP 유리 |

#### C. 검색 파이프라인

| 항목 | HRKP | RAGChatbotServer | 예상 영향 |
|------|------|------------------|----------|
| **검색 채널** | 3채널 (Dense + BM25 + Graph) | 2채널 (Dense + BM25) | HRKP의 Graph 검색이 multi-hop 질의에서 우위 |
| **결과 융합** | RRF (Reciprocal Rank Fusion) | LangChain alpha=0.6 가중합 | RRF가 이론적으로 더 robust한 fusion |
| **Reranker** | 있음 (검색 후 재정렬) | 없음 | HRKP의 Context Precision 우위 예상 |
| **임베딩 모델** | BGE-M3 (1024d, 다국어) | OpenAI text-embedding-3-small (1536d) | OpenAI 임베딩 품질 약간 우위 가능 |
| **임베딩 위치** | 로컬 ONNX (CPU) | OpenAI API (클라우드) | RCSV 임베딩 latency 낮음 (API 최적화) |
| **메타데이터** | 구조화 (PostgreSQL SSOT) | LLM 생성 (level1/2/3, summary) | RCSV의 LLM 메타데이터가 BM25에 유리 |
| **Knowledge Graph** | Neo4j (엔티티/관계) | 없음 | HRKP 고유 강점 (관계 추론) |

### 1.5.3 RAGAS 메트릭 예상 점수

> 아래 예상치는 시스템 아키텍처 분석, 코드 리뷰, 기존 벤치마크 자료를 기반으로 추론한 값입니다. **실측 후 업데이트 예정.**

| 메트릭 | HRKP 예상 | RCSV 예상 | 예상 우위 | 근거 |
|--------|:---------:|:---------:|:---------:|------|
| **Faithfulness** | 0.75~0.85 | **0.80~0.90** | RCSV | GPT-4o-mini의 instruction following이 DeepSeek 대비 우수, 환각 제어 강점 |
| **Answer Relevancy** | 0.70~0.80 | **0.75~0.85** | RCSV | GPT-4o-mini의 자연어 생성 품질이 높고, 질문-답변 정합성 우수 |
| **Context Precision** | **0.75~0.85** | 0.60~0.70 | HRKP | Docling 구조 보존 + SemanticChunker + RRF + Reranker 4중 효과 |
| **Context Recall** | **0.70~0.80** | 0.55~0.65 | HRKP | Docling 표/이미지 추출 + Graph 검색 + 3채널 커버리지 |
| **종합 평균** | **0.73~0.83** | **0.68~0.78** | HRKP | 파싱+검색 품질 우위가 생성 품질 열위를 보완 |

### 1.5.4 성능(Latency) 예상 비교

| 항목 | HRKP 예상 | RCSV 예상 | 근거 |
|------|:---------:|:---------:|------|
| **임베딩 (쿼리)** | 50~200ms (로컬 CPU) | 30~80ms (OpenAI API) | API 호출이 최적화된 서버에서 처리 |
| **ES 검색** | 50~150ms | 50~150ms | 동일 ES, 유사 검색 방식 |
| **Graph 검색** | 100~300ms | N/A | HRKP에만 있음 (추가 latency) |
| **RRF 융합** | 10~30ms | N/A | HRKP에만 있음 |
| **Reranker** | 100~500ms | N/A | HRKP에만 있음 |
| **LLM 생성** | 1~3s (DeepSeek API) | 0.5~2s (GPT-4o-mini) | GPT-4o-mini가 약간 빠름 |
| **E2E P50** | **1.5~3s** | **0.8~2s** | RCSV가 파이프라인 단순하여 빠름 |
| **E2E P95** | **3~5s** | **1.5~3s** | HRKP Graph+Reranker 추가 비용 |

### 1.5.5 비용 비교 (1,000 쿼리 기준)

| 항목 | HRKP | RCSV | 비고 |
|------|-----:|-----:|------|
| **LLM 추론** | $0.05 | $0.15 | DeepSeek $0.14/1M vs GPT-4o-mini $0.15/1M input |
| **임베딩** | $0.00 | $0.002 | 로컬 BGE-M3 vs OpenAI $0.02/1M tokens |
| **인프라 (Docker)** | $0.00* | $0.00* | 둘 다 로컬 Docker (*전기 제외) |
| **총 비용/1K 쿼리** | **~$0.05** | **~$0.15** | HRKP 약 3배 저렴 |

> *DeepSeek V3.2 비용: input $0.14/1M, output $0.28/1M (GPT-4o-mini 대비 95% 절감)*

### 1.5.6 강점/약점 예상 요약

| 시스템 | 강점 | 약점 |
|--------|------|------|
| **HRKP** | Docling 구조 파싱 + SemanticChunker + 3채널 Hybrid + Graph + RRF + Reranker로 검색 품질 우수, 비용 효율적 | 파이프라인 복잡도로 latency 높음, 로컬 임베딩 CPU 병목 |
| **RCSV** | GPT-4o-mini 생성 품질, 단순한 파이프라인으로 빠른 응답, OpenAI 임베딩 품질 | pdfplumber 구조 소실 + 문자 수 청킹으로 의미 절단, Graph/Reranker 없음, API 비용 |

### 1.5.7 메트릭별 예상 승패 매트릭스

```
                    HRKP 우위          RCSV 우위
                    ◄────────────────►
Faithfulness       ■■■■■■■■■■■■████████████  ← RCSV (LLM 품질)
Answer Relevancy   ■■■■■■■■■■■████████████  ← RCSV (LLM 품질)
Context Precision  █████████████████■■■■■■  ← HRKP (Docling+Reranker+RRF)
Context Recall     ████████████████■■■■■■■  ← HRKP (Docling+Graph+3채널)
─────────────────────────────────────────
Parsing Quality    ██████████████████■■■■■  ← HRKP (Docling vs pdfplumber)
Chunking Quality   ████████████████■■■■■■■  ← HRKP (Semantic vs Character)
E2E Latency        ■■■■■■■■■████████████   ← RCSV (단순 파이프라인)
Cost/Query         ██████████████████■■■■   ← HRKP (로컬 추론)

■ = 열위  █ = 우위
```

> **핵심 인사이트**: HRKP는 **파싱+검색(Parsing+Retrieval)** 품질에서, RCSV는 **생성(Generation)** 품질에서 각각 강점을 가질 것으로 예상. Docling에 의한 구조 보존 → SemanticChunker → 깨끗한 청크 → 정밀한 검색이라는 파이프라인 전체의 품질 체인이 HRKP의 검색 우위를 형성한다.

---

## 2. 호환성 분석

### 2.1 HRKP 평가 프레임워크 구조

```mermaid
flowchart TB
    subgraph Core["핵심 평가 엔진 (범용)"]
        RS["RagasEvaluator<br/>evaluate(samples, metrics)"]
        ES["EvaluationSample<br/>question, answer, contexts, ground_truth"]
        MS["MetricScores<br/>faithfulness, relevancy, precision, recall"]
        RG["RagasReportGenerator<br/>generate_markdown(), save_reports()"]
    end

    subgraph HRKP_Specific["HRKP 전용"]
        LE["LiveRagasEvaluator<br/>evaluate_live(questions)"]
        RW["RAGWorkflow.run()<br/>→ answer + search_results"]
    end

    subgraph Adapter["어댑터 (신규 작성 필요)"]
        CA["CrossSystemAdapter<br/>call_external_rag()"]
        RC["RAGChatbotServer<br/>query() 직접 호출"]
    end

    ES --> RS
    RS --> MS
    MS --> RG

    LE --> RW
    RW --> ES

    CA --> RC
    RC --> ES

    style Core fill:#e1f5fe
    style HRKP_Specific fill:#fff3e0
    style Adapter fill:#e8f5e9
```

### 2.2 컴포넌트별 범용성

| 컴포넌트 | 파일 | 범용성 | 외부 시스템 사용 |
|----------|------|--------|-----------------|
| `EvaluationSample` | `evaluation/models.py` | **범용** | 즉시 사용 가능 |
| `MetricScores` | `evaluation/models.py` | **범용** | 즉시 사용 가능 |
| `EvaluationResponse` | `evaluation/models.py` | **범용** | 즉시 사용 가능 |
| `RagasEvaluator` | `evaluation/ragas_evaluator.py` | **범용** | `List[EvaluationSample]`만 제공하면 됨 |
| `RagasReportGenerator` | `evaluation/report_generator.py` | **범용** | `project_name` 파라미터만 변경 |
| `LiveRagasEvaluator` | `evaluation/live_evaluator.py` | **HRKP 전용** | `RAGWorkflow` 하드 의존 → 사용 불가 |

### 2.3 핵심 블로커: RAGChatbotServer API의 contexts 미반환

**RAGChatbotServer `/ai/chat` API 응답:**

```json
{
  "response": "답변 텍스트",
  "processing_time": 2.345,
  "reference_chunk_count": 5,
  "search_mode": "custom-hybrid",
  "vector_store_type": "pgvector",
  "session_id": "abc-123"
}
```

**문제**: `reference_chunk_count`(숫자)만 반환하고, 실제 검색된 **컨텍스트 텍스트**를 반환하지 않음.

**메트릭별 영향:**

| 메트릭 | contexts 필요 | API로 가능 | 내부 호출로 가능 |
|--------|:------------:|:----------:|:---------------:|
| Answer Relevancy | X | **가능** | **가능** |
| Faithfulness | **O** | **불가** | **가능** |
| Context Precision | **O** | **불가** | **가능** |
| Context Recall | **O** | **불가** | **가능** |

### 2.4 RAGChatbotServer 내부 `query()` 메서드 분석

`rag_system.py`의 `SearchRAG.query()` 반환값:

```python
{
    "answer": str,              # LLM 생성 답변
    "sources": List[Document],  # Document 객체 리스트
    "search_mode": str,
    "processing_time": float,
    # ... 기타 필드
}

# Document 객체 구조
# sources[i].page_content → 검색된 원문 텍스트 (contexts로 사용 가능!)
# sources[i].metadata → {"source": "파일명", "page": 1, ...}
```

**결론**: API를 우회하고 `query()` 메서드를 직접 호출하면 `sources[i].page_content`에서 contexts를 추출하여 4/4 메트릭 모두 평가 가능.

---

## 3. 해결 방안

### 3.1 방안 비교

| 방안 | 구현 난이도 | 메트릭 커버리지 | 권장도 |
|------|:-----------:|:--------------:|:------:|
| **A: API 수정** | 중 | 4/4 | 낮음 (원본 코드 수정) |
| **B: 내부 호출 어댑터** | **낮** | **4/4** | **높음 (권장)** |
| **C: 제한 평가** | 최저 | 1/4 | 낮음 |

### 3.2 방안 B: CrossSystemAdapter (권장)

RAGChatbotServer의 `rag_system.py`를 직접 import하여 `query()`를 호출하는 어댑터를 작성한다.

```python
"""
크로스 시스템 RAG 평가 어댑터

RAGChatbotServer의 rag_system.py를 직접 호출하여
EvaluationSample을 생성합니다.
"""
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

from app.evaluation.models import EvaluationResponse, EvaluationSample
from app.evaluation.ragas_evaluator import RagasEvaluator
from app.evaluation.report_generator import RagasReportGenerator


class CrossSystemAdapter:
    """외부 RAG 시스템을 HRKP RAGAS 프레임워크로 평가하는 어댑터"""

    def __init__(
        self,
        system_name: str,
        rag_module_path: str,
        targets: Optional[Dict[str, float]] = None,
    ):
        self.system_name = system_name
        self.rag_module_path = rag_module_path
        self.targets = targets or {
            "faithfulness": 0.9,
            "answer_relevancy": 0.85,
            "context_precision": 0.8,
            "context_recall": 0.7,
        }
        self._rag_system = None
        self._evaluator = RagasEvaluator(targets=self.targets)
        self._reporter = RagasReportGenerator(project_name=system_name)

    def _load_rag_system(self):
        """외부 RAG 시스템 동적 로드"""
        if self._rag_system is None:
            sys.path.insert(0, self.rag_module_path)
            from rag_system import SearchRAG
            self._rag_system = SearchRAG()
        return self._rag_system

    def query_external(
        self, question: str, chat_history: list = None
    ) -> Dict[str, Any]:
        """외부 RAG 시스템에 질의"""
        rag = self._load_rag_system()
        start = time.monotonic()
        result = rag.query(question, chat_history or [])
        elapsed_ms = (time.monotonic() - start) * 1000

        # contexts 추출: sources[i].page_content
        contexts = [
            doc.page_content
            for doc in result.get("sources", [])
            if hasattr(doc, "page_content")
        ]

        return {
            "question": question,
            "answer": result.get("answer", ""),
            "contexts": contexts,
            "latency_ms": elapsed_ms,
            "source_count": len(contexts),
            "search_mode": result.get("search_mode", "unknown"),
        }

    def build_samples(
        self,
        questions: List[str],
        ground_truths: Optional[List[str]] = None,
    ) -> Tuple[List[EvaluationSample], List[Dict]]:
        """질문 리스트로 EvaluationSample 생성"""
        samples = []
        raw_responses = []

        for idx, q in enumerate(questions):
            resp = self.query_external(q)
            raw_responses.append(resp)

            sample = EvaluationSample(
                question=q,
                answer=resp["answer"],
                contexts=resp["contexts"],
                ground_truth=ground_truths[idx] if ground_truths else None,
                metadata={
                    "system": self.system_name,
                    "latency_ms": resp["latency_ms"],
                    "source_count": resp["source_count"],
                },
            )
            samples.append(sample)

        return samples, raw_responses

    async def evaluate(
        self,
        questions: List[str],
        ground_truths: Optional[List[str]] = None,
        metrics: Optional[List[str]] = None,
    ) -> Tuple[EvaluationResponse, List[Dict]]:
        """전체 평가 수행"""
        metrics = metrics or [
            "faithfulness", "answer_relevancy",
            "context_precision", "context_recall",
        ]

        samples, raw = self.build_samples(questions, ground_truths)
        response = await self._evaluator.evaluate(samples, metrics)
        return response, raw

    def generate_report(
        self, response: EvaluationResponse, output_dir: str
    ) -> Dict[str, str]:
        """Markdown + JSON 리포트 생성"""
        return self._reporter.save_reports(response, output_dir)
```

### 3.3 방안 A: RAGChatbotServer API 수정 (대안)

`RAGChatbotServer/app.py`의 `/ai/chat` 엔드포인트에 contexts 반환 추가:

```python
# app.py 수정 위치: /ai/chat 엔드포인트의 응답 구성 부분
# 기존:
return JSONResponse(content={
    "response": answer,
    "reference_chunk_count": len(sources),
    ...
})

# 수정 (contexts 필드 추가):
return JSONResponse(content={
    "response": answer,
    "contexts": [doc.page_content for doc in sources],  # 추가
    "reference_chunk_count": len(sources),
    ...
})
```

---

## 4. 비교 평가 실행 계획

### 4.1 평가 아키텍처

```mermaid
flowchart LR
    subgraph Input["공통 입력"]
        QA["테스트 데이터셋<br/>questions + ground_truths<br/>(최소 24개 QA 쌍)"]
    end

    subgraph HRKP_Eval["HRKP 평가"]
        LR["LiveRagasEvaluator"]
        RW["RAGWorkflow"]
        LR --> RW
    end

    subgraph RCSV_Eval["RAGChatbotServer 평가"]
        CA["CrossSystemAdapter"]
        RS["SearchRAG.query()"]
        CA --> RS
    end

    subgraph Core["공통 평가 엔진"]
        RE["RagasEvaluator"]
        RG["RagasReportGenerator"]
        RE --> RG
    end

    subgraph Output["비교 리포트"]
        CR["comparison_report.md<br/>메트릭 비교표 + 분석"]
    end

    QA --> LR
    QA --> CA
    HRKP_Eval --> RE
    RCSV_Eval --> RE
    Core --> CR

    style Input fill:#e3f2fd
    style Core fill:#e1f5fe
    style Output fill:#e8f5e9
```

### 4.2 테스트 데이터셋 구성

**기존 데이터셋 활용**: `src/tests/evaluation/test_dataset.json` (24개 QA 쌍)

단, 두 시스템에서 **동일한 지식 베이스**를 사용해야 공정한 비교가 가능:

| 전략 | 설명 | 공정성 |
|------|------|--------|
| **A: 동일 문서 적재** | 동일한 PDF를 양쪽 시스템에 적재 | 높음 |
| **B: 도메인 무관 QA** | 기술 상식 QA로 LLM 자체 능력 측정 | 중간 |
| **C: 각자 지식 베이스** | 각 시스템 고유 데이터로 평가 | 낮음 (비교 불가) |

**권장**: **전략 A** - 동일한 테스트 문서 세트를 양쪽에 적재 후 평가

### 4.3 실행 단계

```
Phase 1: 환경 준비
├── 1.1 RAGChatbotServer 기동 확인 (Docker Compose)
├── 1.2 테스트 문서 세트 선정 (5~10개 PDF)
├── 1.3 양쪽 시스템에 문서 적재
└── 1.4 CrossSystemAdapter 구현

Phase 2: 개별 평가
├── 2.1 HRKP Live 평가 (LiveRagasEvaluator)
├── 2.2 RAGChatbotServer 평가 (CrossSystemAdapter)
└── 2.3 개별 리포트 생성

Phase 3: 비교 분석
├── 3.1 메트릭별 비교표 생성
├── 3.2 Latency 비교 (P50/P95/P99)
├── 3.3 비용 분석 (로컬 vs API)
└── 3.4 종합 비교 리포트 작성
```

### 4.4 비교 리포트 형식

```markdown
# RAG 시스템 비교 평가 리포트

## 1. 평가 요약

| 메트릭 | HRKP | RAGChatbotServer | 차이 | 우위 |
|--------|------|------------------|------|------|
| Faithfulness | 0.xx | 0.xx | +0.xx | HRKP/RCSV |
| Answer Relevancy | 0.xx | 0.xx | +0.xx | - |
| Context Precision | 0.xx | 0.xx | +0.xx | - |
| Context Recall | 0.xx | 0.xx | +0.xx | - |
| **평균** | 0.xx | 0.xx | - | - |

## 2. 성능 비교

| 항목 | HRKP | RAGChatbotServer |
|------|------|------------------|
| P50 Latency | xx ms | xx ms |
| P95 Latency | xx ms | xx ms |
| 추정 비용/1000쿼리 | $0.xx | $0.xx |

## 3. 강점/약점 분석
(시스템별 강점, 약점, 개선 방향)

## 4. 결론 및 권장 사항
```

---

## 5. 알려진 제약사항

### 5.1 RAGChatbotServer 버그

| ID | 설명 | 영향 |
|----|------|------|
| C-1 | `PGVectorRAG.__init__` 이중 초기화 → NameError | PGVector 모드 사용 불가 |
| C-2 | Health check가 RAG 쿼리 실행 | 성능 측정 시 노이즈 |
| C-3 | 인증 미구현 | 보안 평가 불가 |

### 5.2 공정성 고려사항

| 요소 | 설명 | 대응 |
|------|------|------|
| **LLM 차이** | DeepSeek vs GPT-4o-mini (모델 능력 차이) | 동일 메트릭으로 객관 비교 |
| **임베딩 차이** | BGE-M3 vs OpenAI embedding | 검색 품질에 영향 |
| **인프라 차이** | 로컬 CPU vs 클라우드 API | Latency에 직접 영향 |
| **지식 베이스** | 적재 문서가 다를 수 있음 | 동일 문서 적재 필수 |

---

## 6. 참고 자료

- [RAGAS 평가 파이프라인 가이드](../05_development/ragas_evaluation_guide.md)
- [EPIC-005: RAG Quality & Performance](../../backlog/epics/EPIC-005-rag-quality-performance.md)
- [STORY-105: RAGAS 평가 기준 문서 확정](../../backlog/stories/STORY-105-ragas-evaluation-criteria.md)
- [STORY-111: HRKP vs RAGChatbotServer 비교 평가](../../backlog/stories/STORY-111-cross-system-ragas-evaluation.md)
- [RAGChatbotServer 분석 (README.md)](../../../RAGChatbotServer/README.md)
- [RAGAS 공식 문서](https://docs.ragas.io/)

---

## 부록 A: HRKP 평가 프레임워크 소스 참조

### A.1 EvaluationSample 모델

```
파일: knowledge_service/src/app/evaluation/models.py:13-32
```

```python
class EvaluationSample(BaseModel):
    question: str      # 필수 - 사용자 질문
    answer: str        # 필수 - RAG 생성 답변
    contexts: List[str]  # 필수 - 검색된 컨텍스트 텍스트 리스트
    ground_truth: Optional[str] = None  # 선택 - Context Recall 측정 시 필요
    metadata: Dict[str, Any] = {}       # 선택 - 추가 메타데이터
```

### A.2 RagasEvaluator 인터페이스

```
파일: knowledge_service/src/app/evaluation/ragas_evaluator.py:44-67
```

```python
class RagasEvaluator:
    def __init__(
        self,
        llm_model: Optional[str] = None,      # 기본: DeepSeek Chat
        embedding_model: Optional[str] = None, # 기본: BGE-M3
        targets: Optional[Dict[str, float]] = None,
    ): ...

    async def evaluate(
        self,
        samples: List[EvaluationSample],  # 범용 입력
        metrics: List[str],               # ["faithfulness", "answer_relevancy", ...]
    ) -> EvaluationResponse: ...
```

### A.3 LiveRagasEvaluator (HRKP 전용)

```
파일: knowledge_service/src/app/evaluation/live_evaluator.py:25-153
```

- `RAGWorkflow.run()` → `rag_response.search_results[].content` 로 contexts 추출
- **외부 시스템에서는 사용 불가** (HRKP RAGWorkflow 하드 의존)

### A.4 기존 평가 결과 (HRKP, 2026-02-04)

```
파일: knowledge_service/docs/results/ragas/ragas_evaluation_2026-02-04_022522.md
```

| 메트릭 | 점수 | 목표 | 달성 |
|--------|------|------|------|
| Faithfulness | 0.4032 | 0.90 | FAIL |
| Answer Relevancy | 0.1895 | 0.85 | FAIL |
| Context Precision | 0.2778 | 0.80 | FAIL |
| Context Recall | N/A | 0.70 | N/A |

> **참고**: 위 점수는 Mock 모드(word overlap 기반)로 실행된 초기 결과입니다. 실제 LLM 기반 평가 시 점수가 달라질 수 있습니다.

---

*Generated by MLRag - 2026-02-10*
