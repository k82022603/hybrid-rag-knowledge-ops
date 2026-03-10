#!/usr/bin/env python3
"""
STORY-097: Graph RAG A/B Comparison Test
=========================================
5 questions x 2 groups (Graph ON vs OFF)
Real environment test against ai-service (localhost:8000)
"""

import json
import sys
import time
from datetime import datetime

import requests

BASE_URL = "http://localhost:8000"
LOGIN_URL = f"{BASE_URL}/api/v1/auth/login"
SEARCH_URL = f"{BASE_URL}/api/v1/search/hybrid"

QUESTIONS = [
    "정보보호 정책의 주요 원칙은 무엇인가요?",
    "네트워크 보안 접근제어 방법",
    "개인정보보호법 주요 조항",
    "클라우드 보안 위협 대응",
    "정보보안 사고 대응 절차",
]

def login():
    """Login and return accessToken."""
    resp = requests.post(
        LOGIN_URL,
        json={"email": "admin@example.com", "password": "admin123!"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    token = data.get("accessToken") or data.get("data", {}).get("accessToken")
    if not token:
        print(f"ERROR: accessToken not found in response: {json.dumps(data, indent=2, ensure_ascii=False)}")
        sys.exit(1)
    return token


def search(token: str, query: str, use_graph: bool, top_k: int = 5):
    """Execute hybrid search and return results with timing."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "query": query,
        "top_k": top_k,
        "useGraph": use_graph,
        "useVector": True,
    }

    start = time.time()
    try:
        resp = requests.post(SEARCH_URL, json=payload, headers=headers, timeout=180)
        elapsed_ms = (time.time() - start) * 1000
        resp.raise_for_status()
        data = resp.json()
        return {
            "status": "ok",
            "data": data,
            "client_latency_ms": round(elapsed_ms, 1),
            "server_latency_ms": data.get("latency_ms"),
        }
    except requests.exceptions.Timeout:
        elapsed_ms = (time.time() - start) * 1000
        return {"status": "timeout", "client_latency_ms": round(elapsed_ms, 1)}
    except requests.exceptions.RequestException as e:
        elapsed_ms = (time.time() - start) * 1000
        error_detail = ""
        if hasattr(e, "response") and e.response is not None:
            try:
                error_detail = e.response.text[:500]
            except Exception:
                pass
        return {
            "status": "error",
            "error": str(e),
            "error_detail": error_detail,
            "client_latency_ms": round(elapsed_ms, 1),
        }


def analyze_results(result_data):
    """Analyze a single search result."""
    if result_data["status"] != "ok":
        return {
            "status": result_data["status"],
            "error": result_data.get("error", ""),
            "client_latency_ms": result_data["client_latency_ms"],
        }

    data = result_data["data"]
    results = data.get("results", [])
    total = data.get("total", 0)

    # source_type distribution
    source_types = {}
    scores = []
    contributing_sources_list = []
    chunk_ids = set()

    for r in results:
        st = r.get("source_type", "unknown")
        source_types[st] = source_types.get(st, 0) + 1
        scores.append(r.get("score", 0))
        chunk_ids.add(r.get("chunk_id", ""))
        cs = r.get("contributing_sources")
        if cs:
            contributing_sources_list.append(cs)

    avg_score = sum(scores) / len(scores) if scores else 0

    return {
        "status": "ok",
        "total": total,
        "result_count": len(results),
        "source_type_dist": source_types,
        "avg_score": round(avg_score, 6),
        "min_score": round(min(scores), 6) if scores else 0,
        "max_score": round(max(scores), 6) if scores else 0,
        "client_latency_ms": result_data["client_latency_ms"],
        "server_latency_ms": result_data.get("server_latency_ms"),
        "chunk_ids": sorted(chunk_ids),
        "contributing_sources": contributing_sources_list,
        "from_cache": data.get("from_cache", False),
    }


def run_ab_test():
    """Run the full A/B test."""
    print("=" * 70)
    print("STORY-097: Graph RAG A/B Comparison Test")
    print(f"Start: {datetime.now().isoformat()}")
    print("=" * 70)

    # Step 1: Login
    print("\n[1] Logging in...")
    token = login()
    print(f"    Token acquired: {token[:20]}...")

    # Step 2: Run tests
    results_a = []  # Graph ON
    results_b = []  # Graph OFF

    for i, question in enumerate(QUESTIONS, 1):
        print(f"\n[Q{i}] {question}")

        # A Group: Graph ON
        print(f"  [A] Graph ON  ... ", end="", flush=True)
        result_a = search(token, question, use_graph=True, top_k=5)
        analysis_a = analyze_results(result_a)
        results_a.append({"question": question, "raw": result_a, "analysis": analysis_a})
        print(f"status={analysis_a['status']}, latency={analysis_a['client_latency_ms']}ms")

        # Small pause to avoid overwhelming
        time.sleep(0.5)

        # B Group: Graph OFF
        print(f"  [B] Graph OFF ... ", end="", flush=True)
        result_b = search(token, question, use_graph=False, top_k=5)
        analysis_b = analyze_results(result_b)
        results_b.append({"question": question, "raw": result_b, "analysis": analysis_b})
        print(f"status={analysis_b['status']}, latency={analysis_b['client_latency_ms']}ms")

        time.sleep(0.5)

    # Step 3: Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print(f"\n{'Question':<35} | {'Graph ON':^25} | {'Graph OFF':^25}")
    print("-" * 90)

    for i in range(len(QUESTIONS)):
        q = QUESTIONS[i][:33]
        a = results_a[i]["analysis"]
        b = results_b[i]["analysis"]

        a_info = f"{a.get('result_count', 'ERR')} results, {a.get('client_latency_ms', '?')}ms" if a['status'] == 'ok' else a['status']
        b_info = f"{b.get('result_count', 'ERR')} results, {b.get('client_latency_ms', '?')}ms" if b['status'] == 'ok' else b['status']

        print(f"{q:<35} | {a_info:^25} | {b_info:^25}")

    # Aggregate stats
    print("\n--- Aggregate Statistics ---")

    for label, results in [("Graph ON (A)", results_a), ("Graph OFF (B)", results_b)]:
        ok_results = [r for r in results if r["analysis"]["status"] == "ok"]
        if ok_results:
            avg_latency = sum(r["analysis"]["client_latency_ms"] for r in ok_results) / len(ok_results)
            avg_score = sum(r["analysis"]["avg_score"] for r in ok_results) / len(ok_results)
            avg_count = sum(r["analysis"]["result_count"] for r in ok_results) / len(ok_results)

            # source type aggregate
            all_sources = {}
            for r in ok_results:
                for src, cnt in r["analysis"].get("source_type_dist", {}).items():
                    all_sources[src] = all_sources.get(src, 0) + cnt

            print(f"\n  {label}:")
            print(f"    Success: {len(ok_results)}/{len(results)}")
            print(f"    Avg Latency: {avg_latency:.1f}ms")
            print(f"    Avg Score: {avg_score:.6f}")
            print(f"    Avg Results: {avg_count:.1f}")
            print(f"    Source Types: {all_sources}")
            print(f"    Cache Hits: {sum(1 for r in ok_results if r['analysis'].get('from_cache'))}")
        else:
            print(f"\n  {label}: ALL FAILED")

    # Unique results analysis
    print("\n--- Unique Results Analysis (Graph ON vs OFF) ---")
    for i in range(len(QUESTIONS)):
        a = results_a[i]["analysis"]
        b = results_b[i]["analysis"]
        if a["status"] == "ok" and b["status"] == "ok":
            a_chunks = set(a.get("chunk_ids", []))
            b_chunks = set(b.get("chunk_ids", []))
            only_a = a_chunks - b_chunks
            only_b = b_chunks - a_chunks
            common = a_chunks & b_chunks
            print(f"\n  Q{i+1}: {QUESTIONS[i][:40]}")
            print(f"    Common: {len(common)}, Only Graph ON: {len(only_a)}, Only Graph OFF: {len(only_b)}")
            if only_a:
                print(f"    Graph ON unique: {sorted(only_a)[:5]}")
            if only_b:
                print(f"    Graph OFF unique: {sorted(only_b)[:5]}")

    # Contributing sources detail (Graph ON)
    print("\n--- Contributing Sources Detail (Graph ON) ---")
    for i in range(len(QUESTIONS)):
        a = results_a[i]["analysis"]
        if a["status"] == "ok":
            cs = a.get("contributing_sources", [])
            print(f"  Q{i+1}: {cs[:3]}")

    # Return structured data for report
    return {
        "timestamp": datetime.now().isoformat(),
        "questions": QUESTIONS,
        "results_a": [{"question": r["question"], "analysis": r["analysis"]} for r in results_a],
        "results_b": [{"question": r["question"], "analysis": r["analysis"]} for r in results_b],
        "raw_a": [r["raw"] for r in results_a],
        "raw_b": [r["raw"] for r in results_b],
    }


if __name__ == "__main__":
    test_data = run_ab_test()

    # Save raw results
    output_path = "/mnt/d/Users/KTDS/Documents/06.과제/hybrid-rag-knowledge-ops/knowledge_service/docs/04_testing/12_embedding_evaluation/21_graph_rag_ab_raw_data.json"
    with open(output_path, "w", encoding="utf-8") as f:
        # Convert sets to lists for JSON serialization
        def serialize(obj):
            if isinstance(obj, set):
                return sorted(obj)
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

        json.dump(test_data, f, ensure_ascii=False, indent=2, default=serialize)
    print(f"\nRaw data saved to: {output_path}")
    print(f"\nDone: {datetime.now().isoformat()}")
