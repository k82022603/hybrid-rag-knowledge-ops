/**
 * k6 Search API Performance Test
 *
 * Hybrid RAG Knowledge Platform - Search API 부하 테스트
 *
 * 시나리오:
 *   - smoke: 1 VU, 30초 (기본 동작 확인)
 *   - load:  10 VU, 2분 (일반 부하)
 *   - stress: 50 VU, 5분 (스트레스 테스트)
 *
 * 실행 예시:
 *   k6 run --env SCENARIO=smoke k6_search_test.js
 *   k6 run --env SCENARIO=load k6_search_test.js
 *   k6 run --env SCENARIO=stress k6_search_test.js
 *
 * STORY-129: k6 성능 회귀 테스트 스크립트
 */

import http from "k6/http";
import { check, sleep, group } from "k6";
import { Counter, Rate, Trend } from "k6/metrics";

// ---------------------------------------------------------------------------
// Custom Metrics
// ---------------------------------------------------------------------------
const searchLatency = new Trend("search_latency_ms", true);
const searchErrors = new Counter("search_errors");
const searchSuccessRate = new Rate("search_success_rate");

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------
const BASE_URL = __ENV.BASE_URL || "http://localhost:8080";
const AUTH_EMAIL = __ENV.AUTH_EMAIL || "admin@example.com";
const AUTH_PASSWORD = __ENV.AUTH_PASSWORD || "admin123!";

const SCENARIO = __ENV.SCENARIO || "smoke";

const scenarios = {
  smoke: {
    executor: "constant-vus",
    vus: 1,
    duration: "30s",
  },
  load: {
    executor: "constant-vus",
    vus: 10,
    duration: "2m",
  },
  stress: {
    executor: "ramping-vus",
    startVUs: 0,
    stages: [
      { duration: "30s", target: 10 },
      { duration: "2m", target: 50 },
      { duration: "1m", target: 50 },
      { duration: "1m30s", target: 0 },
    ],
  },
};

export const options = {
  scenarios: {
    search_test: scenarios[SCENARIO] || scenarios.smoke,
  },
  thresholds: {
    // Search API: p95 < 5s
    search_latency_ms: ["p(95)<5000", "p(99)<10000"],
    // Error rate < 5%
    search_success_rate: ["rate>0.95"],
    // HTTP request duration
    http_req_duration: ["p(95)<5000"],
  },
  // No summary to stdout when running in CI
  summaryTrendStats: ["avg", "min", "med", "max", "p(90)", "p(95)", "p(99)"],
};

// ---------------------------------------------------------------------------
// Test Queries (domain-specific)
// ---------------------------------------------------------------------------
const SEARCH_QUERIES = [
  "정보보호 정책 개요",
  "네트워크 보안 관리 절차",
  "개인정보보호법 준수 방안",
  "클라우드 보안 아키텍처",
  "접근제어 정책",
  "RAG 파이프라인 구성",
  "Knowledge Graph 엔티티 추출",
  "Hybrid Search 검색 최적화",
  "임베딩 모델 성능 비교",
  "보안 사고 대응 절차",
];

// ---------------------------------------------------------------------------
// Setup: Login and get auth token
// ---------------------------------------------------------------------------
export function setup() {
  const loginUrl = `${BASE_URL}/api/v1/auth/login`;
  const payload = JSON.stringify({
    email: AUTH_EMAIL,
    password: AUTH_PASSWORD,
  });

  const params = {
    headers: { "Content-Type": "application/json" },
    timeout: "10s",
  };

  const res = http.post(loginUrl, payload, params);

  const loginSuccess = check(res, {
    "login status is 200": (r) => r.status === 200,
    "login has accessToken": (r) => {
      try {
        const body = JSON.parse(r.body);
        return !!body.accessToken;
      } catch (e) {
        return false;
      }
    },
  });

  if (!loginSuccess) {
    console.error(`Login failed: status=${res.status}, body=${res.body}`);
    return { token: null };
  }

  const data = JSON.parse(res.body);
  const token = data.accessToken;
  console.log(`Login successful. Token obtained (length: ${token.length})`);

  return { token: token };
}

// ---------------------------------------------------------------------------
// Main Test: Search API
// ---------------------------------------------------------------------------
export default function (data) {
  if (!data.token) {
    console.error("No auth token available. Skipping test iteration.");
    searchErrors.add(1);
    return;
  }

  const headers = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${data.token}`,
  };

  group("Hybrid Search", function () {
    const query = SEARCH_QUERIES[Math.floor(Math.random() * SEARCH_QUERIES.length)];
    const payload = JSON.stringify({
      query: query,
      top_k: 5,
      useGraph: true,
      useVector: true,
    });

    const res = http.post(`${BASE_URL}/api/v1/search/hybrid`, payload, {
      headers: headers,
      timeout: "30s",
      tags: { name: "SearchHybrid" },
    });

    const success = check(res, {
      "search status is 200": (r) => r.status === 200,
      "search has results": (r) => {
        try {
          const body = JSON.parse(r.body);
          return body.results && body.results.length > 0;
        } catch (e) {
          return false;
        }
      },
      "search latency < 5s": (r) => r.timings.duration < 5000,
    });

    searchLatency.add(res.timings.duration);
    searchSuccessRate.add(success ? 1 : 0);

    if (!success) {
      searchErrors.add(1);
      if (res.status !== 200) {
        console.warn(`Search failed: status=${res.status}, query="${query}"`);
      }
    }
  });

  group("Semantic Search", function () {
    const query = SEARCH_QUERIES[Math.floor(Math.random() * SEARCH_QUERIES.length)];
    const payload = JSON.stringify({
      query: query,
      top_k: 5,
    });

    const res = http.post(`${BASE_URL}/api/v1/search/semantic`, payload, {
      headers: headers,
      timeout: "30s",
      tags: { name: "SearchSemantic" },
    });

    check(res, {
      "semantic search status is 200": (r) => r.status === 200,
    });

    searchLatency.add(res.timings.duration);
  });

  group("Keyword Search", function () {
    const query = SEARCH_QUERIES[Math.floor(Math.random() * SEARCH_QUERIES.length)];
    const payload = JSON.stringify({
      query: query,
      top_k: 5,
    });

    const res = http.post(`${BASE_URL}/api/v1/search/keyword`, payload, {
      headers: headers,
      timeout: "30s",
      tags: { name: "SearchKeyword" },
    });

    check(res, {
      "keyword search status is 200": (r) => r.status === 200,
    });

    searchLatency.add(res.timings.duration);
  });

  // Think time between iterations
  sleep(Math.random() * 2 + 1);
}

// ---------------------------------------------------------------------------
// Teardown
// ---------------------------------------------------------------------------
export function teardown(data) {
  if (data.token) {
    console.log("Search performance test completed.");
  }
}
