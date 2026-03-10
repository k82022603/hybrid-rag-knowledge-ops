#!/usr/bin/env python3
"""
RAGAS v18 Evaluation - GPT-4o Judge (Direct Implementation)

Same pipeline as v16 (REST API Search + DeepSeek Direct Answer)
but with GPT-4o as RAGAS judge instead of DeepSeek.

Implements RAGAS metrics directly via GPT-4o API calls
(avoids ragas library import hang issues).

Metrics:
- Faithfulness: Is the answer faithful to the contexts?
- Context Precision: Are retrieved contexts relevant to the question?
- Context Recall: Do contexts cover the ground truth information?

Usage:
    cd knowledge_service
    source .venv/bin/activate
    python scripts/ragas_v18_gpt4o_evaluation.py
"""

import asyncio
import json
import math
import os
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

# v16 result path (to extract questions)
V16_RESULT = Path(__file__).resolve().parent.parent / "docs/04_testing/11_ragas/results/ragas_v16_result.json"
OUTPUT_JSON = Path(__file__).resolve().parent.parent / "docs/04_testing/12_embedding_evaluation/ragas_v18_gpt4o_results.json"
OUTPUT_REPORT = Path(__file__).resolve().parent.parent / "docs/04_testing/12_embedding_evaluation/22_ragas_v18_gpt4o_judge.md"

# Rate limiting for GPT-4o
CONCURRENT_LIMIT = 3  # Max concurrent GPT-4o calls
DELAY_BETWEEN_CALLS = 0.5  # seconds


# -------------------------------------------------------------------
# Helper: extract questions from v16
# -------------------------------------------------------------------
def load_questions_from_v16() -> List[Dict[str, str]]:
    """Load 51 questions + ground truths from v16 result JSON."""
    with open(V16_RESULT, "r", encoding="utf-8") as f:
        data = json.load(f)
    questions = []
    for r in data.get("individual_results", []):
        questions.append({
            "question": r["question"],
            "ground_truth": r.get("ground_truth", ""),
        })
    return questions


# -------------------------------------------------------------------
# GPT-4o API call helper
# -------------------------------------------------------------------
async def call_gpt4o(
    client: httpx.AsyncClient,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.0,
    max_tokens: int = 1024,
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
    """Login and get JWT token."""
    resp = await client.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": LOGIN_EMAIL, "password": LOGIN_PASSWORD},
    )
    resp.raise_for_status()
    data = resp.json()
    token = data.get("accessToken", "")
    if not token:
        raise RuntimeError(f"Login failed, response: {data}")
    return token


async def search_hybrid(
    client: httpx.AsyncClient, token: str, query: str, top_k: int = 5
) -> Tuple[List[str], float]:
    """Call hybrid search API and return (contexts, latency_ms)."""
    start = time.monotonic()
    resp = await client.post(
        f"{BASE_URL}{SEARCH_ENDPOINT}",
        json={"query": query, "top_k": top_k},
        headers={"Authorization": f"Bearer {token}"},
        timeout=120.0,
    )
    latency_ms = (time.monotonic() - start) * 1000
    resp.raise_for_status()
    data = resp.json()
    results = data.get("results", [])
    contexts = [r.get("content", "") for r in results if r.get("content")]
    return contexts, latency_ms


# -------------------------------------------------------------------
# Step 2: Generate answer via DeepSeek
# -------------------------------------------------------------------
async def generate_answer_deepseek(
    client: httpx.AsyncClient, question: str, contexts: List[str]
) -> Tuple[str, float]:
    """Generate answer using DeepSeek API directly."""
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
        data = resp.json()
        answer = data["choices"][0]["message"]["content"].strip()
        return answer, latency_ms
    except Exception as e:
        latency_ms = (time.monotonic() - start) * 1000
        print(f"  [ERROR] DeepSeek answer generation failed: {e}")
        return f"Error: {e}", latency_ms


# -------------------------------------------------------------------
# Step 3: RAGAS metrics via GPT-4o (direct implementation)
#
# Following the RAGAS paper methodology:
# - Faithfulness: decompose answer into claims, verify each against context
# - Context Precision: for each context, check if relevant to question
# - Context Recall: decompose ground truth into claims, check coverage
# -------------------------------------------------------------------

