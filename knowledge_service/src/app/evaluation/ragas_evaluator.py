"""
RAGAS 평가기 모듈

RAG 파이프라인의 품질을 RAGAS 메트릭으로 측정합니다.

메트릭:
- Faithfulness: 답변이 컨텍스트에 충실한지 (환각 방지)
- Answer Relevancy: 답변이 질문에 적절한지
- Context Precision: 검색된 컨텍스트가 정확한지
- Context Recall: 필요한 정보가 검색되었는지

사용 예시:
    evaluator = RagasEvaluator()
    result = await evaluator.evaluate(samples)
"""

import asyncio
import json
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from app.core.config import settings
from app.core.logging import get_logger
from app.evaluation.models import (
    EvaluationResult,
    EvaluationResponse,
    EvaluationSample,
    MetricScores,
)

logger = get_logger(__name__)

# 지원 메트릭 목록
SUPPORTED_METRICS: Set[str] = {
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
}


class RagasEvaluator:
    """
    RAGAS 평가기 클래스

    RAG 파이프라인의 품질을 측정하기 위한 RAGAS 메트릭 평가를 수행합니다.

    Attributes:
        llm_model: LLM 모델 (평가에 사용)
        embedding_model: 임베딩 모델 (Answer Relevancy 측정에 사용)
        targets: 메트릭별 목표 점수

    Example:
        >>> evaluator = RagasEvaluator()
        >>> samples = [
        ...     EvaluationSample(
        ...         question="LangGraph란 무엇인가요?",
        ...         answer="LangGraph는 상태 기반 에이전트 프레임워크입니다.",
        ...         contexts=["LangGraph는 LangChain 기반의 상태 기반 에이전트 프레임워크입니다."],
        ...         ground_truth="LangGraph는 상태 기반 에이전트를 구축하기 위한 프레임워크입니다."
        ...     )
        ... ]
        >>> result = await evaluator.evaluate(samples)
        >>> print(result.aggregate_scores.faithfulness)
    """

    def __init__(
        self,
        llm_model: Optional[str] = None,
        embedding_model: Optional[str] = None,
        targets: Optional[Dict[str, float]] = None,
    ):
        """
        초기화

        Args:
            llm_model: LLM 모델명 (기본: DeepSeek Chat)
            embedding_model: 임베딩 모델명 (기본: BGE-M3)
            targets: 메트릭별 목표 점수
        """
        self.llm_model = llm_model or settings.deepseek_chat_model
        self.embedding_model = embedding_model or settings.embedding_model
        self.targets = targets or {
            "faithfulness": settings.ragas_faithfulness_target,
            "answer_relevancy": settings.ragas_relevancy_target,
            "context_precision": settings.ragas_precision_target,
            "context_recall": 0.7,  # 기본값
        }

        self._ragas_initialized = False
        self._ragas_llm = None
        self._ragas_embeddings = None

        logger.info(
            f"RagasEvaluator initialized - LLM: {self.llm_model}, "
            f"Embedding: {self.embedding_model}, Targets: {self.targets}"
        )

    async def _init_ragas(self) -> None:
        """RAGAS 라이브러리 초기화 (지연 로딩)"""
        if self._ragas_initialized:
            return

        # API 키가 없으면 Mock 모드 사용 (무거운 의존성 로딩 건너뛰기)
        api_key = settings.deepseek_api_key
        if not api_key:
            logger.warning("DEEPSEEK_API_KEY not set, using mock evaluation")
            self._ragas_initialized = True
            return

        try:
            # RAGAS는 OpenAI 호환 API를 사용
            # DeepSeek은 OpenAI 호환 API 제공
            from langchain_openai import ChatOpenAI, OpenAIEmbeddings

            # DeepSeek LLM (OpenAI 호환)
            self._ragas_llm = ChatOpenAI(
                model=self.llm_model,
                api_key=api_key,
                base_url=settings.deepseek_base_url,
                temperature=0.0,
            )

            # 임베딩 모델 (로컬 BGE-M3 또는 OpenAI)
            # 여기서는 간단히 OpenAI Embeddings 사용
            # 실제 배포에서는 로컬 BGE-M3 사용 권장
            try:
                self._ragas_embeddings = OpenAIEmbeddings(
                    model="text-embedding-3-small",
                    api_key=os.getenv("OPENAI_API_KEY", ""),
                )
            except Exception as e:
                logger.warning(f"OpenAI Embeddings init failed: {e}, using None")
                self._ragas_embeddings = None

            self._ragas_initialized = True
            logger.info("RAGAS initialized successfully")

        except ImportError as e:
            logger.error(f"RAGAS dependencies not installed: {e}")
            raise ImportError(
                "RAGAS 평가를 위해 ragas, langchain-openai 패키지가 필요합니다. "
                "poetry add ragas langchain-openai"
            )
        except Exception as e:
            logger.error(f"RAGAS initialization failed: {e}")
            raise

    async def evaluate(
        self,
        samples: List[EvaluationSample],
        metrics: Optional[List[str]] = None,
    ) -> EvaluationResponse:
        """
        평가 실행

        Args:
            samples: 평가 샘플 리스트
            metrics: 평가할 메트릭 리스트 (기본: 전체)

        Returns:
            EvaluationResponse: 평가 결과

        Raises:
            ValueError: 잘못된 메트릭 지정
            RuntimeError: 평가 실패
        """
        if not samples:
            raise ValueError("평가할 샘플이 없습니다")

        # 메트릭 검증
        metrics = metrics or list(SUPPORTED_METRICS)
        invalid_metrics = set(metrics) - SUPPORTED_METRICS
        if invalid_metrics:
            raise ValueError(f"지원하지 않는 메트릭: {invalid_metrics}")

        # Context Recall은 ground_truth 필요
        if "context_recall" in metrics:
            has_ground_truth = all(s.ground_truth for s in samples)
            if not has_ground_truth:
                logger.warning(
                    "context_recall 메트릭은 ground_truth가 필요합니다. "
                    "ground_truth가 없는 샘플은 해당 메트릭이 None으로 설정됩니다."
                )

        logger.info(f"Starting evaluation - Samples: {len(samples)}, Metrics: {metrics}")

        await self._init_ragas()

        # 개별 샘플 평가
        results: List[EvaluationResult] = []
        all_scores: Dict[str, List[float]] = {m: [] for m in metrics}

        for idx, sample in enumerate(samples):
            sample_id = f"sample_{idx + 1}_{uuid.uuid4().hex[:8]}"

            try:
                scores = await self._evaluate_sample(sample, metrics)

                # 통과 여부 판정
                passed = self._check_passed(scores)

                result = EvaluationResult(
                    sample_id=sample_id,
                    question=sample.question,
                    scores=scores,
                    passed=passed,
                    details={
                        "answer_length": len(sample.answer),
                        "context_count": len(sample.contexts),
                        "has_ground_truth": sample.ground_truth is not None,
                    },
                )
                results.append(result)

                # 집계용 점수 수집
                for metric in metrics:
                    score = getattr(scores, metric)
                    if score is not None:
                        all_scores[metric].append(score)

            except Exception as e:
                logger.error(f"Sample {sample_id} evaluation failed: {e}")
                results.append(
                    EvaluationResult(
                        sample_id=sample_id,
                        question=sample.question,
                        scores=MetricScores(),
                        passed=False,
                        details={"error": str(e)},
                    )
                )

        # 집계 점수 계산
        aggregate_scores = MetricScores(
            faithfulness=self._average(all_scores.get("faithfulness", [])),
            answer_relevancy=self._average(all_scores.get("answer_relevancy", [])),
            context_precision=self._average(all_scores.get("context_precision", [])),
            context_recall=self._average(all_scores.get("context_recall", [])),
        )

        passed_samples = sum(1 for r in results if r.passed)

        response = EvaluationResponse(
            total_samples=len(samples),
            passed_samples=passed_samples,
            aggregate_scores=aggregate_scores,
            results=results,
            summary={
                "pass_rate": passed_samples / len(samples) if samples else 0.0,
                "metrics_evaluated": metrics,
                "targets": self.targets,
                "meets_targets": self._meets_targets(aggregate_scores),
            },
        )

        logger.info(
            f"Evaluation complete - Pass rate: {response.pass_rate:.2%}, "
            f"Faithfulness: {aggregate_scores.faithfulness}, "
            f"Relevancy: {aggregate_scores.answer_relevancy}"
        )

        return response

    async def _evaluate_sample(
        self,
        sample: EvaluationSample,
        metrics: List[str],
    ) -> MetricScores:
        """
        단일 샘플 평가

        Args:
            sample: 평가 샘플
            metrics: 평가할 메트릭 리스트

        Returns:
            MetricScores: 메트릭 점수
        """
        scores: Dict[str, Optional[float]] = {}

        # API 키가 없으면 mock 평가
        if not settings.deepseek_api_key:
            return self._mock_evaluate(sample, metrics)

        try:
            from datasets import Dataset
            from ragas import evaluate
            from ragas.metrics import (
                answer_relevancy,
                context_precision,
                context_recall,
                faithfulness,
            )

            # RAGAS 데이터셋 생성
            data = {
                "question": [sample.question],
                "answer": [sample.answer],
                "contexts": [sample.contexts],
            }
            if sample.ground_truth:
                data["ground_truth"] = [sample.ground_truth]

            dataset = Dataset.from_dict(data)

            # 메트릭 객체 매핑
            metric_objects = []
            if "faithfulness" in metrics:
                metric_objects.append(faithfulness)
            if "answer_relevancy" in metrics:
                metric_objects.append(answer_relevancy)
            if "context_precision" in metrics:
                metric_objects.append(context_precision)
            if "context_recall" in metrics and sample.ground_truth:
                metric_objects.append(context_recall)

            # RAGAS 평가 실행
            result = evaluate(
                dataset,
                metrics=metric_objects,
                llm=self._ragas_llm,
                embeddings=self._ragas_embeddings,
            )

            # 결과 추출
            for metric in metrics:
                if metric in result:
                    scores[metric] = float(result[metric])
                else:
                    scores[metric] = None

        except ImportError:
            logger.warning("RAGAS not available, using mock evaluation")
            return self._mock_evaluate(sample, metrics)
        except Exception as e:
            logger.error(f"RAGAS evaluation error: {e}")
            # 폴백: mock 평가
            return self._mock_evaluate(sample, metrics)

        return MetricScores(**scores)

    def _mock_evaluate(
        self,
        sample: EvaluationSample,
        metrics: List[str],
    ) -> MetricScores:
        """
        Mock 평가 (RAGAS 불가 시 사용)

        휴리스틱 기반으로 대략적인 점수 계산
        """
        scores: Dict[str, Optional[float]] = {}

        # Faithfulness: 답변 단어 중 컨텍스트에 있는 비율
        if "faithfulness" in metrics:
            answer_words = set(sample.answer.lower().split())
            context_text = " ".join(sample.contexts).lower()
            context_words = set(context_text.split())
            if answer_words:
                overlap = len(answer_words & context_words)
                scores["faithfulness"] = min(overlap / len(answer_words), 1.0)
            else:
                scores["faithfulness"] = 0.0

        # Answer Relevancy: 질문 단어 중 답변에 있는 비율
        if "answer_relevancy" in metrics:
            question_words = set(sample.question.lower().split())
            answer_words = set(sample.answer.lower().split())
            if question_words:
                overlap = len(question_words & answer_words)
                scores["answer_relevancy"] = min(overlap / len(question_words), 1.0)
            else:
                scores["answer_relevancy"] = 0.5

        # Context Precision: 컨텍스트 중 질문과 관련된 비율
        if "context_precision" in metrics:
            question_words = set(sample.question.lower().split())
            relevant_contexts = 0
            for ctx in sample.contexts:
                ctx_words = set(ctx.lower().split())
                if question_words & ctx_words:
                    relevant_contexts += 1
            if sample.contexts:
                scores["context_precision"] = relevant_contexts / len(sample.contexts)
            else:
                scores["context_precision"] = 0.0

        # Context Recall: ground_truth 단어 중 컨텍스트에 있는 비율
        if "context_recall" in metrics and sample.ground_truth:
            gt_words = set(sample.ground_truth.lower().split())
            context_text = " ".join(sample.contexts).lower()
            context_words = set(context_text.split())
            if gt_words:
                overlap = len(gt_words & context_words)
                scores["context_recall"] = min(overlap / len(gt_words), 1.0)
            else:
                scores["context_recall"] = 0.0

        return MetricScores(**scores)

    def _check_passed(self, scores: MetricScores) -> bool:
        """목표 점수 통과 여부 확인"""
        for metric, target in self.targets.items():
            score = getattr(scores, metric, None)
            if score is not None and score < target:
                return False
        return True

    def _meets_targets(self, scores: MetricScores) -> Dict[str, bool]:
        """각 메트릭의 목표 달성 여부"""
        result = {}
        for metric, target in self.targets.items():
            score = getattr(scores, metric, None)
            if score is not None:
                result[metric] = score >= target
        return result

    @staticmethod
    def _average(values: List[float]) -> Optional[float]:
        """평균 계산 (빈 리스트는 None)"""
        return sum(values) / len(values) if values else None

    async def evaluate_from_file(
        self,
        file_path: str,
        metrics: Optional[List[str]] = None,
    ) -> EvaluationResponse:
        """
        파일에서 평가 데이터 로드 후 평가

        Args:
            file_path: JSON 파일 경로
            metrics: 평가할 메트릭 리스트

        Returns:
            EvaluationResponse: 평가 결과
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"평가 데이터 파일을 찾을 수 없습니다: {file_path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        samples = [EvaluationSample(**item) for item in data]
        return await self.evaluate(samples, metrics)


# 싱글톤 인스턴스
_evaluator: Optional[RagasEvaluator] = None


def get_ragas_evaluator() -> RagasEvaluator:
    """RagasEvaluator 인스턴스 반환 (싱글톤)"""
    global _evaluator
    if _evaluator is None:
        _evaluator = RagasEvaluator()
    return _evaluator
