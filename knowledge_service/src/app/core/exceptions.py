"""
사용자 정의 예외 클래스

에러 코드 표준에 따른 예외 정의
"""

from typing import Any, Dict, Optional


class KnowledgeServiceError(Exception):
    """Knowledge Service 기본 예외 클래스"""

    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """예외를 딕셔너리로 변환"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }


# LLM 관련 예외
class LLMError(KnowledgeServiceError):
    """LLM 호출 관련 예외"""

    def __init__(
        self,
        message: str = "LLM 호출 중 오류가 발생했습니다",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="LLM_ERROR",
            status_code=502,
            details=details,
        )


class LLMTimeoutError(LLMError):
    """LLM 타임아웃 예외"""

    def __init__(
        self,
        message: str = "LLM 응답 시간이 초과되었습니다",
        timeout: Optional[int] = None,
    ):
        super().__init__(
            message=message,
            details={"timeout_seconds": timeout} if timeout else None,
        )
        self.error_code = "LLM_TIMEOUT"


class LLMRateLimitError(LLMError):
    """LLM Rate Limit 예외"""

    def __init__(
        self,
        message: str = "LLM API 호출 한도를 초과했습니다",
        retry_after: Optional[int] = None,
    ):
        super().__init__(
            message=message,
            details={"retry_after_seconds": retry_after} if retry_after else None,
        )
        self.error_code = "LLM_RATE_LIMIT"
        self.status_code = 429


# 검색 관련 예외
class SearchError(KnowledgeServiceError):
    """검색 관련 예외"""

    def __init__(
        self,
        message: str = "검색 중 오류가 발생했습니다",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="SEARCH_ERROR",
            status_code=500,
            details=details,
        )


class ElasticsearchError(SearchError):
    """Elasticsearch 관련 예외"""

    def __init__(
        self,
        message: str = "Elasticsearch 오류가 발생했습니다",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, details=details)
        self.error_code = "ELASTICSEARCH_ERROR"


class Neo4jError(SearchError):
    """Neo4j 관련 예외"""

    def __init__(
        self,
        message: str = "Neo4j 오류가 발생했습니다",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, details=details)
        self.error_code = "NEO4J_ERROR"


# 데이터 관련 예외
class DataError(KnowledgeServiceError):
    """데이터 처리 관련 예외"""

    def __init__(
        self,
        message: str = "데이터 처리 중 오류가 발생했습니다",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="DATA_ERROR",
            status_code=400,
            details=details,
        )


class ValidationError(DataError):
    """입력값 검증 예외"""

    def __init__(
        self,
        message: str = "입력값 검증에 실패했습니다",
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if field:
            error_details["field"] = field
        super().__init__(message=message, details=error_details)
        self.error_code = "VALIDATION_ERROR"


class DocumentNotFoundError(DataError):
    """문서를 찾을 수 없는 경우"""

    def __init__(
        self,
        document_id: str,
        message: Optional[str] = None,
    ):
        super().__init__(
            message=message or f"문서를 찾을 수 없습니다: {document_id}",
            details={"document_id": document_id},
        )
        self.error_code = "DOCUMENT_NOT_FOUND"
        self.status_code = 404


# 설정 관련 예외
class ConfigurationError(KnowledgeServiceError):
    """설정 관련 예외"""

    def __init__(
        self,
        message: str = "설정 오류가 발생했습니다",
        config_key: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            status_code=500,
            details={"config_key": config_key} if config_key else None,
        )
