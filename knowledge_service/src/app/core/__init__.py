"""
Core module - 핵심 설정 및 유틸리티

- config: 환경 설정 관리 (pydantic-settings)
- logging: 로깅 설정
- exceptions: 사용자 정의 예외
"""

from app.core.config import settings

__all__ = ["settings"]
