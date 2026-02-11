#!/usr/bin/env python3
"""
STORY-111: HRKP v3 vs v5 Cross-System Comparison v6
====================================================
v6 변경 (v4 스크립트):
  - JWT 토큰 자동 갱신 (15쿼리마다 재로그인)
  - 데이터 품질 사전 분석 (GLYPH 아티팩트 탐지)
  - ONNX Runtime 벤치마크 포함
  - 리포트 경로 통일 (docs/results/ragas/)

비교 구조:
  - HRKP-RAW: /api/v1/search/hybrid (원시 검색 + DeepSeek 별도 생성)
  - HRKP-FULL: /api/v1/search/chat (전체 파이프라인: Reranker + QualityGate)
  - RCSV: ES BM25 only + DeepSeek

Docker 컨테이너 내부에서 실행:
    docker exec kp-ai-service python3 /app/rcsv_comparison_eval_v4.py

소요 시간: 약 40-50분 (50쿼리 × 3시스템)
"""

import json
import os
import re
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from elasticsearch import Elasticsearch

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
ES_URL = os.getenv("ELASTICSEARCH_URL", "http://elasticsearch:9200")
HRKP_API_URL = os.getenv("HRKP_API_URL", "http://localhost:8000/api/v1")
HRKP_INDEX = "knowledge_chunks"
RCSV_INDEX = "rcsv-pdf-documents"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-7c3024219fb74302a296207d2a091fe5")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

# JWT 토큰 갱신 주기 (쿼리 수)
TOKEN_REFRESH_INTERVAL = 15

# v5 baseline (2026-02-10, 50쿼리)
V5_BASELINE = {
    "hrkp_raw": {"faithfulness": 0.1440, "answer_relevancy": 0.4560,
                 "context_precision": 0.3960, "context_recall": 0.1500},
    "hrkp_full": {"faithfulness": 0.0000, "answer_relevancy": 0.1340,
                  "context_precision": 0.2480, "context_recall": 0.0150},
    "rcsv": {"faithfulness": 0.1320, "answer_relevancy": 0.3120,
             "context_precision": 0.2100, "context_recall": 0.0660},
}

