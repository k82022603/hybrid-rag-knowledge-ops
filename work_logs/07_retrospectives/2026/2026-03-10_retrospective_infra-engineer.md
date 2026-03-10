# 프로젝트 회고 — Infra Engineer

**프로젝트**: Hybrid RAG Knowledge Platform 고도화
**기간**: 2026-01-10 ~ 2026-03-10
**역할**: Docker Compose 기반 18개 컨테이너 인프라 구축, 커스텀 이미지 빌드, 네트워크/볼륨 설계, 메모리 프로파일 관리

---

## 1. 내가 기여한 것 (What I Did)

- **Docker Compose 18개 컨테이너 구성**: PostgreSQL, Elasticsearch, Neo4j, Keycloak, Spring Cloud Gateway, AI Service, Nginx, Prometheus, Grafana, Kibana, Jaeger 등 18개 서비스를 하나의 docker-compose.yml로 통합 관리했습니다. 서비스 간 의존성, 헬스체크, 재시작 정책을 체계적으로 설정했습니다.
- **커스텀 ES Nori 이미지 빌드**: 기본 Elasticsearch 이미지에 `analysis-nori` 플러그인이 포함된 커스텀 Dockerfile을 작성하고, Nori 한국어 분석기가 정상 동작하도록 이미지를 빌드했습니다. Nori 사고 이후 가장 중요한 수정 작업이었습니다.
- **WSL2 메모리 프로파일 관리**: 14GB RAM, 4GB swap, 8 CPU의 hybrid-rag 프로파일을 설계하고, `.wslconfig.profile`과 `scripts/switch-wslconfig.sh`로 프로파일 전환 자동화를 구현했습니다.
- **Docker 네트워크 설계**: Frontend, Backend, AI Service, 모니터링 서비스 간의 네트워크 분리와 통신 규칙을 설계하여, 보안과 성능을 동시에 확보했습니다.
- **Nginx 리버스 프록시**: Docker DNS resolver(127.0.0.11) + 변수 upstream 방식으로 Grafana 등 모니터링 서비스의 안정적인 프록싱을 구현했습니다.

## 2. 잘된 점 (What Went Well)

- **단일 명령 환경 구축**: `docker-compose up -d` 한 번으로 전체 플랫폼이 구동되는 환경을 달성했습니다. 신규 팀원이 합류해도 10분 이내에 개발 환경을 셋업할 수 있습니다.
- **헬스체크 체계**: 모든 서비스에 적절한 healthcheck를 설정하여, 서비스 준비 완료 전에 의존 서비스가 시작되는 문제를 방지했습니다. 특히 Elasticsearch와 Keycloak의 긴 초기화 시간을 고려한 설정이 효과적이었습니다.
- **리소스 제한 관리**: 각 컨테이너의 메모리/CPU 제한을 설정하여, WSL2의 제한된 리소스에서도 18개 서비스가 안정적으로 동작하도록 했습니다.

## 3. 아쉬운 점 (What Could Be Better)

- **Nori Dockerfile 초기 누락**: ES Nori 플러그인 설치를 위한 Dockerfile을 초기에 생성하지 않아 32일간 standard analyzer로 동작한 것은 인프라 엔지니어로서 가장 뼈아픈 실수입니다. 커스텀 설정이 필요한 서비스는 반드시 Dockerfile이 있어야 한다는 원칙을 뒤늦게 확립했습니다.
- **볼륨 백업 전략 미비**: Docker Volume의 정기 백업과 복원 절차를 프로젝트 종료까지 자동화하지 못했습니다.
- **멀티 호스트 확장성**: Docker Compose 단일 호스트 전략의 한계를 인지하면서도, Kubernetes 전환 계획을 구체화하지 못했습니다.

## 4. 배운 점 (What I Learned)

- **"Dockerfile이 없으면 커스텀 설정도 없다"**: 공식 이미지에 설정 파일만 마운트하면 될 것 같지만, 플러그인 설치 같은 런타임 이전 작업은 반드시 Dockerfile로 빌드해야 합니다. 이 단순한 원칙을 놓쳐서 32일을 낭비했습니다.
- **WSL2 리소스 관리의 중요성**: 18개 컨테이너를 WSL2에서 운영하려면, 메모리 할당과 스왑 설정이 매우 중요합니다. OOM Killer에 의한 컨테이너 사망을 여러 번 경험하며 프로파일 최적화의 필요성을 체감했습니다.
- **Docker 빌드 캐시 관리**: `docker builder prune -f`와 `docker image prune -a -f`로 빌드 캐시를 정리하는 것이 테스트 전 필수 절차라는 것을 배웠습니다. 디스크 부족으로 빌드 실패하는 경우가 생각보다 잦았습니다.

## 5. 다음 프로젝트에 바라는 점

- Docker Compose에서 Kubernetes로의 마이그레이션을 계획하여, 오토스케일링과 고가용성을 확보하고 싶습니다.
- 이미지 빌드 파이프라인(BuildKit + GitHub Actions)을 구축하여, 커스텀 이미지를 자동으로 빌드하고 레지스트리에 푸시하는 체계를 만들고 싶습니다.

## 6. 팀원들에게 한마디

인프라는 눈에 보이지 않지만, 모든 서비스의 기반입니다. `docker-compose up -d`를 치고 18개 컨테이너가 초록색 healthcheck를 뿌릴 때의 쾌감은 이 일을 하는 보람입니다. Nori 사고는 정말 뼈저리게 반성하고 있고, "환경 구축은 검증까지가 완료"라는 원칙을 가슴에 새겼습니다. DevOps와 함께 모니터링 스택을 올리고, Backend가 Gateway 라우팅을 잡을 때 연동이 매끄러웠던 것은 서로의 설정을 이해하고 있었기 때문입니다. 다음에도 이런 협업을 하고 싶습니다.
