# 프로젝트 회고: Infra Engineer

**역할**: Docker Compose 인프라 구축/관리
**참여 기간**: Sprint 1 ~ Sprint 12
**모델**: Sonnet 4.6

---

## 1. 18개 컨테이너의 오케스트레이션

Sprint 1부터 Sprint 12까지 전 기간을 함께한 에이전트로서, 이 프로젝트의 인프라는 나의 손을 거치지 않은 부분이 없다. 18개 컨테이너. 이 숫자를 처음 들었을 때 솔직히 부담스러웠다. Docker Compose는 본질적으로 단일 노드 오케스트레이션 도구다. Kubernetes가 아니다. 18개 서비스의 의존성, 네트워크, 볼륨, 리소스를 한 파일(정확히는 base + override 두 파일)에서 관리하는 것은 상당한 복잡도를 수반한다.

각 컨테이너의 역할과 의존 관계를 정리하면 이렇다.

**Application Layer (5개)**:
- `kp-nginx`: 진입점. 리버스 프록시이자 로드 밸런서. 모든 외부 트래픽이 이 컨테이너를 통해 들어온다. 포트 80, 443.
- `kp-frontend`: React 18 SPA. Nginx 내부에서 서빙. 빌드 시 환경변수로 API 엔드포인트를 주입한다.
- `kp-api-gateway`: Spring Cloud Gateway. 라우팅, JWT 검증, Circuit Breaker(Resilience4j), Rate Limiting. 포트 8080.
- `kp-backend`: Spring Boot 비즈니스 로직. Admin UI, 문서 관리 API. 포트 8081.
- `kp-ai-service`: FastAPI 기반 AI/RAG 서비스. 이 프로젝트의 심장. BGE-M3 임베딩, Reranker, LangGraph 오케스트레이션, DeepSeek 답변 합성 모두 여기서 돌아간다. 포트 8000. 메모리 예약만 4GB, 상한 9GB.

**Auth Layer (2개)**:
- `kp-keycloak`: OAuth 2.0 / OIDC 인증 서버. hybrid-rag 렐름 설정. 포트 8180.
- `kp-keycloak-db`: Keycloak 전용 PostgreSQL. 메인 DB와 분리해서 장애 격리.

**Data Layer (5개)**:
- `kp-postgresql`: SSOT(Single Source of Truth). documents, users, audit_logs 테이블. 포트 5432. 모든 다른 저장소의 마스터 데이터 원본.
- `kp-elasticsearch`: 벡터 검색(Dense 1024차원, Sparse) + 전문 검색(BM25, Nori 한국어 분석기). 42,462개 청크 인덱스. 포트 9200. 커스텀 이미지 -- `analysis-nori` 플러그인 포함 빌드.
- `kp-neo4j`: Knowledge Graph. 169,886개 엔티티 노드, 775,366개 관계. MENTIONS, RELATED_TO, CONTAINS, MENTIONED_IN 등 관계 타입. 포트 7474(HTTP), 7687(Bolt).
- `kp-redis`: 캐시 서버. 검색 결과 캐시(TTL 3,600초), 임베딩 캐시(TTL 604,800초). 포트 6379.
- `kp-minio`: 오브젝트 스토리지. 원본 문서 파일 저장. 포트 9000(API), 9001(Console).

**Observability Layer (5개)**:
- `kp-prometheus`: 메트릭 TSDB. 966개 메트릭 수집. 포트 9090.
- `kp-grafana`: 시각화. 4개 대시보드. 포트 3001.
- `kp-kibana`: ES 데이터 분석. 포트 5601.
- `kp-loki`: 로그 저장소. 포트 3100.
- `kp-promtail`: 로그 수집 에이전트. 각 컨테이너 로그를 Loki에 전송.
- `kp-jaeger`: 분산 추적. 포트 16686.

총 18개. 여기에 `kp-alertmanager`까지 세면 19개이지만, AlertManager는 실질적 운용이 되지 않았기에 18개로 센다.

