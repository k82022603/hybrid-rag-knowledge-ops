# 사내 지식 검색 시스템 테스트 계획서
## Test Plan for Knowledge Discovery Platform

---

## 문서 정보

| 항목 | 내용 |
|------|------|
| **문서명** | 사내 지식 검색 시스템 테스트 계획서 |
| **버전** | 1.0 |
| **작성일** | 2026-01-14 |
| **작성자** | Claude Code (Opus 4.5) |
| **상태** | 초안 |
| **참조 문서** | [요구사항 명세서](./requirements_specification.md), [백엔드 구현 계획서](./backend_implementation_plan.md) |

---

## 변경 이력

| 버전 | 일자 | 작성자 | 변경 내용 |
|------|------|--------|----------|
| 1.0 | 2026-01-14 | Claude Code | 초안 작성 |

---

## 목차

1. [테스트 전략 개요](#1-테스트-전략-개요)
2. [테스트 범위](#2-테스트-범위)
3. [테스트 유형별 상세](#3-테스트-유형별-상세)
4. [테스트 환경](#4-테스트-환경)
5. [테스트 도구](#5-테스트-도구)
6. [테스트 데이터 관리](#6-테스트-데이터-관리)
7. [테스트 커버리지 목표](#7-테스트-커버리지-목표)
8. [CI/CD 통합](#8-cicd-통합)
9. [결함 관리](#9-결함-관리)
10. [테스트 단계](#10-테스트-단계)

---

## 1. 테스트 전략 개요

### 1.1 테스트 목적

본 테스트 계획서는 사내 지식 검색 시스템의 품질 보증을 위한 테스트 전략을 정의합니다.

| 목적 | 설명 |
|------|------|
| **기능 검증** | 요구사항 명세서의 74개 요구사항 충족 확인 |
| **품질 보증** | 시스템 안정성, 성능, 보안 검증 |
| **회귀 방지** | 자동화 테스트로 변경 시 기존 기능 보호 |
| **조기 결함 발견** | Shift-Left 테스팅으로 초기 결함 식별 |

### 1.2 테스트 원칙

```
┌─────────────────────────────────────────────────────────────────┐
│                      테스트 피라미드                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                          ▲                                      │
│                         /E\         E2E Tests (10%)             │
│                        /2E \        - Playwright                │
│                       /-----\       - 핵심 사용자 시나리오        │
│                      /       \                                  │
│                     / Integr- \     Integration Tests (20%)     │
│                    /   ation   \    - Testcontainers            │
│                   /-------------\   - API 통합 테스트            │
│                  /               \                              │
│                 /   Unit Tests    \ Unit Tests (70%)            │
│                /___________________\- JUnit5, pytest            │
│                                     - 비즈니스 로직 검증          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 테스트 접근 방식

| 접근 방식 | 적용 영역 |
|----------|----------|
| **TDD (Test-Driven Development)** | 핵심 비즈니스 로직, AI 파이프라인 |
| **BDD (Behavior-Driven Development)** | E2E 테스트, 사용자 시나리오 |
| **Risk-Based Testing** | 보안 관련 기능, 데이터 무결성 |
| **Exploratory Testing** | UI/UX, 에지 케이스 발견 |

---

## 2. 테스트 범위

### 2.1 테스트 대상 시스템

#### 2.1.1 백엔드 서비스

| 서비스 | 테스트 범위 | 우선순위 |
|--------|------------|----------|
| **Gateway Service** | 라우팅, 인증, Rate Limiting | 높음 |
| **Knowledge Service** | CRUD, 버전 관리, 파일 처리 | 높음 |
| **Search Service** | 쿼리 처리, 결과 집계 | 높음 |
| **AI Service** | VIP 파이프라인, Hybrid 검색 | 높음 |
| **User Service** | OAuth, 프로필 관리 | 중간 |
| **Export Service** | PDF/Excel/PPT 변환 | 중간 |
| **Dashboard Service** | 통계 API | 낮음 |

#### 2.1.2 프론트엔드

| 영역 | 테스트 범위 | 우선순위 |
|------|------------|----------|
| **지식 관리** | 등록, 수정, 삭제, 조회 | 높음 |
| **검색** | 채팅 모드, 검색 모드 | 높음 |
| **인증** | OAuth 로그인/로그아웃 | 높음 |
| **대시보드** | 위젯, 통계 표시 | 중간 |
| **개인화** | 프로필, 북마크, 설정 | 중간 |
| **문서 변환** | Export 기능 | 낮음 |

### 2.2 테스트 제외 범위

| 제외 항목 | 사유 |
|----------|------|
| 외부 SSO 시스템 내부 | 외부 시스템 (Keycloak/Okta) |
| LLM 모델 품질 | DeepSeek 모델 자체 품질 |
| 브라우저 렌더링 엔진 | 브라우저 벤더 책임 |
| 인프라 HA | Phase 2 범위 |

### 2.3 요구사항-테스트 매핑

| 요구사항 ID | 테스트 유형 | 테스트 케이스 수 (예상) |
|-------------|------------|----------------------|
| FR-KM-001 ~ 005 | Unit, Integration, E2E | 45 |
| FR-DB-001 | Integration, E2E | 15 |
| FR-PER-001 ~ 003 | Unit, Integration, E2E | 25 |
| FR-SR-001 ~ 003 | Unit, Integration, E2E, Performance | 40 |
| FR-EX-001 ~ 003 | Unit, Integration | 20 |
| FR-AUTH-001 ~ 002 | Unit, Integration, Security | 30 |
| NFR-PERF-001 ~ 002 | Performance, Load | 15 |
| NFR-SEC-001 ~ 002 | Security, Penetration | 20 |
| **총계** | | **~210** |

---

## 3. 테스트 유형별 상세

### 3.1 단위 테스트 (Unit Tests)

#### 3.1.1 목적
- 개별 컴포넌트의 기능 검증
- 비즈니스 로직 정확성 확인
- 빠른 피드백 제공

#### 3.1.2 백엔드 단위 테스트 (Java/Spring)

**테스트 대상:**
```
├── Service Layer (80% 이상)
├── Repository Layer (Query 메서드)
├── DTO Validation
├── Utility Classes
└── Exception Handlers
```

**예시 테스트 케이스:**

```java
// KnowledgeServiceTest.java
@ExtendWith(MockitoExtension.class)
class KnowledgeServiceTest {

    @Mock
    private KnowledgeRepository knowledgeRepository;

    @Mock
    private ElasticsearchClient esClient;

    @InjectMocks
    private KnowledgeServiceImpl knowledgeService;

    @Test
    @DisplayName("지식 생성 - 정상 케이스")
    void createKnowledge_Success() {
        // Given
        KnowledgeCreateRequest request = KnowledgeCreateRequest.builder()
            .title("테스트 지식")
            .content("테스트 내용")
            .categoryId(UUID.randomUUID())
            .build();

        Knowledge savedKnowledge = Knowledge.builder()
            .id(UUID.randomUUID())
            .title(request.getTitle())
            .build();

        when(knowledgeRepository.save(any(Knowledge.class)))
            .thenReturn(savedKnowledge);

        // When
        KnowledgeResponse response = knowledgeService.create(request);

        // Then
        assertThat(response).isNotNull();
        assertThat(response.getTitle()).isEqualTo("테스트 지식");
        verify(knowledgeRepository, times(1)).save(any());
    }

    @Test
    @DisplayName("지식 생성 - 제목 누락 시 예외")
    void createKnowledge_EmptyTitle_ThrowsException() {
        // Given
        KnowledgeCreateRequest request = KnowledgeCreateRequest.builder()
            .title("")
            .content("내용")
            .build();

        // When & Then
        assertThrows(ValidationException.class,
            () -> knowledgeService.create(request));
    }

    @Test
    @DisplayName("지식 조회 - 존재하지 않는 ID")
    void getKnowledge_NotFound_ThrowsException() {
        // Given
        UUID nonExistentId = UUID.randomUUID();
        when(knowledgeRepository.findById(nonExistentId))
            .thenReturn(Optional.empty());

        // When & Then
        assertThrows(KnowledgeNotFoundException.class,
            () -> knowledgeService.getById(nonExistentId));
    }
}
```

#### 3.1.3 AI 서비스 단위 테스트 (Python)

**테스트 대상:**
```
├── VIP Pipeline Components
│   ├── Value Stage (Entity Extraction)
│   ├── Intelligent Stage (Query Orchestration)
│   └── Planning Stage (Answer Synthesis)
├── Embedding Service
├── Search Fusion (RRF)
└── Prompt Templates
```

**예시 테스트 케이스:**

```python
# tests/unit/test_entity_extraction.py
import pytest
from unittest.mock import Mock, patch
from app.services.entity_extraction import EntityExtractor

class TestEntityExtractor:

    @pytest.fixture
    def extractor(self):
        return EntityExtractor(model="deepseek-chat")

    def test_extract_entities_success(self, extractor):
        """엔티티 추출 - 정상 케이스"""
        # Given
        document_text = """
        프로젝트명: ACME 시스템 구축
        담당자: 홍길동
        기간: 2025-01-01 ~ 2025-12-31
        """

        # When
        with patch.object(extractor, '_call_llm') as mock_llm:
            mock_llm.return_value = {
                "project_name": "ACME 시스템 구축",
                "persons": ["홍길동"],
                "date_range": {
                    "start": "2025-01-01",
                    "end": "2025-12-31"
                }
            }
            result = extractor.extract(document_text)

        # Then
        assert result is not None
        assert result["project_name"] == "ACME 시스템 구축"
        assert "홍길동" in result["persons"]

    def test_extract_entities_empty_input(self, extractor):
        """엔티티 추출 - 빈 입력"""
        with pytest.raises(ValueError, match="document_text cannot be empty"):
            extractor.extract("")

    def test_extract_entities_llm_timeout(self, extractor):
        """엔티티 추출 - LLM 타임아웃"""
        with patch.object(extractor, '_call_llm') as mock_llm:
            mock_llm.side_effect = TimeoutError("LLM timeout")

            result = extractor.extract("테스트 문서")

            assert result is None  # 실패 시 None 반환
```

```python
# tests/unit/test_hybrid_search.py
import pytest
from app.services.hybrid_search import HybridSearchService

class TestHybridSearch:

    @pytest.fixture
    def search_service(self):
        return HybridSearchService(
            es_client=Mock(),
            neo4j_driver=Mock()
        )

    def test_rrf_fusion_ranking(self, search_service):
        """RRF 퓨전 - 랭킹 계산"""
        # Given
        vector_results = [
            {"id": "doc1", "score": 0.95},
            {"id": "doc2", "score": 0.85},
            {"id": "doc3", "score": 0.75}
        ]
        graph_results = [
            {"id": "doc2", "score": 0.90},
            {"id": "doc1", "score": 0.80},
            {"id": "doc4", "score": 0.70}
        ]

        # When
        fused = search_service._rrf_fusion(
            vector_results,
            graph_results,
            k=60
        )

        # Then
        assert fused[0]["id"] in ["doc1", "doc2"]  # 상위권 유지
        assert len(fused) == 4  # 모든 고유 문서 포함

    def test_search_with_temporal_filter(self, search_service):
        """시간 기반 필터 검색"""
        # Given
        query = "2025년 프로젝트 현황"
        filters = {
            "valid_date_range": {
                "start": "2025-01-01",
                "end": "2025-12-31"
            }
        }

        # When
        with patch.object(search_service, '_vector_search') as mock_vs:
            mock_vs.return_value = [{"id": "doc1"}]
            results = search_service.search(query, filters=filters)

        # Then
        mock_vs.assert_called_once()
        call_args = mock_vs.call_args
        assert "valid_date_range" in str(call_args)
```

#### 3.1.4 프론트엔드 단위 테스트 (React)

**테스트 대상:**
```
├── Custom Hooks
├── Utility Functions
├── Redux Reducers/Actions
├── React Components (렌더링)
└── Form Validation
```

**예시 테스트 케이스:**

```typescript
// __tests__/hooks/useSearch.test.ts
import { renderHook, act } from '@testing-library/react';
import { useSearch } from '@/hooks/useSearch';

describe('useSearch Hook', () => {
  it('검색어 입력 시 상태 업데이트', () => {
    const { result } = renderHook(() => useSearch());

    act(() => {
      result.current.setQuery('테스트 검색어');
    });

    expect(result.current.query).toBe('테스트 검색어');
  });

  it('검색 실행 시 로딩 상태 변경', async () => {
    const { result } = renderHook(() => useSearch());

    act(() => {
      result.current.executeSearch('테스트');
    });

    expect(result.current.isLoading).toBe(true);
  });

  it('빈 검색어로 검색 시 에러', () => {
    const { result } = renderHook(() => useSearch());

    act(() => {
      result.current.executeSearch('');
    });

    expect(result.current.error).toBe('검색어를 입력해주세요');
  });
});
```

```typescript
// __tests__/components/KnowledgeCard.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { KnowledgeCard } from '@/components/KnowledgeCard';

describe('KnowledgeCard Component', () => {
  const mockKnowledge = {
    id: '1',
    title: '테스트 지식',
    summary: '테스트 요약',
    author: '홍길동',
    createdAt: '2026-01-14',
    viewCount: 100,
    likeCount: 10
  };

  it('지식 정보 렌더링', () => {
    render(<KnowledgeCard knowledge={mockKnowledge} />);

    expect(screen.getByText('테스트 지식')).toBeInTheDocument();
    expect(screen.getByText('홍길동')).toBeInTheDocument();
    expect(screen.getByText('100')).toBeInTheDocument();
  });

  it('클릭 시 상세 페이지 이동', () => {
    const onClickMock = jest.fn();
    render(<KnowledgeCard knowledge={mockKnowledge} onClick={onClickMock} />);

    fireEvent.click(screen.getByRole('article'));

    expect(onClickMock).toHaveBeenCalledWith('1');
  });

  it('북마크 버튼 클릭', () => {
    const onBookmarkMock = jest.fn();
    render(
      <KnowledgeCard
        knowledge={mockKnowledge}
        onBookmark={onBookmarkMock}
      />
    );

    fireEvent.click(screen.getByLabelText('북마크'));

    expect(onBookmarkMock).toHaveBeenCalledWith('1');
  });
});
```

### 3.2 통합 테스트 (Integration Tests)

#### 3.2.1 목적
- 컴포넌트 간 상호작용 검증
- 데이터베이스 연동 테스트
- 외부 서비스 연동 테스트

#### 3.2.2 백엔드 통합 테스트

**테스트 환경: Testcontainers**

```java
// KnowledgeIntegrationTest.java
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@Testcontainers
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
class KnowledgeIntegrationTest {

    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16-alpine")
        .withDatabaseName("testdb")
        .withUsername("test")
        .withPassword("test");

    @Container
    static ElasticsearchContainer elasticsearch = new ElasticsearchContainer(
        "docker.elastic.co/elasticsearch/elasticsearch:8.11.0"
    ).withEnv("xpack.security.enabled", "false");

    @Container
    static Neo4jContainer<?> neo4j = new Neo4jContainer<>("neo4j:5.15-community")
        .withoutAuthentication();

    @DynamicPropertySource
    static void configureProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
        registry.add("spring.datasource.username", postgres::getUsername);
        registry.add("spring.datasource.password", postgres::getPassword);
        registry.add("spring.elasticsearch.uris", elasticsearch::getHttpHostAddress);
        registry.add("spring.neo4j.uri", neo4j::getBoltUrl);
    }

    @Autowired
    private TestRestTemplate restTemplate;

    @Autowired
    private KnowledgeRepository knowledgeRepository;

    @Test
    @DisplayName("지식 생성 → PostgreSQL + ES + Neo4j 연동")
    void createKnowledge_SavesAcrossAllDatabases() {
        // Given
        KnowledgeCreateRequest request = new KnowledgeCreateRequest();
        request.setTitle("통합 테스트 지식");
        request.setContent("통합 테스트 내용입니다.");
        request.setCategoryId(UUID.randomUUID());

        // When
        ResponseEntity<KnowledgeResponse> response = restTemplate.postForEntity(
            "/api/v1/knowledge",
            request,
            KnowledgeResponse.class
        );

        // Then
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.CREATED);

        // PostgreSQL 확인
        UUID knowledgeId = response.getBody().getId();
        assertThat(knowledgeRepository.existsById(knowledgeId)).isTrue();

        // Elasticsearch 확인 (비동기이므로 대기)
        await().atMost(5, TimeUnit.SECONDS).untilAsserted(() -> {
            // ES 인덱스 확인 로직
        });
    }

    @Test
    @DisplayName("지식 검색 → Hybrid Search (Vector + Graph)")
    void searchKnowledge_HybridSearch() {
        // Given - 테스트 데이터 준비
        setupTestData();

        // When
        ResponseEntity<SearchResponse> response = restTemplate.getForEntity(
            "/api/v1/search?q=프로젝트 현황&mode=hybrid",
            SearchResponse.class
        );

        // Then
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getBody().getResults()).isNotEmpty();
    }
}
```

#### 3.2.3 AI 서비스 통합 테스트

```python
# tests/integration/test_vip_pipeline.py
import pytest
from testcontainers.elasticsearch import ElasticsearchContainer
from testcontainers.neo4j import Neo4jContainer
from app.pipelines.vip_pipeline import VIPPipeline

@pytest.fixture(scope="module")
def elasticsearch():
    with ElasticsearchContainer("elasticsearch:8.11.0") as es:
        yield es

@pytest.fixture(scope="module")
def neo4j():
    with Neo4jContainer("neo4j:5.15-community") as neo:
        yield neo

class TestVIPPipelineIntegration:

    def test_full_pipeline_execution(self, elasticsearch, neo4j):
        """VIP 파이프라인 전체 실행"""
        # Given
        pipeline = VIPPipeline(
            es_host=elasticsearch.get_url(),
            neo4j_uri=neo4j.get_connection_url()
        )

        query = "2025년 신규 프로젝트 현황 알려줘"

        # When
        result = pipeline.execute(query)

        # Then
        assert result is not None
        assert "answer" in result
        assert "sources" in result
        assert len(result["sources"]) > 0

    def test_entity_extraction_to_neo4j(self, neo4j):
        """엔티티 추출 후 Neo4j 저장"""
        # Given
        document = {
            "id": "doc-001",
            "content": "홍길동이 ACME 프로젝트를 담당합니다.",
            "metadata": {"project": "ACME"}
        }

        # When
        pipeline = VIPPipeline(neo4j_uri=neo4j.get_connection_url())
        pipeline.process_document(document)

        # Then - Neo4j 확인
        with neo4j.get_driver().session() as session:
            result = session.run(
                "MATCH (p:Person {name: '홍길동'})-[:MANAGES]->(proj:Project) "
                "RETURN proj.name as project"
            )
            record = result.single()
            assert record["project"] == "ACME"
```

#### 3.2.4 API 통합 테스트

```python
# tests/integration/test_api_endpoints.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

class TestSearchAPI:

    def test_chat_search_endpoint(self):
        """채팅 검색 API"""
        response = client.post(
            "/api/v1/search/chat",
            json={
                "query": "프로젝트 현황 알려줘",
                "session_id": "test-session-001",
                "history": []
            },
            headers={"Authorization": "Bearer test-token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data

    def test_keyword_search_endpoint(self):
        """키워드 검색 API"""
        response = client.get(
            "/api/v1/search",
            params={
                "q": "시스템 구축",
                "category": "project",
                "page": 1,
                "size": 10
            },
            headers={"Authorization": "Bearer test-token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total" in data
        assert "page" in data
```

### 3.3 E2E 테스트 (End-to-End Tests)

#### 3.3.1 목적
- 사용자 관점의 전체 워크플로우 검증
- 실제 브라우저 환경에서 테스트
- 핵심 비즈니스 시나리오 검증

#### 3.3.2 E2E 테스트 시나리오

| 시나리오 ID | 시나리오명 | 우선순위 |
|-------------|----------|----------|
| E2E-001 | 로그인 → 대시보드 진입 | 높음 |
| E2E-002 | 지식 등록 전체 플로우 | 높음 |
| E2E-003 | 채팅 모드 검색 및 응답 확인 | 높음 |
| E2E-004 | 키워드 검색 및 필터링 | 높음 |
| E2E-005 | 지식 수정 및 버전 확인 | 중간 |
| E2E-006 | 북마크 추가/제거 | 중간 |
| E2E-007 | PDF 변환 및 다운로드 | 중간 |
| E2E-008 | 프로필 설정 변경 | 낮음 |

#### 3.3.3 Playwright 테스트 코드

```typescript
// e2e/tests/knowledge-crud.spec.ts
import { test, expect } from '@playwright/test';

test.describe('지식 CRUD', () => {

  test.beforeEach(async ({ page }) => {
    // 로그인
    await page.goto('/login');
    await page.fill('[data-testid="email"]', 'test@company.com');
    await page.fill('[data-testid="password"]', 'test1234');
    await page.click('[data-testid="login-button"]');
    await expect(page).toHaveURL('/dashboard');
  });

  test('E2E-002: 지식 등록 전체 플로우', async ({ page }) => {
    // 1. 지식 등록 페이지 이동
    await page.click('[data-testid="nav-knowledge"]');
    await page.click('[data-testid="create-knowledge-button"]');
    await expect(page).toHaveURL('/knowledge/create');

    // 2. 지식 정보 입력
    await page.fill('[data-testid="title-input"]', 'E2E 테스트 지식');
    await page.fill('[data-testid="content-editor"]', '# 테스트 내용\n\n본문입니다.');

    // 3. 태그 추가
    await page.fill('[data-testid="tag-input"]', '테스트');
    await page.press('[data-testid="tag-input"]', 'Enter');

    // 4. 카테고리 선택
    await page.click('[data-testid="category-select"]');
    await page.click('[data-testid="category-option-project"]');

    // 5. 저장
    await page.click('[data-testid="submit-button"]');

    // 6. 검증
    await expect(page).toHaveURL(/\/knowledge\/[a-f0-9-]+/);
    await expect(page.locator('h1')).toContainText('E2E 테스트 지식');
  });

  test('E2E-003: 채팅 모드 검색', async ({ page }) => {
    // 1. 검색 페이지 이동
    await page.click('[data-testid="nav-search"]');
    await expect(page).toHaveURL('/search');

    // 2. 채팅 모드 선택
    await page.click('[data-testid="mode-chat"]');

    // 3. 질문 입력
    await page.fill('[data-testid="chat-input"]', '프로젝트 현황 알려줘');
    await page.click('[data-testid="send-button"]');

    // 4. 응답 대기 및 확인
    await expect(page.locator('[data-testid="chat-response"]')).toBeVisible({
      timeout: 30000  // AI 응답 대기
    });

    // 5. 소스 문서 확인
    await expect(page.locator('[data-testid="source-documents"]')).toBeVisible();
  });

  test('E2E-004: 키워드 검색 및 필터링', async ({ page }) => {
    // 1. 검색 페이지 이동
    await page.goto('/search');
    await page.click('[data-testid="mode-keyword"]');

    // 2. 검색어 입력
    await page.fill('[data-testid="search-input"]', '시스템 구축');
    await page.click('[data-testid="search-button"]');

    // 3. 결과 확인
    await expect(page.locator('[data-testid="search-results"]')).toBeVisible();

    // 4. 필터 적용
    await page.click('[data-testid="filter-category"]');
    await page.click('[data-testid="filter-option-project"]');

    // 5. 필터 적용 결과 확인
    await expect(page.locator('[data-testid="result-count"]')).toContainText(/\d+ 건/);
  });
});
```

```typescript
// e2e/tests/authentication.spec.ts
import { test, expect } from '@playwright/test';

test.describe('인증', () => {

  test('E2E-001: OAuth 로그인 → 대시보드 진입', async ({ page }) => {
    // 1. 로그인 페이지 접근
    await page.goto('/');
    await expect(page).toHaveURL('/login');

    // 2. SSO 로그인 버튼 클릭
    await page.click('[data-testid="sso-login-button"]');

    // 3. (Mock) OAuth 인증 완료 후 리다이렉트
    // 실제 환경에서는 SSO 페이지 처리
    await expect(page).toHaveURL('/dashboard');

    // 4. 대시보드 요소 확인
    await expect(page.locator('[data-testid="welcome-message"]')).toBeVisible();
    await expect(page.locator('[data-testid="recent-knowledge"]')).toBeVisible();
  });

  test('로그아웃', async ({ page }) => {
    // 로그인 상태에서 시작
    await page.goto('/dashboard');

    // 프로필 메뉴 클릭
    await page.click('[data-testid="profile-menu"]');
    await page.click('[data-testid="logout-button"]');

    // 로그인 페이지로 리다이렉트 확인
    await expect(page).toHaveURL('/login');
  });
});
```

### 3.4 성능 테스트 (Performance Tests)

#### 3.4.1 목적
- 응답 시간 요구사항 충족 확인
- 동시 사용자 처리 능력 검증
- 병목 구간 식별

#### 3.4.2 성능 테스트 시나리오

| 시나리오 | 목표 | 측정 지표 |
|----------|------|----------|
| **API 응답 시간** | ≤ 1초 (P95) | Response Time |
| **검색 응답 시간** | ≤ 3초 (P95) | Response Time |
| **채팅 첫 토큰** | ≤ 2초 (P95) | TTFT |
| **동시 사용자** | 1,000명 | Concurrent Users |
| **검색 TPS** | ≥ 100 TPS | Throughput |

#### 3.4.3 k6 부하 테스트 스크립트

```javascript
// performance/load-test.js
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const searchResponseTime = new Trend('search_response_time');
const chatFirstTokenTime = new Trend('chat_first_token_time');
const errorRate = new Rate('errors');

export const options = {
  scenarios: {
    // 점진적 부하 증가
    ramping_load: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '2m', target: 100 },   // 워밍업
        { duration: '5m', target: 500 },   // 중간 부하
        { duration: '5m', target: 1000 },  // 최대 부하
        { duration: '2m', target: 0 },     // 쿨다운
      ],
    },
    // 스파이크 테스트
    spike_test: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '1m', target: 100 },
        { duration: '30s', target: 1500 }, // 스파이크
        { duration: '1m', target: 100 },
      ],
      startTime: '15m',
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<1000'],      // 95%가 1초 이내
    search_response_time: ['p(95)<3000'],   // 검색 95%가 3초 이내
    errors: ['rate<0.01'],                  // 에러율 1% 미만
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080';
const AUTH_TOKEN = __ENV.AUTH_TOKEN;

export function setup() {
  // 테스트 데이터 준비
  return {
    searchQueries: [
      '프로젝트 현황',
      '시스템 구축 가이드',
      '2025년 계획',
      'API 문서',
      '개발 환경 설정'
    ]
  };
}

export default function(data) {
  const headers = {
    'Authorization': `Bearer ${AUTH_TOKEN}`,
    'Content-Type': 'application/json'
  };

  // 시나리오 1: 키워드 검색
  const searchQuery = data.searchQueries[Math.floor(Math.random() * data.searchQueries.length)];
  const searchStart = Date.now();

  const searchRes = http.get(
    `${BASE_URL}/api/v1/search?q=${encodeURIComponent(searchQuery)}&page=1&size=10`,
    { headers }
  );

  searchResponseTime.add(Date.now() - searchStart);

  check(searchRes, {
    'search status is 200': (r) => r.status === 200,
    'search has results': (r) => JSON.parse(r.body).results !== undefined,
  }) || errorRate.add(1);

  sleep(1);

  // 시나리오 2: 지식 상세 조회
  const listRes = http.get(`${BASE_URL}/api/v1/knowledge?page=1&size=5`, { headers });

  if (listRes.status === 200) {
    const knowledge = JSON.parse(listRes.body).data[0];
    if (knowledge) {
      const detailRes = http.get(
        `${BASE_URL}/api/v1/knowledge/${knowledge.id}`,
        { headers }
      );

      check(detailRes, {
        'detail status is 200': (r) => r.status === 200,
      }) || errorRate.add(1);
    }
  }

  sleep(2);
}

export function teardown(data) {
  console.log('Performance test completed');
}
```

#### 3.4.4 채팅 응답 시간 테스트

```javascript
// performance/chat-load-test.js
import http from 'k6/http';
import { check } from 'k6';
import { Trend } from 'k6/metrics';

const chatTTFT = new Trend('chat_ttft');  // Time To First Token

export const options = {
  scenarios: {
    chat_load: {
      executor: 'constant-vus',
      vus: 200,           // 동시 채팅 세션
      duration: '10m',
    },
  },
  thresholds: {
    chat_ttft: ['p(95)<2000'],  // 첫 토큰 2초 이내
  },
};

export default function() {
  const payload = JSON.stringify({
    query: '현재 진행 중인 프로젝트 현황을 알려줘',
    session_id: `session-${__VU}-${__ITER}`,
    history: []
  });

  const start = Date.now();

  // SSE 연결로 스트리밍 응답 수신
  const res = http.post(
    `${BASE_URL}/api/v1/search/chat/stream`,
    payload,
    {
      headers: {
        'Authorization': `Bearer ${AUTH_TOKEN}`,
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream'
      },
      timeout: '30s'
    }
  );

  // 첫 번째 청크 수신 시간 측정
  chatTTFT.add(Date.now() - start);

  check(res, {
    'chat response received': (r) => r.status === 200,
  });
}
```

### 3.5 보안 테스트 (Security Tests)

#### 3.5.1 목적
- OWASP Top 10 취약점 검증
- 인증/인가 보안 확인
- 데이터 보호 검증

#### 3.5.2 보안 테스트 체크리스트

| 카테고리 | 테스트 항목 | 방법 |
|----------|------------|------|
| **인증** | JWT 토큰 검증 | 수동 + 자동화 |
| | 세션 타임아웃 | 자동화 |
| | 토큰 만료 처리 | 자동화 |
| **인가** | 권한 없는 리소스 접근 | 자동화 |
| | 수평적 권한 상승 | 수동 |
| | 수직적 권한 상승 | 수동 |
| **입력 검증** | SQL Injection | OWASP ZAP |
| | XSS | OWASP ZAP |
| | Command Injection | 수동 |
| **데이터 보호** | HTTPS 강제 | 자동화 |
| | 민감 정보 노출 | 수동 |
| | 로그 내 민감 정보 | 수동 |

#### 3.5.3 보안 테스트 코드

```java
// SecurityTests.java
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class SecurityTests {

    @Autowired
    private TestRestTemplate restTemplate;

    @Test
    @DisplayName("인증 없이 API 접근 시 401 반환")
    void accessWithoutToken_Returns401() {
        ResponseEntity<String> response = restTemplate.getForEntity(
            "/api/v1/knowledge",
            String.class
        );

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.UNAUTHORIZED);
    }

    @Test
    @DisplayName("만료된 토큰으로 접근 시 401 반환")
    void accessWithExpiredToken_Returns401() {
        HttpHeaders headers = new HttpHeaders();
        headers.setBearerAuth(EXPIRED_TOKEN);

        ResponseEntity<String> response = restTemplate.exchange(
            "/api/v1/knowledge",
            HttpMethod.GET,
            new HttpEntity<>(headers),
            String.class
        );

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.UNAUTHORIZED);
    }

    @Test
    @DisplayName("일반 사용자가 관리자 API 접근 시 403 반환")
    void userAccessAdminApi_Returns403() {
        HttpHeaders headers = new HttpHeaders();
        headers.setBearerAuth(USER_TOKEN);  // 일반 사용자 토큰

        ResponseEntity<String> response = restTemplate.exchange(
            "/api/v1/admin/users",
            HttpMethod.GET,
            new HttpEntity<>(headers),
            String.class
        );

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.FORBIDDEN);
    }

    @Test
    @DisplayName("타인의 지식 수정 시 403 반환")
    void modifyOthersKnowledge_Returns403() {
        HttpHeaders headers = new HttpHeaders();
        headers.setBearerAuth(USER_A_TOKEN);

        KnowledgeUpdateRequest request = new KnowledgeUpdateRequest();
        request.setTitle("수정된 제목");

        // USER_B가 작성한 지식
        ResponseEntity<String> response = restTemplate.exchange(
            "/api/v1/knowledge/" + USER_B_KNOWLEDGE_ID,
            HttpMethod.PUT,
            new HttpEntity<>(request, headers),
            String.class
        );

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.FORBIDDEN);
    }

    @Test
    @DisplayName("SQL Injection 방어")
    void sqlInjection_Prevented() {
        HttpHeaders headers = new HttpHeaders();
        headers.setBearerAuth(USER_TOKEN);

        // SQL Injection 시도
        String maliciousQuery = "'; DROP TABLE knowledge; --";

        ResponseEntity<String> response = restTemplate.exchange(
            "/api/v1/search?q=" + URLEncoder.encode(maliciousQuery, UTF_8),
            HttpMethod.GET,
            new HttpEntity<>(headers),
            String.class
        );

        // 정상 응답 (Injection 실패)
        assertThat(response.getStatusCode()).isIn(HttpStatus.OK, HttpStatus.BAD_REQUEST);

        // 테이블이 존재하는지 확인
        assertThat(knowledgeRepository.count()).isGreaterThan(0);
    }

    @Test
    @DisplayName("XSS 방어 - 저장 시 이스케이핑")
    void xss_Prevented() {
        HttpHeaders headers = new HttpHeaders();
        headers.setBearerAuth(USER_TOKEN);

        KnowledgeCreateRequest request = new KnowledgeCreateRequest();
        request.setTitle("<script>alert('XSS')</script>");
        request.setContent("정상 내용");

        ResponseEntity<KnowledgeResponse> response = restTemplate.postForEntity(
            "/api/v1/knowledge",
            new HttpEntity<>(request, headers),
            KnowledgeResponse.class
        );

        // 저장된 제목에 스크립트가 이스케이핑 되었는지 확인
        assertThat(response.getBody().getTitle())
            .doesNotContain("<script>");
    }
}
```

#### 3.5.4 OWASP ZAP 자동화 스캔

```yaml
# .github/workflows/security-scan.yml
name: Security Scan

on:
  schedule:
    - cron: '0 2 * * 1'  # 매주 월요일 02:00
  workflow_dispatch:

jobs:
  zap-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Start Application
        run: docker-compose up -d

      - name: Wait for Application
        run: sleep 60

      - name: OWASP ZAP Full Scan
        uses: zaproxy/action-full-scan@v0.7.0
        with:
          target: 'http://localhost:8080'
          rules_file_name: 'zap-rules.tsv'
          cmd_options: '-a'

      - name: Upload ZAP Report
        uses: actions/upload-artifact@v4
        with:
          name: zap-report
          path: report_html.html
```

---

## 4. 테스트 환경

### 4.1 환경 구성

| 환경 | 용도 | 구성 |
|------|------|------|
| **Local** | 개발자 단위 테스트 | Docker Compose |
| **CI** | 자동화 테스트 | GitHub Actions + Testcontainers |
| **QA** | 통합/E2E 테스트 | Kubernetes (Dev Cluster) |
| **Staging** | 성능/보안 테스트 | Production-like |
| **Production** | 스모크 테스트 | 실 운영 환경 |

### 4.2 테스트 환경 구성도

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Test Environments                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐           │
│  │    Local     │    │      CI      │    │      QA      │           │
│  │              │    │              │    │              │           │
│  │ Docker       │    │ Testcontainers│   │ K8s Dev      │           │
│  │ Compose      │───▶│ GitHub Actions│──▶│ Cluster      │           │
│  │              │    │              │    │              │           │
│  │ Unit Tests   │    │ Unit/Integ   │    │ E2E Tests    │           │
│  └──────────────┘    └──────────────┘    └──────────────┘           │
│                                                 │                    │
│                                                 ▼                    │
│                      ┌──────────────┐    ┌──────────────┐           │
│                      │   Staging    │    │  Production  │           │
│                      │              │    │              │           │
│                      │ Production   │    │ Smoke Tests  │           │
│                      │ Mirror       │───▶│ Only         │           │
│                      │              │    │              │           │
│                      │ Perf/Security│    │ Monitoring   │           │
│                      └──────────────┘    └──────────────┘           │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.3 테스트용 Docker Compose

```yaml
# docker-compose.test.yml
version: '3.8'

services:
  postgres-test:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: knowledge_test
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
    ports:
      - "5433:5432"
    tmpfs:
      - /var/lib/postgresql/data

  elasticsearch-test:
    image: elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ports:
      - "9201:9200"
    tmpfs:
      - /usr/share/elasticsearch/data

  neo4j-test:
    image: neo4j:5.15-community
    environment:
      NEO4J_AUTH: none
    ports:
      - "7475:7474"
      - "7688:7687"
    tmpfs:
      - /data

  redis-test:
    image: redis:7-alpine
    ports:
      - "6380:6379"

  # Mock LLM Server (개발/테스트용)
  mock-llm:
    build:
      context: ./test/mock-llm
    ports:
      - "8001:8000"
    environment:
      - MOCK_RESPONSE_DELAY=100  # ms
```

---

## 5. 테스트 도구

### 5.1 도구 목록

| 카테고리 | 도구 | 용도 |
|----------|------|------|
| **Unit (Java)** | JUnit 5 | 테스트 프레임워크 |
| | Mockito | 목(Mock) 객체 |
| | AssertJ | 어서션 |
| **Unit (Python)** | pytest | 테스트 프레임워크 |
| | pytest-mock | 목(Mock) |
| | pytest-cov | 커버리지 |
| **Unit (React)** | Jest | 테스트 프레임워크 |
| | React Testing Library | 컴포넌트 테스트 |
| **Integration** | Testcontainers | 컨테이너 기반 테스트 |
| | REST Assured | API 테스트 |
| **E2E** | Playwright | 브라우저 자동화 |
| **Performance** | k6 | 부하 테스트 |
| | Locust | Python 부하 테스트 |
| **Security** | OWASP ZAP | 취약점 스캔 |
| | Trivy | 컨테이너 스캔 |
| **Coverage** | JaCoCo | Java 커버리지 |
| | Coverage.py | Python 커버리지 |
| | Istanbul | JS 커버리지 |
| **Reporting** | Allure | 테스트 리포트 |

### 5.2 도구 설정

#### 5.2.1 JUnit 5 + Mockito 설정

```xml
<!-- pom.xml -->
<dependencies>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-test</artifactId>
        <scope>test</scope>
    </dependency>
    <dependency>
        <groupId>org.testcontainers</groupId>
        <artifactId>junit-jupiter</artifactId>
        <scope>test</scope>
    </dependency>
    <dependency>
        <groupId>org.testcontainers</groupId>
        <artifactId>postgresql</artifactId>
        <scope>test</scope>
    </dependency>
    <dependency>
        <groupId>org.testcontainers</groupId>
        <artifactId>elasticsearch</artifactId>
        <scope>test</scope>
    </dependency>
</dependencies>

<build>
    <plugins>
        <plugin>
            <groupId>org.jacoco</groupId>
            <artifactId>jacoco-maven-plugin</artifactId>
            <version>0.8.11</version>
            <executions>
                <execution>
                    <goals>
                        <goal>prepare-agent</goal>
                    </goals>
                </execution>
                <execution>
                    <id>report</id>
                    <phase>test</phase>
                    <goals>
                        <goal>report</goal>
                    </goals>
                </execution>
            </executions>
        </plugin>
    </plugins>
</build>
```

#### 5.2.2 pytest 설정

```toml
# pyproject.toml
[tool.pytest.ini_options]
minversion = "7.0"
addopts = "-ra -q --cov=app --cov-report=html --cov-report=xml"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

[tool.coverage.run]
source = ["app"]
omit = ["tests/*", "*/__pycache__/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise NotImplementedError",
]
```

#### 5.2.3 Playwright 설정

```typescript
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e/tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['junit', { outputFile: 'test-results/e2e-results.xml' }],
  ],
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
  },
});
```

---

## 6. 테스트 데이터 관리

### 6.1 테스트 데이터 전략

| 전략 | 적용 대상 | 설명 |
|------|----------|------|
| **Fixture** | Unit 테스트 | 고정된 테스트 데이터 |
| **Factory** | Integration 테스트 | 동적 데이터 생성 |
| **Seeding** | E2E 테스트 | 사전 데이터 로드 |
| **Anonymization** | 성능 테스트 | 운영 데이터 익명화 |

### 6.2 테스트 데이터 예시

#### 6.2.1 Java Factory

```java
// TestDataFactory.java
public class TestDataFactory {

