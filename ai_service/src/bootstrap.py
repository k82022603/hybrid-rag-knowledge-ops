"""
RAG Pipeline Bootstrap

ai_service의 LangGraph 워크플로우에 실제 knowledge_service 구현체를
주입하여 완전한 RAG 파이프라인을 구성합니다.

Bootstrap 순서:
    1. LLMService 초기화 (DeepSeek V3.2)
    2. LLMAdapter 생성 (LangGraph 노드용)
    3. KnowledgeServiceClient 생성 (Direct 또는 HTTP 모드)
    4. RetrieverAdapter 생성 (RetrieverNode.retrieve_fn)
    5. RerankerAdapter 생성 (선택적)
    6. LangGraph 노드 생성 (Planner, Retriever, Generator, Validator)
    7. RAGWorkflow 조립

Architecture:
    ┌─────────────────────────────────────────────────────────────────┐
    │ bootstrap_rag_pipeline()                                        │
    │                                                                 │
    │  LLMService ──► LLMAdapter ──► PlannerNode                     │
    │                             ──► GeneratorNode                   │
    │                             ──► ValidatorNode                   │
    │                                                                 │
    │  HybridRetriever ──► KSClient ──► RetrieverAdapter             │
    │                                    ──► RetrieverNode            │
    │                                                                 │
    │  BGEReranker ──► RerankerAdapter (HybridRetriever 내장)        │
    │                                                                 │
    │  All Nodes ──► RAGWorkflow (StateGraph)                        │
    └─────────────────────────────────────────────────────────────────┘

STORY-051: RAG 파이프라인 통합
"""

import logging
import os
from typing import Any, Dict, Optional

from ai_service.src.adapters.knowledge_service_client import (
    ConnectionMode,
    KnowledgeServiceClient,
)
from ai_service.src.adapters.llm_adapter import LLMAdapter
from ai_service.src.adapters.reranker_adapter import RerankerAdapter
from ai_service.src.adapters.retriever_adapter import RetrieverAdapter
from ai_service.src.workflows.nodes.generator import GeneratorNode
from ai_service.src.workflows.nodes.planner import PlannerNode
from ai_service.src.workflows.nodes.retriever import RetrieverNode
from ai_service.src.workflows.nodes.validator import ValidatorNode
from ai_service.src.workflows.rag_workflow import RAGWorkflow

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pipeline Configuration
# ---------------------------------------------------------------------------

class PipelineConfig:
    """
    RAG 파이프라인 설정

    환경변수 및 기본값에서 파이프라인 설정을 로드합니다.

    Attributes:
        connection_mode: knowledge_service 연결 모드
        ks_base_url: knowledge_service HTTP URL (HTTP 모드)
        ks_timeout: HTTP 요청 타임아웃 (초)
        retrieval_top_k: 검색 결과 상위 K
        max_retries: 워크플로우 최대 재시도
        use_reasoner: Reasoner 모델 사용 여부
        reranking_enabled: 리랭킹 활성화 여부
        llm_fallback_enabled: LLM 폴백 응답 활성화 여부
    """

    def __init__(
        self,
        connection_mode: Optional[str] = None,
        ks_base_url: Optional[str] = None,
        ks_timeout: Optional[float] = None,
        retrieval_top_k: Optional[int] = None,
        max_retries: Optional[int] = None,
        use_reasoner: Optional[bool] = None,
        reranking_enabled: Optional[bool] = None,
        llm_fallback_enabled: Optional[bool] = None,
    ):
        """
        초기화

        환경변수에서 기본값을 로드하되, 명시적 인자가 우선합니다.
        """
        self.connection_mode = ConnectionMode(
            connection_mode
            or os.getenv("KS_CONNECTION_MODE", "direct")
        )
        self.ks_base_url = (
            ks_base_url
            or os.getenv("KS_BASE_URL", "http://localhost:8000")
        )
        self.ks_timeout = (
            ks_timeout
            if ks_timeout is not None
            else float(os.getenv("KS_TIMEOUT", "30.0"))
        )
        self.retrieval_top_k = (
            retrieval_top_k
            if retrieval_top_k is not None
            else int(os.getenv("RETRIEVAL_TOP_K", "10"))
        )
        self.max_retries = (
            max_retries
            if max_retries is not None
            else int(os.getenv("RAG_MAX_RETRIES", "2"))
        )
        self.use_reasoner = (
            use_reasoner
            if use_reasoner is not None
            else os.getenv("USE_REASONER", "false").lower() == "true"
        )
        self.reranking_enabled = (
            reranking_enabled
            if reranking_enabled is not None
            else os.getenv("RERANKING_ENABLED", "true").lower() == "true"
        )
        self.llm_fallback_enabled = (
            llm_fallback_enabled
            if llm_fallback_enabled is not None
            else os.getenv("LLM_FALLBACK_ENABLED", "true").lower() == "true"
        )

    def to_dict(self) -> Dict[str, Any]:
        """설정 딕셔너리 반환"""
        return {
            "connection_mode": self.connection_mode.value,
            "ks_base_url": self.ks_base_url,
            "ks_timeout": self.ks_timeout,
            "retrieval_top_k": self.retrieval_top_k,
            "max_retries": self.max_retries,
            "use_reasoner": self.use_reasoner,
            "reranking_enabled": self.reranking_enabled,
            "llm_fallback_enabled": self.llm_fallback_enabled,
        }