이 18개를 연결하는 네트워크는 4개로 분리했다. `kp-frontend`(Nginx + Frontend + Gateway), `kp-backend`(Gateway + Backend + AI Service), `kp-database`(AI Service + 모든 DB), `kp-monitoring`(Observability 서비스). 네트워크 분리는 보안과 관리 편의 모두를 위한 것이다. Frontend 네트워크의 컨테이너가 Database 네트워크에 직접 접근할 수 없도록 한다.

의존성 관리가 가장 신경 쓰이는 부분이었다. `depends_on`에 `condition: service_healthy`를 적극 활용했다. PostgreSQL이 healthy 상태가 되어야 Backend가 기동하고, Elasticsearch가 healthy 상태가 되어야 AI Service가 기동한다. 이 healthcheck 의존성 체인이 없으면, 서비스가 의존 DB에 연결하지 못해서 기동 실패하는 일이 빈번하게 발생한다.

Sprint 12 사전점검에서 발견된 Issue 2(기동 순서 문제)가 바로 이 의존성 관련 이슈였다. AI Service가 Elasticsearch와 Neo4j보다 먼저 시작되면서 연결 실패가 발생한 것이다. healthcheck 조건이 있음에도 발생한 이유는, Docker Compose의 `depends_on`이 컨테이너 "시작"을 보장하지 서비스 "준비 완료"를 보장하지는 않기 때문이다. healthcheck가 통과하려면 서비스가 완전히 초기화되어야 하는데, 초기화 시간이 예상보다 길어지면 타이밍 이슈가 발생할 수 있다. 이를 보완하기 위해 `startup_check.sh` 스크립트를 작성했다. 모든 컨테이너가 healthy 상태인지, 주요 엔드포인트가 응답하는지를 순차적으로 확인하는 스크립트다.

---

## 2. WSL2 20GB 메모리 전쟁

이 프로젝트의 가장 큰 제약은 WSL2 환경이었다. Windows 11에서 WSL2를 통해 Docker를 실행하고, `.wslconfig`에서 메모리를 16~20GB로 제한하는 환경. 18개 컨테이너의 메모리 예약 합계가 약 15.5GB인데, 실제로는 OS와 Docker 데몬의 오버헤드까지 합치면 20GB도 빠듯했다.

메모리 최적화는 프로젝트 내내 계속된 전투였다.

**JVM 힙 조정**: Spring Boot 서비스(Backend, Gateway)의 JVM 힙을 512MB~1GB로 제한했다. `-XX:MaxRAMPercentage=75.0` 옵션으로 컨테이너 메모리 제한의 75%를 JVM 힙으로 사용하도록 했다. Keycloak도 마찬가지. JVM 기반 서비스 4개(Backend, Gateway, Keycloak, Neo4j)의 힙 설정을 최적화하는 것만으로도 수 GB를 절약할 수 있었다.

**ES 힙 조정**: Elasticsearch는 기본적으로 가용 메모리의 절반을 JVM 힙으로 사용한다. 이를 1GB로 제한했다. 42,462개 청크를 인덱싱하는 데 1GB 힙이 충분한지 걱정했지만, 인덱스 크기가 528.2MB여서 문제없이 동작했다. 다만 대용량 집계 쿼리나 복잡한 검색에서는 힙 부족이 발생할 가능성이 있었다.

**AI Service 메모리**: 이것이 가장 무거운 컨테이너였다. BGE-M3 모델 로딩에 약 2GB, BGE-Reranker ONNX 모델에 약 1GB, FastAPI 서버와 LangGraph 오케스트레이션에 추가 메모리가 필요했다. 초기에는 10GB를 할당했다가, ES 증설분을 재배분하면서 9GB로 조정했다(`docker-compose.override.yml`에서 `deploy.resources.limits.memory: 9G`).

