#!/usr/bin/env python3
"""
HRKP Search Quality Smoke Test

Graph RAG 적용 전/후 검색 품질 차이를 실측 데이터로 증빙합니다.
동일 질의를 2가지 모드(Graph ON / OFF)로 실행하여 비교합니다.

- Mode A: useGraph=True, useVector=True  (Hybrid 3채널: BM25 + Dense + Graph)
- Mode B: useGraph=False, useVector=True (Hybrid 2채널: BM25 + Dense only)

Usage:
    # 컨테이너 내부 실행 (권장)
    docker exec kp-ai-service python3 /app/scripts/smoke_test_search.py

    # 로컬 실행 (외부에서 API 호출)
    python smoke_test_search.py --url http://localhost:8000

    # 결과 파일 경로 지정
    python smoke_test_search.py --output /custom/path/result.json

    # 반복 측정 (웜업 포함)
    python smoke_test_search.py --warmup 2 --repeat 3

Author: QA Agent (Claude Opus 4.6)
Date: 2026-02-10
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 테스트 질의 정의
# ---------------------------------------------------------------------------

TEST_QUERIES: List[Dict[str, str]] = [
    # 엔티티 관계 질의 (Graph 강점 - 엔티티명 직접 포함)
    {
        "query": "Neo4j와 Elasticsearch의 역할 차이점은?",
        "type": "entity_relation",
    },
    {
        "query": "LangGraph와 LangChain 중 어떤 것을 사용해야 하나요?",
        "type": "entity_relation",
    },
    # 멀티홉 추론 질의 (Graph 강점 - RELATED_TO 확장 활용)
    {
        "query": "RAG Pipeline에서 BGE-M3 임베딩 모델의 역할은?",
        "type": "multi_hop",
    },
    {
        "query": "Kubernetes에서 Spring Boot 마이크로서비스 배포 방법",
        "type": "multi_hop",
    },
    # 키워드 기반 질의 (BM25 강점)
    {
        "query": "Docker Compose 설정 방법",
        "type": "keyword",
    },
    {
        "query": "환경변수 설정 가이드",
        "type": "keyword",
    },
    # 의미적 유사도 질의 (Vector 강점)
    {
        "query": "대규모 문서를 효율적으로 처리하는 방법",
        "type": "semantic",
    },
    {
        "query": "검색 성능을 최적화하려면 어떻게 해야 하나요?",
        "type": "semantic",
    },
    # 복합 엔티티 질의 (Graph + Vector 시너지)
    {
        "query": "FastAPI와 PostgreSQL 연동하여 RAGAS 평가하기",
        "type": "entity_relation",
    },
    {
        "query": "Agentic AI 에이전트 워크플로우 설계 패턴",
        "type": "multi_hop",
    },
]


# ---------------------------------------------------------------------------
# 콘솔 색상
# ---------------------------------------------------------------------------

class Colors:
    """ANSI 콘솔 색상 코드"""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"

    @staticmethod
    def colorize(text: str, color: str) -> str:
        if os.getenv("NO_COLOR"):
            return text
        return f"{color}{text}{Colors.RESET}"


def log_info(msg: str) -> None:
    print(Colors.colorize(f"  [INFO] {msg}", Colors.CYAN))


def log_ok(msg: str) -> None:
    print(Colors.colorize(f"  [OK]   {msg}", Colors.GREEN))


def log_warn(msg: str) -> None:
    print(Colors.colorize(f"  [WARN] {msg}", Colors.YELLOW))


def log_error(msg: str) -> None:
    print(Colors.colorize(f"  [ERR]  {msg}", Colors.RED))


def log_header(msg: str) -> None:
    print(Colors.colorize(f"\n  {msg}", Colors.BOLD + Colors.BLUE))


def log_separator() -> None:
    print(Colors.colorize(f"  {'=' * 60}", Colors.DIM))


# ---------------------------------------------------------------------------
# HTTP 클라이언트 (requests 사용)
# ---------------------------------------------------------------------------

class SearchTestClient:
    """검색 스모크 테스트용 HTTP 클라이언트"""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        email: str = "admin@example.com",
        password: str = "admin123!",
        timeout: int = 30,
    ):
        self.base_url = base_url.rstrip("/")
        self.email = email
        self.password = password
        self.timeout = timeout
        self.token: Optional[str] = None
        self._session = None

    def _get_session(self):
        """requests.Session lazy 초기화"""
        if self._session is None:
            import requests
            self._session = requests.Session()
            self._session.headers.update({
                "Content-Type": "application/json",
            })
        return self._session

    def authenticate(self) -> float:
        """
        로그인하여 JWT 토큰 획득

        Returns:
            인증 소요 시간 (ms)

        Raises:
            RuntimeError: 인증 실패 시
        """
        session = self._get_session()
        url = f"{self.base_url}/api/v1/auth/login"
        payload = {"email": self.email, "password": self.password}

        start = time.perf_counter()
        resp = session.post(url, json=payload, timeout=self.timeout)
        elapsed_ms = (time.perf_counter() - start) * 1000

        if resp.status_code != 200:
            raise RuntimeError(
                f"Authentication failed: {resp.status_code} - {resp.text}"
            )

        data = resp.json()
        # camelCase alias 또는 snake_case 필드 모두 지원
        self.token = (
            data.get("accessToken")
            or data.get("access_token")
        )
        if not self.token:
            raise RuntimeError(
                f"No access token in response: {list(data.keys())}"
            )

        session.headers["Authorization"] = f"Bearer {self.token}"
        return elapsed_ms

    def hybrid_search(
        self,
        query: str,
        top_k: int = 10,
        use_graph: bool = True,
        use_vector: bool = True,
    ) -> Tuple[Dict[str, Any], float]:
        """
        Hybrid 검색 API 호출

        Args:
            query: 검색 질의
            top_k: 반환 결과 수
            use_graph: Graph 검색 사용 여부
            use_vector: Vector 검색 사용 여부

        Returns:
            (응답 JSON, 소요 시간 ms) 튜플
        """
        session = self._get_session()
        url = f"{self.base_url}/api/v1/search/hybrid"
        payload = {
            "query": query,
            "top_k": top_k,
            "useGraph": use_graph,
            "useVector": use_vector,
        }

        start = time.perf_counter()
        resp = session.post(url, json=payload, timeout=self.timeout)
        elapsed_ms = (time.perf_counter() - start) * 1000

        if resp.status_code != 200:
            raise RuntimeError(
                f"Search failed ({resp.status_code}): {resp.text[:200]}"
            )

        return resp.json(), elapsed_ms


# ---------------------------------------------------------------------------
# 결과 파싱 및 비교
# ---------------------------------------------------------------------------

def extract_top_results(
    response: Dict[str, Any],
    count: int = 5,
) -> List[Dict[str, Any]]:
    """
    검색 응답에서 상위 N개 결과 추출

    Args:
        response: API 응답 JSON
        count: 추출할 결과 수

    Returns:
        상위 결과 리스트
    """
    results = response.get("results", [])
    top = []
    for i, r in enumerate(results[:count]):
        # 메타데이터에서 title 추출 시도
        metadata = r.get("metadata", {})
        title = (
            metadata.get("title")
            or metadata.get("document_title")
            or metadata.get("file_name")
            or r.get("document_id", "N/A")
        )
        content = r.get("content", "")
        snippet = content[:100].replace("\n", " ").strip()
        if len(content) > 100:
            snippet += "..."

        top.append({
            "rank": i + 1,
            "score": round(r.get("score", 0.0), 6),
            "source_type": r.get("source_type", "unknown"),
            "title": title,
            "snippet": snippet,
            "chunk_id": r.get("chunk_id", ""),
        })
    return top


def compute_source_distribution(
    response: Dict[str, Any],
) -> Dict[str, int]:
    """
    검색 결과의 source_type 분포 계산

    Args:
        response: API 응답 JSON

    Returns:
        source_type별 카운트
    """
    dist: Dict[str, int] = {}
    for r in response.get("results", []):
        src = r.get("source_type", "unknown")
        dist[src] = dist.get(src, 0) + 1
    return dist


def compare_results(
    graph_response: Dict[str, Any],
    no_graph_response: Dict[str, Any],
    graph_latency: float,
    no_graph_latency: float,
) -> Dict[str, Any]:
    """
    Graph ON/OFF 결과 비교

    Args:
        graph_response: Graph 활성화 검색 결과
        no_graph_response: Graph 비활성화 검색 결과
        graph_latency: Graph ON 소요 시간 (ms)
        no_graph_latency: Graph OFF 소요 시간 (ms)

    Returns:
        비교 분석 결과
    """
    # chunk_id 기반 결과 집합 비교
    graph_chunks = {
        r.get("chunk_id", "") for r in graph_response.get("results", [])
    }
    no_graph_chunks = {
        r.get("chunk_id", "") for r in no_graph_response.get("results", [])
    }

    overlap = graph_chunks & no_graph_chunks
    graph_unique = graph_chunks - no_graph_chunks
    no_graph_unique = no_graph_chunks - graph_chunks

    # 1위 결과 동일 여부
    graph_results = graph_response.get("results", [])
    no_graph_results = no_graph_response.get("results", [])
    top1_same = False
    if graph_results and no_graph_results:
        top1_same = (
            graph_results[0].get("chunk_id")
            == no_graph_results[0].get("chunk_id")
        )

    # 점수 비교 (상위 5개 평균)
    graph_scores = [
        r.get("score", 0.0) for r in graph_results[:5]
    ]
    no_graph_scores = [
        r.get("score", 0.0) for r in no_graph_results[:5]
    ]
    avg_score_graph = (
        sum(graph_scores) / len(graph_scores) if graph_scores else 0.0
    )
    avg_score_no_graph = (
        sum(no_graph_scores) / len(no_graph_scores) if no_graph_scores else 0.0
    )

    return {
        "latency_diff_ms": round(graph_latency - no_graph_latency, 2),
        "graph_unique_results": len(graph_unique),
        "no_graph_unique_results": len(no_graph_unique),
        "overlap_results": len(overlap),
        "top1_same": top1_same,
        "avg_top5_score_graph": round(avg_score_graph, 6),
        "avg_top5_score_no_graph": round(avg_score_no_graph, 6),
    }


# ---------------------------------------------------------------------------
# 스모크 테스트 실행기
# ---------------------------------------------------------------------------

class SmokeTestRunner:
    """검색 품질 스모크 테스트 실행기"""

    def __init__(
        self,
        client: SearchTestClient,
        queries: Optional[List[Dict[str, str]]] = None,
        warmup_rounds: int = 1,
        repeat: int = 1,
        top_k: int = 10,
    ):
        self.client = client
        self.queries = queries or TEST_QUERIES
        self.warmup_rounds = warmup_rounds
        self.repeat = repeat
        self.top_k = top_k

    def run(self) -> Dict[str, Any]:
        """
        전체 스모크 테스트 실행

        Returns:
            전체 테스트 결과 (JSON 직렬화 가능)
        """
        log_header("HRKP Search Quality Smoke Test")
        log_separator()
        log_info(f"Queries: {len(self.queries)}")
        log_info(f"Warmup rounds: {self.warmup_rounds}")
        log_info(f"Measurement repeats: {self.repeat}")
        log_info(f"Top-K: {self.top_k}")
        log_info(f"API: {self.client.base_url}")
        log_separator()

        # 인증
        log_info("Authenticating...")
        try:
            auth_ms = self.client.authenticate()
            log_ok(f"Authenticated in {auth_ms:.0f}ms")
        except Exception as e:
            log_error(f"Authentication failed: {e}")
            sys.exit(1)

        # 웜업 (캐시 프라이밍)
        if self.warmup_rounds > 0:
            self._run_warmup()

        # 본 측정
        results = self._run_measurements()

        # 요약 통계
        summary = self._compute_summary(results)

        report = {
            "metadata": {
                "test_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "api_url": self.client.base_url,
                "top_k": self.top_k,
                "warmup_rounds": self.warmup_rounds,
                "measurement_repeats": self.repeat,
                "total_queries": len(self.queries),
            },
            "results": results,
            "summary": summary,
        }

        return report

    def _run_warmup(self) -> None:
        """웜업 실행 (캐시 프라이밍 및 JIT 워밍)"""
        log_header(f"Warmup Phase ({self.warmup_rounds} round(s))")

        for rnd in range(self.warmup_rounds):
            for i, q in enumerate(self.queries):
                query = q["query"]
                label = f"  Warmup {rnd + 1}-{i + 1}/{len(self.queries)}"
                try:
                    # Graph OFF 먼저 (캐시 최소화)
                    self.client.hybrid_search(
                        query, self.top_k, use_graph=False
                    )
                    # Graph ON
                    self.client.hybrid_search(
                        query, self.top_k, use_graph=True
                    )
                    print(f"{label}: {query[:40]}... OK")
                except Exception as e:
                    print(f"{label}: {query[:40]}... SKIP ({e})")

        log_ok("Warmup complete")

    def _run_measurements(self) -> List[Dict[str, Any]]:
        """
        본 측정 실행

        측정 순서: 공정한 비교를 위해 각 질의마다
        1) Graph OFF 먼저 실행
        2) Graph ON 실행
        순서를 고정합니다. 웜업으로 캐시 효과는 이미 평준화됩니다.

        Returns:
            질의별 측정 결과 리스트
        """
        log_header(f"Measurement Phase ({len(self.queries)} queries)")
        log_separator()

        all_results = []

        for idx, q in enumerate(self.queries):
            query = q["query"]
            qtype = q["type"]
            query_num = idx + 1

            log_info(
                f"[{query_num}/{len(self.queries)}] "
                f"({qtype}) {query[:50]}..."
            )

            # 반복 측정 결과 수집
            graph_latencies = []
            no_graph_latencies = []
            graph_resp_last = None
            no_graph_resp_last = None

            for rep in range(self.repeat):
                # --- Mode B: Graph OFF ---
                try:
                    no_graph_resp, no_graph_ms = self.client.hybrid_search(
                        query, self.top_k, use_graph=False
                    )
                    no_graph_latencies.append(no_graph_ms)
                    no_graph_resp_last = no_graph_resp
                except Exception as e:
                    log_warn(f"  Graph OFF failed (rep {rep + 1}): {e}")
                    continue

                # 측정 간 짧은 대기 (서버 안정화)
                time.sleep(0.2)

                # --- Mode A: Graph ON ---
                try:
                    graph_resp, graph_ms = self.client.hybrid_search(
                        query, self.top_k, use_graph=True
                    )
                    graph_latencies.append(graph_ms)
                    graph_resp_last = graph_resp
                except Exception as e:
                    log_warn(f"  Graph ON failed (rep {rep + 1}): {e}")
                    continue

                if self.repeat > 1:
                    time.sleep(0.2)

            # 결과 조합 (마지막 응답 기준 + 평균 레이턴시)
            if graph_resp_last is None or no_graph_resp_last is None:
                log_error(f"  SKIP: insufficient results for query {query_num}")
                all_results.append({
                    "query": query,
                    "type": qtype,
                    "error": "Insufficient successful measurements",
                    "graph_enabled": None,
                    "graph_disabled": None,
                    "comparison": None,
                })
                continue

            avg_graph_ms = sum(graph_latencies) / len(graph_latencies)
            avg_no_graph_ms = sum(no_graph_latencies) / len(no_graph_latencies)

            # 서버 보고 레이턴시 (API 응답 내부)
            server_latency_graph = graph_resp_last.get("latency_ms")
            server_latency_no_graph = no_graph_resp_last.get("latency_ms")

            # 결과 구성
            graph_result = {
                "latency_ms": round(avg_graph_ms, 2),
                "server_latency_ms": server_latency_graph,
                "total_results": graph_resp_last.get("total", 0),
                "from_cache": graph_resp_last.get("from_cache", False),
                "top5": extract_top_results(graph_resp_last, 5),
                "source_distribution": compute_source_distribution(
                    graph_resp_last
                ),
            }

            no_graph_result = {
                "latency_ms": round(avg_no_graph_ms, 2),
                "server_latency_ms": server_latency_no_graph,
                "total_results": no_graph_resp_last.get("total", 0),
                "from_cache": no_graph_resp_last.get("from_cache", False),
                "top5": extract_top_results(no_graph_resp_last, 5),
                "source_distribution": compute_source_distribution(
                    no_graph_resp_last
                ),
            }

            comparison = compare_results(
                graph_resp_last, no_graph_resp_last,
                avg_graph_ms, avg_no_graph_ms,
            )

            # 다중 반복 시 raw 레이턴시 포함
            if self.repeat > 1:
                graph_result["latency_samples_ms"] = [
                    round(t, 2) for t in graph_latencies
                ]
                no_graph_result["latency_samples_ms"] = [
                    round(t, 2) for t in no_graph_latencies
                ]

            entry = {
                "query": query,
                "type": qtype,
                "graph_enabled": graph_result,
                "graph_disabled": no_graph_result,
                "comparison": comparison,
            }
            all_results.append(entry)

            # 콘솔 요약 출력
            self._print_query_result(query_num, entry)

            # 다음 질의 전 대기
            if idx < len(self.queries) - 1:
                time.sleep(0.3)

        return all_results

    def _print_query_result(
        self,
        num: int,
        entry: Dict[str, Any],
    ) -> None:
        """질의 결과 콘솔 출력"""
        ge = entry.get("graph_enabled")
        gd = entry.get("graph_disabled")
        comp = entry.get("comparison")

        if ge is None or gd is None:
            return

        ge_lat = ge["latency_ms"]
        gd_lat = gd["latency_ms"]
        diff = comp["latency_diff_ms"]
        graph_unique = comp["graph_unique_results"]
        overlap = comp["overlap_results"]
        top1 = "same" if comp["top1_same"] else "diff"

        # 레이턴시 색상
        def lat_color(ms: float) -> str:
            if ms < 500:
                return Colors.GREEN
            if ms < 1500:
                return Colors.YELLOW
            return Colors.RED

        ge_str = Colors.colorize(f"{ge_lat:7.0f}ms", lat_color(ge_lat))
        gd_str = Colors.colorize(f"{gd_lat:7.0f}ms", lat_color(gd_lat))

        # 소스 분포
        ge_dist = ge.get("source_distribution", {})
        gd_dist = gd.get("source_distribution", {})
        ge_dist_str = " ".join(
            f"{k}:{v}" for k, v in sorted(ge_dist.items())
        )
        gd_dist_str = " ".join(
            f"{k}:{v}" for k, v in sorted(gd_dist.items())
        )

        print(
            f"    Graph ON : {ge_str}  "
            f"results={ge['total_results']:2d}  [{ge_dist_str}]"
        )
        print(
            f"    Graph OFF: {gd_str}  "
            f"results={gd['total_results']:2d}  [{gd_dist_str}]"
        )
        print(
            f"    Diff: latency={diff:+.0f}ms  "
            f"graph_unique={graph_unique}  "
            f"overlap={overlap}  "
            f"top1={top1}"
        )
        print()

    def _compute_summary(
        self,
        results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """전체 테스트 요약 통계 계산"""
        log_header("Summary")
        log_separator()

        valid = [
            r for r in results
            if r.get("graph_enabled") and r.get("graph_disabled")
        ]

        if not valid:
            log_warn("No valid results to summarize")
            return {"error": "No valid results"}

        # 전체 레이턴시 통계
        graph_latencies = [r["graph_enabled"]["latency_ms"] for r in valid]
        no_graph_latencies = [r["graph_disabled"]["latency_ms"] for r in valid]

        avg_graph = sum(graph_latencies) / len(graph_latencies)
        avg_no_graph = sum(no_graph_latencies) / len(no_graph_latencies)

        # 질의 유형별 통계
        type_stats: Dict[str, Dict[str, Any]] = {}
        for r in valid:
            qtype = r["type"]
            if qtype not in type_stats:
                type_stats[qtype] = {
                    "count": 0,
                    "graph_latencies": [],
                    "no_graph_latencies": [],
                    "graph_unique_total": 0,
                    "top1_same_count": 0,
                }
            ts = type_stats[qtype]
            ts["count"] += 1
            ts["graph_latencies"].append(r["graph_enabled"]["latency_ms"])
            ts["no_graph_latencies"].append(r["graph_disabled"]["latency_ms"])
            ts["graph_unique_total"] += r["comparison"]["graph_unique_results"]
            if r["comparison"]["top1_same"]:
                ts["top1_same_count"] += 1

        type_summary = {}
        for qtype, ts in type_stats.items():
            avg_g = sum(ts["graph_latencies"]) / len(ts["graph_latencies"])
            avg_ng = sum(ts["no_graph_latencies"]) / len(ts["no_graph_latencies"])
            type_summary[qtype] = {
                "count": ts["count"],
                "avg_latency_graph_ms": round(avg_g, 2),
                "avg_latency_no_graph_ms": round(avg_ng, 2),
                "avg_latency_diff_ms": round(avg_g - avg_ng, 2),
                "total_graph_unique_results": ts["graph_unique_total"],
                "top1_same_rate": round(
                    ts["top1_same_count"] / ts["count"] * 100, 1
                ),
            }

        # Graph 전용 결과 비율
        total_graph_unique = sum(
            r["comparison"]["graph_unique_results"] for r in valid
        )
        top1_same_count = sum(
            1 for r in valid if r["comparison"]["top1_same"]
        )

        summary = {
            "total_queries": len(results),
            "successful_queries": len(valid),
            "failed_queries": len(results) - len(valid),
            "overall": {
                "avg_latency_graph_ms": round(avg_graph, 2),
                "avg_latency_no_graph_ms": round(avg_no_graph, 2),
                "avg_latency_diff_ms": round(avg_graph - avg_no_graph, 2),
                "total_graph_unique_results": total_graph_unique,
                "top1_same_rate_pct": round(
                    top1_same_count / len(valid) * 100, 1
                ),
            },
            "by_query_type": type_summary,
        }

        # 콘솔 출력
        log_info(
            f"Avg Latency   - Graph ON: {avg_graph:.0f}ms  "
            f"Graph OFF: {avg_no_graph:.0f}ms  "
            f"Diff: {avg_graph - avg_no_graph:+.0f}ms"
        )
        log_info(
            f"Graph Unique  - Total: {total_graph_unique} results "
            f"(across {len(valid)} queries)"
        )
        log_info(
            f"Top-1 Same    - {top1_same_count}/{len(valid)} "
            f"({top1_same_count / len(valid) * 100:.0f}%)"
        )

        for qtype, ts in type_summary.items():
            log_info(
                f"  [{qtype:16s}] "
                f"Graph ON: {ts['avg_latency_graph_ms']:7.0f}ms  "
                f"Graph OFF: {ts['avg_latency_no_graph_ms']:7.0f}ms  "
                f"Diff: {ts['avg_latency_diff_ms']:+7.0f}ms  "
                f"GraphUnique: {ts['total_graph_unique_results']}"
            )

        log_separator()
        return summary


# ---------------------------------------------------------------------------
# 결과 저장
# ---------------------------------------------------------------------------

def save_results(
    report: Dict[str, Any],
    output_path: str,
) -> str:
    """
    결과를 JSON 파일로 저장

    Args:
        report: 테스트 결과 딕셔너리
        output_path: 저장 경로

    Returns:
        실제 저장된 파일 경로
    """
    # 디렉토리 생성
    dir_path = os.path.dirname(output_path)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return output_path


# ---------------------------------------------------------------------------
# 메인 엔트리포인트
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="HRKP Search Quality Smoke Test - Graph RAG ON/OFF 비교",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # 컨테이너 내부 실행\n"
            "  docker exec kp-ai-service python3 /app/scripts/smoke_test_search.py\n"
            "\n"
            "  # 로컬 실행 (커스텀 URL)\n"
            "  python smoke_test_search.py --url http://localhost:8000\n"
            "\n"
            "  # 반복 측정\n"
            "  python smoke_test_search.py --warmup 2 --repeat 3\n"
        ),
    )
    parser.add_argument(
        "--url",
        default=os.getenv("AI_SERVICE_URL", "http://localhost:8000"),
        help="AI Service URL (default: $AI_SERVICE_URL or http://localhost:8000)",
    )
    parser.add_argument(
        "--email",
        default=os.getenv("AI_SERVICE_EMAIL", "admin@example.com"),
        help="Login email (default: admin@example.com)",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("AI_SERVICE_PASSWORD", "admin123!"),
        help="Login password (default: admin123!)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Number of search results to retrieve (default: 10)",
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=1,
        help="Number of warmup rounds before measurement (default: 1)",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Number of measurement repeats per query (default: 1)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help=(
            "Output JSON file path "
            "(default: docs/results/smoke_test_search_YYYY-MM-DD.json)"
        ),
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="HTTP request timeout in seconds (default: 30)",
    )
    args = parser.parse_args()

    # 출력 경로 결정
    today = datetime.now().strftime("%Y-%m-%d")
    if args.output:
        output_path = args.output
    else:
        # 컨테이너 내부인지 확인
        if os.path.exists("/app/docs/results"):
            output_path = f"/app/docs/results/smoke_test/smoke_test_search_{today}.json"
        else:
            # 로컬 환경 (스크립트 기준 상대 경로)
            script_dir = os.path.dirname(os.path.abspath(__file__))
            results_dir = os.path.join(
                script_dir, "..", "docs", "results", "smoke_test"
            )
            output_path = os.path.join(
                results_dir, f"smoke_test_search_{today}.json"
            )
            output_path = os.path.normpath(output_path)

    # 클라이언트 생성
    client = SearchTestClient(
        base_url=args.url,
        email=args.email,
        password=args.password,
        timeout=args.timeout,
    )

    # 테스트 실행
    runner = SmokeTestRunner(
        client=client,
        queries=TEST_QUERIES,
        warmup_rounds=args.warmup,
        repeat=args.repeat,
        top_k=args.top_k,
    )

    start_time = time.perf_counter()
    report = runner.run()
    total_time = (time.perf_counter() - start_time) * 1000

    report["metadata"]["total_elapsed_ms"] = round(total_time, 2)

    # 결과 저장
    saved_path = save_results(report, output_path)
    log_ok(f"Results saved to: {saved_path}")

    # 최종 요약
    log_header("Test Complete")
    summary = report.get("summary", {})
    overall = summary.get("overall", {})
    total_q = summary.get("total_queries", 0)
    success_q = summary.get("successful_queries", 0)
    failed_q = summary.get("failed_queries", 0)

    if overall:
        log_info(
            f"Queries: {success_q}/{total_q} passed  "
            f"({failed_q} failed)"
        )
        log_info(f"Total time: {total_time / 1000:.1f}s")
        log_info(
            f"Graph adds {overall.get('total_graph_unique_results', 0)} "
            f"unique results across all queries"
        )
    else:
        log_warn("No results to summarize")

    print()


if __name__ == "__main__":
    main()