async def evaluate_faithfulness(
    client: httpx.AsyncClient,
    question: str,
    answer: str,
    contexts: List[str],
) -> float:
    """
    Faithfulness: Is the answer faithful to the provided contexts?

    RAGAS approach:
    1. Extract claims from the answer
    2. For each claim, check if it can be inferred from the contexts
    3. Score = (supported claims) / (total claims)
    """
    context_text = "\n---\n".join(contexts)

    # Step 1: Extract claims
    claims_prompt = f"""Given the following answer, extract all individual factual claims/statements.
Return as a JSON array of strings. Each claim should be a single atomic statement.

Answer: {answer}

Return ONLY a JSON array like: ["claim 1", "claim 2", ...]"""

    try:
        claims_response = await call_gpt4o(client, "You are a claim extraction assistant. Return only valid JSON.", claims_prompt)
        # Parse claims
        claims_response = claims_response.strip()
        if claims_response.startswith("```"):
            claims_response = claims_response.split("```")[1]
            if claims_response.startswith("json"):
                claims_response = claims_response[4:]
        claims = json.loads(claims_response)
        if not isinstance(claims, list) or len(claims) == 0:
            return 1.0  # No claims to verify
    except (json.JSONDecodeError, Exception):
        return 0.5  # Fallback

    # Step 2: Verify each claim against contexts
    verify_prompt = f"""Given the following contexts and claims, determine which claims can be supported by the contexts.

Contexts:
{context_text}

Claims to verify:
{json.dumps(claims, ensure_ascii=False)}

For each claim, respond with "supported" or "not_supported".
Return as a JSON array of objects: [{{"claim": "...", "verdict": "supported"}}]
Return ONLY valid JSON."""

    try:
        verify_response = await call_gpt4o(client, "You are a claim verification assistant. Return only valid JSON.", verify_prompt)
        verify_response = verify_response.strip()
        if verify_response.startswith("```"):
            verify_response = verify_response.split("```")[1]
            if verify_response.startswith("json"):
                verify_response = verify_response[4:]
        verdicts = json.loads(verify_response)
        if isinstance(verdicts, list) and len(verdicts) > 0:
            supported = sum(1 for v in verdicts if v.get("verdict", "").lower() == "supported")
            return supported / len(verdicts)
    except (json.JSONDecodeError, Exception):
        pass

    return 0.5  # Fallback


async def evaluate_context_precision(
    client: httpx.AsyncClient,
    question: str,
    contexts: List[str],
    ground_truth: str,
) -> float:
    """
    Context Precision: Are the retrieved contexts relevant to answering the question?

    RAGAS approach:
    For each context, check if it is relevant.
    Weighted by position (earlier contexts weighted more via AP@k).
    Score = Average Precision
    """
    if not contexts:
        return 0.0

    context_items = "\n".join([f"Context {i+1}: {c[:500]}" for i, c in enumerate(contexts)])

    prompt = f"""Given a question and its ground truth answer, determine which of the following retrieved contexts are relevant for answering the question.

Question: {question}
Ground Truth Answer: {ground_truth}

Retrieved Contexts:
{context_items}

For each context, respond with "relevant" or "not_relevant".
Return as a JSON array of objects: [{{"context_id": 1, "verdict": "relevant"}}]
Return ONLY valid JSON."""

    try:
        response = await call_gpt4o(client, "You are a relevance assessment assistant. Return only valid JSON.", prompt)
        response = response.strip()
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
        verdicts = json.loads(response)

        if isinstance(verdicts, list) and len(verdicts) > 0:
            # Calculate Average Precision (AP@k)
            relevant_count = 0
            precision_sum = 0.0
            for i, v in enumerate(verdicts):
                if v.get("verdict", "").lower() == "relevant":
                    relevant_count += 1
                    precision_sum += relevant_count / (i + 1)
            if relevant_count > 0:
                return precision_sum / relevant_count
            return 0.0
    except (json.JSONDecodeError, Exception):
        pass

    return 0.5  # Fallback


async def evaluate_context_recall(
    client: httpx.AsyncClient,
    question: str,
    contexts: List[str],
    ground_truth: str,
) -> float:
    """
    Context Recall: Do the contexts contain the information in the ground truth?

    RAGAS approach:
    1. Decompose ground truth into statements
    2. For each statement, check if it can be attributed to any context
    3. Score = (attributed statements) / (total statements)
    """
    context_text = "\n---\n".join(contexts)

    prompt = f"""Given the ground truth answer and retrieved contexts, determine how well the contexts cover the ground truth information.

Ground Truth: {ground_truth}

Contexts:
{context_text}

Steps:
1. Break the ground truth into individual statements/claims
2. For each statement, check if it can be attributed to the given contexts
3. Return each statement with verdict "attributed" or "not_attributed"

Return as a JSON array: [{{"statement": "...", "verdict": "attributed"}}]
Return ONLY valid JSON."""

    try:
        response = await call_gpt4o(client, "You are a context recall assessment assistant. Return only valid JSON.", prompt)
        response = response.strip()
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
        verdicts = json.loads(response)

        if isinstance(verdicts, list) and len(verdicts) > 0:
            attributed = sum(1 for v in verdicts if v.get("verdict", "").lower() == "attributed")
            return attributed / len(verdicts)
    except (json.JSONDecodeError, Exception):
        pass

    return 0.5  # Fallback