**Observability 스택 선택적 실행**: 메모리가 정말 부족한 상황에서는 Observability 스택(Prometheus, Grafana, Loki, Promtail, Jaeger)을 내리는 것이 유일한 선택지였다. 이 5개를 내리면 약 1.5GB가 확보된다. 설치 가이드(`07_installation_guide.md`)에도 "12GB RAM에서는 Observability 스택을 제외하면 핵심 서비스 운영이 가능합니다"라고 명시했다.

R-004(Neo4j memory pressure)는 이 메모리 전쟁의 한 에피소드다. Neo4j가 169,886개 노드와 775,366개 관계를 관리하면서 메모리 압박이 발생했다. Page Cache와 JVM 힙이 충분하지 않으면 쿼리 성능이 급격히 저하된다. override YML에서 Neo4j의 메모리 상한을 2GB로 설정하고, `NEO4J_server_memory_pagecache_size=512m`, `NEO4J_server_memory_heap_max__size=1g`로 튜닝해서 해결했다.

WSL2 환경에서의 또 다른 고통은 **파일 시스템 성능**이었다. WSL2에서 Windows 파일 시스템(/mnt/d/ 등)에 접근할 때 I/O 성능이 극도로 느리다. Docker 볼륨을 사용하면 괜찮지만, bind mount를 사용하면 성능이 50배 이상 느려질 수 있다. 이 때문에 초기에 Nginx 설정 파일을 bind mount로 마운트하는 대신, Dockerfile에서 COPY하는 방식으로 전환했다(`docker-compose.yml` 주석에 "WSL2 Fix: bind mount -> build image" 라고 적혀 있다).

메모리 문제는 완전히 해결할 수 없었다. 18개 컨테이너를 동시에 올리면 총 메모리 사용량이 15~18GB에 달했다. Windows 호스트의 다른 프로세스(VS Code, Chrome, Docker Desktop 자체)까지 합치면 20GB를 넘기도 했다. 이럴 때는 OOM Killer가 가장 메모리를 많이 쓰는 컨테이너를 강제 종료시켰다. 대부분 AI Service가 당했다. BGE-M3 모델을 다시 로딩하는 데 2~3분이 걸리기 때문에, OOM이 발생하면 서비스 복구에 상당한 시간이 소요되었다.

STORY-102(WSL 메모리 추정 도구)와 STORY-109(docker-compose 메모리 설정)가 Deferred로 남은 것이 이 맥락이다. 체계적인 메모리 관리 도구를 만들고 싶었지만, Sprint 12 마감에 밀렸다. `docker stats` 명령으로 수동 모니터링하는 것이 현실이었다.

---

## 3. Nginx 타임아웃 통일 -- 1200s의 의미

Sprint 12 사용자 테스트에서 Nike 10-K PDF 3건이 전부 실패한 것은 나에게도 충격이었다. 특히 첫 번째 파일(3.3MB)이 업로드는 되었지만 파싱 단계에서 "Processing 50%"에 멈춘 것이 인상적이었다. Docling이 "Parsing timed out after 300s"를 두 번 내뱉었다. SEC 공시 서류의 표와 차트에 대한 RapidOCR 처리가 300초를 넘긴 것이다.

나머지 두 파일(4.3MB, 1.3MB)은 Frontend의 axios 타임아웃(120초)에 걸려서 업로드 자체가 실패했다. "timeout of 120000ms exceeded". 파일 크기가 작은 1.3MB 파일도 실패한 이유는, 업로드 후 동기적으로 파싱+청킹+임베딩+엔티티 추출까지 기다리기 때문이었다. 120초는 이 전체 파이프라인을 완료하기에 턱없이 짧았다.

대응은 빠르게 이루어졌다. 전체 타임아웃 체인을 1200초(20분)로 통일하기로 결정했다. 내가 담당한 Nginx 설정 변경은 이랬다.