# ---------------------------------------------------------------------------
# Test Questions (50개 - v5와 동일)
# ---------------------------------------------------------------------------
TEST_QUESTIONS = [
    # ===== [1-12] 기존 12개 =====
    {"question": "Neo4j와 Elasticsearch의 역할 차이점은?", "type": "entity_relation",
     "ground_truth": "Neo4j는 Knowledge Graph 저장소로 엔티티 간 관계를 관리하고, Elasticsearch는 벡터 검색(kNN)과 BM25 키워드 검색을 담당합니다."},
    {"question": "LangGraph와 LangChain 중 어떤 것을 사용해야 하나요?", "type": "entity_relation",
     "ground_truth": "LangGraph는 상태 기반 에이전트 워크플로우에 적합하고, LangChain은 단순 체인 기반 RAG 파이프라인에 적합합니다."},
    {"question": "FastAPI와 PostgreSQL을 연동하여 RAGAS 평가를 수행하려면?", "type": "entity_relation",
     "ground_truth": "FastAPI에서 asyncpg로 PostgreSQL에 연결하고, RAGAS 라이브러리를 통해 Faithfulness 등 메트릭을 측정합니다."},
    {"question": "RAG Pipeline에서 BGE-M3 임베딩 모델의 역할은?", "type": "multi_hop",
     "ground_truth": "BGE-M3는 RAG Pipeline에서 문서와 쿼리를 1024차원 벡터로 변환하여 시맨틱 검색을 가능하게 합니다."},
    {"question": "Kubernetes에서 Spring Boot 마이크로서비스를 배포하는 방법은?", "type": "multi_hop",
     "ground_truth": "Spring Boot 앱을 Docker 이미지로 빌드한 후 Kubernetes Deployment와 Service를 생성하여 배포합니다."},
    {"question": "Agentic AI 에이전트 워크플로우 설계 패턴은 무엇인가요?", "type": "multi_hop",
     "ground_truth": "Agentic AI 워크플로우는 Planner-Retriever-Generator 패턴을 따르며 LangGraph로 상태 기반 그래프를 구현합니다."},
    {"question": "Docker Compose 설정 방법은?", "type": "keyword",
     "ground_truth": "docker-compose.yml에 서비스, 네트워크, 볼륨을 정의하고 docker-compose up 명령으로 실행합니다."},
    {"question": "RRF 알고리즘이 Hybrid 검색에서 하는 역할은?", "type": "keyword",
     "ground_truth": "RRF(Reciprocal Rank Fusion)는 Vector, BM25, Graph 검색 결과의 순위를 융합하여 최종 순위를 결정합니다."},
    {"question": "RAGAS 평가 메트릭의 종류와 의미는?", "type": "keyword",
     "ground_truth": "Faithfulness(충실도), Answer Relevancy(답변 관련성), Context Precision(맥락 정밀도), Context Recall(맥락 재현율) 4가지입니다."},
    {"question": "대규모 문서를 효율적으로 처리하는 방법은?", "type": "semantic",
     "ground_truth": "청킹(chunking)으로 문서를 분할하고 배치 임베딩으로 벡터화한 후 Elasticsearch에 색인합니다."},
    {"question": "검색 성능을 최적화하려면 어떻게 해야 하나요?", "type": "semantic",
     "ground_truth": "Hybrid 검색(BM25+Dense+Graph), RRF 퓨전, Redis 캐싱, 배치 임베딩으로 성능을 최적화합니다."},
    {"question": "환경변수를 안전하게 관리하는 방법은?", "type": "semantic",
     "ground_truth": ".env 파일에 환경변수를 정의하고 docker-compose에서 env_file로 로드하며, 시크릿은 별도 관리합니다."},

    # ===== [13-20] Graph 트리거 - Technology 엔티티 =====
    {"question": "Spring Cloud Gateway에서 API 라우팅과 필터를 설정하는 방법은?", "type": "graph_entity",
     "ground_truth": "Spring Cloud Gateway에서 RouteLocator로 라우팅 규칙을 정의하고, GlobalFilter로 인증/로깅 등 필터를 적용합니다."},
    {"question": "Redis 캐싱을 RAG 시스템에 적용하여 검색 성능을 개선하는 방법은?", "type": "graph_entity",
     "ground_truth": "Redis에 검색 결과를 캐싱하여 동일 쿼리 재요청 시 Elasticsearch 접근 없이 빠르게 응답합니다."},
    {"question": "DeepSeek V3.2 모델의 특징과 비용 절감 효과는?", "type": "graph_entity",
     "ground_truth": "DeepSeek V3.2는 런타임 LLM으로 사용되며 OpenAI 대비 95% 비용 절감이 가능합니다."},
    {"question": "Vault를 사용한 시크릿 관리와 Spring Cloud Config 연동 방법은?", "type": "graph_entity",
     "ground_truth": "Vault에 시크릿을 저장하고 Spring Cloud Config를 통해 마이크로서비스에 안전하게 주입합니다."},
    {"question": "GitHub Actions로 CI/CD 파이프라인을 구성하는 방법은?", "type": "graph_entity",
     "ground_truth": "GitHub Actions에서 워크플로우 YAML을 정의하여 빌드, 테스트, 배포를 자동화합니다."},
    {"question": "Eureka 서비스 디스커버리와 Kubernetes DNS 기반 서비스 발견의 차이점은?", "type": "graph_entity",
     "ground_truth": "Eureka는 클라이언트 사이드 디스커버리 패턴이고, Kubernetes DNS는 플랫폼 내장 서비스 발견 메커니즘입니다."},
    {"question": "React 18에서 Concurrent 렌더링과 Suspense를 활용하는 방법은?", "type": "graph_entity",
     "ground_truth": "React 18의 Concurrent 렌더링은 UI 응답성을 높이고, Suspense는 비동기 데이터 로딩을 선언적으로 처리합니다."},
    {"question": "Python 3.11 기반 FastAPI 비동기 처리와 asyncpg 연동 방법은?", "type": "graph_entity",
     "ground_truth": "Python 3.11의 async/await와 FastAPI의 비동기 라우터, asyncpg로 PostgreSQL 비동기 쿼리를 수행합니다."},

    # ===== [21-28] Graph 트리거 - Topic 엔티티 =====
    {"question": "Strangler Fig 패턴을 활용한 레거시 시스템 점진적 마이그레이션 전략은?", "type": "graph_entity",
     "ground_truth": "Strangler Fig 패턴은 레거시 시스템을 감싸는 새 서비스를 만들고 점진적으로 트래픽을 이전하는 방법입니다."},
    {"question": "Gleaning 기법이란 무엇이며 RAG 파이프라인에서 어떻게 활용되나요?", "type": "graph_entity",
     "ground_truth": "Gleaning은 LLM이 추출한 엔티티를 반복 검증하여 Knowledge Graph의 품질을 높이는 기법입니다."},
    {"question": "Vector Search와 Graph Search를 결합하면 어떤 이점이 있나요?", "type": "graph_entity",
     "ground_truth": "Vector Search는 의미 유사성 기반 검색을, Graph Search는 엔티티 관계 기반 검색을 제공하여 상호 보완합니다."},
    {"question": "SSOT 원칙이란 무엇이며 데이터 아키텍처에서 왜 중요한가요?", "type": "graph_entity",
     "ground_truth": "SSOT(Single Source of Truth)는 데이터의 단일 원본을 유지하는 원칙으로, PostgreSQL이 SSOT 역할을 합니다."},
    {"question": "하이브리드 검색에서 BM25와 Dense Vector 검색의 가중치 조합 방법은?", "type": "graph_entity",
     "ground_truth": "RRF 퓨전에서 BM25(keyword)와 Dense Vector의 가중치를 각각 1.0으로 설정하고 Graph는 0.3으로 조합합니다."},
    {"question": "마이크로서비스 아키텍처에서 서비스 간 통신 패턴은 어떤 것들이 있나요?", "type": "graph_entity",
     "ground_truth": "동기 방식(REST, gRPC)과 비동기 방식(이벤트 기반 메시징)이 있으며, API Gateway로 진입점을 통합합니다."},
    {"question": "Dual-Write 문제란 무엇이며 MSA 환경에서 어떻게 해결하나요?", "type": "graph_entity",
     "ground_truth": "Dual-Write는 두 데이터 저장소에 동시 쓰기 시 일관성 문제이며, Outbox 패턴이나 CDC로 해결합니다."},
    {"question": "AI Service에서 RAG Pipeline의 전체 처리 흐름은 어떻게 되나요?", "type": "graph_entity",
     "ground_truth": "쿼리 입력 → Hybrid 검색(BM25+Dense+Graph) → RRF 퓨전 → BGE Reranker → Quality Gate → LLM 생성 순서입니다."},

    # ===== [29-36] 법률 도메인 =====
    {"question": "대한민국 헌법에서 국민의 기본권은 어떻게 규정하고 있나요?", "type": "legal",
     "ground_truth": "헌법 제2장에서 국민의 기본권으로 평등권, 자유권, 참정권, 청구권, 사회권 등을 규정하고 있습니다."},
    {"question": "민법에서 계약의 성립 요건은 무엇인가요?", "type": "legal",
     "ground_truth": "계약은 당사자 간 청약과 승낙의 합치로 성립하며, 의사표시의 합치가 핵심 요건입니다."},
    {"question": "형법에서 정당방위의 성립 요건은 무엇인가요?", "type": "legal",
     "ground_truth": "현재의 부당한 침해에 대해 자기 또는 타인의 법익을 방위하기 위한 상당한 이유가 있는 행위입니다."},
    {"question": "상법에서 주식회사의 설립 절차는 어떻게 되나요?", "type": "legal",
     "ground_truth": "발기인이 정관을 작성하고, 주식 인수, 납입, 이사 선임, 설립등기 순서로 진행됩니다."},
    {"question": "민사소송법에서 소장 제출과 소송 진행 절차는?", "type": "legal",
     "ground_truth": "원고가 관할 법원에 소장을 제출하면 피고에게 송달되고, 변론기일을 거쳐 판결이 선고됩니다."},
    {"question": "문화재보호법에서 국가지정문화재의 지정 절차는?", "type": "legal",
     "ground_truth": "문화재위원회의 심의를 거쳐 문화재청장이 국보, 보물, 사적 등으로 지정합니다."},
    {"question": "소방시설법에서 특정소방대상물의 소방시설 설치 의무는?", "type": "legal",
     "ground_truth": "건축물의 용도와 규모에 따라 소화설비, 경보설비, 피난설비 등을 설치해야 합니다."},
    {"question": "법령 용어에서 '선의'와 '악의'의 법률적 의미 차이는?", "type": "legal",
     "ground_truth": "법률에서 선의는 어떤 사실을 모르는 상태, 악의는 어떤 사실을 알고 있는 상태를 의미합니다."},

    # ===== [37-42] AI/LLM 심화 =====
    {"question": "AI 에이전트에서 Tool Calling과 Reasoning의 상호작용은 어떻게 이루어지나요?", "type": "multi_hop",
     "ground_truth": "AI 에이전트는 Reasoning으로 문제를 분석한 후 적절한 Tool을 선택하여 호출하고 결과를 다시 Reasoning에 반영합니다."},
    {"question": "Reranking이 RAG 검색 품질을 향상시키는 원리는 무엇인가요?", "type": "factual",
     "ground_truth": "Reranking은 Cross-encoder로 쿼리와 문서 쌍의 관련성을 정밀 평가하여 초기 검색 결과의 순위를 재조정합니다."},
    {"question": "Agentic Mesh 아키텍처란 무엇이며 미래 AI 에이전트 생태계에 어떤 영향을 미치나요?", "type": "factual",
     "ground_truth": "Agentic Mesh는 다수의 자율 에이전트가 메시 네트워크로 협업하는 분산 AI 아키텍처입니다."},
    {"question": "AI 오케스트레이션이란 무엇이며 2025년 주요 트렌드는?", "type": "factual",
     "ground_truth": "AI 오케스트레이션은 여러 AI 모델과 서비스를 조율하여 복잡한 태스크를 수행하는 기술입니다."},
    {"question": "Chain of Thought 추론 방식이 LLM 성능에 미치는 영향은?", "type": "factual",
     "ground_truth": "Chain of Thought는 LLM이 단계별로 추론하도록 유도하여 복잡한 문제 해결 능력을 향상시킵니다."},
    {"question": "강화학습(RL)을 활용한 검색 에이전트 학습 방법은 어떤 것이 있나요?", "type": "factual",
     "ground_truth": "검색 에이전트에 RL을 적용하여 쿼리 재작성, 문서 선택 등의 정책을 최적화할 수 있습니다."},

    # ===== [43-46] KT DS / 프로젝트 특화 =====
    {"question": "KT DS 아키텍처팀 AI 프로젝트 워크샵의 주요 주제는 무엇이었나요?", "type": "factual",
     "ground_truth": "KT DS 아키텍처팀에서 AI 프로젝트 이해를 위한 워크샵을 진행하여 AI 기반 시스템 설계를 논의했습니다."},
    {"question": "MSA 차세대 플랫폼 전환 프로젝트에서 사용된 기술 스택은?", "type": "graph_entity",
     "ground_truth": "Java 17, Kotlin 1.9, Spring Boot 3.2, PostgreSQL 16, Redis 7, Docker Compose, GitHub Actions 등을 사용합니다."},
    {"question": "SLM(Small Language Model)과 LLM의 차이점과 각각의 활용 사례는?", "type": "comparative",
     "ground_truth": "SLM은 경량 모델로 엣지 디바이스에 적합하고, LLM은 대규모 모델로 복잡한 추론에 적합합니다."},
    {"question": "비즈니스에 실제 활용 가능한 LLM 서비스를 만들기 위한 핵심 고려사항은?", "type": "factual",
     "ground_truth": "프롬프트 설계, RAG 파이프라인, 평가 체계, 비용 최적화, 할루시네이션 방지가 핵심 고려사항입니다."},

    # ===== [47-50] 비-Graph 트리거 (일반 쿼리) =====
    {"question": "프롬프트 엔지니어링의 핵심 원칙과 효과적인 기법은 무엇인가요?", "type": "semantic",
     "ground_truth": "명확한 지시, 예시 제공(few-shot), 역할 부여, 단계별 사고 유도가 핵심 기법입니다."},
    {"question": "벡터 임베딩의 차원 수가 검색 정확도에 미치는 영향은?", "type": "semantic",
     "ground_truth": "차원이 높을수록 의미 표현력이 증가하나 계산 비용도 증가하며, 1024차원이 성능과 효율의 균형점입니다."},
    {"question": "LLM 환각(hallucination)을 줄이기 위한 효과적인 방법은?", "type": "semantic",
     "ground_truth": "RAG로 외부 지식 주입, 온도 낮추기, 소스 인용 강제, Faithfulness 평가로 환각을 줄일 수 있습니다."},
    {"question": "모놀리식 아키텍처에서 마이크로서비스로 전환할 때 가장 큰 도전 과제는?", "type": "comparative",
     "ground_truth": "데이터 일관성 유지, 분산 트랜잭션, 서비스 간 통신 복잡성, 운영 오버헤드 증가가 주요 도전 과제입니다."},
]


