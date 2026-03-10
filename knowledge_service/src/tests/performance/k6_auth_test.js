/**
 * k6 Auth API Performance Test
 *
 * Hybrid RAG Knowledge Platform - 인증 API 부하 테스트
 *
 * 테스트 대상:
 *   - POST /api/v1/auth/login (로그인)
 *   - GET  /api/v1/auth/me (사용자 정보 조회)
 *   - POST /api/v1/auth/refresh (토큰 갱신)
 *
 * 시나리오:
 *   - smoke: 1 VU, 30초
 *   - load:  10 VU, 2분
 *   - stress: 50 VU, 5분
 *
 * 실행 예시:
 *   k6 run --env SCENARIO=smoke k6_auth_test.js
 *
 * STORY-129: k6 성능 회귀 테스트 스크립트
 */

import http from "k6/http";
import { check, sleep, group } from "k6";
import { Counter, Rate, Trend } from "k6/metrics";

// ---------------------------------------------------------------------------
// Custom Metrics
// ---------------------------------------------------------------------------
const loginLatency = new Trend("login_latency_ms", true);
const authLatency = new Trend("auth_latency_ms", true);
const authErrors = new Counter("auth_errors");
const authSuccessRate = new Rate("auth_success_rate");

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
    auth_test: scenarios[SCENARIO] || scenarios.smoke,
  },
  thresholds: {
    // Auth API: p95 < 1s
    login_latency_ms: ["p(95)<1000", "p(99)<2000"],
    auth_latency_ms: ["p(95)<1000", "p(99)<2000"],
    // Error rate < 5%
    auth_success_rate: ["rate>0.95"],
    // General HTTP duration
    http_req_duration: ["p(95)<2000"],
  },
  summaryTrendStats: ["avg", "min", "med", "max", "p(90)", "p(95)", "p(99)"],
};

// ---------------------------------------------------------------------------
// Main Test: Auth API
// ---------------------------------------------------------------------------
export default function () {
  const jsonHeaders = {
    "Content-Type": "application/json",
  };

  let accessToken = null;
  let refreshToken = null;

  // --- Login ---
  group("Login", function () {
    const payload = JSON.stringify({
      email: AUTH_EMAIL,
      password: AUTH_PASSWORD,
    });

    const res = http.post(`${BASE_URL}/api/v1/auth/login`, payload, {
      headers: jsonHeaders,
      timeout: "10s",
      tags: { name: "AuthLogin" },
    });

    const success = check(res, {
      "login status is 200": (r) => r.status === 200,
      "login has accessToken": (r) => {
        try {
          const body = JSON.parse(r.body);
          return !!body.accessToken;
        } catch (e) {
          return false;
        }
      },
      "login latency < 1s": (r) => r.timings.duration < 1000,
    });

    loginLatency.add(res.timings.duration);
    authSuccessRate.add(success ? 1 : 0);

    if (success) {
      const data = JSON.parse(res.body);
      accessToken = data.accessToken;
      refreshToken = data.refreshToken;
    } else {
      authErrors.add(1);
      console.warn(`Login failed: status=${res.status}`);
    }
  });

  // --- Get Current User (/me) ---
  if (accessToken) {
    group("Get User Info", function () {
      const res = http.get(`${BASE_URL}/api/v1/auth/me`, {
        headers: Object.assign({}, jsonHeaders, {
          Authorization: `Bearer ${accessToken}`,
        }),
        timeout: "10s",
        tags: { name: "AuthMe" },
      });

      const success = check(res, {
        "me status is 200": (r) => r.status === 200,
        "me has user data": (r) => {
          try {
            const body = JSON.parse(r.body);
            return !!body.email;
          } catch (e) {
            return false;
          }
        },
        "me latency < 1s": (r) => r.timings.duration < 1000,
      });

      authLatency.add(res.timings.duration);
      authSuccessRate.add(success ? 1 : 0);

      if (!success) {
        authErrors.add(1);
      }
    });
  }

  // --- Token Refresh ---
  if (refreshToken) {
    group("Token Refresh", function () {
      const payload = JSON.stringify({
        refreshToken: refreshToken,
      });

      const res = http.post(`${BASE_URL}/api/v1/auth/refresh`, payload, {
        headers: jsonHeaders,
        timeout: "10s",
        tags: { name: "AuthRefresh" },
      });

      const success = check(res, {
        "refresh status is 200": (r) => r.status === 200,
        "refresh has new token": (r) => {
          try {
            const body = JSON.parse(r.body);
            return !!body.accessToken;
          } catch (e) {
            return false;
          }
        },
        "refresh latency < 1s": (r) => r.timings.duration < 1000,
      });

      authLatency.add(res.timings.duration);
      authSuccessRate.add(success ? 1 : 0);

      if (!success) {
        authErrors.add(1);
      }
    });
  }

  // --- Invalid Login (negative test) ---
  group("Invalid Login", function () {
    const payload = JSON.stringify({
      email: "invalid@example.com",
      password: "wrongpassword",
    });

    const res = http.post(`${BASE_URL}/api/v1/auth/login`, payload, {
      headers: jsonHeaders,
      timeout: "10s",
      tags: { name: "AuthInvalidLogin" },
    });

    check(res, {
      "invalid login returns 401": (r) => r.status === 401,
      "invalid login latency < 1s": (r) => r.timings.duration < 1000,
    });

    authLatency.add(res.timings.duration);
  });

  sleep(Math.random() * 1 + 0.5);
}
