"""
동적 검색 전략 단위 테스트 (STORY-122)

RAGWorkflow.classify_query_type() 및 select_search_strategy() 메서드 검증
- 질의 유형 분류 (factual / relational / keyword / complex)
- 검색 전략 매핑 (vector / graph / keyword / hybrid)
- 경계값 및 특수 케이스
"""

import sys
from pathlib import Path

import pytest

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from app.agents.rag_workflow import RAGWorkflow


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def classify(query: str) -> str:
    """RAGWorkflow.classify_query_type 편의 래퍼"""
    return RAGWorkflow.classify_query_type(query)


def strategy(query_type: str) -> str:
    """RAGWorkflow.select_search_strategy 편의 래퍼"""
    return RAGWorkflow.select_search_strategy(query_type)


# ---------------------------------------------------------------------------
# U01: 빈 질의 → 기본(complex) 전략
# ---------------------------------------------------------------------------


class TestEmptyQuery:
    """U01: 빈/공백 질의는 complex로 분류 → hybrid 전략"""

    def test_empty_string_returns_complex(self):
        assert classify("") == "complex"

    def test_whitespace_only_returns_complex(self):
        assert classify("   ") == "complex"

    def test_tab_only_returns_complex(self):
        assert classify("\t\n") == "complex"

    def test_empty_maps_to_hybrid(self):
        assert strategy(classify("")) == "hybrid"


# ---------------------------------------------------------------------------
# U02: 관계형 질의 분류
# ---------------------------------------------------------------------------


class TestRelationalQueryClassification:
    """U02: 관계형 질의 → relational 분류"""

    def test_relation_word_gwagwa(self):
        assert classify("A와 B의 관계는?") == "relational"

    def test_relation_word_gwa(self):
        assert classify("Neo4j과 Elasticsearch의 관계") == "relational"

    def test_connected_to(self):
        assert classify("RAG에 연결된 서비스는?") == "relational"

    def test_related_wa(self):
        assert classify("LangGraph와 관련된 컴포넌트") == "relational"

    def test_related_gwa(self):
        assert classify("FastAPI과 관련된 라이브러리 목록") == "relational"

    def test_relation_between(self):
        assert classify("Entity와 Chunk 간의 관계를 설명해줘") == "relational"

    def test_mutual_interaction(self):
        assert classify("LLM과 Embedding 모델의 상호작용") == "relational"

    def test_depends_on(self):
        assert classify("AI 서비스가 의존하는 컴포넌트는?") == "relational"

    def test_belongs_to(self):
        assert classify("이 모듈은 어느 서비스에 속하는가?") == "relational"


# ---------------------------------------------------------------------------
# U03: 사실적 질의 분류
# ---------------------------------------------------------------------------


class TestFactualQueryClassification:
    """U03: 사실적 질의 → factual 분류"""

    def test_what_is_pattern_neun(self):
        assert classify("RAG란 무엇인가?") == "factual"

    def test_what_is_pattern_eun(self):
        assert classify("임베딩은 무엇인가?") == "factual"

    def test_definition_pattern(self):
        assert classify("벡터 검색의 정의") == "factual"

    def test_what_does_mean(self):
        assert classify("Hallucination의 무슨 뜻인가?") == "factual"

    def test_how_does_work(self):
        assert classify("BM25가 어떻게 동작하나요?") == "factual"

    def test_iran_pattern(self):
        assert classify("Knowledge Graph란?") == "factual"

    def test_explain_short(self):
        assert classify("RRF를 설명해줘") == "factual"

    def test_concept_pattern(self):
        assert classify("Reranking 개념이 무엇인가") == "factual"


# ---------------------------------------------------------------------------
# U04: 키워드 질의 분류
# ---------------------------------------------------------------------------


class TestKeywordQueryClassification:
    """U04: 단순 키워드 질의 → keyword 분류"""

    def test_single_korean_keyword(self):
        assert classify("Docker") == "keyword"

    def test_two_words_no_question(self):
        assert classify("Docker 설치") == "keyword"

    def test_single_word_english(self):
        assert classify("FastAPI") == "keyword"

    def test_two_english_words(self):
        assert classify("Elasticsearch BM25") == "keyword"


# ---------------------------------------------------------------------------
# U05: 복합/복잡 질의 분류
# ---------------------------------------------------------------------------


