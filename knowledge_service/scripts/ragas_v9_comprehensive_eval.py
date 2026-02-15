#!/usr/bin/env python3
"""
RAGAS v9 종합 평가 - ETL v2 + 4-Way RRF + Graph RAG
=====================================================
v8 (2-channel Hybrid: Dense + BM25 Nori) 대비
v9 (4-channel RRF: Dense + BM25 + Sparse + Graph) 비교 평가

평가 환경:
  - ES 인덱스: knowledge_chunks (56,063 chunks)
  - 검색 방식: 4-Way RRF (Dense + BM25 + Sparse + Graph)
  - RRF 가중치: Vector=1.0, Keyword=1.0, Sparse=0.7, Graph=0.8
  - Entity: 70,855개, Relationship: 375,229개
  - LLM: DeepSeek V3.2 (deepseek-chat)
  - 질문: 51개, 7개 도메인

실행:
    docker exec kp-ai-service python3 /app/scripts/ragas_v9_comprehensive_eval.py
"""

import json
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_URL = os.getenv("HRKP_API_URL", "http://localhost:8000/api/v1")
LOGIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")
LOGIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123!")
DEEPSEEK_API_KEY = os.getenv(
    "DEEPSEEK_API_KEY", "sk-7c3024219fb74302a296207d2a091fe5"
)
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

TOKEN_REFRESH_INTERVAL = 15

# v8 baseline (2026-02-13, 51 queries, RAGAS 0.4.3, Nori+Hybrid 2-channel)
V8_BASELINE = {
    "faithfulness": 0.919,
    "answer_relevancy": 0.647,
    "context_precision": 0.489,
    "context_recall": 0.474,
    "quality_gate": {"HIGH": 24, "PARTIAL": 16, "NONE": 11},
}

