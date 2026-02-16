#!/usr/bin/env python3
"""
RAGAS v10 Post-Entity Extraction Round 2 Evaluation
====================================================
Phase 3 Entity Extraction Round 2 완료 후 검색 품질 평가.
/search/chat 엔드포인트(Reranker 포함 전체 파이프라인) 사용.

변경점 (v9 대비):
- Neo4j: 92,209 Entity (v9: 70,855 +30%)
- Neo4j: 419,066 MENTIONS + 317,003 RELATED (v9: 375,229 총)
- ES: 42,462 chunks (v9: 56,063 - tc<50 삭제)
- Reranker: BGE-Reranker 활성화
- Endpoint: /search/chat (전체 RAG 파이프라인)

실행:
    docker exec kp-ai-service python3 /app/scripts/ragas_v10_post_entity_eval.py
"""

import json
import math
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List

import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_URL = os.getenv("HRKP_API_URL", "http://localhost:8000/api/v1")
LOGIN_EMAIL = "admin@example.com"
LOGIN_PASSWORD = "admin123!"
DEEPSEEK_API_KEY = os.getenv(
    "DEEPSEEK_API_KEY", "sk-7c3024219fb74302a296207d2a091fe5"
)
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

TOKEN_REFRESH_INTERVAL = 15

# Baselines for comparison
V8_BASELINE = {
    "faithfulness": 0.919,
    "answer_relevancy": 0.647,
    "context_precision": 0.489,
    "context_recall": 0.474,
}

V9_BASELINE = {
    "faithfulness": 0.9127,
    "answer_relevancy": 0.547,
    "context_precision": 0.5768,
    "context_recall": 0.5997,
}

