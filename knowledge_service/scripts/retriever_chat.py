#!/usr/bin/env python3
"""
Hybrid RAG Retriever - Interactive Terminal Chat

터미널에서 대화형으로 Hybrid Search를 테스트할 수 있는 도구입니다.
검색어를 입력하면 결과를 보기 좋게 출력합니다.

Usage:
    python retriever_chat.py                    # 기본 (hybrid, top_k=5)
    python retriever_chat.py --type keyword     # 키워드 검색
    python retriever_chat.py --type semantic     # 시맨틱(벡터) 검색
    python retriever_chat.py --top_k 10         # 상위 10개 결과
    python retriever_chat.py --url http://host:8000  # 커스텀 AI Service URL

Author: Claude (Opus 4.6)
Date: 2026-02-06
"""

import argparse
import json
import os
import sys
import time
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from urllib.parse import urljoin


# ─── 색상 코드 ────────────────────────────────────────────────
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BG_BLUE = "\033[44m"
    BG_GREEN = "\033[42m"


def colorize(text, color):
    """ANSI 색상 적용 (NO_COLOR 환경변수로 비활성화 가능)"""
    if os.getenv("NO_COLOR"):
        return text
    return f"{color}{text}{Colors.RESET}"


# ─── API 클라이언트 ──────────────────────────────────────────
class RetrieverClient:
    """AI Service Hybrid Search API 클라이언트"""

    def __init__(self, base_url="http://localhost:8000", email="admin@example.com", password="admin1234"):
        self.base_url = base_url.rstrip("/")
        self.email = email
        self.password = password
        self.token = None

    def _request(self, method, path, data=None, headers=None):
        """HTTP 요청 실행"""
        url = f"{self.base_url}{path}"
        _headers = {"Content-Type": "application/json"}
        if headers:
            _headers.update(headers)
        if self.token:
            _headers["Authorization"] = f"Bearer {self.token}"

        body = json.dumps(data).encode("utf-8") if data else None
        req = Request(url, data=body, headers=_headers, method=method)

        start = time.time()
        resp = urlopen(req, timeout=30)
        elapsed = (time.time() - start) * 1000

        result = json.loads(resp.read().decode("utf-8"))
        return result, elapsed

    def authenticate(self):
        """AI Service JWT 토큰 발급"""
        data = {"email": self.email, "password": self.password}
        result, elapsed = self._request("POST", "/api/v1/auth/login", data)
        self.token = result.get("accessToken") or result.get("access_token")
        return elapsed

    def search(self, query, search_type="hybrid", top_k=5, filters=None):
        """검색 실행"""
        endpoints = {
            "hybrid": "/api/v1/search/hybrid",
            "keyword": "/api/v1/search/keyword",
            "semantic": "/api/v1/search/semantic",
            "graph": "/api/v1/search/hybrid",  # hybrid with useGraph=True, useVector=False
        }
        endpoint = endpoints.get(search_type, endpoints["hybrid"])
        payload = {"query": query, "top_k": top_k}
        if search_type == "graph":
            payload["useGraph"] = True
            payload["useVector"] = False
        if filters:
            payload["filters"] = filters
        return self._request("POST", endpoint, payload)

    def graph_explore(self, entity_name, depth=2, limit=50):
        """Neo4j 서브그래프 탐색"""
        payload = {"entity_name": entity_name, "depth": depth, "limit": limit}
        return self._request("POST", "/api/v1/graph/subgraph", payload)

    def health_check(self):
        """서비스 상태 확인"""
        try:
            result, elapsed = self._request("GET", "/api/v1/health")
            return True, elapsed
        except Exception as e:
            return False, str(e)


# ─── 출력 포매터 ─────────────────────────────────────────────
def print_banner():
    """시작 배너 출력"""
    banner = f"""
{colorize('=' * 60, Colors.CYAN)}
{colorize('  Hybrid RAG Retriever - Interactive Chat', Colors.BOLD + Colors.CYAN)}
{colorize('=' * 60, Colors.CYAN)}

{colorize('Commands:', Colors.YELLOW)}
  /help          이 도움말 표시
  /type <t>      검색 타입 변경 (hybrid|keyword|semantic|graph)
  /topk <n>      top_k 변경 (1~50)
  /graph <name>  Neo4j 서브그래프 탐색 (예: /graph LangGraph)
  /filter <k=v>  필터 추가 (예: document_type=pptx)
  /clear          필터 초기화
  /stats         현재 설정 표시
  /quit          종료 (Ctrl+C도 가능)

{colorize('Tips:', Colors.DIM)}
  - 검색어를 입력하면 바로 Hybrid Search 실행
  - 응답시간, 검색 소스(vector/keyword/graph), 점수가 함께 표시됩니다
  - /type graph 로 전환하면 Neo4j Knowledge Graph 기반 검색
"""
    print(banner)


