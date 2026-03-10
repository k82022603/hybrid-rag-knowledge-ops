"""
엔티티 추출 서비스 모듈

LLM 기반 엔티티/관계 추출 + Gleaning 기법
- 문서에서 엔티티(인물, 조직, 기술, 프로젝트 등) 추출
- 엔티티 간 관계 추출
- Gleaning: 다중 패스 추출로 누락 엔티티 보완 (+33% Recall)
- 메타데이터 추출 (문서 유형, 카테고리 등)
"""

import json
import time
from typing import Any, Dict, List, Optional

from app.agents.state import (
    CategoryMetadata,
    DocumentMetadata,
    Entity,
    ExtractionResult,
    Relationship,
)
from app.core.config import settings
from app.core.exceptions import LLMError
from app.core.logging import get_logger
from app.services.llm_service import get_llm_service
from app.utils.text import extract_json_from_text

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# 프롬프트 템플릿
# ---------------------------------------------------------------------------

ENTITY_EXTRACTION_PROMPT = """다음 텍스트에서 주요 엔티티(개체)를 추출하세요.

## 추출할 엔티티 유형
- **Person**: 인물 (이름, 직책 포함)
- **Organization**: 조직, 회사, 부서
- **Technology**: 기술, 프레임워크, 도구, 프로그래밍 언어
- **Project**: 프로젝트명
- **Concept**: 핵심 개념, 방법론
- **Date**: 중요 날짜, 기간
- **Location**: 장소

## 텍스트
{text}

## 출력 형식 (JSON)
```json
{{
  "entities": [
    {{
      "id": "entity_1",
      "name": "엔티티명",
      "type": "Person|Organization|Technology|Project|Concept|Date|Location",
      "description": "간단한 설명 (1-2문장)"
    }}
  ]
}}
```

중요: 반드시 유효한 JSON 형식으로 응답하세요."""


RELATIONSHIP_EXTRACTION_PROMPT = """다음 텍스트와 추출된 엔티티를 기반으로 엔티티 간 관계를 추출하세요.

## 추출할 관계 유형
- **CREATED**: 생성/개발 관계 (A가 B를 만듦)
- **PARTICIPATED**: 참여 관계 (A가 B에 참여)
- **USES**: 사용 관계 (A가 B를 사용)
- **BELONGS_TO**: 소속 관계 (A가 B에 속함)
- **RELATED_TO**: 일반적 관련 관계
- **MANAGES**: 관리 관계 (A가 B를 관리)
- **DEPENDS_ON**: 의존 관계 (A가 B에 의존)

## 텍스트
{text}

## 추출된 엔티티
{entities_json}

## 출력 형식 (JSON)
```json
{{
  "relationships": [
    {{
      "source": "source_entity_id",
      "target": "target_entity_id",
      "type": "CREATED|PARTICIPATED|USES|BELONGS_TO|RELATED_TO|MANAGES|DEPENDS_ON",
      "description": "관계 설명 (1문장)"
    }}
  ]
}}
```

중요: source와 target은 위 엔티티의 id를 사용하세요. 반드시 유효한 JSON으로 응답하세요."""


GLEANING_PROMPT = """이전에 아래 텍스트에서 엔티티를 추출했습니다.
혹시 누락된 중요한 엔티티가 있는지 확인하고, 추가로 추출하세요.

## 원본 텍스트
{text}

## 이미 추출된 엔티티
{existing_entities_json}

## 추가 추출 지침
1. 이미 추출된 엔티티는 제외하세요.
2. 약어, 별칭, 간접적으로 언급된 엔티티를 찾으세요.
3. 문맥상 암시된 기술이나 조직을 찾으세요.
4. 추가로 발견된 것이 없으면 빈 리스트를 반환하세요.

## 출력 형식 (JSON)
```json
{{
  "entities": [
    {{
      "id": "gleaned_1",
      "name": "엔티티명",
      "type": "Person|Organization|Technology|Project|Concept|Date|Location",
      "description": "간단한 설명"
    }}
  ]
}}
```

중요: 반드시 유효한 JSON 형식으로 응답하세요."""


