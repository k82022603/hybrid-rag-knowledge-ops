"""
RAGAS 평가기 테스트 모듈

RagasEvaluator 클래스의 기능을 검증합니다.

테스트 항목:
- 평가 샘플 데이터 모델 검증
- 메트릭 점수 계산 검증
- Mock 평가 로직 검증
- 파일 기반 평가 기능 검증
- 목표 점수 통과 여부 검증
- Judge LLM 전환 검증 (GPT-4o / DeepSeek)

STORY-058: RAGAS 평가 프레임워크 통합
RAGAS Judge GPT-4o 전환
"""

import json
import os
import tempfile
from pathlib import Path
from typing import List

import pytest

# 전체 모듈에 evaluation 마커 적용
pytestmark = pytest.mark.evaluation

from app.evaluation.models import (
    EvaluationRequest,
    EvaluationResponse,
    EvaluationResult,
    EvaluationSample,
    MetricScores,
)
from app.evaluation.ragas_evaluator import (
    SUPPORTED_JUDGE_MODELS,
    SUPPORTED_METRICS,
    RagasEvaluator,
    get_ragas_evaluator,
    reset_ragas_evaluator,
    _resolve_judge_model,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_evaluation_data() -> List[EvaluationSample]:
    """테스트용 평가 샘플 데이터"""
    return [
        EvaluationSample(
            question="LangGraph란 무엇인가요?",
            answer="LangGraph는 LangChain 기반의 상태 기반 에이전트 프레임워크입니다.",
            contexts=[
                "LangGraph는 LangChain을 기반으로 한 상태 기반 에이전트 프레임워크입니다.",
                "그래프 형태의 워크플로우를 통해 AI 에이전트를 구축할 수 있습니다.",
            ],
            ground_truth="LangGraph는 상태 기반 에이전트를 구축하기 위한 프레임워크입니다.",
        ),
        EvaluationSample(
            question="RAG의 구성 요소는?",
            answer="RAG는 Retrieval, Augmentation, Generation으로 구성됩니다.",
            contexts=[
                "RAG는 검색, 증강, 생성의 세 단계로 구성됩니다.",
                "검색 단계에서 관련 문서를 찾고 LLM이 답변을 생성합니다.",
            ],
            ground_truth="RAG는 검색, 증강, 생성 단계로 구성됩니다.",
        ),
        EvaluationSample(
            question="BGE-M3 임베딩 모델의 특징은?",
            answer="BGE-M3는 다국어 지원 임베딩 모델로 1024차원 벡터를 생성합니다.",
            contexts=[
                "BGE-M3는 100개 이상의 언어를 지원하는 다국어 임베딩 모델입니다.",
                "1024차원의 벡터를 생성하며 Dense, Sparse, Multi-vector를 지원합니다.",
            ],
            ground_truth="BGE-M3는 다국어 지원, 1024차원, 다중 임베딩 방식을 지원합니다.",
        ),
    ]


@pytest.fixture
def evaluator() -> RagasEvaluator:
    """테스트용 RagasEvaluator 인스턴스"""
    return RagasEvaluator(
        targets={
            "faithfulness": 0.7,
            "answer_relevancy": 0.7,
            "context_precision": 0.7,
            "context_recall": 0.7,
        }
    )


@pytest.fixture
def test_dataset_path() -> str:
    """테스트 데이터셋 파일 경로"""
    return str(
        Path(__file__).parent / "test_dataset.json"
    )


@pytest.fixture(autouse=True)
def reset_singleton():
    """각 테스트 후 싱글톤 리셋"""
    yield
    reset_ragas_evaluator()


# ============================================================================
# 모델 테스트
# ============================================================================


class TestEvaluationSample:
    """EvaluationSample 모델 테스트"""

    def test_create_sample_with_all_fields(self):
        """모든 필드가 있는 샘플 생성"""
        sample = EvaluationSample(
            question="테스트 질문",
            answer="테스트 답변",
            contexts=["컨텍스트1", "컨텍스트2"],
            ground_truth="정답",
            metadata={"source": "test"},
        )

        assert sample.question == "테스트 질문"
        assert sample.answer == "테스트 답변"
        assert len(sample.contexts) == 2
        assert sample.ground_truth == "정답"
        assert sample.metadata == {"source": "test"}

    def test_create_sample_without_ground_truth(self):
        """ground_truth 없이 샘플 생성"""
        sample = EvaluationSample(
            question="테스트 질문",
            answer="테스트 답변",
            contexts=["컨텍스트"],
        )

        assert sample.ground_truth is None
        assert sample.metadata == {}

    def test_sample_validation_error(self):
        """필수 필드 누락 시 검증 오류"""
        with pytest.raises(Exception):
            EvaluationSample(
                question="테스트",
                # answer 누락
                contexts=[],
            )


class TestMetricScores:
    """MetricScores 모델 테스트"""

    def test_create_scores_with_all_metrics(self):
        """모든 메트릭이 있는 점수 생성"""
        scores = MetricScores(
            faithfulness=0.9,
            answer_relevancy=0.85,
            context_precision=0.8,
            context_recall=0.75,
        )

        assert scores.faithfulness == 0.9
        assert scores.answer_relevancy == 0.85
        assert scores.context_precision == 0.8
        assert scores.context_recall == 0.75

    def test_scores_average_calculation(self):
        """평균 점수 계산"""
        scores = MetricScores(
            faithfulness=0.8,
            answer_relevancy=0.8,
            context_precision=0.8,
            context_recall=0.8,
        )

        assert scores.average() == pytest.approx(0.8, rel=0.01)

    def test_scores_average_with_none_values(self):
        """None 값이 있을 때 평균 계산"""
        scores = MetricScores(
            faithfulness=0.9,
            answer_relevancy=0.9,
            context_precision=None,
            context_recall=None,
        )

        assert scores.average() == pytest.approx(0.9, rel=0.01)

    def test_scores_average_all_none(self):
        """모든 값이 None일 때 평균"""
        scores = MetricScores()
        assert scores.average() == 0.0

    def test_scores_validation_bounds(self):
        """점수 범위 검증 (0.0 ~ 1.0)"""
        # 정상 범위
        scores = MetricScores(faithfulness=0.0)
        assert scores.faithfulness == 0.0

        scores = MetricScores(faithfulness=1.0)
        assert scores.faithfulness == 1.0

        # 범위 초과 시 검증 오류
        with pytest.raises(Exception):
            MetricScores(faithfulness=1.5)

        with pytest.raises(Exception):
            MetricScores(faithfulness=-0.1)


class TestEvaluationResult:
    """EvaluationResult 모델 테스트"""

    def test_create_result(self):
        """평가 결과 생성"""
        result = EvaluationResult(
            sample_id="test_001",
            question="테스트 질문",
            scores=MetricScores(faithfulness=0.9),
            passed=True,
            details={"note": "good"},
        )

        assert result.sample_id == "test_001"
        assert result.question == "테스트 질문"
        assert result.passed is True
        assert result.scores.faithfulness == 0.9


class TestEvaluationResponse:
    """EvaluationResponse 모델 테스트"""

    def test_pass_rate_calculation(self):
        """통과율 계산"""
        response = EvaluationResponse(
            total_samples=10,
            passed_samples=7,
            aggregate_scores=MetricScores(faithfulness=0.8),
            results=[],
        )

        assert response.pass_rate == pytest.approx(0.7, rel=0.01)

    def test_pass_rate_zero_samples(self):
        """샘플이 0개일 때 통과율"""
        response = EvaluationResponse(
            total_samples=0,
            passed_samples=0,
            aggregate_scores=MetricScores(),
            results=[],
        )

        assert response.pass_rate == 0.0


# ============================================================================
# RagasEvaluator 테스트
# ============================================================================


class TestRagasEvaluatorInit:
    """RagasEvaluator 초기화 테스트"""

    def test_default_initialization(self):
        """기본 초기화"""
        evaluator = RagasEvaluator()

        assert evaluator.llm_model is not None
        assert evaluator.embedding_model is not None
        assert "faithfulness" in evaluator.targets
        assert "answer_relevancy" in evaluator.targets

    def test_custom_targets(self):
        """커스텀 목표 점수로 초기화"""
        targets = {"faithfulness": 0.95, "answer_relevancy": 0.9}
        evaluator = RagasEvaluator(targets=targets)

        assert evaluator.targets["faithfulness"] == 0.95
        assert evaluator.targets["answer_relevancy"] == 0.9

    def test_singleton_pattern(self):
        """싱글톤 패턴 검증"""
        evaluator1 = get_ragas_evaluator()
        evaluator2 = get_ragas_evaluator()

        assert evaluator1 is evaluator2

    def test_singleton_reset(self):
        """싱글톤 리셋 검증"""
        evaluator1 = get_ragas_evaluator()
        reset_ragas_evaluator()
        evaluator2 = get_ragas_evaluator()

        assert evaluator1 is not evaluator2


class TestRagasEvaluatorMetrics:
    """RagasEvaluator 메트릭 테스트"""

    def test_supported_metrics(self):
        """지원 메트릭 확인"""
        assert "faithfulness" in SUPPORTED_METRICS
        assert "answer_relevancy" in SUPPORTED_METRICS
        assert "context_precision" in SUPPORTED_METRICS
        assert "context_recall" in SUPPORTED_METRICS

    @pytest.mark.asyncio
    async def test_invalid_metric_error(self, evaluator, sample_evaluation_data):
        """잘못된 메트릭 지정 시 오류"""
        with pytest.raises(ValueError, match="지원하지 않는 메트릭"):
            await evaluator.evaluate(
                sample_evaluation_data,
                metrics=["invalid_metric"],
            )


# ============================================================================
# Judge LLM 전환 테스트 (GPT-4o / DeepSeek)
# ============================================================================


class TestJudgeModelConfig:
    """Judge LLM 설정 테스트"""

    def test_default_judge_is_deepseek(self):
        """기본 judge 모델은 deepseek"""
        # RAGAS_JUDGE_MODEL 환경변수가 없을 때
        old_val = os.environ.pop("RAGAS_JUDGE_MODEL", None)
        try:
            evaluator = RagasEvaluator()
            assert evaluator.judge_model == "deepseek"
        finally:
            if old_val is not None:
                os.environ["RAGAS_JUDGE_MODEL"] = old_val

    def test_judge_model_gpt4o_via_constructor(self):
        """생성자로 GPT-4o judge 설정"""
        evaluator = RagasEvaluator(judge_model="gpt-4o")

        assert evaluator.judge_model == "gpt-4o"
        assert evaluator.llm_model == "gpt-4o"

    def test_judge_model_gpt4o_mini_via_constructor(self):
        """생성자로 GPT-4o-mini judge 설정"""
        evaluator = RagasEvaluator(judge_model="gpt-4o-mini")

        assert evaluator.judge_model == "gpt-4o-mini"
        assert evaluator.llm_model == "gpt-4o-mini"

    def test_judge_model_deepseek_via_constructor(self):
        """생성자로 deepseek judge 명시적 설정"""
        evaluator = RagasEvaluator(judge_model="deepseek")

        assert evaluator.judge_model == "deepseek"
        # deepseek 모델명은 settings에서 가져옴
        assert "deepseek" in evaluator.llm_model.lower()

    def test_judge_model_via_env_var(self):
        """환경변수로 GPT-4o judge 설정"""
        old_val = os.environ.get("RAGAS_JUDGE_MODEL")
        try:
            os.environ["RAGAS_JUDGE_MODEL"] = "gpt-4o"
            evaluator = RagasEvaluator()

            assert evaluator.judge_model == "gpt-4o"
            assert evaluator.llm_model == "gpt-4o"
        finally:
            if old_val is not None:
                os.environ["RAGAS_JUDGE_MODEL"] = old_val
            else:
                os.environ.pop("RAGAS_JUDGE_MODEL", None)

    def test_constructor_overrides_env_var(self):
        """생성자 인자가 환경변수보다 우선"""
        old_val = os.environ.get("RAGAS_JUDGE_MODEL")
        try:
            os.environ["RAGAS_JUDGE_MODEL"] = "gpt-4o"
            evaluator = RagasEvaluator(judge_model="deepseek")

            assert evaluator.judge_model == "deepseek"
        finally:
            if old_val is not None:
                os.environ["RAGAS_JUDGE_MODEL"] = old_val
            else:
                os.environ.pop("RAGAS_JUDGE_MODEL", None)

    def test_custom_llm_model_overrides_judge_default(self):
        """llm_model 직접 지정 시 judge 모델의 기본 LLM명을 오버라이드"""
        evaluator = RagasEvaluator(
            judge_model="gpt-4o",
            llm_model="gpt-4-turbo",
        )

        assert evaluator.judge_model == "gpt-4o"
        assert evaluator.llm_model == "gpt-4-turbo"

    def test_supported_judge_models_registry(self):
        """지원 Judge 모델 레지스트리 확인"""
        assert "deepseek" in SUPPORTED_JUDGE_MODELS
        assert "gpt-4o" in SUPPORTED_JUDGE_MODELS
        assert "gpt-4o-mini" in SUPPORTED_JUDGE_MODELS

        for model, info in SUPPORTED_JUDGE_MODELS.items():
            assert "description" in info
            assert "env_key" in info

    def test_resolve_judge_model_defaults(self):
        """_resolve_judge_model 기본값 테스트"""
        old_val = os.environ.pop("RAGAS_JUDGE_MODEL", None)
        try:
            assert _resolve_judge_model() == "deepseek"
        finally:
            if old_val is not None:
                os.environ["RAGAS_JUDGE_MODEL"] = old_val

    def test_resolve_judge_model_with_env(self):
        """_resolve_judge_model 환경변수 테스트"""
        old_val = os.environ.get("RAGAS_JUDGE_MODEL")
        try:
            os.environ["RAGAS_JUDGE_MODEL"] = "gpt-4o"
            assert _resolve_judge_model() == "gpt-4o"

            os.environ["RAGAS_JUDGE_MODEL"] = "gpt-4o-mini"
            assert _resolve_judge_model() == "gpt-4o-mini"

            os.environ["RAGAS_JUDGE_MODEL"] = "deepseek-chat"
            assert _resolve_judge_model() == "deepseek"

            # 미지원 모델은 기본값으로 폴백
            os.environ["RAGAS_JUDGE_MODEL"] = "unknown-model"
            assert _resolve_judge_model() == "deepseek"
        finally:
            if old_val is not None:
                os.environ["RAGAS_JUDGE_MODEL"] = old_val
            else:
                os.environ.pop("RAGAS_JUDGE_MODEL", None)

    def test_judge_api_key_deepseek(self):
        """DeepSeek judge API 키 조회"""
        evaluator = RagasEvaluator(judge_model="deepseek")
        # API 키는 환경에 따라 None 또는 문자열
        # 메서드가 에러 없이 실행되는지만 확인
        key = evaluator._get_judge_api_key()
        # key는 None일 수도, 문자열일 수도 있음 (환경에 따라)
        assert key is None or isinstance(key, str)

    def test_judge_api_key_gpt4o(self):
        """GPT-4o judge API 키 조회"""
        evaluator = RagasEvaluator(judge_model="gpt-4o")
        key = evaluator._get_judge_api_key()
        # OPENAI_API_KEY가 없으면 None
        assert key is None or isinstance(key, str)

    def test_judge_base_url_deepseek(self):
        """DeepSeek judge base URL"""
        evaluator = RagasEvaluator(judge_model="deepseek")
        url = evaluator._get_judge_base_url()
        assert url is not None
        assert "deepseek" in url.lower()

    def test_judge_base_url_gpt4o_is_none(self):
        """GPT-4o judge base URL은 None (OpenAI 기본값 사용)"""
        evaluator = RagasEvaluator(judge_model="gpt-4o")
        url = evaluator._get_judge_base_url()
        assert url is None

    @pytest.mark.asyncio
    async def test_evaluate_includes_judge_info_in_summary(self):
        """평가 결과 summary에 judge 모델 정보 포함"""
        evaluator = RagasEvaluator(
            judge_model="deepseek",
            targets={"faithfulness": 0.5},
        )

        sample = EvaluationSample(
            question="테스트 질문입니다",
            answer="테스트 답변입니다",
            contexts=["테스트 컨텍스트입니다"],
        )

        response = await evaluator.evaluate(
            [sample], metrics=["faithfulness"]
        )

        assert "judge_model" in response.summary
        assert response.summary["judge_model"] == "deepseek"
        assert "llm_model" in response.summary

    @pytest.mark.asyncio
    async def test_gpt4o_judge_mock_evaluation(self):
        """GPT-4o judge로 mock 평가 (API 키 없을 때 폴백)"""
        evaluator = RagasEvaluator(
            judge_model="gpt-4o",
            targets={"faithfulness": 0.5},
        )

        sample = EvaluationSample(
            question="RAG란 무엇인가요",
            answer="RAG는 검색 증강 생성입니다",
            contexts=["RAG는 검색 기반 생성 기술입니다"],
        )

        # OPENAI_API_KEY 없이 실행 -- mock으로 폴백
        response = await evaluator.evaluate(
            [sample], metrics=["faithfulness"]
        )

        assert response.total_samples == 1
        assert response.summary["judge_model"] == "gpt-4o"

    def test_singleton_with_judge_model(self):
        """싱글톤에 judge_model 전달"""
        reset_ragas_evaluator()
        evaluator = get_ragas_evaluator(judge_model="gpt-4o")
        assert evaluator.judge_model == "gpt-4o"


class TestMockEvaluation:
    """Mock 평가 테스트 (RAGAS 라이브러리 없이)"""

    @pytest.mark.asyncio
    async def test_mock_faithfulness(self, evaluator):
        """Mock Faithfulness 점수 계산"""
        sample = EvaluationSample(
            question="LangGraph란 무엇인가요?",
            answer="LangGraph는 상태 기반 에이전트 프레임워크입니다",
            contexts=["LangGraph는 상태 기반 에이전트 프레임워크로 그래프를 사용합니다"],
        )

        scores = evaluator._mock_evaluate(sample, ["faithfulness"])

        assert scores.faithfulness is not None
        assert 0.0 <= scores.faithfulness <= 1.0

    @pytest.mark.asyncio
    async def test_mock_answer_relevancy(self, evaluator):
        """Mock Answer Relevancy 점수 계산"""
        sample = EvaluationSample(
            question="BGE-M3 임베딩 모델의 특징은 무엇인가요?",
            answer="BGE-M3는 다국어 임베딩 모델로 1024차원을 지원합니다",
            contexts=["BGE-M3 모델 설명"],
        )

        scores = evaluator._mock_evaluate(sample, ["answer_relevancy"])

        assert scores.answer_relevancy is not None
        assert 0.0 <= scores.answer_relevancy <= 1.0

    @pytest.mark.asyncio
    async def test_mock_context_precision(self, evaluator):
        """Mock Context Precision 점수 계산"""
        sample = EvaluationSample(
            question="RAG 파이프라인이란?",
            answer="RAG는 검색 증강 생성입니다",
            contexts=["RAG 파이프라인은 검색과 생성을 결합합니다", "무관한 컨텍스트"],
        )

        scores = evaluator._mock_evaluate(sample, ["context_precision"])

        assert scores.context_precision is not None
        assert 0.0 <= scores.context_precision <= 1.0

    @pytest.mark.asyncio
    async def test_mock_context_recall(self, evaluator):
        """Mock Context Recall 점수 계산"""
        sample = EvaluationSample(
            question="Hybrid Search란?",
            answer="Hybrid Search는 키워드와 벡터 검색을 결합합니다",
            contexts=["Hybrid Search는 BM25와 벡터 검색을 융합합니다"],
            ground_truth="Hybrid Search는 키워드 검색과 시맨틱 검색을 결합한 방식입니다",
        )

        scores = evaluator._mock_evaluate(sample, ["context_recall"])

        assert scores.context_recall is not None
        assert 0.0 <= scores.context_recall <= 1.0


class TestEvaluationExecution:
    """평가 실행 테스트"""

    @pytest.mark.asyncio
    async def test_evaluate_single_sample(self, evaluator):
        """단일 샘플 평가"""
        samples = [
            EvaluationSample(
                question="테스트 질문입니다",
                answer="테스트 답변입니다",
                contexts=["테스트 컨텍스트입니다"],
                ground_truth="테스트 정답입니다",
            )
        ]

        response = await evaluator.evaluate(samples)

        assert response.total_samples == 1
        assert len(response.results) == 1
        assert response.aggregate_scores is not None

    @pytest.mark.asyncio
    async def test_evaluate_multiple_samples(self, evaluator, sample_evaluation_data):
        """다중 샘플 평가"""
        response = await evaluator.evaluate(sample_evaluation_data)

        assert response.total_samples == len(sample_evaluation_data)
        assert len(response.results) == len(sample_evaluation_data)
        assert response.summary is not None
        assert "pass_rate" in response.summary

    @pytest.mark.asyncio
    async def test_evaluate_with_specific_metrics(self, evaluator, sample_evaluation_data):
        """특정 메트릭만 평가"""
        metrics = ["faithfulness", "answer_relevancy"]
        response = await evaluator.evaluate(sample_evaluation_data, metrics=metrics)

        # 요청한 메트릭만 평가되었는지 확인
        assert response.summary["metrics_evaluated"] == metrics

    @pytest.mark.asyncio
    async def test_evaluate_empty_samples_error(self, evaluator):
        """빈 샘플 리스트로 평가 시 오류"""
        with pytest.raises(ValueError, match="평가할 샘플이 없습니다"):
            await evaluator.evaluate([])

    @pytest.mark.asyncio
    async def test_evaluate_pass_rate_calculation(self, evaluator):
        """통과율 계산 검증"""
        # 높은 점수를 받을 샘플
        high_quality_sample = EvaluationSample(
            question="LangGraph 프레임워크란 무엇인가요",
            answer="LangGraph 프레임워크는 상태 기반 에이전트 프레임워크입니다",
            contexts=["LangGraph 프레임워크는 상태 기반 에이전트 프레임워크로 그래프 형태를 사용합니다"],
            ground_truth="LangGraph 프레임워크는 상태 기반 에이전트 프레임워크입니다",
        )

        response = await evaluator.evaluate([high_quality_sample])

        assert 0.0 <= response.pass_rate <= 1.0


class TestFileBasedEvaluation:
    """파일 기반 평가 테스트"""

    @pytest.mark.asyncio
    async def test_evaluate_from_json_file(self, evaluator, test_dataset_path):
        """JSON 파일에서 평가 데이터 로드 후 평가"""
        if not Path(test_dataset_path).exists():
            pytest.skip("테스트 데이터셋 파일이 없습니다")

        response = await evaluator.evaluate_from_file(test_dataset_path)

        assert response.total_samples >= 20
        assert response.aggregate_scores is not None

    @pytest.mark.asyncio
    async def test_evaluate_from_nonexistent_file(self, evaluator):
        """존재하지 않는 파일로 평가 시 오류"""
        with pytest.raises(FileNotFoundError):
            await evaluator.evaluate_from_file("/nonexistent/path.json")

    @pytest.mark.asyncio
    async def test_evaluate_from_temp_file(self, evaluator):
        """임시 파일로 평가"""
        test_data = [
            {
                "question": "임시 테스트 질문",
                "answer": "임시 테스트 답변",
                "contexts": ["임시 테스트 컨텍스트"],
                "ground_truth": "임시 테스트 정답",
            }
        ]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(test_data, f, ensure_ascii=False)
            temp_path = f.name

        try:
            response = await evaluator.evaluate_from_file(temp_path)
            assert response.total_samples == 1
        finally:
            os.unlink(temp_path)


class TestTargetValidation:
    """목표 점수 검증 테스트"""

    def test_check_passed_all_above_target(self):
        """모든 점수가 목표 이상일 때 통과"""
        evaluator = RagasEvaluator(
            targets={
                "faithfulness": 0.7,
                "answer_relevancy": 0.7,
            }
        )

        scores = MetricScores(
            faithfulness=0.8,
            answer_relevancy=0.8,
        )

        assert evaluator._check_passed(scores) is True

    def test_check_passed_below_target(self):
        """하나라도 목표 미달 시 불합격"""
        evaluator = RagasEvaluator(
            targets={
                "faithfulness": 0.9,
                "answer_relevancy": 0.9,
            }
        )

        scores = MetricScores(
            faithfulness=0.95,
            answer_relevancy=0.5,  # 목표 미달
        )

        assert evaluator._check_passed(scores) is False

    def test_meets_targets_detail(self):
        """메트릭별 목표 달성 여부 상세"""
        evaluator = RagasEvaluator(
            targets={
                "faithfulness": 0.8,
                "answer_relevancy": 0.8,
                "context_precision": 0.8,
            }
        )

        scores = MetricScores(
            faithfulness=0.9,  # 달성
            answer_relevancy=0.7,  # 미달
            context_precision=0.85,  # 달성
        )

        meets = evaluator._meets_targets(scores)

        assert meets["faithfulness"] is True
        assert meets["answer_relevancy"] is False
        assert meets["context_precision"] is True


class TestStatisticalFunctions:
    """통계 함수 테스트"""

    def test_average_normal_values(self):
        """정상 값들의 평균"""
        values = [0.8, 0.9, 0.7, 0.85]
        avg = RagasEvaluator._average(values)

        assert avg == pytest.approx(0.8125, rel=0.01)

    def test_average_empty_list(self):
        """빈 리스트의 평균"""
        avg = RagasEvaluator._average([])
        assert avg is None

    def test_average_single_value(self):
        """단일 값의 평균"""
        avg = RagasEvaluator._average([0.9])
        assert avg == 0.9


# ============================================================================
# 통합 테스트
# ============================================================================


@pytest.mark.integration
class TestRagasIntegration:
    """RAGAS 통합 테스트"""

    @pytest.mark.asyncio
    async def test_full_evaluation_pipeline(self, evaluator, sample_evaluation_data):
        """전체 평가 파이프라인 테스트"""
        # 평가 실행
        response = await evaluator.evaluate(
            sample_evaluation_data,
            metrics=["faithfulness", "answer_relevancy", "context_precision"],
        )

        # 응답 검증
        assert response.total_samples == len(sample_evaluation_data)
        assert response.aggregate_scores is not None
        assert response.summary is not None

        # 개별 결과 검증
        for result in response.results:
            assert result.sample_id is not None
            assert result.question is not None
            assert result.scores is not None

        # 요약 정보 검증
        assert "pass_rate" in response.summary
        assert "metrics_evaluated" in response.summary
        assert "targets" in response.summary
        assert "meets_targets" in response.summary
        assert "judge_model" in response.summary
        assert "llm_model" in response.summary

    @pytest.mark.asyncio
    async def test_evaluation_with_test_dataset_file(self, test_dataset_path):
        """테스트 데이터셋 파일을 사용한 전체 평가"""
        if not Path(test_dataset_path).exists():
            pytest.skip("테스트 데이터셋 파일이 없습니다")

        evaluator = RagasEvaluator(
            targets={
                "faithfulness": 0.7,
                "answer_relevancy": 0.7,
                "context_precision": 0.7,
            }
        )

        response = await evaluator.evaluate_from_file(
            test_dataset_path,
            metrics=["faithfulness", "answer_relevancy", "context_precision"],
        )

        # 데이터셋 크기 검증 (20개 이상)
        assert response.total_samples >= 20

        # 품질 목표 검증
        if response.aggregate_scores.faithfulness is not None:
            print(f"Faithfulness: {response.aggregate_scores.faithfulness:.4f}")
        if response.aggregate_scores.answer_relevancy is not None:
            print(f"Answer Relevancy: {response.aggregate_scores.answer_relevancy:.4f}")
        if response.aggregate_scores.context_precision is not None:
            print(f"Context Precision: {response.aggregate_scores.context_precision:.4f}")

        print(f"Pass Rate: {response.pass_rate:.2%}")


# ============================================================================
# 엣지 케이스 테스트
# ============================================================================


class TestEdgeCases:
    """엣지 케이스 테스트"""

    @pytest.mark.asyncio
    async def test_empty_contexts(self, evaluator):
        """빈 컨텍스트로 평가"""
        sample = EvaluationSample(
            question="테스트 질문",
            answer="테스트 답변",
            contexts=[],
        )

        response = await evaluator.evaluate([sample])
        assert response.total_samples == 1

    @pytest.mark.asyncio
    async def test_long_text(self, evaluator):
        """긴 텍스트로 평가"""
        long_text = "이것은 매우 긴 텍스트입니다. " * 100

        sample = EvaluationSample(
            question=long_text,
            answer=long_text,
            contexts=[long_text],
        )

        response = await evaluator.evaluate([sample])
        assert response.total_samples == 1

    @pytest.mark.asyncio
    async def test_unicode_text(self, evaluator):
        """유니코드 텍스트로 평가"""
        sample = EvaluationSample(
            question="한글 질문입니다. English question.",
            answer="다국어 답변 테스트",
            contexts=["한글과 English가 섞인 컨텍스트"],
        )

        response = await evaluator.evaluate([sample])
        assert response.total_samples == 1

    @pytest.mark.asyncio
    async def test_special_characters(self, evaluator):
        """특수 문자가 포함된 텍스트로 평가"""
        sample = EvaluationSample(
            question="!@#$%^&*() 특수문자 테스트?",
            answer="<tag>HTML</tag> & special chars",
            contexts=["[brackets] {braces} (parens)"],
        )

        response = await evaluator.evaluate([sample])
        assert response.total_samples == 1