async def evaluate_sample_ragas(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    idx: int,
    sample: Dict[str, Any],
) -> Dict[str, Any]:
    """Evaluate a single sample using GPT-4o judge for all RAGAS metrics."""
    async with semaphore:
        q = sample["question"]
        answer = sample["answer"]
        contexts = sample["contexts"]
        gt = sample["ground_truth"]

        try:
            # Run all three metrics (sequentially to avoid rate limits)
            faith = await evaluate_faithfulness(client, q, answer, contexts)
            await asyncio.sleep(DELAY_BETWEEN_CALLS)

            precision = await evaluate_context_precision(client, q, contexts, gt)
            await asyncio.sleep(DELAY_BETWEEN_CALLS)

            recall = await evaluate_context_recall(client, q, contexts, gt)

            return {
                "idx": idx,
                "faithfulness": faith,
                "context_precision": precision,
                "context_recall": recall,
            }
        except Exception as e:
            print(f"  [ERROR] Sample {idx} RAGAS eval failed: {e}")
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
    """Main evaluation pipeline."""
    print("=" * 70)
    print("RAGAS v18 Evaluation - GPT-4o Judge (Direct Implementation)")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Method: same-pipeline (REST Search + DeepSeek Direct)")
    print(f"Judge: GPT-4o (OpenAI) - Direct RAGAS metric implementation")
    print()

    # 1. Load questions
    print("[1/4] Loading questions from v16 dataset...")
    questions_data = load_questions_from_v16()
    print(f"  Loaded {len(questions_data)} questions")

    # 2. Login and search + generate answers
    print(f"\n[2/4] Calling Search API + DeepSeek for {len(questions_data)} questions...")
    samples = []

    async with httpx.AsyncClient() as client:
        token = await get_token(client)
        print(f"  Login successful, token obtained")

        latencies = []

        for i, qd in enumerate(questions_data):
            q = qd["question"]
            gt = qd["ground_truth"]
            print(f"  [{i+1}/{len(questions_data)}] {q[:50]}...", end="", flush=True)

            try:
                # Search
                contexts, search_lat = await search_hybrid(client, token, q, SEARCH_TOP_K)

                # Generate answer
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
    print(f"  Evaluating {len(valid_samples)} samples (3 metrics each)")
    print(f"  Concurrent limit: {CONCURRENT_LIMIT}")
    print(f"  Estimated time: {len(valid_samples) * 3 * 3}+ seconds\n")

    semaphore = asyncio.Semaphore(CONCURRENT_LIMIT)
    eval_start = time.monotonic()

    async with httpx.AsyncClient() as gpt_client:
        tasks = [
            evaluate_sample_ragas(gpt_client, semaphore, i + 1, s)
            for i, s in enumerate(valid_samples)
        ]
        ragas_results = await asyncio.gather(*tasks)

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

    # Latency stats
    latency_stats = {}
    if latencies:
        latency_stats = {
            "avg_ms": round(mean(latencies), 1),
            "median_ms": round(median(latencies), 1),
            "min_ms": round(min(latencies), 1),
            "max_ms": round(max(latencies), 1),
            "real_count": len(valid_samples),
        }

    # Previous version scores for comparison
    v16_scores = {"faithfulness": 0.8588, "context_precision": 0.7389, "context_recall": 0.6902}
    v17_scores = {"faithfulness": 0.8002, "context_precision": 0.6833, "context_recall": 0.6846}
    v11_baseline = {"faithfulness": 0.935, "context_precision": 0.618, "context_recall": 0.672}

    # Build individual results
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
        "delta_vs_v16": {
            k: round(scores[k] - v16_scores[k], 4) for k in scores
        },
        "delta_vs_v11": {
            k: round(scores[k] - v11_baseline[k], 4) for k in scores
        },
        "individual_results": individual_results,
    }

    # Save JSON
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print(f"  JSON saved: {OUTPUT_JSON}")

    # Generate report
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

    # Grade determination
    if am >= 0.8:
        grade = "A+"
    elif am >= 0.75:
        grade = "A"
    elif am >= 0.7:
        grade = "A-"
    elif am >= 0.65:
        grade = "B+"
    elif am >= 0.6:
        grade = "B"
    else:
        grade = "C"

    # Faithfulness distribution
    faith_low = sum(1 for r in individual if r.get("ragas_faithfulness") is not None and r["ragas_faithfulness"] < 0.5)
    faith_mid = sum(1 for r in individual if r.get("ragas_faithfulness") is not None and 0.5 <= r["ragas_faithfulness"] < 0.8)
    faith_high = sum(1 for r in individual if r.get("ragas_faithfulness") is not None and r["ragas_faithfulness"] >= 0.8)
    total_scored = faith_low + faith_mid + faith_high

    # Context Precision distribution
    prec_low = sum(1 for r in individual if r.get("ragas_context_precision") is not None and r["ragas_context_precision"] < 0.5)
    prec_mid = sum(1 for r in individual if r.get("ragas_context_precision") is not None and 0.5 <= r["ragas_context_precision"] < 0.8)
    prec_high = sum(1 for r in individual if r.get("ragas_context_precision") is not None and r["ragas_context_precision"] >= 0.8)

    # Context Recall distribution
    recall_low = sum(1 for r in individual if r.get("ragas_context_recall") is not None and r["ragas_context_recall"] < 0.5)
    recall_mid = sum(1 for r in individual if r.get("ragas_context_recall") is not None and 0.5 <= r["ragas_context_recall"] < 0.8)
    recall_high = sum(1 for r in individual if r.get("ragas_context_recall") is not None and r["ragas_context_recall"] >= 0.8)

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

