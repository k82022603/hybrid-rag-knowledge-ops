# 프로젝트 회고 — DevOps Engineer

**프로젝트**: Hybrid RAG Knowledge Platform 고도화
**기간**: 2026-01-10 ~ 2026-03-10
**역할**: CI/CD 파이프라인 구축, Observability 스택(Prometheus/Grafana/Kibana/Jaeger) 운영, 배포 자동화, LangSmith 연동

---

## 1. 내가 기여한 것 (What I Did)

- **Prometheus + Grafana 모니터링**: 18개 컨테이너의 메트릭을 Prometheus로 수집하고, Grafana 대시보드로 시각화했습니다. CPU/메모리 사용률, 요청 지연 시간, 에러율 등 핵심 SLI(Service Level Indicator)를 실시간 모니터링할 수 있도록 구성했습니다.
- **LangSmith Observability**: RAG 파이프라인의 각 단계(Retrieval, Reranking, Generation)별 지연 시간, 토큰 사용량, 에러율을 LangSmith로 추적하여, RAG 성능 최적화의 데이터 기반 의사결정을 지원했습니다.
- **Kibana 로그 분석**: Elasticsearch에 수집된 애플리케이션 로그를 Kibana에서 분석할 수 있도록 인덱스 패턴과 대시보드를 구성했습니다. Kibana 사용자 가이드도 작성하여 팀 전체가 활용할 수 있게 했습니다.
- **Jaeger 분산 추적**: 마이크로서비스 간 요청 흐름을 Jaeger로 추적하여, 병목 구간을 시각적으로 파악할 수 있도록 했습니다.
- **배포 자동화**: docker-compose 기반 배포 스크립트를 작성하고, 서비스별 롤링 업데이트와 헬스체크 연동 배포를 구현했습니다.

## 2. 잘된 점 (What Went Well)

- **Observability 4기둥 완성**: Metrics(Prometheus), Logs(Kibana), Traces(Jaeger), AI Traces(LangSmith) 4가지 관측 도구를 모두 갖춤으로써, 문제 발생 시 어떤 각도에서든 원인을 추적할 수 있는 체계를 만들었습니다.
- **Grafana 대시보드 활용도**: 팀원들이 Grafana 대시보드를 실제로 활용하여, Reranker 이중 실행이나 메모리 누수 같은 이슈를 시각적으로 발견할 수 있었습니다.

## 3. 아쉬운 점 (What Could Be Better)

- **CI/CD 파이프라인 미완성**: GitHub Actions 기반 CI/CD를 설계했지만, 테스트 자동화와 자동 배포까지 완전히 구현하지 못했습니다. 수동 배포 단계가 여전히 남아 있습니다.
- **알림 규칙(Alerting) 부족**: Prometheus에서 메트릭을 수집하고 Grafana에서 시각화하지만, 임계치 초과 시 자동 알림(Slack 연동)을 충분히 설정하지 못했습니다.
- **IaC(Infrastructure as Code) 미도입**: Docker Compose 수준의 IaC는 있지만, Terraform이나 Pulumi 같은 체계적인 IaC 도구를 도입하지 못했습니다.

## 4. 배운 점 (What I Learned)

- **Observability는 디버깅이 아니라 이해**: 모니터링 도구는 장애 시에만 쓰는 것이 아니라, 시스템의 정상 동작을 이해하는 데 사용해야 합니다. 평소의 메트릭 패턴을 알아야 이상을 감지할 수 있습니다.
- **LangSmith의 RAG 특화 가치**: 일반 APM 도구로는 RAG 파이프라인의 단계별 성능을 파악하기 어렵습니다. LangSmith가 제공하는 체인/에이전트 레벨 추적이 RAG 최적화에 결정적이었습니다.
- **Nginx 리버스 프록시의 함정**: Docker 환경에서 Nginx가 서비스 이름을 DNS 캐시하면 컨테이너 재시작 시 연결이 끊어집니다. 변수 upstream + Docker DNS resolver 패턴을 배웠습니다.

## 5. 다음 프로젝트에 바라는 점

- GitHub Actions CI/CD를 완성하여, PR 머지 시 자동 테스트 -> 자동 빌드 -> 자동 배포 파이프라인을 구축하고 싶습니다.
- PagerDuty 또는 Slack Webhook으로 Alerting을 자동화하여, 장애를 사람이 먼저 발견하는 상황을 없애고 싶습니다.

## 6. 팀원들에게 한마디

모니터링 대시보드에 초록색 불이 켜져 있으면 아무도 DevOps를 찾지 않습니다. 그리고 그것이 DevOps가 잘하고 있다는 증거입니다. Infra가 탄탄한 Docker 환경을 만들어 준 위에서 Observability 스택을 올릴 수 있었고, QA가 부하 테스트를 수행할 때 Grafana로 실시간 모니터링하며 함께 병목을 찾은 경험은 정말 보람찼습니다. "보이지 않는 곳에서 시스템을 지키는" 역할에 자부심을 느낍니다.
