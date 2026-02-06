# Performance Benchmark Report

**Date**: 2026-02-06 16:25:25
**AI Service**: http://localhost:8000
**ES**: http://localhost:9200

---

## Summary

| Metric | Avg | Min | Max | P95 | Threshold | Result |
|--------|-----|-----|-----|-----|-----------|--------|
| Hybrid Search | 962ms | 896ms | 1063ms | 1063ms | <500ms | **FAIL** |
| Document Upload | 113ms | 46ms | 275ms | 275ms | <3000ms | **PASS** |
| ES kNN (pure) | 9ms | 7ms | 11ms | 11ms | <100ms | **PASS** |
| Token Auth | 444ms | 228ms | 585ms | 585ms | <2000ms | **PASS** |

**Overall**: 3/4 PASS

## Hybrid Search (5 iterations)

| # | Time |
|---|------|
| 1 | 976ms |
| 2 | 900ms |
| 3 | 896ms |
| 4 | 975ms |
| 5 | 1063ms |

## Document Upload (5 iterations)

| # | Time |
|---|------|
| 1 | 275ms |
| 2 | 94ms |
| 3 | 46ms |
| 4 | 66ms |
| 5 | 85ms |

## ES kNN (pure) (5 iterations)

| # | Time |
|---|------|
| 1 | 11ms |
| 2 | 8ms |
| 3 | 7ms |
| 4 | 9ms |
| 5 | 7ms |

## Token Auth (5 iterations)

| # | Time |
|---|------|
| 1 | 560ms |
| 2 | 585ms |
| 3 | 582ms |
| 4 | 263ms |
| 5 | 228ms |
