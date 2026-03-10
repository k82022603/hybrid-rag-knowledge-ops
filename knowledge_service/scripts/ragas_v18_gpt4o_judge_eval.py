#!/usr/bin/env python3
"""
RAGAS v18 GPT-4o Judge Evaluation
==================================
v16과 동일 파이프라인(REST API /search/hybrid + DeepSeek answer)을 사용하되,
RAGAS Judge LLM을 GPT-4o로 교체하여 평가 안정성 비교.

핵심 변경점 (v16 대비):
- Judge LLM: DeepSeek -> GPT-4o (RAGAS 공식 권장 LLM)
- Embeddings: OpenAI text-embedding-3-small (answer_relevancy 측정 추가)
- Metrics: 4개 전체 (faithfulness, answer_relevancy, context_precision, context_recall)
  - v16은 answer_relevancy 미측정 (임베딩 미사용)

구현 방식:
- RAGAS 라이브러리 대신 동일한 평가 프롬프트를 GPT-4o에 직접 호출
  (로컬 RAGAS 0.1.19와 langchain-core 1.2.x 비호환 문제 우회)
- RAGAS 공식 프롬프트 기반 Faithfulness/Context Precision/Context Recall 측정
- Answer Relevancy: GPT-4o + OpenAI text-embedding-3-small cosine similarity

파이프라인 (v16과 동일):
- 검색: /api/v1/search/hybrid (4-Way RRF + Reranker 1-Pass)
- 답변 생성: DeepSeek API Direct
- 파라미터: candidates_cap=50, graph_search_top_k=10

실행:
    cd knowledge_service
    source .venv/bin/activate
    python scripts/ragas_v18_gpt4o_judge_eval.py
"""

import json
import math
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_URL = os.getenv("HRKP_API_URL", "http://localhost:8000/api/v1")
LOGIN_EMAIL = "admin@example.com"
LOGIN_PASSWORD = "admin123!"

# Answer generation LLM (DeepSeek -- same pipeline as v16)
DEEPSEEK_API_KEY = os.getenv(
    "DEEPSEEK_API_KEY", "sk-7c3024219fb74302a296207d2a091fe5"
)
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

# Judge LLM (GPT-4o -- the key difference from v16)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = "https://api.openai.com/v1"

TOKEN_REFRESH_INTERVAL = 15
INTER_QUERY_DELAY = 3  # seconds between search queries to prevent service overload
MAX_RETRIES = 3
RETRY_DELAY = 10  # seconds to wait before retry

# v16 Baseline (DeepSeek judge, REST API same-pipeline)
V16_BASELINE = {
    "faithfulness": 0.8588,
    "context_precision": 0.7389,
    "context_recall": 0.6902,
    "arithmetic_mean": 0.7626,
}

# v11 Baseline (DeepSeek judge, Chat API)
V11_BASELINE = {
    "faithfulness": 0.935,
    "context_precision": 0.618,
    "context_recall": 0.672,
}