# Same 51 questions (7 domains)
TEST_QUESTIONS = [
    {
        "question": "Neo4j와 Elasticsearch의 역할 차이점은?",
        "type": "entity_relation",
        "ground_truth": "Neo4j는 Knowledge Graph 저장소로 엔티티 간 관계를 관리하고, Elasticsearch는 벡터 검색(kNN)과 BM25 키워드 검색을 담당합니다.",
    },
    {
        "question": "LangGraph와 LangChain 중 어떤 것을 사용해야 하나요?",
        "type": "entity_relation",
        "ground_truth": "LangGraph는 상태 기반 에이전트 워크플로우에 적합하고, LangChain은 단순 체인 기반 RAG 파이프라인에 적합합니다.",
    },
    {
        "question": "FastAPI와 PostgreSQL을 연동하여 RAGAS 평가를 수행하려면?",
        "type": "entity_relation",
        "ground_truth": "FastAPI에서 asyncpg로 PostgreSQL에 연결하고, RAGAS 라이브러리를 통해 Faithfulness 등 메트릭을 측정합니다.",
    },
    {
        "question": "PostgreSQL과 Neo4j의 데이터 모델 차이는?",
        "type": "entity_relation",
        "ground_truth": "PostgreSQL은 관계형 SSOT 저장소이고, Neo4j는 그래프 데이터베이스로 엔티티 간 관계를 노드-엣지로 표현합니다.",
    },
    {
        "question": "Spring Cloud Gateway와 FastAPI의 역할 분담은?",
        "type": "entity_relation",
        "ground_truth": "Spring Cloud Gateway는 API Gateway로 라우팅/인증을 담당하고, FastAPI는 AI Service 백엔드로 RAG 파이프라인을 실행합니다.",
    },
    {
        "question": "BGE-M3와 BGE-Reranker의 역할 차이는?",
        "type": "entity_relation",
        "ground_truth": "BGE-M3는 Bi-encoder로 문서/쿼리를 벡터로 변환하고, BGE-Reranker는 Cross-encoder로 검색 결과의 순위를 재조정합니다.",
    },
    {
        "question": "DeepSeek V3와 OpenAI GPT의 비용 및 성능 차이는?",
        "type": "entity_relation",
        "ground_truth": "DeepSeek V3는 OpenAI GPT 대비 95% 비용 절감이 가능하며, 한국어 RAG 파이프라인에서 충분한 성능을 제공합니다.",
    },
    {
        "question": "RAG Pipeline에서 BGE-M3 임베딩 모델의 역할은?",
        "type": "multi_hop",
        "ground_truth": "BGE-M3는 RAG Pipeline에서 문서와 쿼리를 1024차원 벡터로 변환하여 시맨틱 검색을 가능하게 합니다.",
    },
    {
        "question": "Knowledge Graph 엔티티 추출이 RAG 검색 품질에 기여하는 방식은?",
        "type": "multi_hop",
        "ground_truth": "엔티티 추출로 문서 간 관계를 Knowledge Graph에 저장하고, Graph Search 채널로 관계 기반 검색을 제공합니다.",
    },
    {
        "question": "Agentic AI 에이전트 워크플로우 설계 패턴은 무엇인가요?",
        "type": "multi_hop",
        "ground_truth": "Agentic AI 워크플로우는 Planner-Retriever-Generator 패턴을 따르며 LangGraph로 상태 기반 그래프를 구현합니다.",
    },
    {
        "question": "LangGraph에서 상태(State) 관리와 노드 간 데이터 전달 방식은?",
        "type": "multi_hop",
        "ground_truth": "LangGraph는 TypedDict 기반 State를 정의하고, 노드 함수가 State를 받아 수정 후 반환하는 방식으로 데이터를 전달합니다.",
    },
    {
        "question": "ETL 파이프라인에서 문서 파싱부터 임베딩 저장까지의 전체 흐름은?",
        "type": "multi_hop",
        "ground_truth": "문서를 Docling으로 파싱하고, 시맨틱 청커로 분할한 후, BGE-M3로 벡터화하여 Elasticsearch에 색인합니다.",
    },
    {
        "question": "Hybrid Search에서 RRF 퓨전이 단일 검색보다 나은 이유는?",
        "type": "multi_hop",
        "ground_truth": "RRF는 Vector, BM25, Graph 등 서로 다른 검색 채널의 순위를 융합하여 단일 채널의 약점을 보완합니다.",
    },
    {
        "question": "AI 에이전트에서 Tool Calling과 Reasoning의 상호작용은?",
        "type": "multi_hop",
        "ground_truth": "AI 에이전트는 Reasoning으로 문제를 분석한 후 적절한 Tool을 선택하여 호출하고 결과를 다시 Reasoning에 반영합니다.",
    },
    {
        "question": "Docker Compose에서 컨테이너 간 네트워크 통신 설정 방법은?",
        "type": "keyword",
        "ground_truth": "docker-compose.yml에서 networks를 정의하고 서비스마다 네트워크를 지정하면 컨테이너 간 호스트명으로 통신합니다.",
    },
    {
        "question": "RRF 알고리즘이 Hybrid 검색에서 하는 역할은?",
        "type": "keyword",
        "ground_truth": "RRF(Reciprocal Rank Fusion)는 Vector, BM25, Graph 검색 결과의 순위를 융합하여 최종 순위를 결정합니다.",
    },
    {
        "question": "RAGAS 평가 메트릭의 종류와 의미는?",
        "type": "keyword",
        "ground_truth": "Faithfulness(충실도), Answer Relevancy(답변 관련성), Context Precision(맥락 정밀도), Context Recall(맥락 재현율) 4가지입니다.",
    },
    {
        "question": "JWT 인증 토큰의 장점과 단점은 무엇인가요?",
        "type": "keyword",
        "ground_truth": "JWT는 서버 상태 비저장(stateless) 인증이 가능하지만, 토큰 만료 전 무효화가 어렵고 크기가 큰 단점이 있습니다.",
    },
    {
        "question": "Kubernetes에서 Spring Boot 마이크로서비스를 배포하는 방법은?",
        "type": "keyword",
        "ground_truth": "Spring Boot 앱을 Docker 이미지로 빌드한 후 Kubernetes Deployment와 Service를 생성하여 배포합니다.",
    },
    {
        "question": "Elasticsearch 벡터 검색을 위한 인덱스 설정 방법은?",
        "type": "keyword",
        "ground_truth": "dense_vector 타입 필드를 정의하고 dims, similarity, knn 옵션을 설정하여 벡터 검색 인덱스를 생성합니다.",
    },
    {
        "question": "WBS(Work Breakdown Structure)란 무엇이며 프로젝트 관리에서 어떻게 활용하나요?",
        "type": "keyword",
        "ground_truth": "WBS는 프로젝트를 작은 작업 단위로 분해하여 체계적으로 관리하는 구조로, 범위 정의와 일정 관리에 활용됩니다.",
    },
    {
        "question": "대규모 문서를 효율적으로 처리하는 방법은?",
        "type": "semantic",
        "ground_truth": "청킹(chunking)으로 문서를 분할하고 배치 임베딩으로 벡터화한 후 Elasticsearch에 색인합니다.",
    },
    {
        "question": "검색 성능을 최적화하려면 어떻게 해야 하나요?",
        "type": "semantic",
        "ground_truth": "Hybrid 검색(BM25+Dense+Graph), RRF 퓨전, Redis 캐싱, 배치 임베딩으로 성능을 최적화합니다.",
    },
    {
        "question": "환경변수를 안전하게 관리하는 방법은?",
        "type": "semantic",
        "ground_truth": ".env 파일에 환경변수를 정의하고 docker-compose에서 env_file로 로드하며, 시크릿은 별도 관리합니다.",
    },
    {
        "question": "답변 품질을 체계적으로 평가하는 방법론은 무엇인가요?",
        "type": "semantic",
        "ground_truth": "RAGAS 프레임워크로 Faithfulness, Answer Relevancy, Context Precision, Context Recall을 측정하여 체계적으로 평가합니다.",
    },
    {
        "question": "반복적이고 점진적인 개발 방법론은 어떤 것이 있나요?",
        "type": "semantic",
        "ground_truth": "Agile/Scrum 방법론으로 Sprint 단위 반복 개발, 데일리 스크럼, 스프린트 리뷰를 통해 점진적으로 발전시킵니다.",
    },
    {
        "question": "데이터베이스 마이그레이션을 안전하게 수행하는 방법은?",
        "type": "semantic",
        "ground_truth": "Flyway/Alembic 등 마이그레이션 도구를 사용하여 스키마 변경을 버전 관리하고 롤백 가능하게 합니다.",
    },
    {
        "question": "마이크로서비스 아키텍처에서 서비스 간 통신 패턴은?",
        "type": "semantic",
        "ground_truth": "동기 방식(REST, gRPC)과 비동기 방식(이벤트 기반 메시징)이 있으며, API Gateway로 진입점을 통합합니다.",
    },
    {
        "question": "Spring Cloud Gateway에서 API 라우팅과 필터를 설정하는 방법은?",
        "type": "graph_entity",
        "ground_truth": "Spring Cloud Gateway에서 RouteLocator로 라우팅 규칙을 정의하고, GlobalFilter로 인증/로깅 등 필터를 적용합니다.",
    },
    {
        "question": "Gleaning 기법이란 무엇이며 RAG 파이프라인에서 어떻게 활용되나요?",
        "type": "graph_entity",
        "ground_truth": "Gleaning은 LLM이 추출한 엔티티를 반복 검증하여 Knowledge Graph의 품질을 높이는 기법입니다.",
    },
    {
        "question": "cosine similarity와 dot product 유사도의 차이와 적합한 사용 시나리오는?",
        "type": "graph_entity",
        "ground_truth": "cosine similarity는 방향만 비교하여 정규화된 벡터에 적합하고, dot product는 크기도 반영하여 비정규화 벡터에 적합합니다.",
    },
    {
        "question": "SSOT 원칙이란 무엇이며 데이터 아키텍처에서 왜 중요한가요?",
        "type": "graph_entity",
        "ground_truth": "SSOT(Single Source of Truth)는 데이터의 단일 원본을 유지하는 원칙으로, PostgreSQL이 SSOT 역할을 합니다.",
    },
    {
        "question": "Vector Search와 Graph Search를 결합하면 어떤 이점이 있나요?",
        "type": "graph_entity",
        "ground_truth": "Vector Search는 의미 유사성 기반 검색을, Graph Search는 엔티티 관계 기반 검색을 제공하여 상호 보완합니다.",
    },
    {
        "question": "React 18에서 Concurrent 렌더링과 Suspense를 활용하는 방법은?",
        "type": "graph_entity",
        "ground_truth": "React 18의 Concurrent 렌더링은 UI 응답성을 높이고, Suspense는 비동기 데이터 로딩을 선언적으로 처리합니다.",
    },
    {
        "question": "Python 3.11의 ExceptionGroup과 except* 구문의 사용 방법은?",
        "type": "graph_entity",
        "ground_truth": "ExceptionGroup은 여러 예외를 하나로 묶고, except*로 특정 예외 유형만 선택적으로 처리합니다.",
    },
    {
        "question": "AI Service에서 RAG Pipeline의 전체 처리 흐름은?",
        "type": "graph_entity",
        "ground_truth": "쿼리 입력 -> Hybrid 검색(BM25+Dense+Sparse+Graph) -> RRF 퓨전 -> Quality Gate -> LLM 생성 순서입니다.",
    },
    {
        "question": "개인정보보호법에서 개인정보 수집 시 동의 요건은?",
        "type": "legal",
        "ground_truth": "개인정보보호법에 따라 정보주체의 동의를 받아야 하며, 수집 목적, 항목, 보유 기간을 명시해야 합니다.",
    },
    {
        "question": "GDPR의 핵심 원칙과 국내 기업의 준수 사항은?",
        "type": "legal",
        "ground_truth": "GDPR은 데이터 최소 수집, 목적 제한, 정보주체 권리 보장 등을 요구하며, EU 시민 데이터 처리 시 준수해야 합니다.",
    },
    {
        "question": "민법에서 계약의 성립 요건은 무엇인가요?",
        "type": "legal",
        "ground_truth": "계약은 당사자 간 청약과 승낙의 합치로 성립하며, 의사표시의 합치가 핵심 요건입니다.",
    },
    {
        "question": "SLA(서비스 수준 협약)에서 반드시 포함해야 할 핵심 항목은?",
        "type": "legal",
        "ground_truth": "가용성(Uptime), 응답 시간, 장애 대응 시간, 보상 조건, 측정 방법 등이 SLA 핵심 항목입니다.",
    },
    {
        "question": "ISMS 인증을 위한 정보보안 점검 항목은?",
        "type": "legal",
        "ground_truth": "관리체계 수립, 보호대책 구현, 접근 통제, 침해사고 대응, 개인정보 보호 등을 점검합니다.",
    },
    {
        "question": "소프트웨어 라이선스 종류(MIT, GPL, Apache)의 차이는?",
        "type": "legal",
        "ground_truth": "MIT는 최소 제약, GPL은 파생물도 GPL 적용 의무, Apache는 특허권 명시 허가가 특징입니다.",
    },
    {
        "question": "법령 용어에서 '선의'와 '악의'의 법률적 의미 차이는?",
        "type": "legal",
        "ground_truth": "법률에서 선의는 어떤 사실을 모르는 상태, 악의는 어떤 사실을 알고 있는 상태를 의미합니다.",
    },
    {
        "question": "RAG(Retrieval-Augmented Generation) 시스템의 동작 원리는?",
        "type": "factual",
        "ground_truth": "RAG는 질문에 관련된 문서를 검색(Retrieval)한 후 LLM이 검색된 컨텍스트를 참고하여 답변을 생성(Generation)합니다.",
    },
    {
        "question": "Transformer 아키텍처의 Self-Attention 메커니즘은?",
        "type": "factual",
        "ground_truth": "Self-Attention은 입력 시퀀스의 각 토큰이 다른 모든 토큰과의 관련도를 계산하여 문맥 정보를 인코딩합니다.",
    },
    {
        "question": "Reranking이 RAG 검색 품질을 향상시키는 원리는?",
        "type": "factual",
        "ground_truth": "Reranking은 Cross-encoder로 쿼리와 문서 쌍의 관련성을 정밀 평가하여 초기 검색 결과의 순위를 재조정합니다.",
    },
    {
        "question": "HNSW와 IVF 벡터 인덱스 알고리즘의 비교는?",
        "type": "factual",
        "ground_truth": "HNSW는 그래프 기반으로 높은 검색 정확도를 제공하고, IVF는 클러스터 기반으로 메모리 효율이 좋습니다.",
    },
    {
        "question": "Chain of Thought 추론이 LLM 성능에 미치는 영향은?",
        "type": "factual",
        "ground_truth": "Chain of Thought는 LLM이 단계별로 추론하도록 유도하여 복잡한 문제 해결 능력을 향상시킵니다.",
    },
    {
        "question": "벡터 임베딩의 차원 수가 검색 정확도에 미치는 영향은?",
        "type": "factual",
        "ground_truth": "차원이 높을수록 의미 표현력이 증가하나 계산 비용도 증가하며, 1024차원이 성능과 효율의 균형점입니다.",
    },
    {
        "question": "비즈니스에 실제 활용 가능한 LLM 서비스를 만들기 위한 핵심 고려사항은?",
        "type": "factual",
        "ground_truth": "프롬프트 설계, RAG 파이프라인, 평가 체계, 비용 최적화, 할루시네이션 방지가 핵심 고려사항입니다.",
    },
    {
        "question": "프롬프트 엔지니어링의 핵심 원칙과 효과적인 기법은?",
        "type": "factual",
        "ground_truth": "명확한 지시, 예시 제공(few-shot), 역할 부여, 단계별 사고 유도가 핵심 기법입니다.",
    },
]