# ---------------------------------------------------------------------------
# Pipeline Result
# ---------------------------------------------------------------------------

class PipelineComponents:
    """
    부트스트랩 결과: 생성된 파이프라인 구성 요소

    Attributes:
        workflow: 완성된 RAGWorkflow 인스턴스
        llm_adapter: LLM 어댑터
        ks_client: Knowledge Service 클라이언트
        retriever_adapter: Retriever 어댑터
        reranker_adapter: Reranker 어댑터 (선택적)
        config: 사용된 설정
    """

    def __init__(
        self,
        workflow: RAGWorkflow,
        llm_adapter: LLMAdapter,
        ks_client: KnowledgeServiceClient,
        retriever_adapter: RetrieverAdapter,
        reranker_adapter: Optional[RerankerAdapter] = None,
        config: Optional[PipelineConfig] = None,
    ):
        self.workflow = workflow
        self.llm_adapter = llm_adapter
        self.ks_client = ks_client
        self.retriever_adapter = retriever_adapter
        self.reranker_adapter = reranker_adapter
        self.config = config

    def health_check(self) -> Dict[str, Any]:
        """전체 파이프라인 상태 점검"""
        health: Dict[str, Any] = {
            "service": "RAGPipeline",
            "status": "healthy",
            "config": self.config.to_dict() if self.config else {},
        }

        health["llm_adapter"] = self.llm_adapter.health_check()
        health["ks_client"] = self.ks_client.health_check()
        health["retriever_adapter"] = self.retriever_adapter.health_check()

        if self.reranker_adapter:
            health["reranker_adapter"] = self.reranker_adapter.health_check()

        health["workflow"] = self.workflow.get_graph_info()

        return health

    async def close(self) -> None:
        """리소스 정리"""
        await self.ks_client.close()
        logger.info("PipelineComponents resources closed")


# ---------------------------------------------------------------------------
# Bootstrap Functions
# ---------------------------------------------------------------------------

