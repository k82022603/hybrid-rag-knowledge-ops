"""
로깅 설정 모듈

JSON 포맷 로깅 및 컬러 로깅 지원
"""

import logging
import sys
from typing import Optional

from colorlog import ColoredFormatter

from app.core.config import settings


def setup_logging(
    level: Optional[str] = None,
    json_format: bool = False,
) -> logging.Logger:
    """
    애플리케이션 로깅 설정

    Args:
        level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: JSON 포맷 사용 여부

    Returns:
        설정된 로거 인스턴스
    """
    log_level = level or ("DEBUG" if settings.debug else "INFO")

    # 루트 로거 설정
    logger = logging.getLogger("knowledge_service")
    logger.setLevel(getattr(logging, log_level))

    # 기존 핸들러 제거
    logger.handlers.clear()

    # 콘솔 핸들러 생성
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level))

    if json_format:
        # JSON 포맷
        from pythonjsonlogger import jsonlogger

        json_formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(name)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(json_formatter)
    else:
        # 컬러 포맷
        color_formatter = ColoredFormatter(
            "%(log_color)s%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s%(reset)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red,bg_white",
            },
        )
        console_handler.setFormatter(color_formatter)

    logger.addHandler(console_handler)

    return logger


# 기본 로거 인스턴스
logger = setup_logging()


def get_logger(name: str) -> logging.Logger:
    """
    모듈별 로거 반환

    Args:
        name: 모듈명 (일반적으로 __name__ 사용)

    Returns:
        해당 모듈의 로거 인스턴스
    """
    return logging.getLogger(f"knowledge_service.{name}")
