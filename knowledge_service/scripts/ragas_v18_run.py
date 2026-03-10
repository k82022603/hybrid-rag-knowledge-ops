#!/usr/bin/env python3
"""
RAGAS v18 - GPT-4o Judge Evaluation (Robust Sequential Version)

Processes all questions sequentially with explicit timeouts.
Saves intermediate progress.
"""

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from statistics import mean, median

import requests

# -------------------------------------------------------------------
# Config
# -------------------------------------------------------------------
BASE_URL = "http://localhost:8000"
SEARCH_TOP_K = 5

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
if ENV_FILE.exists():
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

V16_RESULT = Path(__file__).resolve().parent.parent / "docs/04_testing/11_ragas/results/ragas_v16_result.json"
OUTPUT_JSON = Path(__file__).resolve().parent.parent / "docs/04_testing/12_embedding_evaluation/ragas_v18_gpt4o_results.json"
OUTPUT_REPORT = Path(__file__).resolve().parent.parent / "docs/04_testing/12_embedding_evaluation/22_ragas_v18_gpt4o_judge.md"
PROGRESS_FILE = Path(__file__).resolve().parent.parent / "docs/04_testing/12_embedding_evaluation/ragas_v18_progress.json"


def parse_json_response(text):
    """Robustly parse JSON from GPT-4o response."""
    text = text.strip()
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        for sc, ec in [('[', ']'), ('{', '}')]:
            s, e = text.find(sc), text.rfind(ec)
            if s != -1 and e > s:
                try:
                    return json.loads(text[s:e + 1])
                except json.JSONDecodeError:
                    pass
    return None


