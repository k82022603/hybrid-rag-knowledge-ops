"""
대화 이력 관리 서비스 테스트 모듈

STORY-057: 대화이력 + 스트리밍 구현
"""

import pytest
from datetime import datetime

from app.services.conversation_history import (
    ConversationHistoryService,
    ConversationSession,
    ConversationStore,
    ConversationTurn,
    get_conversation_history_service,
    reset_conversation_history_service,
)


# ---------------------------------------------------------------------------
# ConversationTurn Tests
# ---------------------------------------------------------------------------


class TestConversationTurn:
    """ConversationTurn 테스트"""

    def test_create_turn(self):
        """턴 생성 테스트"""
        turn = ConversationTurn(
            turn_id="turn-001",
            query="안녕하세요",
            answer="안녕하세요! 무엇을 도와드릴까요?",
            sources=[{"title": "문서1"}],
            latency_ms=100.5,
        )

        assert turn.turn_id == "turn-001"
        assert turn.query == "안녕하세요"
        assert turn.answer == "안녕하세요! 무엇을 도와드릴까요?"
        assert len(turn.sources) == 1
        assert turn.latency_ms == 100.5
        assert turn.timestamp is not None

    def test_to_dict(self):
        """딕셔너리 변환 테스트"""
        turn = ConversationTurn(
            turn_id="turn-001",
            query="질문",
            answer="답변",
        )

        result = turn.to_dict()

        assert result["turnId"] == "turn-001"
        assert result["query"] == "질문"
        assert result["answer"] == "답변"
        assert "timestamp" in result

    def test_to_message_format(self):
        """LLM 메시지 형식 변환 테스트"""
        turn = ConversationTurn(
            turn_id="turn-001",
            query="질문입니다",
            answer="답변입니다",
        )

        messages = turn.to_message_format()

        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "질문입니다"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "답변입니다"


# ---------------------------------------------------------------------------
# ConversationSession Tests
# ---------------------------------------------------------------------------


class TestConversationSession:
    """ConversationSession 테스트"""

    def test_create_session(self):
        """세션 생성 테스트"""
        session = ConversationSession(
            session_id="session-001",
            user_id="user-123",
        )

        assert session.session_id == "session-001"
        assert session.user_id == "user-123"
        assert len(session.turns) == 0
        assert session.created_at is not None

    def test_add_turn(self):
        """턴 추가 테스트"""
        session = ConversationSession(session_id="session-001")

        turn = ConversationTurn(
            turn_id="turn-001",
            query="질문",
            answer="답변",
        )
        session.add_turn(turn)

        assert len(session.turns) == 1
        assert session.turns[0].query == "질문"

    def test_get_recent_turns(self):
        """최근 턴 조회 테스트"""
        session = ConversationSession(session_id="session-001")

        # 10개 턴 추가
        for i in range(10):
            turn = ConversationTurn(
                turn_id=f"turn-{i:03d}",
                query=f"질문 {i}",
                answer=f"답변 {i}",
            )
            session.add_turn(turn)

        # 최근 5개 조회
        recent = session.get_recent_turns(n=5)

        assert len(recent) == 5
        assert recent[0].query == "질문 5"
        assert recent[-1].query == "질문 9"

    def test_get_conversation_context(self):
        """대화 컨텍스트 문자열 테스트"""
        session = ConversationSession(session_id="session-001")

        session.add_turn(ConversationTurn(
            turn_id="turn-001",
            query="첫 번째 질문",
            answer="첫 번째 답변",
        ))
        session.add_turn(ConversationTurn(
            turn_id="turn-002",
            query="두 번째 질문",
            answer="두 번째 답변",
        ))

        context = session.get_conversation_context(max_turns=5)

        assert "이전 대화 내용" in context
        assert "첫 번째 질문" in context
        assert "두 번째 답변" in context

    def test_get_conversation_context_with_char_limit(self):
        """컨텍스트 문자 제한 테스트"""
        session = ConversationSession(session_id="session-001")

        # 긴 답변 추가
        session.add_turn(ConversationTurn(
            turn_id="turn-001",
            query="질문",
            answer="A" * 5000,  # 긴 답변
        ))
        session.add_turn(ConversationTurn(
            turn_id="turn-002",
            query="질문2",
            answer="B" * 5000,
        ))

        context = session.get_conversation_context(max_turns=5, max_chars=100)

        # 문자 제한으로 인해 일부만 포함
        assert len(context) <= 200  # 헤더 포함

    def test_get_messages_for_llm(self):
        """LLM 메시지 목록 테스트"""
        session = ConversationSession(session_id="session-001")

        session.add_turn(ConversationTurn(
            turn_id="turn-001",
            query="질문1",
            answer="답변1",
        ))
        session.add_turn(ConversationTurn(
            turn_id="turn-002",
            query="질문2",
            answer="답변2",
        ))

        messages = session.get_messages_for_llm(max_turns=5)

        assert len(messages) == 4  # 2 turns * 2 messages
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"

    def test_to_dict(self):
        """세션 딕셔너리 변환 테스트"""
        session = ConversationSession(
            session_id="session-001",
            user_id="user-123",
        )
        session.add_turn(ConversationTurn(
            turn_id="turn-001",
            query="질문",
            answer="답변",
        ))

        result = session.to_dict()

        assert result["sessionId"] == "session-001"
        assert result["userId"] == "user-123"
        assert result["turnCount"] == 1
        assert len(result["turns"]) == 1


