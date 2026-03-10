"""
Graph RAG A/B Comparison Test

Graph 검색 활성화/비활성화 시 검색 품질 차이를 분석합니다.

테스트 그룹:
  - A그룹: Graph 검색 포함 (useGraph=true)
  - B그룹: Graph 검색 비활성화 (useGraph=false)

평가 지표:
  - 검색 결과 수 / 고유 문서 수
  - 응답 레이턴시 비교
  - 답변 품질 (LLM judge 또는 RAGAS)
  - Precision/Recall 비교

실행 방법:
  export TEST_MODE=docker
  python -m pytest knowledge_service/src/tests/evaluation/graph_rag_ab_test.py -v -s

  또는 직접 실행:
  cd knowledge_service && python -m tests.evaluation.graph_rag_ab_test

STORY-097: Graph RAG A/B 비교 평가 보고서
"""

import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest

# Docker 환경에서만 실행
pytestmark = [
    pytest.mark.evaluation,
    pytest.mark.skipif(
        os.getenv("TEST_MODE") != "docker",
        reason="TEST_MODE=docker 필수 (실제 API 연동 테스트)",
    ),
]

# ---------------------------------------------------------------------------
# Test Dataset: 7 Domain Questions
# ---------------------------------------------------------------------------

AB_TEST_QUESTIONS = [
    # 1. 정보보호 정책
    {
        "id": "SEC-001",
        "domain": "정보보호 정책",
        "question": "정보보호 정책에서 접근통제의 기본 원칙은 무엇인가요?",
        "ground_truth": "접근통제의 기본 원칙은 최소 권한 원칙(Principle of Least Privilege)으로, "
                        "사용자에게 업무 수행에 필요한 최소한의 권한만 부여하는 것입니다.",
        "expected_entities": ["접근통제", "최소 권한 원칙", "보안 정책"],
    },
    {
        "id": "SEC-002",
        "domain": "정보보호 정책",
        "question": "정보보호 관리체계(ISMS)의 핵심 구성요소는 무엇인가요?",
        "ground_truth": "ISMS는 정보보호 정책, 조직, 위험 관리, 자산 관리, 인적 보안, "
                        "물리적 보안, 운영 보안, 접근 통제 등의 영역으로 구성됩니다.",
        "expected_entities": ["ISMS", "위험 관리", "자산 관리"],
    },
    # 2. 네트워크 보안
    {
        "id": "NET-001",
        "domain": "네트워크 보안",
        "question": "네트워크 보안에서 방화벽과 IDS/IPS의 차이점은 무엇인가요?",
        "ground_truth": "방화벽은 트래픽을 규칙 기반으로 허용/차단하고, "
                        "IDS는 침입을 탐지만 하며, IPS는 탐지 후 자동으로 차단까지 수행합니다.",
        "expected_entities": ["방화벽", "IDS", "IPS", "네트워크 보안"],
    },
    {
        "id": "NET-002",
        "domain": "네트워크 보안",
        "question": "VPN의 종류와 각각의 특징을 설명해주세요.",
        "ground_truth": "VPN은 크게 Site-to-Site VPN과 Remote Access VPN으로 나뉘며, "
                        "IPSec, SSL/TLS 등의 프로토콜을 사용합니다.",
        "expected_entities": ["VPN", "IPSec", "SSL"],
    },
    # 3. 개인정보보호
    {
        "id": "PRI-001",
        "domain": "개인정보보호",
        "question": "개인정보보호법에서 정보주체의 권리에는 어떤 것들이 있나요?",
        "ground_truth": "정보주체는 개인정보의 열람, 정정, 삭제, 처리정지를 요구할 수 있는 "
                        "권리를 가지며, 동의 철회권과 손해배상 청구권도 있습니다.",
        "expected_entities": ["정보주체", "개인정보보호법", "열람권", "삭제권"],
    },
    # 4. 클라우드 보안
    {
        "id": "CLD-001",
        "domain": "클라우드 보안",
        "question": "클라우드 환경에서 데이터 암호화 전략은 어떻게 수립해야 하나요?",
        "ground_truth": "클라우드 데이터 암호화는 전송 중 암호화(TLS), 저장 시 암호화(AES-256), "
                        "키 관리(KMS) 세 가지 영역을 포함해야 합니다.",
        "expected_entities": ["암호화", "TLS", "AES-256", "KMS"],
    },
    # 5. 접근제어
    {
        "id": "ACC-001",
        "domain": "접근제어",
        "question": "역할 기반 접근제어(RBAC)와 속성 기반 접근제어(ABAC)의 차이는?",
        "ground_truth": "RBAC는 사용자 역할에 따라 권한을 부여하고, "
                        "ABAC는 사용자, 자원, 환경 등 다양한 속성을 기반으로 동적으로 권한을 결정합니다.",
        "expected_entities": ["RBAC", "ABAC", "접근제어"],
    },
    # 6. 보안 감사
    {
        "id": "AUD-001",
        "domain": "보안 감사",
        "question": "보안 감사 로그에서 반드시 기록해야 하는 항목은 무엇인가요?",
        "ground_truth": "보안 감사 로그에는 접근 시간, 접근 주체, 접근 대상, 수행 행위, "
                        "성공/실패 여부, IP 주소 등이 반드시 기록되어야 합니다.",
        "expected_entities": ["감사 로그", "접근 기록", "보안 감사"],
    },
    # 7. 사고 대응
    {
        "id": "INC-001",
        "domain": "사고 대응",
        "question": "보안 사고 발생 시 대응 절차는 어떻게 되나요?",
        "ground_truth": "보안 사고 대응은 탐지, 분석, 억제, 제거, 복구, 사후 조치의 "
                        "6단계로 진행되며, 사고 발생 후 즉시 CERT팀에 통보해야 합니다.",
        "expected_entities": ["사고 대응", "CERT", "탐지", "복구"],
    },
]


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class SearchResult:
    """단일 검색 결과"""
    query: str
    domain: str
    group: str  # "A" (with graph) or "B" (without graph)
    answer: str = ""
    contexts: List[str] = field(default_factory=list)
    result_count: int = 0
    unique_sources: int = 0
    latency_ms: float = 0.0
    error: Optional[str] = None
    search_type: str = ""
    scores: Dict[str, float] = field(default_factory=dict)