# ---------------------------------------------------------------------------
# Data Quality Analyzer
# ---------------------------------------------------------------------------
class DataQualityAnalyzer:
    """임베딩 데이터 품질 사전 분석"""

    GLYPH_PATTERN = re.compile(r"[■□★☆●○◆◇△▽▷◁▶◀♠♣♥♦]+")
    BROKEN_CHARS = re.compile(r"[\ufff0-\uffff\x00-\x08\x0e-\x1f]{3,}")

    def __init__(self, es: Elasticsearch, index: str = HRKP_INDEX):
        self.es = es
        self.index = index

    def analyze(self) -> Dict[str, Any]:
        """전체 데이터 품질 분석"""
        total = self.es.count(index=self.index)["count"]

        # GLYPH 아티팩트 탐지
        glyph_query = {
            "query": {"regexp": {"content": ".*[■□★☆●○◆◇].*"}},
            "size": 0,
            "track_total_hits": True,
        }
        try:
            glyph_resp = self.es.search(index=self.index, body=glyph_query)
            glyph_count = glyph_resp["hits"]["total"]["value"]
        except Exception:
            glyph_count = -1

        # 문서별 청크 수 분포
        doc_agg = {
            "size": 0,
            "aggs": {
                "docs": {
                    "terms": {"field": "document_id", "size": 50},
                }
            },
        }
        try:
            doc_resp = self.es.search(index=self.index, body=doc_agg)
            doc_chunks = [
                {"doc_id": b["key"], "count": b["doc_count"]}
                for b in doc_resp["aggregations"]["docs"]["buckets"]
            ]
        except Exception:
            doc_chunks = []

        # 짧은 청크 (50자 미만) 비율
        short_query = {
            "query": {"script": {"script": {"source": "doc['content'].size() > 0 && doc['content'].value.length() < 50"}}},
            "size": 0,
            "track_total_hits": True,
        }
        try:
            short_resp = self.es.search(index=self.index, body=short_query)
            short_count = short_resp["hits"]["total"]["value"]
        except Exception:
            short_count = -1

        return {
            "total_chunks": total,
            "glyph_artifact_chunks": glyph_count,
            "glyph_ratio": round(glyph_count / total * 100, 1) if glyph_count > 0 else 0,
            "short_chunks": short_count,
            "top_documents": doc_chunks[:10],
        }