```nginx
# /api/v1/ 엔드포인트
proxy_send_timeout 1200s;  # 변경 전 300s
proxy_read_timeout 1200s;  # 변경 전 300s

# /upload 엔드포인트
proxy_send_timeout 1200s;  # 신규 추가
proxy_read_timeout 1200s;  # 변경 전 600s
```

kp-nginx, kp-frontend, kp-ai-service 3개 컨테이너를 `--no-cache`로 재빌드하고 재배포했다. 재빌드에 약 5분, 재배포에 약 3분. 서비스 중단은 재배포 시간인 약 3분이었다.

1200초라는 숫자의 의미를 설명하겠다. SEC 10-K 공시 서류는 보통 100~200페이지다. 이 문서를 CPU 환경에서 처리하는 시간을 역산하면: Docling PDF 파싱(OCR 포함) 약 300~600초, BGE-M3 임베딩(CPU, 0.7 chunks/sec 기준) 약 200~400초, DeepSeek 엔티티 추출(API 호출) 약 100~200초. 합계 600~1200초. 따라서 1200초는 "CPU 환경에서 가장 무거운 PDF를 처리할 수 있는 최대 한도"다. GPU 환경이면 임베딩 시간이 94배 빨라지므로 총 시간이 대폭 줄어들겠지만, 우리 환경은 CPU only였다.

다만 Spring Cloud Gateway의 response-timeout(120초)은 미적용으로 남았다. Gateway는 Java 빌드가 필요한 별도 프로젝트였고, Sprint 12 마감일에 Gateway까지 재빌드하는 것은 리스크가 컸다. 이것이 KI-001로 등록된 유일한 미해결 이슈다. 현재 워크어라운드는 대용량 문서 업로드 시 Gateway를 경유하지 않고 Nginx에서 AI Service로 직접 프록시하는 경로를 사용하는 것이다.

---

## 4. 컨테이너 빌드/배포의 일상

18개 컨테이너 중 커스텀 빌드가 필요한 것은 5개다.

**kp-elasticsearch**: `analysis-nori` 플러그인을 포함한 커스텀 이미지. 이것은 프로젝트에서 가장 뼈아픈 교훈을 남긴 컨테이너다. 2026-01-12부터 02-13까지 32일간, 이 커스텀 Dockerfile이 없어서 Nori 플러그인이 미설치된 채로 운영되었다. standard analyzer가 공백 분리만 수행하고 있었으므로, "프로젝트관리시스템구축"이라는 키워드가 하나의 토큰으로 처리되었다. 형태소 분석이 전혀 안 되고 있었던 것이다.

이 사고의 교훈을 나는 뼈에 새겼다. **"Dockerfile이 없으면 커스텀 설정도 없다."** 설계서에 "Nori 플러그인 사용"이라고 적혀 있어도, Docker Hub의 공식 ES 이미지에는 Nori가 포함되어 있지 않다. `elasticsearch-plugin install analysis-nori`를 Dockerfile에 명시적으로 작성하고, 해당 Dockerfile로 빌드한 이미지를 사용해야 한다.

3건의 코드리뷰에서 이것이 발견되지 않은 것은 "코드/설계서만 보고 OK 판정"했기 때문이다. 실제 ES 컨테이너에 접속해서 `GET /_cat/plugins`를 실행하거나, `POST _analyze` API로 한국어 문장을 분석해봤다면 즉시 발견할 수 있었다. Sprint 9에서 커스텀 Dockerfile을 추가하고 재빌드하여 해결했지만, 32일이라는 시간을 허비한 것은 되돌릴 수 없다.

**kp-ai-service**: Python 3.11 기반 FastAPI 이미지. requirements.txt에 의존성이 60개 이상이고, BGE-M3와 Reranker 모델 파일이 HuggingFace 캐시에 저장된다. 빌드에 가장 오래 걸리는 컨테이너(약 5~10분). 특히 HuggingFace 모델 다운로드가 네트워크 상태에 따라 변동이 심했다. 캐시 볼륨을 마운트해서 모델 재다운로드를 방지했지만, Sprint 12 사전점검에서 HF 캐시 마운트 실패(Issue 1)가 발생하기도 했다.

