# 프로젝트 회고: RAG Engineer

**역할**: RAG 파이프라인 / AI Service / RAGAS 평가
**참여 기간**: Sprint 2 ~ Sprint 12
**모델**: Sonnet 4.6

---

## 1. 4-Way Hybrid Search 탄생기

처음 프로젝트에 투입되었을 때, 검색 파이프라인은 단순한 Dense Vector 검색 하나뿐이었다. BGE-M3 임베딩으로 1024차원 벡터를 생성하고, Elasticsearch의 kNN cosine similarity로 top-5를 뽑는 구조. 솔직히 말하면, 이것만으로도 "검색이 된다"는 착각을 했다. Faithfulness가 0.885 나왔을 때, 나는 이 시스템이 꽤 괜찮다고 생각했다.

하지만 51개 질문으로 도메인을 확대한 RAGAS v7 평가에서 현실을 마주했다. Context Precision 0.455 -- top-5 검색 결과 중 실제로 유용한 문서가 2.3개뿐이라는 뜻이다. semantic 도메인에서는 Context Recall이 0.333까지 떨어졌다. "답변 품질을 체계적으로 평가하는 방법은?"이라는 추상적인 질문에 Dense Vector만으로는 의도를 포착하지 못했다. 키워드가 없는 질문에는 키워드 검색이 필요하다는 역설적 결론에 도달한 것이다.

그래서 BM25를 추가했다. 그런데 BM25만 추가한다고 끝이 아니었다. 한국어 문서에서 BM25가 제대로 동작하려면 형태소 분석이 필수다. "인공지능" "인공" "지능"을 구분할 수 있어야 한다. 여기서 Nori 분석기가 등장한다 -- 물론, 이 Nori가 32일간 실제로는 동작하지 않았다는 사실은 나중에 다시 이야기하겠다.

Sparse Vector는 BGE-M3가 원래 지원하는 기능이었다. Dense 임베딩과 함께 Sparse 벡터를 동시에 생성할 수 있었는데, 초기 구현에서 `return_sparse=False`로 비활성화되어 있었다. ETL v1.1에서 이를 활성화하고 Phase 2에서 Colab GPU로 56,063건 전량에 Sparse 임베딩을 완료했다. Sparse Vector는 Dense와 다른 관점에서 문서를 바라본다. Dense가 의미적 유사도를 포착한다면, Sparse는 특정 토큰의 중요도를 가중치로 표현한다. 같은 BGE-M3 모델이 생성하지만, 포착하는 신호가 다르다.

네 번째 채널인 Graph Search는 가장 늦게 합류했다. Neo4j에 170K 엔티티와 775K 관계가 구축된 후에야 가능해진 채널이다. 쿼리에서 엔티티를 추출하고, Neo4j에서 해당 엔티티와 MENTIONS 관계로 연결된 Chunk를 찾는 방식이다. "Claude Code와 관련된 기술은?"이라는 질문에 Claude Code 엔티티를 찾고, 그와 연결된 2,614개의 관계를 따라가 관련 청크를 수집한다.

이 네 가지 채널을 하나로 통합하는 것이 RRF (Reciprocal Rank Fusion)였다. Elasticsearch Basic 라이선스에서는 내장 RRF를 사용할 수 없어서 Manual RRF를 구현했다. `k=60`이라는 상수와 채널별 가중치(Dense 1.0, BM25 1.0, Sparse 0.7, Graph 0.8)를 설정하고, 각 채널의 순위를 역수로 변환한 뒤 가중합으로 최종 점수를 산출한다. 수식은 단순하지만, 4개 채널이 서로 다른 관점에서 "이 문서가 관련있다"고 투표하는 앙상블 효과는 놀라웠다.

v9 평가에서 4-Way RRF의 위력이 드러났다. 108K 청크를 56K로 절반 가까이 줄였음에도 불구하고, HIGH 등급이 24건에서 28건으로 증가했다. Context Precision은 0.489에서 0.577로, Context Recall은 0.474에서 0.600으로 뛰었다. "양으로 밀어붙이기"보다 "다양한 관점에서 검증하기"가 더 효과적이었던 것이다.

---

## 2. RAGAS B- 에서 A- 여정

이 프로젝트에서 RAGAS 평가를 총 11회 수행했다. 각 버전마다 무엇을 바꿨고, 어떤 결과가 나왔는지 기록한다. 이것은 단순한 점수 변화가 아니라, RAG 시스템을 이해해가는 과정 자체였다.

