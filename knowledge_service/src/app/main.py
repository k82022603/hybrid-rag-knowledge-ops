"""
Knowledge Service - FastAPI 메인 애플리케이션

Graph RAG 기반 지능형 지식 검색 시스템의 AI Service 엔트리포인트
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router as api_router
from app.core.config import settings
from app.core.exceptions import KnowledgeServiceError
from app.core.logging import get_logger

logger = get_logger(__name__)


async def _connect_with_retry(
    connect_fn,
    name: str,
    max_retries: int = 5,
    base_delay: float = 3.0,
) -> Optional[Any]:
    """지수 백오프를 사용한 연결 재시도

    Args:
        connect_fn: 연결을 수행하는 async callable
        name: 서비스 이름 (로깅용)
        max_retries: 최대 재시도 횟수
        base_delay: 초기 대기 시간 (초)

    Returns:
        연결된 클라이언트 또는 None
    """
    for attempt in range(max_retries):
        try:
            client = await connect_fn()
            logger.info(f"{name} 연결 성공 (시도 {attempt + 1}/{max_retries})")
            return client
        except Exception as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    f"{name} 연결 실패 ({attempt + 1}/{max_retries}): {e}, "
                    f"{delay}초 후 재시도"
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    f"{name} 연결 최종 실패 ({max_retries}회 시도): {e}"
                )
    return None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    애플리케이션 라이프사이클 관리

    - startup: 리소스 초기화 (DB 연결, 모델 로딩, 백그라운드 워커 등)
    - shutdown: 리소스 정리 (연결 종료 등)
    """
    import os

    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")

    # 리소스 초기화
    es_client = None
    neo4j_driver = None
    background_worker = None

    try:
        # Elasticsearch 클라이언트 연결 (지수 백오프 재시도)
        async def _connect_elasticsearch():
            from elasticsearch import AsyncElasticsearch

            client = AsyncElasticsearch(
                hosts=[f"http://{settings.elasticsearch_host}:{settings.elasticsearch_port}"],
            )
            health = await client.cluster.health(timeout="5s")
            logger.info(
                f"Elasticsearch cluster={health.get('cluster_name')}, "
                f"status={health.get('status')}"
            )
            return client

        es_client = await _connect_with_retry(
            _connect_elasticsearch, "Elasticsearch", max_retries=5, base_delay=3.0
        )
        app.state.es_client = es_client

        # Neo4j 드라이버 연결 (지수 백오프 재시도)
        async def _connect_neo4j():
            from neo4j import AsyncGraphDatabase

            driver = AsyncGraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password),
            )
            async with driver.session() as session:
                result = await session.run("RETURN 1 AS ping")
                await result.single()
            logger.info(f"Neo4j connected: {settings.neo4j_uri}")
            return driver

        neo4j_driver = await _connect_with_retry(
            _connect_neo4j, "Neo4j", max_retries=5, base_delay=3.0
        )
        app.state.neo4j_driver = neo4j_driver

        # SearchService 초기화 (ES + Neo4j 클라이언트 주입)
        from app.services.search import init_search_service
        search_service = init_search_service(
            es_client=app.state.es_client,
            neo4j_driver=app.state.neo4j_driver,
        )
        app.state.search_service = search_service

        # DocumentRepository 초기화 (PostgreSQL 연결)
        try:
            from app.services.document_repository import init_document_repository

            doc_repo = await init_document_repository()
            app.state.document_repository = doc_repo
            logger.info("DocumentRepository initialized (PostgreSQL)")
        except Exception as e:
            logger.warning(f"DocumentRepository init failed (non-critical): {e}")
            app.state.document_repository = None

        # EmbeddingService 초기화 (lazy load, 실제 로딩은 첫 요청 시)
        logger.info("EmbeddingService will be initialized on first request")

        # 백그라운드 워커 시작 (환경변수로 제어)
        enable_worker = os.getenv("ENABLE_BACKGROUND_WORKER", "false").lower() == "true"
        if enable_worker:
            try:
                from app.api.routes.documents import _get_document_store
                from app.services.background_worker import BackgroundWorker

                worker_interval = float(os.getenv("WORKER_POLL_INTERVAL", "30.0"))
                worker_batch_size = int(os.getenv("WORKER_BATCH_SIZE", "5"))

                background_worker = BackgroundWorker(
                    document_store=_get_document_store(),
                    poll_interval=worker_interval,
                    batch_size=worker_batch_size,
                    enable_neo4j=(app.state.neo4j_driver is not None),
                    enable_entity_extraction=True,
                )
                await background_worker.start()
                app.state.background_worker = background_worker
                logger.info(
                    f"Background worker started: "
                    f"interval={worker_interval}s, batch_size={worker_batch_size}"
                )
            except Exception as e:
                logger.warning(f"Background worker start failed (non-critical): {e}")
                app.state.background_worker = None
        else:
            logger.info("Background worker disabled (set ENABLE_BACKGROUND_WORKER=true to enable)")
            app.state.background_worker = None

        yield

    finally:
        # Shutdown
        logger.info("Shutting down application...")

        # 백그라운드 워커 중지
        if background_worker is not None:
            try:
                await background_worker.stop()
                logger.info("Background worker stopped")
            except Exception as e:
                logger.warning(f"Error stopping background worker: {e}")

        # Elasticsearch 클라이언트 종료
        if es_client is not None:
            try:
                await es_client.close()
                logger.info("Elasticsearch client closed")
            except Exception as e:
                logger.warning(f"Error closing Elasticsearch client: {e}")

        # Neo4j 드라이버 종료
        if neo4j_driver is not None:
            try:
                await neo4j_driver.close()
                logger.info("Neo4j driver closed")
            except Exception as e:
                logger.warning(f"Error closing Neo4j driver: {e}")

        # DocumentRepository 종료
        if hasattr(app.state, "document_repository") and app.state.document_repository:
            try:
                from app.services.document_repository import close_document_repository

                await close_document_repository()
                logger.info("DocumentRepository closed")
            except Exception as e:
                logger.warning(f"Error closing DocumentRepository: {e}")


