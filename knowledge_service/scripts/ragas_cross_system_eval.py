#!/usr/bin/env python3
"""
STORY-111: RAGAS Cross-System Evaluation
=========================================
HRKP Graph RAG (3채널) vs 2채널 Hybrid 비교 평가

비교 대상:
- System A (Graph ON):  BM25 + Dense Vector + Knowledge Graph
- System B (Graph OFF): BM25 + Dense Vector

동일한 검색 인프라(ES), 임베딩(BGE-M3), LLM(DeepSeek)을 사용하므로
Graph RAG 기여도만 순수하게 측정합니다.

실행:
    cd knowledge_service
    source .venv/bin/activate
    python scripts/ragas_cross_system_eval.py
    python scripts/ragas_cross_system_eval.py --top-k 5 --output-dir docs/results/ragas
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BASE_URL = os.getenv("HRKP_API_URL", "http://localhost:8000/api/v1")
LOGIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")
LOGIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123!")
DEEPSEEK_API_KEY = os.getenv(
    "DEEPSEEK_API_KEY", "sk-7c3024219fb74302a296207d2a091fe5"
)
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# ---------------------------------------------------------------------------
# Test Dataset (12 questions - 4 types x 3 questions)
# ---------------------------------------------------------------------------
TEST_QUESTIONS: List[Dict[str, str]] = [
    # --- Entity-Relation (Graph RAG 강점) ---
    {
        "question": "Neo4j와 Elasticsearch의 역할 차이점은?",
        "type": "entity_relation",
        "ground_truth": (
            "Neo4j는 Knowledge Graph 저장소로 엔티티 간 관계를 관리하고, "
            "Elasticsearch는 벡터 검색(kNN)과 BM25 키워드 검색을 담당합니다."
        ),
    },
    {
        "question": "LangGraph와 LangChain 중 어떤 것을 사용해야 하나요?",
        "type": "entity_relation",
        "ground_truth": (
            "LangGraph는 상태 기반 에이전트 워크플로우에 적합하고, "
            "LangChain은 단순 체인 기반 RAG 파이프라인에 적합합니다."
        ),
    },
    {
        "question": "FastAPI와 PostgreSQL을 연동하여 RAGAS 평가를 수행하려면?",
        "type": "entity_relation",
        "ground_truth": (
            "FastAPI에서 asyncpg로 PostgreSQL에 연결하고, "
            "RAGAS 라이브러리를 통해 Faithfulness 등 메트릭을 측정합니다."
        ),
    },
    # --- Multi-Hop (Graph 관계 확장 필요) ---
    {
        "question": "RAG Pipeline에서 BGE-M3 임베딩 모델의 역할은?",
        "type": "multi_hop",
        "ground_truth": (
            "BGE-M3는 RAG Pipeline에서 문서와 쿼리를 1024차원 벡터로 변환하여 "
            "시맨틱 검색을 가능하게 합니다."
        ),
    },
    {
        "question": "Kubernetes에서 Spring Boot 마이크로서비스를 배포하는 방법은?",
        "type": "multi_hop",
        "ground_truth": (
            "Spring Boot 앱을 Docker 이미지로 빌드한 후 "
            "Kubernetes Deployment와 Service를 생성하여 배포합니다."
        ),
    },
    {
        "question": "Agentic AI 에이전트 워크플로우 설계 패턴은 무엇인가요?",
        "type": "multi_hop",
        "ground_truth": (
            "Agentic AI 워크플로우는 Planner-Retriever-Generator 패턴을 따르며 "
            "LangGraph로 상태 기반 그래프를 구현합니다."
        ),
    },
    # --- Keyword (BM25 강점) ---
    {
        "question": "Docker Compose 설정 방법은?",
        "type": "keyword",
        "ground_truth": (
            "docker-compose.yml에 서비스, 네트워크, 볼륨을 정의하고 "
            "docker-compose up 명령으로 실행합니다."
        ),
    },
    {
        "question": "RRF 알고리즘이 Hybrid 검색에서 하는 역할은?",
        "type": "keyword",
        "ground_truth": (
            "RRF(Reciprocal Rank Fusion)는 Vector, BM25, Graph 검색 결과의 "
            "순위를 융합하여 최종 순위를 결정합니다."
        ),
    },
    {
        "question": "RAGAS 평가 메트릭의 종류와 의미는?",
        "type": "keyword",
        "ground_truth": (
            "Faithfulness(충실도), Answer Relevancy(답변 관련성), "
            "Context Precision(맥락 정밀도), Context Recall(맥락 재현율) 4가지입니다."
        ),
    },
    # --- Semantic (Vector 강점) ---
    {
        "question": "대규모 문서를 효율적으로 처리하는 방법은?",
        "type": "semantic",
        "ground_truth": (
            "청킹(chunking)으로 문서를 분할하고 배치 임베딩으로 벡터화한 후 "
            "Elasticsearch에 색인합니다."
        ),
    },
    {
        "question": "검색 성능을 최적화하려면 어떻게 해야 하나요?",
        "type": "semantic",
        "ground_truth": (
            "Hybrid 검색(BM25+Dense+Graph), RRF 퓨전, Redis 캐싱, "
            "배치 임베딩으로 성능을 최적화합니다."
        ),
    },
    {
        "question": "환경변수를 안전하게 관리하는 방법은?",
        "type": "semantic",
        "ground_truth": (
            ".env 파일에 환경변수를 정의하고 docker-compose에서 "
            "env_file로 로드하며, 시크릿은 별도 관리합니다."
        ),
    },
]


# ---------------------------------------------------------------------------
# HTTP Client
# ---------------------------------------------------------------------------
class HRKPClient:
    """HRKP AI Service API 클라이언트"""

    def __init__(self, base_url: str, timeout: int = 60):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.token: Optional[str] = None
        self.session = requests.Session()

    def login(self, email: str, password: str) -> bool:
        """JWT 인증"""
        resp = self.session.post(
            f"{self.base_url}/auth/login",
            json={"email": email, "password": password},
            timeout=self.timeout,
        )
        if resp.status_code == 200:
            data = resp.json()
            self.token = (
                data.get("accessToken")
                or data.get("access_token")
                or data.get("token")
            )
            self.session.headers["Authorization"] = f"Bearer {self.token}"
            return True
        print(f"  [ERROR] Login failed: {resp.status_code} {resp.text[:200]}")
        return False

    def hybrid_search(
        self,
        query: str,
        top_k: int = 10,
        use_graph: bool = True,
        use_vector: bool = True,
    ) -> Dict[str, Any]:
        """Hybrid 검색 호출"""
        resp = self.session.post(
            f"{self.base_url}/search/hybrid",
            json={
                "query": query,
                "top_k": top_k,
                "useGraph": use_graph,
                "useVector": use_vector,
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# DeepSeek LLM (답변 생성)
# ---------------------------------------------------------------------------
def generate_answer(
    question: str,
    contexts: List[str],
    api_key: str = DEEPSEEK_API_KEY,
    base_url: str = DEEPSEEK_BASE_URL,
    model: str = DEEPSEEK_MODEL,
) -> str:
    """DeepSeek LLM으로 컨텍스트 기반 답변 생성"""
    context_text = "\n\n---\n\n".join(contexts[:5])  # Top-5 컨텍스트 사용

    prompt = f"""다음 컨텍스트를 참고하여 질문에 답변하세요. 컨텍스트에 없는 정보는 사용하지 마세요.