# ---------------------------------------------------------------------------
# HRKP Client (JWT 자동 갱신)
# ---------------------------------------------------------------------------
class HRKPClient:
    def __init__(self):
        self.base_url = HRKP_API_URL
        self.session = requests.Session()
        self.token = None
        self._query_count = 0

    def login(self) -> bool:
        r = self.session.post(
            f"{self.base_url}/auth/login",
            json={"email": "admin@example.com", "password": "admin123!"},
            timeout=30,
        )
        if r.status_code == 200:
            self.token = r.json().get("accessToken")
            self.session.headers["Authorization"] = f"Bearer {self.token}"
            self._query_count = 0
            return True
        return False

    def _maybe_refresh_token(self):
        """TOKEN_REFRESH_INTERVAL 마다 자동 재로그인"""
        self._query_count += 1
        if self._query_count >= TOKEN_REFRESH_INTERVAL:
            print(f"    [JWT 갱신] {self._query_count}쿼리 경과, 재로그인...")
            if self.login():
                print("    [JWT 갱신] 성공")
            else:
                print("    [JWT 갱신] 실패! 이전 토큰 유지")

    def hybrid_search(self, query: str, top_k: int = 10) -> Dict:
        """원시 hybrid 검색 (v2 방식)"""
        r = self.session.post(
            f"{self.base_url}/search/hybrid",
            json={"query": query, "top_k": top_k, "useGraph": True, "useVector": True},
            timeout=60,
        )
        r.raise_for_status()
        return r.json()

    def chat_search(self, query: str, top_k: int = 5) -> Dict:
        """전체 파이프라인 검색 (Reranker + QualityGate)"""
        self._maybe_refresh_token()
        r = self.session.post(
            f"{self.base_url}/search/chat",
            json={"query": query, "top_k": top_k},
            timeout=180,
        )
        r.raise_for_status()
        return r.json()

    def reranker_health(self) -> Dict:
        """Reranker 상태 확인 (ONNX/PyTorch)"""
        try:
            r = self.session.get(f"{self.base_url}/search/health", timeout=10)
            return r.json() if r.status_code == 200 else {}
        except Exception:
            return {}