# ---------------------------------------------------------------------------
# Test Dataset (51 questions - 7 domains)
# Aligned with v7/v8 comprehensive evaluation
# ---------------------------------------------------------------------------
TEST_QUESTIONS: List[Dict[str, str]] = [
    # ===== entity_relation (7) Q1-Q7 =====
    {"question": "Neo4j와 Elasticsearch의 역할 차이점은?", "type": "entity_relation",
     "ground_truth": "Neo4j는 Knowledge Graph 저장소로 엔티티 간 관계를 관리하고, Elasticsearch는 벡터 검색(kNN)과 BM25 키워드 검색을 담당합니다."},
    {"question": "LangGraph와 LangChain 중 어떤 것을 사용해야 하나요?", "type": "entity_relation",
     "ground_truth": "LangGraph는 상태 기반 에이전트 워크플로우에 적합하고, LangChain은 단순 체인 기반 RAG 파이프라인에 적합합니다."},
    {"question": "FastAPI와 PostgreSQL을 연동하여 RAGAS 평가를 수행하려면?", "type": "entity_relation",
     "ground_truth": "FastAPI에서 asyncpg로 PostgreSQL에 연결하고, RAGAS 라이브러리를 통해 Faithfulness 등 메트릭을 측정합니다."},
    {"question": "PostgreSQL과 Neo4j의 데이터 모델 차이는?", "type": "entity_relation",
     "ground_truth": "PostgreSQL은 관계형 SSOT 저장소이고, Neo4j는 그래프 데이터베이스로 엔티티 간 관계를 노드-엣지로 표현합니다."},
    {"question": "Spring Cloud Gateway와 FastAPI의 역할 분담은?", "type": "entity_relation",
     "ground_truth": "Spring Cloud Gateway는 API Gateway로 라우팅/인증을 담당하고, FastAPI는 AI Service 백엔드로 RAG 파이프라인을 실행합니다."},
    {"question": "BGE-M3와 BGE-Reranker의 역할 차이는?", "type": "entity_relation",
     "ground_truth": "BGE-M3는 Bi-encoder로 문서/쿼리를 벡터로 변환하고, BGE-Reranker는 Cross-encoder로 검색 결과의 순위를 재조정합니다."},
    {"question": "DeepSeek V3와 OpenAI GPT의 비용 및 성능 차이는?", "type": "entity_relation",
     "ground_truth": "DeepSeek V3는 OpenAI GPT 대비 95% 비용 절감이 가능하며, 한국어 RAG 파이프라인에서 충분한 성능을 제공합니다."},

    # ===== multi_hop (7) Q8-Q14 =====
    {"question": "RAG Pipeline에서 BGE-M3 임베딩 모델의 역할은?", "type": "multi_hop",
     "ground_truth": "BGE-M3는 RAG Pipeline에서 문서와 쿼리를 1024차원 벡터로 변환하여 시맨틱 검색을 가능하게 합니다."},
    {"question": "Knowledge Graph 엔티티 추출이 RAG 검색 품질에 기여하는 방식은?", "type": "multi_hop",
     "ground_truth": "엔티티 추출로 문서 간 관계를 Knowledge Graph에 저장하고, Graph Search 채널로 관계 기반 검색을 제공합니다."},
    {"question": "Agentic AI 에이전트 워크플로우 설계 패턴은 무엇인가요?", "type": "multi_hop",
     "ground_truth": "Agentic AI 워크플로우는 Planner-Retriever-Generator 패턴을 따르며 LangGraph로 상태 기반 그래프를 구현합니다."},
    {"question": "LangGraph에서 상태(State) 관리와 노드 간 데이터 전달 방식은?", "type": "multi_hop",
     "ground_truth": "LangGraph는 TypedDict 기반 State를 정의하고, 노드 함수가 State를 받아 수정 후 반환하는 방식으로 데이터를 전달합니다."},
    {"question": "ETL 파이프라인에서 문서 파싱부터 임베딩 저장까지의 전체 흐름은?", "type": "multi_hop",
     "ground_truth": "문서를 Docling으로 파싱하고, 시맨틱 청커로 분할한 후, BGE-M3로 벡터화하여 Elasticsearch에 색인합니다."},
    {"question": "Hybrid Search에서 RRF 퓨전이 단일 검색보다 나은 이유는?", "type": "multi_hop",
     "ground_truth": "RRF는 Vector, BM25, Graph 등 서로 다른 검색 채널의 순위를 융합하여 단일 채널의 약점을 보완합니다."},
    {"question": "AI 에이전트에서 Tool Calling과 Reasoning의 상호작용은?", "type": "multi_hop",
     "ground_truth": "AI 에이전트는 Reasoning으로 문제를 분석한 후 적절한 Tool을 선택하여 호출하고 결과를 다시 Reasoning에 반영합니다."},

    # ===== keyword (7) Q15-Q21 =====
    {"question": "Docker Compose에서 컨테이너 간 네트워크 통신 설정 방법은?", "type": "keyword",
     "ground_truth": "docker-compose.yml에서 networks를 정의하고 서비스마다 네트워크를 지정하면 컨테이너 간 호스트명으로 통신합니다."},
    {"question": "RRF 알고리즘이 Hybrid 검색에서 하는 역할은?", "type": "keyword",
     "ground_truth": "RRF(Reciprocal Rank Fusion)는 Vector, BM25, Graph 검색 결과의 순위를 융합하여 최종 순위를 결정합니다."},
    {"question": "RAGAS 평가 메트릭의 종류와 의미는?", "type": "keyword",
     "ground_truth": "Faithfulness(충실도), Answer Relevancy(답변 관련성), Context Precision(맥락 정밀도), Context Recall(맥락 재현율) 4가지입니다."},
    {"question": "JWT 인증 토큰의 장점과 단점은 무엇인가요?", "type": "keyword",
     "ground_truth": "JWT는 서버 상태 비저장(stateless) 인증이 가능하지만, 토큰 만료 전 무효화가 어렵고 크기가 큰 단점이 있습니다."},
    {"question": "Kubernetes에서 Spring Boot 마이크로서비스를 배포하는 방법은?", "type": "keyword",
     "ground_truth": "Spring Boot 앱을 Docker 이미지로 빌드한 후 Kubernetes Deployment와 Service를 생성하여 배포합니다."},
    {"question": "Elasticsearch 벡터 검색을 위한 인덱스 설정 방법은?", "type": "keyword",
     "ground_truth": "dense_vector 타입 필드를 정의하고 dims, similarity, knn 옵션을 설정하여 벡터 검색 인덱스를 생성합니다."},
    {"question": "WBS(Work Breakdown Structure)란 무엇이며 프로젝트 관리에서 어떻게 활용하나요?", "type": "keyword",
     "ground_truth": "WBS는 프로젝트를 작은 작업 단위로 분해하여 체계적으로 관리하는 구조로, 범위 정의와 일정 관리에 활용됩니다."},

    # ===== semantic (7) Q22-Q28 =====
    {"question": "대규모 문서를 효율적으로 처리하는 방법은?", "type": "semantic",
     "ground_truth": "청킹(chunking)으로 문서를 분할하고 배치 임베딩으로 벡터화한 후 Elasticsearch에 색인합니다."},
    {"question": "검색 성능을 최적화하려면 어떻게 해야 하나요?", "type": "semantic",
     "ground_truth": "Hybrid 검색(BM25+Dense+Graph), RRF 퓨전, Redis 캐싱, 배치 임베딩으로 성능을 최적화합니다."},
    {"question": "환경변수를 안전하게 관리하는 방법은?", "type": "semantic",
     "ground_truth": ".env 파일에 환경변수를 정의하고 docker-compose에서 env_file로 로드하며, 시크릿은 별도 관리합니다."},
    {"question": "답변 품질을 체계적으로 평가하는 방법론은 무엇인가요?", "type": "semantic",
     "ground_truth": "RAGAS 프레임워크로 Faithfulness, Answer Relevancy, Context Precision, Context Recall을 측정하여 체계적으로 평가합니다."},
    {"question": "반복적이고 점진적인 개발 방법론은 어떤 것이 있나요?", "type": "semantic",
     "ground_truth": "Agile/Scrum 방법론으로 Sprint 단위 반복 개발, 데일리 스크럼, 스프린트 리뷰를 통해 점진적으로 발전시킵니다."},
    {"question": "데이터베이스 마이그레이션을 안전하게 수행하는 방법은?", "type": "semantic",
     "ground_truth": "Flyway/Alembic 등 마이그레이션 도구를 사용하여 스키마 변경을 버전 관리하고 롤백 가능하게 합니다."},
    {"question": "마이크로서비스 아키텍처에서 서비스 간 통신 패턴은?", "type": "semantic",
     "ground_truth": "동기 방식(REST, gRPC)과 비동기 방식(이벤트 기반 메시징)이 있으며, API Gateway로 진입점을 통합합니다."},

    # ===== graph_entity (8) Q29-Q36 =====
    {"question": "Spring Cloud Gateway에서 API 라우팅과 필터를 설정하는 방법은?", "type": "graph_entity",
     "ground_truth": "Spring Cloud Gateway에서 RouteLocator로 라우팅 규칙을 정의하고, GlobalFilter로 인증/로깅 등 필터를 적용합니다."},
    {"question": "Gleaning 기법이란 무엇이며 RAG 파이프라인에서 어떻게 활용되나요?", "type": "graph_entity",
     "ground_truth": "Gleaning은 LLM이 추출한 엔티티를 반복 검증하여 Knowledge Graph의 품질을 높이는 기법입니다."},
    {"question": "cosine similarity와 dot product 유사도의 차이와 적합한 사용 시나리오는?", "type": "graph_entity",
     "ground_truth": "cosine similarity는 방향만 비교하여 정규화된 벡터에 적합하고, dot product는 크기도 반영하여 비정규화 벡터에 적합합니다."},
    {"question": "SSOT 원칙이란 무엇이며 데이터 아키텍처에서 왜 중요한가요?", "type": "graph_entity",
     "ground_truth": "SSOT(Single Source of Truth)는 데이터의 단일 원본을 유지하는 원칙으로, PostgreSQL이 SSOT 역할을 합니다."},
    {"question": "Vector Search와 Graph Search를 결합하면 어떤 이점이 있나요?", "type": "graph_entity",
     "ground_truth": "Vector Search는 의미 유사성 기반 검색을, Graph Search는 엔티티 관계 기반 검색을 제공하여 상호 보완합니다."},
    {"question": "React 18에서 Concurrent 렌더링과 Suspense를 활용하는 방법은?", "type": "graph_entity",
     "ground_truth": "React 18의 Concurrent 렌더링은 UI 응답성을 높이고, Suspense는 비동기 데이터 로딩을 선언적으로 처리합니다."},
    {"question": "Python 3.11의 ExceptionGroup과 except* 구문의 사용 방법은?", "type": "graph_entity",
     "ground_truth": "ExceptionGroup은 여러 예외를 하나로 묶고, except*로 특정 예외 유형만 선택적으로 처리합니다."},
    {"question": "AI Service에서 RAG Pipeline의 전체 처리 흐름은?", "type": "graph_entity",
     "ground_truth": "쿼리 입력 → Hybrid 검색(BM25+Dense+Sparse+Graph) → RRF 퓨전 → Quality Gate → LLM 생성 순서입니다."},

    # ===== legal (7) Q37-Q43 =====
    {"question": "개인정보보호법에서 개인정보 수집 시 동의 요건은?", "type": "legal",
     "ground_truth": "개인정보보호법에 따라 정보주체의 동의를 받아야 하며, 수집 목적, 항목, 보유 기간을 명시해야 합니다."},
    {"question": "GDPR의 핵심 원칙과 국내 기업의 준수 사항은?", "type": "legal",
     "ground_truth": "GDPR은 데이터 최소 수집, 목적 제한, 정보주체 권리 보장 등을 요구하며, EU 시민 데이터 처리 시 준수해야 합니다."},
    {"question": "민법에서 계약의 성립 요건은 무엇인가요?", "type": "legal",
     "ground_truth": "계약은 당사자 간 청약과 승낙의 합치로 성립하며, 의사표시의 합치가 핵심 요건입니다."},
    {"question": "SLA(서비스 수준 협약)에서 반드시 포함해야 할 핵심 항목은?", "type": "legal",
     "ground_truth": "가용성(Uptime), 응답 시간, 장애 대응 시간, 보상 조건, 측정 방법 등이 SLA 핵심 항목입니다."},
    {"question": "ISMS 인증을 위한 정보보안 점검 항목은?", "type": "legal",
     "ground_truth": "관리체계 수립, 보호대책 구현, 접근 통제, 침해사고 대응, 개인정보 보호 등을 점검합니다."},
    {"question": "소프트웨어 라이선스 종류(MIT, GPL, Apache)의 차이는?", "type": "legal",
     "ground_truth": "MIT는 최소 제약, GPL은 파생물도 GPL 적용 의무, Apache는 특허권 명시 허가가 특징입니다."},
    {"question": "법령 용어에서 '선의'와 '악의'의 법률적 의미 차이는?", "type": "legal",
     "ground_truth": "법률에서 선의는 어떤 사실을 모르는 상태, 악의는 어떤 사실을 알고 있는 상태를 의미합니다."},

    # ===== factual (8) Q44-Q51 =====
    {"question": "RAG(Retrieval-Augmented Generation) 시스템의 동작 원리는?", "type": "factual",
     "ground_truth": "RAG는 질문에 관련된 문서를 검색(Retrieval)한 후 LLM이 검색된 컨텍스트를 참고하여 답변을 생성(Generation)합니다."},
    {"question": "Transformer 아키텍처의 Self-Attention 메커니즘은?", "type": "factual",
     "ground_truth": "Self-Attention은 입력 시퀀스의 각 토큰이 다른 모든 토큰과의 관련도를 계산하여 문맥 정보를 인코딩합니다."},
    {"question": "Reranking이 RAG 검색 품질을 향상시키는 원리는?", "type": "factual",
     "ground_truth": "Reranking은 Cross-encoder로 쿼리와 문서 쌍의 관련성을 정밀 평가하여 초기 검색 결과의 순위를 재조정합니다."},
    {"question": "HNSW와 IVF 벡터 인덱스 알고리즘의 비교는?", "type": "factual",
     "ground_truth": "HNSW는 그래프 기반으로 높은 검색 정확도를 제공하고, IVF는 클러스터 기반으로 메모리 효율이 좋습니다."},
    {"question": "Chain of Thought 추론이 LLM 성능에 미치는 영향은?", "type": "factual",
     "ground_truth": "Chain of Thought는 LLM이 단계별로 추론하도록 유도하여 복잡한 문제 해결 능력을 향상시킵니다."},
    {"question": "벡터 임베딩의 차원 수가 검색 정확도에 미치는 영향은?", "type": "factual",
     "ground_truth": "차원이 높을수록 의미 표현력이 증가하나 계산 비용도 증가하며, 1024차원이 성능과 효율의 균형점입니다."},
    {"question": "비즈니스에 실제 활용 가능한 LLM 서비스를 만들기 위한 핵심 고려사항은?", "type": "factual",
     "ground_truth": "프롬프트 설계, RAG 파이프라인, 평가 체계, 비용 최적화, 할루시네이션 방지가 핵심 고려사항입니다."},
    {"question": "프롬프트 엔지니어링의 핵심 원칙과 효과적인 기법은?", "type": "factual",
     "ground_truth": "명확한 지시, 예시 제공(few-shot), 역할 부여, 단계별 사고 유도가 핵심 기법입니다."},
]


