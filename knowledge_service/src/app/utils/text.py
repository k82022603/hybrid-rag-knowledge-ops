"""
텍스트 유틸리티

텍스트 전처리 및 변환 함수
"""

import re
from typing import Optional


def clean_text(text: str) -> str:
    """
    텍스트 정제

    - 다중 공백 제거
    - 다중 줄바꿈 정리
    - 앞뒤 공백 제거

    Args:
        text: 원본 텍스트

    Returns:
        정제된 텍스트
    """
    # 다중 공백을 단일 공백으로
    text = re.sub(r"[ \t]+", " ", text)

    # 다중 줄바꿈을 최대 2개로
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 앞뒤 공백 제거
    text = text.strip()

    return text


def truncate_text(
    text: str,
    max_length: int = 1000,
    suffix: str = "...",
) -> str:
    """
    텍스트 자르기

    Args:
        text: 원본 텍스트
        max_length: 최대 길이
        suffix: 말줄임표

    Returns:
        잘린 텍스트
    """
    if len(text) <= max_length:
        return text

    # 단어 경계에서 자르기
    truncated = text[: max_length - len(suffix)]
    last_space = truncated.rfind(" ")

    if last_space > max_length // 2:
        truncated = truncated[:last_space]

    return truncated + suffix


def count_tokens(text: str, encoding_name: str = "cl100k_base") -> int:
    """
    토큰 수 계산 (근사값)

    실제 토크나이저 없이 간단한 추정값 반환
    평균적으로 4자 = 1토큰으로 계산

    Args:
        text: 텍스트
        encoding_name: 인코딩 (무시됨, 호환성 유지)

    Returns:
        추정 토큰 수
    """
    # 한국어는 2-3자 = 1토큰, 영어는 4-5자 = 1토큰
    # 평균 3.5자 = 1토큰으로 계산
    return max(1, len(text) // 4)


def extract_json_from_text(text: str) -> Optional[str]:
    """
    텍스트에서 JSON 블록 추출

    ```json ... ``` 또는 { ... } 형태의 JSON 추출

    Args:
        text: 텍스트

    Returns:
        JSON 문자열 또는 None
    """
    # 마크다운 코드 블록에서 추출
    json_block_pattern = r"```(?:json)?\s*([\s\S]*?)```"
    match = re.search(json_block_pattern, text)
    if match:
        return match.group(1).strip()

    # 중괄호로 시작하는 JSON 추출
    brace_pattern = r"\{[\s\S]*\}"
    match = re.search(brace_pattern, text)
    if match:
        return match.group(0)

    return None
