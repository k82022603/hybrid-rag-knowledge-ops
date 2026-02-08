"""
대화 이력 관리 서비스 모듈

STORY-057: 대화이력 + 스트리밍 구현

세션별 대화 이력 저장/조회 및 컨텍스트 관리를 제공합니다.
- 세션별 대화 이력 저장 (인메모리 + 추후 PostgreSQL 연동)
- 대화 컨텍스트 요약 생성
- RAG 파이프라인에 대화 컨텍스트 통합
"""

import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4


def _utc_now_iso() -> str:
    """UTC 현재 시간을 ISO 8601 형식으로 반환"""
    return datetime.now(timezone.utc).isoformat()

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# 데이터 모델
# ---------------------------------------------------------------------------


@dataclass
class ConversationTurn:
    """
    대화 턴 (한 번의 질문-답변 쌍)

    Attributes:
        turn_id: 턴 고유 ID
        query: 사용자 질문
        answer: AI 답변
        sources: 출처 정보 목록
        timestamp: 생성 시간 (ISO 8601)
        latency_ms: 처리 시간 (ms)
        metadata: 추가 메타데이터
    """

    turn_id: str
    query: str
    answer: str
    sources: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: str = field(default_factory=_utc_now_iso)
    latency_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "turnId": self.turn_id,
            "query": self.query,
            "answer": self.answer,
            "sources": self.sources,
            "timestamp": self.timestamp,
            "latencyMs": self.latency_ms,
            "metadata": self.metadata,
        }

    def to_message_format(self) -> List[Dict[str, str]]:
        """LLM 메시지 형식으로 변환"""
        return [
            {"role": "user", "content": self.query},
            {"role": "assistant", "content": self.answer},
        ]


@dataclass
class ConversationSession:
    """
    대화 세션

    Attributes:
        session_id: 세션 고유 ID
        user_id: 사용자 ID (선택)
        turns: 대화 턴 목록
        created_at: 세션 생성 시간
        updated_at: 마지막 업데이트 시간
        metadata: 세션 메타데이터
    """

    session_id: str
    user_id: Optional[str] = None
    turns: List[ConversationTurn] = field(default_factory=list)
    created_at: str = field(default_factory=_utc_now_iso)
    updated_at: str = field(default_factory=_utc_now_iso)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_turn(self, turn: ConversationTurn) -> None:
        """대화 턴 추가"""
        self.turns.append(turn)
        self.updated_at = _utc_now_iso()

    def get_recent_turns(self, n: int = 5) -> List[ConversationTurn]:
        """최근 n개 턴 조회"""
        return self.turns[-n:] if self.turns else []

    def get_conversation_context(
        self,
        max_turns: int = 5,
        max_chars: int = 4000,
    ) -> str:
        """
        대화 컨텍스트 문자열 생성

        최근 대화 이력을 LLM에 전달할 컨텍스트 문자열로 변환합니다.

        Args:
            max_turns: 포함할 최대 턴 수
            max_chars: 최대 문자 수

        Returns:
            대화 컨텍스트 문자열
        """
        recent_turns = self.get_recent_turns(max_turns)
        if not recent_turns:
            return ""

        context_parts: List[str] = []
        total_chars = 0

        for turn in recent_turns:
            turn_text = f"사용자: {turn.query}\nAI: {turn.answer}"
            if total_chars + len(turn_text) > max_chars:
                break
            context_parts.append(turn_text)
            total_chars += len(turn_text) + 2  # newlines

        if not context_parts:
            return ""

        return "## 이전 대화 내용\n\n" + "\n\n".join(context_parts)

    def get_messages_for_llm(
        self,
        max_turns: int = 5,
    ) -> List[Dict[str, str]]:
        """
        LLM 호출용 메시지 목록 생성

        대화 이력을 OpenAI/DeepSeek 메시지 형식으로 변환합니다.

        Args:
            max_turns: 포함할 최대 턴 수

        Returns:
            메시지 목록 [{"role": "...", "content": "..."}]
        """
        recent_turns = self.get_recent_turns(max_turns)
        messages: List[Dict[str, str]] = []

        for turn in recent_turns:
            messages.extend(turn.to_message_format())

        return messages

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "sessionId": self.session_id,
            "userId": self.user_id,
            "turns": [turn.to_dict() for turn in self.turns],
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
            "metadata": self.metadata,
            "turnCount": len(self.turns),
        }


# ---------------------------------------------------------------------------
# 대화 이력 저장소 (인메모리 LRU)
# ---------------------------------------------------------------------------