def bootstrap_rag_pipeline(
    config: Optional[PipelineConfig] = None,
    llm_service: Optional[Any] = None,
    hybrid_retriever: Optional[Any] = None,
    search_service: Optional[Any] = None,
    reranker: Optional[Any] = None,
) -> PipelineComponents:
    """
    RAG 파이프라인 부트스트랩

    모든 구성 요소를 초기화하고 연결하여 완전한 RAGWorkflow를 생성합니다.

    Args:
        config: 파이프라인 설정 (None이면 환경변수에서 로드)
        llm_service: LLMService 인스턴스 (None이면 싱글톤 사용)
        hybrid_retriever: HybridRetriever 인스턴스 (Direct 모드, None이면 싱글톤)
        search_service: SearchService 인스턴스 (Direct 모드)
        reranker: BGEReranker 인스턴스 (None이면 비활성화)

    Returns:
        PipelineComponents: 생성된 파이프라인 구성 요소

    Example:
        >>> components = bootstrap_rag_pipeline()
        >>> result = await components.workflow.invoke("FastAPI 사용법은?")
        >>> print(result["answer"])

        >>> # 커스텀 설정
        >>> config = PipelineConfig(
        ...     connection_mode="http",
        ...     ks_base_url="http://knowledge-svc:8000",
        ... )
        >>> components = bootstrap_rag_pipeline(config=config)
    """
    if config is None:
        config = PipelineConfig()

    logger.info(
        "Bootstrapping RAG pipeline - %s", config.to_dict(),
    )

    # Step 1: LLMService 초기화
    if llm_service is None:
        llm_service = _get_llm_service()

    # Step 2: LLMAdapter 생성
    llm_adapter = LLMAdapter(
        llm_service=llm_service,
        use_reasoner=config.use_reasoner,
        fallback_enabled=config.llm_fallback_enabled,
    )

    # Step 3: KnowledgeServiceClient 생성
    ks_client = KnowledgeServiceClient(
        mode=config.connection_mode,
        base_url=config.ks_base_url,
        timeout=config.ks_timeout,
        hybrid_retriever=hybrid_retriever,
        search_service=search_service,
    )

    # Step 4: RetrieverAdapter 생성
    retriever_adapter = RetrieverAdapter(
        client=ks_client,
        default_top_k=config.retrieval_top_k,
    )

    # Step 5: RerankerAdapter 생성 (선택적)
    reranker_adapter: Optional[RerankerAdapter] = None
    if config.reranking_enabled and reranker is not None:
        reranker_adapter = RerankerAdapter(
            reranker=reranker,
            client=ks_client,
            default_top_k=config.retrieval_top_k,
        )

    # Step 6: LangGraph 노드 생성
    planner_node = PlannerNode(
        llm_call=llm_adapter.call,
    )
    retriever_node = RetrieverNode(
        retrieve_fn=retriever_adapter.retrieve,
        top_k=config.retrieval_top_k,
    )
    generator_node = GeneratorNode(
        llm_call=llm_adapter.call,
        llm_stream=llm_adapter.stream,
    )
    validator_node = ValidatorNode(
        llm_call=llm_adapter.call,
    )

    # Step 7: RAGWorkflow 조립
    workflow = RAGWorkflow(
        planner=planner_node,
        retriever=retriever_node,
        generator=generator_node,
        validator=validator_node,
        max_retries=config.max_retries,
    )

    logger.info(
        "RAG pipeline bootstrapped successfully - "
        "mode=%s, top_k=%d, max_retries=%d, reranking=%s",
        config.connection_mode.value,
        config.retrieval_top_k,
        config.max_retries,
        reranker_adapter is not None,
    )

    return PipelineComponents(
        workflow=workflow,
        llm_adapter=llm_adapter,
        ks_client=ks_client,
        retriever_adapter=retriever_adapter,
        reranker_adapter=reranker_adapter,
        config=config,
    )