    private static final Faker faker = new Faker(new Locale("ko"));

    public static Knowledge createKnowledge() {
        return Knowledge.builder()
            .id(UUID.randomUUID())
            .title(faker.book().title())
            .content(faker.lorem().paragraphs(3).stream()
                .collect(Collectors.joining("\n\n")))
            .categoryId(UUID.randomUUID())
            .authorId(UUID.randomUUID())
            .visibility(Visibility.PUBLIC)
            .viewCount(faker.number().numberBetween(0, 1000))
            .likeCount(faker.number().numberBetween(0, 100))
            .createdAt(LocalDateTime.now())
            .updatedAt(LocalDateTime.now())
            .build();
    }

    public static KnowledgeCreateRequest createKnowledgeRequest() {
        return KnowledgeCreateRequest.builder()
            .title(faker.book().title())
            .content(faker.lorem().paragraph())
            .categoryId(UUID.randomUUID())
            .tags(List.of("테스트", "샘플"))
            .build();
    }

    public static User createUser(String role) {
        return User.builder()
            .id(UUID.randomUUID())
            .email(faker.internet().emailAddress())
            .name(faker.name().fullName())
            .department(faker.company().name())
            .role(Role.valueOf(role))
            .build();
    }
}
```

#### 6.2.2 Python Factory

```python
# tests/factories.py
import factory
from faker import Faker
from app.models import Knowledge, User

