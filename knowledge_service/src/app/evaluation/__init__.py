"""
RAGAS 평가 프레임워크 모듈

RAG 파이프라인의 품질을 측정하기 위한 평가 도구를 제공합니다.

주요 컴포넌트:
- RagasEvaluator: 정적 데이터셋 기반 RAGAS 평가
- LiveRagasEvaluator: 실제 RAG 파이프라인 연동 평가
- RagasReportGenerator: Markdown/JSON 리포트 생성

메트릭:
- Faithfulness: 답변이 컨텍스트에 충실한지 측정 (목표: 0.9)
- Answer Relevancy: 답변이 질문과 관련있는지 측정 (목표: 0.85)
- Context Precision: 검색된 컨텍스트의 정밀도 측정 (목표: 0.8)
- Context Recall: 검색된 컨텍스트의 재현율 측정 (목표: 0.7)

사용 예시:
    # 정적 데이터셋 평가
    evaluator = RagasEvaluator()
    response = await evaluator.evaluate_from_file("test_dataset.json")

    # Live 평가
    live_eval = LiveRagasEvaluator()
    response, rag_responses = await live_eval.evaluate_live(questions, ground_truths)

    # 리포트 생성
    generator = RagasReportGenerator()
    generator.save_reports(response, output_dir="reports")
"""

from app.evaluation.ragas_evaluator import RagasEvaluator, get_ragas_evaluator
from app.evaluation.models import (
    EvaluationSample,
    EvaluationResult,
    MetricScores,
    EvaluationRequest,
    EvaluationResponse,
)
from app.evaluation.report_generator import RagasReportGenerator, get_report_generator
from app.evaluation.live_evaluator import LiveRagasEvaluator, get_live_evaluator

__all__ = [
    # Core Evaluator
    "RagasEvaluator",
    "get_ragas_evaluator",
    # Live Evaluator
    "LiveRagasEvaluator",
    "get_live_evaluator",
    # Report Generator
    "RagasReportGenerator",
    "get_report_generator",
    # Models
    "EvaluationSample",
    "EvaluationResult",
    "MetricScores",
    "EvaluationRequest",
    "EvaluationResponse",
]