def print_result(result, elapsed_ms, search_type):
    """검색 결과 출력"""
    results = result.get("results", [])
    total = result.get("total", len(results))
    cached = result.get("from_cache", False)

    # 헤더
    header_parts = [
        colorize(f"[{search_type.upper()}]", Colors.BG_BLUE + Colors.WHITE),
        colorize(f"{total}건", Colors.GREEN + Colors.BOLD),
        colorize(f"({elapsed_ms:.0f}ms)", Colors.YELLOW),
    ]
    if cached:
        header_parts.append(colorize("[CACHED]", Colors.MAGENTA))
    print(f"\n  {'  '.join(header_parts)}")
    print(colorize("  " + "─" * 56, Colors.DIM))

    if not results:
        print(colorize("  검색 결과가 없습니다.", Colors.DIM))
        return

    for i, item in enumerate(results, 1):
        score = item.get("score", 0)
        content = item.get("content", "").strip()
        metadata = item.get("metadata", {})
        title = metadata.get("title", "N/A")
        source = metadata.get("search_source", "unknown")
        doc_type = metadata.get("document_type", "")
        rrf_score = metadata.get("rrf_score", score)

        # 점수 색상
        if rrf_score >= 0.03:
            score_color = Colors.GREEN
        elif rrf_score >= 0.015:
            score_color = Colors.YELLOW
        else:
            score_color = Colors.RED

        # 소스 색상
        source_colors = {"vector": Colors.BLUE, "keyword": Colors.MAGENTA, "neo4j_graph": Colors.GREEN, "graph": Colors.GREEN}
        source_color = source_colors.get(source, Colors.MAGENTA)

        # 순위 헤더
        print(f"\n  {colorize(f'#{i}', Colors.BOLD + Colors.WHITE)}"
              f"  {colorize(f'{rrf_score:.4f}', score_color)}"
              f"  {colorize(f'[{source}]', source_color)}"
              f"  {colorize(title, Colors.CYAN)}"
              f"  {colorize(f'({doc_type})', Colors.DIM)}")

        # source_ranks 표시
        source_ranks = metadata.get("source_ranks", {})
        if source_ranks:
            ranks_str = ", ".join(f"{k}: #{v}" for k, v in source_ranks.items())
            print(f"     {colorize(f'Ranks: {ranks_str}', Colors.DIM)}")

        # 하이라이트 표시
        highlight = metadata.get("highlight", {})
        if highlight and highlight.get("text"):
            hl_text = highlight["text"][0].replace("<em>", colorize("", Colors.YELLOW + Colors.BOLD)).replace("</em>", colorize("", Colors.RESET))
            # 간단히 <em> 태그를 볼드로
            hl_clean = highlight["text"][0].replace("<em>", "**").replace("</em>", "**")
            print(f"     {colorize('Highlight:', Colors.DIM)} {hl_clean[:120]}")

        # 본문 미리보기 (최대 200자)
        preview = content[:200].replace("\n", " ")
        if len(content) > 200:
            preview += "..."
        print(f"     {colorize(preview, Colors.WHITE)}")

    print(colorize("\n  " + "─" * 56, Colors.DIM))


def print_stats(search_type, top_k, filters, base_url):
    """현재 설정 표시"""
    print(f"\n  {colorize('Current Settings:', Colors.YELLOW + Colors.BOLD)}")
    print(f"  URL:         {colorize(base_url, Colors.CYAN)}")
    print(f"  Search Type: {colorize(search_type, Colors.GREEN)}")
    print(f"  Top-K:       {colorize(str(top_k), Colors.GREEN)}")
    if filters:
        print(f"  Filters:     {colorize(json.dumps(filters), Colors.GREEN)}")
    else:
        print(f"  Filters:     {colorize('(none)', Colors.DIM)}")
    print()