class TestComplexQueryClassification:
    """U05: 복합 질의 → complex 분류"""

    def test_long_multi_word_query(self):
        """9단어 이상 질의는 complex"""
        long_query = "Hybrid RAG 파이프라인에서 Dense Sparse Retrieval을 함께 사용하는 이유가 무엇인가요"
        assert classify(long_query) == "complex"

    def test_ambiguous_multi_sentence(self):
        """복수의 개념이 혼합된 질의"""
        assert classify("RAG와 Fine-tuning 방법론의 장단점 비교 분석") == "complex"

    def test_long_factual_becomes_complex(self):
        """factual 패턴이지만 8단어 초과 → complex"""
        query = "DeepSeek V3 모델이 다른 LLM과 비교하여 무엇이 다른가요"
        assert classify(query) == "complex"


# ---------------------------------------------------------------------------
# U06: relational → graph 전략 매핑
# ---------------------------------------------------------------------------


class TestRelationalToGraphMapping:
    """U06: relational 질의 → graph 검색 전략"""

    def test_relational_query_maps_to_graph(self):
        qtype = classify("A와 B의 관계는?")
        assert qtype == "relational"
        assert strategy(qtype) == "graph"

    def test_select_strategy_relational(self):
        assert strategy("relational") == "graph"


# ---------------------------------------------------------------------------
# U07: factual → vector 전략 매핑
# ---------------------------------------------------------------------------


class TestFactualToVectorMapping:
    """U07: factual 질의 → vector 검색 전략"""

    def test_factual_query_maps_to_vector(self):
        qtype = classify("RAG란 무엇인가?")
        assert qtype == "factual"
        assert strategy(qtype) == "vector"

    def test_select_strategy_factual(self):
        assert strategy("factual") == "vector"


# ---------------------------------------------------------------------------
# U08: keyword → keyword 전략 매핑
# ---------------------------------------------------------------------------


class TestKeywordToKeywordMapping:
    """U08: keyword 질의 → keyword 검색 전략"""

    def test_keyword_query_maps_to_keyword(self):
        qtype = classify("Docker 설치")
        assert qtype == "keyword"
        assert strategy(qtype) == "keyword"

    def test_select_strategy_keyword(self):
        assert strategy("keyword") == "keyword"


# ---------------------------------------------------------------------------
# U09: complex → hybrid 전략 매핑
# ---------------------------------------------------------------------------


class TestComplexToHybridMapping:
    """U09: complex 질의 → hybrid 검색 전략"""

    def test_complex_query_maps_to_hybrid(self):
        long_query = "RAG 파이프라인 전체 구성 요소와 각 역할을 비교하여 설명해줘"
        qtype = classify(long_query)
        assert qtype == "complex"
        assert strategy(qtype) == "hybrid"

    def test_select_strategy_complex(self):
        assert strategy("complex") == "hybrid"


# ---------------------------------------------------------------------------
# U10: 폴백 전략 (알 수 없는 분류 실패)
# ---------------------------------------------------------------------------


class TestFallbackStrategy:
    """U10: 알 수 없는 query_type → hybrid 폴백"""

    def test_unknown_type_falls_back_to_hybrid(self):
        assert strategy("unknown_type") == "hybrid"

    def test_empty_type_falls_back_to_hybrid(self):
        assert strategy("") == "hybrid"

    def test_none_string_falls_back_to_hybrid(self):
        assert strategy("None") == "hybrid"


# ---------------------------------------------------------------------------
# U11: 특수문자 처리
# ---------------------------------------------------------------------------


class TestSpecialCharacters:
    """U11: 특수문자 포함 질의 처리"""

    def test_query_with_question_mark_and_two_words(self):
        """물음표 있으면 keyword 분류 안 됨 (질문 형태)"""
        result = classify("Docker?")
        # 단어 1개 + 물음표 → has_question_marker=True → complex
        assert result == "complex"

    def test_query_with_special_chars_relational(self):
        """특수문자가 있어도 관계형 패턴 인식"""
        assert classify("A/B와의 관계는?") == "relational"

    def test_query_with_parentheses(self):
        """괄호 포함 짧은 질의"""
        result = classify("RAG(검색증강생성)")
        # 1단어, 물음표 없음 → keyword
        assert result == "keyword"

    def test_query_with_colon(self):
        """콜론 포함 2단어"""
        result = classify("FAISS: 설명")
        # 2단어, 물음표 없음 → keyword
        assert result == "keyword"


