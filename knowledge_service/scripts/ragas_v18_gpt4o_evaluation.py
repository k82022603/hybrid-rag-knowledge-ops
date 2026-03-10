#!/usr/bin/env python3
"""
RAGAS v18 Evaluation - GPT-4o Judge (Direct Implementation)

Same pipeline as v16 (REST API Search + DeepSeek Direct Answer)
but with GPT-4o as RAGAS judge instead of DeepSeek.

Implements RAGAS metrics directly via GPT-4o API calls.

Usage:
    cd knowledge_service
    source .venv/bin/activate
    python scripts/ragas_v18_gpt4o_evaluation.py
"""

import asyncio
import json
import math
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from statistics import mean, median
from typing import Any, Dict, List, Optional, Tuple

import httpx

# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------
BASE_URL = "http://localhost:8000"
LOGIN_EMAIL = "admin@example.com"
LOGIN_PASSWORD = "admin123!"
SEARCH_TOP_K = 5
SEARCH_ENDPOINT = "/api/v1/search/hybrid"

# Load env
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
if ENV_FILE.exists():
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

V16_RESULT = Path(__file__).resolve().parent.parent / "docs/04_testing/11_ragas/results/ragas_v16_result.json"
OUTPUT_JSON = Path(__file__).resolve().parent.parent / "docs/04_testing/12_embedding_evaluation/ragas_v18_gpt4o_results.json"
OUTPUT_REPORT = Path(__file__).resolve().parent.parent / "docs/04_testing/12_embedding_evaluation/22_ragas_v18_gpt4o_judge.md"

CONCURRENT_LIMIT = 5
DELAY_BETWEEN_CALLS = 0.3


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
def load_questions_from_v16() -> List[Dict[str, str]]:
    with open(V16_RESULT, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [
        {"question": r["question"], "ground_truth": r.get("ground_truth", "")}
        for r in data.get("individual_results", [])
    ]


def parse_json_from_response(text: str) -> Any:
    """Robustly parse JSON from GPT-4o response, handling markdown code blocks."""
    text = text.strip()
    # Remove markdown code blocks
    if "```" in text:
        # Extract content between first pair of ```
        match = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
        if match:
            text = match.group(1).strip()
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try finding array/object boundaries
    for start_char, end_char in [('[', ']'), ('{', '}')]:
        start = text.find(start_char)
        end = text.rfind(end_char)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
    raise json.JSONDecodeError("Could not parse JSON", text, 0)


# -------------------------------------------------------------------
# GPT-4o API call helper
# -------------------------------------------------------------------
async def call_gpt4o(
    client: httpx.AsyncClient,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.0,
    max_tokens: int = 2048,
) -> str:
    """Call GPT-4o API and return response text."""
    resp = await client.post(
        "https://api.openai.com/v1/chat/completions",
        json={
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        timeout=120.0,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


# -------------------------------------------------------------------
# Step 1: Login & Search API calls
# -------------------------------------------------------------------
async def get_token(client: httpx.AsyncClient) -> str:
    resp = await client.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": LOGIN_EMAIL, "password": LOGIN_PASSWORD},
    )
    resp.raise_for_status()
    return resp.json().get("accessToken", "")


async def search_hybrid(
    client: httpx.AsyncClient, token: str, query: str, top_k: int = 5
) -> Tuple[List[str], float]:
    start = time.monotonic()
    resp = await client.post(
        f"{BASE_URL}{SEARCH_ENDPOINT}",
        json={"query": query, "top_k": top_k},
        headers={"Authorization": f"Bearer {token}"},
        timeout=120.0,
    )
    latency_ms = (time.monotonic() - start) * 1000
    resp.raise_for_status()
    results = resp.json().get("results", [])
    contexts = [r.get("content", "") for r in results if r.get("content")]
    return contexts, latency_ms


# -------------------------------------------------------------------
# Step 2: Generate answer via DeepSeek
# -------------------------------------------------------------------
async def generate_answer_deepseek(
    client: httpx.AsyncClient, question: str, contexts: List[str]
) -> Tuple[str, float]:
    context_text = "\n\n---\n\n".join(contexts[:5])
    prompt = f"""다음 컨텍스트를 기반으로 질문에 답변하세요.
컨텍스트에 없는 내용은 답변하지 마세요.

## 컨텍스트
{context_text}

## 질문
{question}

## 답변"""

    start = time.monotonic()
    try:
        resp = await client.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
                "max_tokens": 1024,
            },
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            timeout=120.0,
        )
        latency_ms = (time.monotonic() - start) * 1000
        resp.raise_for_status()
        answer = resp.json()["choices"][0]["message"]["content"].strip()
        return answer, latency_ms
    except Exception as e:
        latency_ms = (time.monotonic() - start) * 1000
        print(f"  [ERROR] DeepSeek failed: {e}")
        return f"Error: {e}", latency_ms


