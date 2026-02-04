"""
RAGAS 평가 데이터 모델

평가 입력/출력에 사용되는 Pydantic 모델 정의
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EvaluationSample(BaseModel):
    """평가 샘플 데이터 모델

    RAGAS 평가를 위한 단일 QA 쌍을 나타냅니다.

    Attributes:
        question: 사용자 질문
        answer: RAG 시스템이 생성한 답변
        contexts: 검색된 컨텍스트 리스트
        ground_truth: 정답 (Optional, Context Recall 측정 시 필요)
        metadata: 추가 메타데이터
    """

    question: str = Field(..., description="사용자 질문")
    answer: str = Field(..., description="RAG 시스템이 생성한 답변")
    contexts: List[str] = Field(..., description="검색된 컨텍스트 리스트")
    ground_truth: Optional[str] = Field(
        default=None, description="정답 (Context Recall 측정 시 필요)"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="추가 메타데이터")


class MetricScores(BaseModel):
    """메트릭 점수 모델

    RAGAS 평가 메트릭 점수를 나타냅니다.

    Attributes:
        faithfulness: 컨텍스트 충실도 (0.0 ~ 1.0)
        answer_relevancy: 답변 관련성 (0.0 ~ 1.0)
        context_precision: 컨텍스트 정밀도 (0.0 ~ 1.0)
        context_recall: 컨텍스트 재현율 (0.0 ~ 1.0, ground_truth 필요)
    """

    faithfulness: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="컨텍스트 충실도"
    )
    answer_relevancy: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="답변 관련성"
    )
    context_precision: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="컨텍스트 정밀도"
    )
    context_recall: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="컨텍스트 재현율"
    )

    def average(self) -> float:
        """유효한 메트릭들의 평균 계산"""
        scores = [
            s for s in [
                self.faithfulness,
                self.answer_relevancy,
                self.context_precision,
                self.context_recall,
            ] if s is not None
        ]
        return sum(scores) / len(scores) if scores else 0.0


class EvaluationResult(BaseModel):
    """단일 평가 결과 모델

    Attributes:
        sample_id: 샘플 ID
        question: 원본 질문
        scores: 메트릭 점수
        passed: 목표 점수 통과 여부
        details: 상세 평가 정보
    """

    sample_id: str = Field(..., description="샘플 ID")
    question: str = Field(..., description="원본 질문")
    scores: MetricScores = Field(..., description="메트릭 점수")
    passed: bool = Field(default=False, description="목표 점수 통과 여부")
    details: Dict[str, Any] = Field(default_factory=dict, description="상세 평가 정보")


class EvaluationRequest(BaseModel):
    """평가 요청 모델

    Attributes:
        dataset_path: 데이터셋 파일 경로 (JSON)
        samples: 인라인 평가 샘플 리스트
        metrics: 평가할 메트릭 리스트
        targets: 목표 점수 (메트릭별)
    """

    dataset_path: Optional[str] = Field(
        default=None, description="데이터셋 파일 경로 (JSON)"
    )
    samples: Optional[List[EvaluationSample]] = Field(
        default=None, description="인라인 평가 샘플 리스트"
    )
    metrics: List[str] = Field(
        default=["faithfulness", "answer_relevancy", "context_precision"],
        description="평가할 메트릭 리스트",
    )
    targets: Dict[str, float] = Field(
        default_factory=lambda: {
            "faithfulness": 0.7,
            "answer_relevancy": 0.7,
            "context_precision": 0.7,
            "context_recall": 0.7,
        },
        description="목표 점수 (메트릭별)",
    )


class EvaluationResponse(BaseModel):
    """평가 응답 모델

    Attributes:
        timestamp: 평가 시간
        total_samples: 전체 샘플 수
        passed_samples: 통과 샘플 수
        aggregate_scores: 집계 점수
        results: 개별 평가 결과 리스트
        summary: 요약 정보
    """

    timestamp: datetime = Field(default_factory=datetime.utcnow, description="평가 시간")
    total_samples: int = Field(..., description="전체 샘플 수")
    passed_samples: int = Field(..., description="통과 샘플 수")
    aggregate_scores: MetricScores = Field(..., description="집계 점수")
    results: List[EvaluationResult] = Field(..., description="개별 평가 결과 리스트")
    summary: Dict[str, Any] = Field(default_factory=dict, description="요약 정보")

    @property
    def pass_rate(self) -> float:
        """통과율 계산"""
        return self.passed_samples / self.total_samples if self.total_samples > 0 else 0.0