class HRKPClient:
    """HRKP API client with token refresh."""

    def __init__(self):
        self.base_url = BASE_URL.rstrip("/")
        self.session = requests.Session()
        self._query_count = 0

    def login(self) -> bool:
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
        print(f"  [ERROR] Login failed: {r.status_code}")
        return False

    def _maybe_refresh(self):
        self._query_count += 1
        if self._query_count >= TOKEN_REFRESH_INTERVAL:
            self.login()

    def chat_search(self, query: str, top_k: int = 10) -> Dict:
        """Use /search/chat endpoint - full RAG pipeline with reranker."""
        self._maybe_refresh()
        r = self.session.post(
            f"{self.base_url}/search/chat",
            json={"query": query, "top_k": top_k},
            timeout=180,
        )
        r.raise_for_status()
        return r.json()

    def hybrid_search(self, query: str, top_k: int = 10) -> Dict:
        """Use /search/hybrid for raw context extraction."""
        self._maybe_refresh()
        r = self.session.post(
            f"{self.base_url}/search/hybrid",
            json={
                "query": query,
                "top_k": top_k,
                "useGraph": True,
                "useVector": True,
            },
            timeout=120,
        )
        r.raise_for_status()
        return r.json()


def generate_answer(question: str, contexts: List[str]) -> str:
    """Generate answer via DeepSeek for RAGAS evaluation."""
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


