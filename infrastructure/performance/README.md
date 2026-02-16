# Performance Testing Suite

## Hybrid RAG Knowledge Platform

STORY-081: Performance Baseline Testing

---

## Overview

This directory contains performance testing scripts and tools for the Hybrid RAG Knowledge Platform.
Two testing frameworks are supported:

1. **k6** - Modern load testing tool (JavaScript-based)
2. **Locust** - Distributed load testing (Python-based)

---

## Quick Start

### Prerequisites

```bash
# Install k6
# macOS
brew install k6

# Ubuntu/Debian
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg \
    --keyserver hkp://keyserver.ubuntu.com:80 \
    --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | \
    sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update && sudo apt-get install k6

# Windows (chocolatey)
choco install k6

# Install Locust
pip install -r requirements.txt
```

### Running Tests

```bash
# Using the test runner script (recommended)
cd infrastructure/scripts
./performance-test.sh --quick          # Quick smoke test
./performance-test.sh                   # Default load test
./performance-test.sh --full            # Full test suite
./performance-test.sh --tool locust     # Use Locust instead of k6

# Direct k6 execution
cd infrastructure/performance
k6 run k6-load-test.js

# Direct Locust execution
cd infrastructure/performance
locust -f locustfile.py --host=http://localhost:8000
```

---

## Test Files

| File | Description |
|------|-------------|
| `k6-load-test.js` | Main k6 load test script with multiple scenarios |
| `locustfile.py` | Locust test file with user classes |
| `requirements.txt` | Python dependencies for Locust |
| `README.md` | This documentation |

---

## Performance Targets

| Metric | Target | Acceptable |
|--------|--------|------------|
| API Response (P50) | < 500ms | < 1s |
| API Response (P95) | < 2s | < 3s |
| Search Latency (P95) | < 3s | < 5s |
| Throughput | > 100 req/s | > 50 req/s |
| Error Rate | < 0.1% | < 1% |

---

## k6 Test Scenarios

### 1. Smoke Test
Quick validation that endpoints are functional.
- 1 VU, 30 seconds

### 2. Load Test
Simulates normal production traffic.
- Ramp up to 100 VUs over 11 minutes
- Measures baseline performance

### 3. Stress Test
Finds system limits.
- 150 VUs for 6 minutes
- Identifies breaking points

### 4. Spike Test
Tests sudden traffic bursts.
- Sudden jump to 200 VUs
- Tests recovery capability

---

## Locust User Classes

### HybridRAGUser
Typical user behavior with mixed operations:
- 10% health checks
- 50% search operations
- 20% chat operations
- 20% document operations

### SearchHeavyUser
Focus on search performance:
- 100% search operations
- Higher request rate

### ChatHeavyUser
Focus on LLM operations:
- 100% chat operations
- Longer wait times

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BASE_URL` | `http://localhost:8000` | Target service URL |
| `API_PREFIX` | `/api/v1` | API path prefix |
| `AUTH_TOKEN` | (empty) | Bearer token for auth |

### k6 Options

```javascript
export const options = {
    thresholds: {
        http_req_duration: ['p(50)<500', 'p(95)<2000', 'p(99)<3000'],
        http_req_failed: ['rate<0.01'],
    },
};
```

---

## Output

### k6 Output

```bash
# JSON output
k6 run --out json=results.json k6-load-test.js

# Cloud output (k6 Cloud)
k6 run --out cloud k6-load-test.js
```

### Locust Output

```bash
# HTML report
locust -f locustfile.py --html report.html --headless

# CSV output
locust -f locustfile.py --csv results --headless
```

---

## Results Location

Test results are saved to:
```
knowledge_service/docs/results/performance/
  k6_results_YYYYMMDD_HHMMSS.json
  k6_summary_YYYYMMDD_HHMMSS.json
  locust_report_YYYYMMDD_HHMMSS.html
  locust_YYYYMMDD_HHMMSS_stats.csv
```

---

## Monitoring During Tests

### Grafana Dashboards
Access at `http://localhost:3001`

### Prometheus Metrics
Access at `http://localhost:9090`

### Jaeger Tracing
Access at `http://localhost:16686`

---

## Troubleshooting

### Service Not Reachable

```bash
# Check if service is running
curl http://localhost:8000/api/v1/health

# Check Docker containers
docker ps | grep kp-
```

### Auth Token Issues

```bash
# Get token from Keycloak
curl -X POST "http://localhost:8180/realms/hybrid-rag/protocol/openid-connect/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "grant_type=password" \
    -d "client_id=knowledge-frontend" \
    -d "username=testuser" \
    -d "password=testpass"
```

### k6 Memory Issues

```bash
# Increase memory limit
K6_OUT=json=results.json k6 run --no-connection-reuse k6-load-test.js
```

---

## Related Documents

- [Performance Baseline Report](../../knowledge_service/docs/04_testing/08_analysis/10_performance_baseline_report.md)
- [Infrastructure Design](../../knowledge_service/docs/02_design/10_infrastructure_detailed_design.md)
- [API Integration Design](../../knowledge_service/docs/02_design/04_api_integration_design.md)