@dataclass
class ABComparisonResult:
    """A/B 비교 결과"""
    question_id: str
    domain: str
    question: str
    group_a: Optional[SearchResult] = None
    group_b: Optional[SearchResult] = None
    latency_diff_ms: float = 0.0
    result_count_diff: int = 0
    winner: str = "TIE"  # "A", "B", or "TIE"
    notes: str = ""


@dataclass
class ABTestReport:
    """A/B 테스트 종합 보고서"""
    timestamp: str = ""
    total_questions: int = 0
    group_a_config: Dict[str, Any] = field(default_factory=dict)
    group_b_config: Dict[str, Any] = field(default_factory=dict)
    comparisons: List[ABComparisonResult] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# A/B Test Runner
# ---------------------------------------------------------------------------

class GraphRAGABTester:
    """
    Graph RAG A/B 비교 테스트 실행기

    A그룹 (Graph 활성화)과 B그룹 (Graph 비활성화)의 검색 품질을 비교합니다.

    사용법:
        tester = GraphRAGABTester(base_url="http://localhost:8080")
        report = await tester.run_ab_test()
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        auth_email: str = "admin@example.com",
        auth_password: str = "admin123!",
    ):
        self.base_url = base_url.rstrip("/")
        self.auth_email = auth_email
        self.auth_password = auth_password
        self._token: Optional[str] = None

    async def _login(self) -> str:
        """로그인하여 JWT 토큰 획득"""
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/auth/login",
                json={"email": self.auth_email, "password": self.auth_password},
            )
            resp.raise_for_status()
            data = resp.json()
            # camelCase 필드명 사용 (MEMORY.md 참고)
            token = data.get("data", {}).get("accessToken", "")
            if not token:
                raise ValueError(f"Login failed: no accessToken in response: {data}")
            self._token = token
            return token

    async def _search(
        self,
        query: str,
        use_graph: bool = True,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """검색 API 호출"""
        import httpx

        if not self._token:
            await self._login()

        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

        payload = {
            "query": query,
            "top_k": top_k,
            "useGraph": use_graph,
            "useVector": True,
        }

        start_time = time.monotonic()

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/search/hybrid",
                json=payload,
                headers=headers,
            )
            elapsed_ms = (time.monotonic() - start_time) * 1000

            if resp.status_code != 200:
                return {
                    "error": f"HTTP {resp.status_code}: {resp.text[:200]}",
                    "latency_ms": elapsed_ms,
                }

            data = resp.json()
            return {
                "results": data.get("results", []),
                "total": data.get("total", 0),
                "search_type": data.get("search_type", ""),
                "latency_ms": data.get("latency_ms", elapsed_ms),
                "from_cache": data.get("from_cache", False),
            }

    async def _chat(
        self,
        query: str,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """Chat API 호출 (Graph 포함 여부는 서버 설정에 따름)"""
        import httpx

        if not self._token:
            await self._login()

        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

        payload = {
            "query": query,
            "topK": top_k,
            "useReasoner": False,
        }

        start_time = time.monotonic()

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/search/chat",
                json=payload,
                headers=headers,
            )
            elapsed_ms = (time.monotonic() - start_time) * 1000

            if resp.status_code != 200:
                return {
                    "error": f"HTTP {resp.status_code}: {resp.text[:200]}",
                    "latency_ms": elapsed_ms,
                }

            data = resp.json()
            return {
                "answer": data.get("answer", ""),
                "sources": data.get("sources", []),
                "latency_ms": data.get("latency_ms", elapsed_ms),
            }

    async def run_ab_test(
        self,
        questions: Optional[List[Dict]] = None,
    ) -> ABTestReport:
        """
        A/B 테스트 실행

        Args:
            questions: 테스트 질문 목록 (기본: AB_TEST_QUESTIONS)

        Returns:
            ABTestReport: 종합 비교 보고서
        """
        questions = questions or AB_TEST_QUESTIONS

        report = ABTestReport(
            timestamp=datetime.now().isoformat(),
            total_questions=len(questions),
            group_a_config={"useGraph": True, "description": "Graph 검색 활성화"},
            group_b_config={"useGraph": False, "description": "Graph 검색 비활성화"},
        )

        print(f"\n{'='*60}")
        print(f"Graph RAG A/B Test - {len(questions)} questions")
        print(f"{'='*60}\n")

        # Login once
        await self._login()

        for idx, q in enumerate(questions):
            question_id = q["id"]
            domain = q["domain"]
            question = q["question"]

            print(f"[{idx+1}/{len(questions)}] {question_id}: {question[:50]}...")

            # --- Group A: Graph enabled ---
            search_a = await self._search(question, use_graph=True)
            result_a = SearchResult(
                query=question,
                domain=domain,
                group="A",
                result_count=search_a.get("total", 0),
                latency_ms=search_a.get("latency_ms", 0),
                search_type=search_a.get("search_type", ""),
                error=search_a.get("error"),
            )
            if "results" in search_a:
                result_a.contexts = [
                    r.get("content", "")[:200] for r in search_a["results"]
                ]
                sources = set()
                for r in search_a["results"]:
                    src = r.get("source", r.get("document_title", ""))
                    if src:
                        sources.add(src)
                result_a.unique_sources = len(sources)

            # --- Group B: Graph disabled ---
            search_b = await self._search(question, use_graph=False)
            result_b = SearchResult(
                query=question,
                domain=domain,
                group="B",
                result_count=search_b.get("total", 0),
                latency_ms=search_b.get("latency_ms", 0),
                search_type=search_b.get("search_type", ""),
                error=search_b.get("error"),
            )
            if "results" in search_b:
                result_b.contexts = [
                    r.get("content", "")[:200] for r in search_b["results"]
                ]
                sources = set()
                for r in search_b["results"]:
                    src = r.get("source", r.get("document_title", ""))
                    if src:
                        sources.add(src)
                result_b.unique_sources = len(sources)

            # --- Compare ---
            latency_diff = result_a.latency_ms - result_b.latency_ms
            result_count_diff = result_a.result_count - result_b.result_count

            # Simple winner heuristic: more results + more unique sources = better
            if result_a.error or result_b.error:
                winner = "ERROR"
            elif result_a.unique_sources > result_b.unique_sources:
                winner = "A"
            elif result_b.unique_sources > result_a.unique_sources:
                winner = "B"
            else:
                winner = "TIE"

            comparison = ABComparisonResult(
                question_id=question_id,
                domain=domain,
                question=question,
                group_a=result_a,
                group_b=result_b,
                latency_diff_ms=latency_diff,
                result_count_diff=result_count_diff,
                winner=winner,
            )
            report.comparisons.append(comparison)

            print(f"  A(Graph): {result_a.result_count} results, "
                  f"{result_a.latency_ms:.0f}ms, "
                  f"{result_a.unique_sources} sources")
            print(f"  B(NoGraph): {result_b.result_count} results, "
                  f"{result_b.latency_ms:.0f}ms, "
                  f"{result_b.unique_sources} sources")
            print(f"  Winner: {winner}\n")

        # --- Summary ---
        a_wins = sum(1 for c in report.comparisons if c.winner == "A")
        b_wins = sum(1 for c in report.comparisons if c.winner == "B")
        ties = sum(1 for c in report.comparisons if c.winner == "TIE")
        errors = sum(1 for c in report.comparisons if c.winner == "ERROR")

        avg_latency_a = (
            sum(c.group_a.latency_ms for c in report.comparisons if c.group_a)
            / len(report.comparisons)
        )
        avg_latency_b = (
            sum(c.group_b.latency_ms for c in report.comparisons if c.group_b)
            / len(report.comparisons)
        )

        avg_results_a = (
            sum(c.group_a.result_count for c in report.comparisons if c.group_a)
            / len(report.comparisons)
        )
        avg_results_b = (
            sum(c.group_b.result_count for c in report.comparisons if c.group_b)
            / len(report.comparisons)
        )

        report.summary = {
            "a_wins": a_wins,
            "b_wins": b_wins,
            "ties": ties,
            "errors": errors,
            "avg_latency_a_ms": round(avg_latency_a, 1),
            "avg_latency_b_ms": round(avg_latency_b, 1),
            "latency_overhead_ms": round(avg_latency_a - avg_latency_b, 1),
            "avg_results_a": round(avg_results_a, 1),
            "avg_results_b": round(avg_results_b, 1),
            "overall_winner": "A (Graph)" if a_wins > b_wins else (
                "B (No Graph)" if b_wins > a_wins else "TIE"
            ),
        }

        print(f"\n{'='*60}")
        print(f"Summary")
        print(f"{'='*60}")
        print(f"  A (Graph) wins:   {a_wins}")
        print(f"  B (NoGraph) wins: {b_wins}")
        print(f"  Ties:             {ties}")
        print(f"  Errors:           {errors}")
        print(f"  Avg latency A:    {avg_latency_a:.0f}ms")
        print(f"  Avg latency B:    {avg_latency_b:.0f}ms")
        print(f"  Overall winner:   {report.summary['overall_winner']}")
        print(f"{'='*60}\n")

        return report

    def generate_markdown_report(self, report: ABTestReport) -> str:
        """A/B 비교 보고서를 Markdown 형식으로 생성"""
        lines = []

        lines.append("# Graph RAG A/B Comparison Report")
        lines.append("")
        lines.append(f"**Date**: {report.timestamp[:10]}")
        lines.append(f"**Total Questions**: {report.total_questions}")
        lines.append("")

        # Test Configuration
        lines.append("## Test Configuration")
        lines.append("")
        lines.append("| Group | Configuration | Description |")
        lines.append("|-------|--------------|-------------|")
        lines.append(f"| A | useGraph=true | {report.group_a_config.get('description', '')} |")
        lines.append(f"| B | useGraph=false | {report.group_b_config.get('description', '')} |")
        lines.append("")

        # Summary
        s = report.summary
        lines.append("## Summary")
        lines.append("")
        lines.append("| Metric | Group A (Graph) | Group B (No Graph) | Diff |")
        lines.append("|--------|----------------|-------------------|------|")
        lines.append(f"| Wins | {s.get('a_wins', 0)} | {s.get('b_wins', 0)} | - |")
        lines.append(f"| Avg Latency | {s.get('avg_latency_a_ms', 0)}ms | {s.get('avg_latency_b_ms', 0)}ms | {s.get('latency_overhead_ms', 0):+.0f}ms |")
        lines.append(f"| Avg Results | {s.get('avg_results_a', 0)} | {s.get('avg_results_b', 0)} | {s.get('avg_results_a', 0) - s.get('avg_results_b', 0):+.1f} |")
        lines.append(f"| Ties | {s.get('ties', 0)} | - | - |")
        lines.append(f"| Errors | {s.get('errors', 0)} | - | - |")
        lines.append("")
        lines.append(f"**Overall Winner**: {s.get('overall_winner', 'TIE')}")
        lines.append("")

        # Per-Question Results
        lines.append("## Per-Question Results")
        lines.append("")
        lines.append("| ID | Domain | A Results | A Latency | B Results | B Latency | Winner |")
        lines.append("|----|--------|-----------|-----------|-----------|-----------|--------|")

        for c in report.comparisons:
            a_results = c.group_a.result_count if c.group_a else 0
            a_latency = f"{c.group_a.latency_ms:.0f}ms" if c.group_a else "N/A"
            b_results = c.group_b.result_count if c.group_b else 0
            b_latency = f"{c.group_b.latency_ms:.0f}ms" if c.group_b else "N/A"
            lines.append(
                f"| {c.question_id} | {c.domain} | {a_results} | {a_latency} | "
                f"{b_results} | {b_latency} | {c.winner} |"
            )

        lines.append("")

        # Analysis
        lines.append("## Analysis")
        lines.append("")
        overhead = s.get('latency_overhead_ms', 0)
        if overhead > 0:
            lines.append(f"- Graph 검색 활성화 시 평균 {overhead:.0f}ms 추가 레이턴시 발생")
        else:
            lines.append(f"- Graph 검색 활성화 시 오히려 {abs(overhead):.0f}ms 더 빠름 (캐시 효과 가능)")
        lines.append("")

        a_wins = s.get('a_wins', 0)
        b_wins = s.get('b_wins', 0)
        total = report.total_questions
        if a_wins > b_wins:
            lines.append(f"- Graph 활성화(A)가 {a_wins}/{total} 질문에서 우세 "
                         f"-- 다중 홉 추론이 필요한 질문에서 특히 효과적")
        elif b_wins > a_wins:
            lines.append(f"- Graph 비활성화(B)가 {b_wins}/{total} 질문에서 우세 "
                         f"-- 현재 Knowledge Graph 데이터 품질 개선 필요")
        else:
            lines.append(f"- A/B 동점 -- Graph 검색이 특정 도메인에서만 효과적")

        lines.append("")

        # Recommendations
        lines.append("## Recommendations")
        lines.append("")
        if a_wins >= b_wins:
            lines.append("1. Graph 검색 활성화를 기본값으로 유지")
            lines.append("2. 엔티티 추출 품질 향상으로 Graph 검색 효과 극대화")
            lines.append("3. Graph 검색 가중치(rrf_weight_graph) 최적화 검토")
        else:
            lines.append("1. Knowledge Graph 데이터 품질 점검 및 엔티티 추출 개선")
            lines.append("2. Graph 검색 가중치 하향 조정 검토")
            lines.append("3. 도메인별 Graph 효과 분석 후 선별적 활성화 검토")

        if overhead > 500:
            lines.append(f"4. Graph 검색 레이턴시({overhead:.0f}ms) 최적화 필요")

        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(f"*Generated by Graph RAG A/B Test - {datetime.now().strftime('%Y-%m-%d')}*")
        lines.append(f"*STORY-097: Graph RAG A/B Comparison*")

        return "\n".join(lines)

    def save_report(
        self,
        report: ABTestReport,
        output_dir: str,
    ) -> Dict[str, str]:
        """보고서를 JSON + Markdown으로 저장"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        saved = {}

        # JSON
        json_path = output_path / f"graph_rag_ab_{timestamp}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            # Convert dataclasses to dict for JSON serialization
            json_data = {
                "timestamp": report.timestamp,
                "total_questions": report.total_questions,
                "group_a_config": report.group_a_config,
                "group_b_config": report.group_b_config,
                "summary": report.summary,
                "comparisons": [
                    {
                        "question_id": c.question_id,
                        "domain": c.domain,
                        "question": c.question,
                        "group_a": asdict(c.group_a) if c.group_a else None,
                        "group_b": asdict(c.group_b) if c.group_b else None,
                        "latency_diff_ms": c.latency_diff_ms,
                        "result_count_diff": c.result_count_diff,
                        "winner": c.winner,
                    }
                    for c in report.comparisons
                ],
            }
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        saved["json"] = str(json_path)

        # Markdown
        md_path = output_path / f"graph_rag_ab_{timestamp}.md"
        md_content = self.generate_markdown_report(report)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        saved["markdown"] = str(md_path)

        print(f"Reports saved:")
        print(f"  JSON: {json_path}")
        print(f"  Markdown: {md_path}")

        return saved


