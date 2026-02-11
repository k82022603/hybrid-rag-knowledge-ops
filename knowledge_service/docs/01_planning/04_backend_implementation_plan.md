# 사내 지식 검색 시스템 백엔드 구축계획서
## SpringBoot/SpringCloud + Python AI Service 기반 Knowledge Discovery Platform

---

## 문서 정보

| 항목 | 내용 |
|------|------|
| **문서명** | 사내 지식 검색 시스템 백엔드 구축계획서 |
| **버전** | 1.0 |
| **작성일** | 2026-01-14 |
| **작성자** | Claude Code (Opus 4.5) |
| **상태** | 초안 |
| **참조 문서** | [상세 설계서](../02_design/01_hybrid_rag_platform_detailed_design.md), [프론트엔드 구현 계획서](./frontend_implementation_plan.md) |

---

## 변경 이력

| 버전 | 일자 | 작성자 | 변경 내용 |
|------|------|--------|----------|
| 1.0 | 2026-01-14 | Claude Code | 초안 작성 |

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [기술 스택 및 아키텍처](#2-기술-스택-및-아키텍처)
3. [서비스 구성](#3-서비스-구성)
4. [API 설계](#4-api-설계)
5. [데이터베이스 설계](#5-데이터베이스-설계)
6. [AI 서비스 설계](#6-ai-서비스-설계)
7. [인증/인가 설계](#7-인증인가-설계)
8. [개발 환경 구성](#8-개발-환경-구성)
9. [빌드 및 배포](#9-빌드-및-배포)
10. [테스트 전략](#10-테스트-전략)
11. [보안 및 성능](#11-보안-및-성능)
12. [개발 로드맵](#12-개발-로드맵)

---

## 1. 프로젝트 개요

### 1.1 프로젝트 목적

사내 지식 검색 시스템의 백엔드는 Graph RAG 기반 지능형 검색 엔진을 중심으로 지식의 저장, 검색, 분석, 추천 기능을 제공합니다. SpringBoot/SpringCloud 기반 마이크로서비스 아키텍처와 Python 기반 AI 서비스를 결합하여 확장성과 AI 처리 성능을 모두 확보합니다.

### 1.2 핵심 가치 제안

| 가치 | 설명 | 구현 방법 |
|------|------|----------|
| **비용 효율성** | LLM 비용 95% 절감 | DeepSeek V3.2 단일 모델 통합 |
| **빠른 검색** | 평균 응답 0.8초 | 제로 조인 아키텍처, ES 메타데이터 비정규화 |
| **지능형 검색** | 의도 기반 검색 | VIP 3단계 LLM 파이프라인 |
| **확장성** | 수평적 확장 가능 | 마이크로서비스 아키텍처, Kubernetes Ready |

### 1.3 서비스 범위

**In-Scope:**
- 지식 CRUD API
- Hybrid RAG 검색 (Vector + Graph)
- 채팅 기반 대화형 검색 (WebSocket/SSE)
- 문서 파싱 및 자동 메타데이터 추출
- 사용자 인증/인가 (OAuth 2.0)
- 문서 변환 (Excel, PPT, PDF)
- 대시보드 통계 API

**Out-of-Scope:**
- 메시지 큐 (Kafka) - Phase 2
- 멀티 테넌트 지원 - Phase 2
- 실시간 협업 편집 - Phase 3

---

## 2. 기술 스택 및 아키텍처

### 2.1 기술 스택 요약

| 구분 | 기술 | 버전 | 용도 |
|------|------|------|------|
| **API Gateway** | Spring Cloud Gateway | 4.x | API 라우팅, 인증, 로깅 |
| **Web Framework** | Spring Boot | 3.2+ | REST API, WebSocket |
| **Service Discovery** | Spring Cloud Netflix Eureka | 4.x | 서비스 등록/발견 |
| **Config Server** | Spring Cloud Config | 4.x | 중앙 설정 관리 |
| **ORM** | Spring Data JPA | 3.x | PostgreSQL 연동 |
| **검색 클라이언트** | Spring Data Elasticsearch | 5.x | ES 연동 |
| **그래프 클라이언트** | Spring Data Neo4j | 7.x | Neo4j 연동 |
| **AI Framework** | LangChain + LangGraph | 1.2+ | AI 파이프라인 |
| **LLM** | DeepSeek Chat/Reasoner | V3.2 | 엔티티 추출, 답변 합성 |
| **임베딩** | BGE-M3 | - | Dense + Sparse 벡터 |
| **문서 파싱** | Docling | 2.x | PDF/DOCX 텍스트 추출 |
| **캐시** | Redis | 7.x | 세션, 캐시, Rate Limit |
| **비동기 작업** | Celery | 5.x | 문서 처리 백그라운드 |

### 2.2 전체 아키텍처

```
                                    ┌─────────────────────────────────────────────────────────┐
                                    │                      Clients                             │
                                    │    (Web UI, Mobile App, API Consumers)                   │
                                    └──────────────────────┬──────────────────────────────────┘
                                                           │
                                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                     API Gateway (Spring Cloud Gateway)                           │
│                     - Authentication/Authorization, Rate Limiting, Logging                       │
│                     - Request Routing, Load Balancing, Circuit Breaker                          │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
                                                           │
               ┌───────────────────────────────────────────┼───────────────────────────────────────┐
               │                                           │                                        │
               ▼                                           ▼                                        ▼
┌─────────────────────────┐            ┌─────────────────────────────┐            ┌─────────────────────────┐
│   Knowledge Service     │            │       Search Service         │            │     User Service         │
│   (Spring Boot)         │            │       (Spring Boot)          │            │     (Spring Boot)        │
│   - CRUD Operations     │            │   - Query Processing         │            │   - User Management      │
│   - File Upload         │            │   - Result Aggregation       │            │   - Preferences          │
│   - Version Management  │            │   - Chat Session Mgmt        │            │   - OAuth Integration    │
└───────────┬─────────────┘            └───────────┬─────────────────┘            └───────────┬─────────────┘
            │                                       │                                          │
            │                          ┌────────────┴─────────────────┐                        │
            │                          │                              │                        │
            │                          ▼                              ▼                        │
            │           ┌──────────────────────────┐  ┌──────────────────────────┐             │
            │           │   AI Service (Python)    │  │   Export Service         │             │
            │           │   FastAPI + LangGraph    │  │   (Spring Boot)          │             │
            │           │   - Hybrid Search        │  │   - Excel/PPT/PDF        │             │
            │           │   - Entity Extraction    │  │   - Template Processing  │             │
            │           │   - Answer Synthesis     │  │                          │             │
            │           └───────────┬──────────────┘  └──────────────────────────┘             │
            │                       │                                                          │
            └───────────────────────┼──────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
    ┌───────────────────────────────┐   ┌───────────────────────────────┐
    │         Data Layer            │   │      Supporting Services      │
    │  ┌───────────┐ ┌───────────┐  │   │  ┌───────────┐ ┌───────────┐  │
    │  │PostgreSQL │ │   Neo4j   │  │   │  │   Redis   │ │  Celery   │  │
    │  │  (SSOT)   │ │  (Graph)  │  │   │  │  (Cache)  │ │  (Worker) │  │
    │  └───────────┘ └───────────┘  │   │  └───────────┘ └───────────┘  │
    │  ┌─────────────────────────┐  │   │                               │
    │  │     Elasticsearch       │  │   │                               │
    │  │   (Vector + Metadata)   │  │   │                               │
    │  └─────────────────────────┘  │   │                               │
    └───────────────────────────────┘   └───────────────────────────────┘
```

### 2.3 서비스 간 통신

| 통신 유형 | 사용 시나리오 | 기술 |
|----------|--------------|------|
| **동기 REST** | CRUD 작업, 단순 조회 | HTTP/JSON |
| **WebSocket** | 채팅 스트리밍, 실시간 검색 | STOMP over WebSocket |
| **SSE** | 답변 스트리밍 | Server-Sent Events |
| **비동기 작업** | 문서 처리, 인덱싱 | Celery + Redis |

---

## 3. 서비스 구성

### 3.1 서비스 목록

| 서비스 | 포트 | 역할 | 기술 스택 |
|--------|------|------|----------|
| **gateway-service** | 8080 | API Gateway | Spring Cloud Gateway |
| **eureka-service** | 8761 | 서비스 디스커버리 | Spring Cloud Eureka |
| **config-service** | 8888 | 설정 서버 | Spring Cloud Config |
| **knowledge-service** | 8081 | 지식 CRUD | Spring Boot |
| **search-service** | 8082 | 검색 API | Spring Boot |
| **user-service** | 8083 | 사용자 관리 | Spring Boot |
| **export-service** | 8084 | 문서 변환 | Spring Boot |
| **ai-service** | 8000 | AI 처리 | FastAPI + LangGraph |
| **dashboard-service** | 8085 | 통계/분석 | Spring Boot |

### 3.2 Gateway Service (API Gateway)

#### 3.2.1 역할

- 모든 외부 요청의 단일 진입점
- JWT 토큰 검증 및 인증
- Rate Limiting 적용
- 로깅 및 모니터링
- 서킷 브레이커 (장애 격리)

#### 3.2.2 라우팅 설정

```yaml
# application.yml
spring:
  cloud:
    gateway:
      routes:
        - id: knowledge-service
          uri: lb://KNOWLEDGE-SERVICE
          predicates:
            - Path=/api/v1/knowledge/**
          filters:
            - JwtAuthenticationFilter
            - name: CircuitBreaker
              args:
                name: knowledgeCircuitBreaker
                fallbackUri: forward:/fallback/knowledge

        - id: search-service
          uri: lb://SEARCH-SERVICE
          predicates:
            - Path=/api/v1/search/**
          filters:
            - JwtAuthenticationFilter

        - id: ai-service
          uri: http://ai-service:8000
          predicates:
            - Path=/api/v1/ai/**
          filters:
            - JwtAuthenticationFilter

        - id: user-service
          uri: lb://USER-SERVICE
          predicates:
            - Path=/api/v1/users/**
          filters:
            - JwtAuthenticationFilter

        - id: export-service
          uri: lb://EXPORT-SERVICE
          predicates:
            - Path=/api/v1/export/**
          filters:
            - JwtAuthenticationFilter

        - id: auth-service
          uri: lb://USER-SERVICE
          predicates:
            - Path=/oauth2/**, /api/v1/auth/**
```

#### 3.2.3 Rate Limiting 설정

```yaml
spring:
  cloud:
    gateway:
      default-filters:
        - name: RequestRateLimiter
          args:
            redis-rate-limiter:
              replenishRate: 10      # 초당 요청 수
              burstCapacity: 20      # 버스트 최대
              requestedTokens: 1
```

### 3.3 Knowledge Service

#### 3.3.1 역할

- 지식 CRUD 작업
- 파일 업로드 및 저장
- 버전 관리
- 북마크/좋아요 관리

#### 3.3.2 패키지 구조

```
knowledge-service/
├── src/main/java/com/company/knowledge/
│   ├── KnowledgeServiceApplication.java
│   ├── config/
│   │   ├── JpaConfig.java
│   │   ├── ElasticsearchConfig.java
│   │   └── SecurityConfig.java
│   ├── controller/
│   │   ├── KnowledgeController.java
│   │   ├── BookmarkController.java
│   │   └── FileController.java
│   ├── service/
│   │   ├── KnowledgeService.java
│   │   ├── KnowledgeServiceImpl.java
│   │   ├── FileStorageService.java
│   │   └── VersionService.java
│   ├── repository/
│   │   ├── KnowledgeRepository.java
│   │   ├── ChunkRepository.java
│   │   └── BookmarkRepository.java
│   ├── entity/
│   │   ├── Knowledge.java
│   │   ├── Chunk.java
│   │   ├── Bookmark.java
│   │   └── KnowledgeVersion.java
│   ├── dto/
│   │   ├── KnowledgeCreateRequest.java
│   │   ├── KnowledgeUpdateRequest.java
│   │   └── KnowledgeResponse.java
│   └── exception/
│       ├── KnowledgeNotFoundException.java
│       └── GlobalExceptionHandler.java
└── src/main/resources/
    └── application.yml
```

#### 3.3.3 주요 엔티티

```java
@Entity
@Table(name = "knowledge")
public class Knowledge {
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(nullable = false, length = 500)
    private String title;

    @Column(columnDefinition = "TEXT")
    private String content;

    @Column(name = "document_type", length = 50)
    private String documentType;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "author_id")
    private User author;

    @Column(name = "project_id")
    private UUID projectId;

    @Column(name = "valid_start_date")
    private LocalDate validStartDate;

    @Column(name = "valid_end_date")
    private LocalDate validEndDate;

    @Enumerated(EnumType.STRING)
    private Visibility visibility;

    @ElementCollection
    @CollectionTable(name = "knowledge_tags")
    private Set<String> tags = new HashSet<>();

    @Column(name = "view_count")
    private Integer viewCount = 0;

    @Column(name = "like_count")
    private Integer likeCount = 0;

    @Column(name = "version")
    private Integer version = 1;

    @Column(name = "is_deleted")
    private Boolean isDeleted = false;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    // Getters, Setters, Builders...
}
```

### 3.4 Search Service

#### 3.4.1 역할

- 검색 쿼리 처리
- AI Service 호출 및 결과 집계
- 채팅 세션 관리
- 검색 결과 캐싱

#### 3.4.2 검색 흐름

```
[검색 요청] → [의도 분석] → [검색 전략 결정]
                               │
                 ┌─────────────┼─────────────┐
                 ▼             ▼             ▼
            [ES Vector]  [ES Keyword]   [Neo4j Graph]
                 │             │             │
                 └─────────────┼─────────────┘
                               ▼
                        [RRF 융합]
                               │
                               ▼
                      [답변 합성 (LLM)]
                               │
                               ▼
                        [응답 반환]
```

#### 3.4.3 채팅 컨트롤러

```java
@RestController
@RequestMapping("/api/v1/search")
public class SearchController {

    @Autowired
    private SearchService searchService;

    @PostMapping
    public ResponseEntity<SearchResponse> search(@RequestBody SearchRequest request) {
        SearchResponse response = searchService.hybridSearch(request);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/chat")
    public SseEmitter chatStream(@RequestBody ChatRequest request) {
        SseEmitter emitter = new SseEmitter(60000L);

        CompletableFuture.runAsync(() -> {
            try {
                searchService.streamChatResponse(request, emitter);
            } catch (Exception e) {
                emitter.completeWithError(e);
            }
        });

        return emitter;
    }

    @GetMapping("/conversations/{conversationId}")
    public ResponseEntity<ConversationResponse> getConversation(
            @PathVariable UUID conversationId) {
        return ResponseEntity.ok(searchService.getConversation(conversationId));
    }
}
```

### 3.5 AI Service 연동

> **중요**: SpringBoot 백엔드는 AI 모델(DeepSeek, BGE-M3)과 **직접 연동하지 않습니다**.
> AI 관련 작업은 별도의 Python AI Service가 담당하며, SpringBoot는 해당 서비스의 REST API를 호출합니다.
>
> AI Service의 상세 구현은 [ai_service_implementation_plan.md](./ai_service_implementation_plan.md)를 참조하세요.

#### 3.5.1 아키텍처 흐름

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Backend 아키텍처 흐름                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────┐     ┌─────────────┐     ┌─────────────────────────────────┐   │
│  │ Frontend │────▶│   Gateway   │────▶│     SpringBoot Services         │   │
│  │ (React)  │     │             │     │  (Knowledge, Search, User, ...)│   │
│  └──────────┘     └─────────────┘     └───────────────┬─────────────────┘   │
│                                                       │                      │
│                              ┌────────────────────────┼────────────────────┐ │
│                              │                        │                    │ │
│                              ▼                        ▼                    │ │
│                   ┌─────────────────┐     ┌─────────────────────────────┐  │ │
│                   │   PostgreSQL    │     │      AI Service (Python)    │  │ │
│                   │   (CRUD/SSOT)   │     │      FastAPI + LangGraph    │  │ │
│                   └─────────────────┘     └─────────────┬───────────────┘  │ │
│                                                         │                  │ │
│                              ┌───────────────┬──────────┼──────────┐       │ │
│                              │               │          │          │       │ │
│                              ▼               ▼          ▼          ▼       │ │
│                        ┌──────────┐   ┌──────────┐ ┌─────────┐ ┌───────┐  │ │
│                        │ DeepSeek │   │  BGE-M3  │ │Elastic- │ │ Neo4j │  │ │
│                        │   API    │   │ Embedding│ │ search  │ │ Graph │  │ │
│                        └──────────┘   └──────────┘ └─────────┘ └───────┘  │ │
│                                                                            │ │
└────────────────────────────────────────────────────────────────────────────┘ │
                                                                               │
  ※ SpringBoot는 AI Service의 REST API만 호출                                  │
  ※ LLM, 임베딩, 벡터/그래프 검색은 AI Service가 담당                           │
───────────────────────────────────────────────────────────────────────────────┘
```

#### 3.5.2 역할 분담

| 구분 | 서비스 | 직접 연동 | 담당 기능 |
|------|--------|----------|----------|
| **SpringBoot** | Knowledge Service | PostgreSQL | 지식 CRUD, 파일 저장, 버전 관리 |
| | Search Service | PostgreSQL, Redis | 검색 요청 라우팅, 세션 관리, 캐싱 |
| | User Service | PostgreSQL, Redis | OAuth 인증, 프로필, 권한 관리 |
| | Export Service | - | PDF/Excel/PPT 변환 |
| **Python** | AI Service | DeepSeek API, BGE-M3, ES, Neo4j | VIP 파이프라인, RAG 검색, 엔티티 추출, 답변 합성 |

#### 3.5.3 AI Service API 엔드포인트

| 엔드포인트 | 메서드 | 설명 | 호출 서비스 |
|------------|--------|------|-------------|
| `/api/v1/search/hybrid` | POST | Hybrid 검색 (Vector + Graph) | Search Service |
| `/api/v1/search/chat` | POST | 대화형 검색 (스트리밍) | Search Service |
| `/api/v1/extract/entities` | POST | 엔티티 추출 | Knowledge Service |
| `/api/v1/extract/metadata` | POST | 메타데이터 생성 | Knowledge Service |
| `/api/v1/embed` | POST | 텍스트 임베딩 생성 | Knowledge Service |
| `/health` | GET | 헬스체크 | Gateway |

#### 3.5.4 SpringBoot에서 AI Service 호출

**WebClient 설정:**

```java
@Configuration
public class AiServiceConfig {

    @Value("${ai-service.url}")
    private String aiServiceUrl;

    @Value("${ai-service.timeout:30000}")
    private int timeout;

    @Bean
    public WebClient aiServiceClient() {
        return WebClient.builder()
            .baseUrl(aiServiceUrl)
            .defaultHeader(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
            .clientConnector(new ReactorClientHttpConnector(
                HttpClient.create()
                    .responseTimeout(Duration.ofMillis(timeout))
            ))
            .build();
    }
}
```

**Search Service 연동 예시:**

```java
@Service
@RequiredArgsConstructor
public class SearchServiceImpl implements SearchService {

    private final WebClient aiServiceClient;
    private final ConversationRepository conversationRepository;

    @Override
    public SearchResponse hybridSearch(SearchRequest request) {
        // AI Service REST API 호출
        AiSearchResponse aiResponse = aiServiceClient.post()
            .uri("/api/v1/search/hybrid")
            .bodyValue(AiSearchRequest.builder()
                .query(request.getQuery())
                .filters(request.getFilters())
                .topK(request.getSize())
                .searchType("hybrid")
                .build())
            .retrieve()
            .bodyToMono(AiSearchResponse.class)
            .block();

        // 결과 변환 및 반환
        return SearchResponse.builder()
            .results(mapToSearchResults(aiResponse.getDocuments()))
            .total(aiResponse.getTotal())
            .took(aiResponse.getTook())
            .build();
    }

    @Override
    public Flux<String> streamChatResponse(ChatRequest request) {
        // SSE 스트리밍 호출
        return aiServiceClient.post()
            .uri("/api/v1/search/chat")
            .bodyValue(AiChatRequest.builder()
                .query(request.getQuery())
                .conversationId(request.getConversationId())
                .history(request.getHistory())
                .build())
            .retrieve()
            .bodyToFlux(String.class);
    }
}
```

**Knowledge Service 연동 예시:**

```java
@Service
@RequiredArgsConstructor
public class KnowledgeServiceImpl implements KnowledgeService {

    private final WebClient aiServiceClient;
    private final KnowledgeRepository knowledgeRepository;

    @Override
    @Transactional
    public KnowledgeResponse create(KnowledgeCreateRequest request) {
        // 1. PostgreSQL에 기본 정보 저장
        Knowledge knowledge = Knowledge.builder()
            .title(request.getTitle())
            .content(request.getContent())
            .authorId(request.getAuthorId())
            .build();
        knowledge = knowledgeRepository.save(knowledge);

        // 2. AI Service에 메타데이터 추출 요청 (비동기)
        extractMetadataAsync(knowledge.getId(), request.getContent());

        return KnowledgeResponse.from(knowledge);
    }

    @Async
    protected void extractMetadataAsync(UUID knowledgeId, String content) {
        try {
            // AI Service 호출
            MetadataResponse metadata = aiServiceClient.post()
                .uri("/api/v1/extract/metadata")
                .bodyValue(Map.of("text", content, "document_id", knowledgeId))
                .retrieve()
                .bodyToMono(MetadataResponse.class)
                .block();

            // 추출된 메타데이터로 업데이트
            knowledgeRepository.updateMetadata(knowledgeId, metadata);

        } catch (Exception e) {
            log.error("메타데이터 추출 실패: {}", knowledgeId, e);
        }
    }
}
```

#### 3.5.5 설정 (application.yml)

```yaml
# AI Service 연동 설정
ai-service:
  url: ${AI_SERVICE_URL:http://ai-service:8000}
  timeout: 30000
  retry:
    max-attempts: 3
    backoff: 1000

# Circuit Breaker 설정
resilience4j:
  circuitbreaker:
    instances:
      ai-service:
        register-health-indicator: true
        sliding-window-size: 10
        failure-rate-threshold: 50
        wait-duration-in-open-state: 30s
        permitted-number-of-calls-in-half-open-state: 3
```

#### 3.5.6 장애 대응

```java
@Service
@RequiredArgsConstructor
public class SearchServiceImpl implements SearchService {

    private final WebClient aiServiceClient;

    @CircuitBreaker(name = "ai-service", fallbackMethod = "searchFallback")
    @Retry(name = "ai-service")
    public SearchResponse hybridSearch(SearchRequest request) {
        // AI Service 호출
        return callAiService(request);
    }

    // Fallback: AI Service 장애 시 기본 검색으로 대체
    public SearchResponse searchFallback(SearchRequest request, Throwable t) {
        log.warn("AI Service 장애, 기본 검색으로 대체: {}", t.getMessage());

        // PostgreSQL 기본 검색으로 Fallback
        return basicSearchService.search(request);
    }
}
```

### 3.6 User Service

#### 3.6.1 역할

- 사용자 프로필 관리
- OAuth 2.0 인증 처리
- 역할 기반 권한 관리
- 사용자 설정/선호도 관리

#### 3.6.2 OAuth 2.0 연동

```java
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .csrf(csrf -> csrf.disable())
            .sessionManagement(session ->
                session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/oauth2/**", "/api/v1/auth/**").permitAll()
                .requestMatchers("/api/v1/admin/**").hasRole("ADMIN")
                .anyRequest().authenticated()
            )
            .oauth2Login(oauth2 -> oauth2
                .authorizationEndpoint(endpoint ->
                    endpoint.baseUri("/oauth2/authorization"))
                .userInfoEndpoint(userInfo ->
                    userInfo.userService(customOAuth2UserService))
                .successHandler(oAuth2SuccessHandler)
            )
            .addFilterBefore(jwtAuthenticationFilter,
                UsernamePasswordAuthenticationFilter.class);

        return http.build();
    }
}
```

### 3.7 Export Service

#### 3.7.1 역할

- Excel 변환 (Apache POI)
- PPT 변환 (Apache POI)
- PDF 변환 (iText / PDFBox)
- 템플릿 기반 문서 생성

#### 3.7.2 변환 서비스 인터페이스

```java
public interface ExportService {

    byte[] exportToExcel(ExportRequest request);

    byte[] exportToPpt(ExportRequest request);

    byte[] exportToPdf(ExportRequest request);
}

@Service
public class ExportServiceImpl implements ExportService {

    @Override
    public byte[] exportToExcel(ExportRequest request) {
        try (Workbook workbook = new XSSFWorkbook()) {
            Sheet sheet = workbook.createSheet("Knowledge");

            // 헤더 생성
            Row headerRow = sheet.createRow(0);
            CellStyle headerStyle = createHeaderStyle(workbook);

            String[] headers = {"제목", "작성자", "작성일", "카테고리"};
            for (int i = 0; i < headers.length; i++) {
                Cell cell = headerRow.createCell(i);
                cell.setCellValue(headers[i]);
                cell.setCellStyle(headerStyle);
            }

            // 데이터 행 생성
            List<KnowledgeDto> items = request.getItems();
            for (int i = 0; i < items.size(); i++) {
                Row row = sheet.createRow(i + 1);
                KnowledgeDto item = items.get(i);
                row.createCell(0).setCellValue(item.getTitle());
                row.createCell(1).setCellValue(item.getAuthor());
                row.createCell(2).setCellValue(item.getCreatedAt().toString());
                row.createCell(3).setCellValue(item.getCategory());
            }

            ByteArrayOutputStream out = new ByteArrayOutputStream();
            workbook.write(out);
            return out.toByteArray();
        } catch (IOException e) {
            throw new ExportException("Excel 변환 실패", e);
        }
    }
}
```

---

## 4. API 설계

### 4.1 API 버전 전략

- URL 기반 버전 관리: `/api/v1/...`
- 하위 호환성 유지 원칙
- Deprecated API는 6개월 유예 기간

### 4.2 응답 형식 표준

```json
// 성공 응답
{
  "success": true,
  "data": { ... },
  "message": "성공 메시지",
  "timestamp": "2026-01-14T12:00:00Z"
}

// 에러 응답
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "에러 메시지",
    "details": { ... }
  },
  "timestamp": "2026-01-14T12:00:00Z"
}

// 페이지네이션 응답
{
  "success": true,
  "data": {
    "items": [...],
    "pagination": {
      "page": 1,
      "size": 20,
      "totalPages": 10,
      "totalElements": 195,
      "hasNext": true,
      "hasPrevious": false
    }
  }
}
```

### 4.3 Knowledge API

| 메서드 | 엔드포인트 | 설명 | 권한 |
|--------|-----------|------|------|
| GET | `/api/v1/knowledge` | 목록 조회 | User |
| GET | `/api/v1/knowledge/{id}` | 상세 조회 | User |
| POST | `/api/v1/knowledge` | 등록 | User |
| PUT | `/api/v1/knowledge/{id}` | 수정 | Owner/Manager |
| DELETE | `/api/v1/knowledge/{id}` | 삭제 (소프트) | Owner/Manager |
| GET | `/api/v1/knowledge/my` | 내 지식 목록 | User |
| POST | `/api/v1/knowledge/{id}/like` | 좋아요 토글 | User |
| GET | `/api/v1/knowledge/{id}/versions` | 버전 이력 | User |

#### 4.3.1 지식 등록 API

```yaml
POST /api/v1/knowledge
Content-Type: multipart/form-data

Request:
  - title: string (required) - 제목 (최대 500자)
  - content: string (required) - 본문 (마크다운)
  - documentType: string (optional) - 문서 유형
  - projectId: string (optional) - 프로젝트 ID
  - categoryId: string (required) - 카테고리 ID
  - tags: string[] (optional) - 태그 목록
  - validStartDate: string (optional) - 유효 시작일
  - validEndDate: string (optional) - 유효 종료일
  - visibility: string (optional) - 공개 범위 (PUBLIC, DEPARTMENT, PRIVATE)
  - files: File[] (optional) - 첨부 파일

Response (201 Created):
  {
    "success": true,
    "data": {
      "id": "uuid",
      "title": "지식 제목",
      "status": "processing",
      "message": "지식이 등록되었습니다. AI 분석이 진행 중입니다."
    }
  }
```

### 4.4 Search API

| 메서드 | 엔드포인트 | 설명 | 권한 |
|--------|-----------|------|------|
| POST | `/api/v1/search` | Hybrid 검색 | User |
| POST | `/api/v1/search/chat` | 채팅 검색 (SSE) | User |
| GET | `/api/v1/search/personal` | 개인화 검색 | User |
| GET | `/api/v1/search/suggestions` | 검색어 자동완성 | User |
| POST | `/api/v1/search/experts` | 전문가 찾기 | User |

#### 4.4.1 Hybrid 검색 API

```yaml
POST /api/v1/search
Content-Type: application/json

Request:
  {
    "query": "2024년 프로젝트 A의 React 아키텍처는?",
    "filters": {
      "projectName": "프로젝트 A",
      "documentType": "기술문서",
      "dateRange": {
        "start": "2024-01-01",
        "end": "2024-12-31"
      },
      "categories": {
        "level1": "기술",
        "level2": "개발"
      }
    },
    "searchType": "hybrid",
    "topK": 10,
    "includeGraphContext": true
  }

Response (200 OK):
  {
    "success": true,
    "data": {
      "query": "2024년 프로젝트 A의 React 아키텍처는?",
      "answer": "프로젝트 A의 React 아키텍처는...",
      "results": [
        {
          "chunkId": "chunk_001",
          "documentId": "doc_123",
          "title": "프로젝트 A 기술 문서",
          "text": "...",
          "score": 0.92,
          "metadata": {
            "documentType": "기술문서",
            "projectName": "프로젝트 A",
            "author": "홍길동",
            "summary": "React 기반 프론트엔드 아키텍처 설계 가이드"
          },
          "graphContext": {
            "relatedEntities": ["홍길동", "React", "TypeScript"],
            "community": "프론트엔드 개발팀"
          }
        }
      ],
      "searchMetadata": {
        "searchType": "hybrid",
        "vectorResultsCount": 10,
        "graphResultsCount": 5,
        "fusionMethod": "rrf",
        "latencyMs": 450
      }
    }
  }
```

### 4.5 User API

| 메서드 | 엔드포인트 | 설명 | 권한 |
|--------|-----------|------|------|
| GET | `/api/v1/users/me` | 내 정보 조회 | User |
| PUT | `/api/v1/users/me/preferences` | 설정 변경 | User |
| GET | `/api/v1/users/me/search-history` | 검색 기록 | User |
| DELETE | `/api/v1/users/me/search-history` | 기록 삭제 | User |

### 4.6 Bookmark API

| 메서드 | 엔드포인트 | 설명 | 권한 |
|--------|-----------|------|------|
| GET | `/api/v1/bookmarks` | 북마크 목록 | User |
| POST | `/api/v1/bookmarks` | 북마크 추가 | User |
| DELETE | `/api/v1/bookmarks/{knowledgeId}` | 북마크 제거 | User |
| GET | `/api/v1/bookmarks/folders` | 폴더 목록 | User |
| POST | `/api/v1/bookmarks/folders` | 폴더 생성 | User |

### 4.7 Dashboard API

| 메서드 | 엔드포인트 | 설명 | 권한 |
|--------|-----------|------|------|
| GET | `/api/v1/dashboard` | 대시보드 데이터 | User |
| GET | `/api/v1/dashboard/popular` | 인기 지식 | User |
| GET | `/api/v1/dashboard/trends` | 검색 트렌드 | User |
| GET | `/api/v1/dashboard/stats` | 통계 | User |

### 4.8 Admin API

| 메서드 | 엔드포인트 | 설명 | 권한 |
|--------|-----------|------|------|
| GET | `/api/v1/admin/health` | 시스템 상태 | Admin |
| POST | `/api/v1/admin/reindex` | 재인덱싱 | Admin |
| GET | `/api/v1/admin/users` | 사용자 목록 | Admin |
| PUT | `/api/v1/admin/users/{id}/role` | 역할 변경 | Admin |

---

## 5. 데이터베이스 설계

### 5.1 데이터베이스 역할 분담

| 데이터베이스 | 역할 | 저장 데이터 |
|-------------|------|------------|
| **PostgreSQL** | SSOT (마스터) | 문서, 사용자, 청크, 엔티티, 관계 |
| **Elasticsearch** | 검색 엔진 | 벡터, 메타데이터 (비정규화) |
| **Neo4j** | 지식 그래프 | 엔티티, 관계, 커뮤니티 |
| **Redis** | 캐시/세션 | 세션, 검색 결과 캐시, Rate Limit |

### 5.2 PostgreSQL 스키마

> 상세 DDL은 [상세 설계서](../02_design/01_hybrid_rag_platform_detailed_design.md)의 4.1절 참조

**주요 테이블:**

| 테이블 | 설명 | 주요 컬럼 |
|--------|------|----------|
| `documents` | 문서 마스터 | id, title, document_type, author_id, valid_start/end_date |
| `chunks` | 청크 데이터 | id, document_id, chunk_index, content, token_count |
| `entities` | 엔티티 | id, name, type, description |
| `entity_relationships` | 관계 | source_id, target_id, relationship_type |
| `projects` | 프로젝트 | id, name, code, start/end_date |
| `persons` | 사용자 | id, name, email, department |
| `bookmarks` | 북마크 | user_id, knowledge_id, folder_id |
| `search_history` | 검색 기록 | user_id, query, timestamp |

### 5.3 Elasticsearch 인덱스

**인덱스 이름:** `knowledge-chunks`

```json
{
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0,
    "analysis": {
      "analyzer": {
        "korean_analyzer": {
          "type": "custom",
          "tokenizer": "nori_tokenizer",
          "filter": ["lowercase", "nori_part_of_speech"]
        }
      }
    }
  },
  "mappings": {
    "properties": {
      "chunk_id": { "type": "keyword" },
      "document_id": { "type": "keyword" },
      "text": {
        "type": "text",
        "analyzer": "korean_analyzer"
      },
      "dense_vector": {
        "type": "dense_vector",
        "dims": 1024,
        "index": true,
        "similarity": "cosine"
      },
      "sparse_vector": { "type": "sparse_vector" },
      "metadata": {
        "properties": {
          "document_type": { "type": "keyword" },
          "project_name": { "type": "keyword" },
          "valid_start_date": { "type": "date" },
          "valid_end_date": { "type": "date" },
          "categories": {
            "properties": {
              "level1": { "type": "keyword" },
              "level2": { "type": "keyword" },
              "level3": { "type": "keyword" }
            }
          },
          "summary": { "type": "text" },
          "author": { "type": "keyword" },
          "entities": {
            "properties": {
              "persons": { "type": "keyword" },
              "technologies": { "type": "keyword" }
            }
          }
        }
      }
    }
  }
}
```

### 5.4 Neo4j 그래프 스키마

**노드 타입:**

| 노드 | 속성 | 설명 |
|------|------|------|
| `Entity` | id, name, type, description | 엔티티 (Person, Project, Technology 등) |
| `TextUnit` | id, document_id, chunk_index | 청크 참조 (Slim) |
| `Community` | id, title, summary, level | 커뮤니티 그룹 |
| `Document` | id, title, type | 문서 참조 |

**관계 타입:**

| 관계 | 설명 |
|------|------|
| `RELATED_TO` | 엔티티 간 관계 |
| `MENTIONED_IN` | 엔티티-TextUnit 연결 |
| `BELONGS_TO` | 엔티티-Community 소속 |
| `PART_OF` | TextUnit-Document 소속 |
| `PARENT_OF` | Community 계층 |

### 5.5 데이터 동기화 전략

```
PostgreSQL (SSOT) ──► Elasticsearch (비정규화)
       │
       └───────────► Neo4j (관계)
```

**동기화 트리거:**
1. 문서 생성/수정 시 → ES + Neo4j 자동 동기화
2. 엔티티 추출 완료 시 → Neo4j 업데이트
3. 배치 동기화: 매일 새벽 전체 검증

---

## 6. AI 서비스 설계

### 6.1 VIP 3단계 파이프라인

#### Stage 1: Value (엔티티 채굴)

| 항목 | 명세 |
|------|------|
| **모델** | DeepSeek-Chat (Non-thinking) |
| **입력** | 청크 텍스트 (512 토큰) |
| **출력** | 엔티티, 관계, 메타데이터 |
| **비용** | $0.28/1M 입력, $1.10/1M 출력 |

```python
# 엔티티 추출 프롬프트
ENTITY_EXTRACTION_PROMPT = """
다음 텍스트에서 엔티티, 관계, 메타데이터를 JSON으로 추출하세요.

## 텍스트
{text}

## 추출 지침
- 엔티티 타입: Person, Project, Technology, Organization, Concept
- 관계 타입: CREATED, PARTICIPATED, USES, BELONGS_TO, RELATED_TO
- 메타데이터: document_type, project_name, valid_dates, categories, summary

## JSON 형식
{
  "entities": [...],
  "relationships": [...],
  "metadata": {...}
}
"""
```

#### Stage 2: Intelligent (오케스트레이션)

| 항목 | 명세 |
|------|------|
| **분석** | DeepSeek-Reasoner (Thinking Mode) |
| **실행** | DeepSeek-Chat (Non-thinking) |
| **입력** | 사용자 질의 |
| **출력** | 검색 전략, 필터 조건, 검색 결과 |

```python
# 의도 분석 프롬프트
INTENT_ANALYSIS_PROMPT = """
사용자 질문을 분석하여 JSON으로 반환하세요:

1. intent: 'temporal_comparison' | 'fact_retrieval' | 'relationship_exploration' | 'expert_finding'
2. time_constraints: { "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD" } 또는 null
3. entity_filters: { "project_name": "...", "person": "...", "technology": "..." }
4. search_strategy: 'es_only' | 'neo4j_only' | 'hybrid'
5. complexity: 'simple' | 'complex'

질문: {query}
"""
```

#### Stage 3: Planning (답변 합성)

| 항목 | 명세 |
|------|------|
| **모델** | DeepSeek-Chat |
| **입력** | 검색 결과, 사용자 질의 |
| **출력** | 자연어 답변 |

### 6.2 Hybrid 검색 구현

```python
class HybridSearchEngine:
    """Hybrid 검색 엔진 (Vector + Graph)"""

    def __init__(self, es_client, neo4j_driver, embedding_model):
        self.es = es_client
        self.neo4j = neo4j_driver
        self.embedder = embedding_model

    async def search(
        self,
        query: str,
        filters: dict = None,
        top_k: int = 10,
        search_type: str = "hybrid"
    ) -> SearchResult:
        # 1. 쿼리 임베딩 생성
        query_vector = await self.embedder.embed(query)

        # 2. 병렬 검색 실행
        tasks = []

        if search_type in ["vector", "hybrid"]:
            tasks.append(self._vector_search(query_vector, filters, top_k))

        if search_type in ["graph", "hybrid"]:
            tasks.append(self._graph_search(query, filters, top_k))

        results = await asyncio.gather(*tasks)

        # 3. RRF 융합 (Hybrid인 경우)
        if search_type == "hybrid":
            fused_results = self._rrf_fusion(results)
        else:
            fused_results = results[0]

        return fused_results

    async def _vector_search(self, query_vector, filters, top_k):
        """Elasticsearch 벡터 검색"""
        query = {
            "knn": {
                "field": "dense_vector",
                "query_vector": query_vector,
                "k": top_k,
                "num_candidates": top_k * 2
            }
        }

        if filters:
            query["knn"]["filter"] = self._build_es_filter(filters)

        response = await self.es.search(
            index="knowledge-chunks",
            body=query
        )
        return self._parse_es_response(response)

    async def _graph_search(self, query, filters, top_k):
        """Neo4j 그래프 탐색"""
        cypher = """
        CALL db.index.fulltext.queryNodes('entity_fulltext_idx', $query)
        YIELD node, score
        MATCH (node)-[r:RELATED_TO|MENTIONED_IN*1..2]-(related)
        RETURN DISTINCT related, score
        ORDER BY score DESC
        LIMIT $limit
        """

        async with self.neo4j.session() as session:
            result = await session.run(cypher, query=query, limit=top_k)
            return await result.data()

    def _rrf_fusion(self, results_list, k=60):
        """Reciprocal Rank Fusion"""
        scores = {}

        for results in results_list:
            for rank, item in enumerate(results, 1):
                doc_id = item["document_id"]
                if doc_id not in scores:
                    scores[doc_id] = {"item": item, "score": 0}
                scores[doc_id]["score"] += 1 / (k + rank)

        sorted_items = sorted(
            scores.values(),
            key=lambda x: x["score"],
            reverse=True
        )
        return [item["item"] for item in sorted_items]
```

### 6.3 ReAct Agent (복잡한 질의 처리)

```python
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool

@tool
def vector_search(query: str, filters: dict = None) -> list:
    """벡터 유사도 기반 문서 검색"""
    pass

@tool
def graph_traversal(entity_name: str, depth: int = 2) -> list:
    """지식 그래프에서 관련 엔티티 탐색"""
    pass

@tool
def temporal_filter(start_date: str, end_date: str) -> list:
    """특정 기간 내 유효한 문서 필터링"""
    pass

@tool
def cache_result(key: str, data: dict) -> str:
    """중간 결과를 파일 캐시에 저장"""
    pass

# ReAct Agent 생성
agent = create_react_agent(
    model=deepseek_chat,
    tools=[vector_search, graph_traversal, temporal_filter, cache_result],
    state_modifier="복잡한 질문을 단계별로 분해하여 도구를 활용해 답변하세요."
)
```

### 6.4 스트리밍 응답

```python
from fastapi import Response
from fastapi.responses import StreamingResponse
import asyncio

async def stream_chat_response(query: str, conversation_id: str):
    """SSE 스트리밍 응답"""

    async def generate():
        # 1. 검색 실행
        search_results = await search_engine.search(query)

        # 2. 답변 생성 (스트리밍)
        prompt = build_synthesis_prompt(query, search_results)

        async for chunk in llm.astream(prompt):
            yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
            await asyncio.sleep(0.01)  # 부드러운 스트리밍

        # 3. 소스 문서 전송
        sources = [{"id": r["document_id"], "title": r["title"]}
                   for r in search_results[:3]]
        yield f"data: {json.dumps({'type': 'sources', 'content': sources})}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
```

---

## 7. 인증/인가 설계

### 7.1 OAuth 2.0 Flow

```
┌──────────┐     ┌──────────────┐     ┌──────────────┐
│  Client  │     │   Backend    │     │ OAuth Server │
│ (React)  │     │  (Spring)    │     │  (Keycloak)  │
└────┬─────┘     └──────┬───────┘     └──────┬───────┘
     │                  │                    │
     │  1. Login Click  │                    │
     │ ─────────────────>                    │
     │                  │                    │
     │  2. Redirect to OAuth                 │
     │ <─────────────────────────────────────>
     │                  │                    │
     │  3. User Login   │                    │
     │ ─────────────────────────────────────>│
     │                  │                    │
     │  4. Auth Code    │                    │
     │ <─────────────────────────────────────│
     │                  │                    │
     │  5. Auth Code    │                    │
     │ ─────────────────>                    │
     │                  │                    │
     │                  │  6. Token Exchange │
     │                  │ ──────────────────>│
     │                  │                    │
     │                  │  7. Access/Refresh │
     │                  │ <──────────────────│
     │                  │                    │
     │  8. JWT Token    │                    │
     │ <─────────────────                    │
     │                  │                    │
```

### 7.2 JWT 토큰 구조

```json
// Access Token Payload
{
  "sub": "user_id",
  "email": "user@company.com",
  "name": "홍길동",
  "roles": ["USER", "KNOWLEDGE_MANAGER"],
  "department": "개발팀",
  "iat": 1705200000,
  "exp": 1705203600
}
```

### 7.3 역할 기반 권한

| 역할 | 코드 | 권한 |
|------|------|------|
| **일반 사용자** | USER | 조회, 검색, 본인 지식 CRUD, 북마크 |
| **지식 관리자** | KNOWLEDGE_MANAGER | USER + 모든 지식 수정/삭제, 카테고리 관리 |
| **시스템 관리자** | ADMIN | 모든 권한 + 사용자 관리, 시스템 설정 |

### 7.4 Spring Security 설정

```java
@Configuration
@EnableMethodSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .csrf(csrf -> csrf.disable())
            .sessionManagement(session ->
                session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/oauth2/**", "/api/v1/auth/**").permitAll()
                .requestMatchers("/api/v1/admin/**").hasRole("ADMIN")
                .requestMatchers(HttpMethod.DELETE, "/api/v1/knowledge/**")
                    .hasAnyRole("KNOWLEDGE_MANAGER", "ADMIN")
                .anyRequest().authenticated()
            )
            .addFilterBefore(jwtAuthenticationFilter,
                UsernamePasswordAuthenticationFilter.class);

        return http.build();
    }
}
```

---

## 8. 개발 환경 구성

### 8.1 필요 소프트웨어

| 소프트웨어 | 버전 | 용도 |
|-----------|------|------|
| JDK | 21+ | Java 개발 |
| Python | 3.11+ | AI Service |
| Docker | 24+ | 컨테이너화 |
| Docker Compose | 2.x | 로컬 개발 환경 |
| IntelliJ IDEA | 2024+ | IDE (권장) |
| VS Code | Latest | Python IDE |

### 8.2 로컬 개발 환경 (Docker Compose)

```yaml
version: '3.8'

services:
  # 데이터베이스
  postgres:
    image: postgres:16
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: knowledge
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: secret
    volumes:
      - postgres-data:/var/lib/postgresql/data

  neo4j:
    image: neo4j:5.15
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      NEO4J_AUTH: neo4j/password
      NEO4J_PLUGINS: '["apoc"]'
    volumes:
      - neo4j-data:/data

  elasticsearch:
    image: elasticsearch:8.11.0
    ports:
      - "9200:9200"
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms4g -Xmx4g"
    volumes:
      - es-data:/usr/share/elasticsearch/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  # 서비스
  eureka-service:
    build: ./eureka-service
    ports:
      - "8761:8761"

  config-service:
    build: ./config-service
    ports:
      - "8888:8888"
    depends_on:
      - eureka-service

  gateway-service:
    build: ./gateway-service
    ports:
      - "8080:8080"
    depends_on:
      - eureka-service
      - config-service

  knowledge-service:
    build: ./knowledge-service
    ports:
      - "8081:8081"
    depends_on:
      - postgres
      - eureka-service

  search-service:
    build: ./search-service
    ports:
      - "8082:8082"
    depends_on:
      - elasticsearch
      - ai-service
      - eureka-service

  user-service:
    build: ./user-service
    ports:
      - "8083:8083"
    depends_on:
      - postgres
      - redis
      - eureka-service

  ai-service:
    build: ./ai-service
    ports:
      - "8000:8000"
    environment:
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
    depends_on:
      - elasticsearch
      - neo4j

volumes:
  postgres-data:
  neo4j-data:
  es-data:
```

### 8.3 환경 변수

```bash
# .env
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=knowledge
POSTGRES_USER=admin
POSTGRES_PASSWORD=secret

# Elasticsearch
ELASTICSEARCH_HOST=localhost
ELASTICSEARCH_PORT=9200

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# AI Service
DEEPSEEK_API_KEY=your_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com

# OAuth
OAUTH_CLIENT_ID=knowledge-app
OAUTH_CLIENT_SECRET=secret
OAUTH_ISSUER_URI=http://keycloak:8080/realms/company

# JWT
JWT_SECRET=your_jwt_secret_key
JWT_EXPIRATION=3600
```

---

## 9. 빌드 및 배포

### 9.1 Spring Boot 서비스 Dockerfile

```dockerfile
# Dockerfile (Spring Boot Service)
FROM eclipse-temurin:21-jdk-alpine AS builder

WORKDIR /app
COPY gradle gradle
COPY gradlew .
COPY build.gradle settings.gradle ./
COPY src src

RUN chmod +x gradlew && ./gradlew build -x test

FROM eclipse-temurin:21-jre-alpine

WORKDIR /app
COPY --from=builder /app/build/libs/*.jar app.jar

EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
```

### 9.2 AI Service Dockerfile

```dockerfile
# Dockerfile (AI Service)
FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드
COPY app app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 9.3 CI/CD 파이프라인 (GitHub Actions)

```yaml
# .github/workflows/backend-ci.yml
name: Backend CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up JDK 21
        uses: actions/setup-java@v4
        with:
          java-version: '21'
          distribution: 'temurin'

      - name: Run tests
        run: ./gradlew test

      - name: Upload coverage
        uses: codecov/codecov-action@v3

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v4

      - name: Build Docker images
        run: |
          docker build -t knowledge-service:${{ github.sha }} ./knowledge-service
          docker build -t search-service:${{ github.sha }} ./search-service
          docker build -t ai-service:${{ github.sha }} ./ai-service

      - name: Push to registry
        run: |
          echo ${{ secrets.REGISTRY_PASSWORD }} | docker login -u ${{ secrets.REGISTRY_USER }} --password-stdin
          docker push knowledge-service:${{ github.sha }}
          docker push search-service:${{ github.sha }}
          docker push ai-service:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
      - name: Deploy to server
        uses: appleboy/ssh-action@v1.0.0
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_KEY }}
          script: |
            cd /app
            docker-compose pull
            docker-compose up -d
```

---

## 10. 테스트 전략

### 10.1 테스트 피라미드

```
        /\
       /  \
      / E2E \      5% - 핵심 시나리오
     /________\
    /          \
   / Integration \ 25% - 서비스 간 통합
  /______________\
 /                \
/     Unit Tests   \ 70% - 비즈니스 로직
/__________________\
```

### 10.2 단위 테스트

```java
@ExtendWith(MockitoExtension.class)
class KnowledgeServiceTest {

    @Mock
    private KnowledgeRepository knowledgeRepository;

    @InjectMocks
    private KnowledgeServiceImpl knowledgeService;

    @Test
    @DisplayName("지식 등록 - 정상 케이스")
    void createKnowledge_Success() {
        // Given
        KnowledgeCreateRequest request = new KnowledgeCreateRequest();
        request.setTitle("테스트 지식");
        request.setContent("테스트 내용");

        Knowledge saved = Knowledge.builder()
            .id(UUID.randomUUID())
            .title(request.getTitle())
            .build();

        when(knowledgeRepository.save(any())).thenReturn(saved);

        // When
        KnowledgeResponse response = knowledgeService.create(request);

        // Then
        assertThat(response.getTitle()).isEqualTo("테스트 지식");
        verify(knowledgeRepository).save(any());
    }

    @Test
    @DisplayName("지식 조회 - 존재하지 않는 경우")
    void getKnowledge_NotFound() {
        // Given
        UUID id = UUID.randomUUID();
        when(knowledgeRepository.findById(id)).thenReturn(Optional.empty());

        // When & Then
        assertThrows(KnowledgeNotFoundException.class,
            () -> knowledgeService.getById(id));
    }
}
```

### 10.3 통합 테스트

```java
@SpringBootTest
@AutoConfigureMockMvc
@Testcontainers
class KnowledgeControllerIntegrationTest {

    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16");

    @Autowired
    private MockMvc mockMvc;

    @Test
    @DisplayName("지식 목록 조회 API")
    void getKnowledgeList() throws Exception {
        mockMvc.perform(get("/api/v1/knowledge")
                .header("Authorization", "Bearer " + getTestToken()))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.success").value(true))
            .andExpect(jsonPath("$.data.items").isArray());
    }
}
```

### 10.4 AI Service 테스트

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_hybrid_search():
    """Hybrid 검색 API 테스트"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/search",
            json={
                "query": "React 아키텍처",
                "search_type": "hybrid",
                "top_k": 5
            }
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]["results"]) <= 5

@pytest.mark.asyncio
async def test_entity_extraction():
    """엔티티 추출 테스트"""
    text = "홍길동이 React와 TypeScript로 프로젝트 A를 개발했습니다."

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/extract/entities",
            json={"text": text}
        )

    assert response.status_code == 200
    entities = response.json()["data"]["entities"]

    entity_names = [e["name"] for e in entities]
    assert "홍길동" in entity_names
    assert "React" in entity_names
```

---

## 11. 보안 및 성능

### 11.1 보안 체크리스트

| 항목 | 구현 방법 |
|------|----------|
| **HTTPS 강제** | Gateway에서 HTTP → HTTPS 리다이렉트 |
| **JWT 검증** | 모든 API에서 토큰 검증 |
| **SQL Injection 방지** | JPA 파라미터 바인딩 사용 |
| **XSS 방지** | 입력 값 이스케이핑, CSP 헤더 |
| **CORS 설정** | 허용된 도메인만 접근 |
| **Rate Limiting** | Redis 기반 요청 제한 |
| **입력 검증** | Bean Validation + 커스텀 Validator |
| **민감 정보** | 환경 변수로 관리, Vault 연동 |

### 11.2 성능 최적화

| 영역 | 전략 |
|------|------|
| **검색** | ES 메타데이터 비정규화 (제로 조인) |
| **캐싱** | Redis 검색 결과 캐싱 (TTL: 5분) |
| **DB 연결** | HikariCP 커넥션 풀 |
| **비동기 처리** | 문서 처리는 Celery로 백그라운드 |
| **페이지네이션** | Cursor-based Pagination |
| **N+1 문제** | Fetch Join, EntityGraph |

### 11.3 모니터링

| 도구 | 용도 |
|------|------|
| **Prometheus** | 메트릭 수집 |
| **Grafana** | 대시보드 시각화 |
| **ELK Stack** | 로그 수집 및 분석 |
| **Jaeger** | 분산 추적 |
| **Sentry** | 에러 추적 |

---

## 12. 개발 로드맵

### Phase 1: 기반 구축 (3주)

**Week 1: 인프라 설정**
- Docker Compose 개발 환경 구성
- PostgreSQL, Elasticsearch, Neo4j 스키마 생성
- Eureka, Config Server 설정

**Week 2: 코어 서비스 개발**
- Knowledge Service CRUD
- User Service + OAuth 연동
- Gateway 라우팅 설정

**Week 3: AI Service 기반**
- FastAPI 프로젝트 설정
- DeepSeek 클라이언트 연동
- BGE-M3 임베딩 모델 로드

### Phase 2: 핵심 기능 (4주)

**Week 4-5: 검색 기능**
- Hybrid 검색 구현 (Vector + Graph)
- RRF 융합 로직
- 검색 API 완성

**Week 6-7: AI 파이프라인**
- VIP 3단계 파이프라인 구현
- 엔티티 추출 및 그래프 생성
- 답변 합성 및 스트리밍

### Phase 3: 확장 기능 (3주)

**Week 8-9: 채팅 및 대시보드**
- WebSocket 채팅 구현
- SSE 스트리밍 응답
- Dashboard 통계 API

**Week 10: 문서 변환**
- Excel 변환 (Apache POI)
- PPT 변환
- PDF 변환

### Phase 4: 안정화 (2주)

**Week 11: 테스트 및 최적화**
- 통합 테스트 작성
- 성능 테스트 및 튜닝
- 보안 점검

**Week 12: 배포 준비**
- CI/CD 파이프라인 구축
- 모니터링 설정
- 문서화 완료

---

## 부록

### A. 에러 코드 목록

| 코드 | HTTP | 설명 |
|------|------|------|
| `AUTH_001` | 401 | 인증 실패 |
| `AUTH_002` | 403 | 권한 부족 |
| `KNOW_001` | 404 | 지식 없음 |
| `KNOW_002` | 400 | 유효하지 않은 요청 |
| `SEARCH_001` | 500 | 검색 엔진 오류 |
| `AI_001` | 503 | AI 서비스 불가 |

### B. API 응답 시간 목표

| API | 목표 | P99 |
|-----|------|-----|
| 지식 목록 | 200ms | 500ms |
| 지식 상세 | 100ms | 300ms |
| Hybrid 검색 | 800ms | 1.5s |
| 채팅 첫 토큰 | 500ms | 1s |

### C. 참고 자료

- [상세 설계서](../02_design/01_hybrid_rag_platform_detailed_design.md)
- [프론트엔드 구현 계획서](./frontend_implementation_plan.md)
- [요구사항 명세서](./requirements_specification.md)
- [Spring Cloud 문서](https://spring.io/projects/spring-cloud)
- [LangGraph 문서](https://python.langchain.com/docs/langgraph/)

---

**문서 작성 완료: 2026-01-14**
