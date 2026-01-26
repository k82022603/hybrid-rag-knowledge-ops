"""
EntityExtractionService 단위 테스트

엔티티/관계 추출 + Gleaning 테스트
- 엔티티 파싱
- 관계 파싱
- 메타데이터 파싱
- 중복 제거
- 엔티티 유형 정규화
"""

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from app.agents.state import Entity, Relationship
from app.services.entity_extraction import EntityExtractionService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_ENTITY_RESPONSE = json.dumps({
    "entities": [
        {
            "id": "entity_1",
            "name": "FastAPI",
            "type": "Technology",
            "description": "Python 기반 웹 프레임워크",
        },
        {
            "id": "entity_2",
            "name": "DeepSeek",
            "type": "Organization",
            "description": "LLM 제공 기업",
        },
        {
            "id": "entity_3",
            "name": "RAG 파이프라인",
            "type": "Concept",
            "description": "Retrieval-Augmented Generation",
        },
    ]
}, ensure_ascii=False)


SAMPLE_RELATIONSHIP_RESPONSE = json.dumps({
    "relationships": [
        {
            "source": "entity_1",
            "target": "entity_3",
            "type": "USES",
            "description": "FastAPI가 RAG 파이프라인 서비스에 사용됨",
        },
        {
            "source": "entity_2",
            "target": "entity_3",
            "type": "RELATED_TO",
            "description": "DeepSeek가 RAG 파이프라인의 LLM으로 활용됨",
        },
    ]
}, ensure_ascii=False)


SAMPLE_GLEANING_RESPONSE = json.dumps({
    "entities": [
        {
            "id": "gleaned_1",
            "name": "Elasticsearch",
            "type": "Technology",
            "description": "Vector Search 엔진",
        },
    ]
}, ensure_ascii=False)