def run_ragas_library_eval(samples: List[Dict]) -> Any:
    """RAGAS 0.2.15 library evaluation."""
    from langchain_openai import ChatOpenAI
    from ragas import evaluate
    from ragas.llms import LangchainLLMWrapper
    from ragas.metrics import (
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall,
    )
    from ragas.dataset_schema import EvaluationDataset, SingleTurnSample

    # DeepSeek as evaluation LLM
    llm = ChatOpenAI(
        model="deepseek-chat",
        openai_api_key=DEEPSEEK_API_KEY,
        openai_api_base=f"{DEEPSEEK_BASE_URL}/v1",
        temperature=0.0,
        n=1,
    )
    ragas_llm = LangchainLLMWrapper(llm)

    # Build evaluation dataset
    eval_samples = []
    for s in samples:
        eval_samples.append(
            SingleTurnSample(
                user_input=s["question"],
                response=s["answer"],
                retrieved_contexts=s["contexts"],
                reference=s["ground_truth"],
            )
        )
    eval_dataset = EvaluationDataset(samples=eval_samples)

    # Embeddings for answer_relevancy
    from langchain_community.embeddings import HuggingFaceEmbeddings as LCHFEmb
    from ragas.embeddings import LangchainEmbeddingsWrapper

    lc_embeddings = LCHFEmb(
        model_name="BAAI/bge-small-en-v1.5",
        cache_folder="/app/.cache/huggingface/hub",
    )
    ragas_embeddings = LangchainEmbeddingsWrapper(lc_embeddings)

    print(f"  Running RAGAS evaluate on {len(eval_samples)} samples...")
    result = evaluate(
        dataset=eval_dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        llm=ragas_llm,
        embeddings=ragas_embeddings,
        raise_exceptions=False,
    )

    return result


