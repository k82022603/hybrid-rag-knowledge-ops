"""
Standalone Unit Test conftest

Heavy dependency mocking to enable tests without Docker containers.
This conftest runs before any test module to set up package mocks.
"""

import sys
from types import ModuleType
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Mock heavy packages before any app import
# ---------------------------------------------------------------------------

_MOCK_PACKAGES = [
    "langchain_openai",
    "langchain_core",
    "langchain_core.language_models",
    "langchain_core.language_models.chat_models",
    "langchain_core.messages",
    "langchain_core.prompts",
    "langchain_core.output_parsers",
    "langchain_community",
    "langchain",
    "langgraph",
    "langgraph.graph",
    "langgraph.prebuilt",
    "langgraph.checkpoint",
    "openai",
    "FlagEmbedding",
    "sentence_transformers",
    "transformers",
]
# elasticsearch, redis, neo4j, minio는 실제 설치된 패키지이므로 mock하지 않음
# (sys.modules 오염으로 다른 테스트 파일에 영향을 주기 때문)

for _pkg in _MOCK_PACKAGES:
    if _pkg not in sys.modules:
        sys.modules[_pkg] = MagicMock()

try:
    import torch  # noqa: F401
except (OSError, ImportError, ValueError):
    import importlib.machinery

    _torch_mock = ModuleType("torch")
    _torch_mock.__version__ = "2.0.0"
    _torch_mock.__spec__ = importlib.machinery.ModuleSpec("torch", None)
    _torch_mock.cuda = MagicMock()
    _torch_mock.cuda.is_available = MagicMock(return_value=False)
    _torch_mock.Tensor = MagicMock()
    _torch_mock.nn = MagicMock()
    _torch_mock.device = MagicMock()
    _torch_mock.dtype = MagicMock()
    _torch_mock.float32 = MagicMock()
    _torch_mock.float16 = MagicMock()
    _torch_mock.no_grad = MagicMock(
        return_value=MagicMock(__enter__=MagicMock(), __exit__=MagicMock())
    )
    sys.modules["torch"] = _torch_mock
    for submod in [
        "torch.nn",
        "torch.nn.functional",
        "torch.utils",
        "torch.utils.data",
        "torch.cuda",
        "torch.amp",
    ]:
        if submod not in sys.modules:
            sys.modules[submod] = MagicMock()


# Override parent conftest fixtures to avoid app.main import
@pytest.fixture(scope="session", autouse=True)
def setup_test_users():
    """Override parent: skip app.api.routes.auth import"""
    yield


@pytest.fixture(scope="function")
def client():
    """Override parent: provide None client for standalone tests"""
    return None


@pytest.fixture(scope="function")
async def async_client():
    """Override parent: provide None async client for standalone tests"""
    yield None