SAMPLE_METADATA_RESPONSE = json.dumps({
    "document_type": "기술문서",
    "project_name": "Knowledge Service",
    "valid_start_date": "2026-01-01",
    "valid_end_date": None,
    "categories": {
        "level1": "기술",
        "level2": "개발",
        "level3": "AI/ML",
    },
    "summary": "RAG 파이프라인 기술 문서입니다.",
}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# 엔티티 파싱 테스트
# ---------------------------------------------------------------------------


class TestParseEntities:
    """엔티티 파싱 테스트"""

    def setup_method(self):
        """테스트 설정"""
        with patch("app.services.entity_extraction.get_llm_service"):
            self.service = EntityExtractionService()

    def test_parse_valid_json(self):
        """유효한 JSON 파싱"""
        entities = self.service._parse_entities(SAMPLE_ENTITY_RESPONSE)

        assert len(entities) == 3
        assert entities[0].name == "FastAPI"
        assert entities[0].type == "Technology"
        assert entities[1].name == "DeepSeek"
        assert entities[1].type == "Organization"
        assert entities[2].name == "RAG 파이프라인"
        assert entities[2].type == "Concept"

    def test_parse_json_in_code_block(self):
        """마크다운 코드 블록 내 JSON 파싱"""
        response = f'Here are the extracted entities:\n\n```json\n{SAMPLE_ENTITY_RESPONSE}\n```'
        entities = self.service._parse_entities(response)
        assert len(entities) == 3

    def test_parse_empty_response(self):
        """빈 응답 → 빈 리스트"""
        entities = self.service._parse_entities("")
        assert entities == []

    def test_parse_invalid_json(self):
        """잘못된 JSON → 빈 리스트"""
        entities = self.service._parse_entities("not a json {invalid}")
        assert entities == []

    def test_parse_with_id_prefix(self):
        """ID 접두사 적용"""
        entities = self.service._parse_entities(
            SAMPLE_ENTITY_RESPONSE,
            id_prefix="gleaned_1_",
        )

        assert len(entities) == 3
        assert entities[0].id.startswith("gleaned_1_")

    def test_parse_no_entities_key(self):
        """entities 키 없음 → 빈 리스트"""
        response = json.dumps({"data": []})
        entities = self.service._parse_entities(response)
        assert entities == []


# ---------------------------------------------------------------------------
# 관계 파싱 테스트
# ---------------------------------------------------------------------------


class TestParseRelationships:
    """관계 파싱 테스트"""

    def setup_method(self):
        """테스트 설정"""
        with patch("app.services.entity_extraction.get_llm_service"):
            self.service = EntityExtractionService()

        self.entities = [
            Entity(id="entity_1", name="FastAPI", type="Technology"),
            Entity(id="entity_2", name="DeepSeek", type="Organization"),
            Entity(id="entity_3", name="RAG 파이프라인", type="Concept"),
        ]

    def test_parse_valid_relationships(self):
        """유효한 관계 파싱"""
        relationships = self.service._parse_relationships(
            SAMPLE_RELATIONSHIP_RESPONSE,
            self.entities,
        )

        assert len(relationships) == 2
        assert relationships[0].source == "entity_1"
        assert relationships[0].target == "entity_3"
        assert relationships[0].type == "USES"

    def test_filter_invalid_entity_ids(self):
        """존재하지 않는 엔티티 ID → 필터링"""
        response = json.dumps({
            "relationships": [
                {
                    "source": "entity_1",
                    "target": "unknown_entity",
                    "type": "USES",
                },
                {
                    "source": "entity_1",
                    "target": "entity_2",
                    "type": "RELATED_TO",
                },
            ]
        })

        relationships = self.service._parse_relationships(response, self.entities)

        # unknown_entity가 포함된 첫 번째는 필터링, 두 번째만 남음
        assert len(relationships) == 1
        assert relationships[0].target == "entity_2"

    def test_normalize_relationship_type(self):
        """알 수 없는 관계 유형 → RELATED_TO"""
        response = json.dumps({
            "relationships": [
                {
                    "source": "entity_1",
                    "target": "entity_2",
                    "type": "INVENTED",  # 알 수 없는 유형
                },
            ]
        })

        relationships = self.service._parse_relationships(response, self.entities)
        assert len(relationships) == 1
        assert relationships[0].type == "RELATED_TO"

    def test_empty_entities(self):
        """엔티티 없음 → 관계도 없음"""
        response = SAMPLE_RELATIONSHIP_RESPONSE
        relationships = self.service._parse_relationships(response, [])
        assert relationships == []


# ---------------------------------------------------------------------------
# 메타데이터 파싱 테스트
# ---------------------------------------------------------------------------


class TestParseMetadata:
    """메타데이터 파싱 테스트"""

    def setup_method(self):
        """테스트 설정"""
        with patch("app.services.entity_extraction.get_llm_service"):
            self.service = EntityExtractionService()

    def test_parse_valid_metadata(self):
        """유효한 메타데이터 파싱"""
        metadata = self.service._parse_metadata(SAMPLE_METADATA_RESPONSE)

        assert metadata.document_type == "기술문서"
        assert metadata.project_name == "Knowledge Service"
        assert metadata.valid_start_date == "2026-01-01"
        assert metadata.valid_end_date is None
        assert metadata.categories is not None
        assert metadata.categories.level1 == "기술"
        assert metadata.categories.level2 == "개발"
        assert metadata.categories.level3 == "AI/ML"
        assert "RAG" in metadata.summary

    def test_parse_invalid_json(self):
        """잘못된 JSON → 기본 메타데이터"""
        metadata = self.service._parse_metadata("not valid json")
        assert metadata.document_type == "unknown"

    def test_parse_missing_categories(self):
        """카테고리 없음"""
        response = json.dumps({
            "document_type": "보고서",
            "project_name": "",
            "summary": "보고서 요약",
        })
        metadata = self.service._parse_metadata(response)
        assert metadata.document_type == "보고서"
        assert metadata.categories is None


# ---------------------------------------------------------------------------
# 중복 제거 테스트
# ---------------------------------------------------------------------------


class TestDeduplicateEntities:
    """엔티티 중복 제거 테스트"""

    def setup_method(self):
        """테스트 설정"""
        with patch("app.services.entity_extraction.get_llm_service"):
            self.service = EntityExtractionService()

    def test_no_duplicates(self):
        """중복 없음"""
        entities = [
            Entity(id="1", name="FastAPI", type="Technology"),
            Entity(id="2", name="DeepSeek", type="Organization"),
        ]

        result = self.service._deduplicate_entities(entities)
        assert len(result) == 2

    def test_exact_duplicates(self):
        """완전 동일 중복"""
        entities = [
            Entity(id="1", name="FastAPI", type="Technology"),
            Entity(id="2", name="FastAPI", type="Technology"),
        ]

        result = self.service._deduplicate_entities(entities)
        assert len(result) == 1

    def test_case_insensitive_duplicates(self):
        """대소문자 무시 중복"""
        entities = [
            Entity(id="1", name="fastapi", type="Technology"),
            Entity(id="2", name="FastAPI", type="technology"),
        ]

        result = self.service._deduplicate_entities(entities)
        assert len(result) == 1

    def test_different_names_same_type(self):
        """다른 이름, 같은 유형 → 중복 아님"""
        entities = [
            Entity(id="1", name="FastAPI", type="Technology"),
            Entity(id="2", name="Django", type="Technology"),
        ]

        result = self.service._deduplicate_entities(entities)
        assert len(result) == 2

    def test_same_name_different_type(self):
        """같은 이름, 다른 유형 → 중복 아님"""
        entities = [
            Entity(id="1", name="Python", type="Technology"),
            Entity(id="2", name="Python", type="Concept"),
        ]

        result = self.service._deduplicate_entities(entities)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# 엔티티 유형 정규화 테스트
# ---------------------------------------------------------------------------


class TestNormalizeEntityType:
    """엔티티 유형 정규화 테스트"""

    def test_standard_types(self):
        """표준 유형 → 그대로"""
        assert EntityExtractionService._normalize_entity_type("Person") == "Person"
        assert EntityExtractionService._normalize_entity_type("Technology") == "Technology"

    def test_lowercase_mapping(self):
        """소문자 매핑"""
        assert EntityExtractionService._normalize_entity_type("person") == "Person"
        assert EntityExtractionService._normalize_entity_type("organization") == "Organization"
        assert EntityExtractionService._normalize_entity_type("tech") == "Technology"

    def test_alias_mapping(self):
        """별칭 매핑"""
        assert EntityExtractionService._normalize_entity_type("org") == "Organization"
        assert EntityExtractionService._normalize_entity_type("company") == "Organization"
        assert EntityExtractionService._normalize_entity_type("framework") == "Technology"
        assert EntityExtractionService._normalize_entity_type("tool") == "Technology"
        assert EntityExtractionService._normalize_entity_type("method") == "Concept"
        assert EntityExtractionService._normalize_entity_type("place") == "Location"

    def test_unknown_type(self):
        """알 수 없는 유형 → Concept"""
        assert EntityExtractionService._normalize_entity_type("Unknown") == "Concept"
        assert EntityExtractionService._normalize_entity_type("RandomType") == "Concept"


# ---------------------------------------------------------------------------
# EntityExtractionService - 통합 테스트 (LLM Mock)
# ---------------------------------------------------------------------------


class TestExtractEntities:
    """엔티티 추출 통합 테스트 (LLM Mock)"""

    @pytest.mark.asyncio
    async def test_extract_entities_basic(self):
        """기본 엔티티 추출"""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value=SAMPLE_ENTITY_RESPONSE)

        with patch("app.services.entity_extraction.get_llm_service", return_value=mock_llm):
            service = EntityExtractionService(max_gleanings=0)

        entities = await service.extract_entities(
            text="FastAPI와 DeepSeek를 사용한 RAG 파이프라인 설계",
            enable_gleaning=False,
        )

        assert len(entities) == 3
        assert mock_llm.generate.call_count == 1

    @pytest.mark.asyncio
    async def test_extract_entities_with_gleaning(self):
        """Gleaning 포함 엔티티 추출"""
        mock_llm = MagicMock()
        # 1차 추출 → Gleaning 추출 순서
        mock_llm.generate = AsyncMock(
            side_effect=[
                SAMPLE_ENTITY_RESPONSE,  # 1차 추출
                SAMPLE_GLEANING_RESPONSE,  # Gleaning
            ]
        )

        with patch("app.services.entity_extraction.get_llm_service", return_value=mock_llm):
            service = EntityExtractionService(max_gleanings=1)

        entities = await service.extract_entities(
            text="FastAPI와 DeepSeek를 사용한 RAG 파이프라인에서 Elasticsearch 검색을 수행합니다.",
            enable_gleaning=True,
        )

        # 1차 3개 + Gleaning 1개 = 4개
        assert len(entities) == 4
        assert mock_llm.generate.call_count == 2

        # Gleaning으로 Elasticsearch가 추가됨
        names = {e.name for e in entities}
        assert "Elasticsearch" in names

    @pytest.mark.asyncio
    async def test_extract_relationships(self):
        """관계 추출"""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value=SAMPLE_RELATIONSHIP_RESPONSE)

        with patch("app.services.entity_extraction.get_llm_service", return_value=mock_llm):
            service = EntityExtractionService()

        entities = [
            Entity(id="entity_1", name="FastAPI", type="Technology"),
            Entity(id="entity_2", name="DeepSeek", type="Organization"),
            Entity(id="entity_3", name="RAG 파이프라인", type="Concept"),
        ]

        relationships = await service.extract_relationships(
            text="FastAPI에서 DeepSeek를 사용한 RAG 파이프라인",
            entities=entities,
        )

        assert len(relationships) == 2
        assert relationships[0].type == "USES"

    @pytest.mark.asyncio
    async def test_extract_relationships_no_entities(self):
        """엔티티 없음 → 관계 추출 건너뜀"""
        mock_llm = MagicMock()

        with patch("app.services.entity_extraction.get_llm_service", return_value=mock_llm):
            service = EntityExtractionService()

        relationships = await service.extract_relationships(
            text="some text",
            entities=[],
        )

        assert relationships == []
        mock_llm.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_extract_metadata(self):
        """메타데이터 추출"""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value=SAMPLE_METADATA_RESPONSE)

        with patch("app.services.entity_extraction.get_llm_service", return_value=mock_llm):
            service = EntityExtractionService()

        metadata = await service.extract_metadata(
            text="RAG 파이프라인 기술 문서입니다.",
            filename="rag_pipeline_design.pdf",
        )

        assert metadata.document_type == "기술문서"
        assert metadata.project_name == "Knowledge Service"

    @pytest.mark.asyncio
    async def test_extract_metadata_failure_returns_default(self):
        """메타데이터 추출 실패 → 기본값 반환"""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(side_effect=Exception("LLM error"))

        with patch("app.services.entity_extraction.get_llm_service", return_value=mock_llm):
            service = EntityExtractionService()

        metadata = await service.extract_metadata(text="some text")

        assert metadata.document_type == "unknown"
        assert "실패" in metadata.summary