fake = Faker('ko_KR')

class UserFactory(factory.Factory):
    class Meta:
        model = User

    id = factory.LazyFunction(lambda: str(fake.uuid4()))
    email = factory.LazyFunction(fake.email)
    name = factory.LazyFunction(fake.name)
    department = factory.LazyFunction(fake.company)
    role = "USER"

class KnowledgeFactory(factory.Factory):
    class Meta:
        model = Knowledge

    id = factory.LazyFunction(lambda: str(fake.uuid4()))
    title = factory.LazyFunction(fake.sentence)
    content = factory.LazyFunction(lambda: fake.paragraphs(nb=3))
    author_id = factory.LazyFunction(lambda: str(fake.uuid4()))
    category_id = factory.LazyFunction(lambda: str(fake.uuid4()))
    view_count = factory.LazyFunction(lambda: fake.random_int(0, 1000))
    like_count = factory.LazyFunction(lambda: fake.random_int(0, 100))
```

### 6.3 E2E 테스트 시드 데이터

```sql
-- test/seed/e2e-seed.sql
-- 테스트용 카테고리
INSERT INTO categories (id, name, parent_id) VALUES
  ('cat-001', '프로젝트', NULL),
  ('cat-002', '기술문서', NULL),
  ('cat-003', 'FAQ', NULL);

