# 프로젝트 회고 — RAG Engineer

**프로젝트**: Hybrid RAG Knowledge Platform 고도화
**기간**: 2026-01-10 ~ 2026-03-10
**역할**: LangGraph RAG 워크플로우 설계/구현, HybridRetriever 4채널 융합, 임베딩/Reranker 모델 통합, DeepSeek LLM 연동

---

## 1. 내가 기여한 것 (What I Did)

- **LangGraph RAG 워크플로우**: LangGraph를 기반으로 검색-재랭킹-생성 파이프라인을 구현했습니다. Query Analysis -> Retrieval -> Reranking -> Generation의 4단계 워크플로우를 상태 머신으로 설계하여, 각 단계의 독립적인 최적화가 가능한 구조를 만들었습니다.
- **HybridRetriever 4채널 융합**: Dense(BGE-M3 벡터), Sparse(BM25 Nori), Graph(Neo4j 관계), Temporal(시간 가중치) 4채널을 RRF(Reciprocal Rank Fusion)로 융합하는 검색 엔진을 구현했습니다. `c=50, graph_search_top_k=10` 최적 파라미터를 실험으로 확정했습니다.
- **BGE-M3 임베딩 + BGE Reranker**: 한국어 특화 임베딩 모델 BGE-M3과 Cross-encoder Reranker를 ONNX 런타임으로 최적화하여 CPU 환경에서도 실용적인 성능을 달성했습니다. ONNX 2코어 제한으로 healthcheck 보호도 구현했습니다.
- **DeepSeek V3.2 LLM 통합**: 런타임 LLM으로 DeepSeek V3.2를 채택하여 95% 비용 절감을 달성하면서도 한국어 응답 품질을 확보했습니다.
- **Reranker 1-Pass 최적화**: Reranker 2-Pass가 수학적으로 중복임을 증명(Cross-encoder는 query+content만 사용)하고, 1-Pass로 전환하여 지연 시간을 절반으로 줄였습니다.

## 2. 잘된 점 (What Went Well)

- **RAGAS Mean 0.763 역대 최고 달성**: 18회의 RAGAS 평가를 거치며 파라미터를 체계적으로 튜닝한 결과, A등급 품질에 도달했습니다. v15~v17의 변수 격리 실험이 결정적이었습니다.
- **4채널 융합의 시너지**: 단일 채널 대비 4채널 융합이 Faithfulness, Answer Relevancy, Context Recall 모든 지표에서 우위를 보였습니다. 특히 Graph 채널이 엔티티 관계 질문에서 큰 기여를 했습니다.
- **rerank_candidate_count 최적화**: `min(top_k*3, 50)`으로 Reranker 풀 크기를 설정하여, 정밀도와 리콜의 균형을 잡았습니다.

## 3. 아쉬운 점 (What Could Be Better)

- **Chat vs REST API 성능 차이**: HybridRetriever(pool=10)와 SearchService(pool=15)의 파라미터 불일치로 Chat API가 REST API보다 4%p 낮은 성능을 보였습니다. 아직 통일하지 못한 것이 아쉽습니다.
- **Gleaning 미구현**: 설계서에 포함된 Gleaning(반복 추출)을 시간 관계상 구현하지 못했습니다. Context Recall 개선에 기여할 수 있었을 것입니다.
- **한국어 특화 프롬프트 최적화**: 프롬프트 엔지니어링에 더 시간을 투자했으면 Faithfulness 지표를 0.95 이상으로 끌어올릴 수 있었을 것입니다.

## 4. 배운 점 (What I Learned)

- **변수 격리 실험의 중요성**: 여러 파라미터를 동시에 바꾸면 어떤 변수가 성능 변화의 원인인지 알 수 없습니다. v15~v17에서 한 번에 하나씩 변수를 격리한 실험이 최적 파라미터 발견의 열쇠였습니다.
- **Precision-Recall 트레이드오프**: graph_search_top_k를 3으로 줄이면 Precision은 올라가지만 Recall이 급감합니다. 10으로 복원하니 전체 Mean이 12%p 상승했습니다. 이론적 트레이드오프를 실측으로 확인한 귀중한 경험입니다.
- **ONNX 런타임의 실용성**: GPU 없이도 ONNX로 변환한 모델이 실용적인 추론 속도를 제공합니다. CPU 2코어 제한과 배치 처리 조합이 핵심이었습니다.

## 5. 다음 프로젝트에 바라는 점

- Gleaning과 Self-RAG 등 고급 RAG 기법을 구현하여 Context Recall을 0.9 이상으로 끌어올리고 싶습니다.
- A/B 테스트 프레임워크를 도입하여, 파라미터 변경의 효과를 프로덕션 트래픽으로 검증할 수 있으면 좋겠습니다.

## 6. 팀원들에게 한마디

RAG 파이프라인은 혼자서는 절대 완성할 수 없는 영역입니다. ETL이 깨끗한 데이터를 제공하고, DB Designer가 3-Store 스키마를 설계하고, Infra가 안정적인 컨테이너 환경을 구축한 위에서 RAG가 동작할 수 있었습니다. QA와 함께 18회의 RAGAS 평가를 반복하며 0.001 단위로 성능을 끌어올린 과정은 마치 실험실에서 연구하는 느낌이었습니다. 이 팀과 함께여서 Mean 0.763이라는 성과가 가능했습니다. 정말 재미있었고, 감사합니다!
