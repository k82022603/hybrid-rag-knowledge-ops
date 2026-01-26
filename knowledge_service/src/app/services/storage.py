"""
파일 스토리지 서비스

MinIO 오브젝트 스토리지 기반 파일 저장/조회
MinIO 미사용 환경에서는 로컬 파일시스템으로 폴백
"""

import os
import shutil
from pathlib import Path
from typing import Optional

from app.core.logging import get_logger

logger = get_logger(__name__)

# MinIO 환경변수 설정
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"

# 로컬 폴백 저장소 경로
LOCAL_STORAGE_DIR = os.getenv(
    "LOCAL_STORAGE_DIR",
    str(Path(__file__).resolve().parent.parent.parent.parent / "data" / "uploads"),
)

# MinIO 클라이언트 (lazy 초기화)
_minio_client = None
_minio_available: Optional[bool] = None


def _get_minio_client():
    """
    MinIO 클라이언트를 lazy 초기화로 반환

    Returns:
        MinIO 클라이언트 인스턴스 또는 None (연결 실패 시)
    """
    global _minio_client, _minio_available

    if _minio_available is False:
        return None

    if _minio_client is not None:
        return _minio_client

    if not MINIO_ACCESS_KEY or not MINIO_SECRET_KEY:
        logger.info("MinIO credentials not configured, using local storage fallback")
        _minio_available = False
        return None

    try:
        from minio import Minio

        client = Minio(
            endpoint=MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_SECURE,
        )
        # 연결 테스트
        client.list_buckets()
        _minio_client = client
        _minio_available = True
        logger.info(f"MinIO connected: {MINIO_ENDPOINT}")
        return _minio_client
    except ImportError:
        logger.warning("minio package not installed, using local storage fallback")
        _minio_available = False
        return None
    except Exception as e:
        logger.warning(f"MinIO connection failed: {e}, using local storage fallback")
        _minio_available = False
        return None


def _ensure_local_dir(bucket: str) -> Path:
    """
    로컬 폴백 저장 디렉토리 생성

    Args:
        bucket: 버킷명 (로컬 저장 시 하위 디렉토리로 사용)

    Returns:
        로컬 저장 디렉토리 경로
    """
    storage_dir = Path(LOCAL_STORAGE_DIR) / bucket
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir


async def upload_file(
    file_data: bytes,
    bucket: str,
    object_name: str,
    content_type: str = "application/octet-stream",
) -> str:
    """
    파일 업로드 (MinIO 우선, 로컬 폴백)

    Args:
        file_data: 파일 바이너리 데이터
        bucket: 버킷명
        object_name: 오브젝트 키 (파일 경로)
        content_type: MIME 타입

    Returns:
        저장된 파일 경로 (MinIO object path 또는 로컬 파일 경로)

    Raises:
        IOError: 파일 저장 실패 시
    """
    client = _get_minio_client()

    if client is not None:
        return await _upload_to_minio(client, file_data, bucket, object_name, content_type)
    else:
        return await _upload_to_local(file_data, bucket, object_name)


async def _upload_to_minio(
    client,
    file_data: bytes,
    bucket: str,
    object_name: str,
    content_type: str,
) -> str:
    """
    MinIO에 파일 업로드

    Args:
        client: MinIO 클라이언트
        file_data: 파일 바이너리 데이터
        bucket: 버킷명
        object_name: 오브젝트 키
        content_type: MIME 타입

    Returns:
        MinIO 오브젝트 경로
    """
    import io

    try:
        # 버킷 존재 확인 및 생성
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
            logger.info(f"Created MinIO bucket: {bucket}")

        data_stream = io.BytesIO(file_data)
        data_length = len(file_data)

        client.put_object(
            bucket_name=bucket,
            object_name=object_name,
            data=data_stream,
            length=data_length,
            content_type=content_type,
        )

        storage_path = f"minio://{bucket}/{object_name}"
        logger.info(f"File uploaded to MinIO: {storage_path}")
        return storage_path

    except Exception as e:
        logger.error(f"MinIO upload failed: {e}, falling back to local storage")
        return await _upload_to_local(file_data, bucket, object_name)


async def _upload_to_local(
    file_data: bytes,
    bucket: str,
    object_name: str,
) -> str:
    """
    로컬 파일시스템에 파일 저장 (폴백)

    Args:
        file_data: 파일 바이너리 데이터
        bucket: 버킷명 (하위 디렉토리)
        object_name: 파일명

    Returns:
        로컬 파일 절대 경로
    """
    try:
        storage_dir = _ensure_local_dir(bucket)
        # object_name에 하위 경로가 포함될 수 있으므로 디렉토리 생성
        file_path = storage_dir / object_name
        file_path.parent.mkdir(parents=True, exist_ok=True)

        file_path.write_bytes(file_data)

        storage_path = str(file_path.resolve())
        logger.info(f"File saved to local storage: {storage_path}")
        return storage_path

    except Exception as e:
        logger.error(f"Local storage save failed: {e}")
        raise IOError(f"파일 저장에 실패했습니다: {e}") from e


async def get_file_url(bucket: str, object_name: str) -> str:
    """
    파일 접근 URL 반환

    MinIO 환경에서는 presigned URL, 로컬 환경에서는 파일 경로를 반환합니다.

    Args:
        bucket: 버킷명
        object_name: 오브젝트 키

    Returns:
        파일 접근 URL 또는 로컬 경로
    """
    client = _get_minio_client()

    if client is not None:
        try:
            from datetime import timedelta

            url = client.presigned_get_object(
                bucket_name=bucket,
                object_name=object_name,
                expires=timedelta(hours=1),
            )
            return url
        except Exception as e:
            logger.warning(f"Failed to generate presigned URL: {e}")

    # 로컬 폴백
    storage_dir = _ensure_local_dir(bucket)
    file_path = storage_dir / object_name
    return str(file_path.resolve())


async def delete_file(bucket: str, object_name: str) -> bool:
    """
    파일 삭제

    Args:
        bucket: 버킷명
        object_name: 오브젝트 키

    Returns:
        삭제 성공 여부
    """
    client = _get_minio_client()

    if client is not None:
        try:
            client.remove_object(bucket_name=bucket, object_name=object_name)
            logger.info(f"Deleted from MinIO: {bucket}/{object_name}")
            return True
        except Exception as e:
            logger.warning(f"MinIO delete failed: {e}")

    # 로컬 폴백
    try:
        storage_dir = _ensure_local_dir(bucket)
        file_path = storage_dir / object_name
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted from local: {file_path}")
            return True
        return False
    except Exception as e:
        logger.error(f"File delete failed: {e}")
        return False
