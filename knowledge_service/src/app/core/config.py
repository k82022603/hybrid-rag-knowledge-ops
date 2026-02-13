"""
환경 설정 관리 모듈

pydantic-settings를 사용하여 환경변수 기반 설정 관리
"""

import os
from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """애플리케이션 설정 클래스"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # 애플리케이션 설정
    app_name: str = "Knowledge Service"
    app_version: str = "0.1.0"
    debug: bool = Field(default=False, description="디버그 모드")
    environment: str = Field(default="development", description="실행 환경")

    # API 설정
    api_v1_prefix: str = "/api/v1"
    allowed_hosts: List[str] = Field(default=["*"], description="허용 호스트")

    # JWT 인증 설정 (P0 - 필수)
    jwt_secret_key: str = Field(
        default="", description="JWT 시크릿 키 (필수, 최소 32자)"
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT 알고리즘")
    access_token_expire_minutes: int = Field(
        default=30, description="액세스 토큰 만료 시간 (분)"
    )
    refresh_token_expire_days: int = Field(
        default=7, description="리프레시 토큰 만료 시간 (일)"
    )

    # 관리자 계정 설정 (P0 - 필수)
    admin_email: str = Field(
        default="admin@example.com", description="관리자 이메일"
    )
    admin_password_hash: str = Field(
        default="", description="관리자 비밀번호 bcrypt 해시"
    )
    admin_name: str = Field(
        default="시스템 관리자", description="관리자 이름"
    )

    # 테스트 사용자 계정 (선택)
    test_user_email: Optional[str] = Field(
        default=None, description="테스트 사용자 이메일"
    )
    test_user_password_hash: Optional[str] = Field(
        default=None, description="테스트 사용자 비밀번호 bcrypt 해시"
    )
    test_user_name: Optional[str] = Field(
        default=None, description="테스트 사용자 이름"
    )

    # LLM 설정 (DeepSeek)
    deepseek_api_key: Optional[str] = Field(default=None, description="DeepSeek API 키")
    deepseek_base_url: str = Field(
        default="https://api.deepseek.com", description="DeepSeek API Base URL"
    )
    deepseek_chat_model: str = Field(
        default="deepseek-chat", description="DeepSeek Chat 모델명"
    )
    deepseek_reasoner_model: str = Field(
        default="deepseek-reasoner", description="DeepSeek Reasoner 모델명"
    )
    llm_temperature: float = Field(default=0.0, description="LLM Temperature")
    llm_max_tokens: int = Field(default=4096, description="LLM 최대 토큰")
    llm_timeout: int = Field(default=60, description="LLM 타임아웃 (초)")

    # Embedding 설정 (BGE-M3)
    embedding_model: str = Field(default="BAAI/bge-m3", description="임베딩 모델명")
    embedding_dimension: int = Field(default=1024, description="임베딩 차원")
    embedding_batch_size: int = Field(default=4, description="임베딩 배치 크기 (CPU 최적: 4)")
    embedding_max_length: int = Field(default=8192, description="임베딩 최대 토큰 길이")
    embedding_use_fp16: bool = Field(default=True, description="FP16 사용 여부")
    embedding_device: Optional[str] = Field(default=None, description="임베딩 디바이스 (auto)")
    embedding_normalize: bool = Field(default=True, description="벡터 정규화 여부")

    # Redis 설정
    redis_host: str = Field(default="localhost", description="Redis 호스트")
    redis_port: int = Field(default=6379, description="Redis 포트")
    redis_password: Optional[str] = Field(default=None, description="Redis 비밀번호")
    redis_db: int = Field(default=0, description="Redis DB 번호")
    redis_embedding_cache_ttl: int = Field(
        default=86400 * 7, description="임베딩 캐시 TTL (초, 기본 7일)"
    )

    # Search Cache 설정 (STORY-060)
    search_cache_enabled: bool = Field(default=True, description="검색 캐시 활성화 여부")
    search_cache_ttl: int = Field(default=3600, description="검색 캐시 TTL (초, 기본 1시간)")
    search_cache_max_size: int = Field(default=1000, description="검색 캐시 최대 엔트리 수")

    # PostgreSQL 설정
    postgres_host: str = Field(default="localhost", description="PostgreSQL 호스트")
    postgres_port: int = Field(default=5432, description="PostgreSQL 포트")
    postgres_user: str = Field(default="postgres", description="PostgreSQL 사용자")
    postgres_password: Optional[str] = Field(default=None, description="PostgreSQL 비밀번호")
    postgres_db: str = Field(default="knowledge_db", description="PostgreSQL 데이터베이스명")

    @property
    def postgres_url(self) -> str:
        """PostgreSQL 연결 URL 생성"""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # Elasticsearch 설정
    elasticsearch_host: str = Field(default="localhost", description="Elasticsearch 호스트")
    elasticsearch_port: int = Field(default=9200, description="Elasticsearch 포트")
    elasticsearch_user: Optional[str] = Field(default=None, description="Elasticsearch 사용자")
    elasticsearch_password: Optional[str] = Field(
        default=None, description="Elasticsearch 비밀번호"
    )
    elasticsearch_index: str = Field(
        default="knowledge_chunks", description="Elasticsearch 인덱스명 (Nori 한국어 분석기 적용)"
    )

    @property
    def elasticsearch_url(self) -> str:
        """Elasticsearch 연결 URL 생성"""
        if self.elasticsearch_user and self.elasticsearch_password:
            return (
                f"https://{self.elasticsearch_user}:{self.elasticsearch_password}"
                f"@{self.elasticsearch_host}:{self.elasticsearch_port}"
            )
        return f"http://{self.elasticsearch_host}:{self.elasticsearch_port}"

    # Neo4j 설정
    neo4j_uri: str = Field(default="bolt://localhost:7687", description="Neo4j URI")
    neo4j_user: str = Field(default="neo4j", description="Neo4j 사용자")
    neo4j_password: Optional[str] = Field(default=None, description="Neo4j 비밀번호")

    # RAG 설정
    chunk_size: int = Field(default=600, description="청크 크기 (토큰)")
    chunk_overlap: int = Field(default=100, description="청크 오버랩 (토큰)")
    max_gleanings: int = Field(default=1, description="Gleaning 최대 반복 횟수")
    retrieval_top_k: int = Field(default=10, description="검색 결과 상위 K개")
    rrf_k: int = Field(default=60, description="RRF 융합 파라미터")
    rrf_weight_vector: float = Field(default=1.0, description="RRF Vector 채널 가중치")
    rrf_weight_keyword: float = Field(default=1.0, description="RRF Keyword 채널 가중치")
    rrf_weight_graph: float = Field(default=0.8, description="RRF Graph 채널 가중치 (엔티티 관계 기반)")

    # 컨텍스트 품질 판단 설정 (Quality Gate)
    context_quality_high_threshold: float = Field(
        default=0.1, description="HIGH 품질 임계값 (Reranker 0.1+ 또는 RRF 상위권)"
    )
    context_quality_partial_threshold: float = Field(
        default=0.01, description="PARTIAL 품질 임계값 (RRF 점수 0.01+ 이면 부분 컨텍스트)"
    )
    context_min_score_cutoff: float = Field(
        default=0.005, description="최소 점수 컷오프 (RRF 최저 범위인 0.005 미만만 제거)"
    )
    context_quality_min_high_count: int = Field(
        default=1, description="HIGH 판정에 필요한 최소 고품질 결과 수"
    )

    # Ragas 품질 목표
    ragas_faithfulness_target: float = Field(default=0.9, description="Faithfulness 목표")
    ragas_relevancy_target: float = Field(default=0.85, description="Answer Relevancy 목표")
    ragas_precision_target: float = Field(default=0.8, description="Context Precision 목표")

    @field_validator("deepseek_api_key", mode="before")
    @classmethod
    def validate_api_key(cls, v: Optional[str]) -> Optional[str]:
        """API 키가 환경변수에서 로드되었는지 확인"""
        if v is None:
            v = os.getenv("DEEPSEEK_API_KEY")
        return v


@lru_cache()
def get_settings() -> Settings:
    """설정 인스턴스 반환 (캐시됨)"""
    return Settings()


# 전역 설정 인스턴스
settings = get_settings()