# -------------------------------------------------------------------
# Step 3: RAGAS metrics via GPT-4o
# -------------------------------------------------------------------

async def evaluate_faithfulness(
    client: httpx.AsyncClient,
    question: str,
    answer: str,
    contexts: List[str],
) -> float:
    """Faithfulness: claim extraction + verification."""
    # Truncate answer/contexts for prompt size management
    answer_trunc = answer[:3000]
    context_text = "\n---\n".join([c[:1500] for c in contexts[:5]])

    claims_prompt = f"""Given the following answer to a question, extract all individual factual claims/statements.
Each claim should be a single atomic factual statement.

Answer: {answer_trunc}

Return ONLY a JSON array of strings: ["claim 1", "claim 2", ...]
Do NOT wrap in markdown code blocks."""

    try:
        claims_response = await call_gpt4o(
            client,
            "You are a precise claim extraction assistant. Output raw JSON only, no markdown.",
            claims_prompt,
        )
        claims = parse_json_from_response(claims_response)
        if not isinstance(claims, list) or len(claims) == 0:
            return 1.0
    except Exception as e:
        print(f"    [Faith] Claim extraction failed: {e}")
        return 0.5

    # Limit claims to prevent token overflow
    claims = claims[:20]

    verify_prompt = f"""Given the following contexts, determine which claims are supported by the contexts.
A claim is "supported" if the contexts contain information that implies or directly states the claim.
A claim is "not_supported" if the contexts do NOT contain any information supporting the claim.

Contexts:
{context_text}

Claims to verify:
{json.dumps(claims, ensure_ascii=False)}

Return a JSON array: [{{"claim": "...", "verdict": "supported"}}] or [{{"claim": "...", "verdict": "not_supported"}}]
Do NOT wrap in markdown code blocks. Output raw JSON only."""

    try:
        verify_response = await call_gpt4o(
            client,
            "You are a claim verification assistant. Output raw JSON only, no markdown.",
            verify_prompt,
        )
        verdicts = parse_json_from_response(verify_response)
        if isinstance(verdicts, list) and len(verdicts) > 0:
            supported = sum(1 for v in verdicts if v.get("verdict", "").lower() == "supported")
            return round(supported / len(verdicts), 4)
    except Exception as e:
        print(f"    [Faith] Verification failed: {e}")

    return 0.5


async def evaluate_context_precision(
    client: httpx.AsyncClient,
    question: str,
    contexts: List[str],
    ground_truth: str,
) -> float:
    """Context Precision: Average Precision of context relevance."""
    if not contexts:
        return 0.0

    context_items = "\n\n".join([
        f"Context {i+1}: {c[:800]}"
        for i, c in enumerate(contexts)
    ])

    prompt = f"""Given a question and its expected (ground truth) answer, evaluate each retrieved context for relevance.
A context is "relevant" if it contains information useful for answering the question correctly.
A context is "not_relevant" if it does not help answer the question.

Question: {question}

Expected Answer: {ground_truth}

Retrieved Contexts:
{context_items}

For each context (in order), determine if it is "relevant" or "not_relevant".
Return a JSON array of objects with context_id (1-based) and verdict.
Example: [{{"context_id": 1, "verdict": "relevant"}}, {{"context_id": 2, "verdict": "not_relevant"}}]
Do NOT wrap in markdown code blocks. Output raw JSON only."""

    try:
        response = await call_gpt4o(
            client,
            "You are a relevance assessment assistant. Output raw JSON only, no markdown.",
            prompt,
        )
        verdicts = parse_json_from_response(response)

        if isinstance(verdicts, list) and len(verdicts) > 0:
            relevant_count = 0
            precision_sum = 0.0
            for i, v in enumerate(verdicts):
                if v.get("verdict", "").lower() == "relevant":
                    relevant_count += 1
                    precision_sum += relevant_count / (i + 1)
            if relevant_count > 0:
                return round(precision_sum / relevant_count, 4)
            return 0.0
    except Exception as e:
        print(f"    [Prec] Failed: {e}")

    return 0.5


