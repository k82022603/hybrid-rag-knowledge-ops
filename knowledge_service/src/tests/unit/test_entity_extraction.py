"""EntityExtractionService 단위 테스트

STORY-005: KG 엔티티 추출 - 단위 테스트

테스트 범위:
    - EntityExtractionService 초기화 및 설정
    - 엔티티 파싱 (_parse_entities)
    - 관계 파싱 (_parse_relationships)
    - 메타데이터 파싱 (_parse_metadata)
    - 엔티티 중복 제거 (_deduplicate_entities)
    - 엔티티 유형 정규화 (_normalize_entity_type)
    - 1차 엔티티 추출 패스 (_extract_entities_pass)
    - Gleaning 기법 (반복 추출, 조기 중단, 에러 허용)
    - 통합 추출 (extract_full)
    - 메타데이터 추출 (extract_metadata)
    - 텍스트 트렁케이션
    - 싱글톤 팩토리 (get_entity_extraction_service)
    - 에러 핸들링 (LLM 호출 실패, 잘못된 입력)
    - 비동기 메서드 테스트
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from app.agents.state import (
    CategoryMetadata,
    DocumentMetadata,
    Entity,
    ExtractionResult,
    Relationship,
)
from app.core.config import settings
from app.core.exceptions import LLMError
from app.services.entity_extraction import (
    ENTITY_EXTRACTION_PROMPT,
    GLEANING_PROMPT,
    METADATA_EXTRACTION_PROMPT,
    RELATIONSHIP_EXTRACTION_PROMPT,
    EntityExtractionService,
    get_entity_extraction_service,
)


# ---------------------------------------------------------------------------
# 테스트용 상수 (Mock LLM 응답)
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


SAMPLE_GLEANING_RESPONSE_2 = json.dumps({
    "entities": [
        {
            "id": "gleaned_2",
            "name": "Neo4j",
            "type": "Technology",
            "description": "그래프 데이터베이스",
        },
    ]
}, ensure_ascii=False)


SAMPLE_EMPTY_GLEANING_RESPONSE = json.dumps({
    "entities": []
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
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_llm_service():
    """LLM 서비스 Mock 생성"""
    mock = MagicMock()
    mock.generate = AsyncMock()
    return mock


@pytest.fixture
def service(mock_llm_service):
    """EntityExtractionService 인스턴스 생성 (LLM Mock 적용)"""
    with patch(
        "app.services.entity_extraction.get_llm_service",
        return_value=mock_llm_service,
    ):
        svc = EntityExtractionService()
    return svc


@pytest.fixture
def sample_entities():
    """테스트용 엔티티 리스트"""
    return [
        Entity(id="entity_1", name="FastAPI", type="Technology"),
        Entity(id="entity_2", name="DeepSeek", type="Organization"),
        Entity(id="entity_3", name="RAG 파이프라인", type="Concept"),
    ]


@pytest.fixture(autouse=True)
def reset_singleton():
    """각 테스트 전후로 싱글톤 리셋"""
    import app.services.entity_extraction as ext_mod
    ext_mod._extraction_service = None
    yield
    ext_mod._extraction_service = None


# ---------------------------------------------------------------------------
# 1. 초기화 테스트
# ---------------------------------------------------------------------------


class TestEntityExtractionServiceInit:
    """EntityExtractionService 초기화 테스트"""

    def test_default_init(self):
        """기본 초기화 - 기본 파라미터 확인"""
        with patch("app.services.entity_extraction.get_llm_service"):
            service = EntityExtractionService()

        assert service.max_text_length == 30000
        # max_gleanings는 settings.max_gleanings (기본 1)
        assert service.max_gleanings >= 0

    def test_custom_max_text_length(self):
        """커스텀 max_text_length 설정"""
        with patch("app.services.entity_extraction.get_llm_service"):
            service = EntityExtractionService(max_text_length=10000)

        assert service.max_text_length == 10000

    def test_custom_max_gleanings(self):
        """커스텀 max_gleanings 설정"""
        with patch("app.services.entity_extraction.get_llm_service"):
            service = EntityExtractionService(max_gleanings=3)

        assert service.max_gleanings == 3

    def test_zero_gleanings_uses_settings_default(self):
        """max_gleanings=0 -> settings.max_gleanings 사용 (0은 falsy이므로 or 연산자에 의해)"""
        with patch("app.services.entity_extraction.get_llm_service"):
            service = EntityExtractionService(max_gleanings=0)

        # 0은 falsy이므로 settings.max_gleanings (기본 1)가 사용됨
        assert service.max_gleanings == settings.max_gleanings

    def test_none_gleanings_uses_settings_default(self):
        """max_gleanings=None -> settings.max_gleanings 사용"""
        with patch("app.services.entity_extraction.get_llm_service"):
            service = EntityExtractionService(max_gleanings=None)

        assert service.max_gleanings == settings.max_gleanings

    def test_llm_service_injected(self):
        """LLM 서비스가 주입됨"""
        mock_llm = MagicMock()
        with patch(
            "app.services.entity_extraction.get_llm_service",
            return_value=mock_llm,
        ):
            service = EntityExtractionService()

        assert service._llm_service is mock_llm


# ---------------------------------------------------------------------------
# 2. 엔티티 파싱 테스트 (_parse_entities)
# ---------------------------------------------------------------------------


class TestParseEntities:
    """엔티티 파싱 테스트"""

    def setup_method(self):
        """테스트 설정"""
        with patch("app.services.entity_extraction.get_llm_service"):
            self.service = EntityExtractionService()

    def test_parse_valid_json(self):
        """유효한 JSON 파싱 - 3개 엔티티 추출"""
        entities = self.service._parse_entities(SAMPLE_ENTITY_RESPONSE)

        assert len(entities) == 3
        assert entities[0].name == "FastAPI"
        assert entities[0].type == "Technology"
        assert entities[0].id == "entity_1"
        assert entities[0].description == "Python 기반 웹 프레임워크"
        assert entities[1].name == "DeepSeek"
        assert entities[1].type == "Organization"
        assert entities[2].name == "RAG 파이프라인"
        assert entities[2].type == "Concept"

    def test_parse_json_in_code_block(self):
        """마크다운 코드 블록 내 JSON 파싱"""
        response = (
            "Here are the extracted entities:\n\n"
            f"```json\n{SAMPLE_ENTITY_RESPONSE}\n```"
        )
        entities = self.service._parse_entities(response)
        assert len(entities) == 3

    def test_parse_json_in_code_block_without_lang(self):
        """마크다운 코드 블록 (언어 태그 없음) 내 JSON 파싱"""
        response = f"```\n{SAMPLE_ENTITY_RESPONSE}\n```"
        entities = self.service._parse_entities(response)
        assert len(entities) == 3

    def test_parse_empty_response(self):
        """빈 응답 -> 빈 리스트"""
        entities = self.service._parse_entities("")
        assert entities == []

    def test_parse_invalid_json(self):
        """잘못된 JSON -> 빈 리스트"""
        entities = self.service._parse_entities("not a json {invalid}")
        assert entities == []

    def test_parse_with_id_prefix(self):
        """ID 접두사 적용 - gleaning 구분용"""
        entities = self.service._parse_entities(
            SAMPLE_ENTITY_RESPONSE,
            id_prefix="gleaned_1_",
        )

        assert len(entities) == 3
        assert entities[0].id.startswith("gleaned_1_")
        assert entities[1].id.startswith("gleaned_1_")
        assert entities[2].id.startswith("gleaned_1_")

    def test_parse_with_id_prefix_already_prefixed(self):
        """이미 접두사가 있는 ID에는 중복 접두사 미적용"""
        response = json.dumps({
            "entities": [{
                "id": "gleaned_1_existing",
                "name": "Test",
                "type": "Concept",
            }]
        })

        entities = self.service._parse_entities(response, id_prefix="gleaned_1_")
        # 이미 gleaned_1_으로 시작하므로 접두사 미추가
        assert entities[0].id == "gleaned_1_existing"

    def test_parse_no_entities_key(self):
        """entities 키 없음 -> 빈 리스트"""
        response = json.dumps({"data": []})
        entities = self.service._parse_entities(response)
        assert entities == []

    def test_parse_entity_without_description(self):
        """description 없는 엔티티 파싱"""
        response = json.dumps({
            "entities": [{
                "id": "e1",
                "name": "Test Entity",
                "type": "Concept",
            }]
        })
        entities = self.service._parse_entities(response)
        assert len(entities) == 1
        assert entities[0].description is None

    def test_parse_entity_without_id(self):
        """ID 없는 엔티티 -> 빈 문자열 ID"""
        response = json.dumps({
            "entities": [{
                "name": "Test",
                "type": "Concept",
            }]
        })
        entities = self.service._parse_entities(response)
        assert len(entities) == 1
        assert entities[0].id == ""

    def test_parse_entity_without_type(self):
        """type 없는 엔티티 -> Concept 기본값"""
        response = json.dumps({
            "entities": [{
                "id": "e1",
                "name": "Test",
            }]
        })
        entities = self.service._parse_entities(response)
        assert len(entities) == 1
        assert entities[0].type == "Concept"

    def test_parse_entity_type_normalization(self):
        """파싱 시 엔티티 유형 정규화 적용"""
        response = json.dumps({
            "entities": [{
                "id": "e1",
                "name": "Python",
                "type": "language",
            }]
        })
        entities = self.service._parse_entities(response)
        assert entities[0].type == "Technology"

    def test_parse_returns_entity_objects(self):
        """파싱 결과가 Entity Pydantic 모델 인스턴스"""
        entities = self.service._parse_entities(SAMPLE_ENTITY_RESPONSE)
        for entity in entities:
            assert isinstance(entity, Entity)

    def test_parse_korean_entities(self):
        """한국어 엔티티 파싱"""
        response = json.dumps({
            "entities": [{
                "id": "e1",
                "name": "인공지능",
                "type": "Concept",
                "description": "AI 기술의 통칭",
            }]
        }, ensure_ascii=False)
        entities = self.service._parse_entities(response)
        assert entities[0].name == "인공지능"


# ---------------------------------------------------------------------------
# 3. 관계 파싱 테스트 (_parse_relationships)
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
        assert "FastAPI" in relationships[0].description

    def test_filter_invalid_entity_ids(self):
        """존재하지 않는 엔티티 ID -> 필터링"""
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
        assert len(relationships) == 1
        assert relationships[0].target == "entity_2"

    def test_filter_both_source_and_target_invalid(self):
        """소스와 타겟 모두 없는 엔티티 -> 필터링"""
        response = json.dumps({
            "relationships": [{
                "source": "unknown_1",
                "target": "unknown_2",
                "type": "USES",
            }]
        })
        relationships = self.service._parse_relationships(response, self.entities)
        assert relationships == []

    def test_normalize_relationship_type(self):
        """알 수 없는 관계 유형 -> RELATED_TO"""
        response = json.dumps({
            "relationships": [{
                "source": "entity_1",
                "target": "entity_2",
                "type": "INVENTED",
            }]
        })

        relationships = self.service._parse_relationships(response, self.entities)
        assert len(relationships) == 1
        assert relationships[0].type == "RELATED_TO"

    def test_valid_relationship_types(self):
        """유효한 모든 관계 유형 확인"""
        valid_types = [
            "CREATED", "PARTICIPATED", "USES",
            "BELONGS_TO", "RELATED_TO", "MANAGES", "DEPENDS_ON",
        ]

        for rel_type in valid_types:
            response = json.dumps({
                "relationships": [{
                    "source": "entity_1",
                    "target": "entity_2",
                    "type": rel_type,
                }]
            })
            rels = self.service._parse_relationships(response, self.entities)
            assert len(rels) == 1
            assert rels[0].type == rel_type

    def test_relationship_type_case_insensitive(self):
        """관계 유형 대소문자 무관 (uppercase로 변환)"""
        response = json.dumps({
            "relationships": [{
                "source": "entity_1",
                "target": "entity_2",
                "type": "uses",
            }]
        })
        rels = self.service._parse_relationships(response, self.entities)
        assert rels[0].type == "USES"

    def test_empty_entities(self):
        """엔티티 없음 -> 모든 관계 필터링됨"""
        response = SAMPLE_RELATIONSHIP_RESPONSE
        relationships = self.service._parse_relationships(response, [])
        assert relationships == []

    def test_parse_empty_response(self):
        """빈 응답 -> 빈 리스트"""
        relationships = self.service._parse_relationships("", self.entities)
        assert relationships == []

    def test_parse_invalid_json_response(self):
        """잘못된 JSON -> 빈 리스트"""
        relationships = self.service._parse_relationships(
            "invalid json", self.entities
        )
        assert relationships == []

    def test_parse_no_relationships_key(self):
        """relationships 키 없음 -> 빈 리스트"""
        response = json.dumps({"data": []})
        relationships = self.service._parse_relationships(response, self.entities)
        assert relationships == []

    def test_relationship_returns_pydantic_model(self):
        """파싱 결과가 Relationship Pydantic 모델 인스턴스"""
        relationships = self.service._parse_relationships(
            SAMPLE_RELATIONSHIP_RESPONSE, self.entities
        )
        for rel in relationships:
            assert isinstance(rel, Relationship)

    def test_relationship_without_description(self):
        """description 없는 관계 파싱"""
        response = json.dumps({
            "relationships": [{
                "source": "entity_1",
                "target": "entity_2",
                "type": "USES",
            }]
        })
        rels = self.service._parse_relationships(response, self.entities)
        assert len(rels) == 1
        assert rels[0].description is None


# ---------------------------------------------------------------------------
# 4. 메타데이터 파싱 테스트 (_parse_metadata)
# ---------------------------------------------------------------------------


class TestParseMetadata:
    """메타데이터 파싱 테스트"""

    def setup_method(self):
        """테스트 설정"""
        with patch("app.services.entity_extraction.get_llm_service"):
            self.service = EntityExtractionService()

    def test_parse_valid_metadata(self):
        """유효한 메타데이터 파싱 - 전체 필드 확인"""
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
        """잘못된 JSON -> 기본 메타데이터"""
        metadata = self.service._parse_metadata("not valid json")
        assert metadata.document_type == "unknown"
        assert "파싱 실패" in metadata.summary

    def test_parse_empty_response(self):
        """빈 응답 -> 기본 메타데이터"""
        metadata = self.service._parse_metadata("")
        assert metadata.document_type == "unknown"

    def test_parse_missing_categories(self):
        """카테고리 없음 -> categories=None"""
        response = json.dumps({
            "document_type": "보고서",
            "project_name": "",
            "summary": "보고서 요약",
        })
        metadata = self.service._parse_metadata(response)
        assert metadata.document_type == "보고서"
        assert metadata.categories is None

    def test_parse_partial_categories(self):
        """부분 카테고리 (level3 없음)"""
        response = json.dumps({
            "document_type": "가이드",
            "categories": {
                "level1": "경영",
                "level2": "전략",
            },
            "summary": "전략 가이드",
        })
        metadata = self.service._parse_metadata(response)
        assert metadata.categories is not None
        assert metadata.categories.level1 == "경영"
        assert metadata.categories.level2 == "전략"
        assert metadata.categories.level3 is None

    def test_parse_missing_document_type(self):
        """document_type 없음 -> 'unknown' 기본값"""
        response = json.dumps({"summary": "요약"})
        metadata = self.service._parse_metadata(response)
        assert metadata.document_type == "unknown"

    def test_parse_missing_project_name(self):
        """project_name 없음 -> 빈 문자열 기본값"""
        response = json.dumps({"document_type": "기술문서"})
        metadata = self.service._parse_metadata(response)
        assert metadata.project_name == ""

    def test_returns_document_metadata_model(self):
        """반환값이 DocumentMetadata Pydantic 모델 인스턴스"""
        metadata = self.service._parse_metadata(SAMPLE_METADATA_RESPONSE)
        assert isinstance(metadata, DocumentMetadata)
        if metadata.categories:
            assert isinstance(metadata.categories, CategoryMetadata)


# ---------------------------------------------------------------------------
# 5. 중복 제거 테스트 (_deduplicate_entities)
# ---------------------------------------------------------------------------


class TestDeduplicateEntities:
    """엔티티 중복 제거 테스트"""

    def setup_method(self):
        """테스트 설정"""
        with patch("app.services.entity_extraction.get_llm_service"):
            self.service = EntityExtractionService()

    def test_no_duplicates(self):
        """중복 없는 경우 -> 그대로 반환"""
        entities = [
            Entity(id="1", name="FastAPI", type="Technology"),
            Entity(id="2", name="DeepSeek", type="Organization"),
        ]
        result = self.service._deduplicate_entities(entities)
        assert len(result) == 2

    def test_exact_duplicates(self):
        """완전 동일 중복 -> 첫 번째만 유지"""
        entities = [
            Entity(id="1", name="FastAPI", type="Technology"),
            Entity(id="2", name="FastAPI", type="Technology"),
        ]
        result = self.service._deduplicate_entities(entities)
        assert len(result) == 1
        assert result[0].id == "1"

    def test_case_insensitive_duplicates(self):
        """대소문자 무시 중복 제거"""
        entities = [
            Entity(id="1", name="fastapi", type="Technology"),
            Entity(id="2", name="FastAPI", type="technology"),
        ]
        result = self.service._deduplicate_entities(entities)
        assert len(result) == 1

    def test_whitespace_trimmed(self):
        """공백 포함 이름도 중복으로 인식"""
        entities = [
            Entity(id="1", name="FastAPI", type="Technology"),
            Entity(id="2", name=" FastAPI ", type="Technology"),
        ]
        result = self.service._deduplicate_entities(entities)
        assert len(result) == 1

    def test_different_names_same_type(self):
        """다른 이름, 같은 유형 -> 중복 아님"""
        entities = [
            Entity(id="1", name="FastAPI", type="Technology"),
            Entity(id="2", name="Django", type="Technology"),
        ]
        result = self.service._deduplicate_entities(entities)
        assert len(result) == 2

    def test_same_name_different_type(self):
        """같은 이름, 다른 유형 -> 중복 아님"""
        entities = [
            Entity(id="1", name="Python", type="Technology"),
            Entity(id="2", name="Python", type="Concept"),
        ]
        result = self.service._deduplicate_entities(entities)
        assert len(result) == 2

    def test_empty_list(self):
        """빈 리스트 -> 빈 리스트"""
        result = self.service._deduplicate_entities([])
        assert result == []

    def test_single_entity(self):
        """단일 엔티티 -> 그대로"""
        entities = [Entity(id="1", name="FastAPI", type="Technology")]
        result = self.service._deduplicate_entities(entities)
        assert len(result) == 1

    def test_multiple_duplicates(self):
        """여러 중복 -> 각 유형별 첫 번째만 유지"""
        entities = [
            Entity(id="1", name="FastAPI", type="Technology"),
            Entity(id="2", name="fastapi", type="technology"),
            Entity(id="3", name="FASTAPI", type="Technology"),
            Entity(id="4", name="DeepSeek", type="Organization"),
            Entity(id="5", name="deepseek", type="organization"),
        ]
        result = self.service._deduplicate_entities(entities)
        assert len(result) == 2
        assert result[0].id == "1"
        assert result[1].id == "4"


# ---------------------------------------------------------------------------
# 6. 엔티티 유형 정규화 테스트 (_normalize_entity_type)
# ---------------------------------------------------------------------------


class TestNormalizeEntityType:
    """엔티티 유형 정규화 테스트"""

    def test_standard_types_passthrough(self):
        """표준 유형 -> 그대로 반환"""
        standard_types = [
            "Person", "Organization", "Technology",
            "Project", "Concept", "Date", "Location",
        ]
        for t in standard_types:
            assert EntityExtractionService._normalize_entity_type(t) == t

    def test_lowercase_mapping(self):
        """소문자 매핑"""
        assert EntityExtractionService._normalize_entity_type("person") == "Person"
        assert EntityExtractionService._normalize_entity_type("organization") == "Organization"
        assert EntityExtractionService._normalize_entity_type("technology") == "Technology"
        assert EntityExtractionService._normalize_entity_type("project") == "Project"
        assert EntityExtractionService._normalize_entity_type("concept") == "Concept"
        assert EntityExtractionService._normalize_entity_type("date") == "Date"
        assert EntityExtractionService._normalize_entity_type("location") == "Location"

    def test_alias_mapping(self):
        """별칭 매핑 - 다양한 동의어 처리"""
        # Organization 별칭
        assert EntityExtractionService._normalize_entity_type("org") == "Organization"
        assert EntityExtractionService._normalize_entity_type("company") == "Organization"

        # Technology 별칭
        assert EntityExtractionService._normalize_entity_type("tech") == "Technology"
        assert EntityExtractionService._normalize_entity_type("framework") == "Technology"
        assert EntityExtractionService._normalize_entity_type("tool") == "Technology"
        assert EntityExtractionService._normalize_entity_type("language") == "Technology"

        # Person 별칭
        assert EntityExtractionService._normalize_entity_type("people") == "Person"

        # Concept 별칭
        assert EntityExtractionService._normalize_entity_type("method") == "Concept"
        assert EntityExtractionService._normalize_entity_type("methodology") == "Concept"

        # Date 별칭
        assert EntityExtractionService._normalize_entity_type("time") == "Date"
        assert EntityExtractionService._normalize_entity_type("period") == "Date"

        # Location 별칭
        assert EntityExtractionService._normalize_entity_type("place") == "Location"

    def test_unknown_type_fallback_to_concept(self):
        """알 수 없는 유형 -> Concept"""
        assert EntityExtractionService._normalize_entity_type("Unknown") == "Concept"
        assert EntityExtractionService._normalize_entity_type("RandomType") == "Concept"
        assert EntityExtractionService._normalize_entity_type("Product") == "Concept"

    def test_whitespace_handling(self):
        """공백 포함 유형 처리"""
        assert EntityExtractionService._normalize_entity_type(" person ") == "Person"
        assert EntityExtractionService._normalize_entity_type("  tech  ") == "Technology"

    def test_static_method(self):
        """정적 메서드로 호출 가능"""
        result = EntityExtractionService._normalize_entity_type("person")
        assert result == "Person"


# ---------------------------------------------------------------------------
# 7. 1차 엔티티 추출 패스 테스트 (_extract_entities_pass)
# ---------------------------------------------------------------------------


class TestExtractEntitiesPass:
    """1차 엔티티 추출 패스 테스트"""

    @pytest.mark.asyncio
    async def test_successful_extraction(self):
        """성공적인 1차 추출"""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value=SAMPLE_ENTITY_RESPONSE)

        with patch(
            "app.services.entity_extraction.get_llm_service",
            return_value=mock_llm,
        ):
            service = EntityExtractionService()

        entities = await service._extract_entities_pass("테스트 텍스트")

        assert len(entities) == 3
        mock_llm.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_llm_error_propagates(self):
        """LLM 에러 전파 (LLMError는 re-raise)"""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(side_effect=LLMError("API 키 오류"))

        with patch(
            "app.services.entity_extraction.get_llm_service",
            return_value=mock_llm,
        ):
            service = EntityExtractionService()

        with pytest.raises(LLMError):
            await service._extract_entities_pass("테스트")

    @pytest.mark.asyncio
    async def test_generic_exception_returns_empty(self):
        """일반 예외 -> 빈 리스트 반환 (graceful)"""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(side_effect=ValueError("parse error"))

        with patch(
            "app.services.entity_extraction.get_llm_service",
            return_value=mock_llm,
        ):
            service = EntityExtractionService()

        entities = await service._extract_entities_pass("테스트")
        assert entities == []


# ---------------------------------------------------------------------------
# 8. Gleaning 패스 테스트 (_gleaning_pass)
# ---------------------------------------------------------------------------


class TestGleaningPass:
    """Gleaning 패스 테스트"""

    @pytest.mark.asyncio
    async def test_successful_gleaning(self):
        """성공적인 Gleaning - 추가 엔티티 추출"""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value=SAMPLE_GLEANING_RESPONSE)

        with patch(
            "app.services.entity_extraction.get_llm_service",
            return_value=mock_llm,
        ):
            service = EntityExtractionService()

        existing = [
            Entity(id="e1", name="FastAPI", type="Technology"),
        ]

        gleaned = await service._gleaning_pass(
            text="테스트 텍스트",
            existing_entities=existing,
            pass_number=1,
        )

        assert len(gleaned) == 1
        assert gleaned[0].name == "Elasticsearch"

    @pytest.mark.asyncio
    async def test_gleaning_empty_result(self):
        """Gleaning에서 추가 엔티티 없음"""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value=SAMPLE_EMPTY_GLEANING_RESPONSE)

        with patch(
            "app.services.entity_extraction.get_llm_service",
            return_value=mock_llm,
        ):
            service = EntityExtractionService()

        gleaned = await service._gleaning_pass(
            text="텍스트",
            existing_entities=[],
            pass_number=1,
        )
        assert gleaned == []

    @pytest.mark.asyncio
    async def test_gleaning_failure_returns_empty(self):
        """Gleaning 실패 시 빈 리스트 반환 (중단하지 않음)"""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(side_effect=Exception("Network error"))

        with patch(
            "app.services.entity_extraction.get_llm_service",
            return_value=mock_llm,
        ):
            service = EntityExtractionService()

        gleaned = await service._gleaning_pass(
            text="텍스트",
            existing_entities=[],
            pass_number=1,
        )
        assert gleaned == []

    @pytest.mark.asyncio
    async def test_gleaning_pass_uses_id_prefix(self):
        """Gleaning 패스에서 ID 접두사 적용"""
        response = json.dumps({
            "entities": [{
                "id": "new_1",
                "name": "Test",
                "type": "Concept",
            }]
        })
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value=response)

        with patch(
            "app.services.entity_extraction.get_llm_service",
            return_value=mock_llm,
        ):
            service = EntityExtractionService()

        gleaned = await service._gleaning_pass(
            text="텍스트",
            existing_entities=[],
            pass_number=2,
        )
        assert len(gleaned) == 1
        assert "gleaned_2_" in gleaned[0].id


# ---------------------------------------------------------------------------
# 9. extract_entities 통합 테스트 (비동기)
# ---------------------------------------------------------------------------


class TestExtractEntities:
    """엔티티 추출 통합 테스트 (LLM Mock)"""

    @pytest.mark.asyncio
    async def test_extract_entities_basic(self):
        """기본 엔티티 추출 (Gleaning 비활성화)"""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value=SAMPLE_ENTITY_RESPONSE)

        with patch(
            "app.services.entity_extraction.get_llm_service",
            return_value=mock_llm,
        ):
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
        mock_llm.generate = AsyncMock(
            side_effect=[
                SAMPLE_ENTITY_RESPONSE,      # 1차 추출
                SAMPLE_GLEANING_RESPONSE,     # Gleaning 1회
            ]
        )

        with patch(
            "app.services.entity_extraction.get_llm_service",
            return_value=mock_llm,
        ):
            service = EntityExtractionService(max_gleanings=1)

        entities = await service.extract_entities(
            text="FastAPI, DeepSeek, RAG 파이프라인, Elasticsearch",
            enable_gleaning=True,
        )

        # 1차 3개 + Gleaning 1개 = 4개
        assert len(entities) == 4
        assert mock_llm.generate.call_count == 2

        names = {e.name for e in entities}
        assert "Elasticsearch" in names

    @pytest.mark.asyncio
    async def test_extract_entities_gleaning_stops_when_empty(self):
        """Gleaning에서 추가 엔티티 없으면 조기 중단"""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(
            side_effect=[
                SAMPLE_ENTITY_RESPONSE,          # 1차 추출
                SAMPLE_EMPTY_GLEANING_RESPONSE,  # 비어있음 -> 중단
            ]
        )

        with patch(
            "app.services.entity_extraction.get_llm_service",
            return_value=mock_llm,
        ):
            service = EntityExtractionService(max_gleanings=3)

        entities = await service.extract_entities(
            text="테스트 텍스트",
            enable_gleaning=True,
        )

        # 1차 호출 + Gleaning 1회 = 총 2회 (나머지 2회는 조기 중단)
        assert mock_llm.generate.call_count == 2
        assert len(entities) == 3

    @pytest.mark.asyncio
    async def test_extract_entities_multiple_gleanings(self):
        """다중 Gleaning 패스 수행"""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(
            side_effect=[
                SAMPLE_ENTITY_RESPONSE,       # 1차 추출 (3개)
                SAMPLE_GLEANING_RESPONSE,     # Gleaning 1 (1개)
                SAMPLE_GLEANING_RESPONSE_2,   # Gleaning 2 (1개)
            ]
        )

        with patch(
            "app.services.entity_extraction.get_llm_service",
            return_value=mock_llm,
        ):
            service = EntityExtractionService(max_gleanings=2)

        entities = await service.extract_entities(
            text="테스트 텍스트",
            enable_gleaning=True,
        )

        # 3 + 1 + 1 = 5
        assert len(entities) == 5
        assert mock_llm.generate.call_count == 3
        names = {e.name for e in entities}
        assert "Elasticsearch" in names
        assert "Neo4j" in names

    @pytest.mark.asyncio
    async def test_extract_entities_gleaning_disabled(self):
        """enable_gleaning=False -> Gleaning 건너뜀"""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value=SAMPLE_ENTITY_RESPONSE)

        with patch(
            "app.services.entity_extraction.get_llm_service",
            return_value=mock_llm,
        ):
            service = EntityExtractionService(max_gleanings=3)

        entities = await service.extract_entities(
            text="테스트",
            enable_gleaning=False,
        )

        assert len(entities) == 3
        assert mock_llm.generate.call_count == 1

    @pytest.mark.asyncio
    async def test_extract_entities_text_truncation(self):
        """max_text_length 이상 텍스트 -> 트렁케이션"""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value=SAMPLE_ENTITY_RESPONSE)

        with patch(
            "app.services.entity_extraction.get_llm_service",
            return_value=mock_llm,
        ):
            service = EntityExtractionService(max_text_length=100, max_gleanings=0)

        long_text = "A" * 50000

        entities = await service.extract_entities(
            text=long_text,
            enable_gleaning=False,
        )

        assert len(entities) == 3
        # LLM에 전달된 프롬프트가 트렁케이션된 텍스트를 포함하는지 확인
        call_args = mock_llm.generate.call_args
        prompt = call_args.kwargs.get("prompt", call_args[0][0] if call_args[0] else "")
        # 프롬프트에 전체 50000자가 아닌 트렁케이션된 텍스트가 포함됨
        assert len(prompt) < 50000

    @pytest.mark.asyncio
    async def test_extract_entities_deduplication_applied(self):
        """추출 후 중복 제거 적용"""
        # 1차 추출에서 중복된 엔티티 반환
        duplicate_response = json.dumps({
            "entities": [
                {"id": "e1", "name": "FastAPI", "type": "Technology"},
                {"id": "e2", "name": "fastapi", "type": "technology"},
            ]
        })

        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value=duplicate_response)

        with patch(
            "app.services.entity_extraction.get_llm_service",
            return_value=mock_llm,
        ):
            service = EntityExtractionService(max_gleanings=0)

        entities = await service.extract_entities(
            text="FastAPI 테스트",
            enable_gleaning=False,
        )

        # 중복 제거 후 1개만 남음
        assert len(entities) == 1

    @pytest.mark.asyncio
    async def test_extract_entities_returns_entity_list(self):
        """반환값이 Entity 리스트"""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value=SAMPLE_ENTITY_RESPONSE)

        with patch(
            "app.services.entity_extraction.get_llm_service",
            return_value=mock_llm,
        ):
            service = EntityExtractionService(max_gleanings=0)

        entities = await service.extract_entities(text="test", enable_gleaning=False)

        assert isinstance(entities, list)
        for e in entities:
            assert isinstance(e, Entity)


# ---------------------------------------------------------------------------
# 10. extract_relationships 통합 테스트 (비동기)
# ---------------------------------------------------------------------------


class TestExtractRelationships:
    """관계 추출 통합 테스트"""

    @pytest.mark.asyncio
    async def test_extract_relationships(self):
        """기본 관계 추출"""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value=SAMPLE_RELATIONSHIP_RESPONSE)

        with patch(
            "app.services.entity_extraction.get_llm_service",
            return_value=mock_llm,
        ):
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
        """엔티티 없음 -> 관계 추출 건너뜀"""
        mock_llm = MagicMock()

        with patch(
            "app.services.entity_extraction.get_llm_service",
            return_value=mock_llm,
        ):
            service = EntityExtractionService()

        relationships = await service.extract_relationships(
            text="some text",
            entities=[],
        )

        assert relationships == []
        mock_llm.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_extract_relationships_llm_error(self):
        """LLM 에러 발생 시 LLMError 전파"""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(side_effect=LLMError("LLM 실패"))

        with patch(
            "app.services.entity_extraction.get_llm_service",
            return_value=mock_llm,
        ):
            service = EntityExtractionService()

        entities = [Entity(id="e1", name="Test", type="Concept")]

        with pytest.raises(LLMError):
            await service.extract_relationships(
                text="test", entities=entities
            )

    @pytest.mark.asyncio
    async def test_extract_relationships_generic_error_wraps_as_llm_error(self):
        """일반 예외 -> LLMError로 래핑"""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(side_effect=RuntimeError("unexpected"))

        with patch(
            "app.services.entity_extraction.get_llm_service",
            return_value=mock_llm,
        ):
            service = EntityExtractionService()

        entities = [Entity(id="e1", name="Test", type="Concept")]

        with pytest.raises(LLMError, match="관계 추출 실패"):
            await service.extract_relationships(
                text="test", entities=entities
            )

    @pytest.mark.asyncio
    async def test_extract_relationships_text_truncation(self):
        """관계 추출 시 텍스트 트렁케이션 적용"""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value=SAMPLE_RELATIONSHIP_RESPONSE)

        with patch(
            "app.services.entity_extraction.get_llm_service",
            return_value=mock_llm,
        ):
            service = EntityExtractionService(max_text_length=50)

        entities = [
            Entity(id="entity_1", name="FastAPI", type="Technology"),
            Entity(id="entity_3", name="RAG", type="Concept"),
        ]
        long_text = "X" * 100000

        await service.extract_relationships(
            text=long_text, entities=entities
        )

        # LLM이 호출되었으며, 프롬프트가 트렁케이션된 텍스트 포함
        mock_llm.generate.assert_called_once()


# ---------------------------------------------------------------------------
# 11. extract_full 통합 테스트
# ---------------------------------------------------------------------------


class TestExtractFull:
    """통합 추출 테스트 (엔티티 + 관계)"""

    @pytest.mark.asyncio
    async def test_extract_full_basic(self):
        """기본 통합 추출"""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(
            side_effect=[
                SAMPLE_ENTITY_RESPONSE,         # extract_entities -> 1차 추출
                SAMPLE_RELATIONSHIP_RESPONSE,    # extract_relationships
            ]
        )

        with patch(
            "app.services.entity_extraction.get_llm_service",
            return_value=mock_llm,
        ):
            service = EntityExtractionService(max_gleanings=0)

        result = await service.extract_full(
            text="FastAPI와 DeepSeek를 사용한 RAG 파이프라인",
            enable_gleaning=False,
        )

        assert isinstance(result, ExtractionResult)
        assert len(result.entities) == 3
        assert len(result.relationships) == 2
        assert result.metadata is None

    @pytest.mark.asyncio
    async def test_extract_full_with_gleaning(self):
        """Gleaning 포함 통합 추출"""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(
            side_effect=[
                SAMPLE_ENTITY_RESPONSE,         # 1차 추출
                SAMPLE_GLEANING_RESPONSE,       # Gleaning
                SAMPLE_RELATIONSHIP_RESPONSE,    # 관계 추출
            ]
        )

        with patch(
            "app.services.entity_extraction.get_llm_service",
            return_value=mock_llm,
        ):
            service = EntityExtractionService(max_gleanings=1)

        result = await service.extract_full(
            text="테스트 텍스트",
            enable_gleaning=True,
        )

        assert isinstance(result, ExtractionResult)
        assert len(result.entities) == 4
        assert mock_llm.generate.call_count == 3

    @pytest.mark.asyncio
    async def test_extract_full_returns_extraction_result(self):
        """반환값이 ExtractionResult 모델"""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(
            side_effect=[
                SAMPLE_ENTITY_RESPONSE,
                json.dumps({"relationships": []}),
            ]
        )

        with patch(
            "app.services.entity_extraction.get_llm_service",
            return_value=mock_llm,
        ):
            service = EntityExtractionService(max_gleanings=0)

        result = await service.extract_full(text="test", enable_gleaning=False)

        assert isinstance(result, ExtractionResult)
        assert isinstance(result.entities, list)
        assert isinstance(result.relationships, list)


# ---------------------------------------------------------------------------
# 12. extract_metadata 통합 테스트
# ---------------------------------------------------------------------------


class TestExtractMetadata:
    """메타데이터 추출 통합 테스트"""

    @pytest.mark.asyncio
    async def test_extract_metadata_success(self):
        """성공적인 메타데이터 추출"""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value=SAMPLE_METADATA_RESPONSE)

        with patch(
            "app.services.entity_extraction.get_llm_service",
            return_value=mock_llm,
        ):
            service = EntityExtractionService()

        metadata = await service.extract_metadata(
            text="RAG 파이프라인 기술 문서입니다.",
            filename="rag_pipeline_design.pdf",
        )

        assert metadata.document_type == "기술문서"
        assert metadata.project_name == "Knowledge Service"
        assert isinstance(metadata, DocumentMetadata)

    @pytest.mark.asyncio
    async def test_extract_metadata_without_filename(self):
        """파일명 없이 메타데이터 추출"""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value=SAMPLE_METADATA_RESPONSE)

        with patch(
            "app.services.entity_extraction.get_llm_service",
            return_value=mock_llm,
        ):
            service = EntityExtractionService()

        metadata = await service.extract_metadata(text="테스트 텍스트")

        assert metadata.document_type == "기술문서"
        mock_llm.generate.assert_called_once()
        # 프롬프트에 "(파일명 없음)"이 포함되어야 함
        prompt = mock_llm.generate.call_args.kwargs.get(
            "prompt",
            mock_llm.generate.call_args[0][0] if mock_llm.generate.call_args[0] else "",
        )
        assert "파일명 없음" in prompt

    @pytest.mark.asyncio
    async def test_extract_metadata_failure_returns_default(self):
        """메타데이터 추출 실패 -> 기본값 반환"""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(side_effect=Exception("LLM error"))

        with patch(
            "app.services.entity_extraction.get_llm_service",
            return_value=mock_llm,
        ):
            service = EntityExtractionService()

        metadata = await service.extract_metadata(text="some text")

        assert metadata.document_type == "unknown"
        assert "실패" in metadata.summary
        assert metadata.categories is not None
        assert metadata.categories.level1 == "미분류"

    @pytest.mark.asyncio
    async def test_extract_metadata_llm_error_propagates(self):
        """LLMError는 re-raise"""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(side_effect=LLMError("API key invalid"))

        with patch(
            "app.services.entity_extraction.get_llm_service",
            return_value=mock_llm,
        ):
            service = EntityExtractionService()

        with pytest.raises(LLMError):
            await service.extract_metadata(text="test")

    @pytest.mark.asyncio
    async def test_extract_metadata_text_preview_limited(self):
        """메타데이터 추출 시 텍스트 앞부분 5000자만 사용"""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value=SAMPLE_METADATA_RESPONSE)

        with patch(
            "app.services.entity_extraction.get_llm_service",
            return_value=mock_llm,
        ):
            service = EntityExtractionService()

        long_text = "X" * 100000

        await service.extract_metadata(text=long_text, filename="test.pdf")

        # 프롬프트에 전체 100000자가 아닌 앞부분만 포함
        call_args = mock_llm.generate.call_args
        prompt = call_args.kwargs.get("prompt", call_args[0][0] if call_args[0] else "")
        assert len(prompt) < 100000


# ---------------------------------------------------------------------------
# 13. 에러 핸들링 테스트
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """에러 핸들링 테스트"""

    @pytest.mark.asyncio
    async def test_extract_entities_llm_error_propagates(self):
        """엔티티 추출 시 LLMError 전파"""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(side_effect=LLMError("API 오류"))

        with patch(
            "app.services.entity_extraction.get_llm_service",
            return_value=mock_llm,
        ):
            service = EntityExtractionService(max_gleanings=0)

        with pytest.raises(LLMError):
            await service.extract_entities(
                text="test", enable_gleaning=False
            )

    @pytest.mark.asyncio
    async def test_gleaning_failure_does_not_break_extraction(self):
        """Gleaning 실패 시에도 1차 결과 반환"""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(
            side_effect=[
                SAMPLE_ENTITY_RESPONSE,     # 1차 성공
                Exception("Gleaning failed"),  # Gleaning 실패
            ]
        )

        with patch(
            "app.services.entity_extraction.get_llm_service",
            return_value=mock_llm,
        ):
            service = EntityExtractionService(max_gleanings=1)

        entities = await service.extract_entities(
            text="test", enable_gleaning=True
        )

        # Gleaning 실패해도 1차 결과는 유지
        assert len(entities) == 3

    @pytest.mark.asyncio
    async def test_relationship_extraction_wraps_generic_error(self):
        """관계 추출 시 일반 에러 -> LLMError 래핑"""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(side_effect=TypeError("bad type"))

        with patch(
            "app.services.entity_extraction.get_llm_service",
            return_value=mock_llm,
        ):
            service = EntityExtractionService()

        entities = [Entity(id="e1", name="Test", type="Concept")]

        with pytest.raises(LLMError, match="관계 추출 실패"):
            await service.extract_relationships(
                text="test", entities=entities
            )


# ---------------------------------------------------------------------------
# 14. 텍스트 트렁케이션 테스트
# ---------------------------------------------------------------------------


class TestTextTruncation:
    """텍스트 트렁케이션 동작 테스트"""

    @pytest.mark.asyncio
    async def test_short_text_not_truncated(self):
        """짧은 텍스트 -> 트렁케이션 없음"""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value=SAMPLE_ENTITY_RESPONSE)

        with patch(
            "app.services.entity_extraction.get_llm_service",
            return_value=mock_llm,
        ):
            service = EntityExtractionService(
                max_text_length=1000, max_gleanings=0
            )

        short_text = "짧은 텍스트"
        await service.extract_entities(text=short_text, enable_gleaning=False)

        # 호출된 프롬프트에 원본 텍스트가 포함됨
        call_args = mock_llm.generate.call_args
        prompt = call_args.kwargs.get("prompt", call_args[0][0] if call_args[0] else "")
        assert short_text in prompt

    @pytest.mark.asyncio
    async def test_long_text_truncated(self):
        """긴 텍스트 -> max_text_length에 맞게 트렁케이션"""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value=SAMPLE_ENTITY_RESPONSE)

        max_len = 100
        with patch(
            "app.services.entity_extraction.get_llm_service",
            return_value=mock_llm,
        ):
            service = EntityExtractionService(
                max_text_length=max_len, max_gleanings=0
            )

        long_text = "A" * 50000
        await service.extract_entities(text=long_text, enable_gleaning=False)

        call_args = mock_llm.generate.call_args
        prompt = call_args.kwargs.get("prompt", call_args[0][0] if call_args[0] else "")
        # 프롬프트에 원문 전체가 포함되지 않아야 함
        assert "A" * 50000 not in prompt
        # 트렁케이션된 부분만 포함
        assert "A" * max_len in prompt


# ---------------------------------------------------------------------------
# 15. 싱글톤 팩토리 테스트
# ---------------------------------------------------------------------------


class TestGetEntityExtractionService:
    """싱글톤 팩토리 함수 테스트"""

    def test_singleton_returns_same_instance(self):
        """동일 인스턴스 반환"""
        with patch("app.services.entity_extraction.get_llm_service"):
            svc1 = get_entity_extraction_service()
            svc2 = get_entity_extraction_service()
            assert svc1 is svc2

    def test_singleton_reset(self):
        """싱글톤 리셋 (autouse fixture에 의해)"""
        import app.services.entity_extraction as ext_mod

        with patch("app.services.entity_extraction.get_llm_service"):
            svc1 = get_entity_extraction_service()
            ext_mod._extraction_service = None
            svc2 = get_entity_extraction_service()
            assert svc1 is not svc2

    def test_singleton_is_entity_extraction_service(self):
        """반환값이 EntityExtractionService 인스턴스"""
        with patch("app.services.entity_extraction.get_llm_service"):
            svc = get_entity_extraction_service()
            assert isinstance(svc, EntityExtractionService)


# ---------------------------------------------------------------------------
# 16. 프롬프트 템플릿 테스트
# ---------------------------------------------------------------------------


class TestPromptTemplates:
    """프롬프트 템플릿 유효성 테스트"""

    def test_entity_extraction_prompt_has_text_placeholder(self):
        """엔티티 추출 프롬프트에 {text} 플레이스홀더 포함"""
        assert "{text}" in ENTITY_EXTRACTION_PROMPT

    def test_relationship_extraction_prompt_has_placeholders(self):
        """관계 추출 프롬프트에 필수 플레이스홀더 포함"""
        assert "{text}" in RELATIONSHIP_EXTRACTION_PROMPT
        assert "{entities_json}" in RELATIONSHIP_EXTRACTION_PROMPT

    def test_gleaning_prompt_has_placeholders(self):
        """Gleaning 프롬프트에 필수 플레이스홀더 포함"""
        assert "{text}" in GLEANING_PROMPT
        assert "{existing_entities_json}" in GLEANING_PROMPT

    def test_metadata_extraction_prompt_has_placeholders(self):
        """메타데이터 추출 프롬프트에 필수 플레이스홀더 포함"""
        assert "{text}" in METADATA_EXTRACTION_PROMPT
        assert "{filename}" in METADATA_EXTRACTION_PROMPT

    def test_entity_prompt_format_does_not_raise(self):
        """엔티티 프롬프트 포맷팅 에러 없음"""
        formatted = ENTITY_EXTRACTION_PROMPT.format(text="테스트 텍스트")
        assert "테스트 텍스트" in formatted

    def test_relationship_prompt_format_does_not_raise(self):
        """관계 프롬프트 포맷팅 에러 없음"""
        formatted = RELATIONSHIP_EXTRACTION_PROMPT.format(
            text="텍스트", entities_json="[]"
        )
        assert "텍스트" in formatted

    def test_gleaning_prompt_format_does_not_raise(self):
        """Gleaning 프롬프트 포맷팅 에러 없음"""
        formatted = GLEANING_PROMPT.format(
            text="텍스트", existing_entities_json="[]"
        )
        assert "텍스트" in formatted

    def test_metadata_prompt_format_does_not_raise(self):
        """메타데이터 프롬프트 포맷팅 에러 없음"""
        formatted = METADATA_EXTRACTION_PROMPT.format(
            text="텍스트", filename="test.pdf"
        )
        assert "텍스트" in formatted
        assert "test.pdf" in formatted


# ---------------------------------------------------------------------------
# 17. 엣지 케이스 테스트
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """엣지 케이스 테스트"""

    @pytest.mark.asyncio
    async def test_empty_text_extraction(self):
        """빈 텍스트에서 추출"""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(
            return_value=json.dumps({"entities": []})
        )

        with patch(
            "app.services.entity_extraction.get_llm_service",
            return_value=mock_llm,
        ):
            service = EntityExtractionService(max_gleanings=0)

        entities = await service.extract_entities(
            text="", enable_gleaning=False
        )
        assert entities == []

    @pytest.mark.asyncio
    async def test_special_characters_in_text(self):
        """특수 문자 포함 텍스트"""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value=SAMPLE_ENTITY_RESPONSE)

        with patch(
            "app.services.entity_extraction.get_llm_service",
            return_value=mock_llm,
        ):
            service = EntityExtractionService(max_gleanings=0)

        text_with_special = 'JSON {{"key": "value"}} & <html> "quotes" \\ escape'
        entities = await service.extract_entities(
            text=text_with_special, enable_gleaning=False
        )
        # 에러 없이 실행됨
        assert isinstance(entities, list)

    @pytest.mark.asyncio
    async def test_unicode_text_extraction(self):
        """유니코드 텍스트 추출"""
        unicode_response = json.dumps({
            "entities": [{
                "id": "e1",
                "name": "OpenAI",
                "type": "Organization",
                "description": "GPT 시리즈를 개발한 AI 기업",
            }]
        }, ensure_ascii=False)

        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value=unicode_response)

        with patch(
            "app.services.entity_extraction.get_llm_service",
            return_value=mock_llm,
        ):
            service = EntityExtractionService(max_gleanings=0)

        entities = await service.extract_entities(
            text="OpenAI의 CEO Sam Altman이 GPT-4를 발표했다.",
            enable_gleaning=False,
        )
        assert len(entities) == 1
        assert entities[0].name == "OpenAI"

    def test_parse_entities_with_extra_fields(self):
        """추가 필드가 있는 엔티티 JSON -> 무시하고 파싱"""
        response = json.dumps({
            "entities": [{
                "id": "e1",
                "name": "Test",
                "type": "Concept",
                "description": "설명",
                "confidence": 0.95,    # 추가 필드
                "aliases": ["테스트"],  # 추가 필드
            }]
        })

        with patch("app.services.entity_extraction.get_llm_service"):
            service = EntityExtractionService()

        entities = service._parse_entities(response)
        assert len(entities) == 1
        assert entities[0].name == "Test"

    def test_parse_relationships_with_extra_fields(self):
        """추가 필드가 있는 관계 JSON -> 무시하고 파싱"""
        response = json.dumps({
            "relationships": [{
                "source": "entity_1",
                "target": "entity_2",
                "type": "USES",
                "confidence": 0.8,  # 추가 필드
            }]
        })

        entities = [
            Entity(id="entity_1", name="A", type="Concept"),
            Entity(id="entity_2", name="B", type="Concept"),
        ]

        with patch("app.services.entity_extraction.get_llm_service"):
            service = EntityExtractionService()

        rels = service._parse_relationships(response, entities)
        assert len(rels) == 1

    @pytest.mark.asyncio
    async def test_max_gleanings_zero_is_falsy(self):
        """max_gleanings=0은 'or' 연산에서 falsy -> settings.max_gleanings 사용"""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(
            side_effect=[
                SAMPLE_ENTITY_RESPONSE,         # 1차 추출
                SAMPLE_EMPTY_GLEANING_RESPONSE,  # Gleaning (빈 결과)
            ]
        )

        with patch(
            "app.services.entity_extraction.get_llm_service",
            return_value=mock_llm,
        ):
            service = EntityExtractionService(max_gleanings=0)

        # max_gleanings=0은 falsy -> settings.max_gleanings (1) 사용
        # 따라서 gleaning이 1회 시도됨
        entities = await service.extract_entities(
            text="test",
            enable_gleaning=True,
        )

        assert len(entities) == 3
        # 1차 추출 + Gleaning 1회 = 2회 호출
        assert mock_llm.generate.call_count == 2

    @pytest.mark.asyncio
    async def test_enable_gleaning_false_skips_gleaning(self):
        """enable_gleaning=False이면 Gleaning 완전 건너뜀"""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value=SAMPLE_ENTITY_RESPONSE)

        with patch(
            "app.services.entity_extraction.get_llm_service",
            return_value=mock_llm,
        ):
            service = EntityExtractionService()

        entities = await service.extract_entities(
            text="test",
            enable_gleaning=False,
        )

        assert len(entities) == 3
        assert mock_llm.generate.call_count == 1  # 1차 추출만
