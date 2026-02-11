# STORY-086: Terminal Retriever + Performance Measurement Tool

## Story Information

| Item | Value |
|------|-------|
| **ID** | STORY-086 |
| **Jira** | SCRUM-82 |
| **Epic** | EPIC-005 RAG Quality & Performance |
| **Sprint** | Sprint 08 |
| **Points** | 5 |
| **Priority** | P1 - High |
| **Assignee** | RAG |
| **Status** | Done |

---

## Background

UAT Part B identified the need for a CLI-based retrieval testing tool that can directly query the search pipeline without going through the UI. This tool is essential for performance benchmarking, debugging, and regression testing of the RAG pipeline.

---

## User Story

**As a** developer/QA engineer,
**I want** a terminal-based retriever tool with performance metrics,
**So that** I can quickly test search quality and measure latency without the UI.

---

## Acceptance Criteria

- [x] **Given** a search query via CLI, **When** executing the retriever, **Then** search results are displayed in terminal
- [x] **Given** a search execution, **When** performance metrics are collected, **Then** latency breakdown is shown (embedding, search, rerank, LLM)
- [x] **Given** batch queries, **When** running benchmark mode, **Then** aggregate statistics are computed (P50, P95, P99)
- [x] **Given** benchmark results, **When** export is requested, **Then** CSV/JSON output is generated

---

## Tasks

- [x] CLI interface design (argparse)
- [x] Direct connection to AI Service search pipeline
- [x] Performance timer instrumentation at each pipeline stage
- [x] Batch query mode for benchmarking
- [x] Result formatting (Markdown, JSON, CSV)
- [x] Documentation (usage guide in docstring)

---

## Technical Notes

### Architecture
```
terminal_retriever.py
  |-- connect to AI Service (HTTP or direct)
  |-- send query
  |-- collect stage-level timing
  |-- display results + metrics
```

### Planned Output Format
```
Query: "Knowledge Graph embedding"
Results: 5 documents found (984ms total)

  Breakdown:
    Embedding:  650ms (66%)
    ES Search:  120ms (12%)
    Reranking:  100ms (10%)
    Overhead:   114ms (12%)

  Top 3 Results:
    1. [0.92] Document A - Chunk 3 (slide 12)
    2. [0.87] Document B - Chunk 1 (slide 5)
    3. [0.81] Document C - Chunk 7 (slide 23)
```

---

## References

- [RAG Performance Test Design](../../knowledge_service/docs/02_design/12_rag_performance_test_design.md)