-- 테스트용 사용자
INSERT INTO users (id, email, name, department, role) VALUES
  ('user-001', 'test@company.com', '테스트 사용자', '개발팀', 'USER'),
  ('user-002', 'admin@company.com', '관리자', 'IT팀', 'ADMIN'),
  ('user-003', 'km@company.com', '지식관리자', '기획팀', 'KNOWLEDGE_MANAGER');

-- 테스트용 지식
INSERT INTO knowledge (id, title, content, category_id, author_id, visibility) VALUES
  ('know-001', 'E2E 테스트 지식 1', '테스트 내용입니다.', 'cat-001', 'user-001', 'PUBLIC'),
  ('know-002', 'E2E 테스트 지식 2', '또 다른 테스트 내용.', 'cat-002', 'user-002', 'PUBLIC');
```

---

## 7. 테스트 커버리지 목표

### 7.1 커버리지 기준

| 서비스 | Line Coverage | Branch Coverage | 비고 |
|--------|---------------|-----------------|------|
| **Knowledge Service** | ≥ 80% | ≥ 70% | 핵심 CRUD |
| **Search Service** | ≥ 80% | ≥ 70% | 검색 로직 |
| **AI Service** | ≥ 75% | ≥ 65% | LLM 호출 제외 |
| **User Service** | ≥ 80% | ≥ 70% | 인증/인가 |
| **Export Service** | ≥ 70% | ≥ 60% | 파일 변환 |
| **Gateway Service** | ≥ 70% | ≥ 60% | 필터/라우팅 |
| **Frontend** | ≥ 70% | ≥ 60% | 컴포넌트 |

### 7.2 커버리지 제외 항목

```java
// 커버리지 제외 대상
@Generated           // Lombok 생성 코드
@Configuration       // 설정 클래스
@SpringBootApplication
main()               // 메인 메서드
toString(), equals(), hashCode()  // 자동 생성 메서드
```

### 7.3 커버리지 리포트 자동화

```yaml
# .github/workflows/coverage.yml
name: Coverage Report

