#!/usr/bin/env python3
"""
개발 서버 실행 스크립트

Usage:
    python -m scripts.run_server
    python -m scripts.run_server --host 0.0.0.0 --port 8000
"""

import argparse
import uvicorn


def main():
    """서버 실행"""
    parser = argparse.ArgumentParser(description="Knowledge Service 개발 서버")
    parser.add_argument("--host", default="0.0.0.0", help="호스트 주소")
    parser.add_argument("--port", type=int, default=8000, help="포트 번호")
    parser.add_argument("--reload", action="store_true", help="자동 리로드 활성화")
    parser.add_argument("--workers", type=int, default=1, help="워커 수")

    args = parser.parse_args()

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers,
        log_level="info",
    )


if __name__ == "__main__":
    main()
