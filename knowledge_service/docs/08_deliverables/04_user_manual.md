# 사용자 매뉴얼

**시스템**: Hybrid RAG Knowledge Platform
**대상**: 시스템 사용자 (검색, 문서 관리)
**작성일**: 2026-02-18
**버전**: 1.0

---

## 목차

1. [시스템 접속](#1-시스템-접속)
2. [검색 기능](#2-검색-기능)
3. [문서 관리](#3-문서-관리)
4. [Knowledge Graph 탐색](#4-knowledge-graph-탐색)
5. [대화형 검색 (Chat)](#5-대화형-검색-chat)
6. [FAQ / 트러블슈팅](#6-faq--트러블슈팅)

---

## 1. 시스템 접속

### 1.1 브라우저 접속

웹 브라우저에서 다음 URL로 접속합니다.

| 환경 | URL |
|------|-----|
| 프론트엔드 (메인) | `http://localhost` |
| AI Service API 문서 (Swagger UI) | `http://localhost:8000/docs` |
| Kibana (데이터 시각화) | `http://localhost:5601` |
| Neo4j Browser (그래프 탐색) | `http://localhost:7474` |

> **권장 브라우저**: Chrome, Edge, Firefox 최신 버전

### 1.2 로그인 방법

시스템은 2가지 인증 방식을 지원합니다.

#### 방법 1: AI Service 직접 로그인

프론트엔드 로그인 화면에서 이메일/비밀번호를 입력합니다.

| 항목 | 값 |
|------|-----|
| 이메일 | `admin@example.com` |
| 비밀번호 | `admin123!` |

로그인 성공 시 JWT 토큰이 발급되며, 이후 모든 API 요청에 자동으로 포함됩니다.
토큰 만료 시 자동으로 갱신(refresh)됩니다.

#### 방법 2: Keycloak SSO 로그인

프론트엔드에서 "SSO 로그인" 버튼을 클릭하면 Keycloak 인증 화면으로 이동합니다.

| 계정 유형 | ID | 비밀번호 |
|----------|-----|---------|
| 관리자 | `admin` | `admin123` |
| 테스트 사용자 | `test` | `password123` |

SSO 로그인은 Keycloak Realm `hybrid-rag`에서 관리됩니다.

### 1.3 인증 구조

```
사용자 요청
    |
    +-- Bearer Token 포함?
    |       |
    |       +-- HS256 (자체 JWT) --> AI Service 직접 인증
    |       +-- RS256 (Keycloak) --> SSO 인증
    |
    +-- X-Auth-* 헤더? --> API Gateway 경유 인증
    |
    +-- 없음 --> 401 Unauthorized
```

---

## 2. 검색 기능

시스템은 4가지 검색 방식을 제공하며, **하이브리드 검색**이 가장 높은 정확도를 보입니다.

### 2.1 키워드 검색

**Elasticsearch BM25 + Nori 한국어 형태소 분석** 기반 전문 검색입니다.

- **특징**: 정확한 단어 매칭에 강함
- **적합한 경우**: 특정 용어, 문서명, 기술 키워드 검색
- **분석기**: Nori 한국어 형태소 분석기가 "프로젝트관리" 같은 복합어를 "프로젝트" + "관리"로 분리하여 검색

**사용 예시**:

```
검색어: "프로젝트 관리"
결과: BM25 점수 기반으로 정렬된 문서 청크 목록
```

**결과 해석**:
- `score`: BM25 관련성 점수 (높을수록 키워드 매칭이 강함)
- `source_type`: `keyword`
- `highlight`: 검색어가 매칭된 부분이 `<em>` 태그로 강조됨

### 2.2 시맨틱 검색

**BGE-M3 임베딩 모델** 기반 벡터 유사도 검색입니다.

- **특징**: 의미적으로 유사한 문서를 찾음 (단어가 달라도 의미가 같으면 검색)
- **적합한 경우**: "비용 절감 방안" 검색 시 "예산 최적화", "경비 축소" 등도 검색
- **벡터**: 1024차원 Dense Vector (Elasticsearch kNN)

**사용 예시**:

```
검색어: "시스템 성능 개선 방법"
결과: 벡터 코사인 유사도 기반 정렬
```

**결과 해석**:
- `score`: 코사인 유사도 (0~1, 1에 가까울수록 의미적으로 유사)
- `source_type`: `vector`

### 2.3 하이브리드 검색 (권장)

**4-Way 통합 검색**으로, 가장 높은 검색 품질을 제공합니다.

```
검색 파이프라인:

Dense Vector (BGE-M3 1024d)  ─┐
Sparse Vector (BGE-M3)       ─┤
BM25 Keyword (Nori)          ─┼── RRF 융합 ── BGE-Reranker ── 최종 결과
Graph Search (Neo4j)          ─┘
```

- **RRF (Reciprocal Rank Fusion)**: 4개 검색 결과의 순위를 통합하여 최종 점수 산출
- **BGE-Reranker**: RRF 결과를 Cross-encoder로 재순위하여 정밀도 향상
- **Graph Search**: Knowledge Graph에서 엔티티 관계 기반 검색 (MENTIONS, RELATED_TO)

**사용 예시**:

```
검색어: "프로젝트 관리"
옵션: useGraph=true, useVector=true
```

**결과 해석**:
- `score`: Reranker 점수 (0~1, 높을수록 질의와 관련도가 높음)
- `source_type`: 가장 높은 기여를 한 소스 (vector, keyword, graph)
- `contributing_sources`: RRF 융합에 기여한 소스 목록 (예: ["vector", "keyword", "sparse"])
- `metadata.rrf_score`: RRF 원본 점수
- `metadata.rerank_score`: Reranker 재순위 점수
- `metadata.matched_entities`: Graph Search에서 매칭된 엔티티 목록

### 2.4 검색 결과 해석

검색 결과의 각 항목은 다음 정보를 포함합니다.

| 필드 | 설명 |
|------|------|
| `title` | 원본 문서 제목 |
| `content` | 매칭된 청크 내용 (문서의 일부분) |
| `score` | 관련성 점수 |
| `source_type` | 검색 소스 (vector, keyword, graph) |
| `contributing_sources` | 하이브리드 검색 시 기여 소스 목록 |
| `metadata.file_name` | 원본 파일명 |
| `metadata.file_path` | 파일 경로 |
| `metadata.extension` | 파일 확장자 (.pdf, .docx, .pptx 등) |
| `has_embedding` | 벡터 임베딩 존재 여부 |

### 2.5 검색 팁

| 상황 | 권장 검색 방식 |
|------|-------------|
| 정확한 용어/문서명 검색 | 키워드 검색 |
| 의미가 비슷한 문서 탐색 | 시맨틱 검색 |
| 최고 품질 결과가 필요할 때 | 하이브리드 검색 |
| "A와 B의 관계"를 알고 싶을 때 | 하이브리드 검색 (Graph 활성화) |

---

## 3. 문서 관리

### 3.1 문서 목록 조회

시스템에 등록된 문서 목록을 확인할 수 있습니다.

**지원 필터**:
- `limit`: 페이지당 표시할 문서 수 (기본 10)
- `offset`: 시작 위치 (페이징)
- `status`: 처리 상태 필터 (completed, processing, failed)

**문서 정보**:

| 필드 | 설명 |
|------|------|
| `document_id` | 문서 고유 UUID |
| `filename` | 원본 파일명 |
| `format` | 문서 형식 (pdf, docx, pptx, hwp, md, txt, html) |
| `size_bytes` | 파일 크기 |
| `status` | 처리 상태 |
| `created_at` | 업로드 시간 |

### 3.2 문서 처리 상태

| 상태 | 설명 |
|------|------|
| `pending` | 업로드 완료, 처리 대기 중 |
| `processing` | 파싱/청킹/임베딩 진행 중 |
| `completed` | 처리 완료, 검색 가능 |
| `failed` | 처리 실패 (재시도 가능) |

### 3.3 지원 문서 형식

| 형식 | 확장자 | 최대 크기 |
|------|--------|----------|
| PDF | `.pdf` | 100MB |
| Word | `.docx` | 50MB |
| PowerPoint | `.pptx` | 100MB |
| 한글 | `.hwp` | 50MB |
| Markdown | `.md` | 10MB |
| 텍스트 | `.txt` | 10MB |
| HTML | `.html` | 10MB |
| Jupyter | `.ipynb` | 10MB |

### 3.4 문서 업로드

프론트엔드에서 파일을 드래그앤드롭하거나 파일 선택기를 통해 업로드합니다.
업로드된 문서는 MinIO 오브젝트 스토리지에 저장되고, ETL 파이프라인을 통해 자동 처리됩니다.

---

## 4. Knowledge Graph 탐색

### 4.1 개요

시스템은 169,886개의 엔티티 노드와 775,366개의 관계를 가진 Knowledge Graph를 구축하고 있습니다.

**엔티티 유형**:
- Entity: 일반 엔티티 (기술, 개념, 시스템 등)
- Technology: 기술 관련 엔티티
- Person: 인물 엔티티

**관계 유형**:
- `MENTIONS`: 문서가 엔티티를 언급
- `RELATED_TO`: 엔티티 간 관련성
- `HAS_ENTITY`: 청크가 엔티티를 포함
- `PART_OF`: 부분-전체 관계

### 4.2 엔티티 조회

특정 엔티티의 상세 정보를 조회합니다.

- 엔티티 이름, 유형, 설명
- Neo4j 라벨, 추가 속성

### 4.3 서브그래프 탐색

중심 엔티티를 기준으로 연결된 노드와 관계를 탐색합니다.

**파라미터**:
- `entity_name`: 중심 엔티티 이름
- `depth`: 탐색 깊이 (기본 2, 최대 5)
- `limit`: 최대 노드 수 (기본 50, 최대 200)

**활용 예시**:
- "Kubernetes" 엔티티의 관련 기술/프로젝트 탐색
- 특정 인물이 참여한 프로젝트 네트워크 확인
- 기술 간 연관 관계 시각화

### 4.4 전문가 검색

특정 토픽/기술 키워드에 대한 전문가를 Knowledge Graph에서 검색합니다.

- `topic`: 검색할 토픽 (예: "클라우드", "보안")
- `limit`: 반환할 전문가 수

### 4.5 Neo4j Browser 직접 접속

고급 사용자는 Neo4j Browser (`http://localhost:7474`)에서 Cypher 쿼리를 직접 실행할 수 있습니다.

| 항목 | 값 |
|------|-----|
| URL | `http://localhost:7474` |
| 사용자 | `neo4j` |
| 비밀번호 | `neo4j_dev_2026!` |

**유용한 Cypher 쿼리 예시**:

```cypher
// 특정 엔티티의 관련 엔티티 조회
MATCH (e:Entity {name: "Kubernetes"})-[r]-(related)
RETURN e, r, related LIMIT 50

// 두 엔티티 간 최단 경로
MATCH path = shortestPath(
  (a:Entity {name: "Docker"})-[*..5]-(b:Entity {name: "Kubernetes"})
)
RETURN path

// 가장 많이 언급된 엔티티 TOP 10
MATCH (e:Entity)<-[r:MENTIONS]-()
RETURN e.name, count(r) as mentions
ORDER BY mentions DESC LIMIT 10
```

---

## 5. 대화형 검색 (Chat)

### 5.1 개요

LangGraph RAG Workflow 기반의 대화형 검색으로, 자연어 질문에 대해 문맥을 이해하고 답변을 생성합니다.

**파이프라인 구조**:

```
사용자 질문
    |
    v
[Planner] -- 질문 분석, 검색 전략 수립
    |
    v
[Retriever] -- 4-Way Hybrid Search + Reranker
    |
    v
[Generator] -- DeepSeek V3.2로 답변 생성
    |
    v
답변 + 출처 정보
```

### 5.2 사용법

- 자연어로 질문을 입력합니다.
- 시스템이 관련 문서를 검색하고, LLM이 답변을 생성합니다.
- 답변과 함께 출처 문서가 표시됩니다.

### 5.3 대화 이력

- 대화는 세션(conversation) 단위로 관리됩니다.
- `conversationId`를 유지하면 이전 대화 맥락을 참조한 답변이 생성됩니다.
- 새 주제로 전환할 때는 새 대화를 시작하는 것을 권장합니다.

### 5.4 스트리밍

실시간 스트리밍 모드에서는 답변이 토큰 단위로 전송되어, 전체 답변 생성을 기다리지 않고 즉시 결과를 확인할 수 있습니다.

**SSE 이벤트 유형**:
- `start`: 검색 시작 (출처 정보, 세션 ID 포함)
- `chunk`: 답변 텍스트 청크 (토큰 단위)
- `error`: 오류 발생
- `end`: 스트리밍 종료 (전체 통계 포함)

---

## 6. FAQ / 트러블슈팅

### Q1. 검색 결과가 0건입니다.

**원인 및 해결**:

| 원인 | 해결 방법 |
|------|----------|
| 검색어가 너무 구체적 | 더 일반적인 키워드로 변경 |
| 문서가 아직 처리 중 | 문서 상태를 확인 (status: completed인지) |
| 검색 유형이 부적절 | 하이브리드 검색으로 전환 (가장 넓은 검색 범위) |
| 필터 조건이 너무 좁음 | 필터를 제거하고 재검색 |

### Q2. 로그인이 실패합니다.

**원인 및 해결**:

| 원인 | 해결 방법 |
|------|----------|
| 비밀번호 오류 | 정확한 비밀번호 입력 확인 (대소문자, 특수문자) |
| 토큰 만료 | 페이지 새로고침 (자동 토큰 갱신) |
| 서비스 미기동 | AI Service 컨테이너 상태 확인 |

### Q3. 페이지 로딩이 느립니다.

**원인 및 해결**:

| 원인 | 해결 방법 |
|------|----------|
| 네트워크 지연 | 네트워크 연결 확인 |
| 대량 결과 조회 | `top_k` 값을 줄여서 결과 수 제한 |
| 서비스 과부하 | 잠시 후 재시도 |

### Q4. 하이브리드 검색에서 Graph 결과가 없습니다.

**원인**: 검색어와 매칭되는 엔티티가 Knowledge Graph에 없는 경우입니다.
**해결**: Graph 검색은 엔티티 기반이므로, 검색어에 구체적인 기술명이나 프로젝트명을 포함하면 Graph 결과가 더 잘 나타납니다.

### Q5. Chat 검색에서 "환각(hallucination)"이 의심됩니다.

**확인 방법**:
- 답변과 함께 제공되는 출처(sources)를 확인합니다.
- 출처 문서의 내용과 답변이 일치하는지 대조합니다.
- 시스템의 Faithfulness 점수는 0.935로 높은 편이지만, 항상 출처 확인을 권장합니다.

### Q6. 특정 형식의 문서가 업로드되지 않습니다.

**지원 형식 확인**: PDF, DOCX, PPTX, HWP, MD, TXT, HTML, IPYNB
- 지원되지 않는 형식은 업로드가 거부됩니다.
- 파일 크기가 제한을 초과하면 업로드가 실패합니다.
- 파일명에 특수문자가 포함된 경우 문제가 될 수 있습니다.

---

## 시스템 현황 요약

| 항목 | 수치 |
|------|------|
| 등록 문서 | 1,437개 |
| 검색 가능 청크 | 42,462개 |
| 엔티티 노드 | 169,886개 |
| 관계 | 775,366개 |
| RAGAS 평가 등급 | A- (v11) |
| 검색 파이프라인 | 4-Way RRF + BGE-Reranker |
| LLM | DeepSeek V3.2 |

---

*작성: Claude Code (Opus 4.6) | 2026-02-18*