on: [push, pull_request]

jobs:
  coverage:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Tests with Coverage
        run: |
          mvn test jacoco:report

      - name: Upload Coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: ./target/site/jacoco/jacoco.xml
          fail_ci_if_error: true

      - name: Coverage Gate Check
        run: |
          COVERAGE=$(grep -oP 'Total.*?([0-9]+)%' target/site/jacoco/index.html | grep -oP '[0-9]+' | head -1)
          if [ "$COVERAGE" -lt 80 ]; then
            echo "Coverage ${COVERAGE}% is below 80%"
            exit 1
          fi
```

---

## 8. CI/CD 통합

### 8.1 테스트 파이프라인

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CI/CD Test Pipeline                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐   │
│  │  Lint   │───▶│  Unit   │───▶│ Integr- │───▶│Security │───▶│   E2E   │   │
│  │  Check  │    │  Tests  │    │  ation  │    │  Scan   │    │  Tests  │   │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘   │
│       │              │              │              │              │          │
│       ▼              ▼              ▼              ▼              ▼          │
│   [ESLint]      [JUnit5]     [Testcontainers] [OWASP ZAP]  [Playwright]    │
│   [Pylint]      [pytest]                      [Trivy]                       │
│   [Black]       [Jest]                                                      │
│                                                                              │
│  ────────────────────────────────────────────────────────────────────────   │
│                                    │                                         │
│                                    ▼                                         │
│                          ┌─────────────────┐                                 │
│                          │  Coverage Gate  │                                 │
│                          │    (≥ 80%)      │                                 │
│                          └────────┬────────┘                                 │
│                                   │                                          │
│                    ┌──────────────┼──────────────┐                           │
│                    │              │              │                           │
│                    ▼              ▼              ▼                           │
│              [main branch]  [develop]   [feature/*]                         │
│                    │              │              │                           │
│                    ▼              │              │                           │
│            ┌──────────────┐      │              │                           │
│            │ Performance  │      │              │                           │
│            │    Tests     │      │              │                           │
│            │    (k6)      │      │              │                           │
│            └──────┬───────┘      │              │                           │
│                   │              │              │                           │
│                   ▼              │              │                           │
│            ┌──────────────┐      │              │                           │
│            │   Deploy     │◀─────┴──────────────┘                           │
│            │   Staging    │                                                  │
│            └──────────────┘                                                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8.2 GitHub Actions Workflow

```yaml
# .github/workflows/test.yml
name: Test Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  # Stage 1: Lint
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Java Lint (Checkstyle)
        run: mvn checkstyle:check

      - name: Python Lint
        run: |
          pip install black pylint
          black --check ai-service/
          pylint ai-service/app/

      - name: Frontend Lint
        run: |
          cd frontend
          npm ci
          npm run lint

  # Stage 2: Unit Tests
  unit-tests:
    needs: lint
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service: [knowledge-service, search-service, user-service, ai-service]
    steps:
      - uses: actions/checkout@v4

      - name: Run Unit Tests
        run: |
          if [[ "${{ matrix.service }}" == "ai-service" ]]; then
            cd ai-service
            pip install -r requirements.txt
            pytest tests/unit/ --cov=app --cov-report=xml
          else
            cd ${{ matrix.service }}
            mvn test -Dtest=*UnitTest
          fi

      - name: Upload Coverage
        uses: codecov/codecov-action@v3

  # Stage 3: Integration Tests
  integration-tests:
    needs: unit-tests
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: test
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        ports:
          - 5432:5432
    steps:
      - uses: actions/checkout@v4

      - name: Run Integration Tests
        run: |
          mvn test -Dtest=*IntegrationTest

  # Stage 4: Security Scan
  security-scan:
    needs: unit-tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Trivy Container Scan
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          severity: 'CRITICAL,HIGH'

      - name: Dependency Check
        run: mvn org.owasp:dependency-check-maven:check

  # Stage 5: E2E Tests
  e2e-tests:
    needs: [integration-tests, security-scan]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Start Services
        run: docker-compose -f docker-compose.test.yml up -d

      - name: Wait for Services
        run: sleep 60

      - name: Run Playwright Tests
        run: |
          cd frontend
          npm ci
          npx playwright install
          npx playwright test

      - name: Upload Test Results
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report
          path: frontend/playwright-report/

  # Stage 6: Performance Tests (main branch only)
  performance-tests:
    needs: e2e-tests
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run k6 Load Tests
        run: |
          docker run --rm \
            -v $PWD/performance:/scripts \
            -e BASE_URL=${{ secrets.STAGING_URL }} \
            -e AUTH_TOKEN=${{ secrets.TEST_AUTH_TOKEN }} \
            grafana/k6 run /scripts/load-test.js