def create_app() -> FastAPI:
    """FastAPI 애플리케이션 팩토리"""

    app = FastAPI(
        title=settings.app_name,
        description="Graph RAG 기반 지능형 지식 검색 시스템 - AI Service",
        version=settings.app_version,
        # OpenAPI 문서는 항상 활성화 (E2E 테스트 및 개발/운영 모니터링용)
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
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

    # Prometheus 메트릭 엔드포인트 (/metrics)
    try:
        from prometheus_fastapi_instrumentator import Instrumentator

        Instrumentator(
            should_group_status_codes=True,
            should_ignore_untemplated=True,
            excluded_handlers=["/health", "/health/live", "/health/ready", "/metrics"],
        ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
        logger.info("Prometheus metrics enabled at /metrics")
    except ImportError:
        logger.warning("prometheus-fastapi-instrumentator not installed, /metrics disabled")

    # 루트 레벨 Health Check 엔드포인트 (E2E 테스트 및 Docker 헬스체크용)
    @app.get(
        "/health",
        tags=["Health"],
        summary="Root Health Check",
        description="서비스 상태를 확인하는 루트 레벨 헬스체크 엔드포인트",
    )
    async def root_health_check() -> Dict[str, Any]:
        """
        루트 레벨 Health Check

        Docker 컨테이너 헬스체크 및 E2E 테스트에서 사용됩니다.
        상세 헬스체크는 /api/v1/health를 사용하세요.

        Returns:
            서비스 상태 정보
        """
        return {
            "status": "healthy",
            "service": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    @app.get(
        "/health/live",
        tags=["Health"],
        summary="Liveness Probe",
        description="Kubernetes Liveness Probe용 엔드포인트",
    )
    async def root_liveness() -> Dict[str, str]:
        """
        Liveness Probe

        서비스가 살아있는지 확인 (Kubernetes용)
        """
        return {"status": "alive"}

    @app.get(
        "/health/ready",
        tags=["Health"],
        summary="Readiness Probe",
        description="Kubernetes Readiness Probe용 엔드포인트",
    )
    async def root_readiness() -> Dict[str, Any]:
        """
        Readiness Probe

        서비스가 트래픽을 받을 준비가 되었는지 확인 (Kubernetes용)
        """
        checks = {
            "config_loaded": True,
            "llm_api_key_set": settings.deepseek_api_key is not None,
        }
        return {
            "ready": all(checks.values()),
            "checks": checks,
        }

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