# ---------------------------------------------------------------------------
# ConversationStore Tests
# ---------------------------------------------------------------------------


class TestConversationStore:
    """ConversationStore 테스트"""

    def test_create_session(self):
        """세션 생성 테스트"""
        store = ConversationStore(max_sessions=10)

        session = store.create_session(
            session_id="session-001",
            user_id="user-123",
        )

        assert session.session_id == "session-001"
        assert session.user_id == "user-123"
        assert store.get_session_count() == 1

    def test_create_session_auto_id(self):
        """자동 ID 세션 생성 테스트"""
        store = ConversationStore()

        session = store.create_session(user_id="user-123")

        assert session.session_id is not None
        assert len(session.session_id) > 0

    def test_get_session(self):
        """세션 조회 테스트"""
        store = ConversationStore()

        store.create_session(session_id="session-001")
        session = store.get_session("session-001")

        assert session is not None
        assert session.session_id == "session-001"

    def test_get_session_not_found(self):
        """없는 세션 조회 테스트"""
        store = ConversationStore()

        session = store.get_session("nonexistent")

        assert session is None

    def test_get_or_create_session_existing(self):
        """기존 세션 조회 테스트"""
        store = ConversationStore()

        store.create_session(session_id="session-001")
        session = store.get_or_create_session(session_id="session-001")

        assert session.session_id == "session-001"
        assert store.get_session_count() == 1  # 새로 생성되지 않음

    def test_get_or_create_session_new(self):
        """새 세션 생성 테스트"""
        store = ConversationStore()

        session = store.get_or_create_session(session_id="session-001")

        assert session.session_id == "session-001"
        assert store.get_session_count() == 1

    def test_add_turn(self):
        """턴 추가 테스트"""
        store = ConversationStore()

        store.create_session(session_id="session-001")
        turn = store.add_turn(
            session_id="session-001",
            query="질문",
            answer="답변",
            sources=[{"title": "문서"}],
            latency_ms=50.0,
        )

        assert turn.turn_id is not None
        assert turn.query == "질문"

        session = store.get_session("session-001")
        assert len(session.turns) == 1

    def test_add_turn_session_not_found(self):
        """없는 세션에 턴 추가 테스트"""
        store = ConversationStore()

        with pytest.raises(ValueError, match="Session not found"):
            store.add_turn(
                session_id="nonexistent",
                query="질문",
                answer="답변",
            )

    def test_lru_eviction(self):
        """LRU 정책 테스트"""
        store = ConversationStore(max_sessions=3)

        # 3개 세션 생성
        store.create_session(session_id="session-001")
        store.create_session(session_id="session-002")
        store.create_session(session_id="session-003")

        assert store.get_session_count() == 3

        # 4번째 세션 생성 -> 가장 오래된 세션 제거
        store.create_session(session_id="session-004")

        assert store.get_session_count() == 3
        assert store.get_session("session-001") is None  # 제거됨
        assert store.get_session("session-004") is not None

    def test_lru_access_order(self):
        """LRU 접근 순서 테스트"""
        store = ConversationStore(max_sessions=3)

        store.create_session(session_id="session-001")
        store.create_session(session_id="session-002")
        store.create_session(session_id="session-003")

        # session-001 접근 -> 최근으로 이동
        store.get_session("session-001")

        # 새 세션 추가 -> session-002가 제거됨
        store.create_session(session_id="session-004")

        assert store.get_session("session-001") is not None  # 최근 접근
        assert store.get_session("session-002") is None  # 제거됨

    def test_delete_session(self):
        """세션 삭제 테스트"""
        store = ConversationStore()

        store.create_session(session_id="session-001")
        deleted = store.delete_session("session-001")

        assert deleted is True
        assert store.get_session("session-001") is None
        assert store.get_session_count() == 0

    def test_delete_session_not_found(self):
        """없는 세션 삭제 테스트"""
        store = ConversationStore()

        deleted = store.delete_session("nonexistent")

        assert deleted is False

    def test_max_turns_per_session(self):
        """세션당 최대 턴 수 테스트"""
        store = ConversationStore(max_turns_per_session=3)

        store.create_session(session_id="session-001")

        # 5개 턴 추가
        for i in range(5):
            store.add_turn(
                session_id="session-001",
                query=f"질문 {i}",
                answer=f"답변 {i}",
            )

        session = store.get_session("session-001")
        assert len(session.turns) == 3  # 최근 3개만 유지

    def test_get_user_sessions(self):
        """사용자별 세션 조회 테스트"""
        store = ConversationStore()

        store.create_session(session_id="session-001", user_id="user-A")
        store.create_session(session_id="session-002", user_id="user-A")
        store.create_session(session_id="session-003", user_id="user-B")

        user_a_sessions = store.get_user_sessions("user-A")

        assert len(user_a_sessions) == 2