# ---------------------------------------------------------------------------
# HRKP Client (JWT auto refresh)
# ---------------------------------------------------------------------------
class HRKPClient:
    def __init__(self, base_url: str = BASE_URL, timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.token = None
        self.session = requests.Session()
        self._query_count = 0

    def login(self) -> bool:
        resp = self.session.post(
            f"{self.base_url}/auth/login",
            json={"email": LOGIN_EMAIL, "password": LOGIN_PASSWORD},
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            self.token = data.get("accessToken") or data.get("access_token") or data.get("token")
            self.session.headers["Authorization"] = f"Bearer {self.token}"
            self._query_count = 0
            return True
        print(f"  [ERROR] Login failed: {resp.status_code} {resp.text[:200]}")
        return False

    def _maybe_refresh(self):
        self._query_count += 1
        if self._query_count >= TOKEN_REFRESH_INTERVAL:
            print(f"    [JWT refresh] {self._query_count} queries, re-login...")
            self.login()

    def hybrid_search(self, query: str, top_k: int = 10,
                      use_graph: bool = True, use_vector: bool = True) -> Dict:
        self._maybe_refresh()
        resp = self.session.post(
            f"{self.base_url}/search/hybrid",
            json={"query": query, "top_k": top_k,
                  "useGraph": use_graph, "useVector": use_vector},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# DeepSeek LLM Answer Generation
# ---------------------------------------------------------------------------
def generate_answer(question: str, contexts: List[str]) -> str:
    context_text = "\n\n---\n\n".join(contexts[:5])

    prompt = f"""다음 컨텍스트를 참고하여 질문에 답변하세요.
컨텍스트에 없는 정보는 사용하지 마세요. 컨텍스트에 정보가 부족하면 그 사실을 명시하세요.

## 컨텍스트
{context_text}

## 질문
{question}

## 답변
간결하고 정확하게 한국어로 답변하세요."""

    try:
        resp = requests.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                     "Content-Type": "application/json"},
            json={"model": DEEPSEEK_MODEL,
                  "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0.1, "max_tokens": 500},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"[답변 생성 실패: {e}]"


# ---------------------------------------------------------------------------
# LLM-as-Judge Evaluation
# ---------------------------------------------------------------------------
def judge_metric(metric: str, question: str, answer: str,
                 contexts: List[str], ground_truth: str) -> float:
    """DeepSeek LLM으로 단일 메트릭 평가"""
    context_text = "\n".join(f"[Context {i+1}] {c[:500]}" for i, c in enumerate(contexts[:5]))

    prompts = {
        "faithfulness": f"""아래 답변이 주어진 컨텍스트에만 기반하여 작성되었는지 평가하세요.
컨텍스트에 없는 정보를 사용했다면 낮은 점수를 주세요.

컨텍스트:
{context_text}

질문: {question}
답변: {answer}

0.0~1.0 사이 점수만 숫자로 답하세요.""",

        "answer_relevancy": f"""아래 답변이 질문에 얼마나 적절하게 답하고 있는지 평가하세요.
질문의 핵심을 정확히 다루면 높은 점수, 관련 없는 내용이 많으면 낮은 점수를 주세요.

질문: {question}
답변: {answer}

0.0~1.0 사이 점수만 숫자로 답하세요.""",

        "context_precision": f"""검색된 컨텍스트 중 질문에 실제로 관련된 내용의 비율을 평가하세요.
모든 컨텍스트가 관련 있으면 1.0, 관련 없는 것이 많으면 낮은 점수를 주세요.

질문: {question}
컨텍스트:
{context_text}

0.0~1.0 사이 점수만 숫자로 답하세요.""",

        "context_recall": f"""정답에 필요한 정보가 검색된 컨텍스트에 포함되어 있는지 평가하세요.
정답의 핵심 정보가 모두 컨텍스트에 있으면 1.0, 핵심 정보가 누락되면 낮은 점수를 주세요.

질문: {question}
정답 (Ground Truth): {ground_truth}
검색된 컨텍스트:
{context_text}

0.0~1.0 사이 점수만 숫자로 답하세요.""",
    }

    try:
        resp = requests.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                     "Content-Type": "application/json"},
            json={"model": DEEPSEEK_MODEL,
                  "messages": [{"role": "user", "content": prompts[metric]}],
                  "temperature": 0.0, "max_tokens": 10},
            timeout=30,
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"].strip()
        # Extract float
        for token in text.replace(",", ".").split():
            try:
                val = float(token)
                if 0.0 <= val <= 1.0:
                    return val
            except ValueError:
                continue
        return 0.0
    except Exception as e:
        print(f"    [WARN] Judge failed for {metric}: {e}")
        return 0.0


def evaluate_sample(question: str, answer: str, contexts: List[str],
                    ground_truth: str) -> Dict[str, float]:
    """4개 RAGAS 메트릭 평가"""
    scores = {}
    for metric in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
        scores[metric] = judge_metric(metric, question, answer, contexts, ground_truth)
    return scores


# ---------------------------------------------------------------------------
# Quality Gate
# ---------------------------------------------------------------------------
def quality_grade(scores: Dict[str, float]) -> str:
    avg = sum(scores.values()) / len(scores)
    if avg >= 0.70:
        return "HIGH"
    elif avg >= 0.40:
        return "PARTIAL"
    else:
        return "NONE"


# ---------------------------------------------------------------------------
# Main Evaluation
# ---------------------------------------------------------------------------
def run_evaluation():
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*60}")
    print(f"  RAGAS v9 Comprehensive Evaluation")
    print(f"  {ts}")
    print(f"{'='*60}")
    print(f"  Questions: {len(TEST_QUESTIONS)}")
    print(f"  Domains: {len(set(q['type'] for q in TEST_QUESTIONS))}")
    print(f"  Baseline: v8 (2-channel Hybrid, 108K chunks)")
    print(f"  Current:  v9 (4-Way RRF, 56K chunks, Graph RAG)")
    print(f"{'='*60}\n")

    # 1. Login
    print("[Phase 1] Login...")
    client = HRKPClient()
    if not client.login():
        print("  FATAL: Login failed!")
        sys.exit(1)
    print("  OK\n")

    # 2. Search + Answer Generation
    print(f"[Phase 2] Search + Answer Generation ({len(TEST_QUESTIONS)} queries)...")
    results = []
    total_latency = 0

    for idx, q in enumerate(TEST_QUESTIONS):
        qtype = q["type"]
        question = q["question"]
        ground_truth = q["ground_truth"]

        print(f"  Q{idx+1:02d}/{len(TEST_QUESTIONS)} [{qtype:18s}] {question[:50]}...", end=" ", flush=True)

        t0 = time.time()

        # Search
        try:
            search_result = client.hybrid_search(question, top_k=10)
            search_items = search_result.get("results", [])
            contexts = [item.get("content", "") for item in search_items if item.get("content")]
            contributing = [
                item.get("contributing_sources", []) or []
                for item in search_items
            ]
            latency = search_result.get("latency_ms", 0)
        except Exception as e:
            print(f"SEARCH_FAIL: {e}")
            contexts = []
            contributing = []
            latency = 0

        # Generate answer
        if contexts:
            answer = generate_answer(question, contexts)
        else:
            answer = "[검색 결과 없음 - 답변 생성 불가]"

        elapsed = time.time() - t0
        total_latency += elapsed

        # Count graph contributions
        graph_hits = sum(1 for cs in contributing if "graph" in cs)

        results.append({
            "idx": idx + 1,
            "question": question,
            "type": qtype,
            "ground_truth": ground_truth,
            "answer": answer,
            "contexts": contexts[:5],
            "context_count": len(contexts),
            "graph_hits": graph_hits,
            "search_latency_ms": latency,
            "elapsed_s": round(elapsed, 2),
        })

        print(f"OK ({elapsed:.1f}s, {len(contexts)} ctx, {graph_hits} graph)")

    print(f"\n  Total search+generation: {total_latency:.1f}s\n")

    # 3. RAGAS Evaluation (LLM-as-Judge)
    print(f"[Phase 3] RAGAS Evaluation (LLM-as-Judge, {len(results)} samples)...")
    eval_start = time.time()

    for idx, r in enumerate(results):
        print(f"  E{idx+1:02d}/{len(results)} [{r['type']:18s}]", end=" ", flush=True)

        scores = evaluate_sample(
            question=r["question"],
            answer=r["answer"],
            contexts=r["contexts"],
            ground_truth=r["ground_truth"],
        )
        r["scores"] = scores
        r["grade"] = quality_grade(scores)

        f, rel, p, rec = scores["faithfulness"], scores["answer_relevancy"], \
                         scores["context_precision"], scores["context_recall"]
        print(f"F={f:.2f} R={rel:.2f} P={p:.2f} C={rec:.2f} [{r['grade']}]")

    eval_elapsed = time.time() - eval_start
    print(f"\n  Total evaluation: {eval_elapsed:.1f}s\n")

    # 4. Aggregate Results
    print("[Phase 4] Aggregating results...")

    metrics = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    avg_scores = {}
    for m in metrics:
        vals = [r["scores"][m] for r in results]
        avg_scores[m] = sum(vals) / len(vals)

    # Quality Gate
    grades = {"HIGH": 0, "PARTIAL": 0, "NONE": 0}
    for r in results:
        grades[r["grade"]] += 1

    # Domain breakdown
    domains = sorted(set(q["type"] for q in TEST_QUESTIONS))
    domain_scores = {}
    for d in domains:
        domain_results = [r for r in results if r["type"] == d]
        domain_scores[d] = {}
        for m in metrics:
            vals = [r["scores"][m] for r in domain_results]
            domain_scores[d][m] = sum(vals) / len(vals)
        domain_scores[d]["count"] = len(domain_results)
        domain_scores[d]["avg"] = sum(domain_scores[d][m] for m in metrics) / 4

    # Graph contribution
    total_graph_hits = sum(r["graph_hits"] for r in results)
    total_contexts = sum(r["context_count"] for r in results)

    # 5. Print Summary
    print(f"\n{'='*60}")
    print(f"  RAGAS v9 Results Summary")
    print(f"{'='*60}")

    print(f"\n  [Average Scores]")
    for m in metrics:
        v8 = V8_BASELINE[m]
        v9 = avg_scores[m]
        delta = v9 - v8
        sign = "+" if delta >= 0 else ""
        status = "PASS" if v9 >= 0.70 else "FAIL"
        print(f"    {m:22s}: {v9:.3f}  (v8: {v8:.3f}, {sign}{delta:.3f}) [{status}]")

    print(f"\n  [Quality Gate]")
    for g in ["HIGH", "PARTIAL", "NONE"]:
        v8g = V8_BASELINE["quality_gate"].get(g, 0)
        v9g = grades[g]
        pct = v9g / len(results) * 100
        print(f"    {g:8s}: {v9g}/{len(results)} ({pct:.1f}%)  (v8: {v8g})")

    print(f"\n  [Domain Breakdown]")
    print(f"    {'Domain':20s} {'Faith':>7s} {'Relev':>7s} {'Prec':>7s} {'Recall':>7s} {'Avg':>7s}")
    print(f"    {'-'*20} {'-'*7} {'-'*7} {'-'*7} {'-'*7} {'-'*7}")
    for d in domains:
        ds = domain_scores[d]
        print(f"    {d:20s} {ds['faithfulness']:7.3f} {ds['answer_relevancy']:7.3f} "
              f"{ds['context_precision']:7.3f} {ds['context_recall']:7.3f} {ds['avg']:7.3f}")

    print(f"\n  [Graph Contribution]")
    print(f"    Graph hits in top-10: {total_graph_hits}/{total_contexts} "
          f"({total_graph_hits/total_contexts*100:.1f}% of total contexts)")

    # 6. Save Results
    output = {
        "version": "v9_comprehensive",
        "timestamp": ts,
        "system": {
            "es_chunks": 56063,
            "neo4j_entities": 70855,
            "neo4j_relationships": 375229,
            "search_type": "4-Way RRF (Dense + BM25 + Sparse + Graph)",
            "rrf_weights": {"vector": 1.0, "keyword": 1.0, "sparse": 0.7, "graph": 0.8},
            "rrf_k": 60,
            "chunk_size": 1000,
            "chunk_overlap": 200,
        },
        "evaluation": {
            "method": "LLM-as-Judge (DeepSeek V3.2)",
            "question_count": len(TEST_QUESTIONS),
            "domain_count": len(domains),
            "search_time_s": round(total_latency, 1),
            "eval_time_s": round(eval_elapsed, 1),
        },
        "metrics": avg_scores,
        "quality_gate": grades,
        "domain_scores": domain_scores,
        "graph_contribution": {
            "total_graph_hits": total_graph_hits,
            "total_contexts": total_contexts,
            "graph_ratio": round(total_graph_hits / total_contexts * 100, 1),
        },
        "v8_baseline": V8_BASELINE,
        "v8_vs_v9": {
            m: {
                "v8": V8_BASELINE[m],
                "v9": round(avg_scores[m], 3),
                "delta": round(avg_scores[m] - V8_BASELINE[m], 3),
            }
            for m in metrics
        },
        "results": results,
    }

    # Save JSON
    json_path = "/tmp/ragas_v9_comprehensive_result.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n  JSON saved: {json_path}")

    # Save Markdown
    md_path = "/tmp/ragas_v9_comprehensive_report.md"
    _write_markdown_report(output, md_path)
    print(f"  Markdown saved: {md_path}")

    print(f"\n{'='*60}")
    print(f"  RAGAS v9 Evaluation Complete!")
    print(f"{'='*60}\n")

    return output


