"""
BGE Reranker v2 M3

BAAI/bge-reranker-v2-m3 기반 크로스 인코더 리랭커입니다.
쿼리-문서 쌍의 관련성 점수를 계산하여 검색 결과를 재순위화합니다.

특징:
    - 크로스 인코더 기반 정밀 관련성 점수 (0~1)
    - 다국어 지원 (한국어 포함)
    - 배치 처리 최적화 (batch_size=32)
    - CPU/GPU 자동 감지
    - 입력 최대 길이: 512 토큰
    - ONNX Runtime 지원으로 CPU 2~5x 속도 향상 (SCRUM-102)
    - asyncio.to_thread() 래핑으로 이벤트루프 비블로킹 (STORY-052)

Architecture:
    RRF 융합 후 reranking 단계에서 사용됩니다.
    HybridRetriever -> RRF Fusion -> BGE Reranker -> 최종 결과

STORY-032: BGE Reranker 통합 구현
STORY-052: Reranker async 전환 (asyncio.to_thread 래핑)
SCRUM-102: ONNX Runtime 최적화 (CPU 추론 가속)
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Rerank 결과 데이터 모델
# ---------------------------------------------------------------------------


@dataclass
class RerankResult:
    """
    리랭킹 결과 데이터 모델

    Attributes:
        doc_id: 문서(청크) 고유 식별자
        content: 문서(청크) 내용
        score: 리랭킹 점수 (0~1, sigmoid 정규화)
        original_score: 리랭킹 이전 원본 점수 (RRF 등)
        rank: 리랭킹 후 순위 (0-based)
        metadata: 추가 메타데이터 딕셔너리
    """

    doc_id: str
    content: str
    score: float = 0.0
    original_score: float = 0.0
    rank: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return (
            f"RerankResult(doc_id='{self.doc_id}', "
            f"score={self.score:.6f}, "
            f"original_score={self.original_score:.6f}, "
            f"rank={self.rank})"
        )


# ---------------------------------------------------------------------------
# BGE Reranker
# ---------------------------------------------------------------------------


class BGEReranker:
    """
    BGE Reranker v2 M3

    BAAI/bge-reranker-v2-m3 모델을 사용한 크로스 인코더 기반 리랭커입니다.
    쿼리와 문서 쌍의 관련성을 정밀하게 측정하여 검색 결과를 재순위화합니다.

    Args:
        model_name: HuggingFace 모델 이름 (기본: BAAI/bge-reranker-v2-m3, STORY-115)
        device: 연산 디바이스 ('cpu', 'cuda', None=자동감지)
        batch_size: 배치 처리 크기 (기본: 32)
        max_length: 입력 최대 토큰 수 (기본: 512)

    Attributes:
        model_name: 사용 중인 모델 이름
        device: 현재 디바이스 문자열
        batch_size: 배치 크기
        max_length: 최대 토큰 길이
        is_loaded: 모델 로딩 완료 여부

    Example:
        >>> reranker = BGEReranker()
        >>> await reranker.load_model()
        >>> results = await reranker.rerank(
        ...     query="Python FastAPI 사용법",
        ...     documents=[
        ...         {"doc_id": "1", "content": "FastAPI는 Python 웹 프레임워크입니다."},
        ...         {"doc_id": "2", "content": "Java Spring Boot 가이드"},
        ...     ],
        ...     top_k=1,
        ... )
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-v2-m3",
        device: Optional[str] = None,
        batch_size: int = 32,
        max_length: int = 512,
    ):
        """
        초기화

        Args:
            model_name: HuggingFace 모델 이름
            device: 연산 디바이스 (None이면 자동 감지)
            batch_size: 배치 처리 크기
            max_length: 입력 최대 토큰 수

        Raises:
            ValueError: batch_size가 0 이하이거나 max_length가 0 이하인 경우
        """
        if batch_size <= 0:
            raise ValueError(f"batch_size must be positive, got {batch_size}")
        if max_length <= 0:
            raise ValueError(f"max_length must be positive, got {max_length}")

        self.model_name = model_name
        self.batch_size = batch_size
        self.max_length = max_length

        # 디바이스 자동 감지
        self.device = device or self._detect_device()

        # 모델/토크나이저 (lazy loading)
        self._model: Optional[Any] = None
        self._tokenizer: Optional[Any] = None

        # SCRUM-102: ONNX Runtime 세션 (PyTorch 대체)
        self._onnx_session: Optional[Any] = None
        self._use_onnx: bool = False
        self._onnx_cache_dir = Path(
            os.environ.get("TRANSFORMERS_CACHE", "/app/.cache/huggingface")
        ).parent / "onnx"

        logger.info(
            "BGEReranker initialized - model=%s, device=%s, "
            "batch_size=%d, max_length=%d",
            self.model_name, self.device, self.batch_size, self.max_length,
        )

    @property
    def is_loaded(self) -> bool:
        """모델 로딩 완료 여부 (PyTorch 또는 ONNX)"""
        if self._use_onnx:
            return self._onnx_session is not None and self._tokenizer is not None
        return self._model is not None and self._tokenizer is not None

    # ------------------------------------------------------------------
    # Model Loading
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_device() -> str:
        """
        사용 가능한 디바이스 자동 감지

        Returns:
            'cuda' (NVIDIA GPU 사용 가능) 또는 'cpu'
        """
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
        except (ImportError, OSError):
            pass
        return "cpu"

    async def load_model(self) -> None:
        """
        모델 및 토크나이저 로딩

        SCRUM-102: ONNX Runtime을 우선 시도, 실패 시 PyTorch fallback.
        ONNX 모델이 캐시에 없으면 PyTorch 모델에서 자동 변환합니다.

        Raises:
            RuntimeError: 모델 로딩 실패
        """
        if self.is_loaded:
            return

        logger.info("Loading reranker model: %s (device=%s)", self.model_name, self.device)
        start_time = time.monotonic()

        try:
            from transformers import AutoTokenizer
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)

            # SCRUM-102: ONNX Runtime 우선 시도
            if self._try_load_onnx():
                elapsed_ms = (time.monotonic() - start_time) * 1000
                logger.info(
                    "Reranker ONNX model loaded in %.1fms",
                    elapsed_ms,
                )
                return

            # Fallback: PyTorch 모델 로딩
            import torch
            from transformers import AutoModelForSequenceClassification

            self._model = AutoModelForSequenceClassification.from_pretrained(
                self.model_name
            )
            self._model.to(self.device)
            self._model.eval()

            # ONNX 변환 시도 (백그라운드, 실패해도 무시)
            self._try_export_onnx()

            elapsed_ms = (time.monotonic() - start_time) * 1000
            logger.info(
                "Reranker PyTorch model loaded in %.1fms (device=%s)",
                elapsed_ms, self.device,
            )

        except Exception as e:
            self._model = None
            self._tokenizer = None
            self._onnx_session = None
            logger.error("Failed to load reranker model: %s", e)
            raise RuntimeError(f"Reranker model loading failed: {e}") from e

    def _try_load_onnx(self) -> bool:
        """
        ONNX 모델 로딩 시도

        SCRUM-102: 캐시된 ONNX 모델이 있으면 ONNX Runtime으로 로딩.
        STORY-096: HuggingFace Hub의 사전 양자화된 ONNX 모델도 지원
        (예: hooman650/bge-reranker-v2-m3-onnx-o4).

        검색 순서:
        1. 로컬 캐시 디렉토리 ({onnx_cache_dir}/{model_name}.onnx)
        2. HuggingFace Hub에서 ONNX 파일 다운로드 (model.onnx 또는 model_quantized.onnx)

        Returns:
            True: ONNX 로딩 성공, False: 실패 (PyTorch fallback 필요)
        """
        try:
            import onnxruntime as ort

            onnx_path = self._find_onnx_path()
            if onnx_path is None:
                return False

            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            # P1-2: 최대 2코어로 제한하여 전체 CPU 점유 방지
            # (healthcheck 응답 불가 → 컨테이너 재시작 문제 해소)
            sess_options.intra_op_num_threads = min(max(os.cpu_count() or 1, 1), 2)
            sess_options.inter_op_num_threads = 1

            self._onnx_session = ort.InferenceSession(
                str(onnx_path),
                sess_options,
                providers=["CPUExecutionProvider"],
            )
            self._use_onnx = True
            logger.info("ONNX Runtime session loaded: %s", onnx_path)
            return True

        except ImportError:
            logger.debug("onnxruntime not installed, skipping ONNX")
            return False
        except Exception as e:
            logger.warning("ONNX model load failed, using PyTorch: %s", e)
            self._onnx_session = None
            self._use_onnx = False
            return False

    def _find_onnx_path(self) -> Optional[Path]:
        """ONNX 모델 파일 경로를 검색

        검색 순서:
        1. 로컬 캐시 디렉토리 (self-exported)
        2. HuggingFace Hub에서 다운로드 (사전 양자화 모델)

        Returns:
            ONNX 모델 파일 경로 또는 None
        """
        # 1. 로컬 캐시 디렉토리 (기존 self-export 방식)
        local_path = self._onnx_cache_dir / f"{self.model_name.replace('/', '_')}.onnx"
        if local_path.exists():
            logger.debug("Found local ONNX cache: %s", local_path)
            return local_path

        # 2. HuggingFace Hub에서 ONNX 파일 다운로드 시도
        # 사전 양자화된 모델(예: hooman650/bge-reranker-v2-m3-onnx-o4)은
        # 리포지토리에 .onnx 파일이 직접 포함되어 있음
        try:
            from huggingface_hub import hf_hub_download

            # 일반적인 ONNX 파일명 패턴 시도
            for onnx_filename in [
                "model_quantized.onnx",  # INT8 양자화 모델
                "model_optimized.onnx",  # 최적화 모델
                "model.onnx",            # 기본 ONNX 모델
                "onnx/model.onnx",       # 서브디렉토리
            ]:
                try:
                    downloaded_path = hf_hub_download(
                        repo_id=self.model_name,
                        filename=onnx_filename,
                    )
                    logger.info(
                        "Downloaded ONNX model from HuggingFace Hub: %s/%s",
                        self.model_name, onnx_filename,
                    )
                    return Path(downloaded_path)
                except Exception:
                    continue

        except ImportError:
            logger.debug("huggingface_hub not available for ONNX download")
        except Exception as e:
            logger.debug("HuggingFace Hub ONNX download failed: %s", e)

        return None

    def _try_export_onnx(self) -> None:
        """
        PyTorch 모델을 ONNX로 변환 (일회성, 이후 ONNX 캐시 사용)

        SCRUM-102: 최초 1회만 실행되며, 변환된 모델은 캐시 디렉토리에 저장.
        변환 실패 시 PyTorch를 계속 사용.
        """
        try:
            import onnxruntime  # noqa: F401 - 설치 확인
            import torch

            if self._model is None or self._tokenizer is None:
                return

            onnx_path = self._onnx_cache_dir / f"{self.model_name.replace('/', '_')}.onnx"
            if onnx_path.exists():
                return

            self._onnx_cache_dir.mkdir(parents=True, exist_ok=True)

            # 더미 입력 생성 (모델에 맞는 입력 키 자동 감지)
            dummy_input = self._tokenizer(
                [["query", "document"]],
                padding=True,
                truncation=True,
                max_length=self.max_length,
                return_tensors="pt",
            )
            input_names = list(dummy_input.keys())
            dynamic_axes = {name: {0: "batch", 1: "seq"} for name in input_names}
            dynamic_axes["logits"] = {0: "batch"}

            export_start = time.monotonic()

            # ONNX export (opset 18: PyTorch 2.5+ 권장)
            torch.onnx.export(
                self._model,
                tuple(dummy_input.values()),
                str(onnx_path),
                input_names=input_names,
                output_names=["logits"],
                dynamic_axes=dynamic_axes,
                opset_version=18,
                do_constant_folding=True,
            )

            export_ms = (time.monotonic() - export_start) * 1000
            onnx_size_mb = onnx_path.stat().st_size / (1024 * 1024)
            logger.info(
                "ONNX model exported: %s (%.1fMB, %.1fms)",
                onnx_path, onnx_size_mb, export_ms,
            )

            # 바로 ONNX 세션으로 전환
            if self._try_load_onnx():
                # ONNX 로딩 성공 → PyTorch 모델 해제하여 메모리 절약
                self._model = None
                torch.cuda.empty_cache() if torch.cuda.is_available() else None
                logger.info("Switched to ONNX Runtime, PyTorch model released")

        except ImportError:
            logger.debug("onnxruntime not installed, skipping ONNX export")
        except Exception as e:
            logger.warning("ONNX export failed (non-critical): %s", e)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: Optional[int] = None,
    ) -> List[RerankResult]:
        """
        문서 재순위화 (async, non-blocking)

        CPU-intensive 모델 추론을 asyncio.to_thread()로 별도 스레드에서
        실행하여 이벤트루프를 블로킹하지 않습니다.
        배치 처리로 대량 문서를 효율적으로 처리합니다.

        STORY-052: asyncio.to_thread() 래핑으로 non-blocking 전환

        Args:
            query: 검색 쿼리 문자열
            documents: 재순위화할 문서 목록.
                각 문서는 최소 'content' 키를 포함해야 합니다.
                선택적 키: 'doc_id', 'score', 'metadata'
            top_k: 반환할 상위 문서 수 (None이면 전체 반환)

        Returns:
            RerankResult 리스트 (점수 내림차순 정렬)

        Raises:
            RuntimeError: 모델이 로딩되지 않은 경우
            ValueError: query가 비어있는 경우

        Example:
            >>> results = await reranker.rerank(
            ...     query="RAG 파이프라인 구현",
            ...     documents=[
            ...         {"doc_id": "c1", "content": "RAG는 Retrieval Augmented Generation입니다."},
            ...         {"doc_id": "c2", "content": "Spring Boot 설정 가이드"},
            ...     ],
            ...     top_k=1,
            ... )
            >>> results[0].doc_id
            'c1'
        """
        # 빈 입력 처리
        if not documents:
            return []

        if not query or not query.strip():
            logger.warning("Empty query provided to reranker")
            return []

        # 모델 로딩 확인
        if not self.is_loaded:
            await self.load_model()

        start_time = time.monotonic()

        # STORY-052: CPU-intensive 모델 추론을 별도 스레드에서 실행
        # asyncio.to_thread()로 래핑하여 이벤트루프 비블로킹
        rerank_results = await asyncio.to_thread(
            self._sync_rerank, query, documents, top_k
        )

        elapsed_ms = (time.monotonic() - start_time) * 1000
        logger.info(
            "Reranking complete (async) - query='%s', docs=%d, top_k=%s, "
            "latency=%.1fms, top_score=%.4f",
            query[:50],
            len(documents),
            top_k,
            elapsed_ms,
            rerank_results[0].score if rerank_results else 0.0,
        )

        return rerank_results

    async def arerank_with_timeout(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: Optional[int] = None,
        timeout: float = 15.0,
    ) -> List[RerankResult]:
        """
        타임아웃 보호가 적용된 비동기 리랭킹

        지정된 timeout 내에 리랭킹이 완료되지 않으면 fallback으로
        원본 문서를 RerankResult로 변환하여 반환합니다.

        STORY-052: 타임아웃 보호 + fallback

        Args:
            query: 검색 쿼리 문자열
            documents: 재순위화할 문서 목록
            top_k: 반환할 상위 문서 수 (None이면 전체 반환)
            timeout: 최대 대기 시간 (초, 기본: 15.0)

        Returns:
            RerankResult 리스트 (타임아웃 시 원본 순서 기반 fallback)

        Example:
            >>> results = await reranker.arerank_with_timeout(
            ...     query="FastAPI 사용법",
            ...     documents=documents,
            ...     top_k=5,
            ...     timeout=10.0,
            ... )
        """
        try:
            return await asyncio.wait_for(
                self.rerank(query, documents, top_k),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            logger.error(
                "Reranking timed out after %.1fs - query='%s', docs=%d. "
                "Returning original order as fallback.",
                timeout, query[:50], len(documents),
            )
            return self._fallback_results(documents, top_k)

    async def rerank_search_results(
        self,
        query: str,
        search_results: List[Any],
        top_k: Optional[int] = None,
    ) -> List[Any]:
        """
        SearchResult 객체 리스트 리랭킹

        knowledge_service의 SearchResult (Pydantic 모델)을
        직접 리랭킹하여 반환합니다.

        Args:
            query: 검색 쿼리
            search_results: SearchResult 객체 리스트
                (chunk_id, content, score, metadata 속성 필요)
            top_k: 반환할 상위 결과 수

        Returns:
            리랭킹된 SearchResult 리스트 (score/metadata 업데이트됨)
        """
        if not search_results:
            return []

        # SearchResult -> dict 변환
        documents = []
        for sr in search_results:
            documents.append({
                "doc_id": getattr(sr, "chunk_id", ""),
                "content": getattr(sr, "content", ""),
                "score": getattr(sr, "score", 0.0),
                "metadata": getattr(sr, "metadata", {}),
                "document_id": getattr(sr, "document_id", ""),
                "source": getattr(sr, "source", ""),
            })

        # 리랭킹 수행
        reranked = await self.rerank(query, documents, top_k=top_k)

        # SearchResult 재구성
        result_map = {
            getattr(sr, "chunk_id", ""): sr for sr in search_results
        }

        updated_results = []
        for rr in reranked:
            original = result_map.get(rr.doc_id)
            if original is not None:
                # score와 metadata 업데이트
                original.score = rr.score
                original.metadata["rerank_score"] = rr.score
                original.metadata["rerank_rank"] = rr.rank
                original.metadata["original_score"] = rr.original_score
                updated_results.append(original)

        return updated_results

    # ------------------------------------------------------------------
    # Internal methods
    # ------------------------------------------------------------------

    def _sync_rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: Optional[int] = None,
    ) -> List[RerankResult]:
        """
        동기 리랭킹 (스레드 풀에서 실행)

        CPU-intensive 모델 추론을 포함하는 동기 메서드입니다.
        asyncio.to_thread()에 의해 별도 스레드에서 호출됩니다.

        STORY-052: rerank()에서 분리된 동기 전용 로직

        Args:
            query: 검색 쿼리 문자열
            documents: 재순위화할 문서 목록
            top_k: 반환할 상위 문서 수 (None이면 전체 반환)

        Returns:
            RerankResult 리스트 (점수 내림차순 정렬)
        """
        # 쿼리-문서 쌍 생성
        contents = [
            doc.get("content", "") for doc in documents
        ]
        pairs = [[query, content] for content in contents]

        # 배치 점수 계산 (CPU-intensive)
        scores = self._batch_process(pairs, self.batch_size)

        # RerankResult 생성 및 정렬
        rerank_results: List[RerankResult] = []
        for idx, (doc, score) in enumerate(zip(documents, scores)):
            rerank_results.append(
                RerankResult(
                    doc_id=doc.get("doc_id", doc.get("chunk_id", f"doc-{idx}")),
                    content=doc.get("content", ""),
                    score=score,
                    original_score=doc.get("score", 0.0),
                    metadata={
                        **doc.get("metadata", {}),
                        "rerank_score": score,
                        "original_score": doc.get("score", 0.0),
                    },
                )
            )

        # 점수 내림차순 정렬
        rerank_results.sort(key=lambda x: x.score, reverse=True)

        # 순위 할당
        for rank, result in enumerate(rerank_results):
            result.rank = rank

        # top_k 적용
        if top_k is not None and top_k > 0:
            rerank_results = rerank_results[:top_k]

        return rerank_results

    def _fallback_results(
        self,
        documents: List[Dict[str, Any]],
        top_k: Optional[int] = None,
    ) -> List[RerankResult]:
        """
        Fallback 결과 생성 (타임아웃/오류 시 원본 순서 유지)

        리랭킹 실패 시 원본 문서를 RerankResult 형태로 변환하여 반환합니다.
        원본 점수(score)를 rerank 점수로 사용합니다.

        STORY-052: 타임아웃 fallback용

        Args:
            documents: 원본 문서 목록
            top_k: 반환할 상위 문서 수 (None이면 전체 반환)

        Returns:
            RerankResult 리스트 (원본 순서 유지)
        """
        effective_top_k = top_k if (top_k is not None and top_k > 0) else len(documents)
        fallback_results: List[RerankResult] = []

        for idx, doc in enumerate(documents[:effective_top_k]):
            original_score = doc.get("score", 0.0)
            fallback_results.append(
                RerankResult(
                    doc_id=doc.get("doc_id", doc.get("chunk_id", f"doc-{idx}")),
                    content=doc.get("content", ""),
                    score=original_score,
                    original_score=original_score,
                    rank=idx,
                    metadata={
                        **doc.get("metadata", {}),
                        "rerank_fallback": True,
                        "original_score": original_score,
                    },
                )
            )

        return fallback_results

    def _compute_scores(self, pairs: List[List[str]]) -> List[float]:
        """
        쿼리-문서 쌍의 관련성 점수 계산

        SCRUM-102: ONNX Runtime 우선 사용, 실패 시 PyTorch fallback.
        크로스 인코더를 사용하여 각 쌍의 관련성 점수를 계산합니다.
        Sigmoid 함수로 0~1 범위로 정규화합니다.

        Args:
            pairs: [query, document] 쌍 리스트

        Returns:
            관련성 점수 리스트 (0~1 범위)

        Raises:
            RuntimeError: 모델 미로딩 상태
        """
        if not self.is_loaded:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        if not pairs:
            return []

        # SCRUM-102: ONNX Runtime 경로
        if self._use_onnx and self._onnx_session is not None:
            return self._compute_scores_onnx(pairs)

        # PyTorch 경로
        return self._compute_scores_pytorch(pairs)

    def _compute_scores_pytorch(self, pairs: List[List[str]]) -> List[float]:
        """PyTorch 모델로 점수 계산"""
        import torch

        with torch.no_grad():
            inputs = self._tokenizer(
                pairs,
                padding=True,
                truncation=True,
                max_length=self.max_length,
                return_tensors="pt",
            ).to(self.device)

            outputs = self._model(**inputs)

            logits = outputs.logits
            if logits.dim() > 1:
                logits = logits.squeeze(-1)
            scores = torch.sigmoid(logits)

            return scores.cpu().tolist()

    def _compute_scores_onnx(self, pairs: List[List[str]]) -> List[float]:
        """SCRUM-102: ONNX Runtime으로 점수 계산 (CPU 최적화)"""
        import numpy as np

        inputs = self._tokenizer(
            pairs,
            padding=True,
            truncation=True,
            max_length=self.max_length,
            return_tensors="np",
        )

        ort_inputs = {
            "input_ids": inputs["input_ids"].astype(np.int64),
            "attention_mask": inputs["attention_mask"].astype(np.int64),
        }
        # token_type_ids가 있으면 추가 (BERT 계열)
        if "token_type_ids" in inputs:
            ort_inputs["token_type_ids"] = inputs["token_type_ids"].astype(np.int64)

        outputs = self._onnx_session.run(None, ort_inputs)
        logits = outputs[0]

        # Sigmoid 정규화 (numpy)
        if logits.ndim > 1:
            logits = logits.squeeze(-1)
        scores = 1.0 / (1.0 + np.exp(-logits))

        return scores.tolist()

    def _batch_process(
        self,
        pairs: List[List[str]],
        batch_size: int,
    ) -> List[float]:
        """
        배치 단위 점수 계산

        대량의 쿼리-문서 쌍을 batch_size 단위로 나누어 처리합니다.
        메모리 효율성을 위해 배치별로 처리 후 결과를 합칩니다.

        Args:
            pairs: [query, document] 쌍 전체 리스트
            batch_size: 한 번에 처리할 쌍의 수

        Returns:
            전체 쌍에 대한 관련성 점수 리스트
        """
        if not pairs:
            return []

        all_scores: List[float] = []

        for i in range(0, len(pairs), batch_size):
            batch = pairs[i:i + batch_size]
            batch_scores = self._compute_scores(batch)
            all_scores.extend(batch_scores)

        return all_scores

    def health_check(self) -> Dict[str, Any]:
        """
        Reranker 상태 점검

        Returns:
            상태 정보 딕셔너리
        """
        return {
            "service": "BGEReranker",
            "model_name": self.model_name,
            "device": self.device,
            "is_loaded": self.is_loaded,
            "batch_size": self.batch_size,
            "max_length": self.max_length,
            "backend": "onnx" if self._use_onnx else "pytorch",
        }


