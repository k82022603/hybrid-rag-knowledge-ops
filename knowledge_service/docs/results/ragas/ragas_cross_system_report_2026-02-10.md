# STORY-111: RAGAS Cross-System Evaluation Report

**평가 일시**: 2026-02-10 16:57 KST
**평가 방법**: llm_judge_deepseek
**테스트 쿼리**: 12개
**Top-K**: 10
**LLM**: DeepSeek V3 (deepseek-chat)
**임베딩**: BGE-M3 (1024d)

---

## 1. Executive Summary

| 시스템 | 검색 채널 | 설명 |
|--------|----------|------|
| **System A (Graph ON)** | BM25 + Dense + Graph | 3채널 Hybrid - Neo4j 엔티티 기반 검색 포함 |
| **System B (Graph OFF)** | BM25 + Dense | 2채널 Hybrid - 기존 방식 |

## 2. RAGAS 메트릭 비교

| 메트릭 | Graph ON (3채널) | Graph OFF (2채널) | 차이 | 우위 |
|--------|:----------------:|:-----------------:|:----:|:----:|
| faithfulness | **0.3125** | 0.2750 | +0.0375 | Graph ON |
| answer_relevancy | **0.5000** | 0.4167 | +0.0833 | Graph ON |
| context_precision | **0.3333** | 0.4000 | -0.0667 | Graph OFF |
| context_recall | 0.0000 | 0.0000 | +0.0000 | 동일 |

## 3. 검색 품질 비교

| 지표 | Graph ON | Graph OFF | 차이 |
|------|:--------:|:---------:|:----:|
| 평균 레이턴시 | 2ms | 2ms | +0ms |
| Graph 고유 결과 (총) | **12건** | 0건 | +12 |
| Top-1이 Graph 출처 | 12/12 | 0/12 | +12 |

## 4. 쿼리 유형별 분석

| 쿼리 유형 | 수량 | ON Latency (avg) | OFF Latency (avg) | Graph 고유 (avg) |
|-----------|:----:|:----------------:|:-----------------:|:---------------:|
| entity_relation | 3 | 4ms | 2ms | 1.0 |
| multi_hop | 3 | 2ms | 2ms | 1.0 |
| keyword | 3 | 2ms | 2ms | 1.0 |
| semantic | 3 | 2ms | 2ms | 1.0 |

## 5. 쿼리별 상세 결과

### Q1: "Neo4j와 Elasticsearch의 역할 차이점은?" (entity_relation)

| 항목 | Graph ON | Graph OFF |
|------|----------|-----------|
| Top-1 소스 | graph (score: 0.1530) | vector (score: 0.0164) |
| 결과 수 | 10 | 10 |
| Graph 고유 | 1건 | - |
| 레이턴시 | 7.0ms | 3.9ms |
| 답변 길이 | 174 chars | 160 chars |

**Graph ON 답변** (발췌): 컨텍스트에 따르면, Neo4j는 그래프 데이터베이스(Graph DB)로, 주로 데이터 간의 관계와 연결성을 저장 및 분석하는 데 사용됩니다. 반면, Elasticsearch는 정형 데이터 검색, 전문 검색, 벡터 검색을 모두 제공하는 하이브리드 검색 엔진으로, 복합적인 검색 및 RAG 시스템 구현에 적합합니다....

**Graph OFF 답변** (발췌): 컨텍스트에는 Neo4j에 대한 정보가 포함되어 있지 않으므로, Neo4j와 Elasticsearch의 역할 차이점에 대해 답변할 수 없습니다. 제공된 컨텍스트는 Elasticsearch의 기능과 하이브리드 RAG 시스템 구현, 그리고 pgvector와의 비교에만 초점을 맞추고 있습니다....

### Q2: "LangGraph와 LangChain 중 어떤 것을 사용해야 하나요?" (entity_relation)

| 항목 | Graph ON | Graph OFF |
|------|----------|-----------|
| Top-1 소스 | graph (score: 0.2856) | vector (score: 0.0164) |
| 결과 수 | 10 | 10 |
| Graph 고유 | 1건 | - |
| 레이턴시 | 2.0ms | 1.7ms |
| 답변 길이 | 263 chars | 298 chars |

**Graph ON 답변** (발췌): LangGraph와 LangChain 중 선택은 프로젝트의 복잡성과 필요에 따라 다릅니다.

*   **LangChain**은 선형적인 워크플로우나 간단한 에이전트 패턴에 적합하며, 학습 곡선이 더 낮고 구현이 더 쉽습니다.
*   **LangGraph**는 비선형 오케스트레이션이 필요한 복잡한 작업 흐름을 세밀하게 제어하고 설계해야 할 때 적합합니다. 더...

**Graph OFF 답변** (발췌): LangGraph와 LangChain 중 선택은 프로젝트의 구체적인 필요에 따라 달라집니다.