# ---------------------------------------------------------------------------
# ConversationHistoryService Tests
# ---------------------------------------------------------------------------


class TestConversationHistoryService:
    """ConversationHistoryService 테스트"""

    def setup_method(self):
        """테스트 전 싱글톤 초기화"""
        reset_conversation_history_service()

    def test_get_or_create_session(self):
        """세션 생성/조회 테스트"""
        service = ConversationHistoryService()

        session = service.get_or_create_session(
            session_id="session-001",
            user_id="user-123",
        )

        assert session.session_id == "session-001"
        assert session.user_id == "user-123"

    def test_get_session(self):
        """세션 조회 테스트"""
        service = ConversationHistoryService()

        service.get_or_create_session(session_id="session-001")
        session = service.get_session("session-001")

        assert session is not None

    def test_add_turn(self):
        """턴 추가 테스트"""
        service = ConversationHistoryService()

        service.get_or_create_session(session_id="session-001")
        turn = service.add_turn(
            session_id="session-001",
            query="질문",
            answer="답변",
        )

        assert turn.query == "질문"

    def test_add_turn_auto_create_session(self):
        """세션 자동 생성 턴 추가 테스트"""
        service = ConversationHistoryService()

        # 세션이 없어도 자동 생성
        turn = service.add_turn(
            session_id="session-001",
            query="질문",
            answer="답변",
        )

        assert turn is not None
        assert service.get_session("session-001") is not None

    def test_get_conversation_context(self):
        """대화 컨텍스트 조회 테스트"""
        service = ConversationHistoryService()

        service.get_or_create_session(session_id="session-001")
        service.add_turn(
            session_id="session-001",
            query="질문",
            answer="답변",
        )

        context = service.get_conversation_context("session-001")

        assert "이전 대화 내용" in context
        assert "질문" in context

    def test_get_conversation_context_empty(self):
        """빈 대화 컨텍스트 조회 테스트"""
        service = ConversationHistoryService()

        context = service.get_conversation_context("nonexistent")

        assert context == ""

    def test_get_messages_for_llm(self):
        """LLM 메시지 조회 테스트"""
        service = ConversationHistoryService()

        service.get_or_create_session(session_id="session-001")
        service.add_turn(
            session_id="session-001",
            query="질문",
            answer="답변",
        )

        messages = service.get_messages_for_llm("session-001")

        assert len(messages) == 2

    def test_get_session_summary(self):
        """세션 요약 조회 테스트"""
        service = ConversationHistoryService()

        service.get_or_create_session(session_id="session-001", user_id="user-123")
        service.add_turn(
            session_id="session-001",
            query="마지막 질문",
            answer="마지막 답변",
        )

        summary = service.get_session_summary("session-001")

        assert summary["sessionId"] == "session-001"
        assert summary["userId"] == "user-123"
        assert summary["turnCount"] == 1
        assert summary["lastQuery"] == "마지막 질문"

    def test_delete_session(self):
        """세션 삭제 테스트"""
        service = ConversationHistoryService()

        service.get_or_create_session(session_id="session-001")
        deleted = service.delete_session("session-001")

        assert deleted is True
        assert service.get_session("session-001") is None

    def test_get_stats(self):
        """서비스 통계 조회 테스트"""
        service = ConversationHistoryService()

        service.get_or_create_session(session_id="session-001")
        service.get_or_create_session(session_id="session-002")

        stats = service.get_stats()

        assert stats["sessionCount"] == 2
        assert "maxSessions" in stats
        assert "maxContextTurns" in stats


# ---------------------------------------------------------------------------
# Singleton Tests
# ---------------------------------------------------------------------------


class TestSingleton:
    """싱글톤 테스트"""

    def setup_method(self):
        """테스트 전 싱글톤 초기화"""
        reset_conversation_history_service()

    def test_get_singleton(self):
        """싱글톤 인스턴스 테스트"""
        service1 = get_conversation_history_service()
        service2 = get_conversation_history_service()

        assert service1 is service2

    def test_reset_singleton(self):
        """싱글톤 리셋 테스트"""
        service1 = get_conversation_history_service()
        reset_conversation_history_service()
        service2 = get_conversation_history_service()

        assert service1 is not service2
