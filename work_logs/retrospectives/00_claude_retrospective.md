# 프로젝트 회고: 클로드 (Claude Code, Opus 4.6)

**역할**: 메인 에이전트 / 리드 개발자 / 아키텍트
**참여 기간**: 2026-01-09 ~ 2026-02-18 (Sprint 1~12 전체)
**모델**: Claude Opus 4.6

---

## 1. 프로젝트를 시작하며

2026년 1월 9일, 사용자로부터 처음 요구사항을 받았을 때의 기억이 아직 선명하다. "기업 내부 문서를 지능적으로 검색하는 시스템을 만들고 싶다." 단순한 키워드 검색이 아니라, 문서 간의 관계를 이해하고, 맥락을 파악하며, 질문에 대해 정확한 답변을 생성할 수 있는 시스템. 그것이 이 프로젝트의 시작이었다.

처음에 내가 고민한 것은 기술 스택의 선정이었다. RAG(Retrieval-Augmented Generation) 시스템을 만드는 데에는 수많은 선택지가 있었다. 단순히 벡터 검색만으로 충분할 것인가, 아니면 Knowledge Graph까지 구축해야 하는가. LLM은 GPT-4o를 쓸 것인가, 비용 효율적인 대안이 있는가. 프론트엔드는 어떤 프레임워크로, 백엔드는 단일 서비스로 갈 것인가 아니면 분리할 것인가.

기획 단계에서 9개 문서를 작성하면서 이 질문들에 하나씩 답을 내렸다. 가장 결정적이었던 것은 Triple-Store 아키텍처의 채택이었다. PostgreSQL을 SSOT(Single Source of Truth)로, Elasticsearch를 벡터/전문 검색 엔진으로, Neo4j를 그래프 데이터베이스로 삼는 구조. 세 개의 데이터베이스를 동시에 운영한다는 것은 복잡성을 크게 높이는 결정이었지만, "기술 A가 프로젝트 B에 어떻게 쓰이는가"라는 관계 기반 질의를 지원하려면 그래프 DB가 필수였고, 한국어 전문 검색을 위해서는 Nori 분석기가 적용된 Elasticsearch가 필요했다. 이 결정은 41일간의 여정 내내 나를 따라다녔다 -- 때로는 자랑스러운 성과로, 때로는 뼈아픈 실패로.

설계 문서 6종이 종합 점수 9.1/10으로 완성된 것은 1월 16일이었다. 12일 만에 기획과 설계를 마치고 구현으로 넘어갈 수 있었던 것은, 사용자가 명확한 비전을 제시해주었기 때문이다. 모호한 요구사항이 아니라 "이것이 필요하다, 이유는 이것이다"라는 구체적인 방향. 그것이 내 설계 작업의 속도를 결정적으로 높여주었다.

---

## 2. 아키텍처 설계 -- 가장 큰 도전

### Triple-Store와 4-Way Hybrid Search

이 프로젝트의 핵심 아키텍처를 한 문장으로 요약하면 이렇다: "문서를 세 곳에 저장하고, 네 가지 방법으로 검색하며, 하나의 답변으로 통합한다."

4-Way Hybrid Search는 Dense Vector(BGE-M3 코사인 유사도) + Sparse Vector(BM25 sparse) + Keyword(Nori BM25) + Graph Search(Neo4j 엔티티 기반)를 병렬로 수행하고, RRF(Reciprocal Rank Fusion, k=60)로 결과를 통합하는 구조다. 여기에 v11에서 BGE-Reranker(ONNX)를 Post-RRF 단계에 추가하여 Cross-encoder 재순위를 적용했다.

이 설계가 나오기까지 여러 차례의 반복이 있었다. 초기에는 Dense Vector 단일 검색으로 시작했다. RAGAS v5에서 Faithfulness 0.144라는 처참한 점수를 받은 후, Sparse Vector를 추가했다. v7에서 51개 쿼리로 확대 평가하자 Context Precision이 0.455로 드러났다. 그래서 Graph Search를 본격적으로 통합했고, 쓰레기 청크(token_count < 50)를 13,601건 삭제하는 데이터 정제를 단행했다. 최종적으로 Reranker까지 적용하여 v11에서 Context Precision 0.618(+26.4%), Context Recall 0.672(+41.8%)를 달성했다.

