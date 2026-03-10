# k6 Smoke Test Results

**Date**: 2026-03-10
**Environment**: WSL2 (14GB RAM), AI Service localhost:8000
**k6 Version**: v0.50.0
**Test Mode**: Smoke (1 VU, minimal load)

---

## 1. Auth API Smoke Test

**Duration**: 30s | **VUs**: 1 | **Iterations**: 23

### Results: ALL PASS

| Check | Result | Pass Rate |
|-------|--------|-----------|
| login status is 200 | PASS | 100% |
| login has accessToken | PASS | 100% |
| login latency < 1s | PASS | 100% |
| me status is 200 | PASS | 100% |
| me has user data | PASS | 100% |
| me latency < 1s | PASS | 100% |
| refresh status is 200 | PASS | 100% |
| refresh has new token | PASS | 100% |
| refresh latency < 1s | PASS | 100% |
| invalid login returns 401 | PASS | 100% |

### Latency Metrics

| Metric | avg | min | med | p90 | p95 | p99 | max |
|--------|-----|-----|-----|-----|-----|-----|-----|
| login_latency_ms | 399ms | 194ms | 447ms | 506ms | 516ms | 532ms | 536ms |
| auth_latency_ms | 2.3ms | 0.7ms | 1.9ms | 3.4ms | 4.9ms | 10ms | 12ms |
| http_req_duration | 102ms | 0.7ms | 2.3ms | 463ms | 495ms | 519ms | 536ms |

### Throughput

| Metric | Value |
|--------|-------|
| Total Requests | 92 |
| Requests/sec | 2.98 |
| Iterations/sec | 0.74 |
| Success Rate | 100% |
| Data Received | 43 KB (1.4 KB/s) |

### Threshold Results

| Threshold | Criteria | Actual | Status |
|-----------|----------|--------|--------|
| login_latency_ms p95 | < 1000ms | 516ms | PASS |
| login_latency_ms p99 | < 2000ms | 532ms | PASS |
| auth_latency_ms p95 | < 1000ms | 4.9ms | PASS |
| auth_latency_ms p99 | < 2000ms | 10ms | PASS |
| auth_success_rate | > 95% | 100% | PASS |
| http_req_duration p95 | < 2000ms | 495ms | PASS |

---

## 2. Search API Smoke Test

**Duration**: 2m (+ 31s graceful stop) | **VUs**: 1 | **Iterations**: 5 (4 complete + 1 interrupted)

### Results: PARTIAL PASS

| Check | Result | Pass Rate |
|-------|--------|-----------|
| hybrid search 200 | PARTIAL | 60% (3/5) |
| hybrid has results | PARTIAL | 60% (3/5) |
| semantic search 200 | PASS | 100% (5/5) |
| keyword search 200 | PASS | 100% (5/5) |

### Per-Request Timings (from console logs)

| # | Hybrid | Semantic | Keyword |
|---|--------|----------|---------|
| 1 | 22ms (cached) | 2,401ms | 296ms |
| 2 | 11ms (cached) | 1,995ms | 215ms |
| 3 | 34ms | 218ms (cached) | 173ms |
| 4 | TIMEOUT 60s | 4,377ms | 4,810ms |
| 5 | TIMEOUT 60s | (interrupted) | (interrupted) |

### Latency Metrics

| Metric | avg | min | med | p90 | p95 | p99 | max |
|--------|-----|-----|-----|-----|-----|-----|-----|
| hybrid_latency_ms | 24.2s | 11ms | 34ms | 60s | 60s | 60s | 60s |
| semantic_latency_ms | 2.24s | 218ms | 2.19s | 3.78s | 4.08s | 4.31s | 4.37s |
| keyword_latency_ms | 1.37s | 173ms | 255ms | 3.45s | 4.13s | 4.67s | 4.81s |

### Threshold Results

| Threshold | Criteria | Actual | Status |
|-----------|----------|--------|--------|
| hybrid_latency_ms p95 | < 15000ms | 60000ms | FAIL |
| semantic_latency_ms p95 | < 5000ms | 4080ms | PASS |
| keyword_latency_ms p95 | < 3000ms | 4130ms | FAIL |
| search_success_rate | > 80% | 60% | FAIL |
| http_req_duration p95 | < 15000ms | 60000ms | FAIL |

---

## 3. Analysis

### Auth API: Excellent

- All 11 check types pass at 100%
- Login latency p95 = 516ms (well under 1s target)
- Token refresh and /me endpoints respond in < 5ms consistently
- Invalid login correctly returns 401

### Search API: Performance Issues Identified

**Issue 1: Hybrid Search Intermittent Timeout (CRITICAL)**
- 2 out of 5 hybrid search requests timed out at 60 seconds
- When working, hybrid search responds in 11-34ms (cache hit from Elasticsearch)
- Timeout pattern: iteration 4 and 5 both fail, suggesting resource exhaustion
- Hypothesis: Reranker model (ONNX, CPU-bound, 2-core limit) becomes unresponsive
  under sustained load, causing the hybrid pipeline to hang

**Issue 2: Semantic Search Variable Latency**
- Range: 218ms to 4,377ms (20x variation)
- First 2 calls: ~2s (embedding computation), 3rd: 218ms (cached), 4th: 4.4s (after hybrid timeout)

**Issue 3: Keyword Search Spike After Hybrid Timeout**
- Normal: 173-296ms, After hybrid timeout: 4,810ms
- Suggests shared resource contention (ES or Reranker)

### Root Cause Hypothesis

The hybrid search timeout correlates with the reranker's ONNX model becoming
resource-starved in the 14GB WSL2 environment. When the reranker hangs:
1. Hybrid search blocks waiting for reranking
2. Semantic and keyword searches also slow down due to shared CPU/memory pressure
3. After the timeout releases, other endpoints recover

---

## 4. Recommendations

1. **Monitor reranker health**: Add timeout to reranker calls (currently 60s in config)
2. **Consider circuit breaker**: If reranker fails, fall back to non-reranked results
3. **WSL2 memory**: 14GB is tight with 23 active containers; consider reducing container count
4. **Cache warming**: Pre-warm the hybrid search pipeline on service startup
5. **Separate load test run**: Run with more memory (e.g., 16-20GB) to confirm if this is
   purely a resource constraint issue

---

## 5. k6 Script Notes

**API Response Structure Mismatch (Fixed in smoke scripts)**:
The original k6 scripts expected `body.data.accessToken` but the actual API returns
`body.accessToken` (no `data` wrapper). Smoke test scripts were adapted accordingly.

**Original scripts location**:
- `knowledge_service/src/tests/performance/k6_auth_test.js`
- `knowledge_service/src/tests/performance/k6_search_test.js`
- `knowledge_service/src/tests/performance/k6_chat_test.js`

These original scripts need to be updated to match the actual API response structure
before they can be used in CI/CD pipelines.

---

## 6. Raw k6 Output Files

- Auth: `/tmp/k6_auth_result.txt`
- Search (run 1 - cold): `/tmp/k6_search_result.txt`
- Search (run 2 - warm): `/tmp/k6_search_result_v2.txt`
