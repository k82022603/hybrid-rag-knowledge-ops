# STORY-090: PERF - Hybrid Search Latency 984ms > 500ms (CPU BGE-M3 Bottleneck)

## Story Information

| Item | Value |
|------|-------|
| **ID** | STORY-090 |
| **Jira** | SCRUM-86 |
| **Epic** | EPIC-005 RAG Quality & Performance |
| **Sprint** | Sprint 08 |
| **Points** | 2 |
| **Priority** | P3 - Low |
| **Assignee** | RAG/Infra |
| **Status** | Closed - Project Completed (2026-02-18) |

---

## Performance Issue Report

### Summary
During UAT Part B (2026-02-06), Hybrid Search end-to-end latency was measured at **984ms**, which exceeds the 500ms P95 target defined in the performance requirements.

### Environment
- CPU: Development machine (no GPU)
- BGE-M3 model: Running on CPU inference
- Elasticsearch: 1 node, local
- Neo4j: 1 node, local (graph search disabled due to STORY-088)

### Performance Breakdown

| Component | Latency (ms) | Percentage | Notes |
|-----------|-------------|------------|-------|
| BGE-M3 Embedding (CPU) | ~650 | 66% | **Primary bottleneck** |
| Elasticsearch Search | ~120 | 12% | Within target |
| RRF Fusion + Reranking | ~100 | 10% | Within target |
| Network/Overhead | ~114 | 12% | Acceptable |
| **Total** | **~984** | **100%** | Exceeds 500ms target |

### Root Cause
CPU-based BGE-M3 model inference is the primary bottleneck, consuming 66% of total latency. The model performs dense vector encoding on CPU which is inherently slow compared to GPU.

### Expected Resolution
In production GPU environment:
- BGE-M3 GPU inference: ~50ms (13x speedup)
- Expected total latency: ~384ms (well under 500ms target)

---

## Severity Assessment

| Factor | Assessment |
|--------|-----------|
| **Current Impact** | Medium - Development environment only |
| **Production Impact** | Low - GPU expected to resolve |
| **User Experience** | Acceptable for UAT (sub-1s) |
| **Risk** | Low - Well-understood bottleneck |

**Decision**: Categorized as P3 (Low) because this is a known CPU limitation that will be resolved in production GPU environment.

---

## Acceptance Criteria

- [ ] **Given** UAT measurements, **When** documenting baseline, **Then** CPU performance is recorded
- [ ] **Given** production GPU specs, **When** estimating improvement, **Then** GPU targets are defined
- [ ] **Given** GPU environment (if available), **When** running benchmark, **Then** latency < 500ms confirmed
- [ ] **Given** monitoring setup, **When** production deploys, **Then** latency dashboard tracks P50/P95/P99

---

## Tasks

- [ ] Document CPU baseline performance (this story provides the data)
- [ ] Define GPU performance targets
- [ ] Create monitoring dashboard for search latency
- [ ] (If GPU available) Run GPU benchmark and validate < 500ms
- [ ] Update performance test documentation

---

## Performance Targets

| Environment | P50 Target | P95 Target | Notes |
|-------------|-----------|-----------|-------|
| Development (CPU) | < 1000ms | < 1500ms | Baseline |
| Production (GPU) | < 200ms | < 500ms | Production target |
| Production (GPU, cached) | < 100ms | < 300ms | With query cache |

---

## References

- [Performance Requirements](../../knowledge_service/docs/02_design/12_rag_performance_test_design.md)
- [STORY-081 Performance Baseline Testing](./STORY-081-performance-baseline.md)
- [Sprint 07](../sprints/sprint-07.md)