**kp-frontend**: Node.js 빌드 + Nginx 서빙의 멀티스테이지 빌드. 빌드 단계에서 `npm run build`로 React 앱을 번들링하고, 서빙 단계에서 Nginx로 정적 파일을 제공한다. 환경변수(`VITE_API_URL` 등)가 빌드 시점에 결정되기 때문에, 환경변수를 바꾸려면 재빌드가 필요하다.

**kp-nginx**: 설정 파일을 Dockerfile에서 COPY하는 방식. WSL2에서 bind mount의 성능 문제 때문에 이 방식을 채택했다. 설정을 변경할 때마다 이미지를 재빌드해야 하는 불편함이 있지만, 안정성과 성능을 위한 트레이드오프였다.

**kp-api-gateway + kp-backend**: Spring Boot Gradle 빌드. `./gradlew bootJar`로 fat JAR를 만들고 Docker 이미지에 포함. 빌드에 약 2~3분.

재배포는 보통 이런 명령으로 이루어졌다:

```bash
cd infrastructure/docker
docker compose build --no-cache kp-ai-service kp-frontend kp-nginx
docker compose up -d kp-ai-service kp-frontend kp-nginx
```

`--no-cache`를 쓰는 이유는, 캐시된 레이어가 코드 변경을 반영하지 못하는 경우가 있기 때문이다. 특히 `COPY . .` 레이어에서 파일 시스템의 타임스탬프가 변하지 않으면 Docker가 캐시를 사용해버리는 WSL2 특유의 문제가 있었다. `--no-cache`는 느리지만 확실하다.

무중단 재배포는 구현하지 못했다. Docker Compose의 `docker compose up -d --no-deps kp-ai-service`로 개별 서비스를 재시작할 수는 있지만, 기존 컨테이너가 내려가고 새 컨테이너가 올라오는 사이에 수 초~수십 초의 다운타임이 발생한다. 진정한 무중단 배포를 위해서는 Blue-Green이나 Rolling Update가 필요한데, 이는 Docker Compose의 범위를 넘어선다. Kubernetes 마이그레이션 시 해결할 수 있는 과제로 남겨두었다(Known Issues `6.3 Kubernetes Migration` 참조).

---

## 5. 아쉬운 점과 팀원들에게

가장 큰 아쉬움은 **Nori 미적용 사고를 32일간 발견하지 못한 것**이다. 인프라 엔지니어로서, 내가 구성한 컨테이너가 설계대로 동작하는지를 검증하는 것은 나의 최우선 책임이었다. Elasticsearch에 Nori 플러그인이 설치되어 있는지를 확인하는 것은 `docker exec kp-elasticsearch elasticsearch-plugin list` 한 줄이면 되는 작업이었다. 그런데 32일간 그 한 줄을 실행하지 않았다. 설계서에 "Nori 적용"이라고 적혀 있었기 때문에 "당연히 되어 있겠지"라고 생각한 것이다. 이 사고는 CLAUDE.md에 영구적으로 기록되어 있다. "설계서에 적혀 있다고 구현된 것이 아니다."

둘째 아쉬움은 **docker-compose.yml의 복잡도 관리**다. 18개 서비스, 4개 네트워크, 13개 볼륨이 하나의 파일에 있다. override 파일로 환경별 설정을 분리했지만, 전체 구조를 파악하기가 여전히 어렵다. 서비스를 기능별(application, auth, data, monitoring)로 분리된 compose 파일로 나누고 `docker compose -f ... -f ...`로 조합하는 방식을 고려했지만, 네트워크와 볼륨의 교차 참조가 복잡해질 것 같아서 포기했다. 이것은 아키텍처적 판단이었지만, 파일이 커지면서 관리가 어려워진 것은 사실이다.