METADATA_EXTRACTION_PROMPT = """다음 텍스트의 메타데이터를 추출하세요.

## 텍스트 (앞부분)
{text}

## 파일명 (힌트)
{filename}

## 추출 항목
1. **document_type**: 문서 유형
   - 기술문서, 제안서, 회의록, 매뉴얼, 보고서, 가이드, 규정, 공지사항, 기타
2. **project_name**: 관련 프로젝트명 (없으면 빈 문자열)
3. **valid_start_date**: 유효 시작일 (YYYY-MM-DD, 없으면 null)
4. **valid_end_date**: 유효 종료일 (YYYY-MM-DD, 없으면 null)
5. **categories**: 계층적 카테고리
   - level1: 대분류 (기술, 경영, 인사, 법무, 마케팅)
   - level2: 중분류 (예: 기술 > 인프라)
   - level3: 소분류 (예: 기술 > 인프라 > 클라우드)  // 없으면 null
6. **summary**: 핵심 요약 (2-3문장)

## 출력 형식 (JSON)
```json
{{
  "document_type": "기술문서",
  "project_name": "",
  "valid_start_date": null,
  "valid_end_date": null,
  "categories": {{
    "level1": "기술",
    "level2": "개발",
    "level3": null
  }},
  "summary": "문서 요약 내용"
}}
```

중요: 반드시 유효한 JSON 형식으로 응답하세요."""


# ---------------------------------------------------------------------------
# EntityExtractionService
# ---------------------------------------------------------------------------