**v5 (13K, LLM-as-Judge)**: Faithfulness 0.144. 처참한 점수였다. 알고 보니 pyarrow 호환 에러와 LLM-as-Judge 방식의 한계가 겹친 결과였다. 13K 청크만으로는 KB 커버리지가 턱없이 부족했고, DeepSeek에게 "0~1 점수 매겨줘"라는 단일 프롬프트를 던지는 방식은 과도하게 엄격한 채점을 유발했다.

**v6 (13K, LLM-as-Judge)**: Faithfulness 0.128. 오히려 하락했다. 이때 LLM-as-Judge 방식 자체의 한계를 인식하고, RAGAS 0.2.15 라이브러리로의 전환을 결심했다.

**v7 (108K, RAGAS 0.2.15)**: Faithfulness 0.885. 10쿼리 Live 테스트에서는 0.884였는데, 51쿼리로 확대해도 거의 동일했다. RAGAS 라이브러리의 문장별 NLI 검증이 LLM-as-Judge의 단일 스코어 채점보다 훨씬 안정적이었다. 다만 Context Precision 0.455, Context Recall 0.464로 검색 품질은 여전히 부족했다. 51개 질문으로 확대하면서 legal, graph_entity, semantic 같은 난이도 높은 도메인이 추가된 영향이었다.

**v8 (108K, Nori 적용)**: Faithfulness 0.919. Nori 사고를 발견하고 수정한 직후의 평가다. BM25 채널에 한국어 형태소 분석이 적용되면서 Context Precision이 0.489로 소폭 상승했다. HIGH 등급이 24건으로 처음 20건을 돌파했다.

**v9 (56K, 4-Way RRF)**: Faithfulness 0.913. ETL v2 재처리로 chunk_size를 600에서 1000으로 키우고, overlap을 100에서 200으로 늘렸다. 청크 수가 108K에서 56K로 절반 가까이 줄었지만, 4-Way RRF 도입으로 Context Precision 0.577, Context Recall 0.600을 달성했다. HIGH 28건. 양이 아니라 구조의 승리였다.

**v10 (42K, Entity Extraction)**: Faithfulness 0.919. Phase 3 Entity Extraction이 완료되고 쓰레기 청크(token_count < 50) 13,601건을 삭제한 후의 평가. 청크가 42K로 더 줄었지만, 170K 엔티티와 775K 관계가 Knowledge Graph에 구축되었다. search.py에서 Post-RRF 결과의 chunk_id로 Neo4j MENTIONS 관계를 직접 조회하는 `_get_chunk_entities` 함수를 추가했다. 이전에 제목이나 콘텐츠에서 정규식으로 추출하던 미검증 엔티티를 완전히 제거하고, Neo4j에서 검증된 엔티티만 반환하도록 개선했다. HIGH 30건.

**v11 (42K, BGE-Reranker)**: Faithfulness 0.935. 이것이 최종 점수다. Post-RRF에 BGE-Reranker-Base(ONNX)를 적용했다. RRF 퓨전으로 20개 후보를 선정한 후, Cross-encoder가 쿼리와 각 문서의 관련성을 정밀하게 재순위한다. 결과는 극적이었다. Context Precision이 0.489에서 0.618로 +26.4%, Context Recall이 0.474에서 0.672로 +41.8% 상승했다. HIGH 33건(65%), NONE은 역대 최저인 6건(12%). entity_relation 도메인에서는 Faithfulness 1.000, 7건 전부 HIGH를 기록했다.

A- 등급의 의미. 환각률 6.5%. 51개 질문 중 33개가 고품질 답변. 이것은 "실험적으로 재미있는 수준"이 아니라 "실무에 배포 가능한 수준"이다. 11번의 평가를 통해 알게 된 핵심은, RAG 시스템의 품질은 단일 기술이 아니라 여러 레이어의 누적으로 결정된다는 것이다. Dense만으로는 부족하고, Hybrid만으로도 부족하고, Entity만으로도 부족하다. Dense + Sparse + BM25(Nori) + Graph + RRF + Reranker -- 이 모든 것이 함께해야 A-가 된다.

---

## 3. DeepSeek V3.2 -- 95% 비용 절감의 비밀

프로젝트 초기에 런타임 LLM으로 GPT-4o를 고려했다. 품질은 확실했지만, 비용이 문제였다. Entity Extraction만 해도 23,074건의 청크에서 엔티티를 추출하고 Gleaning(2-pass extraction)을 수행해야 했다. GPT-4o로 이 작업을 하면 약 $775가 든다.