# 51 questions across 7 domains
TEST_QUESTIONS = [
    {"question": "Neo4j와 Elasticsearch의 역할 차이점은?", "type": "entity_relation", "ground_truth": "Neo4j는 Knowledge Graph 저장소로 엔티티 간 관계를 관리하고, Elasticsearch는 벡터 검색(kNN)과 BM25 키워드 검색을 담당합니다."},
    {"question": "LangGraph와 LangChain 중 어떤 것을 사용해야 하나요?", "type": "entity_relation", "ground_truth": "LangGraph는 상태 기반 에이전트 워크플로우에 적합하고, LangChain은 단순 체인 기반 RAG 파이프라인에 적합합니다."},
    {"question": "FastAPI와 PostgreSQL을 연동하여 RAGAS 평가를 수행하려면?", "type": "entity_relation", "ground_truth": "FastAPI에서 asyncpg로 PostgreSQL에 연결하고, RAGAS 라이브러리를 통해 Faithfulness 등 메트릭을 측정합니다."},
    {"question": "PostgreSQL과 Neo4j의 데이터 모델 차이는?", "type": "entity_relation", "ground_truth": "PostgreSQL은 관계형 SSOT 저장소이고, Neo4j는 그래프 데이터베이스로 엔티티 간 관계를 노드-엣지로 표현합니다."},
    {"question": "Spring Cloud Gateway와 FastAPI의 역할 분담은?", "type": "entity_relation", "ground_truth": "Spring Cloud Gateway는 API Gateway로 라우팅/인증을 담당하고, FastAPI는 AI Service 백엔드로 RAG 파이프라인을 실행합니다."},
    {"question": "BGE-M3와 BGE-Reranker의 역할 차이는?", "type": "entity_relation", "ground_truth": "BGE-M3는 Bi-encoder로 문서/쿼리를 벡터로 변환하고, BGE-Reranker는 Cross-encoder로 검색 결과의 순위를 재조정합니다."},
    {"question": "DeepSeek V3와 OpenAI GPT의 비용 및 성능 차이는?", "type": "entity_relation", "ground_truth": "DeepSeek V3는 OpenAI GPT 대비 95% 비용 절감이 가능하며, 한국어 RAG 파이프라인에서 충분한 성능을 제공합니다."},
    {"question": "RAG Pipeline에서 BGE-M3 임베딩 모델의 역할은?", "type": "multi_hop", "ground_truth": "BGE-M3는 RAG Pipeline에서 문서와 쿼리를 1024차원 벡터로 변환하여 시맨틱 검색을 가능하게 합니다."},
    {"question": "Knowledge Graph 엔티티 추출이 RAG 검색 품질에 기여하는 방식은?", "type": "multi_hop", "ground_truth": "엔티티 추출로 문서 간 관계를 Knowledge Graph에 저장하고, Graph Search 채널로 관계 기반 검색을 제공합니다."},
    {"question": "Agentic AI 에이전트 워크플로우 설계 패턴은 무엇인가요?", "type": "multi_hop", "ground_truth": "Agentic AI 워크플로우는 Planner-Retriever-Generator 패턴을 따르며 LangGraph로 상태 기반 그래프를 구현합니다."},
    {"question": "LangGraph에서 상태(State) 관리와 노드 간 데이터 전달 방식은?", "type": "multi_hop", "ground_truth": "LangGraph는 TypedDict 기반 State를 정의하고, 노드 함수가 State를 받아 수정 후 반환하는 방식으로 데이터를 전달합니다."},
    {"question": "ETL 파이프라인에서 문서 파싱부터 임베딩 저장까지의 전체 흐름은?", "type": "multi_hop", "ground_truth": "문서를 Docling으로 파싱하고, 시맨틱 청커로 분할한 후, BGE-M3로 벡터화하여 Elasticsearch에 색인합니다."},
    {"question": "Hybrid Search에서 RRF 퓨전이 단일 검색보다 나은 이유는?", "type": "multi_hop", "ground_truth": "RRF는 Vector, BM25, Graph 등 서로 다른 검색 채널의 순위를 융합하여 단일 채널의 약점을 보완합니다."},
    {"question": "AI 에이전트에서 Tool Calling과 Reasoning의 상호작용은?", "type": "multi_hop", "ground_truth": "AI 에이전트는 Reasoning으로 문제를 분석한 후 적절한 Tool을 선택하여 호출하고 결과를 다시 Reasoning에 반영합니다."},
    {"question": "Docker Compose에서 컨테이너 간 네트워크 통신 설정 방법은?", "type": "keyword", "ground_truth": "docker-compose.yml에서 networks를 정의하고 서비스마다 네트워크를 지정하면 컨테이너 간 호스트명으로 통신합니다."},
    {"question": "RRF 알고리즘이 Hybrid 검색에서 하는 역할은?", "type": "keyword", "ground_truth": "RRF(Reciprocal Rank Fusion)는 Vector, BM25, Graph 검색 결과의 순위를 융합하여 최종 순위를 결정합니다."},
    {"question": "RAGAS 평가 메트릭의 종류와 의미는?", "type": "keyword", "ground_truth": "Faithfulness(충실도), Answer Relevancy(답변 관련성), Context Precision(맥락 정밀도), Context Recall(맥락 재현율) 4가지입니다."},
    {"question": "JWT 인증 토큰의 장점과 단점은 무엇인가요?", "type": "keyword", "ground_truth": "JWT는 서버 상태 비저장(stateless) 인증이 가능하지만, 토큰 만료 전 무효화가 어렵고 크기가 큰 단점이 있습니다."},
    {"question": "Kubernetes에서 Spring Boot 마이크로서비스를 배포하는 방법은?", "type": "keyword", "ground_truth": "Spring Boot 앱을 Docker 이미지로 빌드한 후 Kubernetes Deployment와 Service를 생성하여 배포합니다."},
    {"question": "Elasticsearch 벡터 검색을 위한 인덱스 설정 방법은?", "type": "keyword", "ground_truth": "dense_vector 타입 필드를 정의하고 dims, similarity, knn 옵션을 설정하여 벡터 검색 인덱스를 생성합니다."},
    {"question": "WBS(Work Breakdown Structure)란 무엇이며 프로젝트 관리에서 어떻게 활용하나요?", "type": "keyword", "ground_truth": "WBS는 프로젝트를 작은 작업 단위로 분해하여 체계적으로 관리하는 구조로, 범위 정의와 일정 관리에 활용됩니다."},
    {"question": "대규모 문서를 효율적으로 처리하는 방법은?", "type": "semantic", "ground_truth": "청킹(chunking)으로 문서를 분할하고 배치 임베딩으로 벡터화한 후 Elasticsearch에 색인합니다."},
    {"question": "검색 성능을 최적화하려면 어떻게 해야 하나요?", "type": "semantic", "ground_truth": "Hybrid 검색(BM25+Dense+Graph), RRF 퓨전, Redis 캐싱, 배치 임베딩으로 성능을 최적화합니다."},
    {"question": "환경변수를 안전하게 관리하는 방법은?", "type": "semantic", "ground_truth": ".env 파일에 환경변수를 정의하고 docker-compose에서 env_file로 로드하며, 시크릿은 별도 관리합니다."},
    {"question": "답변 품질을 체계적으로 평가하는 방법론은 무엇인가요?", "type": "semantic", "ground_truth": "RAGAS 프레임워크로 Faithfulness, Answer Relevancy, Context Precision, Context Recall을 측정하여 체계적으로 평가합니다."},
    {"question": "반복적이고 점진적인 개발 방법론은 어떤 것이 있나요?", "type": "semantic", "ground_truth": "Agile/Scrum 방법론으로 Sprint 단위 반복 개발, 데일리 스크럼, 스프린트 리뷰를 통해 점진적으로 발전시킵니다."},
    {"question": "데이터베이스 마이그레이션을 안전하게 수행하는 방법은?", "type": "semantic", "ground_truth": "Flyway/Alembic 등 마이그레이션 도구를 사용하여 스키마 변경을 버전 관리하고 롤백 가능하게 합니다."},
    {"question": "마이크로서비스 아키텍처에서 서비스 간 통신 패턴은?", "type": "semantic", "ground_truth": "동기 방식(REST, gRPC)과 비동기 방식(이벤트 기반 메시징)이 있으며, API Gateway로 진입점을 통합합니다."},
    {"question": "Spring Cloud Gateway에서 API 라우팅과 필터를 설정하는 방법은?", "type": "graph_entity", "ground_truth": "Spring Cloud Gateway에서 RouteLocator로 라우팅 규칙을 정의하고, GlobalFilter로 인증/로깅 등 필터를 적용합니다."},
    {"question": "Gleaning 기법이란 무엇이며 RAG 파이프라인에서 어떻게 활용되나요?", "type": "graph_entity", "ground_truth": "Gleaning은 LLM이 추출한 엔티티를 반복 검증하여 Knowledge Graph의 품질을 높이는 기법입니다."},
    {"question": "cosine similarity와 dot product 유사도의 차이와 적합한 사용 시나리오는?", "type": "graph_entity", "ground_truth": "cosine similarity는 방향만 비교하여 정규화된 벡터에 적합하고, dot product는 크기도 반영하여 비정규화 벡터에 적합합니다."},
    {"question": "SSOT 원칙이란 무엇이며 데이터 아키텍처에서 왜 중요한가요?", "type": "graph_entity", "ground_truth": "SSOT(Single Source of Truth)는 데이터의 단일 원본을 유지하는 원칙으로, PostgreSQL이 SSOT 역할을 합니다."},
    {"question": "Vector Search와 Graph Search를 결합하면 어떤 이점이 있나요?", "type": "graph_entity", "ground_truth": "Vector Search는 의미 유사성 기반 검색을, Graph Search는 엔티티 관계 기반 검색을 제공하여 상호 보완합니다."},
    {"question": "React 18에서 Concurrent 렌더링과 Suspense를 활용하는 방법은?", "type": "graph_entity", "ground_truth": "React 18의 Concurrent 렌더링은 UI 응답성을 높이고, Suspense는 비동기 데이터 로딩을 선언적으로 처리합니다."},
    {"question": "Python 3.11의 ExceptionGroup과 except* 구문의 사용 방법은?", "type": "graph_entity", "ground_truth": "ExceptionGroup은 여러 예외를 하나로 묶고, except*로 특정 예외 유형만 선택적으로 처리합니다."},
    {"question": "AI Service에서 RAG Pipeline의 전체 처리 흐름은?", "type": "graph_entity", "ground_truth": "쿼리 입력 -> Hybrid 검색(BM25+Dense+Sparse+Graph) -> RRF 퓨전 -> Quality Gate -> LLM 생성 순서입니다."},
    {"question": "개인정보보호법에서 개인정보 수집 시 동의 요건은?", "type": "legal", "ground_truth": "개인정보보호법에 따라 정보주체의 동의를 받아야 하며, 수집 목적, 항목, 보유 기간을 명시해야 합니다."},
    {"question": "GDPR의 핵심 원칙과 국내 기업의 준수 사항은?", "type": "legal", "ground_truth": "GDPR은 데이터 최소 수집, 목적 제한, 정보주체 권리 보장 등을 요구하며, EU 시민 데이터 처리 시 준수해야 합니다."},
    {"question": "민법에서 계약의 성립 요건은 무엇인가요?", "type": "legal", "ground_truth": "계약은 당사자 간 청약과 승낙의 합치로 성립하며, 의사표시의 합치가 핵심 요건입니다."},
    {"question": "SLA(서비스 수준 협약)에서 반드시 포함해야 할 핵심 항목은?", "type": "legal", "ground_truth": "가용성(Uptime), 응답 시간, 장애 대응 시간, 보상 조건, 측정 방법 등이 SLA 핵심 항목입니다."},
    {"question": "ISMS 인증을 위한 정보보안 점검 항목은?", "type": "legal", "ground_truth": "관리체계 수립, 보호대책 구현, 접근 통제, 침해사고 대응, 개인정보 보호 등을 점검합니다."},
    {"question": "소프트웨어 라이선스 종류(MIT, GPL, Apache)의 차이는?", "type": "legal", "ground_truth": "MIT는 최소 제약, GPL은 파생물도 GPL 적용 의무, Apache는 특허권 명시 허가가 특징입니다."},
    {"question": "법령 용어에서 '선의'와 '악의'의 법률적 의미 차이는?", "type": "legal", "ground_truth": "법률에서 선의는 어떤 사실을 모르는 상태, 악의는 어떤 사실을 알고 있는 상태를 의미합니다."},
    {"question": "RAG(Retrieval-Augmented Generation) 시스템의 동작 원리는?", "type": "factual", "ground_truth": "RAG는 질문에 관련된 문서를 검색(Retrieval)한 후 LLM이 검색된 컨텍스트를 참고하여 답변을 생성(Generation)합니다."},
    {"question": "Transformer 아키텍처의 Self-Attention 메커니즘은?", "type": "factual", "ground_truth": "Self-Attention은 입력 시퀀스의 각 토큰이 다른 모든 토큰과의 관련도를 계산하여 문맥 정보를 인코딩합니다."},
    {"question": "Reranking이 RAG 검색 품질을 향상시키는 원리는?", "type": "factual", "ground_truth": "Reranking은 Cross-encoder로 쿼리와 문서 쌍의 관련성을 정밀 평가하여 초기 검색 결과의 순위를 재조정합니다."},
    {"question": "HNSW와 IVF 벡터 인덱스 알고리즘의 비교는?", "type": "factual", "ground_truth": "HNSW는 그래프 기반으로 높은 검색 정확도를 제공하고, IVF는 클러스터 기반으로 메모리 효율이 좋습니다."},
    {"question": "Chain of Thought 추론이 LLM 성능에 미치는 영향은?", "type": "factual", "ground_truth": "Chain of Thought는 LLM이 단계별로 추론하도록 유도하여 복잡한 문제 해결 능력을 향상시킵니다."},
    {"question": "벡터 임베딩의 차원 수가 검색 정확도에 미치는 영향은?", "type": "factual", "ground_truth": "차원이 높을수록 의미 표현력이 증가하나 계산 비용도 증가하며, 1024차원이 성능과 효율의 균형점입니다."},
    {"question": "비즈니스에 실제 활용 가능한 LLM 서비스를 만들기 위한 핵심 고려사항은?", "type": "factual", "ground_truth": "프롬프트 설계, RAG 파이프라인, 평가 체계, 비용 최적화, 할루시네이션 방지가 핵심 고려사항입니다."},
    {"question": "프롬프트 엔지니어링의 핵심 원칙과 효과적인 기법은?", "type": "factual", "ground_truth": "명확한 지시, 예시 제공(few-shot), 역할 부여, 단계별 사고 유도가 핵심 기법입니다."},
]