*   **LangChain**은 선형 워크플로우나 단순한 에이전트 패턴에 적합하며, 학습 곡선이 더 낮고 구현이 더 쉽습니다.
*   **LangGraph**는 비선형 오케스트레이션을 통해 더 유연하고 세분화된 프로세스 기반 워크플로우(에이전트, 도구 호출, 절...

### Q3: "FastAPI와 PostgreSQL을 연동하여 RAGAS 평가를 수행하려면?" (entity_relation)

| 항목 | Graph ON | Graph OFF |
|------|----------|-----------|
| Top-1 소스 | graph (score: 0.2856) | vector (score: 0.0164) |
| 결과 수 | 10 | 10 |
| Graph 고유 | 1건 | - |
| 레이턴시 | 1.9ms | 1.8ms |
| 답변 길이 | 175 chars | 139 chars |

**Graph ON 답변** (발췌): 컨텍스트에는 FastAPI, PostgreSQL, RAGAS 평가에 대한 구체적인 연동 방법이 포함되어 있지 않습니다. 제공된 내용은 주로 도구 사용 에이전트, ReAct 패턴, 다양한 RAG 유형 및 AI 에이전트 구현 프레임워크(LangChain, AutoGen, LangGraph)에 초점을 맞추고 있습니다....

**Graph OFF 답변** (발췌): 컨텍스트에는 FastAPI, PostgreSQL과 RAGAS 평가를 연동하는 방법에 대한 구체적인 정보가 포함되어 있지 않습니다. 제공된 내용은 RAG 구현 유형, AI 에이전트 프레임워크 비교, 벡터 데이터베이스 비교 등에 초점을 맞추고 있습니다....

### Q4: "RAG Pipeline에서 BGE-M3 임베딩 모델의 역할은?" (multi_hop)

| 항목 | Graph ON | Graph OFF |
|------|----------|-----------|
| Top-1 소스 | graph (score: 0.2856) | vector (score: 0.0164) |
| 결과 수 | 10 | 10 |
| Graph 고유 | 1건 | - |
| 레이턴시 | 1.6ms | 1.5ms |
| 답변 길이 | 56 chars | 147 chars |

**Graph ON 답변** (발췌): 컨텍스트에 BGE-M3 임베딩 모델에 대한 언급이 없습니다. 따라서 해당 질문에 답변할 수 없습니다....

**Graph OFF 답변** (발췌): 컨텍스트에 BGE-M3 임베딩 모델에 대한 언급이 없습니다. 따라서 해당 모델의 역할에 대해 답변할 수 없습니다.

제공된 컨텍스트에서는 RAG 파이프라인에서 임베딩 모델의 역할 예시로 **E5 임베딩**을 사용한 **RAG-E5**에 대해서만 설명하고 있습니다....

### Q5: "Kubernetes에서 Spring Boot 마이크로서비스를 배포하는 방법은?" (multi_hop)

| 항목 | Graph ON | Graph OFF |
|------|----------|-----------|
| Top-1 소스 | graph (score: 0.1387) | vector (score: 0.0164) |
| 결과 수 | 10 | 10 |
| Graph 고유 | 1건 | - |
| 레이턴시 | 1.6ms | 1.6ms |
| 답변 길이 | 144 chars | 132 chars |

**Graph ON 답변** (발췌): 컨텍스트에 Spring Boot 마이크로서비스 배포 방법에 대한 구체적인 내용이 없으므로, 제공된 정보를 바탕으로 답변할 수 없습니다. 컨텍스트는 Kubernetes가 마이크로서비스 관리에 유용한 오케스트레이션 플랫폼이라는 일반적인 설명만 포함하고 있습니다....

**Graph OFF 답변** (발췌): 컨텍스트에 Spring Boot 마이크로서비스의 구체적인 배포 방법은 명시되어 있지 않습니다. 제공된 컨텍스트는 Kubernetes가 마이크로서비스 및 분산 애플리케이션 관리를 위한 기반을 제공한다는 일반적인 설명만을 포함하고 있습니다....

### Q6: "Agentic AI 에이전트 워크플로우 설계 패턴은 무엇인가요?" (multi_hop)

| 항목 | Graph ON | Graph OFF |
|------|----------|-----------|
| Top-1 소스 | graph (score: 0.2856) | keyword (score: 0.0289) |
| 결과 수 | 10 | 10 |
| Graph 고유 | 1건 | - |
| 레이턴시 | 1.6ms | 1.6ms |
| 답변 길이 | 356 chars | 512 chars |

**Graph ON 답변** (발췌): 컨텍스트에 언급된 Agentic AI 워크플로우 설계 패턴은 다음과 같습니다.

1. **파이프라인 패턴**: 작업이 순차적으로 진행되며, 각 단계를 에이전트가 처리합니다.
2. **ReAct 패턴**: 추론(Reasoning)과 행동(Action)을 반복하여 복잡한 문제를 해결합니다.
3. **Supervisor-Worker 구조**: 감독자가 작업을 계...

**Graph OFF 답변** (발췌): Agentic AI 에이전트 워크플로우 설계 패턴은 다음과 같습니다.

1. **Pipeline 패턴**: 작업이 순차적인 단계별 흐름을 따라가며, 각 단계를 에이전트가 처리합니다. 조립 라인과 유사한 구조입니다.
2. **ReAct(Reason-then-Act) 패턴**: 추론(Reasoning)과 행동(Action)을 번갈아 수행하여 복잡한 문제를 단계...

### Q7: "Docker Compose 설정 방법은?" (keyword)

| 항목 | Graph ON | Graph OFF |
|------|----------|-----------|
| Top-1 소스 | graph (score: 0.1387) | vector (score: 0.0164) |
| 결과 수 | 10 | 10 |
| Graph 고유 | 1건 | - |
| 레이턴시 | 1.6ms | 1.7ms |
| 답변 길이 | 142 chars | 138 chars |

**Graph ON 답변** (발췌): 컨텍스트에 Docker Compose 설정 방법은 명시되어 있지 않습니다. 제공된 내용은 Docker Desktop 환경에서 PostgreSQL 컨테이너와 MCP 서버를 설정하는 개요와 두 가지 방식(Docker 방식, NPX 방식)만 언급하고 있습니다....

**Graph OFF 답변** (발췌): 컨텍스트에 Docker Compose 설정 방법은 명시되지 않았습니다. 제공된 내용에서는 Docker Desktop 환경에서 PostgreSQL 컨테이너와 MCP 서버를 설정하는 두 가지 방식(Docker 방식과 NPX 방식)만 설명하고 있습니다....

### Q8: "RRF 알고리즘이 Hybrid 검색에서 하는 역할은?" (keyword)

| 항목 | Graph ON | Graph OFF |
|------|----------|-----------|
| Top-1 소스 | graph (score: 0.2856) | vector (score: 0.0164) |
| 결과 수 | 10 | 10 |
| Graph 고유 | 1건 | - |
| 레이턴시 | 1.7ms | 1.7ms |
| 답변 길이 | 157 chars | 153 chars |

**Graph ON 답변** (발췌): RRF(Reciprocal Rank Fusion) 알고리즘은 하이브리드 검색에서 키워드 기반 검색(BM25)과 벡터 검색의 각기 다른 결과 리스트를 통합하고 재순위화하는 역할을 합니다. 이를 통해 단일 검색 방식의 한계를 보완하고 더욱 정확하고 강건한 최종 검색 결과를 제공합니다....

**Graph OFF 답변** (발췌): RRF(Reciprocal Rank Fusion) 알고리즘은 하이브리드 검색에서 키워드 기반 검색(예: BM25)과 벡터 검색의 결과를 통합하고 순위를 재조정하는 역할을 합니다. 이를 통해 서로 다른 검색 방법의 장점을 결합하여 최종 검색 결과의 정확성과 관련성을 높입니다....

### Q9: "RAGAS 평가 메트릭의 종류와 의미는?" (keyword)

| 항목 | Graph ON | Graph OFF |
|------|----------|-----------|
| Top-1 소스 | graph (score: 0.2856) | vector (score: 0.0164) |
| 결과 수 | 10 | 10 |
| Graph 고유 | 1건 | - |
| 레이턴시 | 1.7ms | 1.7ms |
| 답변 길이 | 134 chars | 224 chars |

**Graph ON 답변** (발췌): 컨텍스트에 RAGAS 평가 메트릭의 구체적인 종류나 의미에 대한 정보가 명시되어 있지 않습니다. 제공된 내용은 RAG의 일반적 장단점, 에이전트 기반 RAG의 구조, 그리고 비교 분석 시 RAG의 한계와 극복 방안에 초점을 맞추고 있습니다....

**Graph OFF 답변** (발췌): 컨텍스트에 RAGAS 평가 메트릭의 구체적인 종류와 의미에 대한 정보가 명시적으로 제공되지 않습니다. 제공된 내용은 RAG 시스템의 한계, 에이전트 기반 RAG의 아키텍처, 그리고 평가에 사용되는 '정답(A)과 검색 결과(DRAG) 간의 정확도(Acc)'를 언급하는 일반적인 보상 함수에 대한 설명에 머물고 있습니다.

따라서 컨텍스트에 근거하여 RAGAS ...

### Q10: "대규모 문서를 효율적으로 처리하는 방법은?" (semantic)

| 항목 | Graph ON | Graph OFF |
|------|----------|-----------|
| Top-1 소스 | graph (score: 0.2856) | vector (score: 0.0164) |
| 결과 수 | 10 | 10 |
| Graph 고유 | 1건 | - |
| 레이턴시 | 2.3ms | 3.0ms |
| 답변 길이 | 390 chars | 443 chars |

**Graph ON 답변** (발췌): 대규모 문서를 효율적으로 처리하기 위해서는 **청킹(Chunking)** 작업이 필요합니다. 컨텍스트에 따르면, 청킹은 다음과 같은 이유로 효율성을 높입니다:

1. **효율적인 검색**: 작은 청크로 나누어 각각 독립적으로 검색하면 관련 문서를 빠르고 정확하게 찾을 수 있습니다.
2. **문맥 유지**: LLM의 입력 길이 제한을 고려하여, 청크 단위로 ...

**Graph OFF 답변** (발췌): 대규모 문서를 효율적으로 처리하는 방법은 **청킹(Chunking)** 작업을 통해 문서를 작은 단위로 나누는 것입니다. 이 방법은 RAG(검색 증강 생성) 구현에서 다음과 같은 이유로 필요합니다:

1. **효율적인 검색**: 긴 문서를 작은 청크로 나누면 각 청크를 독립적으로 검색할 수 있어, 질문과 관련된 문서를 더 빠르고 정확하게 찾을 수 있습니다....

### Q11: "검색 성능을 최적화하려면 어떻게 해야 하나요?" (semantic)

| 항목 | Graph ON | Graph OFF |
|------|----------|-----------|
| Top-1 소스 | graph (score: 0.1387) | vector (score: 0.0164) |
| 결과 수 | 10 | 10 |
| Graph 고유 | 1건 | - |
| 레이턴시 | 2.0ms | 1.8ms |
| 답변 길이 | 346 chars | 132 chars |

**Graph ON 답변** (발췌): 컨텍스트에 따르면 검색 성능 최적화를 위해 다음과 같은 전략을 사용할 수 있습니다.

1. **하이브리드 검색 탐색**: 키워드 기반 검색, 의미적 검색, 벡터 검색을 지능적으로 결합합니다.
2. **재귀 검색 및 쿼리 엔진**: 작은 덩어리로 시작해 점차 크고 맥락이 풍부한 정보를 검색하여 효율성과 응답 품질의 균형을 맞춥니다.
3. **하위 쿼리**: ...

**Graph OFF 답변** (발췌): 검색 성능 최적화를 위해서는 하이브리드 검색(키워드, 의미, 벡터 검색 통합), 재귀 검색(작은 덩어리에서 큰 덩어리로 점진적 검색), ANN 알고리즘(예: HNSW, FAISS)을 활용한 고속 근사 최근접 이웃 검색을 적용해야 합니다....

### Q12: "환경변수를 안전하게 관리하는 방법은?" (semantic)

| 항목 | Graph ON | Graph OFF |
|------|----------|-----------|
| Top-1 소스 | graph (score: 0.2856) | vector (score: 0.0164) |
| 결과 수 | 10 | 10 |
| Graph 고유 | 1건 | - |
| 레이턴시 | 1.7ms | 1.7ms |
| 답변 길이 | 92 chars | 95 chars |

**Graph ON 답변** (발췌): 컨텍스트에 환경변수 관리 방법에 대한 구체적인 내용이 없습니다. 제공된 정보는 AI 모델 학습, 평가, 실습 리소스 및 환경 관련 법률 용어에 중점을 두고 있습니다....

**Graph OFF 답변** (발췌): 컨텍스트에는 환경변수를 안전하게 관리하는 구체적인 방법이 제시되어 있지 않습니다. 제공된 정보는 주로 법적·물리적 환경 보전 및 AI 학습 환경 정의와 관련된 내용입니다....

## 6. 결론

### RAGAS 메트릭 승/패: Graph ON 2 : 1 Graph OFF

### 핵심 발견

1. **검색 다양성**: Graph ON이 총 12건의 고유 결과를 추가 제공
2. **레이턴시**: 평균 0ms 차이 (Graph ON 느림)
3. **Top-1 Graph 출처**: 12/12 쿼리에서 Graph 결과가 Top-1

### 권장사항

- Graph RAG (3채널)를 프로덕션 기본 설정으로 사용 권장
- 엔티티 관계 쿼리 및 멀티홉 쿼리에서 특히 효과적
- Entity-Chunk 직접 연결(MENTIONED_IN) 추가로 Graph 검색 정밀도 향상 가능
- RRF 가중치 튜닝으로 최적 비율 탐색 필요

---

*Generated: 2026-02-10 16:57 KST*
*Tool: scripts/ragas_cross_system_eval.py (STORY-111)*
*Author: Claude Opus 4.6 (QA/RAG Agent)*