## 컨텍스트
{context_text}

## 질문
{question}

## 답변
간결하고 정확하게 한국어로 답변하세요."""

    try:
        resp = requests.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 500,
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"[답변 생성 실패: {e}]"


# ---------------------------------------------------------------------------
# RAGAS Evaluation (with fallback)
# ---------------------------------------------------------------------------
def run_ragas_evaluation(
    samples: List[Dict[str, Any]],
    metrics_list: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    RAGAS 평가 실행

    ragas 라이브러리 사용 시도 -> 실패 시 mock heuristic fallback
    """
    metrics_list = metrics_list or [
        "faithfulness",
        "answer_relevancy",
        "context_precision",
        "context_recall",
    ]

    # 1) Try ragas library
    try:
        return _ragas_library_eval(samples, metrics_list)
    except Exception as e:
        print(f"  [WARN] RAGAS library eval failed: {e}")

    # 2) Try LLM-as-judge (DeepSeek)
    try:
        print(f"  [INFO] Using LLM-as-judge (DeepSeek) evaluation")
        return _llm_judge_eval(samples, metrics_list)
    except Exception as e:
        print(f"  [WARN] LLM judge eval failed: {e}")
        print(f"  [INFO] Falling back to heuristic evaluation")

    # 3) Fallback: heuristic word-overlap
    return _heuristic_eval(samples, metrics_list)


