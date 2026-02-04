#!/usr/bin/env python3
"""
RAGAS 평가 실행 스크립트 (v2.0)

RAG 파이프라인의 품질을 RAGAS 메트릭으로 측정합니다.

주요 기능:
- 정적 데이터셋 평가 (기존 기능)
- Live RAG 파이프라인 평가 (신규)
- Markdown/JSON 리포트 자동 생성
- CLI 인터페이스

사용법:
    # 기본 테스트 데이터셋으로 평가
    python scripts/run_ragas_eval.py

    # 커스텀 데이터셋으로 평가
    python scripts/run_ragas_eval.py --dataset /path/to/dataset.json

    # 특정 메트릭만 평가
    python scripts/run_ragas_eval.py --metrics faithfulness,answer_relevancy

    # Markdown + JSON 리포트 저장
    python scripts/run_ragas_eval.py --output-dir ./reports --format both

    # Live 모드 (실제 RAG 파이프라인 실행)
    python scripts/run_ragas_eval.py --live --questions questions.json

    # Mock 모드로 평가 (API 키 없이)
    python scripts/run_ragas_eval.py --mock

환경변수:
    DEEPSEEK_API_KEY: DeepSeek API 키 (없으면 Mock 평가)
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# 프로젝트 루트를 Python 경로에 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from app.evaluation.models import EvaluationResponse, MetricScores
from app.evaluation.ragas_evaluator import RagasEvaluator, SUPPORTED_METRICS
from app.evaluation.report_generator import RagasReportGenerator


# ============================================================================
# 기본 설정
# ============================================================================

DEFAULT_DATASET_PATH = PROJECT_ROOT / "src/tests/evaluation/test_dataset.json"

DEFAULT_TARGETS = {
    "faithfulness": 0.7,
    "answer_relevancy": 0.7,
    "context_precision": 0.7,
    "context_recall": 0.7,
}

# 콘솔 색상 코드
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    END = "\033[0m"


# ============================================================================
# 유틸리티 함수
# ============================================================================


def print_header(text: str) -> None:
    """헤더 출력"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}\n")


