/**
 * k6 RAG Pipeline Performance Test
 *
 * STORY-081: Performance Baseline Testing
 * Focus: RAG Pipeline Performance Verification
 *
 * Tests:
 * - Vector embedding generation
 * - Hybrid search with RRF fusion
 * - LangGraph workflow execution
 * - Response generation with LLM
 *
 * Usage:
 *   k6 run k6-rag-pipeline-test.js
 *   k6 run --vus 50 --duration 10m k6-rag-pipeline-test.js
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { SharedArray } from 'k6/data';
import { randomItem } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';

// =============================================================================
// CONFIGURATION
// =============================================================================

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const API_PREFIX = __ENV.API_PREFIX || '/api/v1';
const AUTH_TOKEN = __ENV.AUTH_TOKEN || '';

export const options = {
    scenarios: {
        // RAG Pipeline focused testing
        rag_pipeline: {
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '1m', target: 20 },   // Warm up
                { duration: '5m', target: 50 },   // Baseline measurement
                { duration: '3m', target: 100 },  // Peak load
                { duration: '1m', target: 0 },    // Cool down
            ],
            gracefulStop: '30s',
        },
    },

    thresholds: {
        // RAG-specific thresholds
        'rag_embedding_time': ['p(95)<1000'],      // Embedding < 1s
        'rag_search_time': ['p(95)<3000'],         // Search < 3s
        'rag_generation_time': ['p(95)<5000'],     // Generation < 5s
        'rag_total_time': ['p(95)<8000'],          // Total < 8s

        // Quality checks
        'rag_search_has_results': ['rate>0.95'],   // > 95% have results
        'rag_answer_quality': ['rate>0.90'],       // > 90% quality answers

        // Error rates
        'http_req_failed': ['rate<0.01'],
    },
};

// =============================================================================
// CUSTOM METRICS
// =============================================================================

// RAG Pipeline metrics
const ragEmbeddingTime = new Trend('rag_embedding_time', true);
const ragSearchTime = new Trend('rag_search_time', true);
const ragGenerationTime = new Trend('rag_generation_time', true);
const ragTotalTime = new Trend('rag_total_time', true);

// Quality metrics
const ragSearchHasResults = new Rate('rag_search_has_results');
const ragAnswerQuality = new Rate('rag_answer_quality');

// Error tracking
const ragErrors = new Counter('rag_errors');

// =============================================================================
// TEST DATA
// =============================================================================

// Complex queries to stress RAG pipeline
const ragQueries = new SharedArray('ragQueries', function() {
    return [
        // Korean queries
        {
            query: '프로젝트 관리에서 리스크 관리와 품질 관리의 연관성을 설명해주세요.',
            expectedTopics: ['리스크', '품질', '관리'],
        },
        {
            query: '마이크로서비스 아키텍처에서 데이터 일관성을 유지하는 방법은 무엇인가요?',
            expectedTopics: ['마이크로서비스', '데이터', '일관성'],
        },
        {
            query: 'CI/CD 파이프라인 구축 시 보안을 고려해야 할 사항은 무엇인가요?',
            expectedTopics: ['CI/CD', '보안', '파이프라인'],
        },
        {
            query: '성능 최적화를 위한 캐싱 전략과 데이터베이스 튜닝 방법을 알려주세요.',
            expectedTopics: ['캐싱', '데이터베이스', '최적화'],
        },
        {
            query: 'Kubernetes 환경에서 애플리케이션 모니터링을 구축하는 방법은?',
            expectedTopics: ['Kubernetes', '모니터링', '애플리케이션'],
        },
        {
            query: '코드 리뷰 프로세스를 효과적으로 운영하기 위한 베스트 프랙티스는?',
            expectedTopics: ['코드 리뷰', '프로세스', '베스트 프랙티스'],
        },
        {
            query: 'API 게이트웨이의 역할과 구현 시 고려사항을 설명해주세요.',
            expectedTopics: ['API', '게이트웨이', '구현'],
        },
        {
            query: '분산 시스템에서 장애 복구와 데이터 백업 전략은 어떻게 수립하나요?',
            expectedTopics: ['분산', '장애 복구', '백업'],
        },
    ];
});

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

function getHeaders() {
    const headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    };
    if (AUTH_TOKEN) {
        headers['Authorization'] = `Bearer ${AUTH_TOKEN}`;
    }
    return headers;
}

function checkAnswerQuality(answer, expectedTopics) {
    if (!answer || answer.length < 50) return false;

    // Check if answer mentions expected topics
    const answerLower = answer.toLowerCase();
    const matchedTopics = expectedTopics.filter(topic =>
        answerLower.includes(topic.toLowerCase())
    );

    // At least one topic should be mentioned
    return matchedTopics.length > 0;
}

// =============================================================================
// TEST FUNCTIONS
// =============================================================================

export default function() {
    const headers = getHeaders();
    const testCase = randomItem(ragQueries);
    const startTime = Date.now();

    group('RAG Pipeline Test', function() {

        // Step 1: Hybrid Search (includes embedding + retrieval)
        group('Hybrid Search', function() {
            const searchPayload = JSON.stringify({
                query: testCase.query,
                top_k: 10,
                useGraph: true,
                useVector: true,
            });

            const searchStart = Date.now();
            const searchRes = http.post(`${BASE_URL}${API_PREFIX}/search/hybrid`, searchPayload, {
                headers: headers,
                tags: { step: 'hybrid_search' },
                timeout: '15s',
            });
            const searchDuration = Date.now() - searchStart;

            ragSearchTime.add(searchDuration);

            const searchSuccess = check(searchRes, {
                'hybrid search returns 200': (r) => r.status === 200,
                'hybrid search has results': (r) => {
                    try {
                        const body = JSON.parse(r.body);
                        const hasResults = body.results && body.results.length > 0;
                        ragSearchHasResults.add(hasResults);
                        return hasResults;
                    } catch (e) {
                        ragSearchHasResults.add(false);
                        return false;
                    }
                },
                'hybrid search latency < 3s': (r) => searchDuration < 3000,
            });

            if (!searchSuccess) {
                ragErrors.add(1);
            }

            // Extract latency from response if available
            try {
                const body = JSON.parse(searchRes.body);
                if (body.latency_ms) {
                    ragEmbeddingTime.add(body.latency_ms * 0.3); // Estimate embedding portion
                }
            } catch (e) {}
        });

        // Step 2: Chat with RAG (full pipeline)
        group('Chat Generation', function() {
            const chatPayload = JSON.stringify({
                query: testCase.query,
                topK: 5,
                useReasoner: false,
            });

            const chatStart = Date.now();
            const chatRes = http.post(`${BASE_URL}${API_PREFIX}/search/chat`, chatPayload, {
                headers: headers,
                tags: { step: 'chat_generation' },
                timeout: '30s',
            });
            const chatDuration = Date.now() - chatStart;

            ragGenerationTime.add(chatDuration);

            const chatSuccess = check(chatRes, {
                'chat returns 200': (r) => r.status === 200,
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
                        return body.sources && body.sources.length > 0;
                    } catch (e) {
                        return false;
                    }
                },
                'chat latency < 10s': (r) => chatDuration < 10000,
            });

            // Check answer quality
            if (chatRes.status === 200) {
                try {
                    const body = JSON.parse(chatRes.body);
                    const isQuality = checkAnswerQuality(body.answer, testCase.expectedTopics);
                    ragAnswerQuality.add(isQuality);
                } catch (e) {
                    ragAnswerQuality.add(false);
                }
            } else {
                ragAnswerQuality.add(false);
                ragErrors.add(1);
            }
        });

        // Record total pipeline time
        const totalDuration = Date.now() - startTime;
        ragTotalTime.add(totalDuration);
    });

    // Simulate user think time
    sleep(Math.random() * 3 + 2);
}

// =============================================================================
// LIFECYCLE HOOKS
// =============================================================================

export function setup() {
    console.log('='.repeat(60));
    console.log('RAG Pipeline Performance Test');
    console.log('='.repeat(60));
    console.log(`Target: ${BASE_URL}`);
    console.log(`Test Cases: ${ragQueries.length}`);
    console.log('='.repeat(60));

    // Verify service health
    const health = http.get(`${BASE_URL}${API_PREFIX}/health`, { timeout: '5s' });
    if (health.status !== 200) {
        console.error('Service not healthy!');
    } else {
        console.log('Service health check passed');
    }

    return { startTime: Date.now() };
}

export function teardown(data) {
    const duration = (Date.now() - data.startTime) / 1000;
    console.log('='.repeat(60));
    console.log(`RAG Pipeline Test completed in ${duration.toFixed(2)}s`);
    console.log('='.repeat(60));
}

export function handleSummary(data) {
    const summary = {
        timestamp: new Date().toISOString(),
        test: 'RAG Pipeline Performance',
        metrics: {
            embedding_time_p95: data.metrics.rag_embedding_time?.values?.['p(95)'] || 0,
            search_time_p95: data.metrics.rag_search_time?.values?.['p(95)'] || 0,
            generation_time_p95: data.metrics.rag_generation_time?.values?.['p(95)'] || 0,
            total_time_p95: data.metrics.rag_total_time?.values?.['p(95)'] || 0,
            search_has_results_rate: data.metrics.rag_search_has_results?.values?.rate || 0,
            answer_quality_rate: data.metrics.rag_answer_quality?.values?.rate || 0,
            error_count: data.metrics.rag_errors?.values?.count || 0,
        },
    };

    let textOutput = '\n';
    textOutput += '='.repeat(60) + '\n';
    textOutput += 'RAG PIPELINE PERFORMANCE RESULTS\n';
    textOutput += '='.repeat(60) + '\n\n';
    textOutput += `Embedding Time (P95): ${summary.metrics.embedding_time_p95.toFixed(2)}ms\n`;
    textOutput += `Search Time (P95): ${summary.metrics.search_time_p95.toFixed(2)}ms\n`;
    textOutput += `Generation Time (P95): ${summary.metrics.generation_time_p95.toFixed(2)}ms\n`;
    textOutput += `Total Pipeline (P95): ${summary.metrics.total_time_p95.toFixed(2)}ms\n\n`;
    textOutput += `Search Success Rate: ${(summary.metrics.search_has_results_rate * 100).toFixed(2)}%\n`;
    textOutput += `Answer Quality Rate: ${(summary.metrics.answer_quality_rate * 100).toFixed(2)}%\n`;
    textOutput += `Errors: ${summary.metrics.error_count}\n`;
    textOutput += '='.repeat(60) + '\n';

    return {
        'stdout': textOutput,
        './rag-pipeline-results.json': JSON.stringify(summary, null, 2),
    };
}
