"""
Knowledge Service - FastAPI 메인 애플리케이션

Graph RAG 기반 지능형 지식 검색 시스템의 AI Service 엔트리포인트
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router as api_router
from app.core.config import settings
from app.core.exceptions import KnowledgeServiceError
from app.core.logging import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    애플리케이션 라이프사이클 관리

    - startup: 리소스 초기화 (DB 연결, 모델 로딩 등)
    - shutdown: 리소스 정리 (연결 종료 등)
    """
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")

    # TODO: 리소스 초기화
    # - Elasticsearch 클라이언트 연결
    # - Neo4j 드라이버 연결
    # - BGE-M3 임베딩 모델 로딩

    yield

    # Shutdown
    logger.info("Shutting down application...")

    # TODO: 리소스 정리
    # - 연결 종료


def create_app() -> FastAPI:
    """FastAPI 애플리케이션 팩토리"""

    app = FastAPI(
        title=settings.app_name,
        description="Graph RAG 기반 지능형 지식 검색 시스템 - AI Service",
        version=settings.app_version,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url="/openapi.json" if settings.debug else None,
        lifespan=lifespan,
    )

    # CORS 미들웨어
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_hosts,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 전역 예외 핸들러
    @app.exception_handler(KnowledgeServiceError)
    async def knowledge_service_exception_handler(
        request: Request, exc: KnowledgeServiceError
    ) -> JSONResponse:
        """Knowledge Service 예외 핸들러"""
        logger.error(
            f"KnowledgeServiceError: {exc.error_code} - {exc.message}",
            extra={"details": exc.details, "path": request.url.path},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """일반 예외 핸들러"""
        logger.exception(f"Unhandled exception: {exc}", extra={"path": request.url.path})
        return JSONResponse(
            status_code=500,
            content={
                "error_code": "INTERNAL_ERROR",
                "message": "내부 서버 오류가 발생했습니다",
                "details": {"error": str(exc)} if settings.debug else {},
            },
        )

    # API 라우터 등록
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    return app


# 애플리케이션 인스턴스
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
    )