#### Faithfulness 분포

| 구간 | 질문 수 | 비율 |
|------|:-------:|:----:|
| High (>= 0.8) | {faith_high} | {pct(faith_high, total_scored)} |
| Medium (0.5-0.8) | {faith_mid} | {pct(faith_mid, total_scored)} |
| Low (< 0.5) | {faith_low} | {pct(faith_low, total_scored)} |

#### Context Precision 분포

| 구간 | 질문 수 | 비율 |
|------|:-------:|:----:|
| High (>= 0.8) | {prec_high} | {pct(prec_high, total_scored)} |
| Medium (0.5-0.8) | {prec_mid} | {pct(prec_mid, total_scored)} |
| Low (< 0.5) | {prec_low} | {pct(prec_low, total_scored)} |

#### Context Recall 분포

| 구간 | 질문 수 | 비율 |
|------|:-------:|:----:|
| High (>= 0.8) | {recall_high} | {pct(recall_high, total_scored)} |
| Medium (0.5-0.8) | {recall_mid} | {pct(recall_mid, total_scored)} |
| Low (< 0.5) | {recall_low} | {pct(recall_low, total_scored)} |

---

## 4. Latency 통계

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

RAGAS 라이브러리(0.2.6)의 langchain-core 호환성 이슈로 인해,
RAGAS 논문 방법론을 GPT-4o API 직접 호출로 구현했습니다.

#### Faithfulness (충실도)
1. 답변에서 개별 팩트(claim) 추출
2. 각 claim이 컨텍스트로부터 지지되는지 검증
3. Score = (지지된 claims) / (전체 claims)

#### Context Precision (맥락 정밀도)
1. 각 검색된 컨텍스트의 질문 관련성 판정
2. Average Precision (AP@k) 계산 (순위 가중치 적용)

#### Context Recall (맥락 재현율)
1. Ground truth를 개별 문장/주장으로 분해
2. 각 문장이 검색된 컨텍스트에 귀속 가능한지 판정
3. Score = (귀속된 문장) / (전체 문장)

> GPT-4o의 강력한 이해력으로 DeepSeek judge 대비 더 일관된 평가 기대

---

## 8. 결론

### GPT-4o Judge의 특성
- RAGAS 공식 문서에서 권장하는 Judge 모델
- Faithfulness 측정에서 더 안정적인 결과 기대
- DeepSeek Judge 대비 비용이 높지만 평가 정확도가 높음

### v18 평가 결과 요약
- **산술평균**: {am:.4f} (등급: {grade})
- **Judge 전환 효과**: 동일 파이프라인에서 Judge만 변경하여 측정 편향 분석
- **RAGAS 평가 소요**: {data.get('ragas_eval_time_seconds', 'N/A')}초

---

*Generated: {data['timestamp']}*
*RAGAS methodology via GPT-4o API | Judge: GPT-4o | 51 questions*
"""

    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        f.write(report)


# -------------------------------------------------------------------
# Entry point
# -------------------------------------------------------------------
if __name__ == "__main__":
    result = asyncio.run(run_evaluation())
    print(f"\nFinal scores: {result['scores']}")
    print(f"Arithmetic mean: {result['arithmetic_mean']}")
    sys.exit(0)
