# STORY-044: Backend Search Service

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-44 |
| **Epic** | EPIC-002 |
| **Status** | To Do |
| **Priority** | High |
| **Story Points** | 5 |
| **Assignee** | Backend |
| **Sprint** | 3 |

---

## User Story

**As a** Frontend 개발자,
**I want** Backend에서 AI Service를 호출하는 Search API,
**So that** Frontend는 단일 엔드포인트로 검색 기능을 사용할 수 있음.

---

## Acceptance Criteria

- [ ] **Given** 검색 요청, **When** POST /api/v1/search/chat, **Then** AI Service 호출 후 결과 반환
- [ ] **Given** 스트리밍 요청, **When** GET /api/v1/search/chat/stream, **Then** SSE로 응답 스트리밍
- [ ] **Given** AI Service 장애, **When** 검색 요청, **Then** Circuit Breaker 동작 및 fallback 응답
- [ ] **Given** 검색 완료, **When** 응답 반환, **Then** 검색 기록 저장
- [ ] **Given** 인증된 사용자, **When** 검색 요청, **Then** 사용자 ID와 함께 요청

---

## Tasks

- [ ] SearchController 구현
- [ ] SearchService 구현
- [ ] AI Service WebClient 설정
- [ ] SSE 스트리밍 컨트롤러
- [ ] Circuit Breaker (Resilience4j) 설정
- [ ] 검색 기록 저장 로직
- [ ] 단위/통합 테스트 작성

---

## 기술 노트

### SearchController

```java
// backend/backend-service/src/main/java/.../search/SearchController.java
@RestController
@RequestMapping("/api/v1/search")
@RequiredArgsConstructor
@Tag(name = "Search", description = "지식 검색 API")
public class SearchController {

    private final SearchService searchService;

    @PostMapping("/chat")
    @Operation(summary = "채팅 검색", description = "RAG 기반 채팅 검색")
    public ResponseEntity<SearchResponse> chatSearch(
            @Valid @RequestBody SearchRequest request,
            @AuthenticationPrincipal Jwt jwt
    ) {
        String userId = jwt.getSubject();
        SearchResponse response = searchService.search(request, userId);
        return ResponseEntity.ok(response);
    }

    @GetMapping(value = "/chat/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    @Operation(summary = "채팅 검색 (스트리밍)", description = "SSE 기반 스트리밍 검색")
    public Flux<ServerSentEvent<String>> streamChatSearch(
            @RequestParam String query,
            @AuthenticationPrincipal Jwt jwt
    ) {
        String userId = jwt.getSubject();
        SearchRequest request = new SearchRequest(query, null);

        return searchService.streamSearch(request, userId)
                .map(chunk -> ServerSentEvent.<String>builder()
                        .data(chunk)
                        .build())
                .concatWith(Flux.just(
                        ServerSentEvent.<String>builder()
                                .data("{\"type\":\"done\"}")
                                .build()
                ));
    }

    @GetMapping("/history")
    @Operation(summary = "검색 기록", description = "사용자 검색 기록 조회")
    public ResponseEntity<List<SearchHistoryResponse>> getSearchHistory(
            @AuthenticationPrincipal Jwt jwt,
            @RequestParam(defaultValue = "10") int limit
    ) {
        String userId = jwt.getSubject();
        return ResponseEntity.ok(searchService.getHistory(userId, limit));
    }
}
```

### SearchService

