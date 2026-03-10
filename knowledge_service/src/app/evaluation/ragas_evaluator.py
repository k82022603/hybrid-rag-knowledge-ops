"""
RAGAS 평가기 모듈

RAG 파이프라인의 품질을 RAGAS 메트릭으로 측정합니다.

메트릭:
- Faithfulness: 답변이 컨텍스트에 충실한지 (환각 방지)
- Answer Relevancy: 답변이 질문에 적절한지
- Context Precision: 검색된 컨텍스트가 정확한지
- Context Recall: 필요한 정보가 검색되었는지

Judge LLM 설정:
- 기본값: DeepSeek (RAGAS_JUDGE_MODEL 미설정 시)
- GPT-4o: RAGAS_JUDGE_MODEL=gpt-4o + OPENAI_API_KEY 설정 시
- 환경변수로 런타임 전환 가능

사용 예시:
    evaluator = RagasEvaluator()
    result = await evaluator.evaluate(samples)

    # GPT-4o judge 사용:
    evaluator = RagasEvaluator(judge_model="gpt-4o")
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

# 지원 Judge 모델 목록
SUPPORTED_JUDGE_MODELS: Dict[str, Dict[str, str]] = {
    "deepseek": {
        "description": "DeepSeek Chat (default, cost-effective)",
        "env_key": "DEEPSEEK_API_KEY",
    },
    "gpt-4o": {
        "description": "OpenAI GPT-4o (higher accuracy for Faithfulness)",
        "env_key": "OPENAI_API_KEY",
    },
    "gpt-4o-mini": {
        "description": "OpenAI GPT-4o-mini (balanced cost/accuracy)",
        "env_key": "OPENAI_API_KEY",
    },
}


def _resolve_judge_model() -> str:
    """
    Judge LLM 모델을 결정합니다.

    우선순위:
    1. RAGAS_JUDGE_MODEL 환경변수
    2. settings.deepseek_chat_model (기본값: deepseek)

    Returns:
        Judge 모델 식별자 (예: "deepseek", "gpt-4o")
    """
    judge = os.getenv("RAGAS_JUDGE_MODEL", "").strip().lower()
    if judge and judge in SUPPORTED_JUDGE_MODELS:
        return judge
    if judge == "deepseek-chat" or judge == "deepseek":
        return "deepseek"
    # 기본값: deepseek
    return "deepseek"


class RagasEvaluator:
    """
    RAGAS 평가기 클래스

    RAG 파이프라인의 품질을 측정하기 위한 RAGAS 메트릭 평가를 수행합니다.

    Judge LLM을 DeepSeek 또는 GPT-4o 중 선택할 수 있습니다.
    - 기본값: DeepSeek (비용 효율적)
    - GPT-4o: Faithfulness 측정 안정성이 높음 (RAGAS 공식 권장)

    Attributes:
        llm_model: LLM 모델명 (RAGAS judge에 사용)
        embedding_model: 임베딩 모델명 (Answer Relevancy 측정에 사용)
        targets: 메트릭별 목표 점수
        judge_model: Judge LLM 식별자 ("deepseek" | "gpt-4o" | "gpt-4o-mini")

    Example:
        >>> # DeepSeek judge (기본)
        >>> evaluator = RagasEvaluator()

        >>> # GPT-4o judge
        >>> evaluator = RagasEvaluator(judge_model="gpt-4o")

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
        judge_model: Optional[str] = None,
    ):
        """
        초기화

        Args:
            llm_model: LLM 모델명 (기본: judge_model에 따라 자동 결정)
            embedding_model: 임베딩 모델명 (기본: BGE-M3)
            targets: 메트릭별 목표 점수
            judge_model: Judge LLM 선택 ("deepseek" | "gpt-4o" | "gpt-4o-mini")
                         기본값: RAGAS_JUDGE_MODEL 환경변수 또는 "deepseek"
        """
        # Judge 모델 결정
        self.judge_model = judge_model or _resolve_judge_model()

        # LLM 모델명 결정
        if llm_model:
            self.llm_model = llm_model
        elif self.judge_model == "deepseek":
            self.llm_model = settings.deepseek_chat_model
        elif self.judge_model in ("gpt-4o", "gpt-4o-mini"):
            self.llm_model = self.judge_model
        else:
            self.llm_model = settings.deepseek_chat_model

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
            f"RagasEvaluator initialized - Judge: {self.judge_model}, "
            f"LLM: {self.llm_model}, "
            f"Embedding: {self.embedding_model}, Targets: {self.targets}"
        )

    def _get_judge_api_key(self) -> Optional[str]:
        """
        Judge 모델에 맞는 API 키를 반환합니다.

        Returns:
            API 키 문자열 또는 None
        """
        if self.judge_model == "deepseek":
            return settings.deepseek_api_key or os.getenv("DEEPSEEK_API_KEY")
        elif self.judge_model in ("gpt-4o", "gpt-4o-mini"):
            key = os.getenv("OPENAI_API_KEY")
            if not key:
                logger.warning(
                    f"OPENAI_API_KEY not set for judge_model={self.judge_model}. "
                    f"Set OPENAI_API_KEY environment variable."
                )
            return key
        return None

    def _get_judge_base_url(self) -> Optional[str]:
        """
        Judge 모델에 맞는 API base URL을 반환합니다.

        Returns:
            Base URL 문자열 또는 None (OpenAI 기본값 사용)
        """
        if self.judge_model == "deepseek":
            return settings.deepseek_base_url
        # OpenAI 모델은 base_url 불필요 (langchain-openai 기본값 사용)
        return None

    async def _init_ragas(self) -> None:
        """RAGAS 라이브러리 초기화 (지연 로딩)"""
        if self._ragas_initialized:
            return

        api_key = self._get_judge_api_key()
        if not api_key:
            logger.warning(
                f"API key not available for judge_model={self.judge_model}, "
                f"using mock evaluation"
            )
            self._ragas_initialized = True
            return

        try:
            from langchain_openai import ChatOpenAI, OpenAIEmbeddings

            # Judge LLM 초기화
            llm_kwargs: Dict[str, Any] = {
                "model": self.llm_model,
                "api_key": api_key,
                "temperature": 0.0,
            }

            base_url = self._get_judge_base_url()
            if base_url:
                llm_kwargs["base_url"] = base_url

            self._ragas_llm = ChatOpenAI(**llm_kwargs)

            logger.info(
                f"RAGAS Judge LLM initialized: model={self.llm_model}, "
                f"provider={self.judge_model}"
                + (f", base_url={base_url}" if base_url else "")
            )

            # 임베딩 모델 (Answer Relevancy 계산용)
            # OpenAI Embeddings 사용 (GPT-4o judge 시 동일 API 키 활용)
            openai_key = os.getenv("OPENAI_API_KEY", "")
            if openai_key:
                try:
                    self._ragas_embeddings = OpenAIEmbeddings(
                        model="text-embedding-3-small",
                        api_key=openai_key,
                    )
                except Exception as e:
                    logger.warning(f"OpenAI Embeddings init failed: {e}, using None")
                    self._ragas_embeddings = None
            else:
                logger.info("OPENAI_API_KEY not set, embeddings will be None")
                self._ragas_embeddings = None

            self._ragas_initialized = True
            logger.info(
                f"RAGAS initialized successfully with {self.judge_model} judge"
            )

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

        logger.info(
            f"Starting evaluation - Samples: {len(samples)}, "
            f"Metrics: {metrics}, Judge: {self.judge_model}"
        )

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
                "judge_model": self.judge_model,
                "llm_model": self.llm_model,
            },
        )

        logger.info(
            f"Evaluation complete - Pass rate: {response.pass_rate:.2%}, "
            f"Faithfulness: {aggregate_scores.faithfulness}, "
            f"Relevancy: {aggregate_scores.answer_relevancy}, "
            f"Judge: {self.judge_model}"
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
        api_key = self._get_judge_api_key()
        if not api_key:
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


def get_ragas_evaluator(
    judge_model: Optional[str] = None,
) -> RagasEvaluator:
    """
    RagasEvaluator 인스턴스 반환 (싱글톤)

    Args:
        judge_model: Judge LLM 선택 ("deepseek" | "gpt-4o" | "gpt-4o-mini")
                     기본값: RAGAS_JUDGE_MODEL 환경변수 또는 "deepseek"

    Returns:
        RagasEvaluator 인스턴스
    """
    global _evaluator
    if _evaluator is None:
        _evaluator = RagasEvaluator(judge_model=judge_model)
    return _evaluator


def reset_ragas_evaluator() -> None:
    """싱글톤 인스턴스 초기화 (테스트 또는 judge 전환 시 사용)"""
    global _evaluator
    _evaluator = None