# ===========================================================================
# HRKP API Client
# ===========================================================================
class HRKPClient:
    """HRKP API client with retry and token refresh."""

    def __init__(self):
        self.base_url = BASE_URL.rstrip("/")
        self.session = requests.Session()
        self._query_count = 0

    def login(self) -> bool:
        for attempt in range(MAX_RETRIES):
            try:
                r = self.session.post(
                    f"{self.base_url}/auth/login",
                    json={"email": LOGIN_EMAIL, "password": LOGIN_PASSWORD},
                    timeout=30,
                )
                if r.status_code == 200:
                    data = r.json()
                    token = (
                        data.get("accessToken")
                        or data.get("access_token")
                        or data.get("token")
                    )
                    self.session.headers["Authorization"] = f"Bearer {token}"
                    self._query_count = 0
                    return True
                print(f"  [WARN] Login attempt {attempt+1} failed: {r.status_code}")
            except Exception as e:
                print(f"  [WARN] Login attempt {attempt+1} error: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
        return False

    def _maybe_refresh(self):
        self._query_count += 1
        if self._query_count >= TOKEN_REFRESH_INTERVAL:
            self.login()

    def hybrid_search(self, query: str, top_k: int = 10) -> Dict:
        """Use /search/hybrid with retry logic."""
        self._maybe_refresh()
        for attempt in range(MAX_RETRIES):
            try:
                r = self.session.post(
                    f"{self.base_url}/search/hybrid",
                    json={
                        "query": query,
                        "top_k": top_k,
                        "useGraph": True,
                        "useVector": True,
                    },
                    timeout=180,
                )
                r.raise_for_status()
                return r.json()
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    wait = RETRY_DELAY * (attempt + 1)
                    print(f"\n    [RETRY {attempt+1}] {e}, waiting {wait}s...", end=" ", flush=True)
                    time.sleep(wait)
                    # Re-login after connection error
                    self.login()
                else:
                    raise

    def warmup(self) -> bool:
        """Send a simple query to warm up the service (load models)."""
        print("  Warming up AI service (loading embedding model + reranker)...")
        try:
            r = self.session.post(
                f"{self.base_url}/search/hybrid",
                json={"query": "test", "top_k": 3, "useGraph": False, "useVector": True},
                timeout=180,
            )
            print(f"  Warmup complete: status={r.status_code}")
            return r.status_code == 200
        except Exception as e:
            print(f"  Warmup failed: {e}")
            return False


# ===========================================================================
# GPT-4o Judge Functions (RAGAS-equivalent prompts)
# ===========================================================================
def call_gpt4o(prompt: str, max_tokens: int = 1000) -> str:
    """Call GPT-4o API."""
    resp = requests.post(
        f"{OPENAI_BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "max_tokens": max_tokens,
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def get_openai_embedding(text: str) -> List[float]:
    """Get embedding from OpenAI text-embedding-3-small."""
    resp = requests.post(
        f"{OPENAI_BASE_URL}/embeddings",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "text-embedding-3-small",
            "input": text,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def evaluate_faithfulness(question: str, answer: str, contexts: List[str]) -> float:
    """
    RAGAS Faithfulness metric via GPT-4o.
    Measures if the answer is grounded in the provided contexts.

    Steps (RAGAS approach):
    1. Extract claims from the answer
    2. For each claim, verify if it can be inferred from the contexts
    3. Score = (supported claims) / (total claims)
    """
    context_text = "\n\n".join(f"Context {i+1}: {c}" for i, c in enumerate(contexts[:5]))

    prompt = f"""You are evaluating the faithfulness of an answer to a question based on the provided contexts.

Faithfulness measures whether EVERY claim in the answer can be inferred from the given contexts.

## Contexts
{context_text}

## Question
{question}

## Answer
{answer}

## Task
1. Extract all factual claims/statements from the answer.
2. For each claim, determine if it can be supported by the contexts (YES or NO).
3. Calculate the faithfulness score as: (number of supported claims) / (total number of claims).

## Output Format (JSON only)
{{
  "claims": [
    {{"claim": "...", "supported": true/false}},
    ...
  ],
  "total_claims": N,
  "supported_claims": M,
  "score": M/N
}}

Return ONLY valid JSON, no other text."""

    try:
        result = call_gpt4o(prompt)
        # Parse JSON from response
        result = result.strip()
        if result.startswith("```"):
            result = result.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        data = json.loads(result)
        score = float(data.get("score", 0))
        return max(0.0, min(1.0, score))
    except Exception as e:
        print(f"    [WARN] Faithfulness eval error: {e}")
        return 0.0


def evaluate_answer_relevancy(question: str, answer: str) -> float:
    """
    RAGAS Answer Relevancy metric via GPT-4o + embeddings.
    Measures how relevant the answer is to the question.

    RAGAS approach: Generate N questions from the answer, then compute
    average cosine similarity between generated questions and the original.
    """
    prompt = f"""Given the following answer, generate 3 questions that this answer would be a good response to.
The generated questions should be diverse and cover different aspects of the answer.

## Answer
{answer}

## Output Format (JSON only)
{{
  "questions": [
    "generated question 1",
    "generated question 2",
    "generated question 3"
  ]
}}

Return ONLY valid JSON, no other text."""

    try:
        result = call_gpt4o(prompt, max_tokens=500)
        result = result.strip()
        if result.startswith("```"):
            result = result.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        data = json.loads(result)
        gen_questions = data.get("questions", [])

        if not gen_questions:
            return 0.0

        # Get embedding for original question
        q_emb = get_openai_embedding(question)

        # Get embeddings for generated questions and compute similarities
        similarities = []
        for gq in gen_questions:
            gq_emb = get_openai_embedding(gq)
            sim = cosine_similarity(q_emb, gq_emb)
            similarities.append(sim)

        return max(0.0, min(1.0, sum(similarities) / len(similarities)))
    except Exception as e:
        print(f"    [WARN] Answer relevancy eval error: {e}")
        return 0.0


def evaluate_context_precision(question: str, contexts: List[str], ground_truth: str) -> float:
    """
    RAGAS Context Precision metric via GPT-4o.
    Measures if the relevant contexts are ranked higher.

    For each context, determine if it's relevant to answering the question
    given the ground truth. Then compute precision@k weighted by rank.
    """
    if not contexts:
        return 0.0

    context_items = "\n".join(
        f"Context {i+1}: {c[:500]}" for i, c in enumerate(contexts[:5])
    )

    prompt = f"""You are evaluating the precision of retrieved contexts for answering a question.

## Question
{question}

## Ground Truth Answer
{ground_truth}

## Retrieved Contexts (ranked by retrieval score)
{context_items}

## Task
For each context, determine if it contains information useful for answering the question
correctly based on the ground truth. Answer YES or NO for each.

## Output Format (JSON only)
{{
  "verdicts": [
    {{"context_idx": 1, "relevant": true/false, "reason": "brief reason"}},
    {{"context_idx": 2, "relevant": true/false, "reason": "brief reason"}},
    ...
  ]
}}

Return ONLY valid JSON, no other text."""

    try:
        result = call_gpt4o(prompt)
        result = result.strip()
        if result.startswith("```"):
            result = result.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        data = json.loads(result)
        verdicts = data.get("verdicts", [])

        if not verdicts:
            return 0.0

        # Compute precision@k with RAGAS formula
        # precision@k = (sum of relevant up to k) / k, averaged over all k
        relevant_flags = [v.get("relevant", False) for v in verdicts]
        n = len(relevant_flags)

        # RAGAS Context Precision formula:
        # For each position k (1-indexed), precision@k = relevant_count_up_to_k / k
        # Final score = average of precision@k only at positions where the item is relevant
        precision_sum = 0.0
        relevant_count = 0
        relevant_positions = 0

        for k in range(1, n + 1):
            if relevant_flags[k - 1]:
                relevant_count += 1
                precision_at_k = relevant_count / k
                precision_sum += precision_at_k
                relevant_positions += 1

        if relevant_positions == 0:
            return 0.0

        return precision_sum / relevant_positions

    except Exception as e:
        print(f"    [WARN] Context precision eval error: {e}")
        return 0.0


def evaluate_context_recall(question: str, contexts: List[str], ground_truth: str) -> float:
    """
    RAGAS Context Recall metric via GPT-4o.
    Measures what fraction of the ground truth is covered by the contexts.

    RAGAS approach: Split ground truth into sentences/claims, check if each
    can be attributed to some context.
    """
    if not contexts:
        return 0.0

    context_text = "\n\n".join(f"Context {i+1}: {c}" for i, c in enumerate(contexts[:5]))

    prompt = f"""You are evaluating context recall: what fraction of the ground truth information
is covered by the retrieved contexts.

## Question
{question}

## Ground Truth
{ground_truth}

## Retrieved Contexts
{context_text}

## Task
1. Break the ground truth into individual factual statements/claims.
2. For each statement, determine if it can be attributed to (found in or inferred from) any of the contexts.
3. Calculate recall as: (attributed statements) / (total statements).

## Output Format (JSON only)
{{
  "statements": [
    {{"statement": "...", "attributed": true/false, "context_idx": N_or_null}},
    ...
  ],
  "total_statements": N,
  "attributed_statements": M,
  "score": M/N
}}

Return ONLY valid JSON, no other text."""

    try:
        result = call_gpt4o(prompt)
        result = result.strip()
        if result.startswith("```"):
            result = result.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        data = json.loads(result)
        score = float(data.get("score", 0))
        return max(0.0, min(1.0, score))
    except Exception as e:
        print(f"    [WARN] Context recall eval error: {e}")
        return 0.0


# ===========================================================================
# Answer Generation
# ===========================================================================
def generate_answer(question: str, contexts: List[str]) -> str:
    """Generate answer via DeepSeek for RAGAS evaluation (same pipeline as v16)."""
    context_text = "\n\n---\n\n".join(contexts[:5])
    prompt = f"""다음 컨텍스트를 참고하여 질문에 답변하세요.
컨텍스트에 없는 정보는 사용하지 마세요.

## 컨텍스트
{context_text}

## 질문
{question}

## 답변
간결하고 정확하게 한국어로 답변하세요."""

    try:
        resp = requests.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 500,
                "n": 1,
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"[Answer generation failed: {e}]"


def safe_val(v):
    """Convert NaN/None to 0.0."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return 0.0
    return round(float(v), 4)


def load_env():
    """Load environment variables from .env file."""
    global OPENAI_API_KEY, DEEPSEEK_API_KEY
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if "=" not in line or line.startswith("#"):
                    continue
                key, val = line.split("=", 1)
                val = val.strip().strip('"').strip("'")
                if key == "OPENAI_API_KEY" and not OPENAI_API_KEY:
                    OPENAI_API_KEY = val
                    os.environ["OPENAI_API_KEY"] = val
                elif key == "DEEPSEEK_API_KEY" and DEEPSEEK_API_KEY == "sk-7c3024219fb74302a296207d2a091fe5":
                    DEEPSEEK_API_KEY = val
                    os.environ["DEEPSEEK_API_KEY"] = val


# ===========================================================================
# Main
# ===========================================================================
def main():
    global OPENAI_API_KEY, DEEPSEEK_API_KEY

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'=' * 70}")
    print(f"  RAGAS v18 GPT-4o Judge Evaluation")
    print(f"  (GPT-4o Judge + /search/hybrid + DeepSeek Answer)")
    print(f"  {ts}")
    print(f"{'=' * 70}\n")

    # Load env
    load_env()

    if not OPENAI_API_KEY:
        print("  [ERROR] OPENAI_API_KEY not set.")
        sys.exit(1)

    print(f"  OpenAI API Key: ...{OPENAI_API_KEY[-8:]}")
    print(f"  DeepSeek API Key: ...{DEEPSEEK_API_KEY[-8:]}")

    # 1. Login + Warmup
    client = HRKPClient()
    if not client.login():
        print("  Login failed. Exiting.")
        sys.exit(1)
    print("  Login successful.")

    # Warmup to prevent first-query OOM
    client.warmup()
    print(f"  Waiting {INTER_QUERY_DELAY}s for service stabilization...\n")
    time.sleep(INTER_QUERY_DELAY)

    # 2. Phase 1: Search + Generate Answers
    print(f"[Phase 1] Hybrid Search + DeepSeek Answer ({len(TEST_QUESTIONS)} queries)...")
    print(f"  Inter-query delay: {INTER_QUERY_DELAY}s | Max retries: {MAX_RETRIES}")
    samples = []
    pipeline_meta = []
    total_search_time = 0.0
    failed_queries = 0

    for idx, q in enumerate(TEST_QUESTIONS):
        label = f"  Q{idx + 1:02d}/{len(TEST_QUESTIONS)} [{q['type']:18s}]"
        print(f"{label} {q['question'][:50]}...", end=" ", flush=True)
        t0 = time.time()

        try:
            sr = client.hybrid_search(q["question"], top_k=10)
            raw_results = sr.get("results", [])
            contexts = []
            for item in raw_results:
                content = item.get("content", "")
                if content and not content.startswith("**HRKP"):
                    contexts.append(content)
            latency = sr.get("latency_ms", 0)
        except Exception as e:
            print(f"FAIL({e})", end=" ", flush=True)
            contexts = []
            latency = 0
            failed_queries += 1

        # Generate answer via DeepSeek
        answer = generate_answer(q["question"], contexts) if contexts else "[No context retrieved]"
        elapsed = time.time() - t0
        total_search_time += elapsed

        graph_count = sum(
            1 for item in (raw_results if 'raw_results' in dir() else [])
            if isinstance(item, dict) and item.get("source_type") == "graph"
        ) if contexts else 0

        # Re-count from actual results
        try:
            graph_count = sum(1 for item in raw_results if item.get("source_type") == "graph")
        except:
            graph_count = 0

        samples.append({
            "question": q["question"],
            "answer": answer,
            "contexts": contexts[:5],
            "ground_truth": q["ground_truth"],
            "type": q["type"],
        })
        pipeline_meta.append({
            "idx": idx + 1,
            "latency_ms": latency,
            "context_count": len(contexts),
            "graph_results": graph_count,
            "total_results": len(raw_results) if contexts else 0,
        })
        print(f"OK ({elapsed:.1f}s, {len(contexts)} ctx, {graph_count} graph)")

        # Inter-query delay to prevent service overload
        if idx < len(TEST_QUESTIONS) - 1:
            time.sleep(INTER_QUERY_DELAY)

    samples_with_ctx = sum(1 for s in samples if s['contexts'])
    print(f"\n  Phase 1 complete: {total_search_time:.1f}s total")
    print(f"  Samples with contexts: {samples_with_ctx}/{len(samples)}")
    print(f"  Failed queries: {failed_queries}")

    if samples_with_ctx < 10:
        print(f"\n  [ERROR] Too few samples with contexts ({samples_with_ctx}). "
              f"AI service may be unstable. Aborting.")
        sys.exit(1)

    # 3. Phase 2: GPT-4o Judge Evaluation
    print(f"\n[Phase 2] GPT-4o Judge Evaluation ({samples_with_ctx} samples with contexts)...")
    eval_start = time.time()

    metric_names = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    per_sample = []
    all_scores = {m: [] for m in metric_names}

    for idx, s in enumerate(samples):
        label = f"  E{idx + 1:02d}/{len(samples)}"
        print(f"{label} {s['question'][:45]}...", end=" ", flush=True)

        if not s["contexts"]:
            # No context = score 0 for all metrics
            scores = {m: 0.0 for m in metric_names}
            print(f"SKIP (no ctx)")
        else:
            try:
                # Evaluate all 4 metrics
                faith = evaluate_faithfulness(s["question"], s["answer"], s["contexts"])
                relev = evaluate_answer_relevancy(s["question"], s["answer"])
                prec = evaluate_context_precision(s["question"], s["contexts"], s["ground_truth"])
                recall = evaluate_context_recall(s["question"], s["contexts"], s["ground_truth"])

                scores = {
                    "faithfulness": safe_val(faith),
                    "answer_relevancy": safe_val(relev),
                    "context_precision": safe_val(prec),
                    "context_recall": safe_val(recall),
                }
                print(f"F={faith:.2f} R={relev:.2f} P={prec:.2f} C={recall:.2f}")
            except Exception as e:
                print(f"ERR: {e}")
                scores = {m: 0.0 for m in metric_names}

        for m in metric_names:
            all_scores[m].append(scores[m])

        avg = sum(scores[m] for m in metric_names) / 4
        grade = "HIGH" if avg >= 0.70 else ("PARTIAL" if avg >= 0.40 else "NONE")

        per_sample.append({
            "idx": idx + 1,
            "question": s["question"],
            "type": s["type"],
            **scores,
            "avg": round(avg, 4),
            "grade": grade,
            "latency_ms": pipeline_meta[idx]["latency_ms"],
            "graph_results": pipeline_meta[idx]["graph_results"],
        })

    eval_elapsed = time.time() - eval_start
    print(f"\n  Phase 2 complete: {eval_elapsed:.1f}s ({eval_elapsed/len(samples):.1f}s/sample)")

    # 4. Aggregate Results
    final_scores = {}
    for m in metric_names:
        vals = all_scores[m]
        final_scores[m] = round(sum(vals) / len(vals), 4) if vals else 0.0

    valid_scores = [v for v in final_scores.values() if v is not None]
    arithmetic_mean = round(sum(valid_scores) / len(valid_scores), 4)

    # Grade
    if arithmetic_mean >= 0.80:
        grade = "A+"
    elif arithmetic_mean >= 0.75:
        grade = "A"
    elif arithmetic_mean >= 0.70:
        grade = "A-"
    elif arithmetic_mean >= 0.65:
        grade = "B+"
    elif arithmetic_mean >= 0.60:
        grade = "B"
    else:
        grade = "B-"

    # Print results
    print(f"\n{'=' * 70}")
    print(f"  RESULTS: v18(GPT-4o Judge) vs v16(DeepSeek Judge)")
    print(f"{'=' * 70}")
    print(f"  {'Metric':22s}  {'v18(GPT4o)':>10s}  {'v16(DS)':>8s}  {'Delta':>8s}")
    print(f"  {'-' * 55}")
    for m in metric_names:
        v18 = final_scores.get(m, 0)
        v16 = V16_BASELINE.get(m)
        if v16 is not None:
            delta = v18 - v16
            sign = "+" if delta >= 0 else ""
            print(f"  {m:22s}  {v18:10.4f}  {v16:8.4f}  {sign}{delta:.4f}")
        else:
            print(f"  {m:22s}  {v18:10.4f}  {'N/A':>8s}  {'NEW':>8s}")

    print(f"  {'-' * 55}")
    v16_mean = V16_BASELINE.get("arithmetic_mean", 0)
    delta_mean = arithmetic_mean - v16_mean
    sign = "+" if delta_mean >= 0 else ""
    print(f"  {'Arithmetic Mean':22s}  {arithmetic_mean:10.4f}  {v16_mean:8.4f}  {sign}{delta_mean:.4f}")
    print(f"\n  Grade: {grade} (Mean={arithmetic_mean:.4f})")

    # Quality Gate
    grades_dist = {"HIGH": 0, "PARTIAL": 0, "NONE": 0}
    for s in per_sample:
        grades_dist[s["grade"]] += 1

    print(f"\n  Quality Gate Distribution:")
    print(f"    HIGH={grades_dist['HIGH']}, PARTIAL={grades_dist['PARTIAL']}, NONE={grades_dist['NONE']}")

    # Domain breakdown
    domains = sorted(set(q["type"] for q in TEST_QUESTIONS))
    print(f"\n  Domain Breakdown:")
    print(f"  {'Domain':20s}  {'Faith':>7s}  {'Relev':>7s}  {'Prec':>7s}  {'Recall':>7s}  {'Avg':>7s}")
    print(f"  {'-' * 65}")

    domain_scores = {}
    for d in domains:
        ds = [s for s in per_sample if s["type"] == d]
        if ds:
            avg_f = sum(s["faithfulness"] for s in ds) / len(ds)
            avg_r = sum(s["answer_relevancy"] for s in ds) / len(ds)
            avg_p = sum(s["context_precision"] for s in ds) / len(ds)
            avg_c = sum(s["context_recall"] for s in ds) / len(ds)
            avg_all = (avg_f + avg_r + avg_p + avg_c) / 4
            domain_scores[d] = {
                "faithfulness": round(avg_f, 4),
                "answer_relevancy": round(avg_r, 4),
                "context_precision": round(avg_p, 4),
                "context_recall": round(avg_c, 4),
                "avg": round(avg_all, 4),
            }
            print(f"  {d:20s}  {avg_f:7.3f}  {avg_r:7.3f}  {avg_p:7.3f}  {avg_c:7.3f}  {avg_all:7.3f}")

    # Latency stats
    latencies = [s["latency_ms"] for s in per_sample if s["latency_ms"] > 0]
    if latencies:
        latencies.sort()
        p50 = latencies[len(latencies) // 2]
        p95 = latencies[int(len(latencies) * 0.95)]
        print(f"\n  Latency: P50={p50:.0f}ms, P95={p95:.0f}ms, Avg={sum(latencies)/len(latencies):.0f}ms")

    # Save JSON
    result_dir = Path(__file__).parent.parent / "docs" / "04_testing" / "11_ragas" / "results"
    result_dir.mkdir(parents=True, exist_ok=True)

    output = {
        "version": "v18",
        "timestamp": datetime.now().isoformat(),
        "purpose": "GPT-4o Judge 평가 - DeepSeek judge 대비 평가 안정성 비교",
        "method": "same-pipeline (search: REST API, answer: DeepSeek, judge: GPT-4o)",
        "config": {
            "candidates_cap": 50,
            "graph_search_top_k": 10,
            "reranker_passes": 1,
            "rerank_candidate_count_formula": "min(top_k*3, 50)",
            "rerank_candidate_count_actual": 15,
            "answer_generation": "DeepSeek API direct",
            "judge_llm": "GPT-4o",
            "judge_embeddings": "text-embedding-3-small",
            "ragas_metrics_implementation": "RAGAS-equivalent prompts via GPT-4o API",
            "inter_query_delay_sec": INTER_QUERY_DELAY,
        },
        "scores": final_scores,
        "arithmetic_mean": arithmetic_mean,
        "grade": grade,
        "latency_stats": {
            "avg_ms": round(sum(latencies) / len(latencies), 1) if latencies else 0,
            "median_ms": round(latencies[len(latencies) // 2], 1) if latencies else 0,
            "p95_ms": round(latencies[int(len(latencies) * 0.95)], 1) if latencies else 0,
            "real_count": len(latencies),
        },
        "v16_baseline": V16_BASELINE,
        "v11_baseline": V11_BASELINE,
        "delta_vs_v16": {
            m: round(final_scores.get(m, 0) - V16_BASELINE.get(m, 0), 4)
            for m in metric_names
            if V16_BASELINE.get(m) is not None
        },
        "quality_gate": grades_dist,
        "domain_scores": domain_scores,
        "individual_results": per_sample,
        "timing": {
            "search_generate_sec": round(total_search_time, 1),
            "ragas_eval_sec": round(eval_elapsed, 1),
            "total_sec": round(total_search_time + eval_elapsed, 1),
        },
    }

    json_path = result_dir / "ragas_v18_result.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n  JSON saved: {json_path}")

    tmp_path = "/tmp/ragas_v18_gpt4o_result.json"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"  JSON saved: {tmp_path}")

    # Summary
    print(f"\n{'=' * 70}")
    print(f"  SUMMARY")
    print(f"{'=' * 70}")
    print(f"  v18 GPT-4o Judge: Mean={arithmetic_mean:.4f} ({grade})")
    for m in metric_names:
        v = final_scores.get(m, 0)
        print(f"    {m}: {v:.4f}")
    print(f"  v16 DeepSeek Judge: Mean={v16_mean:.4f}")
    print(f"  Delta: {sign}{delta_mean:.4f}p")
    print(f"  Queries: {samples_with_ctx}/{len(samples)} with contexts, {failed_queries} failed")
    print(f"  Time: Search={total_search_time:.0f}s, Eval={eval_elapsed:.0f}s, Total={total_search_time + eval_elapsed:.0f}s")

    print(f"\n{'=' * 70}")
    print(f"  v18 GPT-4o Judge Evaluation Complete!")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    main()