def bootstrap_with_defaults() -> PipelineComponents:
    """
    기본 설정으로 RAG 파이프라인 부트스트랩

    knowledge_service의 싱글톤 인스턴스들을 사용합니다.
    개발/테스트 환경에서 간편하게 사용할 수 있습니다.

    Returns:
        PipelineComponents: 생성된 파이프라인 구성 요소
    """
    # knowledge_service 싱글톤 인스턴스 획득 시도
    hybrid_retriever = None
    search_service = None
    reranker = None

    try:
        from app.rag.retriever import get_hybrid_retriever
        hybrid_retriever = get_hybrid_retriever()
        logger.info("HybridRetriever singleton acquired")
    except ImportError:
        logger.warning(
            "knowledge_service not importable - "
            "HybridRetriever will be lazily resolved"
        )

    try:
        from ai_service.src.reranking.bge_reranker import get_reranker
        reranker = get_reranker()
        logger.info("BGEReranker singleton acquired")
    except Exception:
        logger.info("BGEReranker not available - reranking disabled")

    return bootstrap_rag_pipeline(
        hybrid_retriever=hybrid_retriever,
        search_service=search_service,
        reranker=reranker,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_llm_service() -> Any:
    """
    LLMService 싱글톤 인스턴스 획득

    Returns:
        LLMService 인스턴스

    Raises:
        RuntimeError: LLMService를 초기화할 수 없는 경우
    """
    try:
        from app.services.llm_service import get_llm_service
        return get_llm_service()
    except ImportError:
        logger.warning(
            "knowledge_service.llm_service not importable - "
            "creating standalone LLMService"
        )

    # 스탠드얼론 LLMService 생성 (knowledge_service 외부에서 실행 시)
    try:
        return _create_standalone_llm_service()
    except Exception as e:
        raise RuntimeError(
            f"Failed to initialize LLMService: {e}. "
            f"Ensure DEEPSEEK_API_KEY is set."
        ) from e


def _create_standalone_llm_service() -> Any:
    """
    독립 실행용 LLMService 생성

    knowledge_service를 임포트할 수 없는 환경에서
    최소한의 LLM 호출 기능을 제공합니다.

    Returns:
        StandaloneLLMService 인스턴스
    """
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError(
            "DEEPSEEK_API_KEY environment variable is not set. "
            "Set it to use DeepSeek V3.2 LLM."
        )

    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    chat_model = os.getenv("DEEPSEEK_CHAT_MODEL", "deepseek-chat")

    logger.info(
        "Creating standalone LLM service - model=%s, base_url=%s",
        chat_model, base_url,
    )

    return _StandaloneLLMService(
        api_key=api_key,
        base_url=base_url,
        chat_model=chat_model,
    )


class _StandaloneLLMService:
    """
    독립 실행용 LLM 서비스

    knowledge_service의 LLMService를 임포트할 수 없을 때
    최소한의 LLM 호출 기능을 제공합니다.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        chat_model: str = "deepseek-chat",
    ):
        self._api_key = api_key
        self._base_url = base_url
        self._chat_model = chat_model
        self._llm: Optional[Any] = None

    @property
    def llm(self) -> Any:
        """ChatOpenAI 인스턴스 (lazy loading)"""
        if self._llm is None:
            from langchain_openai import ChatOpenAI
            self._llm = ChatOpenAI(
                model=self._chat_model,
                base_url=self._base_url,
                api_key=self._api_key,
                temperature=0.0,
                max_tokens=4096,
                timeout=60,
            )
        return self._llm

    async def generate_with_messages(
        self,
        messages: list,
        use_reasoner: bool = False,
    ) -> str:
        """메시지 기반 LLM 호출"""
        response = await self.llm.ainvoke(messages)
        return response.content


# ---------------------------------------------------------------------------
# Singleton Pipeline
# ---------------------------------------------------------------------------

_pipeline_components: Optional[PipelineComponents] = None


def get_pipeline() -> PipelineComponents:
    """
    RAG 파이프라인 싱글톤 인스턴스 반환

    최초 호출 시 bootstrap_with_defaults()로 초기화합니다.

    Returns:
        PipelineComponents 싱글톤 인스턴스
    """
    global _pipeline_components
    if _pipeline_components is None:
        _pipeline_components = bootstrap_with_defaults()
    return _pipeline_components


def reset_pipeline() -> None:
    """싱글톤 초기화 (테스트용)"""
    global _pipeline_components
    _pipeline_components = None