# ---------------------------------------------------------------------------
# Singleton instance
# ---------------------------------------------------------------------------

_reranker: Optional[BGEReranker] = None


def get_reranker(
    model_name: Optional[str] = None,
    device: Optional[str] = None,
    batch_size: int = 32,
    max_length: int = 512,
) -> BGEReranker:
    """
    BGEReranker 싱글톤 인스턴스 반환

    모델명은 settings.reranker_model_name 환경변수로 설정 가능합니다.
    INT8 양자화 모델(예: hooman650/bge-reranker-v2-m3-onnx-o4)을 사용하면
    CPU 추론 2-4x 개선됩니다.

    Args:
        model_name: HuggingFace 모델 이름 (None이면 settings에서 로드)
        device: 연산 디바이스
        batch_size: 배치 처리 크기
        max_length: 입력 최대 토큰 수

    Returns:
        BGEReranker 싱글톤 인스턴스
    """
    global _reranker
    if _reranker is None:
        # config.py의 reranker_model_name 설정 우선 사용
        if model_name is None:
            try:
                from app.core.config import settings
                model_name = settings.reranker_model_name
            except Exception:
                model_name = "BAAI/bge-reranker-v2-m3"
        _reranker = BGEReranker(
            model_name=model_name,
            device=device,
            batch_size=batch_size,
            max_length=max_length,
        )
    return _reranker


def reset_reranker() -> None:
    """싱글톤 인스턴스 초기화 (테스트용)"""
    global _reranker
    _reranker = None
