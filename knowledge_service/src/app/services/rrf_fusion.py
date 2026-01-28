"""
RRF (Reciprocal Rank Fusion) 알고리즘 모듈

다중 검색 소스의 결과를 RRF 알고리즘으로 융합하는 독립 모듈입니다.
SearchService 내부의 _rrf_fusion 메서드를 대체/보완하여
가중치 기반 RRF, 융합 과정 설명 등 고급 기능을 제공합니다.

RRF 공식:
    RRF(d) = sum(weight_i * 1 / (k + rank_i + 1))

여기서:
    - k: 순위 안정화 상수 (기본값 60, 높을수록 하위 순위 영향 감소)
    - rank_i: 소스 i에서 문서 d의 순위 (0-based)
    - weight_i: 소스 i의 가중치

참고:
    - Cormack et al., "Reciprocal Rank Fusion outperforms Condorcet
      and individual Rank Learning Methods" (2009)

STORY-031: RRF Fusion 알고리즘 구현
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# RRF 결과 데이터클래스
# ---------------------------------------------------------------------------


@dataclass
class RRFResult:
    """
    RRF Fusion 결과를 나타내는 데이터클래스

    각 문서의 RRF 점수, 원본 소스별 점수, 메타데이터를 포함합니다.

    Attributes:
        doc_id: 문서(청크) 고유 식별자
        content: 문서(청크) 내용
        metadata: 원본 메타데이터 딕셔너리
        rrf_score: RRF 융합 점수 (가중치 적용)
        source_scores: 소스별 RRF 점수 딕셔너리
            예: {"es": 0.0164, "neo4j": 0.0161}
    """

    doc_id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    rrf_score: float = 0.0
    source_scores: Dict[str, float] = field(default_factory=dict)

    def __repr__(self) -> str:
        return (
            f"RRFResult(doc_id='{self.doc_id}', "
            f"rrf_score={self.rrf_score:.6f}, "
            f"sources={list(self.source_scores.keys())})"
        )


# ---------------------------------------------------------------------------
# RRF Fusion 설명 데이터클래스
# ---------------------------------------------------------------------------


@dataclass
class RRFFusionExplanation:
    """
    RRF Fusion 과정 설명

    융합 과정의 디버깅 및 투명성을 위해 상세한 설명 정보를 제공합니다.

    Attributes:
        results: RRF 융합 결과 리스트
        k: 사용된 k 값
        weights: 적용된 가중치 딕셔너리
        source_counts: 소스별 입력 결과 수
        total_unique: 고유 문서 수
        fusion_details: 문서별 융합 상세 정보
    """

    results: List[RRFResult]
    k: int
    weights: Dict[str, float]
    source_counts: Dict[str, int]
    total_unique: int
    fusion_details: List[Dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# RRFFusion 클래스
# ---------------------------------------------------------------------------


class RRFFusion:
    """
    Reciprocal Rank Fusion (RRF) 알고리즘 구현

    다중 검색 소스의 결과를 RRF 공식으로 융합하여
    통합 순위를 생성합니다.

    RRF 공식:
        RRF(d) = sum(weight_i * 1 / (k + rank_i + 1))

    Args:
        k: 순위 안정화 상수. 기본값 60.
            값이 클수록 상위/하위 순위 간 점수 차이가 줄어듦.
            값이 작으면 상위 순위 결과에 더 높은 가중치 부여.

    Usage:
        >>> fusion = RRFFusion(k=60)
        >>> es_results = [{"doc_id": "doc-1", "content": "..."}]
        >>> neo4j_results = [{"doc_id": "doc-1", "content": "..."}]
        >>> results = fusion.fuse(
        ...     result_lists=[es_results, neo4j_results],
        ...     weights=[0.6, 0.4],
        ...     source_names=["es", "neo4j"],
        ... )
    """

    def __init__(self, k: int = 60) -> None:
        """
        RRFFusion 초기화

        Args:
            k: 순위 안정화 상수 (기본값 60)

        Raises:
            ValueError: k가 0 이하인 경우
        """
        if k <= 0:
            raise ValueError(f"k must be a positive integer, got {k}")
        self._k = k
        logger.debug("RRFFusion initialized with k=%d", self._k)

    @property
    def k(self) -> int:
        """순위 안정화 상수 k 값"""
        return self._k

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fuse(
        self,
        result_lists: List[List[Dict[str, Any]]],
        weights: Optional[List[float]] = None,
        source_names: Optional[List[str]] = None,
    ) -> List[RRFResult]:
        """
        다중 검색 소스의 결과를 RRF 알고리즘으로 융합

        각 소스의 결과 리스트를 받아 RRF 공식을 적용하고,
        가중치를 반영한 통합 점수로 정렬된 결과를 반환합니다.

        Args:
            result_lists: 소스별 검색 결과 리스트.
                각 결과는 최소한 "doc_id" 키를 가진 딕셔너리.
                선택적으로 "content", "metadata" 키 포함 가능.
                예: [[{"doc_id": "1", "content": "..."}], ...]
            weights: 소스별 가중치 리스트.
                None이면 모든 소스에 동일 가중치(1.0) 적용.
                예: [0.6, 0.4]
            source_names: 소스 식별 이름 리스트.
                None이면 "source_0", "source_1", ... 자동 생성.
                예: ["es", "neo4j"]

        Returns:
            RRF 점수 기준 내림차순 정렬된 RRFResult 리스트

        Raises:
            ValueError: result_lists가 빈 리스트이거나,
                weights 길이가 result_lists와 불일치하거나,
                source_names 길이가 result_lists와 불일치하거나,
                가중치에 음수가 포함된 경우
        """
        # 입력 검증
        self._validate_inputs(result_lists, weights, source_names)

        num_sources = len(result_lists)

        # 기본값 설정
        effective_weights = self._resolve_weights(weights, num_sources)
        effective_names = self._resolve_source_names(source_names, num_sources)

        # RRF 점수 계산
        scores: Dict[str, float] = {}
        source_scores: Dict[str, Dict[str, float]] = {}
        doc_data: Dict[str, Dict[str, Any]] = {}

        for source_idx, result_list in enumerate(result_lists):
            source_name = effective_names[source_idx]
            weight = effective_weights[source_idx]

            for rank, result in enumerate(result_list):
                doc_id = self._extract_doc_id(result)
                if doc_id is None:
                    logger.warning(
                        "Skipping result at rank %d in source '%s': no doc_id found",
                        rank,
                        source_name,
                    )
                    continue

                # RRF 공식: weight * 1 / (k + rank + 1)
                rrf_score = weight * (1.0 / (self._k + rank + 1))

                # 누적 합산 (동일 문서가 여러 소스에 존재할 경우)
                scores[doc_id] = scores.get(doc_id, 0.0) + rrf_score

                # 소스별 점수 기록
                if doc_id not in source_scores:
                    source_scores[doc_id] = {}
                source_scores[doc_id][source_name] = rrf_score

                # 문서 데이터 저장 (첫 번째 등장 기준)
                if doc_id not in doc_data:
                    doc_data[doc_id] = {
                        "content": self._extract_content(result),
                        "metadata": self._extract_metadata(result),
                    }

        # 점수 기준 내림차순 정렬
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        # RRFResult 리스트 생성
        fused_results: List[RRFResult] = []
        for doc_id in sorted_ids:
            data = doc_data[doc_id]
            fused_results.append(
                RRFResult(
                    doc_id=doc_id,
                    content=data["content"],
                    metadata=data["metadata"],
                    rrf_score=round(scores[doc_id], 6),
                    source_scores={
                        k: round(v, 6) for k, v in source_scores[doc_id].items()
                    },
                )
            )

        logger.info(
            "RRF fusion complete - Sources: %d, Input docs: %d, "
            "Unique docs: %d, k=%d, weights=%s",
            num_sources,
            sum(len(rl) for rl in result_lists),
            len(fused_results),
            self._k,
            dict(zip(effective_names, effective_weights)),
        )

        return fused_results

    def fuse_with_explanation(
        self,
        result_lists: List[List[Dict[str, Any]]],
        weights: Optional[List[float]] = None,
        source_names: Optional[List[str]] = None,
    ) -> RRFFusionExplanation:
        """
        RRF 융합을 수행하고 상세한 과정 설명을 포함하여 반환

        fuse()와 동일한 융합을 수행하되, 각 문서의 소스별 순위,
        가중치 적용 전/후 점수, 최종 점수 계산 과정을 포함합니다.
        디버깅, 품질 분석, 투명성 확보에 활용됩니다.

        Args:
            result_lists: 소스별 검색 결과 리스트
            weights: 소스별 가중치 리스트
            source_names: 소스 식별 이름 리스트

        Returns:
            RRFFusionExplanation 객체 (results, 과정 설명 포함)

        Raises:
            ValueError: fuse()와 동일한 검증 조건
        """
        # 입력 검증
        self._validate_inputs(result_lists, weights, source_names)

        num_sources = len(result_lists)
        effective_weights = self._resolve_weights(weights, num_sources)
        effective_names = self._resolve_source_names(source_names, num_sources)

        # 소스별 결과 수 기록
        source_counts: Dict[str, int] = {
            effective_names[i]: len(result_lists[i])
            for i in range(num_sources)
        }

        # 소스별 순위 추적 (doc_id -> {source_name: rank})
        source_ranks: Dict[str, Dict[str, int]] = {}
        # 소스별 가중치 미적용 점수 추적
        raw_scores: Dict[str, Dict[str, float]] = {}

        # 일반 fuse로 결과 생성
        # 내부 로직을 상세히 추적하기 위해 수동 계산
        scores: Dict[str, float] = {}
        source_scores: Dict[str, Dict[str, float]] = {}
        doc_data: Dict[str, Dict[str, Any]] = {}

        for source_idx, result_list in enumerate(result_lists):
            source_name = effective_names[source_idx]
            weight = effective_weights[source_idx]

            for rank, result in enumerate(result_list):
                doc_id = self._extract_doc_id(result)
                if doc_id is None:
                    continue

                # Raw RRF (가중치 미적용)
                raw_rrf = 1.0 / (self._k + rank + 1)
                # Weighted RRF
                weighted_rrf = weight * raw_rrf

                scores[doc_id] = scores.get(doc_id, 0.0) + weighted_rrf

                if doc_id not in source_scores:
                    source_scores[doc_id] = {}
                source_scores[doc_id][source_name] = weighted_rrf

                if doc_id not in source_ranks:
                    source_ranks[doc_id] = {}
                source_ranks[doc_id][source_name] = rank

                if doc_id not in raw_scores:
                    raw_scores[doc_id] = {}
                raw_scores[doc_id][source_name] = raw_rrf

                if doc_id not in doc_data:
                    doc_data[doc_id] = {
                        "content": self._extract_content(result),
                        "metadata": self._extract_metadata(result),
                    }

        # 점수 기준 정렬
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        # RRFResult 리스트 생성
        fused_results: List[RRFResult] = []
        fusion_details: List[Dict[str, Any]] = []

        for final_rank, doc_id in enumerate(sorted_ids):
            data = doc_data[doc_id]

            rrf_result = RRFResult(
                doc_id=doc_id,
                content=data["content"],
                metadata=data["metadata"],
                rrf_score=round(scores[doc_id], 6),
                source_scores={
                    k: round(v, 6) for k, v in source_scores[doc_id].items()
                },
            )
            fused_results.append(rrf_result)

            # 상세 설명 생성
            detail: Dict[str, Any] = {
                "final_rank": final_rank,
                "doc_id": doc_id,
                "rrf_score": round(scores[doc_id], 6),
                "source_contributions": {},
                "appears_in_sources": list(source_scores[doc_id].keys()),
                "num_sources": len(source_scores[doc_id]),
            }

            for src_name in source_scores[doc_id]:
                detail["source_contributions"][src_name] = {
                    "rank": source_ranks[doc_id][src_name],
                    "raw_rrf_score": round(raw_scores[doc_id][src_name], 6),
                    "weight": effective_weights[effective_names.index(src_name)],
                    "weighted_rrf_score": round(
                        source_scores[doc_id][src_name], 6
                    ),
                }

            fusion_details.append(detail)

        logger.info(
            "RRF fusion with explanation - Sources: %d, "
            "Unique docs: %d, k=%d",
            num_sources,
            len(fused_results),
            self._k,
        )

        return RRFFusionExplanation(
            results=fused_results,
            k=self._k,
            weights=dict(zip(effective_names, effective_weights)),
            source_counts=source_counts,
            total_unique=len(fused_results),
            fusion_details=fusion_details,
        )

    # ------------------------------------------------------------------
    # SearchResult 호환 메서드
    # ------------------------------------------------------------------

    def fuse_search_results(
        self,
        result_lists: List[List[Any]],
        weights: Optional[List[float]] = None,
        source_names: Optional[List[str]] = None,
    ) -> List[Any]:
        """
        SearchResult 객체 리스트를 RRF로 융합

        기존 SearchService._rrf_fusion과 호환되는 인터페이스로,
        app.agents.state.SearchResult 객체를 직접 처리합니다.
        HybridRetriever 통합 시 사용됩니다.

        Args:
            result_lists: SearchResult 객체 리스트의 리스트
            weights: 소스별 가중치 (None이면 동일 가중치)
            source_names: 소스 이름 리스트

        Returns:
            RRF 점수로 정렬된 SearchResult 리스트
            (score, metadata에 rrf_score/source_ranks 추가)
        """
        num_sources = len(result_lists)
        if num_sources == 0:
            return []

        effective_weights = self._resolve_weights(weights, num_sources)
        effective_names = self._resolve_source_names(source_names, num_sources)

        scores: Dict[str, float] = {}
        results_map: Dict[str, Any] = {}
        source_ranks_map: Dict[str, Dict[str, int]] = {}
        source_scores_map: Dict[str, Dict[str, float]] = {}

        for source_idx, result_list in enumerate(result_lists):
            source_name = effective_names[source_idx]
            weight = effective_weights[source_idx]

            for rank, result in enumerate(result_list):
                chunk_id = getattr(result, "chunk_id", None)
                if chunk_id is None:
                    continue

                rrf_score = weight * (1.0 / (self._k + rank + 1))
                scores[chunk_id] = scores.get(chunk_id, 0.0) + rrf_score

                if chunk_id not in results_map:
                    results_map[chunk_id] = result

                if chunk_id not in source_ranks_map:
                    source_ranks_map[chunk_id] = {}
                source_ranks_map[chunk_id][source_name] = rank + 1

                if chunk_id not in source_scores_map:
                    source_scores_map[chunk_id] = {}
                source_scores_map[chunk_id][source_name] = rrf_score

        # 점수 기준 정렬
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        fused_results: List[Any] = []
        for chunk_id in sorted_ids:
            result = results_map[chunk_id]
            result.score = round(scores[chunk_id], 6)
            result.metadata["rrf_score"] = result.score
            result.metadata["source_ranks"] = source_ranks_map.get(chunk_id, {})
            result.metadata["source_scores"] = {
                k: round(v, 6)
                for k, v in source_scores_map.get(chunk_id, {}).items()
            }
            fused_results.append(result)

        logger.info(
            "RRF fusion (SearchResult) - Sources: %d, "
            "Input: %d, Unique: %d, k=%d",
            num_sources,
            sum(len(rl) for rl in result_lists),
            len(fused_results),
            self._k,
        )

        return fused_results

    # ------------------------------------------------------------------
    # Internal methods
    # ------------------------------------------------------------------

    def _validate_inputs(
        self,
        result_lists: List[List[Any]],
        weights: Optional[List[float]],
        source_names: Optional[List[str]],
    ) -> None:
        """
        입력값 검증

        Args:
            result_lists: 검색 결과 리스트
            weights: 가중치 리스트
            source_names: 소스 이름 리스트

        Raises:
            ValueError: 유효하지 않은 입력
        """
        if not isinstance(result_lists, list):
            raise ValueError(
                f"result_lists must be a list, got {type(result_lists).__name__}"
            )

        num_sources = len(result_lists)

        if num_sources == 0:
            raise ValueError("result_lists must contain at least one source")

        if weights is not None:
            if len(weights) != num_sources:
                raise ValueError(
                    f"weights length ({len(weights)}) must match "
                    f"result_lists length ({num_sources})"
                )
            for i, w in enumerate(weights):
                if w < 0:
                    raise ValueError(
                        f"Weight at index {i} is negative ({w}). "
                        f"All weights must be non-negative."
                    )

        if source_names is not None:
            if len(source_names) != num_sources:
                raise ValueError(
                    f"source_names length ({len(source_names)}) must match "
                    f"result_lists length ({num_sources})"
                )

    @staticmethod
    def _resolve_weights(
        weights: Optional[List[float]], num_sources: int
    ) -> List[float]:
        """
        가중치 결정. None이면 동일 가중치(1.0)를 부여.

        Args:
            weights: 사용자 지정 가중치 또는 None
            num_sources: 소스 수

        Returns:
            가중치 리스트
        """
        if weights is not None:
            return weights
        return [1.0] * num_sources

    @staticmethod
    def _resolve_source_names(
        source_names: Optional[List[str]], num_sources: int
    ) -> List[str]:
        """
        소스 이름 결정. None이면 자동 생성.

        Args:
            source_names: 사용자 지정 이름 또는 None
            num_sources: 소스 수

        Returns:
            소스 이름 리스트
        """
        if source_names is not None:
            return source_names
        return [f"source_{i}" for i in range(num_sources)]

    @staticmethod
    def _extract_doc_id(result: Any) -> Optional[str]:
        """
        결과에서 문서 ID 추출

        딕셔너리의 "doc_id" 키 또는 객체의 doc_id/chunk_id 속성을 탐색합니다.

        Args:
            result: 검색 결과 (dict 또는 객체)

        Returns:
            문서 ID 문자열 또는 None
        """
        if isinstance(result, dict):
            return result.get("doc_id") or result.get("chunk_id")
        return getattr(result, "doc_id", None) or getattr(result, "chunk_id", None)

    @staticmethod
    def _extract_content(result: Any) -> str:
        """
        결과에서 콘텐츠 추출

        Args:
            result: 검색 결과 (dict 또는 객체)

        Returns:
            콘텐츠 문자열 (없으면 빈 문자열)
        """
        if isinstance(result, dict):
            return result.get("content", "")
        return getattr(result, "content", "")

    @staticmethod
    def _extract_metadata(result: Any) -> Dict[str, Any]:
        """
        결과에서 메타데이터 추출

        Args:
            result: 검색 결과 (dict 또는 객체)

        Returns:
            메타데이터 딕셔너리 (없으면 빈 딕셔너리)
        """
        if isinstance(result, dict):
            return dict(result.get("metadata", {}))
        return dict(getattr(result, "metadata", {}))


# ---------------------------------------------------------------------------
# 모듈 수준 팩토리 함수
# ---------------------------------------------------------------------------

_default_rrf_fusion: Optional[RRFFusion] = None


def get_rrf_fusion(k: int = 60) -> RRFFusion:
    """
    RRFFusion 인스턴스 반환 (싱글톤)

    Args:
        k: 순위 안정화 상수 (최초 생성 시에만 적용)

    Returns:
        RRFFusion 인스턴스
    """
    global _default_rrf_fusion
    if _default_rrf_fusion is None:
        _default_rrf_fusion = RRFFusion(k=k)
    return _default_rrf_fusion


def reset_rrf_fusion() -> None:
    """싱글톤 인스턴스 초기화 (테스트용)"""
    global _default_rrf_fusion
    _default_rrf_fusion = None