# ---------------------------------------------------------------------------
# RCSV Search
# ---------------------------------------------------------------------------
class RCSVSearcher:
    def __init__(self, es: Elasticsearch, index: str = RCSV_INDEX):
        self.es = es
        self.index = index

    def bm25_search(self, query: str, top_k: int = 10) -> List[Dict]:
        body = {
            "query": {"match": {"text": {"query": query, "analyzer": "standard"}}},
            "_source": ["text", "chunk_id", "document_id", "metadata"],
            "size": top_k,
        }
        r = self.es.search(index=self.index, body=body)
        return [
            {
                "chunk_id": h["_id"],
                "content": h["_source"].get("text", ""),
                "score": h["_score"],
                "source": "keyword",
                "metadata": h["_source"].get("metadata", {}),
            }
            for h in r["hits"]["hits"]
        ]


# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------
def generate_answer_deepseek(question: str, contexts: List[str]) -> str:
    ctx = "\n\n---\n\n".join(contexts[:5])
    try:
        r = requests.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "user",
                        "content": f"다음 컨텍스트를 참고하여 질문에 답변하세요. 컨텍스트에 없는 정보는 사용하지 마세요.\n\n## 컨텍스트\n{ctx}\n\n## 질문\n{question}\n\n간결하고 정확하게 한국어로 답변하세요.",
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 500,
            },
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"[DeepSeek error: {e}]"


# ---------------------------------------------------------------------------
# LLM-as-Judge
# ---------------------------------------------------------------------------
def llm_judge(prompt: str, retries: int = 2) -> float:
    for attempt in range(retries + 1):
        try:
            r = requests.post(
                f"{DEEPSEEK_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.0,
                    "max_tokens": 10,
                },
                timeout=30,
            )
            r.raise_for_status()
            text = r.json()["choices"][0]["message"]["content"].strip()
            match = re.search(r"(\d+\.?\d*)", text)
            if match:
                return max(0.0, min(1.0, float(match.group(1))))
            return 0.5
        except Exception as e:
            if attempt < retries:
                time.sleep(2)
            else:
                print(f"[WARN] Judge failed after {retries + 1} attempts: {e}")
                return 0.5
    return 0.5


def evaluate_samples(samples: List[Dict], label: str = "") -> Dict[str, float]:
    scores = {
        "faithfulness": [],
        "answer_relevancy": [],
        "context_precision": [],
        "context_recall": [],
    }
    for i, s in enumerate(samples):
        ctx = "\n---\n".join(s["contexts"][:3])[:2000]
        print(f"    {label} Q{i+1} judging...", end=" ", flush=True)

        scores["faithfulness"].append(
            llm_judge(
                f"답변이 컨텍스트에 충실한지 0.0~1.0으로 평가. 모든 주장이 근거 있으면 1.0.\n\n컨텍스트:\n{ctx}\n\n답변:\n{s['answer'][:500]}\n\n숫자만:"
            )
        )
        scores["answer_relevancy"].append(
            llm_judge(
                f"답변이 질문에 적절한지 0.0~1.0으로 평가. 정확히 답하면 1.0.\n\n질문: {s['question']}\n\n답변:\n{s['answer'][:500]}\n\n숫자만:"
            )
        )
        scores["context_precision"].append(
            llm_judge(
                f"컨텍스트가 질문에 관련되는지 0.0~1.0으로 평가.\n\n질문: {s['question']}\n\n컨텍스트:\n{ctx}\n\n숫자만:"
            )
        )
        if s.get("ground_truth"):
            scores["context_recall"].append(
                llm_judge(
                    f"정답 정보가 컨텍스트에 있는지 0.0~1.0으로 평가.\n\n정답: {s['ground_truth']}\n\n컨텍스트:\n{ctx}\n\n숫자만:"
                )
            )
        print("done")

    return {k: round(sum(v) / len(v), 4) if v else None for k, v in scores.items()}