def print_section(text: str) -> None:
    """섹션 헤더 출력"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}--- {text} ---{Colors.END}")


def print_metric(name: str, value: Optional[float], target: float) -> None:
    """메트릭 결과 출력"""
    if value is None:
        print(f"  {name:20}: {Colors.YELLOW}N/A{Colors.END}")
        return

    passed = value >= target
    color = Colors.GREEN if passed else Colors.RED
    status = "PASS" if passed else "FAIL"

    print(
        f"  {name:20}: {color}{value:.4f}{Colors.END} "
        f"(target: {target:.2f}) [{color}{status}{Colors.END}]"
    )


def print_summary(response: EvaluationResponse, targets: Dict[str, float]) -> None:
    """평가 결과 요약 출력"""
    print_section("평가 결과 요약")

    scores = response.aggregate_scores
    print_metric("Faithfulness", scores.faithfulness, targets.get("faithfulness", 0.7))
    print_metric("Answer Relevancy", scores.answer_relevancy, targets.get("answer_relevancy", 0.7))
    print_metric("Context Precision", scores.context_precision, targets.get("context_precision", 0.7))
    print_metric("Context Recall", scores.context_recall, targets.get("context_recall", 0.7))

    print(f"\n  {'통과율':20}: {Colors.BOLD}{response.pass_rate:.2%}{Colors.END}")
    print(f"  {'통과 샘플':20}: {response.passed_samples}/{response.total_samples}")

    # 전체 합격 여부
    meets_targets = response.summary.get("meets_targets", {})
    all_passed = all(meets_targets.values()) if meets_targets else False

    if all_passed:
        print(f"\n{Colors.GREEN}{Colors.BOLD}[SUCCESS] 모든 목표 점수를 달성했습니다!{Colors.END}")
    else:
        failed_metrics = [m for m, passed in meets_targets.items() if not passed]
        print(f"\n{Colors.RED}{Colors.BOLD}[FAIL] 목표 미달 메트릭: {', '.join(failed_metrics)}{Colors.END}")


def save_results(
    response: EvaluationResponse,
    output_path: Optional[str] = None,
    output_dir: Optional[str] = None,
    output_format: str = "both",
    targets: Optional[Dict[str, float]] = None,
) -> Dict[str, str]:
    """결과를 파일로 저장

    Args:
        response: 평가 응답
        output_path: 단일 JSON 파일 경로 (레거시 호환)
        output_dir: 출력 디렉토리 (Markdown + JSON)
        output_format: 'json', 'markdown', 'both'
        targets: 목표 점수 딕셔너리

    Returns:
        저장된 파일 경로 딕셔너리
    """
    saved_files = {}

    # 레거시 호환: 단일 파일 경로 지정 시
    if output_path:
        result_dict = {
            "timestamp": response.timestamp.isoformat(),
            "total_samples": response.total_samples,
            "passed_samples": response.passed_samples,
            "pass_rate": response.pass_rate,
            "aggregate_scores": {
                "faithfulness": response.aggregate_scores.faithfulness,
                "answer_relevancy": response.aggregate_scores.answer_relevancy,
                "context_precision": response.aggregate_scores.context_precision,
                "context_recall": response.aggregate_scores.context_recall,
                "average": response.aggregate_scores.average(),
            },
            "summary": response.summary,
            "results": [
                {
                    "sample_id": r.sample_id,
                    "question": r.question,
                    "passed": r.passed,
                    "scores": {
                        "faithfulness": r.scores.faithfulness,
                        "answer_relevancy": r.scores.answer_relevancy,
                        "context_precision": r.scores.context_precision,
                        "context_recall": r.scores.context_recall,
                    },
                    "details": r.details,
                }
                for r in response.results
            ],
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result_dict, f, ensure_ascii=False, indent=2)

        print(f"\n{Colors.GREEN}결과가 저장되었습니다: {output_path}{Colors.END}")
        saved_files["json"] = output_path

    # 새 기능: 디렉토리에 Markdown + JSON 저장
    if output_dir:
        generator = RagasReportGenerator()
        saved_files = generator.save_reports(
            response=response,
            output_dir=output_dir,
            targets=targets,
        )

        for fmt, path in saved_files.items():
            print(f"{Colors.GREEN}{fmt.upper()} 리포트 저장: {path}{Colors.END}")

    return saved_files


# ============================================================================
# 메인 실행 로직
# ============================================================================


async def run_evaluation(
    dataset_path: str,
    metrics: List[str],
    targets: Dict[str, float],
    output_path: Optional[str] = None,
    output_dir: Optional[str] = None,
    verbose: bool = False,
) -> EvaluationResponse:
    """정적 데이터셋 평가 실행"""
    print_header("RAGAS 평가 실행")

    # 환경 정보 출력
    print_section("환경 정보")
    has_api_key = bool(os.getenv("DEEPSEEK_API_KEY"))
    mode = "RAGAS (LLM 기반)" if has_api_key else "Mock (휴리스틱 기반)"
    print(f"  평가 모드: {Colors.BOLD}{mode}{Colors.END}")
    print(f"  데이터셋: {dataset_path}")
    print(f"  메트릭: {', '.join(metrics)}")

    # 평가기 초기화
    print_section("평가기 초기화")
    evaluator = RagasEvaluator(targets=targets)
    print(f"  LLM 모델: {evaluator.llm_model}")
    print(f"  임베딩 모델: {evaluator.embedding_model}")

    # 데이터셋 로드 및 평가 실행
    print_section("평가 실행 중...")

    start_time = datetime.now()
    response = await evaluator.evaluate_from_file(dataset_path, metrics=metrics)
    elapsed = datetime.now() - start_time

    print(f"  완료! (소요 시간: {elapsed.total_seconds():.2f}초)")

    # 상세 결과 출력 (verbose 모드)
    if verbose:
        print_section("개별 샘플 결과")
        for result in response.results:
            status = f"{Colors.GREEN}PASS{Colors.END}" if result.passed else f"{Colors.RED}FAIL{Colors.END}"
            print(f"\n  [{status}] {result.sample_id}")
            print(f"    질문: {result.question[:50]}...")
            if result.scores.faithfulness is not None:
                print(f"    Faithfulness: {result.scores.faithfulness:.4f}")
            if result.scores.answer_relevancy is not None:
                print(f"    Answer Relevancy: {result.scores.answer_relevancy:.4f}")

    # 요약 출력
    print_summary(response, targets)

    # 결과 저장
    if output_path or output_dir:
        save_results(
            response=response,
            output_path=output_path,
            output_dir=output_dir,
            targets=targets,
        )

    return response


async def run_live_evaluation(
    questions_path: str,
    metrics: List[str],
    targets: Dict[str, float],
    top_k: int = 5,
    output_dir: Optional[str] = None,
    verbose: bool = False,
) -> EvaluationResponse:
    """Live RAG 파이프라인 평가 실행"""
    from app.evaluation.live_evaluator import LiveRagasEvaluator

    print_header("RAGAS Live 평가 실행")

    # 환경 정보 출력
    print_section("환경 정보")
    has_api_key = bool(os.getenv("DEEPSEEK_API_KEY"))
    mode = "Live + RAGAS" if has_api_key else "Live + Mock"
    print(f"  평가 모드: {Colors.BOLD}{mode}{Colors.END}")
    print(f"  질문 파일: {questions_path}")
    print(f"  검색 top_k: {top_k}")
    print(f"  메트릭: {', '.join(metrics)}")

    # 평가기 초기화
    print_section("평가기 초기화")
    evaluator = LiveRagasEvaluator(targets=targets)
    print(f"  RAG Workflow 연동: 활성화")

    # 평가 실행
    print_section("Live 평가 실행 중...")
    print(f"  {Colors.YELLOW}(실제 RAG 파이프라인이 실행됩니다){Colors.END}")

    start_time = datetime.now()

    try:
        response, rag_responses = await evaluator.evaluate_from_questions_file(
            file_path=questions_path,
            top_k=top_k,
            metrics=metrics,
        )
    except Exception as e:
        print(f"\n{Colors.RED}Live 평가 실패: {e}{Colors.END}")
        print(f"{Colors.YELLOW}Hint: 서비스가 실행 중인지 확인하세요.{Colors.END}")
        raise

    elapsed = datetime.now() - start_time

    print(f"  완료! (소요 시간: {elapsed.total_seconds():.2f}초)")

    # RAG 응답 통계
    if verbose:
        print_section("RAG 파이프라인 응답")
        success_count = sum(1 for r in rag_responses if not r.get("error"))
        print(f"  성공: {success_count}/{len(rag_responses)}")
        avg_latency = sum(r["latency_ms"] for r in rag_responses if r["latency_ms"]) / max(success_count, 1)
        print(f"  평균 레이턴시: {avg_latency:.1f}ms")

        for idx, r in enumerate(rag_responses[:5]):
            if r.get("error"):
                print(f"\n  [{Colors.RED}ERROR{Colors.END}] Q{idx+1}: {r['question'][:40]}...")
            else:
                print(f"\n  [{Colors.GREEN}OK{Colors.END}] Q{idx+1}: {r['question'][:40]}...")
                print(f"    답변 길이: {len(r['answer'])}, 컨텍스트: {len(r['contexts'])}개")

    # 요약 출력
    print_summary(response, targets)

    # 결과 저장
    if output_dir:
        save_results(
            response=response,
            output_dir=output_dir,
            targets=targets,
        )

        # RAG 응답도 별도 저장
        rag_output_path = Path(output_dir) / f"rag_responses_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.json"
        with open(rag_output_path, "w", encoding="utf-8") as f:
            json.dump(rag_responses, f, ensure_ascii=False, indent=2)
        print(f"{Colors.GREEN}RAG 응답 저장: {rag_output_path}{Colors.END}")

    return response


def parse_args() -> argparse.Namespace:
    """명령행 인자 파싱"""
    parser = argparse.ArgumentParser(
        description="RAGAS 평가 실행 스크립트 v2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 정적 데이터셋 평가 (기본)
  python scripts/run_ragas_eval.py

  # 커스텀 데이터셋 + 리포트 저장
  python scripts/run_ragas_eval.py --dataset custom.json --output-dir ./reports

  # 특정 메트릭만 평가
  python scripts/run_ragas_eval.py --metrics faithfulness,answer_relevancy --verbose

  # Live 모드 (실제 RAG 파이프라인 실행)
  python scripts/run_ragas_eval.py --live --questions questions.json --output-dir ./reports

  # Mock 모드 (API 키 없이 휴리스틱 평가)
  python scripts/run_ragas_eval.py --mock
        """,
    )

    # 기본 옵션
    parser.add_argument(
        "--dataset",
        type=str,
        default=str(DEFAULT_DATASET_PATH),
        help=f"평가 데이터셋 경로 (기본: {DEFAULT_DATASET_PATH})",
    )

    parser.add_argument(
        "--metrics",
        type=str,
        default="faithfulness,answer_relevancy,context_precision",
        help="평가할 메트릭 (쉼표로 구분, 기본: faithfulness,answer_relevancy,context_precision)",
    )

    # 출력 옵션
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="결과 저장 경로 (JSON, 레거시 호환)",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="리포트 출력 디렉토리 (Markdown + JSON 생성)",
    )

    # 목표 점수
    parser.add_argument(
        "--faithfulness-target",
        type=float,
        default=0.9,
        help="Faithfulness 목표 점수 (기본: 0.9)",
    )

    parser.add_argument(
        "--relevancy-target",
        type=float,
        default=0.85,
        help="Answer Relevancy 목표 점수 (기본: 0.85)",
    )

    parser.add_argument(
        "--precision-target",
        type=float,
        default=0.8,
        help="Context Precision 목표 점수 (기본: 0.8)",
    )

    parser.add_argument(
        "--recall-target",
        type=float,
        default=0.7,
        help="Context Recall 목표 점수 (기본: 0.7)",
    )

    # Live 모드 옵션
    parser.add_argument(
        "--live",
        action="store_true",
        help="Live 모드: 실제 RAG 파이프라인 실행",
    )

    parser.add_argument(
        "--questions",
        type=str,
        default=None,
        help="Live 모드용 질문 파일 경로 (JSON)",
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Live 모드 검색 결과 수 (기본: 5)",
    )

    # 기타 옵션
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="상세 결과 출력",
    )

    parser.add_argument(
        "--mock",
        action="store_true",
        help="Mock 모드로 실행 (API 키 무시, 휴리스틱 평가)",
    )

    return parser.parse_args()