def main():
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'=' * 70}")
    print(f"  RAGAS v10 Post-Entity Extraction Round 2 Evaluation")
    print(f"  (RAGAS 0.2.15 Library + /search/hybrid pipeline)")
    print(f"  {ts}")
    print(f"{'=' * 70}\n")

    # 1. Login
    client = HRKPClient()
    if not client.login():
        print("  Login failed. Exiting.")
        sys.exit(1)
    print("  Login successful.\n")

    # 2. Phase 1: Search + Generate Answers
    print(f"[Phase 1] Hybrid Search + Answer Generation ({len(TEST_QUESTIONS)} queries)...")
    samples = []
    pipeline_meta = []
    total_search_time = 0.0

    for idx, q in enumerate(TEST_QUESTIONS):
        label = f"  Q{idx + 1:02d}/{len(TEST_QUESTIONS)} [{q['type']:18s}]"
        print(f"{label} {q['question'][:50]}...", end=" ", flush=True)
        t0 = time.time()

        try:
            sr = client.hybrid_search(q["question"], top_k=10)
            raw_results = sr.get("results", [])
            # Extract raw text contexts (skip AI-generated responses)
            contexts = []
            for item in raw_results:
                content = item.get("content", "")
                if content and not content.startswith("**HRKP"):
                    contexts.append(content)
            latency = sr.get("latency_ms", 0)
        except Exception as e:
            print(f"FAIL: {e}")
            contexts = []
            latency = 0

        # Generate answer via DeepSeek
        answer = generate_answer(q["question"], contexts) if contexts else "[No context]"
        elapsed = time.time() - t0
        total_search_time += elapsed

        # Collect graph contribution info
        graph_count = sum(
            1 for item in raw_results if item.get("source_type") == "graph"
        )

        samples.append(
            {
                "question": q["question"],
                "answer": answer,
                "contexts": contexts[:5],
                "ground_truth": q["ground_truth"],
                "type": q["type"],
            }
        )
        pipeline_meta.append(
            {
                "idx": idx + 1,
                "latency_ms": latency,
                "context_count": len(contexts),
                "graph_results": graph_count,
                "total_results": len(raw_results),
            }
        )
        print(f"OK ({elapsed:.1f}s, {len(contexts)} ctx, {graph_count} graph)")

    print(f"\n  Phase 1 complete: {total_search_time:.1f}s total")

    # 3. Phase 2: RAGAS Library Evaluation
    print(f"\n[Phase 2] RAGAS 0.2.15 Library Evaluation...")
    eval_start = time.time()

    try:
        ragas_result = run_ragas_library_eval(samples)
        eval_elapsed = time.time() - eval_start
        print(f"\n  RAGAS evaluation completed in {eval_elapsed:.1f}s")

        # Extract scores from DataFrame
        df = ragas_result.to_pandas()
        metric_names = [
            "faithfulness",
            "answer_relevancy",
            "context_precision",
            "context_recall",
        ]
        scores = {}
        for m in metric_names:
            if m in df.columns:
                vals = [safe_val(v) for v in df[m]]
                scores[m] = round(sum(vals) / len(vals), 4) if vals else 0.0
            else:
                scores[m] = 0.0

        # Print results
        print(f"\n{'=' * 70}")
        print(f"  RESULTS: v10 vs v9 vs v8")
        print(f"{'=' * 70}")
        print(f"  {'Metric':22s}  {'v10':>8s}  {'v9':>8s}  {'v8':>8s}  {'v9->v10':>8s}")
        print(f"  {'-' * 60}")
        for m in metric_names:
            v10 = scores[m]
            v9 = V9_BASELINE[m]
            v8 = V8_BASELINE[m]
            delta = v10 - v9
            sign = "+" if delta >= 0 else ""
            print(
                f"  {m:22s}  {v10:8.4f}  {v9:8.4f}  {v8:8.4f}  {sign}{delta:.4f}"
            )

        # Per-sample scores
        per_sample = []
        for idx, row in df.iterrows():
            s = {
                "idx": idx + 1,
                "question": samples[idx]["question"],
                "type": samples[idx]["type"],
            }
            for m in metric_names:
                s[m] = safe_val(row.get(m, 0)) if m in df.columns else 0.0
            avg = sum(s[m] for m in metric_names) / 4
            s["avg"] = round(avg, 4)
            s["grade"] = (
                "HIGH" if avg >= 0.70 else ("PARTIAL" if avg >= 0.40 else "NONE")
            )
            # Add pipeline metadata
            meta = pipeline_meta[idx]
            s["latency_ms"] = meta["latency_ms"]
            s["graph_results"] = meta["graph_results"]
            per_sample.append(s)

        # Quality Gate
        grades = {"HIGH": 0, "PARTIAL": 0, "NONE": 0}
        for s in per_sample:
            grades[s["grade"]] += 1

        print(f"\n  Quality Gate Distribution:")
        print(
            f"    HIGH={grades['HIGH']}, PARTIAL={grades['PARTIAL']}, NONE={grades['NONE']}"
        )
        print(
            f"    (v9: HIGH={28}, PARTIAL={12}, NONE={11})"
        )

        # Domain breakdown
        domains = sorted(set(q["type"] for q in TEST_QUESTIONS))
        print(f"\n  Domain Breakdown:")
        print(
            f"  {'Domain':20s}  {'Faith':>7s}  {'Relev':>7s}  {'Prec':>7s}  {'Recall':>7s}  {'Avg':>7s}"
        )
        print(f"  {'-' * 65}")

        domain_scores = {}
        for d in domains:
            ds = [s for s in per_sample if samples[s["idx"] - 1]["type"] == d]
            if ds:
                avg_f = sum(s["faithfulness"] for s in ds) / len(ds)
                avg_r = sum(s["answer_relevancy"] for s in ds) / len(ds)
                avg_p = sum(s["context_precision"] for s in ds) / len(ds)
                avg_c = sum(s["context_recall"] for s in ds) / len(ds)
                avg_all = (avg_f + avg_r + avg_p + avg_c) / 4
                domain_scores[d] = {
                    "faithfulness": round(avg_f, 3),
                    "answer_relevancy": round(avg_r, 3),
                    "context_precision": round(avg_p, 3),
                    "context_recall": round(avg_c, 3),
                    "avg": round(avg_all, 3),
                }
                print(
                    f"  {d:20s}  {avg_f:7.3f}  {avg_r:7.3f}  {avg_p:7.3f}  {avg_c:7.3f}  {avg_all:7.3f}"
                )

        # Graph contribution analysis
        print(f"\n  Graph Contribution Analysis:")
        high_graph = [s for s in per_sample if s["graph_results"] >= 5]
        low_graph = [s for s in per_sample if s["graph_results"] < 3]
        if high_graph:
            hg_high = sum(1 for s in high_graph if s["grade"] == "HIGH")
            print(
                f"    High Graph (5+): {len(high_graph)} queries, HIGH={hg_high} ({100*hg_high/len(high_graph):.0f}%)"
            )
        if low_graph:
            lg_high = sum(1 for s in low_graph if s["grade"] == "HIGH")
            print(
                f"    Low Graph (0-2): {len(low_graph)} queries, HIGH={lg_high} ({100*lg_high/len(low_graph):.0f}%)"
            )

        # Latency stats
        latencies = [s["latency_ms"] for s in per_sample if s["latency_ms"] > 0]
        if latencies:
            latencies.sort()
            p50 = latencies[len(latencies) // 2]
            p95 = latencies[int(len(latencies) * 0.95)]
            print(f"\n  Latency: P50={p50:.0f}ms, P95={p95:.0f}ms, Avg={sum(latencies)/len(latencies):.0f}ms")

        # Save JSON output
        output = {
            "version": "v10_post_entity_r2",
            "ragas_version": "0.2.15",
            "timestamp": ts,
            "environment": {
                "es_chunks": 42462,
                "neo4j_entities": 92209,
                "neo4j_mentions": 419066,
                "neo4j_related": 317003,
                "neo4j_part_of": 39297,
                "reranker": True,
                "endpoint": "/search/hybrid + DeepSeek generate",
                "search_channels": "4-Way RRF (Dense+BM25+Sparse+Graph)",
            },
            "metrics": scores,
            "v9_baseline": V9_BASELINE,
            "v8_baseline": V8_BASELINE,
            "quality_gate": grades,
            "domain_scores": domain_scores,
            "per_sample": per_sample,
            "timing": {
                "search_generate_sec": round(total_search_time, 1),
                "ragas_eval_sec": round(eval_elapsed, 1),
                "total_sec": round(total_search_time + eval_elapsed, 1),
            },
        }
        json_path = "/tmp/ragas_v10_post_entity_result.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\n  JSON saved: {json_path}")

    except Exception as e:
        print(f"\n  [ERROR] RAGAS evaluation failed: {e}")
        import traceback

        traceback.print_exc()
        eval_elapsed = time.time() - eval_start

    print(f"\n{'=' * 70}")
    print(f"  v10 Post-Entity Extraction Round 2 Evaluation Complete!")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    main()