```java
// backend/backend-service/src/main/java/.../search/SearchService.java
@Service
@RequiredArgsConstructor
@Slf4j
public class SearchService {

    private final AIServiceClient aiServiceClient;
    private final SearchHistoryRepository historyRepository;

    @CircuitBreaker(name = "aiService", fallbackMethod = "searchFallback")
    public SearchResponse search(SearchRequest request, String userId) {
        // 1. AI Service 호출
        AISearchResponse aiResponse = aiServiceClient.hybridSearch(request);

        // 2. 검색 기록 저장
        saveSearchHistory(userId, request.getQuery(), aiResponse);

        // 3. 응답 변환
        return SearchResponse.builder()
                .answer(aiResponse.getAnswer())
                .sources(aiResponse.getSources().stream()
                        .map(this::convertSource)
                        .toList())
                .responseTime(aiResponse.getResponseTime())
                .build();
    }

    @CircuitBreaker(name = "aiService", fallbackMethod = "streamSearchFallback")
    public Flux<String> streamSearch(SearchRequest request, String userId) {
        return aiServiceClient.streamHybridSearch(request)
                .doOnComplete(() -> {
                    // 스트리밍 완료 후 기록 저장
                    saveSearchHistoryAsync(userId, request.getQuery());
                });
    }

    // Fallback 메서드
    public SearchResponse searchFallback(SearchRequest request, String userId, Throwable t) {
        log.error("AI Service 호출 실패: {}", t.getMessage());
        return SearchResponse.builder()
                .answer("죄송합니다. 검색 서비스가 일시적으로 불가능합니다. 잠시 후 다시 시도해주세요.")
                .sources(Collections.emptyList())
                .error(true)
                .build();
    }

    public Flux<String> streamSearchFallback(SearchRequest request, String userId, Throwable t) {
        log.error("AI Service 스트리밍 실패: {}", t.getMessage());
        return Flux.just("{\"content\":\"검색 서비스가 일시적으로 불가능합니다.\",\"error\":true}");
    }

    private void saveSearchHistory(String userId, String query, AISearchResponse response) {
        SearchHistory history = SearchHistory.builder()
                .userId(userId)
                .query(query)
                .answer(response.getAnswer())
                .sourcesCount(response.getSources().size())
                .responseTimeMs(response.getResponseTime())
                .createdAt(LocalDateTime.now())
                .build();
        historyRepository.save(history);
    }
}
```

### AI Service WebClient

```java
// backend/backend-service/src/main/java/.../client/AIServiceClient.java
@Component
@RequiredArgsConstructor
@Slf4j
public class AIServiceClient {

    private final WebClient webClient;

    public AISearchResponse hybridSearch(SearchRequest request) {
        return webClient.post()
                .uri("/internal/v1/search/hybrid")
                .bodyValue(request)
                .retrieve()
                .bodyToMono(AISearchResponse.class)
                .timeout(Duration.ofSeconds(30))
                .block();
    }

    public Flux<String> streamHybridSearch(SearchRequest request) {
        return webClient.post()
                .uri("/internal/v1/search/chat/stream")
                .bodyValue(request)
                .accept(MediaType.TEXT_EVENT_STREAM)
                .retrieve()
                .bodyToFlux(String.class)
                .timeout(Duration.ofSeconds(60));
    }
}

// WebClient 설정
@Configuration
public class WebClientConfig {

    @Bean
    public WebClient aiServiceWebClient(
            @Value("${ai-service.url}") String aiServiceUrl
    ) {
        return WebClient.builder()
                .baseUrl(aiServiceUrl)
                .defaultHeader(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
                .codecs(configurer -> configurer
                        .defaultCodecs()
                        .maxInMemorySize(10 * 1024 * 1024)) // 10MB
                .build();
    }
}
```

### Resilience4j 설정

```yaml
# application.yml
resilience4j:
  circuitbreaker:
    instances:
      aiService:
        registerHealthIndicator: true
        slidingWindowSize: 10
        minimumNumberOfCalls: 5
        failureRateThreshold: 50
        waitDurationInOpenState: 30s
        permittedNumberOfCallsInHalfOpenState: 3
        automaticTransitionFromOpenToHalfOpenEnabled: true
  retry:
    instances:
      aiService:
        maxAttempts: 3
        waitDuration: 1s
        retryExceptions:
          - java.io.IOException
          - java.util.concurrent.TimeoutException
```

### 영향 범위
- `backend/backend-service/src/main/java/.../search/SearchController.java`
- `backend/backend-service/src/main/java/.../search/SearchService.java`
- `backend/backend-service/src/main/java/.../client/AIServiceClient.java`
- `backend/backend-service/src/main/java/.../config/WebClientConfig.java`
- `backend/backend-service/src/main/resources/application.yml`

---

## 테스트 계획

- [ ] Unit Test: SearchService (Mock AI Client)
- [ ] Unit Test: Circuit Breaker fallback
- [ ] Integration Test: AI Service 연동
- [ ] Integration Test: SSE 스트리밍
- [ ] Load Test: 동시 검색 처리

---

## 참고 자료

- [API 통합 설계서](../../knowledge_service/docs/02_design/api_integration_design.md)
- [Backend 상세 설계서](../../knowledge_service/docs/02_design/backend_detailed_design.md)
- [Resilience4j 가이드](https://resilience4j.readme.io/)