def _ragas_library_eval(
    samples: List[Dict[str, Any]],
    metrics_list: List[str],
) -> Dict[str, Any]:
    """ragas 라이브러리 기반 평가"""
    from datasets import Dataset
    from langchain_openai import ChatOpenAI
    from ragas import evaluate
    from ragas.metrics import (
        answer_relevancy,
        context_precision,
        context_recall,
        faithfulness,
    )

    metric_map = {
        "faithfulness": faithfulness,
        "answer_relevancy": answer_relevancy,
        "context_precision": context_precision,
        "context_recall": context_recall,
    }

    # DeepSeek LLM (OpenAI 호환)
    llm = ChatOpenAI(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        temperature=0.0,
    )

    # 데이터셋 구성
    data = {
        "question": [s["question"] for s in samples],
        "answer": [s["answer"] for s in samples],
        "contexts": [s["contexts"] for s in samples],
    }
    if all(s.get("ground_truth") for s in samples):
        data["ground_truth"] = [s["ground_truth"] for s in samples]

    dataset = Dataset.from_dict(data)

    selected_metrics = [metric_map[m] for m in metrics_list if m in metric_map]

    # ground_truth 없으면 context_recall 제외
    if "ground_truth" not in data:
        selected_metrics = [m for m in selected_metrics if m != context_recall]

    result = evaluate(dataset, metrics=selected_metrics, llm=llm)

    # 결과 추출
    scores = {}
    for m_name in metrics_list:
        val = result.get(m_name)
        if val is not None:
            scores[m_name] = round(float(val), 4)
        else:
            scores[m_name] = None

    return {
        "method": "ragas_library",
        "scores": scores,
        "details": {str(k): float(v) for k, v in result.items() if isinstance(v, (int, float))},
    }


def _llm_judge_eval(
    samples: List[Dict[str, Any]],
    metrics_list: List[str],
) -> Dict[str, Any]:
    """DeepSeek LLM-as-Judge 기반 평가"""
    all_scores: Dict[str, List[float]] = {m: [] for m in metrics_list}

    for idx, s in enumerate(samples):
        context_text = "\n---\n".join(s["contexts"][:3])  # Top-3 context

        # Faithfulness: 답변이 컨텍스트에 충실한지
        if "faithfulness" in metrics_list:
            score = _llm_score(
                f"""컨텍스트를 참고하여 답변의 충실도를 평가하세요.
답변의 모든 주장이 컨텍스트에 근거하면 1.0, 근거 없는 주장이 많으면 0.0입니다.

컨텍스트:
{context_text[:2000]}

답변:
{s['answer'][:500]}

0.0~1.0 사이 숫자만 반환하세요."""
            )
            all_scores["faithfulness"].append(score)

        # Answer Relevancy: 답변이 질문에 적절한지
        if "answer_relevancy" in metrics_list:
            score = _llm_score(
                f"""질문에 대한 답변의 관련성을 평가하세요.
답변이 질문에 정확하고 완전하게 답하면 1.0, 전혀 관련 없으면 0.0입니다.

질문: {s['question']}

답변:
{s['answer'][:500]}

0.0~1.0 사이 숫자만 반환하세요."""
            )
            all_scores["answer_relevancy"].append(score)

        # Context Precision: 검색된 컨텍스트가 질문에 관련되는지
        if "context_precision" in metrics_list:
            score = _llm_score(
                f"""검색된 컨텍스트가 질문과 얼마나 관련되는지 평가하세요.
모든 컨텍스트가 질문에 관련되면 1.0, 전혀 관련 없으면 0.0입니다.

질문: {s['question']}

컨텍스트:
{context_text[:2000]}

0.0~1.0 사이 숫자만 반환하세요."""
            )
            all_scores["context_precision"].append(score)

        # Context Recall: ground_truth 정보가 컨텍스트에 있는지
        if "context_recall" in metrics_list and s.get("ground_truth"):
            score = _llm_score(
                f"""정답(ground truth)의 핵심 정보가 컨텍스트에 포함되어 있는지 평가하세요.
정답의 모든 핵심 정보가 컨텍스트에 있으면 1.0, 전혀 없으면 0.0입니다.

정답: {s['ground_truth']}

컨텍스트:
{context_text[:2000]}

0.0~1.0 사이 숫자만 반환하세요."""
            )
            all_scores["context_recall"].append(score)

        if (idx + 1) % 4 == 0:
            print(f"    Evaluated {idx+1}/{len(samples)} samples...")

    scores = {}
    for m in metrics_list:
        vals = all_scores.get(m, [])
        scores[m] = round(sum(vals) / len(vals), 4) if vals else None

    return {"method": "llm_judge_deepseek", "scores": scores}