def _write_markdown_report(data: Dict, path: str):
    """Markdown 리포트 생성"""
    m = data["metrics"]
    v8v9 = data["v8_vs_v9"]
    qg = data["quality_gate"]
    ds = data["domain_scores"]
    gc = data["graph_contribution"]
    sys_info = data["system"]

    lines = [
        f"# RAGAS v9 종합 평가 결과 — 4-Way RRF + Graph RAG",
        f"",
        f"**Version**: v9 (ETL v2 재처리)",
        f"**Date**: {data['timestamp']}",
        f"**Author**: Claude Code (Opus 4.6)",
        f"**Status**: 완료",
        f"",
        f"---",
        f"",
        f"## 1. 평가 환경",
        f"",
        f"| 항목 | v8 (Baseline) | v9 (Current) |",
        f"|------|:---:|:---:|",
        f"| ES 청크 수 | 108,896 | **{sys_info['es_chunks']:,}** |",
        f"| 검색 방식 | Dense + BM25(Nori) + Manual RRF | **4-Way RRF** (Dense+BM25+Sparse+Graph) |",
        f"| Chunk Size | 600 | **{sys_info['chunk_size']}** |",
        f"| Chunk Overlap | 100 | **{sys_info['chunk_overlap']}** |",
        f"| Neo4j 엔티티 | - | **{sys_info['neo4j_entities']:,}** |",
        f"| Neo4j 관계 | - | **{sys_info['neo4j_relationships']:,}** |",
        f"| Sparse Vector | 없음 | **BGE-M3 Sparse** |",
        f"| Graph Search | 미통합 | **Entity-Enhanced BM25** |",
        f"| RRF 가중치 | Vector=1.0, Keyword=1.0 | V={sys_info['rrf_weights']['vector']}, K={sys_info['rrf_weights']['keyword']}, S={sys_info['rrf_weights']['sparse']}, G={sys_info['rrf_weights']['graph']} |",
        f"| 평가 방법 | LLM-as-Judge (DeepSeek) | LLM-as-Judge (DeepSeek) |",
        f"| 질문 수 | 51 (7 도메인) | 51 (7 도메인) |",
        f"",
        f"---",
        f"",
        f"## 2. 전체 평가 결과",
        f"",
        f"### 2.1 평균 점수 (v8 vs v9)",
        f"",
        f"| 메트릭 | v8 | **v9** | 변화 | 목표 | 달성 |",
        f"|--------|:---:|:---:|:---:|:---:|:---:|",
    ]

    for metric_key in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
        v = v8v9[metric_key]
        sign = "+" if v["delta"] >= 0 else ""
        target = 0.70
        status = "PASS" if v["v9"] >= target else "FAIL"
        lines.append(f"| {metric_key} | {v['v8']:.3f} | **{v['v9']:.3f}** | {sign}{v['delta']:.3f} | {target:.2f} | {status} |")

    lines += [
        f"",
        f"### 2.2 Quality Gate",
        f"",
        f"| 등급 | v8 | v9 | 비율 |",
        f"|:---:|:---:|:---:|:---:|",
        f"| HIGH (avg >= 0.70) | {data['v8_baseline']['quality_gate']['HIGH']} | **{qg['HIGH']}** | {qg['HIGH']/51*100:.1f}% |",
        f"| PARTIAL (0.40-0.69) | {data['v8_baseline']['quality_gate']['PARTIAL']} | **{qg['PARTIAL']}** | {qg['PARTIAL']/51*100:.1f}% |",
        f"| NONE (< 0.40) | {data['v8_baseline']['quality_gate']['NONE']} | **{qg['NONE']}** | {qg['NONE']/51*100:.1f}% |",
        f"",
        f"---",
        f"",
        f"## 3. 도메인별 상세 분석",
        f"",
        f"| 도메인 | Faith | Relev | Prec | Recall | 종합 |",
        f"|--------|:---:|:---:|:---:|:---:|:---:|",
    ]

    for d_name in sorted(ds.keys()):
        d = ds[d_name]
        lines.append(f"| {d_name} | {d['faithfulness']:.3f} | {d['answer_relevancy']:.3f} | "
                     f"{d['context_precision']:.3f} | {d['context_recall']:.3f} | {d['avg']:.3f} |")

    lines += [
        f"",
        f"---",
        f"",
        f"## 4. Graph RAG 기여도",
        f"",
        f"| 항목 | 값 |",
        f"|------|-----|",
        f"| Graph 기여 검색 결과 | {gc['total_graph_hits']}/{gc['total_contexts']} ({gc['graph_ratio']}%) |",
        f"| 엔티티 수 | {sys_info['neo4j_entities']:,} |",
        f"| 관계 수 | {sys_info['neo4j_relationships']:,} |",
        f"",
        f"---",
        f"",
        f"## 5. 개별 질문 결과",
        f"",
        f"| # | 질문 | 도메인 | Faith | Relev | Prec | Recall | 등급 | Graph |",
        f"|:---:|------|--------|:---:|:---:|:---:|:---:|:---:|:---:|",
    ]

    for r in data["results"]:
        s = r["scores"]
        lines.append(
            f"| Q{r['idx']:02d} | {r['question'][:40]}... | {r['type']} | "
            f"{s['faithfulness']:.2f} | {s['answer_relevancy']:.2f} | "
            f"{s['context_precision']:.2f} | {s['context_recall']:.2f} | "
            f"{r['grade']} | {r['graph_hits']} |"
        )

    lines += [
        f"",
        f"---",
        f"",
        f"## 6. 결론",
        f"",
        f"### 시스템 변경 사항",
        f"- ETL v2 재처리: chunk_size 600→1000, overlap 100→200",
        f"- 4-Way RRF: Dense + BM25 + Sparse + Graph 채널 통합",
        f"- Entity Extraction: 70,855 엔티티, 375,229 관계 구축",
        f"- Entity-Enhanced BM25: Graph 채널에서 엔티티 기반 검색어 확장",
        f"",
        f"### 소요 시간",
        f"- 검색 + 답변 생성: {data['evaluation']['search_time_s']}초",
        f"- RAGAS 평가: {data['evaluation']['eval_time_s']}초",
        f"",
        f"---",
        f"",
        f"*기록: {data['timestamp']}*",
        f"*평가 스크립트: scripts/ragas_v9_comprehensive_eval.py*",
    ]

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    run_evaluation()
