"""
Live RAG 평가기

실제 RAG 파이프라인을 실행하여 평가 데이터를 생성하고 RAGAS 평가를 수행합니다.

기존 정적 데이터셋 평가 외에, 실제 시스템의 live 성능을 측정할 수 있습니다.

사용 예시:
    evaluator = LiveRagasEvaluator()
    response = await evaluator.evaluate_live(questions, ground_truths)
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.core.logging import get_logger
from app.evaluation.models import EvaluationResponse, EvaluationSample
from app.evaluation.ragas_evaluator import RagasEvaluator

logger = get_logger(__name__)


class LiveRagasEvaluator:
    """
    Live RAG 평가기

    실제 RAG 워크플로우를 실행하여 답변을 생성하고,
    생성된 답변에 대해 RAGAS 평가를 수행합니다.

    Attributes:
        rag_workflow: RAGWorkflow 인스턴스
        ragas_evaluator: RagasEvaluator 인스턴스
        targets: 메트릭별 목표 점수

    Example:
        >>> evaluator = LiveRagasEvaluator()
        >>> questions = ["RAG란 무엇인가요?", "LangGraph란?"]
        >>> ground_truths = ["RAG는 검색 기반 생성입니다", "LangGraph는 상태 기반 프레임워크입니다"]
        >>> response = await evaluator.evaluate_live(questions, ground_truths)
    """

    def __init__(
        self,
        rag_workflow: Optional[Any] = None,
        search_service: Optional[Any] = None,
        targets: Optional[Dict[str, float]] = None,
    ):
        """
        초기화

        Args:
            rag_workflow: RAGWorkflow 인스턴스 (None이면 싱글톤 사용)
            search_service: SearchService 인스턴스 (workflow 생성 시 사용)
            targets: 메트릭별 목표 점수
        """
        self._rag_workflow = rag_workflow
        self._search_service = search_service
        self._targets = targets or {
            "faithfulness": settings.ragas_faithfulness_target,
            "answer_relevancy": settings.ragas_relevancy_target,
            "context_precision": settings.ragas_precision_target,
            "context_recall": 0.7,
        }
        self._ragas_evaluator: Optional[RagasEvaluator] = None

    @property
    def rag_workflow(self) -> Any:
        """RAGWorkflow 지연 초기화"""
        if self._rag_workflow is None:
            from app.agents.rag_workflow import get_rag_workflow
            self._rag_workflow = get_rag_workflow(
                search_service=self._search_service
            )
        return self._rag_workflow

    @property
    def ragas_evaluator(self) -> RagasEvaluator:
        """RagasEvaluator 지연 초기화"""
        if self._ragas_evaluator is None:
            self._ragas_evaluator = RagasEvaluator(targets=self._targets)
        return self._ragas_evaluator

    async def evaluate_live(
        self,
        questions: List[str],
        ground_truths: Optional[List[str]] = None,
        top_k: int = 5,
        metrics: Optional[List[str]] = None,
    ) -> Tuple[EvaluationResponse, List[Dict[str, Any]]]:
        """
        Live 평가 수행

        실제 RAG 파이프라인을 실행하여 답변을 생성하고 RAGAS 평가를 수행합니다.

        Args:
            questions: 평가할 질문 리스트
            ground_truths: 정답 리스트 (Context Recall 측정용, Optional)
            top_k: 검색 결과 수
            metrics: 평가할 메트릭 리스트

        Returns:
            (EvaluationResponse, 개별 RAG 응답 리스트) 튜플
        """
        if not questions:
            raise ValueError("평가할 질문이 없습니다")

        if ground_truths and len(ground_truths) != len(questions):
            raise ValueError(
                f"질문 수({len(questions)})와 정답 수({len(ground_truths)})가 일치하지 않습니다"
            )

        metrics = metrics or ["faithfulness", "answer_relevancy", "context_precision"]

        logger.info(
            "Live evaluation started - Questions: %d, Metrics: %s",
            len(questions), metrics,
        )

        start_time = time.monotonic()

        # 1. RAG 워크플로우 실행
        rag_responses = await self._run_rag_pipeline(questions, top_k)

        # 2. 평가 샘플 생성
        samples = self._build_evaluation_samples(
            questions=questions,
            rag_responses=rag_responses,
            ground_truths=ground_truths,
        )

        # 3. RAGAS 평가 수행
        evaluation_response = await self.ragas_evaluator.evaluate(
            samples=samples,
            metrics=metrics,
        )

        elapsed = time.monotonic() - start_time

        logger.info(
            "Live evaluation complete - "
            "Samples: %d, Pass rate: %.1f%%, "
            "Faithfulness: %.4f, Relevancy: %.4f, "
            "Total time: %.2fs",
            len(samples),
            evaluation_response.pass_rate * 100,
            evaluation_response.aggregate_scores.faithfulness or 0,
            evaluation_response.aggregate_scores.answer_relevancy or 0,
            elapsed,
        )

        return evaluation_response, rag_responses

    async def _run_rag_pipeline(
        self,
        questions: List[str],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """
        RAG 파이프라인 실행

        Args:
            questions: 질문 리스트
            top_k: 검색 결과 수

        Returns:
            RAG 응답 딕셔너리 리스트
        """
        responses: List[Dict[str, Any]] = []

        for idx, question in enumerate(questions):
            logger.debug("Processing question %d/%d: %s", idx + 1, len(questions), question[:50])

            try:
                # RAG 워크플로우 실행
                rag_response = await self.rag_workflow.run(
                    query=question,
                    top_k=top_k,
                    use_reasoner=False,
                )

                # 컨텍스트 추출
                contexts = [
                    result.content
                    for result in rag_response.search_results
                ]

                responses.append({
                    "question": question,
                    "answer": rag_response.answer,
                    "contexts": contexts,
                    "sources": rag_response.sources,
                    "latency_ms": rag_response.latency_ms,
                    "error": None,
                })

            except Exception as e:
                logger.warning("RAG pipeline failed for question %d: %s", idx + 1, e)
                responses.append({
                    "question": question,
                    "answer": "",
                    "contexts": [],
                    "sources": [],
                    "latency_ms": 0,
                    "error": str(e),
                })

        return responses

    def _build_evaluation_samples(
        self,
        questions: List[str],
        rag_responses: List[Dict[str, Any]],
        ground_truths: Optional[List[str]] = None,
    ) -> List[EvaluationSample]:
        """
        평가 샘플 생성

        Args:
            questions: 질문 리스트
            rag_responses: RAG 응답 리스트
            ground_truths: 정답 리스트

        Returns:
            EvaluationSample 리스트
        """
        samples: List[EvaluationSample] = []

        for idx, (question, response) in enumerate(zip(questions, rag_responses)):
            if response.get("error"):
                logger.warning("Skipping failed sample %d: %s", idx + 1, response["error"])
                continue

            sample = EvaluationSample(
                question=question,
                answer=response["answer"],
                contexts=response["contexts"],
                ground_truth=ground_truths[idx] if ground_truths else None,
                metadata={
                    "latency_ms": response["latency_ms"],
                    "source_count": len(response["sources"]),
                },
            )
            samples.append(sample)

        return samples

    async def evaluate_from_questions_file(
        self,
        file_path: str,
        top_k: int = 5,
        metrics: Optional[List[str]] = None,
    ) -> Tuple[EvaluationResponse, List[Dict[str, Any]]]:
        """
        파일에서 질문을 로드하여 Live 평가 수행

        JSON 파일 형식:
        [
            {"question": "질문1", "ground_truth": "정답1"},
            {"question": "질문2", "ground_truth": "정답2"}
        ]

        또는 간단한 형식:
        ["질문1", "질문2", "질문3"]

        Args:
            file_path: JSON 파일 경로
            top_k: 검색 결과 수
            metrics: 평가할 메트릭 리스트

        Returns:
            (EvaluationResponse, RAG 응답 리스트) 튜플
        """
        import json
        from pathlib import Path

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"질문 파일을 찾을 수 없습니다: {file_path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 형식 확인
        if isinstance(data, list) and len(data) > 0:
            if isinstance(data[0], str):
                # 단순 문자열 리스트
                questions = data
                ground_truths = None
            elif isinstance(data[0], dict):
                # 딕셔너리 리스트
                questions = [item.get("question", item.get("q", "")) for item in data]
                ground_truths = [
                    item.get("ground_truth", item.get("answer", item.get("gt")))
                    for item in data
                ]
                # None이 아닌 값만 유지
                if all(gt is None for gt in ground_truths):
                    ground_truths = None
            else:
                raise ValueError("지원하지 않는 파일 형식입니다")
        else:
            raise ValueError("파일에 질문이 없습니다")

        return await self.evaluate_live(
            questions=questions,
            ground_truths=ground_truths,
            top_k=top_k,
            metrics=metrics,
        )


# 싱글톤 인스턴스
_live_evaluator: Optional[LiveRagasEvaluator] = None


def get_live_evaluator(
    rag_workflow: Optional[Any] = None,
    search_service: Optional[Any] = None,
) -> LiveRagasEvaluator:
    """LiveRagasEvaluator 인스턴스 반환 (싱글톤)"""
    global _live_evaluator
    if _live_evaluator is None:
        _live_evaluator = LiveRagasEvaluator(
            rag_workflow=rag_workflow,
            search_service=search_service,
        )
    return _live_evaluator


def reset_live_evaluator() -> None:
    """싱글톤 인스턴스 초기화 (테스트용)"""
    global _live_evaluator
    _live_evaluator = None