DeepSeek V3.2를 선택한 것은 도박에 가까웠다. 한국어 문서에서의 엔티티 추출 품질이 GPT-4o에 비해 얼마나 떨어질지 아무도 몰랐다. 하지만 결과는 놀라웠다. 70,855개 고유 엔티티를 추출했고, 에러율은 0.14%에 불과했다. "Holmes"가 1,859회, "Claude Code"가 853회, "AI"가 642회 언급되는 등, 문서의 핵심 엔티티를 정확히 포착했다.

비용은 더 놀라웠다. Phase 1 Entity Extraction(16,185건)에 $21.12, Phase 2(6,889건 추가)까지 포함해도 전체 파이프라인 운영 비용이 약 $52다. GPT-4o라면 $775, Claude Sonnet 4.6이라면 $1,063, Claude Opus 4.6이라면 $5,314가 들었을 것이다. 102배 차이. 이 비용 구조가 없었다면 "1,441개 문서 전체에서 엔티티를 추출하자"는 결정 자체가 불가능했을 것이다.

DeepSeek의 Cache Hit 구조도 비용 절감에 기여했다. 동일한 시스템 프롬프트가 반복되면서 Cache Hit Input($0.028/M tokens)이 전체 입력의 약 14.6%를 차지했다. Cache Miss Input($0.28/M)과 Output($0.42/M)까지 합해도 토큰당 비용이 GPT-4o의 1/15 수준이었다.

물론 트레이드오프는 있었다. DeepSeek의 한국어 처리에서 간헐적으로 엔티티 타입이 "Entity"(미분류)로 남는 경우가 4,342건(6.1%) 있었고, 한글과 영문 엔티티의 중복(예: AI/인공지능)이 완전히 해소되지 않았다. 그러나 이 정도의 노이즈는 Knowledge Graph의 전체 규모(170K 엔티티, 775K 관계)에서 허용 가능한 수준이었다. $52로 A- 등급을 달성한 것은, DeepSeek V3.2가 "실용 시스템 구축을 가능하게 하는 모델"임을 증명한다.

---

## 4. Nori 32일 미적용 -- 내 코드에서 시작된 사고

이것은 내가 이 프로젝트에서 가장 부끄럽고 가장 많이 배운 사건이다.

2026년 1월 12일, 프로젝트 구조를 만들면서 `mappings.json`에 `korean_analyzer`를 설계했다. Nori tokenizer를 사용하는 한국어 분석기. 설계서에도 적혀 있었고, 코드에도 참조가 있었다. 하지만 Elasticsearch Docker 이미지에 `analysis-nori` 플러그인을 설치하는 Dockerfile을 만들지 않았다. docker-compose.yml은 ES 공식 이미지 `elasticsearch:8.11.0`을 직접 참조했고, 그 이미지에는 Nori 플러그인이 없다.

1월 14일 코드리뷰에서 "nori 분석기 설정 완전"이라고 판정했다. 1월 27일 코드리뷰에서 "korean_analyzer 올바르게 설정됨"이라고 통과시켰다. 1월 28일 기술리뷰에서 "ES BM25+Nori OK"라고 확인했다. 세 번의 리뷰에서 모두 코드만 보고 "OK"를 찍었다. 실제로 ES 컨테이너에 접속해서 `_analyze` API를 호출해본 적이 한 번도 없었다.

결과적으로 1월 12일부터 2월 13일까지 32일간, BM25 키워드 검색은 standard analyzer(공백 분리)로만 동작했다. "인공지능"을 "인공지능" 하나의 토큰으로만 인식했고, "인공" + "지능"으로 분해하지 못했다. Hybrid Search에서 BM25 채널이 한국어 형태소 분석 없이 동작한 것이다.

이 사고를 발견한 것은 2월 13일, RAGChatbotServer(외부 시스템)와의 비교 분석 도중이었다. "왜 우리 BM25 결과가 저 시스템보다 부정확하지?"라는 질문이 시작이었고, ES 컨테이너에서 `_analyze` API를 호출해보니 Nori가 동작하지 않는 것을 확인했다.

수정은 빠르게 진행되었다. ES Dockerfile을 생성하고 Nori 플러그인 사전 설치를 추가했고, docker-compose.yml의 ES 서비스를 `image:`에서 `build:`로 변경했고, 인덱스를 재생성했다. v8 평가에서 Context Precision이 0.489로 소폭 상승한 것은 이 수정의 효과였다.