```

### 8.3 테스트 결과 알림

```yaml
# .github/workflows/test-notification.yml
name: Test Notification

on:
  workflow_run:
    workflows: ["Test Pipeline"]
    types: [completed]

jobs:
  notify:
    runs-on: ubuntu-latest
    steps:
      - name: Send Slack Notification
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ github.event.workflow_run.conclusion }}
          fields: repo,message,commit,author,action,eventName,ref,workflow
          text: |
            Test Pipeline ${{ github.event.workflow_run.conclusion }}
            Coverage: ${{ env.COVERAGE }}%
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
```

---

## 9. 결함 관리

### 9.1 결함 분류

| 심각도 | 정의 | 예시 |
|--------|------|------|
| **Critical** | 시스템 전체 장애 | 서버 크래시, 데이터 손실 |
| **High** | 핵심 기능 불가 | 검색 실패, 로그인 불가 |
| **Medium** | 기능 일부 제한 | 필터 오작동, UI 깨짐 |
| **Low** | 사소한 문제 | 오타, 미세한 정렬 |

### 9.2 결함 처리 프로세스

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ 발견    │───▶│ 등록    │───▶│ 분석    │───▶│ 수정    │───▶│ 검증    │
│ (Tester)│    │ (JIRA)  │    │ (Dev)   │    │ (Dev)   │    │ (Tester)│
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
                                                                  │
                                                                  ▼
                                                            ┌─────────┐
                                                            │ 종료    │
                                                            │ (Close) │
                                                            └─────────┘
```