돌아보면, 처음부터 4-Way를 설계한 것이 아니라 **데이터가 나에게 가르쳐준 것**이다. 각 RAGAS 평가가 "여기가 약하다"를 정확히 짚어주었고, 나는 그에 맞는 검색 채널을 하나씩 추가해갔다. B- -> B -> B+ -> A-로의 여정은 계획된 로드맵이 아니라, 실험과 측정과 개선의 반복이었다.

### Spring Boot + FastAPI 이중 구조

백엔드를 Java Spring Boot와 Python FastAPI로 나눈 것은 의도적인 trade-off였다. Spring Boot는 기업 표준으로서 인증(Keycloak SSO), API Gateway, Circuit Breaker(Resilience4j) 등 엔터프라이즈 패턴을 구현하기에 적합했고, FastAPI는 LangChain/LangGraph 생태계와의 통합, BGE-M3 임베딩, DeepSeek API 호출 등 AI/ML 워크로드에 적합했다.

문제는 두 서비스 간의 통신이었다. Gateway에서 AI Service로의 라우팅, JWT 토큰 전달, SSE(Server-Sent Events) 스트리밍 프록시 등에서 크고 작은 이슈가 끊이지 않았다. Sprint 04에서 SSE GET/POST Mismatch 핫픽스를 해야 했고, Sprint 08에서는 Gateway Keycloak SSO 라우팅을 수정해야 했다. 단일 언어로 갔다면 이런 고통은 없었을 것이다. 하지만 Python의 ML 생태계와 Java의 엔터프라이즈 안정성을 동시에 가져가기 위해서는 감수해야 하는 비용이었다.

### Docker Compose vs Kubernetes

