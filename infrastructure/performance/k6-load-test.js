/**
 * k6 Performance Test Script - Hybrid RAG Knowledge Platform
 *
 * STORY-081: Performance Baseline Testing
 *
 * Target Metrics:
 * - API Response P50: < 500ms
 * - API Response P95: < 2s (acceptable < 3s)
 * - Search Latency P95: < 3s (acceptable < 5s)
 * - Throughput: > 100 req/s (acceptable > 50 req/s)
 * - Error Rate: < 0.1% (acceptable < 1%)
 *
 * Usage:
 *   k6 run k6-load-test.js
 *   k6 run --vus 100 --duration 5m k6-load-test.js
 *   k6 run --out json=results.json k6-load-test.js
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { SharedArray } from 'k6/data';
import { randomItem } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';

// =============================================================================
// CONFIGURATION
// =============================================================================

// Environment variables with defaults
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const API_PREFIX = __ENV.API_PREFIX || '/api/v1';
const AUTH_TOKEN = __ENV.AUTH_TOKEN || '';

// Test scenarios
export const options = {
    scenarios: {
        // Scenario 1: Smoke Test (Quick validation)
        smoke: {
            executor: 'constant-vus',
            vus: 1,
            duration: '30s',
            startTime: '0s',
            tags: { scenario: 'smoke' },
        },

        // Scenario 2: Load Test (Normal traffic simulation)
        load: {
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '1m', target: 50 },   // Ramp up to 50 users
                { duration: '3m', target: 50 },   // Stay at 50 users
                { duration: '1m', target: 100 },  // Ramp up to 100 users
                { duration: '5m', target: 100 },  // Stay at 100 users (baseline)
                { duration: '1m', target: 0 },    // Ramp down
            ],
            startTime: '30s',
            tags: { scenario: 'load' },
        },

        // Scenario 3: Stress Test (Peak traffic)
        stress: {
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '2m', target: 150 },
                { duration: '3m', target: 150 },
                { duration: '1m', target: 0 },
            ],
            startTime: '11m',
            tags: { scenario: 'stress' },
        },

        // Scenario 4: Spike Test (Sudden traffic burst)
        spike: {
            executor: 'ramping-vus',
            startVUs: 50,
            stages: [
                { duration: '10s', target: 200 },  // Sudden spike
                { duration: '30s', target: 200 },  // Maintain spike
                { duration: '10s', target: 50 },   // Return to normal
            ],
            startTime: '17m',
            tags: { scenario: 'spike' },
        },
    },

    // Performance thresholds
    thresholds: {
        // Overall HTTP metrics
        http_req_duration: ['p(50)<500', 'p(95)<2000', 'p(99)<3000'],
        http_req_failed: ['rate<0.01'],  // Error rate < 1%

        // Health check specific
        'http_req_duration{endpoint:health}': ['p(95)<100'],

        // Search endpoints
        'http_req_duration{endpoint:search_hybrid}': ['p(95)<3000'],
        'http_req_duration{endpoint:search_semantic}': ['p(95)<3000'],
        'http_req_duration{endpoint:search_keyword}': ['p(95)<2000'],

        // Chat endpoint (LLM involved)
        'http_req_duration{endpoint:chat}': ['p(95)<5000'],

        // Document endpoints
        'http_req_duration{endpoint:documents}': ['p(95)<1000'],

        // Custom metrics
        'search_latency': ['p(95)<3000'],
        'error_rate': ['rate<0.01'],
    },
};

// =============================================================================
// CUSTOM METRICS
// =============================================================================

// Latency trends
const searchLatency = new Trend('search_latency', true);
const chatLatency = new Trend('chat_latency', true);
const documentLatency = new Trend('document_latency', true);

// Error counters
const errorRate = new Rate('error_rate');
const timeoutErrors = new Counter('timeout_errors');
const validationErrors = new Counter('validation_errors');

// Success counters
const successfulSearches = new Counter('successful_searches');
const successfulChats = new Counter('successful_chats');

// =============================================================================
// TEST DATA
// =============================================================================

// Sample search queries (Korean)
const searchQueries = new SharedArray('searchQueries', function() {
    return [
        '프로젝트 관리 방법론',
        '소프트웨어 개발 프로세스',
        '품질 관리 절차',
        '보안 정책 가이드라인',
        '시스템 아키텍처 설계',
        'API 연동 가이드',
        '데이터베이스 설계 원칙',
        '테스트 자동화 전략',
        '배포 파이프라인 구성',
        '모니터링 및 알림 설정',
        '장애 대응 프로세스',
        '코드 리뷰 체크리스트',
        '성능 최적화 기법',
        '클라우드 인프라 관리',
        '컨테이너 오케스트레이션',
    ];
});

// Sample chat questions (Korean)
const chatQuestions = new SharedArray('chatQuestions', function() {
    return [
        '프로젝트 일정 관리에서 가장 중요한 것은 무엇인가요?',
        'RAG 시스템의 장점을 설명해주세요.',
        '마이크로서비스 아키텍처의 특징은 무엇인가요?',
        'CI/CD 파이프라인 구축 방법을 알려주세요.',
        '코드 품질을 높이는 방법은 무엇인가요?',
    ];
});

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

function getHeaders() {
    const headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Accept-Language': 'ko-KR',
    };

    if (AUTH_TOKEN) {
        headers['Authorization'] = `Bearer ${AUTH_TOKEN}`;
    }

    return headers;
}

function handleResponse(res, endpoint, latencyMetric) {
    const success = res.status >= 200 && res.status < 400;
    errorRate.add(!success);

    if (latencyMetric) {
        latencyMetric.add(res.timings.duration);
    }

    if (res.status === 408 || res.timings.duration > 10000) {
        timeoutErrors.add(1);
    }

    if (res.status === 400 || res.status === 422) {
        validationErrors.add(1);
    }

    return success;
}

// =============================================================================
// TEST SCENARIOS
// =============================================================================

export default function() {
    const headers = getHeaders();

    // Health Check (10% of requests)
    if (Math.random() < 0.1) {
        group('Health Check', function() {
            const res = http.get(`${BASE_URL}${API_PREFIX}/health`, {
                headers: headers,
                tags: { endpoint: 'health' },
            });

            check(res, {
                'health check status is 200': (r) => r.status === 200,
                'health check has status field': (r) => {
                    try {
                        const body = JSON.parse(r.body);
                        return body.status !== undefined;
                    } catch (e) {
                        return false;
                    }
                },
            });
        });
    }

    // Search Operations (50% of requests)
    if (Math.random() < 0.5) {
        group('Search Operations', function() {
            const query = randomItem(searchQueries);
            const searchType = Math.random();

            if (searchType < 0.5) {
                // Hybrid Search (most common)
                const payload = JSON.stringify({
                    query: query,
                    top_k: 10,
                    useGraph: true,
                    useVector: true,
                });

                const res = http.post(`${BASE_URL}${API_PREFIX}/search/hybrid`, payload, {
                    headers: headers,
                    tags: { endpoint: 'search_hybrid' },
                    timeout: '10s',
                });

                const success = handleResponse(res, 'search_hybrid', searchLatency);

                check(res, {
                    'hybrid search status is 200': (r) => r.status === 200,
                    'hybrid search has results': (r) => {
                        try {
                            const body = JSON.parse(r.body);
                            return Array.isArray(body.results);
                        } catch (e) {
                            return false;
                        }
                    },
                });

                if (success) {
                    successfulSearches.add(1);
                }

            } else if (searchType < 0.8) {
                // Semantic Search
                const payload = JSON.stringify({
                    query: query,
                    top_k: 10,
                });

                const res = http.post(`${BASE_URL}${API_PREFIX}/search/semantic`, payload, {
                    headers: headers,
                    tags: { endpoint: 'search_semantic' },
                    timeout: '10s',
                });

                handleResponse(res, 'search_semantic', searchLatency);

                check(res, {
                    'semantic search status is 200': (r) => r.status === 200,
                });

            } else {
                // Keyword Search
                const payload = JSON.stringify({
                    query: query,
                    top_k: 10,
                });

                const res = http.post(`${BASE_URL}${API_PREFIX}/search/keyword`, payload, {
                    headers: headers,
                    tags: { endpoint: 'search_keyword' },
                    timeout: '5s',
                });

                handleResponse(res, 'search_keyword', searchLatency);

                check(res, {
                    'keyword search status is 200': (r) => r.status === 200,
                });
            }
        });
    }

    // Chat Operations (20% of requests)
    if (Math.random() < 0.2) {
        group('Chat Operations', function() {
            const question = randomItem(chatQuestions);

            const payload = JSON.stringify({
                query: question,
                topK: 5,
                useReasoner: false,
            });

            const res = http.post(`${BASE_URL}${API_PREFIX}/search/chat`, payload, {
                headers: headers,
                tags: { endpoint: 'chat' },
                timeout: '30s',  // LLM operations can take longer
            });

            const success = handleResponse(res, 'chat', chatLatency);

            check(res, {
                'chat status is 200': (r) => r.status === 200,
                'chat has answer': (r) => {
                    try {
                        const body = JSON.parse(r.body);
                        return body.answer && body.answer.length > 0;
                    } catch (e) {
                        return false;
                    }
                },
                'chat has sources': (r) => {
                    try {
                        const body = JSON.parse(r.body);
                        return Array.isArray(body.sources);
                    } catch (e) {
                        return false;
                    }
                },
            });

            if (success) {
                successfulChats.add(1);
            }
        });
    }

    // Document Operations (20% of requests)
    if (Math.random() < 0.2) {
        group('Document Operations', function() {
            // List documents
            const res = http.get(`${BASE_URL}${API_PREFIX}/documents?page=1&page_size=20`, {
                headers: headers,
                tags: { endpoint: 'documents' },
                timeout: '5s',
            });

            handleResponse(res, 'documents', documentLatency);

            check(res, {
                'documents list status is 200': (r) => r.status === 200,
                'documents list has items': (r) => {
                    try {
                        const body = JSON.parse(r.body);
                        return Array.isArray(body.documents);
                    } catch (e) {
                        return false;
                    }
                },
            });
        });
    }

    // Random sleep between 1-3 seconds to simulate realistic user behavior
    sleep(Math.random() * 2 + 1);
}

// =============================================================================
// LIFECYCLE HOOKS
// =============================================================================

export function setup() {
    console.log('='.repeat(60));
    console.log('Hybrid RAG Knowledge Platform - Performance Test');
    console.log('='.repeat(60));
    console.log(`Base URL: ${BASE_URL}`);
    console.log(`API Prefix: ${API_PREFIX}`);
    console.log(`Auth Token: ${AUTH_TOKEN ? 'Configured' : 'Not configured'}`);
    console.log('='.repeat(60));

    // Verify service is reachable
    const res = http.get(`${BASE_URL}${API_PREFIX}/health`, {
        timeout: '10s',
    });

    if (res.status !== 200) {
        console.error(`Service not reachable. Status: ${res.status}`);
        console.error(`Response: ${res.body}`);
    } else {
        console.log('Service health check passed');
    }

    return { startTime: Date.now() };
}

export function teardown(data) {
    const duration = (Date.now() - data.startTime) / 1000;
    console.log('='.repeat(60));
    console.log(`Test completed in ${duration.toFixed(2)} seconds`);
    console.log('='.repeat(60));
}

// =============================================================================
// SUMMARY HANDLER
// =============================================================================

export function handleSummary(data) {
    const summary = {
        timestamp: new Date().toISOString(),
        platform: 'Hybrid RAG Knowledge Platform',
        testDuration: data.state.testRunDurationMs / 1000,

        metrics: {
            http_reqs: {
                count: data.metrics.http_reqs?.values?.count || 0,
                rate: data.metrics.http_reqs?.values?.rate || 0,
            },
            http_req_duration: {
                avg: data.metrics.http_req_duration?.values?.avg || 0,
                p50: data.metrics.http_req_duration?.values?.['p(50)'] || 0,
                p90: data.metrics.http_req_duration?.values?.['p(90)'] || 0,
                p95: data.metrics.http_req_duration?.values?.['p(95)'] || 0,
                p99: data.metrics.http_req_duration?.values?.['p(99)'] || 0,
                max: data.metrics.http_req_duration?.values?.max || 0,
            },
            http_req_failed: {
                rate: data.metrics.http_req_failed?.values?.rate || 0,
            },
            error_rate: {
                rate: data.metrics.error_rate?.values?.rate || 0,
            },
            search_latency: {
                avg: data.metrics.search_latency?.values?.avg || 0,
                p95: data.metrics.search_latency?.values?.['p(95)'] || 0,
            },
            chat_latency: {
                avg: data.metrics.chat_latency?.values?.avg || 0,
                p95: data.metrics.chat_latency?.values?.['p(95)'] || 0,
            },
        },

        thresholds: data.thresholds,
    };

    return {
        'stdout': textSummary(data, { indent: '  ', enableColors: true }),
        './performance-results.json': JSON.stringify(summary, null, 2),
        './performance-results.html': htmlReport(data),
    };
}

// Helper functions for summary output
function textSummary(data, options) {
    let output = '\n';
    output += '='.repeat(60) + '\n';
    output += 'PERFORMANCE TEST RESULTS\n';
    output += '='.repeat(60) + '\n\n';

    output += 'HTTP Request Duration:\n';
    output += `  P50: ${(data.metrics.http_req_duration?.values?.['p(50)'] || 0).toFixed(2)}ms\n`;
    output += `  P95: ${(data.metrics.http_req_duration?.values?.['p(95)'] || 0).toFixed(2)}ms\n`;
    output += `  P99: ${(data.metrics.http_req_duration?.values?.['p(99)'] || 0).toFixed(2)}ms\n\n`;

    output += 'Throughput:\n';
    output += `  Requests: ${data.metrics.http_reqs?.values?.count || 0}\n`;
    output += `  Rate: ${(data.metrics.http_reqs?.values?.rate || 0).toFixed(2)} req/s\n\n`;

    output += 'Error Rate:\n';
    output += `  Failed: ${((data.metrics.http_req_failed?.values?.rate || 0) * 100).toFixed(4)}%\n\n`;

    output += 'Search Latency (P95):\n';
    output += `  ${(data.metrics.search_latency?.values?.['p(95)'] || 0).toFixed(2)}ms\n\n`;

    output += '='.repeat(60) + '\n';

    return output;
}

function htmlReport(data) {
    const p50 = (data.metrics.http_req_duration?.values?.['p(50)'] || 0).toFixed(2);
    const p95 = (data.metrics.http_req_duration?.values?.['p(95)'] || 0).toFixed(2);
    const p99 = (data.metrics.http_req_duration?.values?.['p(99)'] || 0).toFixed(2);
    const reqCount = data.metrics.http_reqs?.values?.count || 0;
    const reqRate = (data.metrics.http_reqs?.values?.rate || 0).toFixed(2);
    const errorRate = ((data.metrics.http_req_failed?.values?.rate || 0) * 100).toFixed(4);
    const searchP95 = (data.metrics.search_latency?.values?.['p(95)'] || 0).toFixed(2);

    return `<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Performance Test Results - Hybrid RAG Platform</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }
        .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 30px 0; }
        .metric-card { background: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #007bff; }
        .metric-card h3 { margin: 0 0 10px 0; color: #666; font-size: 14px; text-transform: uppercase; }
        .metric-card .value { font-size: 28px; font-weight: bold; color: #333; }
        .metric-card .unit { font-size: 14px; color: #666; }
        .status-pass { border-left-color: #28a745; }
        .status-fail { border-left-color: #dc3545; }
        .threshold-table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        .threshold-table th, .threshold-table td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        .threshold-table th { background: #f8f9fa; }
        .badge { padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
        .badge-success { background: #d4edda; color: #155724; }
        .badge-danger { background: #f8d7da; color: #721c24; }
        footer { margin-top: 40px; text-align: center; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Performance Test Results</h1>
        <p>Hybrid RAG Knowledge Platform - Generated at ${new Date().toISOString()}</p>

        <div class="metrics">
            <div class="metric-card ${parseFloat(p50) < 500 ? 'status-pass' : 'status-fail'}">
                <h3>Response Time (P50)</h3>
                <div class="value">${p50}<span class="unit">ms</span></div>
                <small>Target: < 500ms</small>
            </div>
            <div class="metric-card ${parseFloat(p95) < 2000 ? 'status-pass' : 'status-fail'}">
                <h3>Response Time (P95)</h3>
                <div class="value">${p95}<span class="unit">ms</span></div>
                <small>Target: < 2000ms</small>
            </div>
            <div class="metric-card ${parseFloat(searchP95) < 3000 ? 'status-pass' : 'status-fail'}">
                <h3>Search Latency (P95)</h3>
                <div class="value">${searchP95}<span class="unit">ms</span></div>
                <small>Target: < 3000ms</small>
            </div>
            <div class="metric-card ${parseFloat(reqRate) > 50 ? 'status-pass' : 'status-fail'}">
                <h3>Throughput</h3>
                <div class="value">${reqRate}<span class="unit">req/s</span></div>
                <small>Target: > 100 req/s</small>
            </div>
            <div class="metric-card ${parseFloat(errorRate) < 1 ? 'status-pass' : 'status-fail'}">
                <h3>Error Rate</h3>
                <div class="value">${errorRate}<span class="unit">%</span></div>
                <small>Target: < 0.1%</small>
            </div>
            <div class="metric-card">
                <h3>Total Requests</h3>
                <div class="value">${reqCount}</div>
            </div>
        </div>

        <h2>Performance Targets</h2>
        <table class="threshold-table">
            <thead>
                <tr>
                    <th>Metric</th>
                    <th>Target</th>
                    <th>Acceptable</th>
                    <th>Actual</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>API Response (P50)</td>
                    <td>< 500ms</td>
                    <td>< 1s</td>
                    <td>${p50}ms</td>
                    <td><span class="badge ${parseFloat(p50) < 500 ? 'badge-success' : 'badge-danger'}">${parseFloat(p50) < 500 ? 'PASS' : 'FAIL'}</span></td>
                </tr>
                <tr>
                    <td>API Response (P95)</td>
                    <td>< 2s</td>
                    <td>< 3s</td>
                    <td>${p95}ms</td>
                    <td><span class="badge ${parseFloat(p95) < 2000 ? 'badge-success' : (parseFloat(p95) < 3000 ? 'badge-success' : 'badge-danger')}">${parseFloat(p95) < 2000 ? 'PASS' : (parseFloat(p95) < 3000 ? 'ACCEPTABLE' : 'FAIL')}</span></td>
                </tr>
                <tr>
                    <td>Search Latency (P95)</td>
                    <td>< 3s</td>
                    <td>< 5s</td>
                    <td>${searchP95}ms</td>
                    <td><span class="badge ${parseFloat(searchP95) < 3000 ? 'badge-success' : 'badge-danger'}">${parseFloat(searchP95) < 3000 ? 'PASS' : 'FAIL'}</span></td>
                </tr>
                <tr>
                    <td>Throughput</td>
                    <td>> 100 req/s</td>
                    <td>> 50 req/s</td>
                    <td>${reqRate} req/s</td>
                    <td><span class="badge ${parseFloat(reqRate) > 100 ? 'badge-success' : (parseFloat(reqRate) > 50 ? 'badge-success' : 'badge-danger')}">${parseFloat(reqRate) > 100 ? 'PASS' : (parseFloat(reqRate) > 50 ? 'ACCEPTABLE' : 'FAIL')}</span></td>
                </tr>
                <tr>
                    <td>Error Rate</td>
                    <td>< 0.1%</td>
                    <td>< 1%</td>
                    <td>${errorRate}%</td>
                    <td><span class="badge ${parseFloat(errorRate) < 0.1 ? 'badge-success' : (parseFloat(errorRate) < 1 ? 'badge-success' : 'badge-danger')}">${parseFloat(errorRate) < 0.1 ? 'PASS' : (parseFloat(errorRate) < 1 ? 'ACCEPTABLE' : 'FAIL')}</span></td>
                </tr>
            </tbody>
        </table>

        <footer>
            <p>Generated by k6 Performance Test Suite - STORY-081</p>
        </footer>
    </div>
</body>
</html>`;
}