### 9.3 JIRA 결함 템플릿

```markdown
## 결함 제목
[심각도] 간단한 설명

## 환경
- 브라우저: Chrome 120
- OS: Windows 11
- 서버 환경: QA

## 재현 단계
1. 로그인
2. 검색 페이지 이동
3. '프로젝트'로 검색
4. 필터 적용

## 기대 결과
- 검색 결과가 필터에 맞게 표시

## 실제 결과
- 필터가 적용되지 않음

## 스크린샷/로그
[첨부]

## 관련 정보
- 요구사항: FR-SR-002-03
- 테스트 케이스: TC-SR-015
```

---

## 10. 테스트 단계

### 10.1 단계별 테스트 활동

| 단계 | 활동 | 산출물 |
|------|------|--------|
| **Phase 1: 계획** | 테스트 계획 수립, 환경 구축 | 테스트 계획서 |
| **Phase 2: 설계** | 테스트 케이스 설계, 데이터 준비 | 테스트 케이스 |
| **Phase 3: 구현** | 테스트 스크립트 개발 | 자동화 스크립트 |
| **Phase 4: 실행** | 테스트 실행, 결함 등록 | 테스트 결과 |
| **Phase 5: 평가** | 결과 분석, 품질 평가 | 테스트 리포트 |

### 10.2 단계별 Entry/Exit 기준

