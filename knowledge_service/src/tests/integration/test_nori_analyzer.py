"""
STORY-113: Nori 플러그인 자동 검증 통합 테스트

2026-02-13 Nori 미적용 사고(32일간 미발견)를 재발 방지하기 위한 자동 검증 테스트.
ES `_analyze` API로 nori_tokenizer 실동작을 검증한다.

배경:
    - ES Dockerfile 누락으로 Nori 플러그인 미설치 상태로 32일 운영
    - 코드리뷰 3건에서 미발견 (코드만 보고 실동작 미검증)
    - 이 테스트로 ES 기동 후 즉시 Nori 동작 여부를 자동 검증

인덱스 실제 구성 (2026-03-05 확인):
    - analyzer: `korean_analyzer` (nori_tokenizer + nori_part_of_speech 필터)
    - tokenizer: `nori_tokenizer` (decompound_mode=mixed, 사용자 사전 포함)
    - 적용 필드: text, heading, title, metadata.summary

테스트 범위:
    1. Nori 플러그인(analysis-nori)이 ES에 실제로 설치되어 있는지 확인
    2. `_analyze` API로 한국어 형태소 분석 결과 검증
    3. standard analyzer vs korean_analyzer(nori 기반) 결과 차이 확인
    4. `knowledge_chunks` 인덱스의 korean_analyzer 설정 확인
    5. E2E 종합 검증 (CI/CD 게이트)

실행 방법:
    TEST_MODE=docker pytest src/tests/integration/test_nori_analyzer.py -v

중요: Mock 모드 절대 금지! 반드시 TEST_MODE=docker 설정 후 실행
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest
import requests

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))


# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------

ES_HOST = os.getenv("ES_HOST", "http://localhost:9200")
INDEX_NAME = "knowledge_chunks"
# 실제 인덱스에서 사용하는 Nori 기반 커스텀 analyzer 이름
KOREAN_ANALYZER_NAME = "korean_analyzer"

# 한국어 형태소 분석 테스트 텍스트
TEST_TEXTS = {
    "basic": "한국어형태소분석",
    "sentence": "안녕하세요 저는 한국어 자연어처리를 공부하고 있습니다",
    "mixed": "RAG 시스템에서 한국어 형태소 분석기를 사용합니다",
    "compound": "지식관리시스템의검색성능향상",
}

# standard analyzer는 공백 기준 분리, Nori는 형태소 기준 분리
# "한국어형태소분석" → standard: 1 토큰, nori: 복수 토큰 (한국어, 형태소, 분석 등)
MIN_NORI_TOKENS_FOR_COMPOUND = 2  # 복합어에서 최소 2개 이상 분리되어야 함


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def es_base_url() -> str:
    """Elasticsearch 기본 URL"""
    return ES_HOST


@pytest.fixture(scope="module")
def es_available(es_base_url: str) -> bool:
    """ES 서버 가용성 확인"""
    try:
        resp = requests.get(es_base_url, timeout=5)
        return resp.status_code == 200
    except requests.exceptions.ConnectionError:
        return False


@pytest.fixture(scope="module")
def index_exists(es_base_url: str, es_available: bool) -> bool:
    """knowledge_chunks 인덱스 존재 여부"""
    if not es_available:
        return False
    try:
        resp = requests.head(f"{es_base_url}/{INDEX_NAME}", timeout=5)
        return resp.status_code == 200
    except requests.exceptions.ConnectionError:
        return False


# ---------------------------------------------------------------------------
# Skip Conditions
# ---------------------------------------------------------------------------


def require_es(es_available: bool):
    """ES 미가용 시 테스트 스킵"""
    if not es_available:
        pytest.skip(
            f"Elasticsearch not available at {ES_HOST}. "
            "Run with TEST_MODE=docker and ensure ES container is running."
        )


def require_index(index_exists: bool):
    """인덱스 미존재 시 테스트 스킵"""
    if not index_exists:
        pytest.skip(
            f"Index '{INDEX_NAME}' does not exist. "
            "Run ETL pipeline or create the index first."
        )


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def get_tokens(analysis_result: Dict[str, Any]) -> List[str]:
    """분석 결과에서 토큰 목록 추출"""
    return [token["token"] for token in analysis_result.get("tokens", [])]


# ---------------------------------------------------------------------------
# Test Class: Nori Plugin Installation
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.nori
class TestNoriPluginInstallation:
    """Nori 플러그인 설치 여부 검증"""

    def test_es_is_reachable(self, es_base_url: str, es_available: bool):
        """ES 서버가 응답하는지 확인"""
        require_es(es_available)

        resp = requests.get(es_base_url, timeout=5)
        assert resp.status_code == 200, f"ES 서버 응답 실패: {resp.status_code}"

        data = resp.json()
        assert "version" in data, "ES 버전 정보 없음"
        version = data.get("version", {}).get("number", "unknown")
        print(f"\nES 버전: {version}")

    def test_nori_plugin_installed(self, es_base_url: str, es_available: bool):
        """
        Nori 플러그인이 ES에 설치되어 있는지 확인.

        실패 시: ES Dockerfile에 analysis-nori 플러그인 설치 필요
        참고: CLAUDE.md - "2026-02-13 Nori 미적용 사고"
        """
        require_es(es_available)

        resp = requests.get(f"{es_base_url}/_cat/plugins?format=json", timeout=5)
        assert resp.status_code == 200, f"플러그인 조회 실패: {resp.status_code}"

        plugins = resp.json()
        plugin_names = [p.get("component", "") for p in plugins]

        assert "analysis-nori" in plugin_names, (
            f"Nori 플러그인(analysis-nori)이 설치되지 않았습니다!\n"
            f"설치된 플러그인: {plugin_names}\n"
            f"해결 방법: ES Dockerfile에 "
            f"'elasticsearch-plugin install analysis-nori' 추가 후 리빌드"
        )
        print(f"\n[PASS] analysis-nori 플러그인 설치 확인. 전체 플러그인: {plugin_names}")

    def test_nori_tokenizer_works_globally(self, es_base_url: str, es_available: bool):
        """
        Nori tokenizer를 글로벌 레벨에서 직접 사용 가능한지 확인.
        인덱스 없이도 동작해야 함.
        """
        require_es(es_available)

        url = f"{es_base_url}/_analyze"
        payload = {
            "tokenizer": "nori_tokenizer",
            "text": TEST_TEXTS["basic"],
        }

        resp = requests.post(url, json=payload, timeout=10)

        assert resp.status_code == 200, (
            f"nori_tokenizer 글로벌 사용 실패 (HTTP {resp.status_code}):\n{resp.text}\n"
            f"원인: Nori 플러그인이 설치되지 않았거나 ES가 재시작되지 않음"
        )

        tokens = get_tokens(resp.json())
        assert len(tokens) >= 1, "nori_tokenizer가 토큰을 생성하지 못함"
        print(f"\n글로벌 nori_tokenizer 분석 결과: {tokens}")


# ---------------------------------------------------------------------------
# Test Class: Korean Morphological Analysis
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.nori
class TestKoreanMorphologicalAnalysis:
    """한국어 형태소 분석 결과 검증"""

    def test_nori_splits_compound_word(self, es_base_url: str, es_available: bool):
        """
        복합어를 형태소 단위로 분리하는지 확인.
        "한국어형태소분석" → 복수 토큰 분리 (한국어, 형태소, 분석 등)

        이것이 실패하면 Nori가 설치되지 않았거나 standard analyzer로 동작 중.
        """
        require_es(es_available)

        url = f"{es_base_url}/_analyze"
        payload = {
            "tokenizer": "nori_tokenizer",
            "text": TEST_TEXTS["basic"],  # "한국어형태소분석"
        }
        resp = requests.post(url, json=payload, timeout=10)
        assert resp.status_code == 200

        tokens = get_tokens(resp.json())
        print(f"\n복합어 분석 결과: '{TEST_TEXTS['basic']}' → {tokens}")

        assert len(tokens) >= MIN_NORI_TOKENS_FOR_COMPOUND, (
            f"Nori tokenizer가 복합어를 분리하지 못했습니다!\n"
            f"입력: '{TEST_TEXTS['basic']}'\n"
            f"출력 토큰: {tokens} (개수: {len(tokens)})\n"
            f"기대: 최소 {MIN_NORI_TOKENS_FOR_COMPOUND}개 이상 분리\n"
            f"원인: Nori 플러그인이 실제로 동작하지 않음"
        )

    def test_nori_vs_standard_differ_on_korean(
        self, es_base_url: str, es_available: bool
    ):
        """
        Standard analyzer vs Nori tokenizer 결과 비교.
        한국어 복합어에서 두 결과는 반드시 달라야 함.

        - standard: 공백 기준 단순 분리 → 복합어 = 1 토큰
        - nori: 형태소 기준 분리 → 복합어 = 복수 토큰
        """
        require_es(es_available)

        url = f"{es_base_url}/_analyze"
        text = TEST_TEXTS["basic"]  # "한국어형태소분석" (공백 없는 복합어)

        # Standard analyzer 분석
        std_resp = requests.post(
            url, json={"analyzer": "standard", "text": text}, timeout=10
        )
        assert std_resp.status_code == 200
        std_tokens = get_tokens(std_resp.json())

        # Nori tokenizer 분석
        nori_resp = requests.post(
            url, json={"tokenizer": "nori_tokenizer", "text": text}, timeout=10
        )
        assert nori_resp.status_code == 200
        nori_tokens = get_tokens(nori_resp.json())

        print(f"\nStandard 분석: {std_tokens}")
        print(f"Nori 분석:     {nori_tokens}")

        # standard는 공백 없는 한국어를 1개 토큰으로 처리
        assert len(std_tokens) <= 1, (
            f"Standard analyzer가 예상과 다름: {std_tokens}"
        )

        # Nori는 복합어를 복수 토큰으로 분리해야 함
        assert len(nori_tokens) > len(std_tokens), (
            f"Nori가 Standard보다 더 세밀히 분석해야 합니다!\n"
            f"Standard 토큰: {std_tokens}\n"
            f"Nori 토큰: {nori_tokens}\n"
            f"Nori가 제대로 동작하지 않고 있음"
        )

    def test_nori_handles_sentence(self, es_base_url: str, es_available: bool):
        """한국어 문장을 의미 있는 형태소로 분석하는지 확인"""
        require_es(es_available)

        url = f"{es_base_url}/_analyze"
        text = TEST_TEXTS["sentence"]

        resp = requests.post(
            url,
            json={"tokenizer": "nori_tokenizer", "text": text},
            timeout=10,
        )
        assert resp.status_code == 200

        tokens = get_tokens(resp.json())
        print(f"\n문장 분석 결과: '{text}'\n→ {tokens}")

        # 최소한 의미 있는 키워드들이 추출되어야 함
        assert len(tokens) >= 3, (
            f"문장 형태소 분석 결과가 너무 적습니다: {tokens}"
        )

        # "공부" 또는 "자연어" 등의 의미 단위가 포함되어야 함
        token_set = set(tokens)
        expected_keywords = {"공부", "자연어", "한국어", "처리"}
        found = token_set.intersection(expected_keywords)

        assert len(found) >= 1, (
            f"의미 있는 한국어 키워드가 추출되지 않았습니다.\n"
            f"분석 결과: {tokens}\n"
            f"기대 키워드 중 최소 1개 포함 필요: {expected_keywords}"
        )

    def test_nori_handles_mixed_text(self, es_base_url: str, es_available: bool):
        """영문 + 한국어 혼합 텍스트 처리 확인"""
        require_es(es_available)

        url = f"{es_base_url}/_analyze"
        text = TEST_TEXTS["mixed"]  # "RAG 시스템에서 한국어 형태소 분석기를 사용합니다"

        resp = requests.post(
            url,
            json={"tokenizer": "nori_tokenizer", "text": text},
            timeout=10,
        )
        assert resp.status_code == 200

        tokens = get_tokens(resp.json())
        print(f"\n혼합 텍스트 분석: '{text}'\n→ {tokens}")

        token_set = set(tokens)

        # 영문 "rag"(소문자 변환) 또는 "RAG"가 포함되어야 함
        has_rag = "rag" in token_set or "RAG" in token_set
        assert has_rag, f"영문 'RAG' 토큰이 없음: {tokens}"

        # 한국어 형태소가 포함되어야 함
        assert len(tokens) >= 3, f"혼합 텍스트 분석 결과가 너무 적습니다: {tokens}"


# ---------------------------------------------------------------------------
# Test Class: knowledge_chunks Index Nori Configuration
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.nori
class TestKnowledgeChunksIndexNoriConfig:
    """knowledge_chunks 인덱스의 korean_analyzer(Nori 기반) 설정 검증"""

    def test_index_exists(self, es_base_url: str, es_available: bool):
        """knowledge_chunks 인덱스가 존재하는지 확인"""
        require_es(es_available)

        resp = requests.head(f"{es_base_url}/{INDEX_NAME}", timeout=5)
        assert resp.status_code == 200, (
            f"인덱스 '{INDEX_NAME}'가 존재하지 않습니다.\n"
            f"ETL 파이프라인을 실행하거나 인덱스를 생성하세요."
        )

    def test_index_settings_contain_nori(
        self, es_base_url: str, es_available: bool, index_exists: bool
    ):
        """
        knowledge_chunks 인덱스 settings에 nori 관련 설정이 있는지 확인.
        nori_tokenizer, nori_part_of_speech 필터가 정의되어 있어야 함.
        """
        require_es(es_available)
        require_index(index_exists)

        resp = requests.get(
            f"{es_base_url}/{INDEX_NAME}/_settings", timeout=10
        )
        assert resp.status_code == 200, f"인덱스 설정 조회 실패: {resp.status_code}"

        settings_data = resp.json()
        settings_str = str(settings_data).lower()

        assert "nori" in settings_str, (
            f"인덱스 '{INDEX_NAME}' 설정에 nori 관련 설정이 없습니다!\n"
            f"현재 설정: {settings_data}\n"
            f"해결 방법: 인덱스 settings에 nori_tokenizer/nori_part_of_speech 추가 후 재생성"
        )
        print(f"\n[PASS] 인덱스 settings에 nori 설정 확인")

    def test_index_settings_has_korean_analyzer(
        self, es_base_url: str, es_available: bool, index_exists: bool
    ):
        """
        korean_analyzer가 인덱스 settings에 정의되어 있는지 확인.
        이 analyzer가 nori_tokenizer를 사용해야 함.
        """
        require_es(es_available)
        require_index(index_exists)

        resp = requests.get(
            f"{es_base_url}/{INDEX_NAME}/_settings", timeout=10
        )
        assert resp.status_code == 200

        settings_data = resp.json()
        # 중첩된 설정에서 korean_analyzer 찾기
        settings_str = str(settings_data)

        assert "korean_analyzer" in settings_str, (
            f"인덱스 settings에 'korean_analyzer'가 정의되지 않았습니다!\n"
            f"현재 analyzer 설정을 확인하세요."
        )

        # korean_analyzer가 nori_tokenizer를 사용하는지 확인
        assert "nori_tokenizer" in settings_str, (
            f"인덱스 settings에 'nori_tokenizer'가 정의되지 않았습니다!\n"
            f"korean_analyzer의 tokenizer 설정을 확인하세요."
        )
        print(f"\n[PASS] korean_analyzer와 nori_tokenizer 설정 확인")

    def test_index_analyze_with_korean_analyzer(
        self, es_base_url: str, es_available: bool, index_exists: bool
    ):
        """
        knowledge_chunks 인덱스에서 korean_analyzer로 분석 가능한지 확인.
        korean_analyzer = nori_tokenizer + nori_part_of_speech 필터.
        """
        require_es(es_available)
        require_index(index_exists)

        text = TEST_TEXTS["basic"]

        resp = requests.post(
            f"{es_base_url}/{INDEX_NAME}/_analyze",
            json={"analyzer": KOREAN_ANALYZER_NAME, "text": text},
            timeout=10,
        )

        assert resp.status_code == 200, (
            f"인덱스 '{INDEX_NAME}'에서 '{KOREAN_ANALYZER_NAME}' 사용 실패!\n"
            f"HTTP {resp.status_code}: {resp.text}\n"
            f"원인: 인덱스에 '{KOREAN_ANALYZER_NAME}' analyzer가 정의되지 않음\n"
            f"해결: 인덱스 settings에 korean_analyzer 추가 필요"
        )

        tokens = get_tokens(resp.json())
        print(
            f"\n인덱스 korean_analyzer 분석 결과: '{text}' → {tokens}"
        )

        assert len(tokens) >= MIN_NORI_TOKENS_FOR_COMPOUND, (
            f"인덱스의 korean_analyzer가 복합어를 분리하지 못했습니다.\n"
            f"입력: '{text}'\n"
            f"출력: {tokens}\n"
            f"기대: 최소 {MIN_NORI_TOKENS_FOR_COMPOUND}개 이상"
        )

    def test_index_analyze_compound_decompound(
        self, es_base_url: str, es_available: bool, index_exists: bool
    ):
        """
        인덱스의 korean_analyzer가 복합어를 분해하는지 확인.
        decompound_mode=mixed 설정으로 복합어+원형 모두 인덱싱.
        """
        require_es(es_available)
        require_index(index_exists)

        text = TEST_TEXTS["compound"]

        resp = requests.post(
            f"{es_base_url}/{INDEX_NAME}/_analyze",
            json={"analyzer": KOREAN_ANALYZER_NAME, "text": text},
            timeout=10,
        )
        assert resp.status_code == 200, (
            f"korean_analyzer를 인덱스에서 사용할 수 없음: {resp.text}"
        )

        tokens = get_tokens(resp.json())
        print(f"\n복합어 decompound 분석: '{text}' → {tokens}")

        assert len(tokens) >= 3, (
            f"복합어 분해가 충분하지 않습니다.\n"
            f"입력: '{text}'\n"
            f"출력: {tokens}\n"
            f"기대: 최소 3개 이상 분리 (지식/관리/시스템/검색/성능/향상 등)"
        )

    def test_index_mappings_use_korean_analyzer(
        self, es_base_url: str, es_available: bool, index_exists: bool
    ):
        """
        knowledge_chunks 인덱스 매핑에서 text/heading/title 필드가
        korean_analyzer를 사용하는지 확인.
        핵심 검색 필드가 nori 기반 analyzer를 사용하지 않으면 한국어 검색 품질이 저하됨.
        """
        require_es(es_available)
        require_index(index_exists)

        resp = requests.get(
            f"{es_base_url}/{INDEX_NAME}/_mapping", timeout=10
        )
        assert resp.status_code == 200

        mapping_data = resp.json()
        mapping_str = str(mapping_data)

        # korean_analyzer가 매핑에 정의되어 있어야 함
        assert "korean_analyzer" in mapping_str, (
            f"인덱스 '{INDEX_NAME}' 매핑에 'korean_analyzer'가 없습니다!\n"
            f"text/heading/title 필드가 korean_analyzer를 사용해야 합니다."
        )

        print(f"\n[PASS] 매핑에 korean_analyzer 적용 확인")

        # text 필드가 korean_analyzer를 사용하는지 확인
        # 실제 매핑: 'text': {'type': 'text', 'analyzer': 'korean_analyzer'}
        # mapping_data에서 text 필드 analyzer 직접 확인
        found_index = None
        for idx_name, idx_data in mapping_data.items():
            props = idx_data.get("mappings", {}).get("properties", {})
            text_field = props.get("text", {})
            if text_field.get("analyzer") == "korean_analyzer":
                found_index = idx_name
                break

        assert found_index is not None, (
            f"text 필드가 korean_analyzer를 사용하지 않습니다.\n"
            f"매핑: {mapping_data}"
        )
        print(f"[PASS] text 필드가 korean_analyzer 사용 확인 (인덱스: {found_index})")


# ---------------------------------------------------------------------------
# Test Class: End-to-End Nori Verification (Integration Summary)
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.nori
class TestNoriEndToEndVerification:
    """Nori 플러그인 E2E 종합 검증 (CI/CD 게이트)"""

    def test_nori_e2e_verification(self, es_base_url: str, es_available: bool):
        """
        Nori 전체 파이프라인 검증.
        이 테스트 하나로 Nori 정상 동작 여부를 빠르게 확인 가능.

        CI/CD 파이프라인에서 ES 기동 후 이 테스트로 Nori 동작을 자동 검증.
        실패 시 32일 사고와 같은 사태 재발 방지.
        """
        require_es(es_available)

        failures = []

        # 1. Nori 플러그인 설치 확인
        try:
            plugins_resp = requests.get(
                f"{es_base_url}/_cat/plugins?format=json", timeout=5
            )
            if plugins_resp.status_code == 200:
                plugins = [p.get("component", "") for p in plugins_resp.json()]
                if "analysis-nori" not in plugins:
                    failures.append(
                        f"[FAIL] analysis-nori 플러그인 미설치. 설치된 플러그인: {plugins}"
                    )
                else:
                    print(f"\n[PASS] analysis-nori 플러그인 설치 확인")
        except Exception as e:
            failures.append(f"[ERROR] 플러그인 조회 실패: {e}")

        # 2. nori_tokenizer 직접 동작 확인
        try:
            analyze_resp = requests.post(
                f"{es_base_url}/_analyze",
                json={"tokenizer": "nori_tokenizer", "text": TEST_TEXTS["basic"]},
                timeout=10,
            )
            if analyze_resp.status_code != 200:
                failures.append(
                    f"[FAIL] nori_tokenizer 동작 실패 (HTTP {analyze_resp.status_code})"
                )
            else:
                tokens = get_tokens(analyze_resp.json())
                if len(tokens) < MIN_NORI_TOKENS_FOR_COMPOUND:
                    failures.append(
                        f"[FAIL] nori_tokenizer 복합어 분리 실패: {tokens}"
                    )
                else:
                    print(f"[PASS] nori_tokenizer 복합어 분리 확인: {tokens}")
        except Exception as e:
            failures.append(f"[ERROR] nori_tokenizer 분석 실패: {e}")

        # 3. Standard vs Nori 차이 확인
        try:
            std_resp = requests.post(
                f"{es_base_url}/_analyze",
                json={"analyzer": "standard", "text": TEST_TEXTS["basic"]},
                timeout=10,
            )
            nori_resp = requests.post(
                f"{es_base_url}/_analyze",
                json={"tokenizer": "nori_tokenizer", "text": TEST_TEXTS["basic"]},
                timeout=10,
            )
            if std_resp.status_code == 200 and nori_resp.status_code == 200:
                std_tokens = get_tokens(std_resp.json())
                nori_tokens = get_tokens(nori_resp.json())
                if len(nori_tokens) <= len(std_tokens):
                    failures.append(
                        f"[FAIL] Nori({nori_tokens})가 Standard({std_tokens})보다 세밀하지 않음"
                    )
                else:
                    print(
                        f"[PASS] Standard({std_tokens}) vs Nori({nori_tokens}) 차이 확인"
                    )
        except Exception as e:
            failures.append(f"[ERROR] Standard vs Nori 비교 실패: {e}")

        # 최종 결과
        if failures:
            failure_report = "\n".join(failures)
            pytest.fail(
                f"Nori E2E 검증 실패!\n\n"
                f"{failure_report}\n\n"
                f"[재발 방지] 이 테스트는 2026-02-13 Nori 32일 미적용 사고 재발 방지용입니다.\n"
                f"ES Dockerfile에 analysis-nori 플러그인 설치 후 컨테이너를 리빌드하세요."
            )
        else:
            print(
                f"\n[SUCCESS] Nori 플러그인 E2E 검증 완료 - 모든 항목 정상"
            )