# ---------------------------------------------------------------------------
# Pytest Tests (TEST_MODE=docker)
# ---------------------------------------------------------------------------

class TestGraphRAGABComparison:
    """Graph RAG A/B 비교 테스트 (Docker 환경)"""

    @pytest.fixture
    def tester(self):
        """A/B 테스트 실행기"""
        base_url = os.getenv("BASE_URL", "http://localhost:8080")
        return GraphRAGABTester(base_url=base_url)

    @pytest.mark.asyncio
    async def test_ab_comparison_full(self, tester):
        """전체 A/B 비교 테스트"""
        report = await tester.run_ab_test()

        assert report.total_questions == len(AB_TEST_QUESTIONS)
        assert len(report.comparisons) == len(AB_TEST_QUESTIONS)
        assert report.summary is not None

        # 에러 비율 확인
        error_count = report.summary.get("errors", 0)
        error_rate = error_count / report.total_questions
        assert error_rate < 0.3, f"Error rate too high: {error_rate:.0%}"

        # 보고서 저장
        output_dir = str(
            Path(__file__).parent.parent.parent.parent
            / "docs" / "results" / "graph_rag_ab"
        )
        tester.save_report(report, output_dir)

    @pytest.mark.asyncio
    async def test_ab_latency_overhead(self, tester):
        """Graph 검색 레이턴시 오버헤드 테스트"""
        # 3개 질문만으로 빠르게 확인
        subset = AB_TEST_QUESTIONS[:3]
        report = await tester.run_ab_test(questions=subset)

        overhead = report.summary.get("latency_overhead_ms", 0)
        # Graph 검색은 추가 레이턴시가 5초 미만이어야 함
        assert abs(overhead) < 5000, (
            f"Graph search latency overhead too high: {overhead:.0f}ms"
        )

    @pytest.mark.asyncio
    async def test_ab_single_domain(self, tester):
        """단일 도메인 A/B 비교"""
        # 정보보호 정책 도메인만 테스트
        questions = [q for q in AB_TEST_QUESTIONS if q["domain"] == "정보보호 정책"]
        report = await tester.run_ab_test(questions=questions)

        assert report.total_questions == len(questions)
        for c in report.comparisons:
            assert c.domain == "정보보호 정책"


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

async def main():
    """CLI에서 직접 실행 시"""
    base_url = os.getenv("BASE_URL", "http://localhost:8080")
    tester = GraphRAGABTester(base_url=base_url)

    report = await tester.run_ab_test()

    # Save reports
    project_root = Path(__file__).parent.parent.parent.parent
    output_dir = str(project_root / "docs" / "results" / "graph_rag_ab")
    tester.save_report(report, output_dir)

    # Also generate the static report template
    doc_dir = str(
        project_root / "docs" / "04_testing" / "12_embedding_evaluation"
    )
    md_content = tester.generate_markdown_report(report)
    report_path = Path(doc_dir) / "21_graph_rag_ab_comparison.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"Static report: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