#### Phase 1: 계획
| Entry 기준 | Exit 기준 |
|------------|----------|
| 요구사항 명세서 완료 | 테스트 계획서 승인 |
| 설계 문서 완료 | 테스트 환경 구축 완료 |

#### Phase 2: 설계
| Entry 기준 | Exit 기준 |
|------------|----------|
| 테스트 계획서 승인 | 테스트 케이스 리뷰 완료 |
| API 명세서 완료 | 테스트 데이터 준비 완료 |

#### Phase 3: 구현
| Entry 기준 | Exit 기준 |
|------------|----------|
| 테스트 케이스 승인 | 자동화 스크립트 완성 |
| 개발 코드 통합 완료 | 스크립트 리뷰 완료 |

#### Phase 4: 실행
| Entry 기준 | Exit 기준 |
|------------|----------|
| 빌드 배포 완료 | 모든 테스트 실행 완료 |
| 테스트 환경 준비 | Critical/High 결함 해결 |

#### Phase 5: 평가
| Entry 기준 | Exit 기준 |
|------------|----------|
| 테스트 실행 완료 | 테스트 리포트 승인 |
| 결함 분석 완료 | 릴리스 승인 |

### 10.3 릴리스 기준

| 항목 | 기준 |
|------|------|
| **테스트 실행률** | 100% |
| **테스트 통과율** | ≥ 95% |
| **커버리지** | ≥ 80% |
| **Critical 결함** | 0 |
| **High 결함** | 0 |
| **Medium 결함** | ≤ 5 (계획된 수정) |
| **성능 기준** | 모두 충족 |
| **보안 스캔** | Critical/High 0 |

---

## 부록

### A. 테스트 케이스 템플릿

```markdown
## 테스트 케이스 ID: TC-[도메인]-[번호]

### 기본 정보
- **테스트명**:
- **요구사항 ID**:
- **우선순위**: 높음/중간/낮음
- **테스트 유형**: Unit/Integration/E2E

### 사전 조건
1.
2.

### 테스트 단계
| 단계 | 행동 | 기대 결과 |
|------|------|----------|
| 1 | | |
| 2 | | |

### 테스트 데이터
- 입력:
- 예상 출력:

### 사후 조건
-
```

### B. 용어 정의

| 용어 | 정의 |
|------|------|
| **TDD** | Test-Driven Development |
| **BDD** | Behavior-Driven Development |
| **E2E** | End-to-End |
| **TTFT** | Time To First Token |
| **TPS** | Transactions Per Second |
| **P95** | 95th Percentile |
| **RRF** | Reciprocal Rank Fusion |

### C. 참고 자료

- [JUnit 5 User Guide](https://junit.org/junit5/docs/current/user-guide/)
- [pytest Documentation](https://docs.pytest.org/)
- [Playwright Documentation](https://playwright.dev/docs/intro)
- [k6 Documentation](https://k6.io/docs/)
- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)

---

**문서 작성 완료: 2026-01-14**
