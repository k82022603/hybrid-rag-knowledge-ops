# Bug Fix Report: Gateway 405 오류 + 그래프 시각화 빈 결과 + Lucene 특수문자

## 기본 정보

| 항목 | 내용 |
|------|------|
| **보고일** | 2026-02-11 |
| **수정자** | Claude (AI Assistant) |
| **우선순위** | High |
| **상태** | 수정 완료, 검증 완료 |
| **커밋** | `eb40cda`, `b4278fa`, (Bug #4: 미커밋) |
| **영향 범위** | Chat 검색 (405 → 200), 그래프 시각화 (빈 결과 → 정상), Subgraph API (500 → 200), Chat 503 Timeout → 200 |
| **관련 이슈** | ISSUE-011 (그래프 패널 엔티티명), SCRUM-101 (graph 소스 태깅) |

---

## 버그 요약

이 보고서는 동일 세션에서 발견/수정된 **연관된 4건의 버그**를 다룹니다.

| # | 버그 | 증상 | 근본 원인 |
|---|------|------|-----------|
| 1 | Gateway 405 Method Not Allowed | POST `/api/v1/search/chat` → 405 | FallbackController 어노테이션 + Circuit Breaker 설정 |
| 2 | 그래프 시각화 빈 결과 | 그래프 아이콘 클릭 → 빈 그래프 | RRF 융합에서 `matched_entities` 유실 |
| 3 | Subgraph API Lucene 파싱 오류 | `CI/CD` → 500 Server Error | Neo4j Fulltext 쿼리에 Lucene 특수문자 미이스케이프 |
| 4 | AI Service 503 Timeout | 특정 프롬프트에서 503 반환 | Gateway/Resilience4j 타임아웃(60s) < AI 처리시간(91s) |

---

## Bug #1: Gateway 405 Method Not Allowed

### 증상

```
POST /api/v1/search/chat HTTP/1.1

→ 405 Method Not Allowed
{
  "timestamp": "2026-02-11T...",
  "path": "/fallback/ai-service",
  "status": 405,
  "error": "Method Not Allowed"
}
```

- `/api/v1/search/chat`에 POST 요청 시 405 반환
- 에러 응답이 Spring Boot 형식 (FastAPI가 아님) → Gateway 레벨 문제
- AI Service 직접 호출 (`:8000`) 시에는 정상 200 OK

### 원인 분석

**2가지 원인**이 복합 작용:

#### 원인 1: FallbackController 어노테이션 스택 오류

```mermaid
flowchart TB
    subgraph Before["수정 전 (WebFlux 비호환)"]
        A1["@GetMapping('/ai-service')"] --> B1["@PostMapping('/ai-service')"]
        B1 --> C1["public Mono<...> aiServiceFallback()"]
        C1 -.->|"WebFlux: GET만 등록됨"| D1["POST 요청 → 405"]
    end

    subgraph After["수정 후 (WebFlux 호환)"]
        A2["@RequestMapping(value='/ai-service',<br/>method={GET, POST})"] --> C2["public Mono<...> aiServiceFallback()"]
        C2 -->|"GET/POST 모두 지원"| D2["POST 요청 → 503 (정상 fallback)"]
    end

    style D1 fill:#f66,color:#fff
    style D2 fill:#6c6,color:#fff
```

Spring WebFlux에서 `@GetMapping` + `@PostMapping`을 같은 메서드에 스택하면 **마지막 어노테이션만 등록**됩니다.
`@GetMapping`이 먼저 처리되어 GET만 등록 → POST 요청 시 405 반환.

#### 원인 2: Circuit Breaker 임계값 과소 설정

```yaml
# 수정 전
ai-config:
  slow-call-duration-threshold: 5s   # LLM 호출은 항상 >5s
  sliding-window-size: 5
  slow-call-rate-threshold: 80

# 수정 후
ai-config:
  slow-call-duration-threshold: 30s   # LLM 응답 대기 충분
  sliding-window-size: 10
  slow-call-rate-threshold: 90
```

LLM 기반 Chat 검색은 **평균 15~50초** 소요되므로, `slow-call-duration-threshold: 5s`는 모든 호출을 "느린 호출"로 판정합니다.
5건 중 80%가 느리면 → Circuit Breaker OPEN → Fallback 라우팅 → 405 (원인 1과 결합).

```mermaid
sequenceDiagram
    participant Client
    participant Nginx
    participant Gateway
    participant CB as Circuit Breaker
    participant Fallback
    participant AI as AI Service

    Note over CB: slow-call-threshold: 5s<br/>모든 LLM 호출 >5s

    Client->>Nginx: POST /api/v1/search/chat
    Nginx->>Gateway: proxy_pass
    Gateway->>CB: 요청 전달
    CB-->>CB: OPEN 상태 (slow rate > 80%)
    CB->>Fallback: fallback 라우팅
    Fallback-->>Gateway: 405 (GET만 등록됨)
    Gateway-->>Nginx: 405 Method Not Allowed
    Nginx-->>Client: 405 응답
```

### 수정 내용

| 파일 | 변경 |
|------|------|
| `FallbackController.java` | 6개 fallback + generic → `@RequestMapping(method = {GET, POST})` |
| `application.yml` | `slow-call-duration-threshold: 30s`, `sliding-window-size: 10`, `slow-call-rate-threshold: 90` |

### 검증

```
POST /api/v1/search/chat (via nginx full path)
→ 200 OK, 51.6s, answer 2544자
```

---

## Bug #2: 그래프 시각화 빈 결과

### 증상

검색 결과에서 `source_type: "graph"` 항목의 그래프 아이콘 클릭 시:

```json
POST /api/v1/graph/subgraph
{
  "entity_name": "AI_Orchestration_Explained_The_What_Why__How_for_2024",
  "depth": 1, "limit": 15
}

→ {"center": "AI_Orchestration_Explained_The_What_Why__How_for_2024",
   "nodes": [], "edges": [], "node_count": 0}
```

`entity_name`에 **문서 제목**이 전달되어 Neo4j 엔티티 검색 실패 → 빈 그래프.

### 원인 분석 (3단계)

```mermaid
flowchart TB
    subgraph Root["근본 원인: RRF 융합에서 matched_entities 유실"]
        direction TB
        V["Vector Search<br/>chunk_id: abc123<br/>metadata: {title: '...'}"]
        G["Graph Search<br/>chunk_id: abc123<br/>metadata: {matched_entities: ['Kubernetes']}"]

        V -->|"1st: results_map에 저장"| RRF["RRF Fusion<br/>results_map[abc123] = Vector 결과"]
        G -->|"2nd: 이미 존재 → 무시됨"| RRF

        RRF -->|"matched_entities 없음"| BUILD["build_sources_from_results()"]
        BUILD -->|"fallback: 제목에서 추출"| TITLE["related_entities =<br/>['AI_Orchestration_Explained...']"]
        TITLE -->|"문서 제목으로 subgraph 조회"| NEO["Neo4j fulltext 검색"]
        NEO -->|"엔티티 아님 → 매칭 실패"| EMPTY["nodes: [], edges: []"]
    end

    style V fill:#4a9,color:#fff
    style G fill:#a64,color:#fff
    style EMPTY fill:#f66,color:#fff
```

#### 원인 1: RRF 융합에서 metadata 유실

`_rrf_fusion()` 메서드에서 동일 `chunk_id`가 여러 소스에 존재할 때, **첫 번째 소스의 결과만 저장**합니다.

```python
# search.py - _rrf_fusion()
for result in result_list:
    if chunk_id not in results_map:
        results_map[chunk_id] = result   # 첫 번째만 저장
```

소스 처리 순서: **Vector(1st) → Keyword(2nd) → Graph(3rd)**

| 단계 | 처리 | 결과 |
|------|------|------|
| Vector 처리 | `results_map["abc123"] = vector_result` | `metadata: {title: "..."}` (matched_entities 없음) |
| Graph 처리 | `"abc123" in results_map` → **스킵** | Graph의 `matched_entities: ["Kubernetes"]` **유실** |
| source 업데이트 | `result.source = "graph"` (RRF 점수 기반) | source는 graph이지만 metadata는 vector 것 |

#### 원인 2: 제목 → 엔티티 fallback 부정확

`_extract_entities_from_title()`이 제목 전체를 엔티티로 반환:

```python
# 수정 전
def _extract_entities_from_title(title):
    if not title or _is_filename(title):
        return []
    return [title]  # "AI_Orchestration_Explained_..." 그대로 반환
```

#### 원인 3: subgraph API fallback 부재

`query_subgraph()`가 fulltext 인덱스에서 못 찾으면 즉시 빈 결과 반환.
문서 제목이나 부분 매칭 시도 없이 포기.

### 수정 내용

```mermaid
flowchart TB
    subgraph Fix["수정 후 데이터 흐름"]
        direction TB
        V2["Vector Search<br/>chunk: abc123<br/>metadata: {title}"]
        G2["Graph Search<br/>chunk: abc123<br/>metadata: {matched_entities: ['Kubernetes']}"]

        V2 -->|"1st 저장"| RRF2["RRF Fusion"]
        G2 -->|"2nd: matched_entities 병합!"| RRF2

        RRF2 -->|"matched_entities 보존"| BUILD2["build_sources_from_results()"]
        BUILD2 -->|"matched_entities 사용"| ENT2["related_entities =<br/>['Kubernetes']"]
        ENT2 -->|"실제 엔티티명"| NEO2["Neo4j subgraph 조회"]
        NEO2 -->|"성공"| GRAPH["nodes: 3, edges: 3"]
    end

    style G2 fill:#6a6,color:#fff
    style GRAPH fill:#6c6,color:#fff
```

#### Fix 1: RRF 융합 — matched_entities 병합 (`search.py`)

```python
if chunk_id not in results_map:
    results_map[chunk_id] = result
else:
    # ISSUE-011: graph 소스의 matched_entities 병합
    existing = results_map[chunk_id]
    new_entities = result.metadata.get("matched_entities", [])
    if new_entities and not existing.metadata.get("matched_entities"):
        existing.metadata["matched_entities"] = new_entities
```

#### Fix 2: 제목에서 키워드 추출 개선 (`rag_workflow.py`)

```python
# 수정 후: 제목을 분리하여 개별 키워드 추출
def _extract_entities_from_title(title):
    # "AI_Orchestration_Explained_The_What_Why__How_for_2024"
    # → ['AI', 'Orchestration'] (불용어/날짜 제거)

    parts = re.split(r'[_\-\s]+', title)
    # 불용어 필터링 (the, for, explained, ...)
    # 날짜 필터링 (20250108, 2024, ...)
    # 한글 키워드 추출
    return entities[:5]
```

| 입력 (제목) | 수정 전 | 수정 후 |
|------------|---------|---------|
| `AI_Orchestration_Explained_The_What_Why__How_for_2024` | `["AI_Orchestration_Explained_..."]` | `["AI", "Orchestration"]` |
| `아키텍처팀 AI프로젝트 이해 워크샵-20250108` | `["아키텍처팀 AI프로젝트 이해 워크샵-20250108"]` | `["아키텍처팀", "AI프로젝트", "이해", "워크샵", "프로젝트"]` |
| `KMS_설계서.pdf` | `[]` (파일명 감지) | `[]` (파일명 감지) |

#### Fix 3: subgraph API 3단계 fallback (`neo4j_storage.py`)

```mermaid
flowchart LR
    REQ["entity_name 입력"] --> FT["1. Fulltext Index<br/>entity_fulltext_idx"]
    FT -->|"Found"| OK["서브그래프 반환"]
    FT -->|"Miss"| CT["2. CONTAINS 매칭<br/>center.name CONTAINS entity"]
    CT -->|"Found"| OK
    CT -->|"Miss"| DT["3. Document Title 매칭<br/>d.title → MENTIONED_IN → entity"]
    DT -->|"Found"| OK
    DT -->|"Miss"| EMPTY["빈 결과 반환"]

    style FT fill:#4a9,color:#fff
    style CT fill:#da5,color:#fff
    style DT fill:#a64,color:#fff
    style OK fill:#6c6,color:#fff
```

| Fallback 단계 | 쿼리 전략 | 대상 |
|--------------|----------|------|
| 1. Fulltext | `db.index.fulltext.queryNodes("entity_fulltext_idx", ...)` | 정확한 엔티티명 |
| 2. CONTAINS | `center.name CONTAINS $name OR $name CONTAINS center.name` | 부분 매칭 |
| 3. Document Title | `Document.title` → `PART_OF` → `Chunk` → `MENTIONED_IN` → `Entity` | 문서에서 역추적 |

### 검증

#### 수정 전

```json
// Chat API sources
{
  "graph_context": {
    "related_entities": ["AI_Orchestration_Explained_The_What_Why__How_for_2024"]
  }
}
// → subgraph: nodes=0, edges=0
```

#### 수정 후

```json
// Chat API sources (캐시 클리어 후)
{
  "graph_context": {
    "related_entities": ["CI/CD", "Kubernetes", "CI/CD 파이프라인"]
  }
}
// → subgraph("Kubernetes"): nodes=3, edges=3
//   - Kubernetes (Technology)
//   - test_doc_2.txt (Knowledge)
//   - MSA 차세대 플랫폼 전환 프로젝트 (Topic)
```

---

## Bug #3: Subgraph API Lucene 특수문자 파싱 오류

### 증상

Bug #2 수정 후, `CI/CD`와 같은 Lucene 특수문자가 포함된 엔티티명으로 subgraph 조회 시:

```
POST /api/v1/graph/subgraph
{"entity_name": "CI/CD", "depth": 1, "limit": 15}

→ 500 Internal Server Error
{
  "detail": "Knowledge Graph 조회 실패: 서브그래프 조회 실패:
    {code: Neo.ClientError.Procedure.ProcedureCallFailed}
    TokenMgrError: Lexical error at line 1, column 6.
    Encountered: <EOF> after prefix \"/CD\" (in lexical state 2)"
}
```

### 원인 분석

```mermaid
flowchart LR
    INPUT["entity_name = 'CI/CD'"] --> FT["db.index.fulltext.queryNodes()"]
    FT --> LUCENE["Lucene Query Parser"]
    LUCENE -->|"'/' = 정규식 구분자"| PARSE["'/CD' → 정규식으로 해석 시도"]
    PARSE -->|"EOF 도달"| ERROR["TokenMgrError:<br/>Lexical error"]

    style ERROR fill:#f66,color:#fff
```

Neo4j의 `db.index.fulltext.queryNodes()`는 내부적으로 **Apache Lucene Query Parser**를 사용합니다.
Lucene에서 `/`는 정규식 구분자로 해석되어, `CI/CD`가 `CI` + `/CD`(불완전 정규식)로 파싱됩니다.

#### Lucene 특수문자 목록

```
+ - && || ! ( ) { } [ ] ^ " ~ * ? : \ /
```

이 중 어느 것이라도 엔티티명에 포함되면 동일한 파싱 오류가 발생합니다.

### 수정 내용

`neo4j_storage.py`의 `query_subgraph()` 메서드에 **Lucene 이스케이프 함수** 추가:

```python
def _escape_lucene(text: str) -> str:
    """Lucene 쿼리 특수문자를 이스케이프합니다."""
    special = r'+-&&||!(){}[]^"~*?:\/'
    escaped = []
    for ch in text:
        if ch in special:
            escaped.append(f"\\{ch}")
        else:
            escaped.append(ch)
    return "".join(escaped)

# fulltext 쿼리 호출 전 이스케이프 적용
escaped_entity_name = _escape_lucene(entity_name)
# db.index.fulltext.queryNodes("entity_fulltext_idx", escaped_entity_name)
```

```mermaid
flowchart LR
    INPUT2["entity_name = 'CI/CD'"] --> ESC["_escape_lucene()"]
    ESC -->|"'CI\\/CD'"| FT2["db.index.fulltext.queryNodes()"]
    FT2 --> LUCENE2["Lucene Query Parser"]
    LUCENE2 -->|"'\\/' = 리터럴 '/'"| OK["정상 검색 → 3 nodes, 3 edges"]

    style ESC fill:#da5,color:#fff
    style OK fill:#6c6,color:#fff
```

| 입력 | 이스케이프 전 | 이스케이프 후 | 결과 |
|------|-------------|-------------|------|
| `CI/CD` | `CI/CD` (정규식 오류) | `CI\/CD` | 3 nodes, 3 edges |
| `C++` | `C++` (AND 연산자 오류) | `C\+\+` | 정상 검색 |
| `"마이크로서비스"` | 구문 검색 오류 | `\"마이크로서비스\"` | 정상 검색 |

### 검증

```json
// 수정 전
POST /api/v1/graph/subgraph {"entity_name": "CI/CD"}
→ 500 Internal Server Error (TokenMgrError)

// 수정 후
POST /api/v1/graph/subgraph {"entity_name": "CI/CD"}
→ 200 OK
{
  "center": "CI/CD",
  "nodes": [
    {"name": "CI/CD", "type": "Topic"},
    {"name": "test_doc_2.txt", "type": "Knowledge"},
    {"name": "MSA 차세대 플랫폼 전환 프로젝트", "type": "Topic"}
  ],
  "edges": [...],
  "node_count": 3
}
```

---

## Bug #4: AI Service 503 Timeout (Chat 검색)

### 증상

```
POST /api/v1/search/chat HTTP/1.1
→ 503 Service Unavailable
{
  "error": "AI service is temporarily unavailable",
  "message": "Search and RAG functionality is currently limited."
}
```

특정 프롬프트에서 AI 서비스가 타임아웃으로 503 반환.

### 원인 분석

```mermaid
sequenceDiagram
    participant Client
    participant Nginx
    participant Gateway
    participant AI as AI Service

    Note over AI: CPU 기반 처리 (GPU 없음)

    Client->>Nginx: POST /api/v1/search/chat
    Nginx->>Gateway: proxy_pass (120s timeout)
    Gateway->>AI: forward (60s timeout)
    AI->>AI: Embedding 모델 로드 (46s)
    AI->>AI: Hybrid Search + Reranking (9s)
    Note over Gateway: 60초 경과 → TimeLimiter timeout!
    Gateway-->>Nginx: 503 (fallback)
    Nginx-->>Client: 503 Service Unavailable
    AI->>AI: LLM 생성 (35s) - 이미 끊김
    Note over AI: 총 91초 소요 (Gateway는 60초에서 포기)
```

**근본 원인**: CPU 환경에서의 처리 시간이 Gateway/Resilience4j 타임아웃(60초)을 초과

| 단계 | Cold Start | Warm |
|------|-----------|------|
| 임베딩 모델 로드 | **46초** | 0초 (캐시) |
| Hybrid Search + Reranking | 9초 | 2초 (캐시) |
| LLM 생성 | 35초 | 31초 |
| **합계** | **91초** | **34초** |

### 수정 내용

4개 타임아웃을 120초로 통일 (Nginx `/api/v1/search`와 일치):

| 설정 | 파일 | 변경 |
|------|------|------|
| Gateway `response-timeout` | gateway application.yml | 60s → **120s** |
| Resilience4j `ai-service TimeLimiter` | gateway application.yml | 60s → **120s** |
| Resilience4j `slow-call-duration-threshold` | gateway application.yml | 30s → **45s** |
| Backend WebClient `ai-service.timeout` | backend application.yml | 60s → **120s** |

### 검증

```
# Redis FLUSH + AI Service 재시작 (True Cold Start)
POST /api/v1/search/chat → 200 OK, 62.2s

# Warm (캐시 히트)
POST /api/v1/search/chat → 200 OK, 33.7s
```

---

## 수정 파일 목록

| 파일 | 변경 | 버그 |
|------|------|------|
| `gateway/.../FallbackController.java` | `@RequestMapping(method={GET,POST})` 통일 | #1 |
| `gateway/.../application.yml` | Circuit Breaker 임계값 조정 | #1 |
| `src/app/services/search.py` | RRF 융합 시 `matched_entities` 병합 | #2 |
| `src/app/agents/rag_workflow.py` | `_extract_entities_from_title()` 키워드 분리 | #2 |
| `src/app/storage/neo4j_storage.py` | `query_subgraph` 3단계 fallback 추가 | #2 |
| `src/app/storage/neo4j_storage.py` | `_escape_lucene()` 함수 추가, fulltext 쿼리 이스케이프 | #3 |
| `gateway/.../application.yml` | `response-timeout` 60→120s, TimeLimiter 60→120s | #4 |
| `backend/.../application.yml` | `ai-service.timeout` 60→120s | #4 |

---

## 재발 방지 대책

### 단기

| 항목 | 조치 |
|------|------|
| **Circuit Breaker 모니터링** | Grafana 대시보드에 CB 상태 (OPEN/HALF_OPEN/CLOSED) 패널 추가 권장 |
| **Redis 캐시 주의** | 코드 수정 후 `FLUSHDB`로 캐시 클리어 필요 (오래된 메타데이터 반환 방지) |
| **Lucene 이스케이프** | Neo4j fulltext 쿼리 사용 시 반드시 `_escape_lucene()` 적용 (새 fulltext 쿼리 추가 시 체크) |

### 중기

| 항목 | 조치 |
|------|------|
| **E2E 테스트 추가** | Chat → Graph 클릭 → Subgraph 비어있지 않음 검증 |
| **RRF 융합 단위 테스트** | Vector+Graph 중복 chunk의 `matched_entities` 보존 검증 |
| **FallbackController 테스트** | POST 메서드 지원 여부 WebTestClient로 검증 |
| **Lucene 특수문자 테스트** | `CI/CD`, `C++`, `"quoted"` 등 특수문자 포함 엔티티 subgraph 조회 검증 |

### 장기

| 항목 | 조치 |
|------|------|
| **KG 추출 확장** | 현재 5개 Knowledge 노드만 엔티티 연결 → 전체 문서에 Entity Extraction 수행 |
| **Graph 품질 대시보드** | 문서별 엔티티 연결 수 모니터링 (연결 없는 문서 식별) |

---

## 참고

- [Circuit Breaker 운영 매뉴얼](./12_circuit_breaker_operations_manual.md)
- [Neo4j 쿼리 가이드](./15_neo4j_query_guide.md)
- [Graph Search 구현 문서](../03_implementation/graph_search_implementation_2026-02-07.md)