class ConversationStore:
    """
    대화 이력 저장소 (인메모리 LRU 캐시)

    세션별 대화 이력을 메모리에 저장합니다.
    LRU (Least Recently Used) 정책으로 오래된 세션을 자동 제거합니다.

    추후 PostgreSQL 연동 시 이 클래스를 확장합니다.
    """

    def __init__(
        self,
        max_sessions: int = 1000,
        max_turns_per_session: int = 50,
    ):
        """
        초기화

        Args:
            max_sessions: 최대 세션 수
            max_turns_per_session: 세션당 최대 턴 수
        """
        self._sessions: OrderedDict[str, ConversationSession] = OrderedDict()
        self._max_sessions = max_sessions
        self._max_turns_per_session = max_turns_per_session

    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """
        세션 조회

        LRU 정책에 따라 조회된 세션을 가장 최근으로 이동합니다.

        Args:
            session_id: 세션 ID

        Returns:
            ConversationSession 또는 None
        """
        if session_id in self._sessions:
            # LRU: 최근 접근 세션을 맨 뒤로 이동
            self._sessions.move_to_end(session_id)
            return self._sessions[session_id]
        return None

    def create_session(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ConversationSession:
        """
        새 세션 생성

        Args:
            session_id: 세션 ID (None이면 자동 생성)
            user_id: 사용자 ID
            metadata: 세션 메타데이터

        Returns:
            생성된 ConversationSession
        """
        # 용량 초과 시 가장 오래된 세션 제거
        while len(self._sessions) >= self._max_sessions:
            oldest_key = next(iter(self._sessions))
            del self._sessions[oldest_key]
            logger.debug(f"LRU eviction - Removed session: {oldest_key}")

        sid = session_id or str(uuid4())
        session = ConversationSession(
            session_id=sid,
            user_id=user_id,
            metadata=metadata or {},
        )
        self._sessions[sid] = session

        logger.info(f"Session created - ID: {sid}, User: {user_id}")
        return session

    def get_or_create_session(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> ConversationSession:
        """
        세션 조회 또는 생성

        Args:
            session_id: 세션 ID (None이면 새 세션 생성)
            user_id: 사용자 ID

        Returns:
            ConversationSession
        """
        if session_id:
            session = self.get_session(session_id)
            if session:
                return session

        return self.create_session(session_id=session_id, user_id=user_id)

    def add_turn(
        self,
        session_id: str,
        query: str,
        answer: str,
        sources: Optional[List[Dict[str, Any]]] = None,
        latency_ms: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ConversationTurn:
        """
        대화 턴 추가

        Args:
            session_id: 세션 ID
            query: 사용자 질문
            answer: AI 답변
            sources: 출처 정보
            latency_ms: 처리 시간
            metadata: 턴 메타데이터

        Returns:
            생성된 ConversationTurn

        Raises:
            ValueError: 세션을 찾을 수 없는 경우
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        turn = ConversationTurn(
            turn_id=str(uuid4()),
            query=query,
            answer=answer,
            sources=sources or [],
            latency_ms=latency_ms,
            metadata=metadata or {},
        )

        session.add_turn(turn)

        # 턴 수 제한
        if len(session.turns) > self._max_turns_per_session:
            session.turns = session.turns[-self._max_turns_per_session:]

        logger.debug(
            f"Turn added - Session: {session_id}, "
            f"Turn: {turn.turn_id}, "
            f"Total turns: {len(session.turns)}"
        )

        return turn

    def delete_session(self, session_id: str) -> bool:
        """
        세션 삭제

        Args:
            session_id: 세션 ID

        Returns:
            삭제 성공 여부
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"Session deleted: {session_id}")
            return True
        return False

    def get_session_count(self) -> int:
        """현재 세션 수 조회"""
        return len(self._sessions)

    def get_user_sessions(self, user_id: str) -> List[ConversationSession]:
        """사용자의 모든 세션 조회"""
        return [
            session
            for session in self._sessions.values()
            if session.user_id == user_id
        ]


# ---------------------------------------------------------------------------
# ConversationHistoryService
# ---------------------------------------------------------------------------


class ConversationHistoryService:
    """
    대화 이력 관리 서비스

    세션별 대화 이력 저장/조회 및 RAG 파이프라인과의 통합을 제공합니다.

    Usage:
        service = get_conversation_history_service()

        # 세션 생성/조회
        session = service.get_or_create_session(
            session_id="conv-123",
            user_id="user-456",
        )

        # 대화 턴 추가
        service.add_turn(
            session_id="conv-123",
            query="질문",
            answer="답변",
            sources=[...],
        )

        # 컨텍스트 조회
        context = service.get_conversation_context("conv-123")
    """

    def __init__(
        self,
        store: Optional[ConversationStore] = None,
        max_context_turns: int = 10,
        max_context_chars: int = 4000,
    ):
        """
        초기화

        Args:
            store: ConversationStore 인스턴스 (None이면 기본 생성)
            max_context_turns: 컨텍스트에 포함할 최대 턴 수
            max_context_chars: 컨텍스트 최대 문자 수
        """
        self._store = store or ConversationStore()
        self._max_context_turns = max_context_turns
        self._max_context_chars = max_context_chars

    def get_or_create_session(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> ConversationSession:
        """
        세션 조회 또는 생성

        Args:
            session_id: 세션 ID (None이면 새 세션 생성)
            user_id: 사용자 ID

        Returns:
            ConversationSession
        """
        return self._store.get_or_create_session(
            session_id=session_id,
            user_id=user_id,
        )

    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """
        세션 조회

        Args:
            session_id: 세션 ID

        Returns:
            ConversationSession 또는 None
        """
        return self._store.get_session(session_id)

    def add_turn(
        self,
        session_id: str,
        query: str,
        answer: str,
        sources: Optional[List[Dict[str, Any]]] = None,
        latency_ms: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ConversationTurn:
        """
        대화 턴 추가

        세션이 없으면 자동으로 생성합니다.

        Args:
            session_id: 세션 ID
            query: 사용자 질문
            answer: AI 답변
            sources: 출처 정보
            latency_ms: 처리 시간
            metadata: 턴 메타데이터

        Returns:
            생성된 ConversationTurn
        """
        # 세션이 없으면 생성
        session = self._store.get_session(session_id)
        if not session:
            session = self._store.create_session(session_id=session_id)

        return self._store.add_turn(
            session_id=session_id,
            query=query,
            answer=answer,
            sources=sources,
            latency_ms=latency_ms,
            metadata=metadata,
        )

    def get_conversation_context(
        self,
        session_id: str,
        max_turns: Optional[int] = None,
        max_chars: Optional[int] = None,
    ) -> str:
        """
        대화 컨텍스트 문자열 조회

        Args:
            session_id: 세션 ID
            max_turns: 최대 턴 수 (None이면 기본값)
            max_chars: 최대 문자 수 (None이면 기본값)

        Returns:
            대화 컨텍스트 문자열 (세션이 없으면 빈 문자열)
        """
        session = self._store.get_session(session_id)
        if not session:
            return ""

        return session.get_conversation_context(
            max_turns=max_turns or self._max_context_turns,
            max_chars=max_chars or self._max_context_chars,
        )

    def get_messages_for_llm(
        self,
        session_id: str,
        max_turns: Optional[int] = None,
    ) -> List[Dict[str, str]]:
        """
        LLM 호출용 메시지 목록 조회

        Args:
            session_id: 세션 ID
            max_turns: 최대 턴 수

        Returns:
            메시지 목록
        """
        session = self._store.get_session(session_id)
        if not session:
            return []

        return session.get_messages_for_llm(
            max_turns=max_turns or self._max_context_turns,
        )

    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        세션 요약 정보 조회

        Args:
            session_id: 세션 ID

        Returns:
            세션 요약 딕셔너리 또는 None
        """
        session = self._store.get_session(session_id)
        if not session:
            return None

        return {
            "sessionId": session.session_id,
            "userId": session.user_id,
            "turnCount": len(session.turns),
            "createdAt": session.created_at,
            "updatedAt": session.updated_at,
            "lastQuery": session.turns[-1].query if session.turns else None,
        }

    def delete_session(self, session_id: str) -> bool:
        """
        세션 삭제

        Args:
            session_id: 세션 ID

        Returns:
            삭제 성공 여부
        """
        return self._store.delete_session(session_id)

    def get_stats(self) -> Dict[str, Any]:
        """
        서비스 통계 조회

        Returns:
            통계 딕셔너리
        """
        return {
            "sessionCount": self._store.get_session_count(),
            "maxSessions": self._store._max_sessions,
            "maxTurnsPerSession": self._store._max_turns_per_session,
            "maxContextTurns": self._max_context_turns,
            "maxContextChars": self._max_context_chars,
        }


# ---------------------------------------------------------------------------
# 싱글톤 인스턴스
# ---------------------------------------------------------------------------

_conversation_history_service: Optional[ConversationHistoryService] = None


def get_conversation_history_service() -> ConversationHistoryService:
    """ConversationHistoryService 인스턴스 반환 (싱글톤)"""
    global _conversation_history_service
    if _conversation_history_service is None:
        _conversation_history_service = ConversationHistoryService()
    return _conversation_history_service


def reset_conversation_history_service() -> None:
    """싱글톤 인스턴스 초기화 (테스트용)"""
    global _conversation_history_service
    _conversation_history_service = None