class EntityExtractionService:
    """
    엔티티 추출 서비스

    LLM을 활용하여 문서에서 엔티티, 관계, 메타데이터를 추출합니다.
    Gleaning 기법을 통해 추출 품질을 향상시킵니다 (+33% Recall).

    Pipeline:
        1. 1차 엔티티 추출 (LLM)
        2. Gleaning: 누락 엔티티 보완 (LLM 재질문)
        3. 관계 추출 (LLM)
        4. 결과 통합 및 검증
    """

    def __init__(
        self,
        max_text_length: int = 30000,
        max_gleanings: Optional[int] = None,
        adaptive_gleaning: Optional[bool] = None,
    ):
        """
        초기화

        Args:
            max_text_length: 처리할 최대 텍스트 길이
            max_gleanings: Gleaning 최대 반복 횟수 (None이면 설정값 사용)
            adaptive_gleaning: Adaptive Gleaning 활성화 여부 (None이면 설정값 사용)
        """
        self.max_text_length = max_text_length
        self.max_gleanings = max_gleanings or settings.max_gleanings
        self.adaptive_gleaning = (
            adaptive_gleaning if adaptive_gleaning is not None
            else settings.adaptive_gleaning
        )
        self._llm_service = get_llm_service()

    def _determine_max_gleanings(self, text_length: int) -> int:
        """
        Adaptive Gleaning: 문서 길이 기반 동적 gleaning 횟수 결정

        짧은 문서는 적게, 긴 문서는 많이 gleaning하여 LLM 호출 비용을 최적화합니다.

        Args:
            text_length: 원본 텍스트 길이 (자)

        Returns:
            결정된 최대 gleaning 횟수
        """
        if not self.adaptive_gleaning:
            return self.max_gleanings

        short_threshold = settings.adaptive_gleaning_short_threshold
        long_threshold = settings.adaptive_gleaning_long_threshold

        if text_length < short_threshold:
            adaptive_max = 1
        elif text_length <= long_threshold:
            adaptive_max = 2
        else:
            adaptive_max = 3

        logger.info(
            f"Adaptive gleaning: text_length={text_length}, "
            f"determined max_gleanings={adaptive_max} "
            f"(thresholds: short<{short_threshold}, long>{long_threshold})"
        )

        return adaptive_max

    async def extract_entities(
        self,
        text: str,
        enable_gleaning: bool = True,
    ) -> List[Entity]:
        """
        텍스트에서 엔티티 추출

        Adaptive Gleaning이 활성화된 경우:
        - 문서 길이에 따라 gleaning 횟수를 동적으로 결정
          (짧은 텍스트 1회, 중간 2회, 긴 텍스트 3회)
        - 수확 체감 법칙: 이전 pass 대비 새 엔티티 비율이
          설정값(기본 10%) 미만이면 조기 종료

        Args:
            text: 추출 대상 텍스트
            enable_gleaning: Gleaning 활성화 여부

        Returns:
            추출된 Entity 리스트

        Raises:
            LLMError: LLM 호출 실패
        """
        start_time = time.monotonic()
        truncated_text = text[:self.max_text_length]

        # Adaptive Gleaning: 문서 길이 기반 동적 횟수 결정
        effective_max_gleanings = self._determine_max_gleanings(len(truncated_text))
        diminishing_rate = settings.adaptive_gleaning_diminishing_rate

        logger.info(
            f"Entity extraction - Text length: {len(text)}, "
            f"Truncated: {len(truncated_text)}, "
            f"Gleaning: {enable_gleaning}, "
            f"Adaptive: {self.adaptive_gleaning}, "
            f"Max gleanings: {effective_max_gleanings}"
        )

        # 1차 추출
        entities = await self._extract_entities_pass(truncated_text)
        logger.info(f"1st pass entities: {len(entities)}")

        # Gleaning: 누락 엔티티 추가 추출
        gleaning_count = 0
        if enable_gleaning and effective_max_gleanings > 0:
            for pass_num in range(effective_max_gleanings):
                entities_before = len(entities)

                gleaned = await self._gleaning_pass(
                    text=truncated_text,
                    existing_entities=entities,
                    pass_number=pass_num + 1,
                )

                if not gleaned:
                    logger.info(f"Gleaning pass {pass_num + 1}: No new entities found - stopping")
                    break

                entities.extend(gleaned)
                gleaning_count += 1

                # 수확 체감 법칙 (Diminishing Returns)
                new_ratio = len(gleaned) / entities_before if entities_before > 0 else 1.0
                logger.info(
                    f"Gleaning pass {pass_num + 1}: "
                    f"+{len(gleaned)} entities (total: {len(entities)}), "
                    f"new_ratio: {new_ratio:.2%}"
                )

                if self.adaptive_gleaning and new_ratio < diminishing_rate:
                    logger.info(
                        f"Gleaning early stop: new_ratio {new_ratio:.2%} "
                        f"< threshold {diminishing_rate:.0%} - diminishing returns"
                    )
                    break

        # 중복 제거
        entities = self._deduplicate_entities(entities)

        latency_ms = (time.monotonic() - start_time) * 1000
        logger.info(
            f"Entity extraction complete - "
            f"Total: {len(entities)}, "
            f"Gleaning passes: {gleaning_count}, "
            f"Adaptive: {self.adaptive_gleaning}, "
            f"Latency: {latency_ms:.1f}ms"
        )

        return entities

    async def extract_relationships(
        self,
        text: str,
        entities: List[Entity],
    ) -> List[Relationship]:
        """
        엔티티 간 관계 추출

        Args:
            text: 원본 텍스트
            entities: 추출된 엔티티 리스트

        Returns:
            추출된 Relationship 리스트

        Raises:
            LLMError: LLM 호출 실패
        """
        if not entities:
            logger.info("No entities provided - skipping relationship extraction")
            return []

        start_time = time.monotonic()
        truncated_text = text[:self.max_text_length]

        entities_json = json.dumps(
            [e.model_dump() for e in entities],
            ensure_ascii=False,
            indent=2,
        )

        prompt = RELATIONSHIP_EXTRACTION_PROMPT.format(
            text=truncated_text,
            entities_json=entities_json,
        )

        logger.info(
            f"Relationship extraction - Entities: {len(entities)}, "
            f"Text length: {len(truncated_text)}"
        )

        try:
            response = await self._llm_service.generate(prompt=prompt)
            relationships = self._parse_relationships(response, entities)

            latency_ms = (time.monotonic() - start_time) * 1000
            logger.info(
                f"Relationship extraction complete - "
                f"Total: {len(relationships)}, "
                f"Latency: {latency_ms:.1f}ms"
            )

            return relationships

        except LLMError:
            raise
        except Exception as e:
            logger.exception(f"Relationship extraction failed: {e}")
            raise LLMError(f"관계 추출 실패: {str(e)}")

    async def extract_full(
        self,
        text: str,
        enable_gleaning: bool = True,
    ) -> ExtractionResult:
        """
        엔티티 + 관계 + 메타데이터 통합 추출

        Args:
            text: 추출 대상 텍스트
            enable_gleaning: Gleaning 활성화 여부

        Returns:
            ExtractionResult 객체
        """
        logger.info(f"Full extraction - Text length: {len(text)}")

        # 엔티티 추출
        entities = await self.extract_entities(text, enable_gleaning=enable_gleaning)

        # 관계 추출
        relationships = await self.extract_relationships(text, entities)

        return ExtractionResult(
            entities=entities,
            relationships=relationships,
            metadata=None,
        )

    async def extract_metadata(
        self,
        text: str,
        filename: Optional[str] = None,
    ) -> DocumentMetadata:
        """
        문서 메타데이터 추출

        Args:
            text: 문서 텍스트
            filename: 원본 파일명 (힌트용)

        Returns:
            DocumentMetadata 객체

        Raises:
            LLMError: LLM 호출 실패
        """
        start_time = time.monotonic()

        # 메타데이터 추출에는 앞부분만 사용 (효율성)
        text_preview = text[:5000]

        prompt = METADATA_EXTRACTION_PROMPT.format(
            text=text_preview,
            filename=filename or "(파일명 없음)",
        )

        logger.info(
            f"Metadata extraction - Text length: {len(text)}, "
            f"Filename: {filename}"
        )

        try:
            response = await self._llm_service.generate(prompt=prompt)
            metadata = self._parse_metadata(response)

            latency_ms = (time.monotonic() - start_time) * 1000
            logger.info(
                f"Metadata extraction complete - "
                f"Type: {metadata.document_type}, "
                f"Latency: {latency_ms:.1f}ms"
            )

            return metadata

        except LLMError:
            raise
        except Exception as e:
            logger.exception(f"Metadata extraction failed: {e}")
            # 실패 시 기본값 반환
            return DocumentMetadata(
                document_type="unknown",
                project_name="",
                categories=CategoryMetadata(
                    level1="미분류", level2="미분류", level3=None,
                ),
                summary="메타데이터 추출에 실패했습니다.",
            )

    # ------------------------------------------------------------------
    # Internal methods
    # ------------------------------------------------------------------

    async def _extract_entities_pass(self, text: str) -> List[Entity]:
        """
        1차 엔티티 추출 패스

        Args:
            text: 추출 대상 텍스트

        Returns:
            추출된 Entity 리스트
        """
        prompt = ENTITY_EXTRACTION_PROMPT.format(text=text)

        try:
            response = await self._llm_service.generate(prompt=prompt)
            return self._parse_entities(response)

        except LLMError:
            raise
        except Exception as e:
            logger.exception(f"Entity extraction pass failed: {e}")
            return []

    async def _gleaning_pass(
        self,
        text: str,
        existing_entities: List[Entity],
        pass_number: int,
    ) -> List[Entity]:
        """
        Gleaning 패스: 누락된 엔티티 추가 추출

        이전에 추출한 엔티티를 보여주고 "누락된 엔티티가 있는지" 재질문합니다.

        Args:
            text: 원본 텍스트
            existing_entities: 이미 추출된 엔티티
            pass_number: Gleaning 패스 번호

        Returns:
            추가로 발견된 Entity 리스트
        """
        existing_json = json.dumps(
            [e.model_dump() for e in existing_entities],
            ensure_ascii=False,
            indent=2,
        )

        prompt = GLEANING_PROMPT.format(
            text=text,
            existing_entities_json=existing_json,
        )

        logger.info(f"Gleaning pass {pass_number} - Existing entities: {len(existing_entities)}")

        try:
            response = await self._llm_service.generate(prompt=prompt)
            gleaned_entities = self._parse_entities(response, id_prefix=f"gleaned_{pass_number}_")

            return gleaned_entities

        except Exception as e:
            logger.warning(f"Gleaning pass {pass_number} failed: {e}")
            return []

    def _parse_entities(
        self,
        response: str,
        id_prefix: str = "",
    ) -> List[Entity]:
        """
        LLM 응답에서 엔티티 파싱

        Args:
            response: LLM 응답 문자열
            id_prefix: ID 접두사 (Gleaning 구분용)

        Returns:
            파싱된 Entity 리스트
        """
        json_str = extract_json_from_text(response)
        if not json_str:
            logger.warning("Failed to extract JSON from entity extraction response")
            return []

        try:
            data = json.loads(json_str)
            entities_data = data.get("entities", [])

            entities: List[Entity] = []
            for item in entities_data:
                entity_id = item.get("id", "")
                if id_prefix and not entity_id.startswith(id_prefix):
                    entity_id = f"{id_prefix}{entity_id}"

                entity = Entity(
                    id=entity_id,
                    name=item.get("name", ""),
                    type=self._normalize_entity_type(item.get("type", "Concept")),
                    description=item.get("description"),
                )
                entities.append(entity)

            return entities

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error in entity extraction: {e}")
            return []

    def _parse_relationships(
        self,
        response: str,
        entities: List[Entity],
    ) -> List[Relationship]:
        """
        LLM 응답에서 관계 파싱

        Args:
            response: LLM 응답 문자열
            entities: 추출된 엔티티 리스트 (ID 검증용)

        Returns:
            파싱된 Relationship 리스트
        """
        json_str = extract_json_from_text(response)
        if not json_str:
            logger.warning("Failed to extract JSON from relationship extraction response")
            return []

        try:
            data = json.loads(json_str)
            rels_data = data.get("relationships", [])

            entity_ids = {e.id for e in entities}
            valid_types = {
                "CREATED", "PARTICIPATED", "USES", "BELONGS_TO",
                "RELATED_TO", "MANAGES", "DEPENDS_ON",
            }

            relationships: List[Relationship] = []
            for item in rels_data:
                source = item.get("source", "")
                target = item.get("target", "")
                rel_type = item.get("type", "RELATED_TO").upper()

                # 소스/타겟 엔티티 존재 여부 검증
                if source not in entity_ids or target not in entity_ids:
                    logger.debug(
                        f"Skipping relationship with unknown entity: "
                        f"{source} -> {target}"
                    )
                    continue

                # 관계 유형 검증
                if rel_type not in valid_types:
                    rel_type = "RELATED_TO"

                relationship = Relationship(
                    source=source,
                    target=target,
                    type=rel_type,
                    description=item.get("description"),
                )
                relationships.append(relationship)

            return relationships

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error in relationship extraction: {e}")
            return []

    def _parse_metadata(self, response: str) -> DocumentMetadata:
        """
        LLM 응답에서 메타데이터 파싱

        Args:
            response: LLM 응답 문자열

        Returns:
            DocumentMetadata 객체
        """
        json_str = extract_json_from_text(response)
        if not json_str:
            logger.warning("Failed to extract JSON from metadata extraction response")
            return DocumentMetadata(
                document_type="unknown",
                summary="메타데이터 파싱 실패",
            )

        try:
            data = json.loads(json_str)

            categories = None
            cat_data = data.get("categories")
            if cat_data:
                categories = CategoryMetadata(
                    level1=cat_data.get("level1", "미분류"),
                    level2=cat_data.get("level2", "미분류"),
                    level3=cat_data.get("level3"),
                )

            return DocumentMetadata(
                document_type=data.get("document_type", "unknown"),
                project_name=data.get("project_name", ""),
                valid_start_date=data.get("valid_start_date"),
                valid_end_date=data.get("valid_end_date"),
                categories=categories,
                summary=data.get("summary", ""),
            )

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error in metadata extraction: {e}")
            return DocumentMetadata(
                document_type="unknown",
                summary="메타데이터 JSON 파싱 실패",
            )

    def _deduplicate_entities(self, entities: List[Entity]) -> List[Entity]:
        """
        엔티티 중복 제거

        이름과 유형이 동일한 엔티티를 제거합니다.

        Args:
            entities: 엔티티 리스트

        Returns:
            중복 제거된 엔티티 리스트
        """
        seen: set = set()
        unique: List[Entity] = []

        for entity in entities:
            key = (entity.name.lower().strip(), entity.type.lower())
            if key not in seen:
                seen.add(key)
                unique.append(entity)

        if len(unique) < len(entities):
            logger.debug(
                f"Deduplicated entities: {len(entities)} -> {len(unique)} "
                f"({len(entities) - len(unique)} duplicates removed)"
            )

        return unique

    @staticmethod
    def _normalize_entity_type(entity_type: str) -> str:
        """
        엔티티 유형 정규화

        Args:
            entity_type: 원본 엔티티 유형

        Returns:
            정규화된 엔티티 유형
        """
        type_map = {
            "person": "Person",
            "people": "Person",
            "organization": "Organization",
            "org": "Organization",
            "company": "Organization",
            "technology": "Technology",
            "tech": "Technology",
            "tool": "Technology",
            "framework": "Technology",
            "language": "Technology",
            "project": "Project",
            "concept": "Concept",
            "method": "Concept",
            "methodology": "Concept",
            "date": "Date",
            "time": "Date",
            "period": "Date",
            "location": "Location",
            "place": "Location",
        }

        normalized = type_map.get(entity_type.lower().strip(), None)
        if normalized:
            return normalized

        # 알려지지 않은 유형은 Concept으로 매핑
        if entity_type not in {
            "Person", "Organization", "Technology",
            "Project", "Concept", "Date", "Location",
        }:
            return "Concept"

        return entity_type


# ---------------------------------------------------------------------------
# 싱글톤 인스턴스
# ---------------------------------------------------------------------------

_extraction_service: Optional[EntityExtractionService] = None


def get_entity_extraction_service() -> EntityExtractionService:
    """EntityExtractionService 인스턴스 반환 (싱글톤)"""
    global _extraction_service
    if _extraction_service is None:
        _extraction_service = EntityExtractionService()
    return _extraction_service