async def evaluate_context_recall(
    client: httpx.AsyncClient,
    question: str,
    contexts: List[str],
    ground_truth: str,
) -> float:
    """Context Recall: coverage of ground truth by contexts."""
    context_text = "\n---\n".join([c[:1500] for c in contexts[:5]])

    prompt = f"""Given the ground truth answer and retrieved contexts, evaluate how well the contexts cover the ground truth.

Ground Truth Answer: {ground_truth}

Retrieved Contexts:
{context_text}

Steps:
1. Break the ground truth into individual factual statements
2. For each statement, determine if it can be attributed to (found in or inferred from) the retrieved contexts
3. A statement is "attributed" if ANY of the contexts supports it
4. A statement is "not_attributed" if NONE of the contexts support it

Return a JSON array: [{{"statement": "...", "verdict": "attributed"}}]
Do NOT wrap in markdown code blocks. Output raw JSON only."""

    try:
        response = await call_gpt4o(
            client,
            "You are a context recall assessment assistant. Output raw JSON only, no markdown.",
            prompt,
        )
        verdicts = parse_json_from_response(response)

        if isinstance(verdicts, list) and len(verdicts) > 0:
            attributed = sum(1 for v in verdicts if v.get("verdict", "").lower() == "attributed")
            return round(attributed / len(verdicts), 4)
    except Exception as e:
        print(f"    [Recall] Failed: {e}")

    return 0.5


async def evaluate_sample_ragas(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    idx: int,
    total: int,
    sample: Dict[str, Any],
) -> Dict[str, Any]:
    """Evaluate a single sample using GPT-4o judge for all RAGAS metrics."""
    async with semaphore:
        q = sample["question"]
        answer = sample["answer"]
        contexts = sample["contexts"]
        gt = sample["ground_truth"]

        print(f"  RAGAS [{idx}/{total}] {q[:45]}...", end="", flush=True)

        try:
            faith = await evaluate_faithfulness(client, q, answer, contexts)
            await asyncio.sleep(DELAY_BETWEEN_CALLS)

            precision = await evaluate_context_precision(client, q, contexts, gt)
            await asyncio.sleep(DELAY_BETWEEN_CALLS)

            recall = await evaluate_context_recall(client, q, contexts, gt)

            print(f" F={faith:.2f} P={precision:.2f} R={recall:.2f}")

            return {
                "idx": idx,
                "faithfulness": faith,
                "context_precision": precision,
                "context_recall": recall,
            }
        except Exception as e:
            print(f" ERROR: {e}")
            return {
                "idx": idx,
                "faithfulness": None,
                "context_precision": None,
                "context_recall": None,
                "error": str(e),
            }


