"""
API 라우터 모듈

모든 API 엔드포인트를 하나의 라우터로 통합
"""

from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.cache import router as cache_router
from app.api.routes.documents import router as documents_router
from app.api.routes.embed import router as embed_router
from app.api.routes.extract import router as extract_router
from app.api.routes.graph import router as graph_router
from app.api.routes.health import router as health_router
from app.api.routes.search import router as search_router

router = APIRouter()

# 라우터 등록
router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
router.include_router(cache_router, prefix="/cache", tags=["Cache"])
router.include_router(documents_router, prefix="/documents", tags=["Documents"])
router.include_router(health_router, prefix="/health", tags=["Health"])
router.include_router(search_router, prefix="/search", tags=["Search"])
router.include_router(extract_router, prefix="/extract", tags=["Extract"])
router.include_router(embed_router, prefix="/embed", tags=["Embed"])
router.include_router(graph_router, prefix="/graph", tags=["Graph"])