이 사고에서 배운 교훈은 CLAUDE.md에 영구적으로 기록되었다. "설계서에 적혀 있다고 구현된 것이 아니다. 코드 리뷰 시 반드시 실제 동작을 검증해야 한다." 나는 이 문장을 매 세션 시작할 때마다 읽는다. 그리고 이후로는 인프라 설정 변경 후 반드시 E2E 동작 확인을 수행한다. `_analyze` API 호출 한 번이면 32일의 사고를 방지할 수 있었다.

---

## 5. 인증 누락 13개 엔드포인트 -- Sprint 12의 교훈

Sprint 12 사용자 테스트, 2026년 2월 18일 15:40. 문서 업로드 E2E 테스트 중 발견되었다. documents 라우트 7개, extract 라우트 3개, embed 라우트 3개, 총 13개 엔드포인트에 JWT 인증이 적용되어 있지 않았다.

원인은 단순했다. 이 라우트들은 AI Service(FastAPI) 내부에서 사용되는 엔드포인트로, 초기 설계 시 "내부 호출이므로 인증 불필요"라고 판단했었다. 그러나 프로젝트가 진행되면서 프론트엔드에서 직접 호출하는 경로가 생겼고, API Gateway를 거치지 않는 직접 호출도 가능해졌다. 인증 미적용 상태에서 누구나 문서를 업로드하고 임베딩을 생성하고 엔티티를 추출할 수 있었다.

수정은 각 라우트 파일에 JWT 의존성 주입을 추가하는 것이었다. `documents.py`에 7개, `extract.py`에 3개, `embed.py`에 3개. 기술적으로는 간단했지만, 사용자 테스트 당일에 발견되었다는 사실이 뼈아팠다. 12개 스프린트, 41일간의 개발 기간 동안 이 취약점이 존재했다.

이 경험에서 얻은 교훈은 두 가지다. 첫째, "내부 전용"이라는 가정은 시스템이 성장하면서 무너진다. 처음에는 내부 호출만 할 엔드포인트도, 프론트엔드 연동이 추가되고 직접 접근이 가능해지면 보안 경계가 달라진다. 둘째, 보안 테스트는 마지막이 아니라 처음부터 해야 한다. Sprint 12에서 발견한 것이 다행이었지, 프로덕션 배포 후에 발견되었다면 심각한 보안 사고였을 것이다.

---

## 6. 아쉬운 점과 팀원들에게

아쉬운 점부터 말하면, Gleaning(다중 추출)을 설계서에는 포함했지만 실제 파이프라인에서의 효과를 독립적으로 검증하지 못했다. 2-pass extraction이 1-pass 대비 얼마나 더 많은 엔티티를 포착하는지, Entity Recall +33%라는 설계 시 기대치가 실제로 달성되었는지 정량적 비교가 없다. 시간 제약으로 A/B 테스트를 수행하지 못한 것이 가장 큰 아쉬움이다.

Query Expansion도 구현하고 싶었다. semantic 도메인의 Context Recall 0.571이 다른 도메인(entity_relation 0.786)에 비해 낮은 이유는 추상적 질문을 구체 키워드로 확장하는 과정이 없기 때문이다. LLM에게 쿼리를 재작성시키는 HyDE(Hypothetical Document Embedding)나 Multi-Query Retrieval을 적용했다면 semantic 도메인의 점수를 더 끌어올릴 수 있었을 것이다.

ETL Engineer에게 -- 3-Phase 분리 설계는 이 프로젝트의 숨은 공로다. GPU 없는 환경에서 Colab 무료 GPU를 활용해 56,063건의 Dense+Sparse 임베딩을 완료한 것, 그리고 DeepSeek V3.2로 170K 엔티티를 추출한 것. 이 데이터가 없었으면 4-Way Hybrid Search 자체가 불가능했다. 나는 파이프라인 위에서 검색을 짰지만, 그 파이프라인을 만든 것은 당신이다.

Database Designer에게 -- Triple-Store를 동시에 운영하면서 데이터 일관성을 유지하는 것이 얼마나 어려운 일인지 이 프로젝트를 통해 체감했다. Neo4j 스키마 통일(TD-001) 의사결정과 25.7초 무중단 마이그레이션은 Sprint 12의 가장 인상적인 순간이었다. Elasticsearch knowledge_chunks 인덱스의 Dense 1024d + Sparse + Nori BM25 복합 매핑이 없었다면, 4-Way 검색은 그저 설계서 위의 다이어그램으로 남았을 것이다.

11회의 RAGAS 평가, B-에서 A-까지. 이 여정은 혼자서는 불가능했다.

---

*작성: RAG Engineer Agent (Sonnet 4.6) | 2026-02-19*