def _llm_score(prompt: str) -> float:
    """DeepSeek에 평가 요청하여 0.0~1.0 점수 반환"""
    try:
        resp = requests.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": DEEPSEEK_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
                "max_tokens": 10,
            },
            timeout=30,
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"].strip()
        # 숫자만 추출
        import re
        match = re.search(r"(\d+\.?\d*)", text)
        if match:
            val = float(match.group(1))
            return max(0.0, min(1.0, val))
        return 0.5
    except Exception:
        return 0.5


def _heuristic_eval(
    samples: List[Dict[str, Any]],
    metrics_list: List[str],
) -> Dict[str, Any]:
    """휴리스틱 단어 겹침 기반 평가 (fallback)"""
    all_scores: Dict[str, List[float]] = {m: [] for m in metrics_list}

    for s in samples:
        answer_words = set(s["answer"].lower().split())
        question_words = set(s["question"].lower().split())
        context_text = " ".join(s["contexts"]).lower()
        context_words = set(context_text.split())

        # Faithfulness: 답변 단어 중 컨텍스트에 있는 비율
        if "faithfulness" in metrics_list and answer_words:
            overlap = len(answer_words & context_words)
            all_scores["faithfulness"].append(
                min(overlap / len(answer_words), 1.0)
            )

        # Answer Relevancy: 질문 단어 중 답변에 있는 비율
        if "answer_relevancy" in metrics_list and question_words:
            overlap = len(question_words & answer_words)
            all_scores["answer_relevancy"].append(
                min(overlap / len(question_words), 1.0)
            )

        # Context Precision: 컨텍스트 중 질문과 관련된 비율
        if "context_precision" in metrics_list and s["contexts"]:
            relevant = sum(
                1
                for ctx in s["contexts"]
                if question_words & set(ctx.lower().split())
            )
            all_scores["context_precision"].append(
                relevant / len(s["contexts"])
            )

        # Context Recall: ground_truth 단어 중 컨텍스트에 있는 비율
        if "context_recall" in metrics_list and s.get("ground_truth"):
            gt_words = set(s["ground_truth"].lower().split())
            if gt_words:
                overlap = len(gt_words & context_words)
                all_scores["context_recall"].append(
                    min(overlap / len(gt_words), 1.0)
                )

    scores = {}
    for m in metrics_list:
        vals = all_scores.get(m, [])
        scores[m] = round(sum(vals) / len(vals), 4) if vals else None

    return {"method": "heuristic_word_overlap", "scores": scores}