# ─── 메인 루프 ──────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Hybrid RAG Retriever - Interactive Terminal Chat",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python retriever_chat.py                        # 기본 실행
  python retriever_chat.py --type semantic        # 벡터 검색만
  python retriever_chat.py --top_k 10             # 상위 10개
  python retriever_chat.py --url http://host:8000 # 원격 서버
        """,
    )
    parser.add_argument("--url", default="http://localhost:8000", help="AI Service URL (default: http://localhost:8000)")
    parser.add_argument("--type", default="hybrid", choices=["hybrid", "keyword", "semantic", "graph"], help="검색 타입 (default: hybrid)")
    parser.add_argument("--top_k", type=int, default=5, help="결과 개수 (default: 5)")
    parser.add_argument("--email", default="admin@example.com", help="AI Service 이메일 (default: admin@example.com)")
    parser.add_argument("--password", default="admin1234", help="AI Service 비밀번호 (default: admin1234)")
    args = parser.parse_args()

    search_type = args.type
    top_k = args.top_k
    filters = {}
    client = RetrieverClient(args.url, args.email, args.password)

    # 서비스 상태 확인
    print(colorize("\n  Connecting to AI Service...", Colors.DIM))
    ok, health_ms = client.health_check()
    if not ok:
        print(colorize(f"  ERROR: AI Service에 연결할 수 없습니다 ({args.url})", Colors.RED))
        print(colorize(f"  상세: {health_ms}", Colors.DIM))
        print(colorize("  Docker가 실행 중인지 확인하세요: docker ps | grep ai-service", Colors.DIM))
        sys.exit(1)
    print(colorize(f"  Connected! (health: {health_ms:.0f}ms)", Colors.GREEN))

    # 인증
    try:
        auth_ms = client.authenticate()
        print(colorize(f"  Authenticated! (token: {auth_ms:.0f}ms)", Colors.GREEN))
    except HTTPError as e:
        print(colorize(f"  ERROR: 인증 실패 - {e.code} {e.reason}", Colors.RED))
        sys.exit(1)

    print_banner()

    # 대화 루프
    while True:
        try:
            prompt = colorize(f"[{search_type}|k={top_k}]", Colors.CYAN + Colors.BOLD)
            user_input = input(f"\n  {prompt} {colorize('>', Colors.GREEN)} ").strip()

            if not user_input:
                continue

            # 명령어 처리
            if user_input.startswith("/"):
                parts = user_input.split(maxsplit=1)
                cmd = parts[0].lower()
                arg = parts[1].strip() if len(parts) > 1 else ""

                if cmd == "/quit" or cmd == "/exit" or cmd == "/q":
                    print(colorize("\n  Goodbye!\n", Colors.CYAN))
                    break
                elif cmd == "/help":
                    print_banner()
                elif cmd == "/type":
                    if arg in ("hybrid", "keyword", "semantic", "graph"):
                        search_type = arg
                        print(colorize(f"  Search type -> {search_type}", Colors.GREEN))
                    else:
                        print(colorize("  Usage: /type <hybrid|keyword|semantic|graph>", Colors.RED))
                elif cmd == "/graph":
                    if not arg:
                        print(colorize("  Usage: /graph <entity_name>  (예: /graph LangGraph)", Colors.RED))
                    else:
                        try:
                            result, elapsed = client.graph_explore(arg)
                            nodes = result.get("nodes", [])
                            edges = result.get("edges", [])
                            center = result.get("center", arg)
                            print(f"\n  {colorize('[GRAPH EXPLORE]', Colors.BG_GREEN + Colors.WHITE)}"
                                  f"  {colorize(center, Colors.BOLD + Colors.CYAN)}"
                                  f"  {colorize(f'({elapsed:.0f}ms)', Colors.YELLOW)}")
                            print(colorize(f"  Nodes: {len(nodes)}, Edges: {len(edges)}", Colors.GREEN))
                            for i, node in enumerate(nodes[:10], 1):
                                name = node.get("name", node.get("value", node.get("knowledge_id", "?")))
                                desc = node.get("description", "")[:80]
                                print(f"    {colorize(f'#{i}', Colors.DIM)} {colorize(str(name), Colors.CYAN)}"
                                      f"  {colorize(desc, Colors.WHITE)}")
                            if len(nodes) > 10:
                                print(colorize(f"    ... 외 {len(nodes) - 10}개 노드", Colors.DIM))
                        except HTTPError as e:
                            body = e.read().decode("utf-8", errors="replace")
                            print(colorize(f"  Graph Error: {e.code} - {body[:200]}", Colors.RED))
                        except URLError as e:
                            print(colorize(f"  Connection Error: {e.reason}", Colors.RED))
                elif cmd == "/topk":
                    try:
                        n = int(arg)
                        if 1 <= n <= 50:
                            top_k = n
                            print(colorize(f"  top_k -> {top_k}", Colors.GREEN))
                        else:
                            print(colorize("  top_k는 1~50 범위로 입력하세요", Colors.RED))
                    except ValueError:
                        print(colorize("  Usage: /topk <number>", Colors.RED))
                elif cmd == "/filter":
                    if "=" in arg:
                        k, v = arg.split("=", 1)
                        filters[k.strip()] = v.strip()
                        print(colorize(f"  Filter added: {k.strip()}={v.strip()}", Colors.GREEN))
                    else:
                        print(colorize("  Usage: /filter <key=value>", Colors.RED))
                elif cmd == "/clear":
                    filters = {}
                    print(colorize("  Filters cleared", Colors.GREEN))
                elif cmd == "/stats":
                    print_stats(search_type, top_k, filters, args.url)
                else:
                    print(colorize(f"  Unknown command: {cmd}. Type /help for commands.", Colors.RED))
                continue

            # 검색 실행
            try:
                result, elapsed = client.search(user_input, search_type, top_k, filters or None)
                print_result(result, elapsed, search_type)
            except HTTPError as e:
                body = e.read().decode("utf-8", errors="replace")
                print(colorize(f"  Search Error: {e.code} - {body[:200]}", Colors.RED))
            except URLError as e:
                print(colorize(f"  Connection Error: {e.reason}", Colors.RED))
                print(colorize("  서비스 연결을 확인하세요.", Colors.DIM))

        except KeyboardInterrupt:
            print(colorize("\n\n  Goodbye!\n", Colors.CYAN))
            break
        except EOFError:
            print(colorize("\n\n  Goodbye!\n", Colors.CYAN))
            break


if __name__ == "__main__":
    main()
