/**
 * k6 Chat API Performance Test (SSE Streaming)
 *
 * Hybrid RAG Knowledge Platform - Chat API 부하 테스트
 *
 * Chat API는 SSE 스트리밍 방식으로 응답하므로,
 * 전체 응답 완료까지의 시간을 측정합니다.
 *
 * 시나리오:
 *   - smoke: 1 VU, 30초
 *   - load:  5 VU, 2분 (Chat은 리소스 집약적이므로 VU를 줄임)
 *   - stress: 20 VU, 5분
 *
 * 실행 예시:
 *   k6 run --env SCENARIO=smoke k6_chat_test.js
 *   k6 run --env SCENARIO=load k6_chat_test.js
 *
 * STORY-129: k6 성능 회귀 테스트 스크립트
 */

import http from "k6/http";
import { check, sleep, group } from "k6";
import { Counter, Rate, Trend } from "k6/metrics";

// ---------------------------------------------------------------------------
// Custom Metrics
// ---------------------------------------------------------------------------
const chatLatency = new Trend("chat_latency_ms", true);
const chatTTFB = new Trend("chat_ttfb_ms", true);
const chatErrors = new Counter("chat_errors");
const chatSuccessRate = new Rate("chat_success_rate");

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
    vus: 5,
    duration: "2m",
  },
  stress: {
    executor: "ramping-vus",
    startVUs: 0,
    stages: [
      { duration: "30s", target: 5 },
      { duration: "2m", target: 20 },
      { duration: "1m", target: 20 },
      { duration: "1m30s", target: 0 },
    ],
  },
};

export const options = {
  scenarios: {
    chat_test: scenarios[SCENARIO] || scenarios.smoke,
  },
  thresholds: {
    // Chat API: p95 < 60s (LLM 생성 포함)
    chat_latency_ms: ["p(95)<60000", "p(99)<120000"],
    // TTFB (Time to First Byte): p95 < 10s
    chat_ttfb_ms: ["p(95)<10000"],
    // Error rate < 5%
    chat_success_rate: ["rate>0.95"],
  },
  summaryTrendStats: ["avg", "min", "med", "max", "p(90)", "p(95)", "p(99)"],
};

// ---------------------------------------------------------------------------
// Chat Queries
// ---------------------------------------------------------------------------
const CHAT_QUERIES = [
  "정보보호 정책에서 가장 중요한 항목은 무엇인가요?",
  "네트워크 보안을 강화하기 위한 방법을 알려주세요.",
  "개인정보보호법에서 정보주체의 권리는 무엇인가요?",
  "클라우드 환경에서의 데이터 암호화 방안은?",
  "접근제어 시스템 구축 시 고려사항은?",
  "RAG 시스템의 검색 품질을 개선하는 방법은?",
  "Knowledge Graph가 검색에 어떤 도움을 주나요?",
];

// ---------------------------------------------------------------------------
// Setup: Login
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
        return body.data && body.data.accessToken;
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
  const token = data.data.accessToken;
  console.log(`Login successful for chat test. Token length: ${token.length}`);

  return { token: token };
}

// ---------------------------------------------------------------------------
// Main Test: Chat API (Non-Streaming + Streaming)
// ---------------------------------------------------------------------------
export default function (data) {
  if (!data.token) {
    console.error("No auth token available. Skipping test iteration.");
    chatErrors.add(1);
    return;
  }

  const headers = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${data.token}`,
  };

  // --- Non-Streaming Chat ---
  group("Chat (Non-Streaming)", function () {
    const query = CHAT_QUERIES[Math.floor(Math.random() * CHAT_QUERIES.length)];
    const payload = JSON.stringify({
      query: query,
      topK: 5,
      useReasoner: false,
    });

    const res = http.post(`${BASE_URL}/api/v1/search/chat`, payload, {
      headers: headers,
      timeout: "120s",
      tags: { name: "ChatNonStreaming" },
    });

    const success = check(res, {
      "chat status is 200": (r) => r.status === 200,
      "chat has answer": (r) => {
        try {
          const body = JSON.parse(r.body);
          return body.answer && body.answer.length > 0;
        } catch (e) {
          return false;
        }
      },
      "chat latency < 60s": (r) => r.timings.duration < 60000,
    });

    chatLatency.add(res.timings.duration);
    chatTTFB.add(res.timings.waiting);
    chatSuccessRate.add(success ? 1 : 0);

    if (!success) {
      chatErrors.add(1);
      if (res.status !== 200) {
        console.warn(`Chat failed: status=${res.status}, query="${query.substring(0, 30)}..."`);
      }
    }
  });

  // --- Streaming Chat (SSE) ---
  group("Chat (SSE Streaming)", function () {
    const query = CHAT_QUERIES[Math.floor(Math.random() * CHAT_QUERIES.length)];
    const payload = JSON.stringify({
      query: query,
      topK: 5,
      useReasoner: false,
    });

    // SSE streaming endpoint -- k6 receives the full buffered response
    // We measure total time and TTFB
    const res = http.post(`${BASE_URL}/api/v1/search/chat/stream`, payload, {
      headers: Object.assign({}, headers, {
        Accept: "text/event-stream",
      }),
      timeout: "120s",
      tags: { name: "ChatSSEStreaming" },
    });

    const success = check(res, {
      "stream status is 200": (r) => r.status === 200,
      "stream has SSE data": (r) => {
        return r.body && r.body.includes("data:");
      },
      "stream TTFB < 10s": (r) => r.timings.waiting < 10000,
    });

    chatLatency.add(res.timings.duration);
    chatTTFB.add(res.timings.waiting);
    chatSuccessRate.add(success ? 1 : 0);

    if (!success) {
      chatErrors.add(1);
    }
  });

  // Longer think time for chat (resource-intensive)
  sleep(Math.random() * 3 + 2);
}

// ---------------------------------------------------------------------------
// Teardown
// ---------------------------------------------------------------------------
export function teardown(data) {
  if (data.token) {
    console.log("Chat performance test completed.");
  }
}