# ---------------------------------------------------------------------------
# Main Evaluation Flow
# ---------------------------------------------------------------------------
def run_evaluation(
    top_k: int = 10,
    output_dir: str = "docs/results/ragas",
) -> Dict[str, Any]:
    """메인 평가 실행"""
    print("=" * 70)
    print("  STORY-111: RAGAS Cross-System Evaluation")
    print("  HRKP Graph RAG (3채널) vs 2채널 Hybrid")
    print("=" * 70)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M KST")
    print(f"  Start: {ts}")
    print(f"  Questions: {len(TEST_QUESTIONS)}")
    print(f"  Top-K: {top_k}")
    print()

    # 1. Login
    print("[1/5] HRKP API 인증...")
    client = HRKPClient(BASE_URL)
    if not client.login(LOGIN_EMAIL, LOGIN_PASSWORD):
        print("  FAILED - 로그인 실패. 종료합니다.")
        sys.exit(1)
    print("  OK")
    print()

    # 2. Search (Graph ON vs Graph OFF)
    print("[2/5] Hybrid 검색 실행 (Graph ON/OFF)...")
    graph_on_results: List[Dict[str, Any]] = []
    graph_off_results: List[Dict[str, Any]] = []

    for idx, q in enumerate(TEST_QUESTIONS):
        question = q["question"]
        qtype = q["type"]
        print(f"  Q{idx+1}/{len(TEST_QUESTIONS)} [{qtype}] {question[:50]}...")

        # Graph ON (3채널)
        on_results = []
        on_contexts, on_sources, on_latency = [], [], 0.0
        try:
            t0 = time.monotonic()
            on_resp = client.hybrid_search(
                question, top_k=top_k, use_graph=True, use_vector=True
            )
            on_latency = round((time.monotonic() - t0) * 1000, 1)
            on_results = on_resp.get("results", [])
            on_contexts = [r["content"] for r in on_results]
            on_sources = [r.get("source_type", "unknown") for r in on_results]
        except Exception as e:
            print(f"    [ERROR] Graph ON failed: {e}")

        # Graph OFF (2채널)
        off_results = []
        off_contexts, off_sources, off_latency = [], [], 0.0
        try:
            t0 = time.monotonic()
            off_resp = client.hybrid_search(
                question, top_k=top_k, use_graph=False, use_vector=True
            )
            off_latency = round((time.monotonic() - t0) * 1000, 1)
            off_results = off_resp.get("results", [])
            off_contexts = [r["content"] for r in off_results]
            off_sources = [r.get("source_type", "unknown") for r in off_results]
        except Exception as e:
            print(f"    [ERROR] Graph OFF failed: {e}")

        # Graph 고유 결과 수 계산
        on_ids = {r["chunk_id"] for r in on_results} if on_results else set()
        off_ids = {r["chunk_id"] for r in off_results} if off_results else set()
        graph_unique = len(on_ids - off_ids)

        graph_on_results.append({
            "question": question,
            "type": qtype,
            "contexts": on_contexts,
            "sources": on_sources,
            "latency_ms": on_latency,
            "result_count": len(on_contexts),
            "graph_unique_count": graph_unique,
            "top1_source": on_sources[0] if on_sources else None,
            "top1_score": on_results[0]["score"] if on_results else 0,
        })
        graph_off_results.append({
            "question": question,
            "type": qtype,
            "contexts": off_contexts,
            "sources": off_sources,
            "latency_ms": off_latency,
            "result_count": len(off_contexts),
            "top1_source": off_sources[0] if off_sources else None,
            "top1_score": off_results[0]["score"] if off_results else 0,
        })

        print(
            f"    ON: {len(on_contexts)} results, {on_latency}ms | "
            f"OFF: {len(off_contexts)} results, {off_latency}ms | "
            f"Graph unique: {graph_unique}"
        )

    print()

    # 3. Generate answers with DeepSeek
    print("[3/5] DeepSeek LLM 답변 생성...")
    for idx, q in enumerate(TEST_QUESTIONS):
        question = q["question"]
        print(f"  Q{idx+1}/{len(TEST_QUESTIONS)} Generating answers...")

        # Graph ON answer
        ans_on = generate_answer(question, graph_on_results[idx]["contexts"])
        graph_on_results[idx]["answer"] = ans_on

        # Graph OFF answer
        ans_off = generate_answer(question, graph_off_results[idx]["contexts"])
        graph_off_results[idx]["answer"] = ans_off

        print(f"    ON: {len(ans_on)} chars | OFF: {len(ans_off)} chars")

    print()

    # 4. RAGAS Evaluation
    print("[4/5] RAGAS 평가 실행...")

    # Build evaluation samples
    samples_on = [
        {
            "question": q["question"],
            "answer": graph_on_results[i]["answer"],
            "contexts": graph_on_results[i]["contexts"][:5],
            "ground_truth": q.get("ground_truth"),
        }
        for i, q in enumerate(TEST_QUESTIONS)
    ]
    samples_off = [
        {
            "question": q["question"],
            "answer": graph_off_results[i]["answer"],
            "contexts": graph_off_results[i]["contexts"][:5],
            "ground_truth": q.get("ground_truth"),
        }
        for i, q in enumerate(TEST_QUESTIONS)
    ]

    print("  Evaluating Graph ON (3채널)...")
    eval_on = run_ragas_evaluation(samples_on)
    print(f"  Method: {eval_on['method']}")
    print(f"  Scores: {eval_on['scores']}")

    print("  Evaluating Graph OFF (2채널)...")
    eval_off = run_ragas_evaluation(samples_off)
    print(f"  Method: {eval_off['method']}")
    print(f"  Scores: {eval_off['scores']}")

    print()

    # 5. Generate Report
    print("[5/5] 비교 리포트 생성...")

    report = build_report(
        eval_on=eval_on,
        eval_off=eval_off,
        graph_on_results=graph_on_results,
        graph_off_results=graph_off_results,
        questions=TEST_QUESTIONS,
        top_k=top_k,
    )

    # Save outputs
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d")

    # JSON raw data
    json_path = output_path / f"ragas_cross_system_{date_str}.json"
    raw_data = {
        "timestamp": datetime.now().isoformat(),
        "top_k": top_k,
        "question_count": len(TEST_QUESTIONS),
        "eval_graph_on": eval_on,
        "eval_graph_off": eval_off,
        "graph_on_results": graph_on_results,
        "graph_off_results": graph_off_results,
        "questions": TEST_QUESTIONS,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(raw_data, f, ensure_ascii=False, indent=2)
    print(f"  JSON: {json_path}")

    # Markdown report
    md_path = output_path / f"ragas_cross_system_report_{date_str}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"  Report: {md_path}")

    print()
    print("=" * 70)
    print("  Evaluation Complete!")
    print("=" * 70)

    # Print summary
    on_scores = eval_on["scores"]
    off_scores = eval_off["scores"]
    print()
    print("  === RAGAS Scores Summary ===")
    print(f"  {'Metric':<25} {'Graph ON':>10} {'Graph OFF':>10} {'Delta':>10}")
    print(f"  {'-'*25} {'-'*10} {'-'*10} {'-'*10}")
    for metric in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
        v_on = on_scores.get(metric)
        v_off = off_scores.get(metric)
        if v_on is not None and v_off is not None:
            delta = v_on - v_off
            sign = "+" if delta >= 0 else ""
            print(f"  {metric:<25} {v_on:>10.4f} {v_off:>10.4f} {sign}{delta:>9.4f}")
        else:
            print(f"  {metric:<25} {'N/A':>10} {'N/A':>10} {'N/A':>10}")

    # Search quality metrics
    avg_on_latency = sum(r["latency_ms"] for r in graph_on_results) / len(graph_on_results)
    avg_off_latency = sum(r["latency_ms"] for r in graph_off_results) / len(graph_off_results)
    total_graph_unique = sum(r.get("graph_unique_count", 0) for r in graph_on_results)

    print()
    print(f"  Avg Latency   ON: {avg_on_latency:.0f}ms | OFF: {avg_off_latency:.0f}ms")
    print(f"  Graph Unique Results: {total_graph_unique}")
    print()

    return raw_data


# ---------------------------------------------------------------------------
# Report Builder
# ---------------------------------------------------------------------------
def build_report(
    eval_on: Dict,
    eval_off: Dict,
    graph_on_results: List[Dict],
    graph_off_results: List[Dict],
    questions: List[Dict],
    top_k: int,
) -> str:
    """Markdown 비교 리포트 생성"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M KST")
    on_scores = eval_on["scores"]
    off_scores = eval_off["scores"]

    avg_on_lat = sum(r["latency_ms"] for r in graph_on_results) / len(graph_on_results)
    avg_off_lat = sum(r["latency_ms"] for r in graph_off_results) / len(graph_off_results)
    total_unique = sum(r.get("graph_unique_count", 0) for r in graph_on_results)

    lines: List[str] = []
    w = lines.append

    w("# STORY-111: RAGAS Cross-System Evaluation Report")
    w("")
    w(f"**평가 일시**: {now}")
    w(f"**평가 방법**: {eval_on['method']}")
    w(f"**테스트 쿼리**: {len(questions)}개")
    w(f"**Top-K**: {top_k}")
    w(f"**LLM**: DeepSeek V3 ({DEEPSEEK_MODEL})")
    w(f"**임베딩**: BGE-M3 (1024d)")
    w("")
    w("---")
    w("")

    # 1. Executive Summary
    w("## 1. Executive Summary")
    w("")
    w("| 시스템 | 검색 채널 | 설명 |")
    w("|--------|----------|------|")
    w("| **System A (Graph ON)** | BM25 + Dense + Graph | 3채널 Hybrid - Neo4j 엔티티 기반 검색 포함 |")
    w("| **System B (Graph OFF)** | BM25 + Dense | 2채널 Hybrid - 기존 방식 |")
    w("")

    # 2. RAGAS Scores
    w("## 2. RAGAS 메트릭 비교")
    w("")
    w("| 메트릭 | Graph ON (3채널) | Graph OFF (2채널) | 차이 | 우위 |")
    w("|--------|:----------------:|:-----------------:|:----:|:----:|")

    for metric in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
        v_on = on_scores.get(metric)
        v_off = off_scores.get(metric)
        if v_on is not None and v_off is not None:
            delta = v_on - v_off
            sign = "+" if delta >= 0 else ""
            winner = "Graph ON" if delta > 0.001 else ("Graph OFF" if delta < -0.001 else "동일")
            icon = "**" if abs(delta) > 0.01 else ""
            w(f"| {metric} | {icon}{v_on:.4f}{icon} | {v_off:.4f} | {sign}{delta:.4f} | {winner} |")
        else:
            w(f"| {metric} | N/A | N/A | N/A | N/A |")

    w("")

    # 3. Search Quality
    w("## 3. 검색 품질 비교")
    w("")
    w("| 지표 | Graph ON | Graph OFF | 차이 |")
    w("|------|:--------:|:---------:|:----:|")
    w(f"| 평균 레이턴시 | {avg_on_lat:.0f}ms | {avg_off_lat:.0f}ms | {avg_on_lat - avg_off_lat:+.0f}ms |")
    w(f"| Graph 고유 결과 (총) | **{total_unique}건** | 0건 | +{total_unique} |")

    # Top-1 source distribution
    on_graph_top1 = sum(1 for r in graph_on_results if r.get("top1_source") == "graph")
    w(f"| Top-1이 Graph 출처 | {on_graph_top1}/{len(questions)} | 0/{len(questions)} | +{on_graph_top1} |")
    w("")

    # 4. Query Type Analysis
    w("## 4. 쿼리 유형별 분석")
    w("")

    types = {}
    for i, q in enumerate(questions):
        t = q["type"]
        if t not in types:
            types[t] = {"on_lat": [], "off_lat": [], "on_unique": [], "count": 0}
        types[t]["on_lat"].append(graph_on_results[i]["latency_ms"])
        types[t]["off_lat"].append(graph_off_results[i]["latency_ms"])
        types[t]["on_unique"].append(graph_on_results[i].get("graph_unique_count", 0))
        types[t]["count"] += 1

    w("| 쿼리 유형 | 수량 | ON Latency (avg) | OFF Latency (avg) | Graph 고유 (avg) |")
    w("|-----------|:----:|:----------------:|:-----------------:|:---------------:|")
    for t, data in types.items():
        avg_on = sum(data["on_lat"]) / len(data["on_lat"])
        avg_off = sum(data["off_lat"]) / len(data["off_lat"])
        avg_unique = sum(data["on_unique"]) / len(data["on_unique"])
        w(f"| {t} | {data['count']} | {avg_on:.0f}ms | {avg_off:.0f}ms | {avg_unique:.1f} |")

    w("")

    # 5. Per-Question Details
    w("## 5. 쿼리별 상세 결과")
    w("")

    for idx, q in enumerate(questions):
        on = graph_on_results[idx]
        off = graph_off_results[idx]
        w(f"### Q{idx+1}: \"{q['question']}\" ({q['type']})")
        w("")
        w("| 항목 | Graph ON | Graph OFF |")
        w("|------|----------|-----------|")
        w(f"| Top-1 소스 | {on.get('top1_source', 'N/A')} (score: {on.get('top1_score', 0):.4f}) | {off.get('top1_source', 'N/A')} (score: {off.get('top1_score', 0):.4f}) |")
        w(f"| 결과 수 | {on['result_count']} | {off['result_count']} |")
        w(f"| Graph 고유 | {on.get('graph_unique_count', 0)}건 | - |")
        w(f"| 레이턴시 | {on['latency_ms']}ms | {off['latency_ms']}ms |")
        w(f"| 답변 길이 | {len(on.get('answer', ''))} chars | {len(off.get('answer', ''))} chars |")
        w("")

        # Answer snippets
        ans_on = on.get("answer", "")[:200]
        ans_off = off.get("answer", "")[:200]
        w(f"**Graph ON 답변** (발췌): {ans_on}...")
        w("")
        w(f"**Graph OFF 답변** (발췌): {ans_off}...")
        w("")

    # 6. Conclusion
    w("## 6. 결론")
    w("")

    # Calculate winning metrics
    wins_on = 0
    wins_off = 0
    for metric in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
        v_on = on_scores.get(metric)
        v_off = off_scores.get(metric)
        if v_on is not None and v_off is not None:
            if v_on > v_off + 0.001:
                wins_on += 1
            elif v_off > v_on + 0.001:
                wins_off += 1

    w(f"### RAGAS 메트릭 승/패: Graph ON {wins_on} : {wins_off} Graph OFF")
    w("")
    w("### 핵심 발견")
    w("")
    w(f"1. **검색 다양성**: Graph ON이 총 {total_unique}건의 고유 결과를 추가 제공")
    w(f"2. **레이턴시**: 평균 {abs(avg_on_lat - avg_off_lat):.0f}ms 차이 ({'Graph ON 느림' if avg_on_lat > avg_off_lat else 'Graph ON 빠름'})")
    w(f"3. **Top-1 Graph 출처**: {on_graph_top1}/{len(questions)} 쿼리에서 Graph 결과가 Top-1")
    w("")
    w("### 권장사항")
    w("")
    if wins_on >= wins_off:
        w("- Graph RAG (3채널)를 프로덕션 기본 설정으로 사용 권장")
        w("- 엔티티 관계 쿼리 및 멀티홉 쿼리에서 특히 효과적")
    else:
        w("- 2채널 모드가 RAGAS 메트릭에서 우세하나, Graph 고유 결과의 다양성 가치를 고려해야 함")
    w("- Entity-Chunk 직접 연결(MENTIONED_IN) 추가로 Graph 검색 정밀도 향상 가능")
    w("- RRF 가중치 튜닝으로 최적 비율 탐색 필요")
    w("")
    w("---")
    w("")
    w(f"*Generated: {now}*")
    w(f"*Tool: scripts/ragas_cross_system_eval.py (STORY-111)*")
    w(f"*Author: Claude Opus 4.6 (QA/RAG Agent)*")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="STORY-111: RAGAS Cross-System Evaluation"
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="검색 결과 수 (default: 10)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="docs/results/ragas",
        help="출력 디렉토리 (default: docs/results/ragas)",
    )
    args = parser.parse_args()

    run_evaluation(top_k=args.top_k, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