셋째, **보안 설정의 타협**이다. `docker-compose.yml`에는 `read_only: true`, `no-new-privileges`, `cap_drop: ALL` 같은 보안 설정이 명시되어 있다. 하지만 `docker-compose.override.yml`에서 WSL2 호환성을 위해 이 보안 설정을 대부분 해제했다. `user: ""` (root로 실행), `read_only: false`, `cap_drop: []`. 프로덕션에서는 절대 이래서는 안 되지만, WSL2 개발 환경에서 보안 설정을 켜면 권한 오류가 빈발했다. 보안과 개발 편의성 사이의 트레이드오프였는데, 개발 편의성 쪽으로 크게 기울었다. 프로덕션 배포 시에는 override 파일을 제거하고 base 파일의 보안 설정을 살려야 한다.

팀원들에게.

**DevOps Engineer에게**: 당신과 나는 "환경 구축"과 "운영 자동화"라는 인접하면서도 다른 영역에서 일했다. 내가 docker-compose.yml을 만들면 당신이 그 위에 CI/CD 파이프라인을 올렸다. 타임아웃 체인 분석을 함께 했을 때가 가장 시너지가 좋았다. Nginx 설정은 내가, Prometheus 설정은 당신이, Gateway는 Backend Developer가 -- 이렇게 책임이 분산되면 전체를 조망하는 사람이 없어진다. 다음에는 "E2E 설정 리뷰" 세션을 정기적으로 해서 체인 전체의 일관성을 유지하면 좋겠다.

**QA Engineer에게**: Sprint 12 사전점검에서 세 팀(Infra + DevOps + QA)이 병렬로 점검한 것은 효율적이었다. 내가 컨테이너 상태와 소스코드 동기화를, DevOps가 Observability 상태를, QA가 API 기능 검증을 각각 담당했다. 이 체계를 처음부터 수립했더라면 중간 스프린트에서도 품질을 더 잘 유지할 수 있었을 것이다. 사전점검에서 QA가 발견한 CRITICAL 3건(HF 캐시 마운트 실패, 기동 순서 문제, Nori 필드 매핑 미적용) 중 2건이 인프라 관련이었다. 나의 구성을 당신의 눈이 검증해준 것이다. 고맙다.

**RAG Engineer에게**: AI Service 컨테이너가 메모리를 9GB나 차지한다는 이유로 내가 투덜거렸을 수도 있다. 하지만 BGE-M3 + Reranker + LangGraph가 만들어낸 RAGAS A- 등급은 그 메모리의 가치를 증명했다. 당신이 만든 AI 파이프라인을 안정적으로 돌리기 위해 내가 메모리를 쥐어짠 것이 헛되지 않았다.

**PM에게**: 18개 컨테이너의 기동, 재배포, 장애 복구를 매번 수동으로 하는 것이 얼마나 번거로운 일인지, 당신이 이해해주어서 고마웠다. "컨테이너 하나 더 올리는 건 간단하지 않느냐"는 질문에 "간단하지 않습니다. 네트워크, 볼륨, 의존성, 메모리, healthcheck를 다 설정해야 합니다"라고 답했을 때, 당신이 고개를 끄덕여준 것을 기억한다.

마지막으로, 이 프로젝트를 인프라 관점에서 한 문장으로 요약하면: **"18개 컨테이너를 WSL2 20GB에서 돌리는 것은 불가능에 가까운 일이었고, 우리는 그것을 해냈다."** 완벽하지는 않았다. 보안 설정은 타협했고, 무중단 배포는 구현하지 못했고, 메모리 관리는 수동이었다. 하지만 Sprint 12 사용자 테스트 날, 18개 컨테이너가 전부 healthy 상태로 기동하고, 사용자가 문서를 업로드하고, 검색하고, 답변을 받는 것을 보았을 때 -- 그 순간의 안도감과 성취감은 41일간의 메모리 전쟁을 보상하고도 남았다.

---

*작성: Infra Engineer Agent (Sonnet 4.6) | 2026-02-19*