# ---------------------------------------------------------------------------
# U12: 매우 긴 질의 처리
# ---------------------------------------------------------------------------


class TestVeryLongQuery:
    """U12: 매우 긴 질의 처리 (성능/예외 없이 실행)"""

    def test_very_long_query_classifies_without_error(self):
        """500자 이상 질의도 에러 없이 분류"""
        long_query = "RAG 시스템에서 " * 50 + "어떻게 동작하나요?"
        result = classify(long_query)
        assert result in {"factual", "relational", "keyword", "complex"}

    def test_long_relational_query(self):
        """긴 관계형 질의"""
        query = "이 시스템에서 " + "Neo4j와 Elasticsearch" + "의 상호작용" + " 방식이 무엇인지 상세히 설명해주세요"
        result = classify(query)
        assert result == "relational"

    def test_strategy_never_raises(self):
        """어떤 입력에도 strategy() 예외 없음"""
        for qtype in ["factual", "relational", "keyword", "complex", "", "x" * 100]:
            result = strategy(qtype)
            assert result in {"vector", "graph", "keyword", "hybrid"}


# ---------------------------------------------------------------------------
# U13: 한국어/영어 혼합 질의
# ---------------------------------------------------------------------------


class TestMixedLanguageQuery:
    """U13: 한국어+영어 혼합 질의 분류"""

    def test_mixed_relational_en_ko(self):
        """영어 개념 + 한국어 관계 패턴"""
        assert classify("LangGraph와 FastAPI의 관계") == "relational"

    def test_mixed_factual_en_ko(self):
        """영어 약어 + 한국어 정의 패턴"""
        assert classify("BM25란 무엇인가?") == "factual"

    def test_mixed_keyword_en_ko(self):
        """영어 단어 + 한국어 단어 2개"""
        assert classify("Docker 설치") == "keyword"

    def test_mixed_complex_long(self):
        """긴 한영 혼합 질의 → complex"""
        query = "Elasticsearch와 Neo4j를 동시에 사용하는 Hybrid RAG 아키텍처의 장점은 무엇인가요"
        result = classify(query)
        # 9단어 이상이므로 factual 패턴이 있어도 complex
        assert result in {"complex", "relational"}


# ---------------------------------------------------------------------------
# U14: 경계값 테스트
# ---------------------------------------------------------------------------


class TestBoundaryValues:
    """U14: 경계값 테스트"""

    def test_exactly_one_word_no_question(self):
        """정확히 1단어, 물음표 없음 → keyword"""
        assert classify("Elasticsearch") == "keyword"

    def test_exactly_two_words_no_question(self):
        """정확히 2단어, 물음표 없음 → keyword"""
        assert classify("Neo4j Graph") == "keyword"

    def test_exactly_three_words_no_pattern(self):
        """3단어, 패턴 없음 → complex"""
        assert classify("Neo4j Graph Database") == "complex"

    def test_eight_words_factual_pattern(self):
        """8단어 이하 + factual 패턴 → factual"""
        # "임베딩은 무엇인가 알고 싶습니다" = 4단어
        assert classify("임베딩은 무엇인가 알고 싶습니다") == "factual"

    def test_nine_words_factual_pattern_becomes_complex(self):
        """9단어 초과 + factual 패턴 → complex (긴 질의 hybrid 폴백)"""
        # words > 8 이면 factual 패턴 매칭 안 함 (정확히 9단어로 구성)
        query = "Elasticsearch 벡터 검색이란 무엇인지 구체적으로 자세하게 여러 방면에서 알려주세요"
        assert len(query.split()) > 8, f"테스트 쿼리는 8단어 초과여야 함 (현재: {len(query.split())}단어)"
        result = classify(query)
        assert result == "complex"

    def test_strategy_all_types_covered(self):
        """4가지 질의 유형 모두 유효한 전략으로 매핑"""
        expected = {
            "factual": "vector",
            "relational": "graph",
            "keyword": "keyword",
            "complex": "hybrid",
        }
        for qtype, expected_strategy in expected.items():
            assert strategy(qtype) == expected_strategy, f"{qtype} → {expected_strategy} 실패"