def main() -> int:
    """메인 함수"""
    args = parse_args()

    # Mock 모드면 API 키 제거
    if args.mock:
        os.environ.pop("DEEPSEEK_API_KEY", None)
        os.environ.pop("OPENAI_API_KEY", None)

    # 메트릭 파싱
    metrics = [m.strip() for m in args.metrics.split(",")]
    invalid_metrics = set(metrics) - SUPPORTED_METRICS
    if invalid_metrics:
        print(f"{Colors.RED}오류: 지원하지 않는 메트릭: {invalid_metrics}{Colors.END}")
        print(f"지원 메트릭: {', '.join(SUPPORTED_METRICS)}")
        return 1

    # 목표 점수 설정
    targets = {
        "faithfulness": args.faithfulness_target,
        "answer_relevancy": args.relevancy_target,
        "context_precision": args.precision_target,
        "context_recall": args.recall_target,
    }

    try:
        # Live 모드
        if args.live:
            # 질문 파일 확인
            if not args.questions:
                print(f"{Colors.RED}오류: --live 모드에서는 --questions 파일이 필요합니다{Colors.END}")
                return 1

            if not Path(args.questions).exists():
                print(f"{Colors.RED}오류: 질문 파일을 찾을 수 없습니다: {args.questions}{Colors.END}")
                return 1

            response = asyncio.run(
                run_live_evaluation(
                    questions_path=args.questions,
                    metrics=metrics,
                    targets=targets,
                    top_k=args.top_k,
                    output_dir=args.output_dir,
                    verbose=args.verbose,
                )
            )

        # 정적 데이터셋 평가 (기본)
        else:
            # 데이터셋 파일 확인
            if not Path(args.dataset).exists():
                print(f"{Colors.RED}오류: 데이터셋 파일을 찾을 수 없습니다: {args.dataset}{Colors.END}")
                return 1

            response = asyncio.run(
                run_evaluation(
                    dataset_path=args.dataset,
                    metrics=metrics,
                    targets=targets,
                    output_path=args.output,
                    output_dir=args.output_dir,
                    verbose=args.verbose,
                )
            )

        # 목표 달성 여부에 따른 종료 코드
        meets_targets = response.summary.get("meets_targets", {})
        all_passed = all(meets_targets.values()) if meets_targets else False

        return 0 if all_passed else 1

    except FileNotFoundError as e:
        print(f"{Colors.RED}파일 오류: {e}{Colors.END}")
        return 1
    except Exception as e:
        print(f"{Colors.RED}실행 오류: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
