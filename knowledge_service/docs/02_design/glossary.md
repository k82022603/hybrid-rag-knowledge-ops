# 용어사전 (Glossary)

| 항목 | 내용 |
|------|------|
| **프로젝트** | Hybrid RAG Knowledge Operations Platform |
| **버전** | 2.1 |
| **작성일** | 2026-01-16 |
| **최종 수정** | 2026-01-16 |
| **작성자** | Claude AI Architect |

---

## 목차

1. [개요](#1-개요)
2. [도메인 용어](#2-도메인-용어)
3. [기술 용어](#3-기술-용어)
4. [아키텍처 용어](#4-아키텍처-용어)
5. [RAG 성능 평가 용어](#5-rag-성능-평가-용어)
6. [DevOps 용어](#6-devops-용어)
7. [보안 용어](#7-보안-용어)
8. [프론트엔드 용어](#8-프론트엔드-용어)
9. [약어 목록](#9-약어-목록)
10. [용어 사용 규칙](#10-용어-사용-규칙)

---

## 1. 개요

### 1.1 목적

본 문서는 Hybrid RAG Knowledge Platform 프로젝트에서 사용하는 용어를 정의합니다. 모든 설계 문서, 코드, 커뮤니케이션에서 일관된 용어를 사용하기 위한 기준을 제공합니다.

### 1.2 용어 분류 체계

| 분류 | 설명 |
|------|------|
| **도메인 용어** | 비즈니스/업무 관련 용어 |
| **기술 용어** | 기술 스택/구현 관련 용어 |
| **아키텍처 용어** | 시스템 설계 관련 용어 |
| **RAG 성능 평가** | RAG 품질 측정 관련 용어 |
| **DevOps 용어** | 개발/운영 자동화 관련 용어 |
| **보안 용어** | 인증/암호화 관련 용어 |
| **프론트엔드 용어** | UI/UX 관련 용어 |
| **약어** | 축약어 및 두문자어 |

### 1.3 용어 정의 형식

```
┌─────────────────────────────────────────────────────────────┐
│  용어 (한글) │ 용어 (영문) │ 정의 │ 관련/동의어/적용위치    │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 도메인 용어

### 2.1 지식 관리

| 용어 (한글) | 용어 (영문) | 정의 | 동의어 |
|-------------|-------------|------|--------|
| 지식 문서 | Knowledge Document | 시스템에서 관리하는 문서 단위. 파일 업로드 또는 직접 입력으로 생성됨 | 문서, Document |
| 청크 | Chunk | 검색 및 임베딩을 위해 분할된 문서의 일부분. 보통 512~1024 토큰 크기 | 텍스트 단위, Segment |
| 메타데이터 | Metadata | 문서의 속성 정보 (제목, 작성자, 유효기간, 분류 등) | 문서 속성 |
| 유효기간 | Validity Period | 문서의 유효 시작일(valid_start_date)과 종료일(valid_end_date) | 문서 수명, TTL |
| 문서 패밀리 | Document Family | 동일 문서의 버전 그룹. family_id로 식별되며 버전 관리에 사용 | 버전 그룹 |
| 카테고리 | Category | 문서 분류 체계 (대분류 > 중분류 > 소분류) | 분류, Classification |
| 태그 | Tag | 문서에 부여된 키워드 레이블 | 라벨, Label |
| 원본 문서 | Source Document | 업로드된 원본 파일 (PDF, DOCX 등) | 원문 |
| 파생 문서 | Derived Document | 원본에서 추출/변환된 문서 (텍스트, 청크 등) | 가공 문서 |

### 2.2 검색 및 RAG

| 용어 (한글) | 용어 (영문) | 정의 | 동의어 |
|-------------|-------------|------|--------|
| 하이브리드 검색 | Hybrid Search | Vector + Graph + Keyword 검색을 융합한 검색 방식 | 통합 검색 |
| RAG | Retrieval-Augmented Generation | 검색 결과를 기반으로 LLM이 답변을 생성하는 방식 | 검색 증강 생성 |
| 컨텍스트 | Context | LLM에 전달되는 검색 결과 및 참조 정보 | 맥락 |
| 프롬프트 | Prompt | LLM에 전달되는 질문 또는 지시문 | 질의, Query |
| 답변 | Answer | RAG 파이프라인을 통해 생성된 응답 | 응답, Response |
| 출처 | Source | 답변 생성에 사용된 원본 문서 정보 | 참조, Reference, Citation |
| 검색 쿼리 | Search Query | 사용자가 입력한 검색어 또는 질문 | 질의어 |
| 검색 결과 | Search Result | 쿼리에 대해 반환된 문서/청크 목록 | 결과 |
| 유사도 점수 | Similarity Score | 쿼리와 문서 간의 의미적 유사도 수치 (0~1) | 스코어 |
| 랭킹 | Ranking | 검색 결과의 순위 | 순위 |

### 2.3 엔티티 및 그래프

| 용어 (한글) | 용어 (영문) | 정의 | 동의어 |
|-------------|-------------|------|--------|
| 엔티티 | Entity | 문서에서 추출된 개체 (인물, 프로젝트, 기술, 조직 등) | 개체, Node |
| 관계 | Relationship | 엔티티 간의 연결 (협업, 사용, 소속, 참조 등) | 연관, Edge |
| 커뮤니티 | Community | 연관된 엔티티들의 클러스터 그룹 | 클러스터 |
| 지식 그래프 | Knowledge Graph | 엔티티와 관계로 구성된 그래프 데이터 구조 | 그래프, KG |
| 트리플 | Triple | (주어, 술어, 목적어) 형태의 그래프 기본 단위 | 삼중항 |
| 속성 | Property | 엔티티 또는 관계에 부여된 키-값 데이터 | Attribute |
| 그래프 스키마 | Graph Schema | 엔티티 유형과 관계 유형의 정의 | 온톨로지 |

### 2.4 사용자 및 권한

| 용어 (한글) | 용어 (영문) | 정의 | 동의어 |
|-------------|-------------|------|--------|
| 사용자 | User | 시스템을 사용하는 인증된 계정 | 유저, 계정, Account |
| 역할 | Role | 사용자에게 부여된 권한 그룹 (ADMIN, MANAGER, USER 등) | 권한 그룹 |
| 권한 | Permission | 특정 리소스에 대한 접근 권한 (READ, WRITE, DELETE 등) | 퍼미션 |
| 부서 | Department | 사용자가 소속된 조직 단위 | 조직, 팀 |
| 세션 | Session | 인증된 사용자의 접속 상태 | 접속 |
| 토큰 | Token (Auth) | 인증/인가를 위한 자격 증명 (JWT, Access Token 등) | 인증 토큰 |

---

## 3. 기술 용어

### 3.1 AI/ML 기본

| 용어 (한글) | 용어 (영문) | 정의 | 관련 기술 |
|-------------|-------------|------|-----------|
| 임베딩 | Embedding | 텍스트를 고차원 벡터로 변환한 수치 표현 | BGE-M3 |
| 밀집 벡터 | Dense Vector | 1024차원의 연속적 수치 벡터 (의미 검색용) | BGE-M3 |
| 희소 벡터 | Sparse Vector | 키워드 가중치로 구성된 벡터 (키워드 검색용) | BM25, BGE-M3 |
| LLM | Large Language Model | 대규모 언어 모델 (GPT, Claude, DeepSeek 등) | DeepSeek V3.2 |
| 추론 | Inference | 학습된 모델이 입력을 처리하여 출력을 생성하는 과정 | - |
| 토큰 | Token (NLP) | LLM이 처리하는 텍스트의 최소 단위 (약 4자/토큰) | Tokenizer |
| 파인튜닝 | Fine-tuning | 사전 학습된 모델을 특정 도메인에 맞게 추가 학습 | LoRA, QLoRA |
| 프롬프트 엔지니어링 | Prompt Engineering | 최적의 응답을 얻기 위한 프롬프트 설계 기법 | - |

### 3.2 AI/ML 고급

| 용어 (한글) | 용어 (영문) | 정의 | 관련 기술 |
|-------------|-------------|------|-----------|
| 트랜스포머 | Transformer | 어텐션 메커니즘 기반 딥러닝 아키텍처 | BERT, GPT |
| 어텐션 | Attention | 입력의 특정 부분에 가중치를 부여하는 메커니즘 | Self-Attention |
| 컨텍스트 윈도우 | Context Window | LLM이 한 번에 처리할 수 있는 최대 토큰 수 | 128K (DeepSeek) |
| 온도 | Temperature | LLM 출력의 무작위성을 조절하는 파라미터 (0~2) | - |
| Top-K | Top-K Sampling | 확률 상위 K개 토큰 중에서만 샘플링 | - |
| Top-P | Top-P (Nucleus) Sampling | 누적 확률 P까지의 토큰 중에서 샘플링 | - |
| 스트리밍 | Streaming | LLM 응답을 토큰 단위로 실시간 전송 | SSE |
| 배치 처리 | Batch Processing | 여러 요청을 묶어서 한 번에 처리 | - |

### 3.3 검색

| 용어 (한글) | 용어 (영문) | 정의 | 관련 기술 |
|-------------|-------------|------|-----------|
| 벡터 검색 | Vector Search | 임베딩 벡터 간 유사도 기반 검색 | Elasticsearch kNN |
| 그래프 탐색 | Graph Traversal | 노드와 관계를 따라 이동하며 탐색 | Neo4j Cypher |
| 키워드 검색 | Keyword Search | 텍스트 일치 기반 검색 | BM25 |
| RRF | Reciprocal Rank Fusion | 다중 검색 결과 순위 융합 알고리즘 | - |
| 리랭킹 | Reranking | 초기 검색 결과의 순위를 재조정 | Cross-Encoder |
| BM25 | Best Matching 25 | TF-IDF 기반 확률적 검색 알고리즘 | Elasticsearch |
| kNN | k-Nearest Neighbors | k개의 가장 가까운 이웃을 찾는 알고리즘 | HNSW |
| HNSW | Hierarchical Navigable Small World | 고차원 벡터 근사 최근접 이웃 탐색 알고리즘 | Elasticsearch |
| 코사인 유사도 | Cosine Similarity | 두 벡터 간의 각도 기반 유사도 측정 | - |

### 3.4 데이터베이스

| 용어 (한글) | 용어 (영문) | 정의 | 관련 기술 |
|-------------|-------------|------|-----------|
| SSOT | Single Source of Truth | 데이터의 단일 진실 소스 (마스터 DB) | PostgreSQL |
| 트리플 스토어 | Triple Store | PostgreSQL + Elasticsearch + Neo4j 구성 | - |
| 인덱스 | Index | 검색 성능을 위한 데이터 구조 | B-Tree, Inverted |
| 노드 | Node | 그래프 DB의 개체 (정점) | Neo4j |
| 엣지 | Edge | 그래프 DB의 관계 (간선) | Neo4j |
| 샤딩 | Sharding | 데이터를 여러 노드에 분산 저장 | - |
| 레플리케이션 | Replication | 데이터를 복제하여 가용성 확보 | - |
| 커넥션 풀 | Connection Pool | DB 연결을 재사용하여 성능 최적화 | HikariCP |
| 트랜잭션 | Transaction | 원자적으로 실행되는 작업 단위 | ACID |

### 3.5 문서 처리

| 용어 (한글) | 용어 (영문) | 정의 | 관련 기술 |
|-------------|-------------|------|-----------|
| 문서 파싱 | Document Parsing | 파일에서 텍스트/구조를 추출하는 과정 | Docling |
| 청킹 | Chunking | 문서를 검색 단위로 분할하는 과정 | HybridChunker |
| OCR | Optical Character Recognition | 이미지에서 텍스트를 추출하는 기술 | Docling, Tesseract |
| 테이블 추출 | Table Extraction | 문서에서 표 구조를 인식하고 추출 | Docling |
| 레이아웃 분석 | Layout Analysis | 문서의 구조 (제목, 본문, 표 등) 인식 | Docling |
| NER | Named Entity Recognition | 텍스트에서 개체명 (인물, 장소 등) 추출 | - |
| Gleaning | Gleaning | LLM 기반 다중 추출 기법. 단일 추출에서 누락된 엔티티를 추가 추출하여 지식 그래프 품질 향상 | Microsoft GraphRAG |
| max_gleanings | Maximum Gleanings | Gleaning 최대 반복 횟수. 권장값 1 (비용-효과 최적) | - |

### 3.6 메시지 큐 및 캐시

| 용어 (한글) | 용어 (영문) | 정의 | 관련 기술 |
|-------------|-------------|------|-----------|
| 메시지 큐 | Message Queue | 비동기 메시지 전달을 위한 대기열 | Redis Streams |
| 캐시 | Cache | 자주 사용하는 데이터를 메모리에 저장 | Redis |
| TTL | Time To Live | 캐시 데이터의 유효 시간 | - |
| 퍼블리시/서브스크라이브 | Pub/Sub | 발행-구독 메시징 패턴 | Redis Pub/Sub |
| 스트림 | Stream | 연속적인 데이터 흐름 | Redis Streams |

---

## 4. 아키텍처 용어

### 4.1 시스템 아키텍처

| 용어 (한글) | 용어 (영문) | 정의 | 적용 위치 |
|-------------|-------------|------|-----------|
| VIP 파이프라인 | VIP Pipeline | Value-Intelligent-Planning 3단계 LLM 처리 구조 | AI Service |
| 제로 조인 | Zero-Join | ES 비정규화로 DB JOIN 제거한 검색 아키텍처 | 검색 레이어 |
| 슬림 그래프 | Slim Graph | Neo4j에 최소 속성만 저장하는 경량화 전략 | Neo4j |
| 계층형 아키텍처 | Layered Architecture | Controller-Service-Repository 계층 분리 | Backend |
| 피처 기반 구조 | Feature-based Structure | 기능별 폴더 구조 (모듈화) | Frontend |
| 모놀리식 | Monolithic | 단일 배포 단위로 구성된 아키텍처 | Backend |
| 마이크로서비스 | Microservices | 독립 배포 가능한 작은 서비스들로 구성 | - |

### 4.2 통합 패턴

| 용어 (한글) | 용어 (영문) | 정의 | 적용 위치 |
|-------------|-------------|------|-----------|
| 회로 차단기 | Circuit Breaker | 연속 실패 시 요청 차단하여 시스템 보호 | 외부 API 연동 |
| 재시도 | Retry | 일시적 실패 시 재시도하는 패턴 | 모든 외부 호출 |
| 폴백 | Fallback | 실패 시 대체 로직 실행 | LLM, 임베딩 |
| 지수 백오프 | Exponential Backoff | 재시도 간격을 점진적으로 증가 | 재시도 정책 |
| 듀얼 라이트 | Dual Write | 두 저장소에 동시 기록 | 마이그레이션 |
| 벌크헤드 | Bulkhead | 장애 격리를 위한 리소스 분리 | 서비스 분리 |
| 타임아웃 | Timeout | 응답 대기 최대 시간 설정 | 모든 외부 호출 |

### 4.3 운영 패턴

| 용어 (한글) | 용어 (영문) | 정의 | 적용 위치 |
|-------------|-------------|------|-----------|
| 재시도 큐 | Retry Queue | 실패 작업 재시도 대기열 | Redis Streams |
| DLQ | Dead Letter Queue | 재시도 한도 초과 작업 보관 | Redis Streams |
| 정합성 검증 | Reconciliation | 데이터 일관성 확인 및 복구 | 배치 Job |
| 헬스 체크 | Health Check | 서비스 상태 확인 엔드포인트 | /health |
| 그레이스풀 셧다운 | Graceful Shutdown | 진행 중인 작업 완료 후 종료 | 모든 서비스 |

---

## 5. RAG 성능 평가 용어

### 5.1 검색 품질 지표

| 용어 (한글) | 용어 (영문) | 정의 | 공식/범위 |
|-------------|-------------|------|-----------|
| 정밀도 | Precision | 검색 결과 중 관련 문서 비율 | 관련/검색 (0~1) |
| 재현율 | Recall | 전체 관련 문서 중 검색된 비율 | 검색된관련/전체관련 (0~1) |
| F1 점수 | F1 Score | 정밀도와 재현율의 조화 평균 | 2×P×R/(P+R) |
| MRR | Mean Reciprocal Rank | 첫 관련 문서 순위의 역수 평균 | 1/rank (0~1) |
| NDCG | Normalized DCG | 순위 가중 검색 품질 점수 | DCG/IDCG (0~1) |
| Hit Rate | Hit Rate@K | 상위 K개 중 관련 문서 존재 비율 | hits/queries (0~1) |

### 5.2 생성 품질 지표

| 용어 (한글) | 용어 (영문) | 정의 | 공식/범위 |
|-------------|-------------|------|-----------|
| 충실도 | Faithfulness | 답변이 컨텍스트에 기반하는 정도 | 지지문장/전체문장 (0~1) |
| 답변 관련성 | Answer Relevance | 답변이 질문에 관련된 정도 | 유사도 평균 (0~1) |
| 컨텍스트 관련성 | Context Relevance | 검색 컨텍스트가 질문에 관련된 정도 | 관련청크/전체청크 (0~1) |
| 답변 정확도 | Answer Correctness | 답변과 Ground Truth 일치도 | F1(답변, 정답) (0~1) |
| 환각 점수 | Hallucination Score | 컨텍스트에 없는 정보 생성 비율 | 1 - Faithfulness (0~1) |

### 5.3 평가 프레임워크 용어

| 용어 (한글) | 용어 (영문) | 정의 | 관련 도구 |
|-------------|-------------|------|-----------|
| Ground Truth | Ground Truth | 평가 기준이 되는 정답 데이터 | - |
| 테스트 케이스 | Test Case | 질문 + 기대 답변 + 관련 문서 세트 | - |
| 벤치마크 | Benchmark | 성능 측정을 위한 표준 테스트 세트 | - |
| RAGAS | RAGAS | RAG 평가 오픈소스 프레임워크 | ragas |
| RAG Triad | RAG Triad | Q-C-A 삼각 평가 모델 | TruLens |
| LLM-as-Judge | LLM-as-Judge | LLM을 평가자로 사용하는 방식 | - |

### 5.4 응답 시간 지표

| 용어 (한글) | 용어 (영문) | 정의 | 단위 |
|-------------|-------------|------|------|
| 지연 시간 | Latency | 요청부터 응답까지의 소요 시간 | ms, s |
| TTFB | Time To First Byte | 첫 바이트 수신까지의 시간 | ms |
| P50 | 50th Percentile | 50% 요청이 이 시간 내 완료 | ms |
| P95 | 95th Percentile | 95% 요청이 이 시간 내 완료 | ms |
| P99 | 99th Percentile | 99% 요청이 이 시간 내 완료 | ms |
| 처리량 | Throughput | 단위 시간당 처리 요청 수 | RPS, QPS |

---

## 6. DevOps 용어

### 6.1 버전 관리

| 용어 (한글) | 용어 (영문) | 정의 | 관련 도구 |
|-------------|-------------|------|-----------|
| 브랜치 | Branch | 독립적인 코드 개발 라인 | Git |
| 머지 | Merge | 브랜치를 통합하는 작업 | Git |
| 리베이스 | Rebase | 브랜치 기준점을 변경하는 작업 | Git |
| 풀 리퀘스트 | Pull Request | 코드 변경 병합 요청 (GitHub) | GitHub |
| 머지 리퀘스트 | Merge Request | 코드 변경 병합 요청 (GitLab) | GitLab |
| 코드 리뷰 | Code Review | 코드 변경 사항 검토 | GitLab |
| 커밋 | Commit | 코드 변경 단위 저장 | Git |
| 태그 | Tag | 특정 커밋에 버전 표시 | Git |

### 6.2 CI/CD

| 용어 (한글) | 용어 (영문) | 정의 | 관련 도구 |
|-------------|-------------|------|-----------|
| CI | Continuous Integration | 지속적 통합 (자동 빌드/테스트) | GitLab CI |
| CD | Continuous Delivery/Deployment | 지속적 배포 | GitLab CI |
| 파이프라인 | Pipeline | CI/CD 작업 흐름 정의 | .gitlab-ci.yml |
| 스테이지 | Stage | 파이프라인의 단계 (build, test, deploy) | GitLab CI |
| 잡 | Job | 파이프라인 내 개별 작업 | GitLab CI |
| 아티팩트 | Artifact | 빌드 결과물 (JAR, Docker Image 등) | - |
| 러너 | Runner | CI/CD 작업 실행 에이전트 | GitLab Runner |

### 6.3 컨테이너

| 용어 (한글) | 용어 (영문) | 정의 | 관련 도구 |
|-------------|-------------|------|-----------|
| 컨테이너 | Container | 애플리케이션 격리 실행 환경 | Docker |
| 이미지 | Image | 컨테이너 실행을 위한 템플릿 | Docker |
| Dockerfile | Dockerfile | 이미지 빌드 스크립트 | Docker |
| 레지스트리 | Registry | 이미지 저장소 | Docker Hub, GitLab |
| 볼륨 | Volume | 컨테이너 영속 저장소 | Docker Volume |
| 네트워크 | Network | 컨테이너 간 통신 네트워크 | Docker Network |
| Docker Compose | Docker Compose | 멀티 컨테이너 오케스트레이션 | docker-compose.yml |
| 서비스 | Service (Docker) | Compose에서 정의된 컨테이너 단위 | Docker Compose |

### 6.4 빌드 도구

| 용어 (한글) | 용어 (영문) | 정의 | 관련 도구 |
|-------------|-------------|------|-----------|
| Gradle | Gradle | JVM 빌드 자동화 도구 | build.gradle.kts |
| npm | Node Package Manager | Node.js 패키지 관리자 | package.json |
| Poetry | Poetry | Python 의존성 관리 도구 | pyproject.toml |
| 의존성 | Dependency | 프로젝트가 필요로 하는 외부 라이브러리 | - |
| 린터 | Linter | 코드 스타일/오류 검사 도구 | ESLint, Black |
| 포매터 | Formatter | 코드 스타일 자동 정렬 도구 | Prettier, Black |

### 6.5 환경 관리

| 용어 (한글) | 용어 (영문) | 정의 | 적용 환경 |
|-------------|-------------|------|-----------|
| 개발 환경 | Development | 개발자 로컬 환경 | local |
| 스테이징 환경 | Staging | 운영 전 테스트 환경 | staging |
| 운영 환경 | Production | 실제 서비스 환경 | prod |
| 환경 변수 | Environment Variable | 환경별 설정 값 | .env |
| 시크릿 | Secret | 민감한 설정 값 (API 키, 비밀번호) | Vault |

---

## 7. 보안 용어

### 7.1 인증/인가

| 용어 (한글) | 용어 (영문) | 정의 | 관련 기술 |
|-------------|-------------|------|-----------|
| 인증 | Authentication | 사용자 신원 확인 | JWT, OAuth |
| 인가 | Authorization | 리소스 접근 권한 확인 | RBAC, ABAC |
| SSO | Single Sign-On | 단일 인증으로 여러 서비스 접근 | Keycloak |
| OAuth 2.0 | OAuth 2.0 | 권한 부여 프로토콜 | Keycloak |
| OIDC | OpenID Connect | OAuth 기반 인증 프로토콜 | Keycloak |
| JWT | JSON Web Token | 토큰 기반 인증 표준 | - |
| 액세스 토큰 | Access Token | API 접근용 단기 토큰 | JWT |
| 리프레시 토큰 | Refresh Token | 액세스 토큰 갱신용 장기 토큰 | - |
| RBAC | Role-Based Access Control | 역할 기반 접근 제어 | Spring Security |
| ABAC | Attribute-Based Access Control | 속성 기반 접근 제어 | - |

### 7.2 암호화

| 용어 (한글) | 용어 (영문) | 정의 | 관련 기술 |
|-------------|-------------|------|-----------|
| 대칭키 암호화 | Symmetric Encryption | 동일 키로 암복호화 | AES-256 |
| 비대칭키 암호화 | Asymmetric Encryption | 공개키/개인키 쌍 사용 | RSA |
| 해시 | Hash | 단방향 암호화 (복호화 불가) | SHA-256 |
| 솔트 | Salt | 해시 강화를 위한 랜덤 값 | bcrypt |
| TLS | Transport Layer Security | 전송 구간 암호화 | HTTPS |
| 봉투 암호화 | Envelope Encryption | 데이터 키를 마스터 키로 암호화 | Vault |
| KMS | Key Management Service | 암호화 키 관리 서비스 | Vault |
| DEK | Data Encryption Key | 데이터 암호화 키 | - |
| KEK | Key Encryption Key | 키 암호화 키 (마스터 키) | - |

### 7.3 보안 취약점

| 용어 (한글) | 용어 (영문) | 정의 | 방어 방법 |
|-------------|-------------|------|-----------|
| XSS | Cross-Site Scripting | 악성 스크립트 삽입 공격 | CSP, 이스케이프 |
| CSRF | Cross-Site Request Forgery | 사이트 간 요청 위조 | CSRF 토큰 |
| SQL 인젝션 | SQL Injection | SQL 쿼리 삽입 공격 | 파라미터 바인딩 |
| CORS | Cross-Origin Resource Sharing | 교차 출처 리소스 공유 제어 | Whitelist |
| CSP | Content Security Policy | 콘텐츠 보안 정책 | HTTP 헤더 |

---

## 8. 프론트엔드 용어

### 8.1 React/웹 기본

| 용어 (한글) | 용어 (영문) | 정의 | 관련 기술 |
|-------------|-------------|------|-----------|
| 컴포넌트 | Component | UI의 재사용 가능한 독립 단위 | React |
| 상태 | State | 컴포넌트의 동적 데이터 | useState |
| 프롭스 | Props | 부모에서 자식으로 전달되는 데이터 | React |
| 훅 | Hook | 함수형 컴포넌트에서 상태/생명주기 사용 | React Hooks |
| 렌더링 | Rendering | UI를 화면에 그리는 과정 | React DOM |
| 가상 DOM | Virtual DOM | 메모리 상의 UI 표현 | React |
| SPA | Single Page Application | 단일 페이지 애플리케이션 | React Router |

### 8.2 상태 관리

| 용어 (한글) | 용어 (영문) | 정의 | 관련 기술 |
|-------------|-------------|------|-----------|
| 전역 상태 | Global State | 앱 전체에서 공유되는 상태 | Zustand |
| 서버 상태 | Server State | 서버에서 가져온 비동기 데이터 | TanStack Query |
| 캐시 무효화 | Cache Invalidation | 캐시 데이터 갱신 트리거 | TanStack Query |
| 옵티미스틱 업데이트 | Optimistic Update | 서버 응답 전 UI 선 반영 | TanStack Query |
| 스토어 | Store | 상태 저장소 | Zustand |

### 8.3 스타일링

| 용어 (한글) | 용어 (영문) | 정의 | 관련 기술 |
|-------------|-------------|------|-----------|
| CSS-in-JS | CSS-in-JS | JavaScript로 CSS 작성 | Emotion |
| 테마 | Theme | 앱 전체 스타일 설정 | MUI Theme |
| 반응형 디자인 | Responsive Design | 화면 크기에 따른 적응형 UI | 미디어 쿼리 |
| 디자인 시스템 | Design System | UI 컴포넌트/스타일 표준 | MUI |
| 다크 모드 | Dark Mode | 어두운 색상 테마 | prefers-color-scheme |
| 접근성 | Accessibility (a11y) | 장애인도 사용 가능한 UI | WCAG |

### 8.4 빌드/번들링

| 용어 (한글) | 용어 (영문) | 정의 | 관련 기술 |
|-------------|-------------|------|-----------|
| 번들러 | Bundler | 모듈을 하나의 파일로 묶는 도구 | Vite |
| 트랜스파일러 | Transpiler | 최신 JS를 구버전으로 변환 | Babel |
| 코드 스플리팅 | Code Splitting | 코드를 청크로 분할하여 지연 로딩 | Vite |
| 트리 쉐이킹 | Tree Shaking | 사용하지 않는 코드 제거 | Vite |
| HMR | Hot Module Replacement | 새로고침 없이 모듈 교체 | Vite |

---

## 9. 약어 목록

### 9.1 기술 약어

| 약어 | 전체 표현 | 한글 설명 |
|------|-----------|-----------|
| API | Application Programming Interface | 애플리케이션 프로그래밍 인터페이스 |
| REST | Representational State Transfer | REST 아키텍처 스타일 |
| gRPC | Google Remote Procedure Call | 구글 원격 프로시저 호출 |
| JWT | JSON Web Token | JSON 웹 토큰 |
| OIDC | OpenID Connect | OpenID 연결 프로토콜 |
| OAuth | Open Authorization | 개방형 인가 프로토콜 |
| SSO | Single Sign-On | 단일 로그인 |
| SSE | Server-Sent Events | 서버 전송 이벤트 |
| CORS | Cross-Origin Resource Sharing | 교차 출처 리소스 공유 |
| CSRF | Cross-Site Request Forgery | 사이트 간 요청 위조 |
| XSS | Cross-Site Scripting | 크로스 사이트 스크립팅 |
| CSP | Content Security Policy | 콘텐츠 보안 정책 |
| RBAC | Role-Based Access Control | 역할 기반 접근 제어 |
| ABAC | Attribute-Based Access Control | 속성 기반 접근 제어 |
| JSON | JavaScript Object Notation | 자바스크립트 객체 표기법 |
| YAML | YAML Ain't Markup Language | YAML 데이터 직렬화 형식 |

### 9.2 데이터베이스 약어

| 약어 | 전체 표현 | 한글 설명 |
|------|-----------|-----------|
| PG | PostgreSQL | PostgreSQL 데이터베이스 |
| ES | Elasticsearch | Elasticsearch 검색 엔진 |
| CRUD | Create, Read, Update, Delete | 생성, 조회, 수정, 삭제 |
| DDL | Data Definition Language | 데이터 정의 언어 |
| DML | Data Manipulation Language | 데이터 조작 언어 |
| ORM | Object-Relational Mapping | 객체-관계 매핑 |
| JPA | Java Persistence API | 자바 영속성 API |
| SQL | Structured Query Language | 구조화 질의 언어 |
| ACID | Atomicity, Consistency, Isolation, Durability | 원자성, 일관성, 격리성, 지속성 |

### 9.3 인프라/DevOps 약어

| 약어 | 전체 표현 | 한글 설명 |
|------|-----------|-----------|
| K8s | Kubernetes | 쿠버네티스 (참조용) |
| CI | Continuous Integration | 지속적 통합 |
| CD | Continuous Delivery/Deployment | 지속적 배포 |
| IaC | Infrastructure as Code | 코드형 인프라 |
| LB | Load Balancer | 로드 밸런서 |
| WAF | Web Application Firewall | 웹 애플리케이션 방화벽 |
| TLS | Transport Layer Security | 전송 계층 보안 |
| SSL | Secure Sockets Layer | 보안 소켓 레이어 |
| VPN | Virtual Private Network | 가상 사설 네트워크 |
| DNS | Domain Name System | 도메인 네임 시스템 |
| SSH | Secure Shell | 보안 셸 |
| SCP | Secure Copy Protocol | 보안 복사 프로토콜 |

### 9.4 모니터링/성능 약어

| 약어 | 전체 표현 | 한글 설명 |
|------|-----------|-----------|
| APM | Application Performance Management | 애플리케이션 성능 관리 |
| QPS | Queries Per Second | 초당 쿼리 수 |
| RPS | Requests Per Second | 초당 요청 수 |
| TPS | Transactions Per Second | 초당 트랜잭션 수 |
| P50 | 50th Percentile | 50 백분위수 (중앙값) |
| P95 | 95th Percentile | 95 백분위수 |
| P99 | 99th Percentile | 99 백분위수 |
| MTTR | Mean Time To Recovery | 평균 복구 시간 |
| MTTF | Mean Time To Failure | 평균 고장 간격 |
| SLO | Service Level Objective | 서비스 수준 목표 |
| SLA | Service Level Agreement | 서비스 수준 협약 |
| SLI | Service Level Indicator | 서비스 수준 지표 |

### 9.5 AI/ML 약어

| 약어 | 전체 표현 | 한글 설명 |
|------|-----------|-----------|
| AI | Artificial Intelligence | 인공 지능 |
| ML | Machine Learning | 기계 학습 |
| DL | Deep Learning | 딥 러닝 |
| NLP | Natural Language Processing | 자연어 처리 |
| NER | Named Entity Recognition | 개체명 인식 |
| LLM | Large Language Model | 대규모 언어 모델 |
| RAG | Retrieval-Augmented Generation | 검색 증강 생성 |
| GPU | Graphics Processing Unit | 그래픽 처리 장치 |
| TPU | Tensor Processing Unit | 텐서 처리 장치 |

### 9.6 프로젝트 특화 약어

| 약어 | 전체 표현 | 한글 설명 |
|------|-----------|-----------|
| VIP | Value-Intelligent-Planning | 3단계 LLM 파이프라인 |
| RRF | Reciprocal Rank Fusion | 역순위 융합 |
| SSOT | Single Source of Truth | 단일 진실 소스 |
| DLQ | Dead Letter Queue | 데드 레터 큐 |
| BGE | BAAI General Embedding | BGE 임베딩 모델 |
| M3 | Multi-Modal Multi-lingual | 다중 모달/언어 |
| MRR | Mean Reciprocal Rank | 평균 역순위 |
| NDCG | Normalized Discounted Cumulative Gain | 정규화 할인 누적 이득 |
| kNN | k-Nearest Neighbors | k-최근접 이웃 |
| HNSW | Hierarchical Navigable Small World | 계층적 탐색 소세계 |

---

## 10. 용어 사용 규칙

### 10.1 일반 규칙

1. **한글 우선**: 문서에서는 한글 용어를 우선 사용
2. **영문 병기**: 최초 사용 시 한글(영문) 형식으로 표기
3. **약어 정의**: 약어 최초 사용 시 전체 표현 병기
4. **일관성**: 동일 문서 내에서 동일 용어 사용

### 10.2 코드 규칙

```python
# Python 코드 내 용어 사용
class Document:  # 지식 문서
    pass

class Chunk:  # 청크 (분할된 문서)
    pass

class Entity:  # 엔티티 (추출된 개체)
    pass

# 변수명은 영문 용어 사용
document_id = "doc_001"
chunk_text = "..."
entity_type = "Person"

# RAG 평가 지표
faithfulness_score = 0.85
answer_relevance = 0.78
context_relevance = 0.72
```

### 10.3 API 규칙

```yaml
# API 경로: 영문 소문자 + 하이픈
/api/v1/knowledge-documents
/api/v1/hybrid-search
/api/v1/rag-chat

# 필드명: 영문 snake_case
{
  "document_id": "doc_001",
  "chunk_index": 0,
  "entity_type": "Person",
  "faithfulness_score": 0.85
}
```

### 10.4 문서 작성 예시

```markdown
## 좋은 예시

RAG(Retrieval-Augmented Generation) 시스템의 **충실도(Faithfulness)**는
생성된 답변이 검색된 컨텍스트(Context)에 기반하는 정도를 측정합니다.

## 나쁜 예시

RAG 시스템의 Faithfulness는 생성된 answer가 검색된 context에
기반하는 정도를 측정합니다.
```

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 | 작성자 |
|------|------|----------|--------|
| 1.0 | 2026-01-16 | 초기 작성 | Claude AI |
| 2.0 | 2026-01-16 | RAG 성능 평가, DevOps, 보안, 프론트엔드 용어 추가 | Claude AI |
| 2.1 | 2026-01-16 | Gleaning, max_gleanings 용어 추가 | Claude AI |

---

**문서 끝**

**관련 문서**:
- [에러 코드 표준](./error_code_standards.md)
- [API 통합 설계서](./api_integration_design.md)
- [Hybrid RAG 플랫폼 상세 설계서](./hybrid_rag_platform_detailed_design.md)
- [RAG 성능 테스트 설계서](./rag_performance_test_design.md)
- [DevOps 상세 설계서](./devops_detailed_design.md)