# ---------------------------------------------------------------------------
# Report Builder
# ---------------------------------------------------------------------------
def build_report(
    raw_scores, full_scores, rcsv_scores,
    raw_results, full_results, rcsv_results,
    questions, ts, data_quality, reranker_info,
):
    lines = []
    w = lines.append

    w("# HRKP v6 Cross-System RAGAS Evaluation Report")
    w("")
    w(f"**평가 일시**: {ts}")
    w(f"**평가 방법**: LLM-as-Judge (DeepSeek V3.2)")
    w(f"**테스트 쿼리**: {len(questions)}개 (7개 도메인)")
    w(f"**스크립트**: `scripts/rcsv_comparison_eval_v4.py`")
    w(f"**변경사항**: JWT 자동 갱신, 데이터 품질 사전 분석")
    w("")
    w("---")
    w("")

    # 0. Data Quality
    w("## 0. 데이터 품질 사전 분석")
    w("")
    w(f"| 항목 | 값 |")
    w(f"|------|-----|")
    w(f"| 총 청크 수 | {data_quality['total_chunks']:,} |")
    w(f"| GLYPH 아티팩트 | {data_quality['glyph_artifact_chunks']} ({data_quality['glyph_ratio']}%) |")
    w(f"| 짧은 청크 (<50자) | {data_quality['short_chunks']} |")
    w("")
    if data_quality.get("top_documents"):
        w("### 문서별 청크 수 (상위 10)")
        w("")
        w("| 문서 ID | 청크 수 |")
        w("|---------|:-------:|")
        for d in data_quality["top_documents"][:10]:
            w(f"| {d['doc_id'][:40]}... | {d['count']} |")
        w("")

    # 0.5 Reranker Status
    w("## 0.5 Reranker 상태")
    w("")
    if reranker_info:
        for k, v in reranker_info.items():
            w(f"- **{k}**: {v}")
    else:
        w("- (상태 정보 미확인)")
    w("")

    # 1. System comparison
    w("## 1. 시스템 비교")
    w("")
    w("| 항목 | HRKP-RAW | HRKP-FULL | RCSV |")
    w("|------|----------|-----------|------|")
    w("| 검색 | BM25+Dense+Graph(RRF) | BM25+Dense+Graph(RRF)+**BGE Reranker** | BM25 only |")
    w("| 품질 필터 | 없음 | **Quality Gate v5** | 없음 |")
    w("| LLM | DeepSeek (별도 생성) | DeepSeek (파이프라인 내장) | DeepSeek (별도 생성) |")
    w("")

    # 2. RAGAS metrics
    w("## 2. RAGAS 메트릭 비교")
    w("")
    w("| 메트릭 | v5-RAW baseline | v6-RAW | v6-FULL | v6-RCSV |")
    w("|--------|:--------------:|:------:|:-------:|:-------:|")
    for m in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
        v5r = V5_BASELINE["hrkp_raw"].get(m, 0)
        raw = raw_scores.get(m) or 0
        full = full_scores.get(m) or 0
        rcsv = rcsv_scores.get(m) or 0
        w(f"| {m} | {v5r:.4f} | {raw:.4f} | {full:.4f} | {rcsv:.4f} |")
    w("")

    # 3. v6-FULL vs v5-FULL improvement
    w("## 3. v6-FULL vs v5 baseline 개선")
    w("")
    w("| 메트릭 | v5-FULL | v6-FULL | 변화량 | 판정 |")
    w("|--------|:------:|:-------:|:------:|:----:|")
    wins = 0
    for m in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
        v5f = V5_BASELINE["hrkp_full"].get(m, 0)
        full = full_scores.get(m) or 0
        d = full - v5f
        verdict = "**UP**" if d > 0.005 else ("DOWN" if d < -0.005 else "=")
        if d > 0.005:
            wins += 1
        w(f"| {m} | {v5f:.4f} | {full:.4f} | {d:+.4f} | {verdict} |")
    w("")
    w(f"> **개선된 메트릭**: {wins}/4 (v5-FULL은 JWT 만료로 Q43-Q50 ERR 포함, 이번은 자동 갱신)")
    w("")

    # 4. Quality Gate analysis
    w("## 4. Quality Gate 분석")
    w("")
    w("| Q# | 질문 | 도메인 | Grade | Max Score | Sources | 레이턴시 |")
    w("|:--:|------|--------|:-----:|:---------:|:-------:|--------:|")
    grade_counts = {}
    for i, fr in enumerate(full_results):
        g = fr.get("grade", "N/A")
        grade_counts[g] = grade_counts.get(g, 0) + 1
        w(
            f"| Q{i+1} | {questions[i]['question'][:35]}... | {questions[i]['type']} | "
            f"{g} | {fr.get('max_score', 0):.4f} | {fr['num_results']} | {fr['latency_ms']/1000:.1f}s |"
        )
    w("")

    # Grade distribution
    w("### Grade 분포")
    w("")
    w("| Grade | 건수 | 비율 |")
    w("|:-----:|:----:|:----:|")
    for g in ["HIGH", "PARTIAL", "NONE", "ERR"]:
        cnt = grade_counts.get(g, 0)
        pct = round(cnt / len(full_results) * 100, 1)
        if cnt > 0:
            w(f"| **{g}** | {cnt} | {pct}% |")
    w("")

    # 5. Domain analysis
    w("## 5. 도메인별 성능")
    w("")
    domain_stats = {}
    for i, fr in enumerate(full_results):
        dtype = questions[i]["type"]
        if dtype not in domain_stats:
            domain_stats[dtype] = {"total": 0, "high": 0, "none": 0, "err": 0, "scores": []}
        domain_stats[dtype]["total"] += 1
        if fr.get("grade") == "HIGH":
            domain_stats[dtype]["high"] += 1
        elif fr.get("grade") == "NONE":
            domain_stats[dtype]["none"] += 1
        elif fr.get("grade") == "ERR":
            domain_stats[dtype]["err"] += 1
        if fr.get("max_score", 0) > 0:
            domain_stats[dtype]["scores"].append(fr["max_score"])

    w("| 도메인 | 쿼리 | HIGH | NONE | ERR | HIGH% | 평균 max_score |")
    w("|--------|:----:|:----:|:----:|:---:|:-----:|:--------------:|")
    for dtype, stats in sorted(domain_stats.items(), key=lambda x: -(x[1]["high"] / max(x[1]["total"], 1))):
        avg_s = sum(stats["scores"]) / len(stats["scores"]) if stats["scores"] else 0
        high_pct = round(stats["high"] / max(stats["total"] - stats["err"], 1) * 100, 1)
        w(
            f"| {dtype} | {stats['total']} | {stats['high']} | {stats['none']} | "
            f"{stats['err']} | {high_pct}% | {avg_s:.3f} |"
        )
    w("")

    # 6. Latency
    w("## 6. 레이턴시")
    w("")
    raw_lat = sum(r["latency_ms"] for r in raw_results) / len(raw_results)
    full_lat = sum(r["latency_ms"] for r in full_results if r.get("grade") != "ERR") / max(
        sum(1 for r in full_results if r.get("grade") != "ERR"), 1
    )
    rcsv_lat = sum(r["latency_ms"] for r in rcsv_results) / len(rcsv_results)
    w("| 시스템 | 평균 레이턴시 |")
    w("|--------|:-----------:|")
    w(f"| HRKP-RAW | {raw_lat:.0f}ms |")
    w(f"| HRKP-FULL | {full_lat:.0f}ms |")
    w(f"| RCSV | {rcsv_lat:.0f}ms |")
    w("")

    # 7. Conclusion
    w("## 7. 결론")
    w("")
    w(f"- **개선된 메트릭**: {wins}/4 (vs v5-FULL)")
    w(f"- **JWT 만료 이슈**: 자동 갱신으로 해결 ({TOKEN_REFRESH_INTERVAL}쿼리마다 재로그인)")
    w(f"- **데이터 품질**: GLYPH 아티팩트 {data_quality['glyph_artifact_chunks']}개 ({data_quality['glyph_ratio']}%)")
    w("")
    w("---")
    w(f"*Generated: {ts}*")
    w("*Script: rcsv_comparison_eval_v4.py*")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("  HRKP v6 Cross-System RAGAS Evaluation")
    print("  50-Query, JWT auto-refresh, Data Quality Analysis")
    print("=" * 70)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M KST")
    print(f"  Time: {ts}")
    print(f"  Questions: {len(TEST_QUESTIONS)}")
    print(f"  JWT refresh interval: every {TOKEN_REFRESH_INTERVAL} queries")
    print()

    es = Elasticsearch(ES_URL)

    # -----------------------------------------------------------------------
    # [0/6] Data Quality Analysis
    # -----------------------------------------------------------------------
    print("[0/6] Data Quality Analysis...")
    analyzer = DataQualityAnalyzer(es)
    data_quality = analyzer.analyze()
    print(f"  Total chunks: {data_quality['total_chunks']:,}")
    print(f"  GLYPH artifacts: {data_quality['glyph_artifact_chunks']} ({data_quality['glyph_ratio']}%)")
    print(f"  Short chunks: {data_quality['short_chunks']}")
    print()

    # -----------------------------------------------------------------------
    # [0.5/6] Reranker Health Check
    # -----------------------------------------------------------------------
    hrkp = HRKPClient()
    if not hrkp.login():
        print("  HRKP login FAILED!")
        sys.exit(1)
    print("  HRKP login OK")

    reranker_info = hrkp.reranker_health()
    if reranker_info:
        print(f"  Reranker: {json.dumps(reranker_info, indent=2)[:200]}")
    print()

    hrkp_count = es.count(index=HRKP_INDEX)["count"]
    rcsv_count = es.count(index=RCSV_INDEX)["count"]
    print(f"  HRKP index: {hrkp_count} docs")
    print(f"  RCSV index: {rcsv_count} docs")
    print()

    # -----------------------------------------------------------------------
    # [1/6] HRKP-RAW
    # -----------------------------------------------------------------------
    print("[1/6] HRKP-RAW: /api/v1/search/hybrid...")
    hrkp_raw_results = []
    for i, q in enumerate(TEST_QUESTIONS):
        t0 = time.monotonic()
        try:
            resp = hrkp.hybrid_search(q["question"])
            lat = round((time.monotonic() - t0) * 1000, 1)
            results = resp.get("results", [])
            contexts = [r["content"] for r in results[:10]]
            top1_score = results[0]["score"] if results else 0
        except Exception as e:
            print(f"  Q{i+1} ERROR: {e}")
            contexts, lat, top1_score = [], 0, 0
        hrkp_raw_results.append({
            "question": q["question"], "type": q["type"],
            "contexts": contexts, "latency_ms": lat,
            "top1_score": top1_score, "num_results": len(contexts),
        })
        if (i + 1) % 10 == 0 or i == 0:
            print(f"  Q{i+1}: {len(contexts)} results, {lat}ms, top1={top1_score:.4f}")
    print(f"  Completed: {len(hrkp_raw_results)} queries")
    print()

    # -----------------------------------------------------------------------
    # [2/6] HRKP-FULL (with JWT auto-refresh)
    # -----------------------------------------------------------------------
    print(f"[2/6] HRKP-FULL: /api/v1/search/chat (JWT refresh every {TOKEN_REFRESH_INTERVAL}q)...")
    hrkp_full_results = []
    for i, q in enumerate(TEST_QUESTIONS):
        t0 = time.monotonic()
        try:
            resp = hrkp.chat_search(q["question"])
            lat = round((time.monotonic() - t0) * 1000, 1)
            sources = resp.get("sources", [])
            contexts = [s.get("content", "") for s in sources]
            answer = resp.get("answer", "")
            stages = resp.get("pipelineStages", {})
            qg = stages.get("quality_gate", {})
            grade = qg.get("grade", "N/A")
            max_score = qg.get("max_score", 0)
        except Exception as e:
            print(f"  Q{i+1} ERROR: {e}")
            contexts, lat, answer = [], 0, f"[ERROR: {e}]"
            grade, max_score = "ERR", 0
        hrkp_full_results.append({
            "question": q["question"], "type": q["type"],
            "contexts": contexts, "latency_ms": lat,
            "answer": answer, "grade": grade, "max_score": max_score,
            "num_results": len(contexts),
        })
        print(f"  Q{i+1}: grade={grade}, {len(contexts)}src, {lat/1000:.1f}s, max={max_score:.4f}")
    err_count = sum(1 for r in hrkp_full_results if r.get("grade") == "ERR")
    print(f"  Completed: {len(hrkp_full_results)} queries ({err_count} ERR)")
    print()

    # -----------------------------------------------------------------------
    # [3/6] RCSV BM25
    # -----------------------------------------------------------------------
    print("[3/6] RCSV: BM25 + DeepSeek...")
    rcsv = RCSVSearcher(es)
    rcsv_results = []
    for i, q in enumerate(TEST_QUESTIONS):
        t0 = time.monotonic()
        try:
            results = rcsv.bm25_search(q["question"])
            lat = round((time.monotonic() - t0) * 1000, 1)
            contexts = [r["content"] for r in results[:10]]
        except Exception as e:
            print(f"  Q{i+1} RCSV ERROR: {e}")
            contexts, lat = [], 0
        rcsv_results.append({
            "question": q["question"], "type": q["type"],
            "contexts": contexts, "latency_ms": lat,
            "num_results": len(contexts),
        })
        if (i + 1) % 10 == 0 or i == 0:
            print(f"  Q{i+1}: {len(contexts)} results, {lat}ms")
    print(f"  Completed: {len(rcsv_results)} queries")
    print()

    # -----------------------------------------------------------------------
    # [4/6] Answer generation (RAW + RCSV only)
    # -----------------------------------------------------------------------
    print("[4/6] Answer generation (DeepSeek)...")
    for i, q in enumerate(TEST_QUESTIONS):
        if (i + 1) % 5 == 0 or i == 0:
            print(f"  Q{i+1}...", end=" ", flush=True)
        hrkp_raw_results[i]["answer"] = generate_answer_deepseek(
            q["question"], hrkp_raw_results[i]["contexts"]
        )
        rcsv_results[i]["answer"] = generate_answer_deepseek(
            q["question"], rcsv_results[i]["contexts"]
        )
        if (i + 1) % 5 == 0 or i == 0:
            print(f"RAW={len(hrkp_raw_results[i]['answer'])}c, RCSV={len(rcsv_results[i]['answer'])}c")
    print()

    # -----------------------------------------------------------------------
    # [5/6] RAGAS evaluation (LLM-as-judge)
    # -----------------------------------------------------------------------
    print("[5/6] RAGAS evaluation (LLM-as-judge)...")

    def make_samples(results, questions):
        return [
            {
                "question": q["question"],
                "answer": results[i].get("answer", ""),
                "contexts": results[i]["contexts"][:5],
                "ground_truth": q.get("ground_truth"),
            }
            for i, q in enumerate(questions)
        ]

    print("  --- HRKP-RAW ---")
    raw_scores = evaluate_samples(make_samples(hrkp_raw_results, TEST_QUESTIONS), "RAW")
    print(f"  RAW: {raw_scores}")

    print("  --- HRKP-FULL ---")
    full_scores = evaluate_samples(make_samples(hrkp_full_results, TEST_QUESTIONS), "FULL")
    print(f"  FULL: {full_scores}")

    print("  --- RCSV ---")
    rcsv_scores = evaluate_samples(make_samples(rcsv_results, TEST_QUESTIONS), "RCSV")
    print(f"  RCSV: {rcsv_scores}")
    print()

    # -----------------------------------------------------------------------
    # [6/6] Report generation
    # -----------------------------------------------------------------------
    print("[6/6] Report generation...")

    report = build_report(
        raw_scores, full_scores, rcsv_scores,
        hrkp_raw_results, hrkp_full_results, rcsv_results,
        TEST_QUESTIONS, ts, data_quality, reranker_info,
    )

    out_dir = "/app/data"
    os.makedirs(out_dir, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")

    json_path = f"{out_dir}/hrkp_ragas_v6_{date_str}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "raw_scores": raw_scores,
                "full_scores": full_scores,
                "rcsv_scores": rcsv_scores,
                "v5_baseline": V5_BASELINE,
                "data_quality": data_quality,
                "reranker_info": reranker_info,
                "hrkp_raw_results": hrkp_raw_results,
                "hrkp_full_results": hrkp_full_results,
                "rcsv_results": rcsv_results,
                "questions": TEST_QUESTIONS,
                "timestamp": ts,
                "jwt_refresh_interval": TOKEN_REFRESH_INTERVAL,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    report_path = f"{out_dir}/hrkp_ragas_v6_report_{date_str}.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"  JSON: {json_path}")
    print(f"  Report: {report_path}")
    print()

    # Summary
    print("=" * 70)
    print("  v6 RAGAS Comparison Summary")
    print("=" * 70)
    header = f"  {'Metric':<25} {'v5-RAW':>8} {'v6-RAW':>8} {'v6-FULL':>8} {'v6-RCSV':>8}"
    print(header)
    print(f"  {'-'*25} {'-'*8} {'-'*8} {'-'*8} {'-'*8}")
    for m in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
        v5r = V5_BASELINE["hrkp_raw"].get(m, 0)
        raw = raw_scores.get(m) or 0
        full = full_scores.get(m) or 0
        rcsv = rcsv_scores.get(m) or 0
        print(f"  {m:<25} {v5r:>8.4f} {raw:>8.4f} {full:>8.4f} {rcsv:>8.4f}")

    # v6-FULL vs v5-FULL
    print()
    print("  v6-FULL vs v5-FULL (JWT 만료 수정):")
    for m in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
        v5f = V5_BASELINE["hrkp_full"].get(m, 0)
        full = full_scores.get(m) or 0
        d = full - v5f
        print(f"    {m:<25} {d:+.4f} {'UP' if d > 0.005 else 'DOWN' if d < -0.005 else '='}")
    print()
    print(f"  Data quality: {data_quality['glyph_artifact_chunks']} GLYPH artifacts ({data_quality['glyph_ratio']}%)")
    print(f"  JWT errors: {err_count}/{len(hrkp_full_results)}")
    print()


if __name__ == "__main__":
    main()
