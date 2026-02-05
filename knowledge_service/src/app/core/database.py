"""
PostgreSQL 데이터베이스 연결 관리

SQLAlchemy async 세션을 사용한 PostgreSQL 연결 관리.
documents, chunks, users 테이블과의 상호작용을 위한 기반 모듈.
"""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy import Column, DateTime, Enum, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# SQLAlchemy Base
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    """SQLAlchemy 선언적 기본 클래스"""
    pass


# ---------------------------------------------------------------------------
# Database Engine & Session
# ---------------------------------------------------------------------------


def get_database_url() -> str:
    """
    PostgreSQL 비동기 연결 URL 생성

    Returns:
        asyncpg 드라이버를 사용하는 PostgreSQL URL
    """
    # 환경변수 우선, 없으면 settings 사용
    host = os.getenv("POSTGRES_HOST", settings.postgres_host)
    port = os.getenv("POSTGRES_PORT", str(settings.postgres_port))
    user = os.getenv("POSTGRES_USER", settings.postgres_user)
    password = os.getenv("POSTGRES_PASSWORD", settings.postgres_password or "")
    db = os.getenv("POSTGRES_DB", settings.postgres_db)

    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"


# 전역 엔진 및 세션 팩토리 (지연 초기화)
_engine = None
_async_session_factory = None


def get_engine():
    """SQLAlchemy 비동기 엔진 반환 (싱글톤)"""
    global _engine
    if _engine is None:
        database_url = get_database_url()
        _engine = create_async_engine(
            database_url,
            echo=settings.debug,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800,
        )
        logger.info(f"Database engine created: {settings.postgres_host}:{settings.postgres_port}")
    return _engine


def get_session_factory():
    """SQLAlchemy 비동기 세션 팩토리 반환 (싱글톤)"""
    global _async_session_factory
    if _async_session_factory is None:
        engine = get_engine()
        _async_session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _async_session_factory


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    비동기 데이터베이스 세션 컨텍스트 매니저

    사용 예시:
        async with get_async_session() as session:
            result = await session.execute(select(Document))

    Yields:
        AsyncSession: SQLAlchemy 비동기 세션
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI Dependency용 데이터베이스 세션

    사용 예시:
        @router.get("/documents")
        async def list_documents(db: AsyncSession = Depends(get_db_session)):
            ...

    Yields:
        AsyncSession: SQLAlchemy 비동기 세션
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise


async def check_database_connection() -> bool:
    """
    데이터베이스 연결 상태 확인

    Returns:
        연결 성공 여부
    """
    try:
        async with get_async_session() as session:
            await session.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


async def close_database():
    """데이터베이스 연결 종료"""
    global _engine, _async_session_factory
    if _engine:
        await _engine.dispose()
        _engine = None
        _async_session_factory = None
        logger.info("Database connection closed")


# ---------------------------------------------------------------------------
# Document Model (SQLAlchemy ORM)
# ---------------------------------------------------------------------------


class DocumentModel(Base):
    """
    문서 ORM 모델

    PostgreSQL documents 테이블과 매핑.
    """

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[Optional[str]] = mapped_column(String(500))
    format: Mapped[str] = mapped_column(String(20), nullable=False)  # pdf, docx, hwp, pptx
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="uploaded"
    )  # uploaded, queued, processing, completed, failed
    progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    # 메타데이터
    title: Mapped[Optional[str]] = mapped_column(String(500))
    description: Mapped[Optional[str]] = mapped_column(Text)
    project_name: Mapped[Optional[str]] = mapped_column(String(200))

    # 처리 결과
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    entity_count: Mapped[int] = mapped_column(Integer, default=0)
    relationship_count: Mapped[int] = mapped_column(Integer, default=0)

    # 타임스탬프
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
    )

    def to_dict(self) -> dict:
        """딕셔너리 변환"""
        return {
            "document_id": str(self.id),
            "filename": self.filename,
            "original_filename": self.original_filename,
            "format": self.format,
            "size_bytes": self.size_bytes,
            "storage_path": self.storage_path,
            "status": self.status,
            "progress_percent": self.progress_percent,
            "error_message": self.error_message,
            "title": self.title,
            "description": self.description,
            "project_name": self.project_name,
            "chunk_count": self.chunk_count,
            "entity_count": self.entity_count,
            "relationship_count": self.relationship_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# User Model (SQLAlchemy ORM) - 향후 사용
# ---------------------------------------------------------------------------


class UserModel(Base):
    """
    사용자 ORM 모델

    PostgreSQL users 테이블과 매핑.
    향후 auth.py에서 직접 연동 시 사용.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="user")  # user, admin
    is_active: Mapped[bool] = mapped_column(default=True)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
    )

    def to_dict(self) -> dict:
        """딕셔너리 변환 (비밀번호 해시 포함)"""
        return {
            "id": str(self.id),
            "email": self.email,
            "password_hash": self.password_hash,
            "name": self.name,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