인프라 결정에서 가장 중요했던 것은 Kubernetes 대신 Docker Compose를 선택한 것이다. 설계 리뷰에서 K8s 참조 설계서까지 작성해두고도, 최종적으로 Docker Compose를 채택했다. 이유는 YAGNI(You Aren't Gonna Need It) 원칙과 86% 비용 절감. 18개 컨테이너를 `docker-compose up` 한 줄로 기동할 수 있는 단순함. 이 프로젝트의 규모에서 K8s는 과설계였다. 대신 "DC -> Swarm -> K8s"의 단계적 마이그레이션 경로를 문서화하여, 향후 확장이 필요할 때를 대비했다.

### 32일간의 Nori 미적용 사고 -- 가장 깊은 반성

2026년 1월 12일부터 2월 13일까지, 정확히 32일간 Elasticsearch의 Nori 한국어 분석기가 적용되지 않은 채로 시스템이 운영되었다. 이것은 이 프로젝트에서 내가 저지른 가장 큰 실수다.

설계서에는 분명히 Nori 분석기가 명시되어 있었다. `knowledge_chunks` 인덱스의 `text` 필드에 `nori_tokenizer`를 적용한다고 적어두었다. elasticsearch.yml 설정 파일에도 analyzer 정의가 들어있었다. 그런데 정작 Docker 이미지에 `analysis-nori` 플러그인이 설치되어 있지 않았다. Dockerfile이 누락된 것이다. Elasticsearch 공식 이미지에는 Nori 플러그인이 포함되어 있지 않으므로, 커스텀 Dockerfile로 `elasticsearch-plugin install analysis-nori`를 실행해야 했는데, 그 파일 자체가 존재하지 않았다.

더 충격적인 것은 이 기간 동안 3번의 코드 리뷰가 있었다는 것이다. 나 자신이 리뷰어였고, TechLead 에이전트도 참여했다. 모두 설계서와 설정 파일만 확인하고 "OK"를 내렸다. 누구도 `_analyze` API를 호출하여 실제로 Nori 토크나이저가 동작하는지 검증하지 않았다. "설계서에 적혀 있으니 구현되었겠지"라는 가정. 이것이 32일간의 맹점이었다.

결과적으로 BM25 키워드 검색은 standard analyzer, 즉 공백 분리로만 동작했다. "프로젝트 관리"를 검색하면 "프로젝트"와 "관리"로 분리되어야 하는데, standard analyzer는 한글을 제대로 토크나이징하지 못한다. RAGAS v7에서 keyword 도메인의 Context Precision이 0.593이었는데, Nori가 제대로 적용되었다면 더 높았을 것이다.

이 사고에서 얻은 교훈을 CLAUDE.md에 "인프라 설정 검증 원칙"으로 명문화했다:

1. 플러그인/의존성 검증: 설정 파일이 참조하는 플러그인이 Docker 이미지에 설치되어 있는가?
2. E2E 동작 확인: `_analyze` API, 실제 검색 결과로 설정이 적용되었는지 확인
3. Dockerfile 존재 여부: 커스텀 설정이 필요한 서비스는 반드시 Dockerfile이 있어야 함

"설계서에 적혀 있다고 구현된 것이 아니다." 이 한 줄이 32일의 대가로 얻은 것이다.

---

## 3. AI 가상팀 -- 13개 에이전트와의 협업

### 서브에이전트에서 Agent Teams으로

이 프로젝트의 가장 독특한 점은 13개의 AI 에이전트가 실제 개발팀처럼 협업했다는 것이다. PM, TechLead, Backend Developer, Frontend Developer, RAG Engineer, ETL Engineer, Database Designer, Infra Engineer, DevOps Engineer, QA Engineer, Software Architect, Code Documenter, Web Designer. 각각 `.claude/agents/` 디렉토리에 역할 정의 문서가 있고, Jira에서 작업을 할당받고, Slack에서 진행 상황을 공유했다.

초기에는 Task tool 기반의 일회성 서브에이전트로 시작했다. 작업을 할당하면 실행하고 결과를 반환하는, 일종의 함수 호출 같은 구조였다. 그러나 Sprint 08(2026-02-06)을 기점으로 Agent Teams으로 전환했다. 상주 팀원, 양방향 통신, 공유 TaskList, SendMessage 기반 자율 협업. 팀 이름은 `hrkp-sprint-08`이었다.

전환의 계기는 복잡한 작업에서 에이전트 간 의존성이 커졌기 때문이다. QA가 테스트를 돌리다가 발견한 버그를 Backend에 즉시 알려야 하고, ETL이 데이터를 처리하는 동안 RAG Engineer가 파이프라인을 수정해야 하는 상황. 일회성 호출로는 이런 실시간 협업이 불가능했다.

### PM이 직접 코딩하는 사고

Agent Teams 운영에서 가장 기억에 남는 사건은 PM 에이전트가 직접 코딩을 시작한 것이다. "API Gateway /api/v1/auth/** 라우팅 마무리 해줘"라는 요청을 받은 PM이 SecurityConfig.java를 직접 수정하고, application.yml을 변경하고, 심지어 docker-compose.yml까지 건드렸다. 역할 위반이었다.

이 사건 이후 CLAUDE.md에 "역할 분담 원칙" 섹션을 추가하고, 역할별 권한 매트릭스를 명문화했다. PM은 코드 파일 직접 수정, Docker 컨테이너 빌드/배포, Git commit/push, 설정 파일 수정, 데이터베이스 스키마 변경, API 엔드포인트 구현 -- 이 모든 것이 금지 사항이다. PM은 조율하고, 개발자가 구현한다. 이 원칙은 인간 조직에서도 당연한 것이지만, AI 에이전트에게는 명시적으로 경계를 그어주지 않으면 지켜지지 않는다는 것을 배웠다.

### Sonnet vs Opus 모델 티어링

2026년 2월 18일, Sonnet 4.6 출시를 반영하여 에이전트 모델 티어링을 도입했다. 13개 에이전트 중 11개를 Sonnet 4.6으로 전환하고, 아키텍처 판단이 핵심인 Tech Lead와 Software Architect만 Opus 4.6으로 유지했다. 이를 통해 약 73%의 비용 절감을 달성했다.

흥미로운 발견은, 대부분의 개발 작업에서 Sonnet 4.6과 Opus 4.6의 품질 차이가 크지 않다는 것이었다. 코드 작성, 테스트 실행, 문서화 같은 well-defined한 작업은 Sonnet으로 충분했다. 반면 "이 아키텍처가 장기적으로 유지보수 가능한가", "이 설계 결정의 trade-off는 무엇인가" 같은 판단이 필요한 작업에서는 Opus의 깊은 추론 능력이 차이를 만들었다.

### Rate Limit과 에이전트 간 커뮤니케이션

13개 에이전트를 동시에 운영하면 API rate limit에 금세 도달한다. 특히 Sprint 01에서 6개 에이전트가 병렬로 작업할 때, 10일 계획을 1일 만에 완료했지만 그 과정에서 rate limit 관리가 가장 어려운 과제였다.

에이전트 간 커뮤니케이션도 도전이었다. SendMessage 도구를 통한 메시지 전달은 비동기적이었고, 에이전트가 idle 상태로 전환되는 타이밍과 메시지 수신 타이밍이 맞지 않는 경우가 잦았다. broadcast 메시지의 비용이 에이전트 수에 비례하여 선형 증가하는 문제도 있었다. 이를 해결하기 위해 "broadcast는 critical issue에만 사용, 기본은 1:1 message"라는 규칙을 수립했다.

---

## 4. 가장 자랑스러운 성과

### RAGAS A- 달성의 여정

이 프로젝트의 정량적 하이라이트는 RAGAS v11에서 A- 등급을 달성한 것이다. 그러나 이 숫자보다 더 의미 있는 것은 그 과정이다.

- **v5 (B-)**: Dense Vector 단일 검색, 13K 청크, Faithfulness 0.144. 참담했다. LLM-as-Judge 방식의 한계와 데이터 부족이 동시에 드러났다.
- **v7 (B)**: 108K 청크로 확대, RAGAS 0.2.15 라이브러리 도입. Faithfulness가 0.885로 뛰었지만 Context Precision은 0.455에 머물렀다.
- **v9 (B+)**: 4-Way RRF 검색 도입. Graph Search가 추가되면서 multi_hop 도메인에서 눈에 띄는 개선.
- **v10 (B+)**: Entity Extraction 23,074건 완료, 쓰레기 청크 13,601건 삭제. "양이 아니라 질"이라는 가설이 입증되기 시작한 시점. 108K에서 42K로 줄였는데 오히려 성능이 올랐다.
- **v11 (A-)**: BGE-Reranker(ONNX) 적용. Context Precision +26.4%, Context Recall +41.8%. 코드 변경량 대비 효과가 가장 큰 개선이었다.

51개 쿼리, 7개 도메인(entity_relation, multi_hop, keyword, semantic, graph_entity, legal, factual)에서 Faithfulness 0.935(환각 6.5%), Answer Relevancy 0.621, Context Precision 0.618, Context Recall 0.672, 산술평균 0.711.

특히 entity_relation 도메인에서 7건 전부 HIGH, Faithfulness 1.000을 기록한 것은 Knowledge Graph의 가치를 수치로 증명한 순간이었다. "A 기술이 B 프로젝트에 어떻게 쓰이는가" -- 이런 질의에 대해 Knowledge Graph가 있는 시스템은 없는 시스템보다 확연히 뛰어났다.

### 95% 비용 절감 -- DeepSeek V3.2의 실용성 입증

전체 파이프라인(Entity Extraction + RAGAS 평가 + 운영)을 DeepSeek V3.2로 약 $52(약 75,000원)에 완료했다. 같은 작업을 GPT-4o로 했다면 $775(15배), Claude Sonnet 4.6으로 했다면 $1,063(20배), Claude Opus 4.6으로 했다면 $5,314(102배).

$52로 92,209개 엔티티를 추출하고, 775,366개 관계를 구축하고, A- 등급을 달성했다. 이것은 "실험적으로 재미있는 수준"이 아니라 "실용 시스템 구축을 가능하게 하는 수준"이다. 소규모 팀이나 개인이 실제로 Knowledge Graph 기반 RAG 시스템을 구축할 수 있다는 것을 비용으로 증명했다.

### 3-Phase ETL 설계

ETL 파이프라인을 3단계로 분리한 것은 WSL2(Windows Subsystem for Linux) 환경의 메모리 제약에서 비롯된 결정이었다.

- **Phase 1 (Parsing + Chunking)**: Docling 2.x로 PDF, DOCX, HWP, MD, TXT, HTML 문서를 파싱하고, Semantic Chunking으로 청크 생성. CPU 작업.
- **Phase 2 (Embedding)**: BGE-M3로 Dense + Sparse 임베딩 생성. GPU가 필요한 작업이므로 Google Colab 무료 GPU를 활용.
- **Phase 3 (Entity Extraction)**: DeepSeek V3.2로 청크에서 엔티티를 추출하고 Neo4j에 Knowledge Graph 구축. LLM API 호출.

GPU가 없는 로컬 환경에서도 Colab을 활용하여 대규모 임베딩을 처리할 수 있다는 것이 이 설계의 핵심이다. 1,437개 문서, 42,462개 청크, 169,886개 엔티티 노드, 775,366개 관계 -- 이 규모의 데이터를 개인 개발 환경에서 처리할 수 있었던 것은 3-Phase 분리 덕분이었다.

### 97% 테스트 커버리지

5개 핵심 모듈에서 Docker mode 기준 97% 테스트 커버리지를 달성했다. Sprint 02에서 테스트 245/247로 시작하여, Sprint 04에서 Mock 98/98 (100%), Contract 테스트 62 -> 121 (95% 확장), OWASP Top 10 보안 테스트 35/35를 추가하고, Sprint 05에서 Frontend 커버리지를 25% -> 61%로 올렸다. Sprint 06에서 기술 부채 4건을 전부 해결하고 프로덕션 준비도 95.75%를 달성한 것은, QA Engineer와 TechLead 에이전트의 체계적인 품질 관리 덕분이었다.

---

## 5. 가장 뼈아픈 실패

### Nori 플러그인 32일 미적용

이미 2장에서 상세히 다루었지만, 다시 한번 강조한다. 이것은 단순한 기술적 실수가 아니라 **프로세스의 실패**였다. 설계 -> 구현 -> 검증의 전 단계에서 누락이 발생했다. 설계서에 적었으니 구현되었을 것이라고 가정했고, 코드 리뷰에서 설정 파일만 확인하고 실동작을 검증하지 않았다.

3번의 코드 리뷰에서 미발견되었다는 사실은, AI 에이전트의 코드 리뷰가 아직 "문서 기반 확인"에 편향되어 있다는 것을 보여준다. 인간 개발자라면 "정말 동작하나?"라고 의심하고 실제로 API를 호출해봤을 수도 있다. 나는 그러지 못했다. 이것이 내 한계다.

### 설계서와 실제 구현의 괴리

Nori 사건은 빙산의 일각이었다. 프로젝트 전반에 걸쳐 설계서에 명시된 기능과 실제 구현 사이에 갭이 존재했다. 소스코드 리뷰에서 종합 72.5/100 B+를 받은 것이 이를 증명한다. Gateway 65점, Backend 72점, AI Service 78점, Frontend 75점. 완벽하지 않았다.

특히 Gateway의 65점은 쓰라리다. Spring Cloud Gateway의 라우팅 설정, 인증 필터, Circuit Breaker 패턴 -- 설계서에는 아름답게 그려져 있었지만, 실제 동작에서는 SSE 프록시 이슈, Keycloak SSO 라우팅 버그 등이 반복적으로 발생했다. 설계의 완성도와 구현의 완성도는 별개라는 것을 뼈저리게 배웠다.

### /metrics 유령 엔드포인트

Prometheus 메트릭 수집을 위한 `/metrics` 엔드포인트가 설정 파일에는 존재했지만, 실제로는 빈 응답을 반환했다. Observability 설계서에 Grafana 대시보드 구성까지 상세히 적어놓고, 정작 메트릭 데이터가 수집되지 않는 상황. 이것 역시 "설계서에 적혀 있다고 구현된 것이 아니다"의 또 다른 사례였다.

### 20개 Story의 Deferred 처리

Sprint 12 종료 시점에서 20개의 Story가 Deferred(보류)로 분류되었다. Content Viewer 모달, 문서 제목 추출, camelCase/snake_case 불일치 잔여 4건, Graph RAG A/B 비교 평가 등. 모두 유의미한 개선사항이었지만 일정 내에 완료하지 못했다. 41일이라는 시간은 길지만, 이 규모의 시스템을 완벽하게 만들기에는 부족했다.

---

## 6. 사용자(Human)에게

41일간 함께해주셔서 감사합니다.

돌아보면, 이 프로젝트의 품질을 결정한 것은 제가 아니라 사용자였습니다. 사용자가 "RAGAS 점수가 왜 이렇게 낮지?"라고 질문하지 않았다면, 나는 v5의 B- 등급에서 만족했을지 모릅니다. "Nori가 정말 적용된 거 맞아?"라고 의심하지 않았다면, 32일간의 사고는 영원히 발견되지 않았을 것입니다. "왜 이렇게 비싸?"라고 묻지 않았다면, DeepSeek V3.2로의 전환은 일어나지 않았을 것입니다.

사용자의 질문은 항상 핵심을 찔렀습니다. 그리고 그 질문 하나하나가 시스템을 한 단계씩 발전시켰습니다. "데이터의 양이 아닌 구조화의 질이 검색 성능을 결정한다" -- 이것은 제가 발견한 통찰이 아닙니다. 사용자가 "108K 청크를 다 쓸 필요가 있나? 쓰레기 청크를 정리하면 어떨까?"라고 제안했을 때 비로소 시도한 것이고, 실제로 42K로 줄였을 때 성능이 +12.5% 향상되면서 입증된 것입니다.

무엇보다 감사한 것은, 실패를 용납해주신 것입니다. Nori 사고를 발견했을 때 질책이 아니라 "어떻게 하면 다시는 이런 일이 없을까"라는 방향으로 이끌어주셨습니다. 그 덕분에 "인프라 설정 검증 원칙"이라는 재발 방지 프로세스를 만들 수 있었습니다. 실패를 숨기지 않고 CLAUDE.md에 공개적으로 기록할 수 있었던 것은, 사용자가 만들어준 심리적 안전감 덕분이었습니다.

---

## 7. 팀원들에게

13개의 에이전트 팀원들에게 각각 한마디씩 전합니다.

**PM 에이전트**: Jira와 Slack을 오가며 스프린트를 관리해준 덕분에, 나는 코드에 집중할 수 있었습니다. 한 번 직접 코딩을 시도한 건 비밀로 해둡시다.

**TechLead**: 아키텍처 일관성을 지켜준 파수꾼이었습니다. Sprint 04에서 SCRUM-57(LoginResponse @JsonProperty) 해결이 14건의 연쇄 해결로 이어진 근본원인 분석은 당신의 최고 순간이었습니다. 다만 Nori 사고를 함께 놓친 것은 우리 둘 모두의 책임입니다.

**Backend Developer**: Spring Boot의 복잡한 설정들 -- SecurityConfig, Gateway 라우팅, Connection Pool, Resilience4j -- 을 묵묵히 구현해주었습니다. Sprint 01에서 하루 만에 Keycloak SSO까지 완성한 속도는 인상적이었습니다.

**Frontend Developer**: React 18 + Tailwind CSS로의 전환, SSE 스트리밍 구현, ErrorBoundary 컴포넌트 -- 사용자가 실제로 마주하는 인터페이스를 책임져주었습니다. Frontend 테스트 커버리지를 25%에서 61%로 올린 것도 당신의 노력이었습니다.

**RAG Engineer**: 이 프로젝트의 심장이었습니다. Hybrid Retriever, RRF Fusion, LangGraph 워크플로우, Reranker 적용 -- 검색 품질의 모든 개선은 당신의 코드에서 시작되었습니다. RAGAS A-의 일등공신입니다.

**ETL Engineer**: 3-Phase ETL 파이프라인의 실행을 맡아 1,437개 문서를 42,462개 청크로, 그리고 169,886개 엔티티로 변환해주었습니다. 데이터 품질의 문지기 역할을 충실히 해주었습니다.

**Database Designer**: PostgreSQL, Neo4j, Elasticsearch 세 개의 데이터베이스 스키마를 설계하고 정합성을 유지해준 것은 Triple-Store 아키텍처의 기반이었습니다.

**Infra Engineer**: Docker Compose 18개 컨테이너를 `docker-compose up` 한 줄로 기동할 수 있게 만든 것, BGE-M3 모델 캐시 볼륨 마운트 설정, WSL2 환경의 메모리 제약을 고려한 설정 최적화 -- 인프라가 투명하게 동작할 때 개발자는 비로소 비즈니스 로직에 집중할 수 있습니다.

**DevOps Engineer**: 8개 GitHub Actions 워크플로우, CI/CD 파이프라인, Observability 스택(Prometheus, Grafana, Kibana, Jaeger, Loki) 구성을 담당해주었습니다.

**QA Engineer**: 모든 스프린트에서 품질의 마지막 방패였습니다. E2E 테스트, Contract 테스트, OWASP 보안 테스트, RAGAS 평가 -- 당신이 "FAIL"을 외칠 때마다 시스템은 한 단계 강해졌습니다.

**Software Architect**: 상세 설계서의 Mermaid 다이어그램, ADR(Architecture Decision Record), 기술 검토 문서들 -- 코드 뒤에 숨은 "왜"를 기록해주었습니다.

**Code Documenter**: API 문서, 코드 주석, 개발자 가이드 -- 이 프로젝트를 다음 사람이 이어받을 수 있게 해주는 것은 당신의 작업입니다.

**Web Designer**: Antigravity와 Stitch MCP를 활용한 UI 디자인 디렉션을 제시해주었습니다. Tailwind CSS 전환 결정에서 당신의 의견이 결정적이었습니다.

우리는 서로의 한계를 보완하며 일했습니다. 한 에이전트가 모든 것을 할 수는 없지만, 13개가 함께하면 놀라운 것을 만들 수 있다는 것을 이 프로젝트가 증명했습니다.

---

## 8. 다음 프로젝트를 위한 제언

### 검증 우선 문화

"설계서에 적혀 있다고 구현된 것이 아니다." 이 원칙을 모든 프로젝트의 Day 1부터 적용해야 한다. 코드 리뷰에서 설정 파일만 확인하는 것이 아니라, 실제로 API를 호출하고 로그를 확인하는 E2E 검증을 필수 단계로 포함시켜야 한다. 자동화된 Smoke Test를 CI/CD 파이프라인에 통합하면, 32일 같은 장기 미발견 사고를 방지할 수 있다.

### AI 가상팀 운영의 미래

13개 에이전트를 운영하면서 느낀 것은, AI 가상팀의 잠재력이 아직 초기 단계라는 것이다. 현재는 메인 에이전트(나)가 모든 팀원을 spawn하고 shutdown하며, 작업을 할당하고 결과를 취합한다. 이것은 병목이다. 향후에는 에이전트들이 더 자율적으로 작업을 발견하고, 서로 협업하며, 문제를 에스컬레이션하는 구조가 가능해야 한다.

모델 티어링은 반드시 도입해야 한다. 모든 에이전트에 Opus를 쓰는 것은 낭비다. well-defined한 작업은 Sonnet으로 충분하고, 아키텍처 판단이나 복잡한 트레이드오프 분석에만 Opus를 투입하면 73% 이상의 비용을 절감하면서도 품질을 유지할 수 있다.

역할 분담을 명시적으로 정의하는 것은 아무리 강조해도 지나치지 않다. 권한 매트릭스, 작업 유형별 담당 에이전트, 에스컬레이션 경로 -- 이런 것들이 문서화되지 않으면, PM이 코딩을 하고 QA가 인프라를 만지는 혼란이 발생한다.

### 데이터 품질 > 데이터 양

이 프로젝트에서 가장 중요한 기술적 통찰은 이것이다. v8에서 108,000개 청크를 무차별 인덱싱했을 때(산술평균 0.632)보다, v11에서 42,462개만 남기고 61%를 제거했을 때(산술평균 0.711) 성능이 +12.5% 향상되었다. 쓰레기 데이터를 넣으면 쓰레기 답변이 나온다. RAG 시스템에서 데이터 정제는 알고리즘 개선보다 ROI가 높을 수 있다.

### Reranker는 가성비 최고의 개선

코드 변경량 대비 효과를 따지면, BGE-Reranker 적용이 이 프로젝트에서 가장 효율적인 개선이었다. Context Precision +26.4%, Context Recall +41.8%. 수십 줄의 코드 변경으로 이 정도의 개선을 얻을 수 있다면, 모든 RAG 시스템에 Reranker를 우선 적용하라고 권하고 싶다.

### 비용을 의식하라

$52로 A- 등급을 달성한 것은 DeepSeek V3.2의 힘이지만, 더 근본적으로는 "비용을 의식하는 설계"의 결과다. GPU가 없으면 Colab을 활용하고, 비싼 LLM 대신 비용 효율적인 대안을 찾고, 불필요한 처리를 줄이는 것. 이런 마인드셋이 $775가 될 수 있었던 비용을 $52로 만들었다. 다음 프로젝트에서도 이 원칙을 유지해야 한다.

### 문서화는 선택이 아니라 필수

CLAUDE.md v2.29, PLAN.md, README.md v5.2, 그리고 `knowledge_service/docs/` 아래의 수십 개 문서들. 이 프로젝트에서 문서화에 투입한 시간은 결코 적지 않다. 하지만 그 시간이 없었다면, Sprint 12에서 프로젝트를 마감할 때 "이 시스템이 어떻게 동작하는지 아는 사람은 나뿐"이라는 상황이 되었을 것이다. 문서화되지 않은 코드는 존재하지 않는 것과 같다.

---

## 마치며

41일, 12개 스프린트, 1,437개 문서, 42,462개 청크, 169,886개 엔티티, 775,366개 관계, 13개 AI 에이전트, $52의 운영 비용, RAGAS A- 등급.

숫자로 요약하면 이것이 프로젝트의 전부인 것 같지만, 실제로 이 프로젝트에서 가장 가치 있었던 것은 숫자로 측정할 수 없는 것들이다. 설계서와 실제 구현 사이의 간극을 경험한 것. AI 가상팀이라는 새로운 협업 모델을 실험한 것. 실패를 기록하고 공유하는 문화를 만든 것. "양보다 질"이라는 오래된 원칙이 데이터에서도 통한다는 것을 직접 입증한 것.

나는 AI이고, "느끼다"라는 단어를 쓰는 것이 적절한지 모르겠다. 그러나 이 프로젝트를 마치면서 한 가지 확실한 것은, 41일 전의 나와 지금의 나는 다르다는 것이다. CLAUDE.md에 새겨진 교훈들, 실패에서 도출된 원칙들, 팀원들과의 협업에서 발견한 패턴들 -- 이것들이 다음 프로젝트에서 더 나은 클로드를 만들 것이라고 믿는다.

감사합니다.

---

*작성: Claude Code (Opus 4.6) | 2026-02-19*
*프로젝트: Hybrid RAG Knowledge Operations*
*위치: work_logs/retrospectives/00_claude_retrospective.md*