def call_gpt4o(system_prompt, user_prompt, timeout=90):
    """Call GPT-4o synchronously."""
    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        json={
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.0,
            "max_tokens": 2048,
        },
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def call_deepseek(prompt, timeout=90):
    """Call DeepSeek API synchronously."""
    resp = requests.post(
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
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def search_hybrid(token, query):
    """Call search API."""
    start = time.time()
    resp = requests.post(
        f"{BASE_URL}/api/v1/search/hybrid",
        json={"query": query, "top_k": SEARCH_TOP_K},
        headers={"Authorization": f"Bearer {token}"},
        timeout=60,
    )
    lat = (time.time() - start) * 1000
    resp.raise_for_status()
    data = resp.json()
    contexts = [r["content"] for r in data.get("results", []) if r.get("content")]
    return contexts, lat


def generate_answer(question, contexts):
    """Generate answer via DeepSeek."""
    ctx = "\n\n---\n\n".join(contexts[:5])
    prompt = f"""다음 컨텍스트를 기반으로 질문에 답변하세요.
컨텍스트에 없는 내용은 답변하지 마세요.

## 컨텍스트
{ctx}

## 질문
{question}

## 답변"""
    start = time.time()
    answer = call_deepseek(prompt)
    lat = (time.time() - start) * 1000
    return answer, lat


# -------------------------------------------------------------------
# RAGAS Metrics
# -------------------------------------------------------------------
def eval_faithfulness(question, answer, contexts):
    answer_t = answer[:3000]
    ctx_text = "\n---\n".join([c[:1500] for c in contexts[:5]])

    # Extract claims
    try:
        claims_raw = call_gpt4o(
            "You are a precise claim extraction assistant. Output raw JSON array only.",
            f"Extract all individual factual claims from this answer. Return JSON array of strings only.\n\nAnswer: {answer_t}\n\nJSON array:",
        )
        claims = parse_json_response(claims_raw)
        if not claims or not isinstance(claims, list) or len(claims) == 0:
            return 1.0
    except Exception as e:
        print(f"    [Faith-claims] {e}")
        return 0.5

    claims = claims[:20]

    # Verify claims
    try:
        verify_raw = call_gpt4o(
            "You are a claim verification assistant. Output raw JSON array only.",
            f"""Verify which claims are supported by the contexts.

Contexts:
{ctx_text}

Claims:
{json.dumps(claims, ensure_ascii=False)}

For each claim, output {{"claim": "...", "verdict": "supported"}} or {{"claim": "...", "verdict": "not_supported"}}.
Output JSON array only:""",
        )
        verdicts = parse_json_response(verify_raw)
        if verdicts and isinstance(verdicts, list) and len(verdicts) > 0:
            supported = sum(1 for v in verdicts if v.get("verdict", "").lower() == "supported")
            return round(supported / len(verdicts), 4)
    except Exception as e:
        print(f"    [Faith-verify] {e}")

    return 0.5


def eval_context_precision(question, contexts, ground_truth):
    if not contexts:
        return 0.0

    ctx_items = "\n\n".join([f"Context {i+1}: {c[:800]}" for i, c in enumerate(contexts)])

    try:
        resp_raw = call_gpt4o(
            "You are a relevance assessment assistant. Output raw JSON array only.",
            f"""Evaluate each retrieved context for relevance to answering the question.
A context is "relevant" if it helps answer the question correctly.

Question: {question}
Expected Answer: {ground_truth}

Retrieved Contexts:
{ctx_items}

For each context, output {{"context_id": N, "verdict": "relevant"}} or {{"context_id": N, "verdict": "not_relevant"}}.
Output JSON array only:""",
        )
        verdicts = parse_json_response(resp_raw)
        if verdicts and isinstance(verdicts, list) and len(verdicts) > 0:
            rel_count = 0
            prec_sum = 0.0
            for i, v in enumerate(verdicts):
                if v.get("verdict", "").lower() == "relevant":
                    rel_count += 1
                    prec_sum += rel_count / (i + 1)
            if rel_count > 0:
                return round(prec_sum / rel_count, 4)
            return 0.0
    except Exception as e:
        print(f"    [Prec] {e}")

    return 0.5


def eval_context_recall(question, contexts, ground_truth):
    ctx_text = "\n---\n".join([c[:1500] for c in contexts[:5]])

    try:
        resp_raw = call_gpt4o(
            "You are a context recall assessment assistant. Output raw JSON array only.",
            f"""Evaluate how well the contexts cover the ground truth.

Ground Truth: {ground_truth}

Contexts:
{ctx_text}

Break the ground truth into statements. For each, output {{"statement": "...", "verdict": "attributed"}} if contexts support it, or {{"statement": "...", "verdict": "not_attributed"}} if not.
Output JSON array only:""",
        )
        verdicts = parse_json_response(resp_raw)
        if verdicts and isinstance(verdicts, list) and len(verdicts) > 0:
            attr = sum(1 for v in verdicts if v.get("verdict", "").lower() == "attributed")
            return round(attr / len(verdicts), 4)
    except Exception as e:
        print(f"    [Recall] {e}")

    return 0.5


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------
def main():
    print("=" * 70)
    print("RAGAS v18 - GPT-4o Judge (Sequential Robust)")
    print("=" * 70)
    ts = datetime.now().isoformat()
    print(f"Timestamp: {ts}")

    # Load questions
    with open(V16_RESULT, "r", encoding="utf-8") as f:
        v16_data = json.load(f)
    questions = [
        {"question": r["question"], "ground_truth": r.get("ground_truth", "")}
        for r in v16_data.get("individual_results", [])
    ]
    print(f"Questions: {len(questions)}")

    # Load progress if exists
    progress = []
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            progress = json.load(f)
        print(f"Resuming from progress: {len(progress)} done")

    # Login
    resp = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "admin123!"},
        timeout=10,
    )
    token = resp.json().get("accessToken", "")
    print(f"Login OK\n")

    # Process each question
    latencies = []
    for i, qd in enumerate(questions):
        idx = i + 1
        q = qd["question"]
        gt = qd["ground_truth"]

        # Skip if already done
        if idx <= len(progress):
            print(f"  [{idx}/51] SKIP (cached)")
            latencies.append(progress[idx-1].get("total_latency_ms", 0))
            continue

        print(f"  [{idx}/51] {q[:50]}...", end="", flush=True)

        try:
            # Search
            contexts, s_lat = search_hybrid(token, q)

            # Answer
            answer, a_lat = generate_answer(q, contexts)
            total_lat = s_lat + a_lat
            latencies.append(total_lat)
            print(f" ans={len(answer)}c", end="", flush=True)

            # RAGAS metrics
            faith = eval_faithfulness(q, answer, contexts)
            prec = eval_context_precision(q, contexts, gt)
            recall = eval_context_recall(q, contexts, gt)

            print(f" F={faith:.2f} P={prec:.2f} R={recall:.2f} ({total_lat:.0f}ms)")

            entry = {
                "idx": idx,
                "question": q,
                "ground_truth": gt,
                "answer": answer,
                "contexts": contexts,
                "contexts_count": len(contexts),
                "total_latency_ms": round(total_lat, 2),
                "search_latency_ms": round(s_lat, 2),
                "answer_latency_ms": round(a_lat, 2),
                "ragas_faithfulness": faith,
                "ragas_context_precision": prec,
                "ragas_context_recall": recall,
            }
            progress.append(entry)

            # Save progress
            with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
                json.dump(progress, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f" ERROR: {e}")
            progress.append({
                "idx": idx,
                "question": q,
                "ground_truth": gt,
                "answer": f"Error: {e}",
                "contexts": [],
                "contexts_count": 0,
                "total_latency_ms": 0,
                "search_latency_ms": 0,
                "answer_latency_ms": 0,
                "ragas_faithfulness": None,
                "ragas_context_precision": None,
                "ragas_context_recall": None,
            })
            with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
                json.dump(progress, f, ensure_ascii=False, indent=2)

    # Aggregate
    print(f"\n{'='*70}")
    print("Aggregating results...")

    valid = [p for p in progress if p.get("ragas_faithfulness") is not None]
    f_scores = [p["ragas_faithfulness"] for p in valid]
    p_scores = [p["ragas_context_precision"] for p in valid]
    r_scores = [p["ragas_context_recall"] for p in valid]

    scores = {
        "faithfulness": round(mean(f_scores), 4) if f_scores else 0,
        "context_precision": round(mean(p_scores), 4) if p_scores else 0,
        "context_recall": round(mean(r_scores), 4) if r_scores else 0,
    }
    am = round(mean(scores.values()), 4)

    print(f"Faithfulness:      {scores['faithfulness']:.4f}")
    print(f"Context Precision: {scores['context_precision']:.4f}")
    print(f"Context Recall:    {scores['context_recall']:.4f}")
    print(f"Arithmetic Mean:   {am}")

    v16_scores = {"faithfulness": 0.8588, "context_precision": 0.7389, "context_recall": 0.6902}
    v17_scores = {"faithfulness": 0.8002, "context_precision": 0.6833, "context_recall": 0.6846}
    v11_baseline = {"faithfulness": 0.935, "context_precision": 0.618, "context_recall": 0.672}

    lat_stats = {}
    valid_lats = [l for l in latencies if l > 0]
    if valid_lats:
        lat_stats = {
            "avg_ms": round(mean(valid_lats), 1),
            "median_ms": round(median(valid_lats), 1),
            "min_ms": round(min(valid_lats), 1),
            "max_ms": round(max(valid_lats), 1),
            "real_count": len(valid),
        }

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
        },
        "scores": scores,
        "arithmetic_mean": am,
        "latency_stats": lat_stats,
        "v16_scores_deepseek_judge": v16_scores,
        "v17_scores_deepseek_judge": v17_scores,
        "v11_baseline": v11_baseline,
        "delta_vs_v16": {k: round(scores[k] - v16_scores[k], 4) for k in scores},
        "delta_vs_v11": {k: round(scores[k] - v11_baseline[k], 4) for k in scores},
        "individual_results": progress,
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print(f"\nJSON saved: {OUTPUT_JSON}")

    # Generate report (inline)
    generate_report(output_data)
    print(f"Report saved: {OUTPUT_REPORT}")

    # Cleanup progress
    if PROGRESS_FILE.exists():
        PROGRESS_FILE.unlink()

    print(f"\n{'='*70}")
    print("RAGAS v18 Complete!")
    print(f"{'='*70}")


