"""
RAGAS 평가 테스트 conftest

evaluation 테스트에 필요한 fixture와 설정을 정의합니다.
다른 모듈과의 의존성을 최소화하여 독립적으로 실행 가능합니다.

STORY-058: RAGAS 평가 프레임워크 통합
"""

import os
import sys
from pathlib import Path

import pytest

# src 디렉토리를 Python 경로에 추가
SRC_DIR = Path(__file__).parent.parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


# 환경변수 설정 (테스트용)
os.environ.setdefault("ENVIRONMENT", "test")


def pytest_configure(config):
    """pytest 설정"""
    # evaluation 마커 등록
    config.addinivalue_line(
        "markers", "evaluation: RAGAS evaluation tests - STORY-058"
    )


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """테스트 데이터 디렉토리 경로"""
    return Path(__file__).parent


@pytest.fixture(scope="session")
def test_dataset_path(test_data_dir: Path) -> str:
    """테스트 데이터셋 파일 경로"""
    return str(test_data_dir / "test_dataset.json")