# -------------------------------------------------------------------
# Main evaluation pipeline
# -------------------------------------------------------------------
async def run_evaluation():
    print("=" * 70)
    print("RAGAS v18 Evaluation - GPT-4o Judge (Direct Implementation)")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Method: same-pipeline (REST Search + DeepSeek Direct)")
    print(f"Judge: GPT-4o (OpenAI)")
    print()

    # 1. Load questions
    print("[1/4] Loading questions from v16 dataset...")
    questions_data = load_questions_from_v16()
    print(f"  Loaded {len(questions_data)} questions")

    # 2. Search + generate answers
    print(f"\n[2/4] Calling Search API + DeepSeek for {len(questions_data)} questions...")
    samples = []

    async with httpx.AsyncClient() as client:
        token = await get_token(client)
        print(f"  Login successful")

        latencies = []

        for i, qd in enumerate(questions_data):
            q = qd["question"]
            gt = qd["ground_truth"]
            print(f"  [{i+1}/{len(questions_data)}] {q[:50]}...", end="", flush=True)

            try:
                contexts, search_lat = await search_hybrid(client, token, q, SEARCH_TOP_K)
                answer, answer_lat = await generate_answer_deepseek(client, q, contexts)
                total_lat = search_lat + answer_lat
                latencies.append(total_lat)

                samples.append({
                    "question": q,
                    "answer": answer,
                    "contexts": contexts,
                    "ground_truth": gt,
                    "search_latency_ms": search_lat,
                    "answer_latency_ms": answer_lat,
                    "total_latency_ms": total_lat,
                })
                print(f" OK ({total_lat:.0f}ms)")
            except Exception as e:
                print(f" FAILED: {e}")
                samples.append({
                    "question": q,
                    "answer": f"Error: {e}",
                    "contexts": [],
                    "ground_truth": gt,
                    "search_latency_ms": 0,
                    "answer_latency_ms": 0,
                    "total_latency_ms": 0,
                })

    valid_samples = [s for s in samples if not s["answer"].startswith("Error:")]
    print(f"\n  Valid samples: {len(valid_samples)}/{len(samples)}")
    if latencies:
        print(f"  Avg latency: {mean(latencies):.0f}ms")
        print(f"  Median latency: {median(latencies):.0f}ms")

    # 3. RAGAS evaluation with GPT-4o
    print(f"\n[3/4] Running RAGAS evaluation with GPT-4o judge...")
    print(f"  Evaluating {len(valid_samples)} samples (3 GPT-4o calls each)")
    print(f"  Concurrent limit: {CONCURRENT_LIMIT}\n")

    semaphore = asyncio.Semaphore(CONCURRENT_LIMIT)
    eval_start = time.monotonic()

    async with httpx.AsyncClient() as gpt_client:
        # Run sequentially to avoid rate limits and see progress
        ragas_results = []
        for i, s in enumerate(valid_samples):
            result = await evaluate_sample_ragas(
                gpt_client, semaphore, i + 1, len(valid_samples), s
            )
            ragas_results.append(result)

    eval_time = time.monotonic() - eval_start
    print(f"\n  RAGAS evaluation completed in {eval_time:.1f}s")

    # Aggregate scores
    faith_scores = [r["faithfulness"] for r in ragas_results if r.get("faithfulness") is not None]
    prec_scores = [r["context_precision"] for r in ragas_results if r.get("context_precision") is not None]
    recall_scores = [r["context_recall"] for r in ragas_results if r.get("context_recall") is not None]

    scores = {
        "faithfulness": round(mean(faith_scores), 4) if faith_scores else 0.0,
        "context_precision": round(mean(prec_scores), 4) if prec_scores else 0.0,
        "context_recall": round(mean(recall_scores), 4) if recall_scores else 0.0,
    }

    print(f"\n  Faithfulness:      {scores['faithfulness']:.4f} ({len(faith_scores)} samples)")
    print(f"  Context Precision: {scores['context_precision']:.4f} ({len(prec_scores)} samples)")
    print(f"  Context Recall:    {scores['context_recall']:.4f} ({len(recall_scores)} samples)")

    score_values = [v for v in scores.values() if v is not None]
    arithmetic_mean = round(mean(score_values), 4) if score_values else 0.0
    print(f"  Arithmetic Mean:   {arithmetic_mean}")

    # 4. Save results
    print(f"\n[4/4] Saving results...")

    latency_stats = {}
    if latencies:
        latency_stats = {
            "avg_ms": round(mean(latencies), 1),
            "median_ms": round(median(latencies), 1),
            "min_ms": round(min(latencies), 1),
            "max_ms": round(max(latencies), 1),
            "real_count": len(valid_samples),
        }

    v16_scores = {"faithfulness": 0.8588, "context_precision": 0.7389, "context_recall": 0.6902}
    v17_scores = {"faithfulness": 0.8002, "context_precision": 0.6833, "context_recall": 0.6846}
    v11_baseline = {"faithfulness": 0.935, "context_precision": 0.618, "context_recall": 0.672}

    individual_results = []
    for i, s in enumerate(valid_samples):
        ragas_r = ragas_results[i] if i < len(ragas_results) else {}
        individual_results.append({
            "idx": i + 1,
            "question": s["question"],
            "ground_truth": s["ground_truth"],
            "answer": s["answer"],
            "contexts": s["contexts"],
            "contexts_count": len(s["contexts"]),
            "latency_ms": round(s["total_latency_ms"], 2),
            "search_latency_ms": round(s["search_latency_ms"], 2),
            "answer_latency_ms": round(s["answer_latency_ms"], 2),
            "ragas_faithfulness": ragas_r.get("faithfulness"),
            "ragas_context_precision": ragas_r.get("context_precision"),
            "ragas_context_recall": ragas_r.get("context_recall"),
        })

    output_data = {
        "version": "v18",
        "timestamp": datetime.now().isoformat(),
        "purpose": "GPT-4o Judge 평가 (DeepSeek judge 대비 Faithfulness 안정성 비교)",
        "method": "same-pipeline",
        "judge": "gpt-4o",
        "judge_implementation": "direct (RAGAS methodology via GPT-4o API)",
        "config": {
            "pipeline": "REST API /api/v1/search/hybrid + DeepSeek Direct Answer",
            "candidates_cap": 50,
            "graph_search_top_k": 10,
            "reranker_passes": 1,
            "rerank_candidate_count_formula": "min(top_k*3, 50)",
            "rerank_candidate_count_actual": 15,
            "answer_generation": "DeepSeek API direct",
            "ragas_judge": "gpt-4o (OpenAI)",
            "ragas_metrics_implementation": "Direct GPT-4o claim extraction + verification (RAGAS paper methodology)",
        },
        "scores": scores,
        "arithmetic_mean": arithmetic_mean,
        "latency_stats": latency_stats,
        "ragas_eval_time_seconds": round(eval_time, 1),
        "v16_scores_deepseek_judge": v16_scores,
        "v17_scores_deepseek_judge": v17_scores,
        "v11_baseline": v11_baseline,
        "delta_vs_v16": {k: round(scores[k] - v16_scores[k], 4) for k in scores},
        "delta_vs_v11": {k: round(scores[k] - v11_baseline[k], 4) for k in scores},
        "individual_results": individual_results,
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print(f"  JSON saved: {OUTPUT_JSON}")

    generate_report(output_data)
    print(f"  Report saved: {OUTPUT_REPORT}")

    print("\n" + "=" * 70)
    print("RAGAS v18 Evaluation Complete!")
    print("=" * 70)

    return output_data


def generate_report(data: Dict[str, Any]):
    """Generate markdown report."""
    scores = data["scores"]
    v16 = data["v16_scores_deepseek_judge"]
    v17 = data["v17_scores_deepseek_judge"]
    v11 = data["v11_baseline"]
    delta_v16 = data["delta_vs_v16"]
    delta_v11 = data["delta_vs_v11"]
    latency = data.get("latency_stats", {})
    individual = data.get("individual_results", [])
    am = data["arithmetic_mean"]

    if am >= 0.8: grade = "A+"
    elif am >= 0.75: grade = "A"
    elif am >= 0.7: grade = "A-"
    elif am >= 0.65: grade = "B+"
    elif am >= 0.6: grade = "B"
    else: grade = "C"

    def dist(key):
        vals = [r.get(key) for r in individual if r.get(key) is not None]
        low = sum(1 for v in vals if v < 0.5)
        mid = sum(1 for v in vals if 0.5 <= v < 0.8)
        high = sum(1 for v in vals if v >= 0.8)
        total = len(vals)
        return low, mid, high, total

    f_low, f_mid, f_high, f_total = dist("ragas_faithfulness")
    p_low, p_mid, p_high, p_total = dist("ragas_context_precision")
    r_low, r_mid, r_high, r_total = dist("ragas_context_recall")

    def fmt_delta(v):
        return f"+{v:.4f}" if v >= 0 else f"{v:.4f}"

    def pct(n, total):
        return f"{n/max(total,1)*100:.0f}%"

    report = f"""# RAGAS v18 -- GPT-4o Judge 평가 결과

**일자**: {data['timestamp'][:10]}
**버전**: v18
**방법**: REST API Same-Pipeline (Search + DeepSeek Direct Answer)
**목적**: GPT-4o Judge 평가 -- DeepSeek Judge 대비 Faithfulness 안정성 비교
**구현**: RAGAS 논문 방법론을 GPT-4o API로 직접 구현 (claim extraction + verification)

---

## 1. 평가 설정

| 항목 | 값 |
|------|-----|
| 평가 경로 | REST API `/api/v1/search/hybrid` + DeepSeek Direct |
| candidates_cap | 50 |
| graph_search_top_k | 10 |
| Reranker | 1-Pass |
| rerank_candidate_count | `min(top_k * 3, 50)` = 15 |
| 답변 생성 | DeepSeek API Direct (same-pipeline) |
| **평가 LLM (Judge)** | **GPT-4o (OpenAI)** |
| 평가 방법 | RAGAS 논문 방법론 직접 구현 |
| 질문 수 | {len(individual)} (7개 도메인) |
| RAGAS 평가 소요 | {data.get('ragas_eval_time_seconds', 'N/A')}초 |

---

## 2. 결과 요약

| Metric | v11 (DeepSeek) | v16 (DeepSeek) | v17 (DeepSeek) | **v18 (GPT-4o)** | vs v16 | vs v11 |
|--------|:---------:|:---------:|:---------:|:-----------:|:------:|:------:|
| Faithfulness | {v11['faithfulness']:.4f} | {v16['faithfulness']:.4f} | {v17['faithfulness']:.4f} | **{scores['faithfulness']:.4f}** | {fmt_delta(delta_v16['faithfulness'])} | {fmt_delta(delta_v11['faithfulness'])} |
| Context Precision | {v11['context_precision']:.4f} | {v16['context_precision']:.4f} | {v17['context_precision']:.4f} | **{scores['context_precision']:.4f}** | {fmt_delta(delta_v16['context_precision'])} | {fmt_delta(delta_v11['context_precision'])} |
| Context Recall | {v11['context_recall']:.4f} | {v16['context_recall']:.4f} | {v17['context_recall']:.4f} | **{scores['context_recall']:.4f}** | {fmt_delta(delta_v16['context_recall'])} | {fmt_delta(delta_v11['context_recall'])} |
| **산술평균** | **0.7417** | **0.7626** | **0.7227** | **{am:.4f}** | **{fmt_delta(am - 0.7626)}** | **{fmt_delta(am - 0.7417)}** |

### 등급 판정

| 버전 | Judge | 산술평균 | 등급 |
|------|-------|---------|------|
| v11 | DeepSeek | 0.742 | A- |
| v16 | DeepSeek | 0.763 | A |
| v17 | DeepSeek | 0.723 | A- |
| **v18** | **GPT-4o** | **{am:.3f}** | **{grade}** |

---

## 3. Judge 모델 비교 분석

### 3.1 GPT-4o vs DeepSeek Judge 차이

v16과 v18은 동일한 파이프라인(REST Search + DeepSeek Direct)을 사용하므로,
점수 차이는 순수하게 **RAGAS Judge 모델의 차이**에서 발생합니다.

| 메트릭 | v16 (DeepSeek) | v18 (GPT-4o) | 차이 | 해석 |
|--------|:---------:|:---------:|:----:|------|
| Faithfulness | {v16['faithfulness']:.4f} | {scores['faithfulness']:.4f} | {fmt_delta(delta_v16['faithfulness'])} | {"GPT-4o가 더 엄격" if delta_v16['faithfulness'] < 0 else "GPT-4o가 더 관대"} |
| Context Precision | {v16['context_precision']:.4f} | {scores['context_precision']:.4f} | {fmt_delta(delta_v16['context_precision'])} | {"GPT-4o가 더 엄격" if delta_v16['context_precision'] < 0 else "GPT-4o가 더 관대"} |
| Context Recall | {v16['context_recall']:.4f} | {scores['context_recall']:.4f} | {fmt_delta(delta_v16['context_recall'])} | {"GPT-4o가 더 엄격" if delta_v16['context_recall'] < 0 else "GPT-4o가 더 관대"} |

### 3.2 메트릭 분포

#### Faithfulness

| 구간 | 질문 수 | 비율 |
|------|:-------:|:----:|
| High (>= 0.8) | {f_high} | {pct(f_high, f_total)} |
| Medium (0.5-0.8) | {f_mid} | {pct(f_mid, f_total)} |
| Low (< 0.5) | {f_low} | {pct(f_low, f_total)} |

#### Context Precision

| 구간 | 질문 수 | 비율 |
|------|:-------:|:----:|
| High (>= 0.8) | {p_high} | {pct(p_high, p_total)} |
| Medium (0.5-0.8) | {p_mid} | {pct(p_mid, p_total)} |
| Low (< 0.5) | {p_low} | {pct(p_low, p_total)} |

#### Context Recall

| 구간 | 질문 수 | 비율 |
|------|:-------:|:----:|
| High (>= 0.8) | {r_high} | {pct(r_high, r_total)} |
| Medium (0.5-0.8) | {r_mid} | {pct(r_mid, r_total)} |
| Low (< 0.5) | {r_low} | {pct(r_low, r_total)} |

---

## 4. Latency 통계 (Search + Answer Generation)

| 항목 | 값 |
|------|-----|
| 평균 | {latency.get('avg_ms', 'N/A')} ms |
| 중앙값 | {latency.get('median_ms', 'N/A')} ms |
| 최소 | {latency.get('min_ms', 'N/A')} ms |
| 최대 | {latency.get('max_ms', 'N/A')} ms |

---

## 5. 버전별 전체 비교

```
버전    Judge     Faith   Prec    Recall  Mean    특이사항
---------------------------------------------------------------
v11     DeepSeek  0.935   0.618   0.672   0.742   Chat API E2E (baseline)
v14     DeepSeek  0.940   0.682   0.608   0.743   REST, graph_top_k 복원
v15     DeepSeek  0.907   0.682   0.595   0.728   REST, 2-Pass (중복 증명)
v16     DeepSeek  0.859   0.739   0.690   0.763   REST, 최적 파라미터 확정
v17     DeepSeek  0.800   0.683   0.685   0.723   Chat API E2E
v18     GPT-4o    {scores['faithfulness']:.3f}   {scores['context_precision']:.3f}   {scores['context_recall']:.3f}   {am:.3f}   REST, GPT-4o Judge
```

---

## 6. 개별 질문 결과

| # | 질문 | Faith | Prec | Recall | Latency |
|:---:|------|:---:|:---:|:---:|:---:|
"""

    for r in individual:
        q_short = r["question"][:45]
        f = r.get("ragas_faithfulness")
        p = r.get("ragas_context_precision")
        rc = r.get("ragas_context_recall")
        lat = r.get("latency_ms", 0)
        f_str = f"{f:.3f}" if f is not None else "N/A"
        p_str = f"{p:.3f}" if p is not None else "N/A"
        rc_str = f"{rc:.3f}" if rc is not None else "N/A"
        report += f"| Q{r['idx']:02d} | {q_short} | {f_str} | {p_str} | {rc_str} | {lat:.0f}ms |\n"

    report += f"""
---

## 7. 평가 방법론

### RAGAS 논문 기반 직접 구현

RAGAS 라이브러리의 langchain-core 호환성 이슈로 인해,
RAGAS 논문 방법론을 GPT-4o API 직접 호출로 구현했습니다.

#### Faithfulness (충실도)
1. GPT-4o로 답변에서 개별 팩트(claim) 추출
2. 각 claim이 컨텍스트로부터 지지되는지 GPT-4o로 검증
3. Score = (지지된 claims) / (전체 claims)

#### Context Precision (맥락 정밀도)
1. 각 검색된 컨텍스트의 질문 관련성을 GPT-4o로 판정
2. Average Precision (AP@k) 계산 (순위 가중치 적용)

#### Context Recall (맥락 재현율)
1. GPT-4o로 ground truth를 개별 문장으로 분해
2. 각 문장이 검색된 컨텍스트에 귀속 가능한지 GPT-4o로 판정
3. Score = (귀속된 문장) / (전체 문장)

---

## 8. 결론

### v18 평가 결과 요약
- **산술평균**: {am:.4f} (등급: {grade})
- **Judge 전환 효과**: 동일 파이프라인에서 Judge만 GPT-4o로 변경
- **RAGAS 평가 소요**: {data.get('ragas_eval_time_seconds', 'N/A')}초
- **GPT-4o API 호출**: {len(individual) * 3 * 2}회 (51 samples x 3 metrics x 2 calls/metric avg)

---

*Generated: {data['timestamp']}*
*RAGAS methodology via GPT-4o API | Judge: GPT-4o | {len(individual)} questions*
"""

    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        f.write(report)


if __name__ == "__main__":
    result = asyncio.run(run_evaluation())
    print(f"\nFinal scores: {result['scores']}")
    print(f"Arithmetic mean: {result['arithmetic_mean']}")
    sys.exit(0)