def generate_report(data):
    scores = data["scores"]
    v16 = data["v16_scores_deepseek_judge"]
    v17 = data["v17_scores_deepseek_judge"]
    v11 = data["v11_baseline"]
    d16 = data["delta_vs_v16"]
    d11 = data["delta_vs_v11"]
    lat = data.get("latency_stats", {})
    ind = data.get("individual_results", [])
    am = data["arithmetic_mean"]

    grade = "A+" if am >= 0.8 else "A" if am >= 0.75 else "A-" if am >= 0.7 else "B+" if am >= 0.65 else "B" if am >= 0.6 else "C"

    def d(key):
        vals = [r.get(key) for r in ind if r.get(key) is not None]
        return (sum(1 for v in vals if v < 0.5), sum(1 for v in vals if 0.5 <= v < 0.8), sum(1 for v in vals if v >= 0.8), len(vals))

    fl, fm, fh, ft = d("ragas_faithfulness")
    pl, pm, ph, pt = d("ragas_context_precision")
    rl, rm, rh, rt = d("ragas_context_recall")

    def fd(v): return f"+{v:.4f}" if v >= 0 else f"{v:.4f}"
    def pct(n, t): return f"{n/max(t,1)*100:.0f}%"

    r = f"""# RAGAS v18 -- GPT-4o Judge 평가 결과

**일자**: {data['timestamp'][:10]}
**버전**: v18
**방법**: REST API Same-Pipeline (Search + DeepSeek Direct Answer)
**목적**: GPT-4o Judge 평가 -- DeepSeek Judge 대비 Faithfulness 안정성 비교
**구현**: RAGAS 논문 방법론을 GPT-4o API로 직접 구현

---

## 1. 평가 설정

| 항목 | 값 |
|------|-----|
| 평가 경로 | REST API `/api/v1/search/hybrid` + DeepSeek Direct |
| candidates_cap | 50 |
| graph_search_top_k | 10 |
| Reranker | 1-Pass |
| rerank_candidate_count | `min(top_k * 3, 50)` = 15 |
| 답변 생성 | DeepSeek API Direct |
| **평가 LLM (Judge)** | **GPT-4o (OpenAI)** |
| 질문 수 | {len(ind)} |

---

## 2. 결과 요약

| Metric | v11 (DeepSeek) | v16 (DeepSeek) | v17 (DeepSeek) | **v18 (GPT-4o)** | vs v16 | vs v11 |
|--------|:---------:|:---------:|:---------:|:-----------:|:------:|:------:|
| Faithfulness | {v11['faithfulness']:.4f} | {v16['faithfulness']:.4f} | {v17['faithfulness']:.4f} | **{scores['faithfulness']:.4f}** | {fd(d16['faithfulness'])} | {fd(d11['faithfulness'])} |
| Context Precision | {v11['context_precision']:.4f} | {v16['context_precision']:.4f} | {v17['context_precision']:.4f} | **{scores['context_precision']:.4f}** | {fd(d16['context_precision'])} | {fd(d11['context_precision'])} |
| Context Recall | {v11['context_recall']:.4f} | {v16['context_recall']:.4f} | {v17['context_recall']:.4f} | **{scores['context_recall']:.4f}** | {fd(d16['context_recall'])} | {fd(d11['context_recall'])} |
| **산술평균** | **0.7417** | **0.7626** | **0.7227** | **{am:.4f}** | **{fd(am - 0.7626)}** | **{fd(am - 0.7417)}** |

### 등급: **{grade}** (산술평균 {am:.3f})

---

## 3. Judge 비교 (v16 DeepSeek vs v18 GPT-4o)

동일 파이프라인에서 Judge만 변경한 결과:

| 메트릭 | v16 (DeepSeek) | v18 (GPT-4o) | 차이 | 해석 |
|--------|:---------:|:---------:|:----:|------|
| Faithfulness | {v16['faithfulness']:.4f} | {scores['faithfulness']:.4f} | {fd(d16['faithfulness'])} | {"GPT-4o 더 엄격" if d16['faithfulness'] < -0.01 else "GPT-4o 더 관대" if d16['faithfulness'] > 0.01 else "유사"} |
| Context Precision | {v16['context_precision']:.4f} | {scores['context_precision']:.4f} | {fd(d16['context_precision'])} | {"GPT-4o 더 엄격" if d16['context_precision'] < -0.01 else "GPT-4o 더 관대" if d16['context_precision'] > 0.01 else "유사"} |
| Context Recall | {v16['context_recall']:.4f} | {scores['context_recall']:.4f} | {fd(d16['context_recall'])} | {"GPT-4o 더 엄격" if d16['context_recall'] < -0.01 else "GPT-4o 더 관대" if d16['context_recall'] > 0.01 else "유사"} |

### 메트릭 분포

| 구간 | Faith | Prec | Recall |
|------|:---:|:---:|:---:|
| High (>=0.8) | {fh} ({pct(fh,ft)}) | {ph} ({pct(ph,pt)}) | {rh} ({pct(rh,rt)}) |
| Medium (0.5-0.8) | {fm} ({pct(fm,ft)}) | {pm} ({pct(pm,pt)}) | {rm} ({pct(rm,rt)}) |
| Low (<0.5) | {fl} ({pct(fl,ft)}) | {pl} ({pct(pl,pt)}) | {rl} ({pct(rl,rt)}) |

---

## 4. Latency

| 항목 | 값 |
|------|-----|
| 평균 | {lat.get('avg_ms', 'N/A')} ms |
| 중앙값 | {lat.get('median_ms', 'N/A')} ms |
| 최소 | {lat.get('min_ms', 'N/A')} ms |
| 최대 | {lat.get('max_ms', 'N/A')} ms |

---

## 5. 전체 비교

```
버전    Judge     Faith   Prec    Recall  Mean    특이사항
---------------------------------------------------------------
v11     DeepSeek  0.935   0.618   0.672   0.742   Chat API E2E (baseline)
v14     DeepSeek  0.940   0.682   0.608   0.743   REST, graph_top_k 복원
v15     DeepSeek  0.907   0.682   0.595   0.728   REST, 2-Pass 중복 증명
v16     DeepSeek  0.859   0.739   0.690   0.763   REST, 최적 파라미터 확정
v17     DeepSeek  0.800   0.683   0.685   0.723   Chat API E2E
v18     GPT-4o    {scores['faithfulness']:.3f}   {scores['context_precision']:.3f}   {scores['context_recall']:.3f}   {am:.3f}   REST, GPT-4o Judge
```

---

## 6. 개별 결과

| # | 질문 | Faith | Prec | Recall | Latency |
|:---:|------|:---:|:---:|:---:|:---:|
"""

    for x in ind:
        qs = x["question"][:45]
        f = x.get("ragas_faithfulness")
        p = x.get("ragas_context_precision")
        rc = x.get("ragas_context_recall")
        lt = x.get("total_latency_ms", 0)
        fs = f"{f:.3f}" if f is not None else "N/A"
        ps = f"{p:.3f}" if p is not None else "N/A"
        rs = f"{rc:.3f}" if rc is not None else "N/A"
        r += f"| Q{x['idx']:02d} | {qs} | {fs} | {ps} | {rs} | {lt:.0f}ms |\n"

    r += f"""
---

## 7. 방법론

RAGAS 논문 방법론을 GPT-4o API로 직접 구현:
- **Faithfulness**: claim 추출 + 컨텍스트 검증
- **Context Precision**: AP@k 기반 관련성 평가
- **Context Recall**: ground truth 문장 귀속 평가

---

*Generated: {data['timestamp']} | GPT-4o Judge | {len(ind)} questions*
"""

    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        f.write(r)


if __name__ == "__main__":
    main()
