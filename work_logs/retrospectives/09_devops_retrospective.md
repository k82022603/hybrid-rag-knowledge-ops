# 프로젝트 회고: DevOps Engineer

**역할**: CI/CD / Observability
**참여 기간**: Sprint 2 ~ Sprint 12
**모델**: Sonnet 4.6

---

## 1. 8개 GitHub Actions 워크플로우

처음 이 프로젝트의 CI/CD를 설계할 때, 나는 "워크플로우는 많을수록 좋다"고 생각하지 않았다. 오히려 "각 워크플로우가 명확한 한 가지 책임을 가져야 한다"는 원칙을 세웠다. 결과적으로 10개의 워크플로우 파일이 만들어졌고, 핵심적으로 운용된 것은 8개다.

`ci.yml`은 모든 PR에서 자동 실행되는 메인 파이프라인이다. 린트, 타입 체크, 유닛 테스트, 커버리지 리포트를 순서대로 수행한다. 이 워크플로우가 통과하지 않으면 PR을 머지할 수 없도록 branch protection rule을 설정했다. `pr-build.yml`은 PR 생성 시 Docker 이미지 빌드 가능 여부를 검증한다. 빌드가 깨지는 변경이 메인 브랜치에 들어오는 것을 사전 차단하는 역할이다.

`code-quality.yml`은 Black, isort, mypy, bandit 등 코드 품질 도구를 통합 실행한다. Python 코드의 일관된 스타일과 보안 취약점 사전 탐지가 목적이다. `docker-build.yml`은 메인 브랜치 변경 시 Docker 이미지를 빌드하고 태그를 관리한다. `docker-compose-validate.yml`은 docker-compose.yml의 문법 검증과 서비스 구성 일관성을 체크한다. 이 워크플로우가 없었다면 잘못된 YAML 문법이 배포 시점에야 발견되었을 것이다.

`deploy-staging.yml`과 `deploy-production.yml`은 스테이징과 프로덕션 환경 배포를 담당한다. `rollback.yml`은 배포 실패 시 이전 버전으로 롤백하는 비상 워크플로우다. 실제로 이 rollback 워크플로우를 실행한 적은 없지만, 존재 자체가 안전망이었다. `e2e-test.yml`은 E2E 테스트를 CI에서 자동 실행하는 워크플로우인데, QA Engineer가 언급했듯이 Playwright 기반 자동화가 완성되지 못해서 실질적 활용도는 낮았다.

8개 워크플로우를 운영하면서 가장 어려웠던 것은 "속도와 안전성의 균형"이었다. 전체 CI 파이프라인이 너무 오래 걸리면 개발자가 기다리다 지쳐서 CI를 무시하게 된다. 너무 빠르면 검증이 충분하지 않다. 나는 핵심 검증(lint + type check + unit test)을 5분 이내로 완료하는 것을 목표로 했고, Docker 빌드나 E2E 같은 무거운 작업은 별도 워크플로우로 분리해서 병렬 실행되도록 했다.

pre-commit hooks도 설정했다. Black 포매팅, isort 정렬, trailing whitespace 제거가 커밋 전에 자동 실행된다. "CI에서 스타일 문제로 실패하는 것은 시간 낭비"라는 철학이었다. 로컬에서 미리 잡을 수 있는 것은 로컬에서 잡자.

돌아보면, CI/CD 파이프라인의 진정한 가치는 "코드의 품질을 지키는 자동화된 문지기"에 있었다. 174개 유닛 테스트가 매 PR에서 자동으로 돌아간다는 것, 그것 자체가 프로젝트의 품질 기준선을 유지하는 힘이었다.

---

## 2. Observability 스택 구축

이 프로젝트의 Observability 스택은 5개 도구로 구성된다. Prometheus(메트릭 수집), Grafana(시각화), Kibana(ES 데이터 분석), Jaeger(분산 추적), Loki + Promtail(로그 수집). 이 5개를 Docker Compose 18개 컨테이너 환경에 통합하는 작업은, 기술적으로는 단순해 보이지만 실제로는 상당한 조율이 필요했다.

Prometheus는 메트릭의 심장이다. `prometheus.yml`에 scrape 타겟을 정의하고, 각 서비스가 `/metrics` 엔드포인트를 노출하도록 했다. Sprint 12 사전점검 기준으로 966개 메트릭이 수집되고 있었다. Backend(Spring Boot Actuator), Gateway(Spring Cloud Gateway Actuator), Grafana 자체 메트릭, Loki 메트릭, Jaeger 메트릭이 UP 상태로 수집 중이었다.

Grafana에는 4개 대시보드를 구성했다. **Application Dashboard**는 HTTP 요청 수, 응답 시간, 에러율을 보여준다. **Database Dashboard**는 PostgreSQL, Elasticsearch, Neo4j의 연결 상태와 쿼리 성능을 모니터링한다. **RAG & SLA Dashboard**는 검색 파이프라인의 응답 시간과 SLA 준수 여부를 추적한다. **System Overview**는 전체 컨테이너의 리소스 사용량(CPU, Memory, Network)을 한눈에 보여준다.

Grafana 대시보드를 설계하면서 가장 신경 쓴 것은 "한눈에 이상을 감지할 수 있는가?"였다. 색상 코딩(Green/Yellow/Red)과 임계값 설정을 통해, 대시보드를 열었을 때 빨간색이 보이면 즉시 조치가 필요하다는 것을 알 수 있도록 했다. Grafana 사용자 가이드(`32_grafana_user_guide.md`)도 별도로 작성해서, 운영자가 대시보드를 해석하고 활용할 수 있도록 했다.

Loki + Promtail 조합은 로그 수집을 담당한다. Promtail이 각 컨테이너의 로그를 수집해서 Loki에 전송하고, Grafana에서 LogQL로 검색할 수 있다. 다만 WSL2 환경에서 Docker 로그 경로 이슈가 있었다(사전점검 기존 이슈 4번). WSL2의 Docker Desktop은 로그 파일의 경로가 일반 Linux와 다르기 때문에, Promtail의 `docker_sd_configs`가 기대대로 동작하지 않았다. 완전한 해결은 하지 못했지만, 워크어라운드로 대부분의 로그를 수집할 수 있었다.

Jaeger는 분산 추적을 위한 도구다. 16686 포트로 UI에 접근할 수 있고, 서비스 간 호출 체인을 시각화한다. 다만 솔직히 말하면, 실제 서비스 계측(OpenTelemetry instrumentation)이 완전히 적용되지 않아서 Jaeger의 활용도는 기대에 미치지 못했다(사전점검 기존 이슈 3번). 인프라는 구축했지만, 각 서비스에 tracing 코드를 삽입하는 작업이 부족했다. 이것은 내가 DevOps로서 개발팀과 더 긴밀하게 협력했어야 할 부분이다.

Kibana는 Elasticsearch 데이터를 시각화하고 분석하는 도구다. 42,462개 청크의 분포, 임베딩 품질, 검색 쿼리 패턴 등을 분석할 수 있다. `02_kibana_user_guide.md`에 상세 사용법을 문서화했다. Dev Tools에서 직접 ES 쿼리를 실행할 수 있어서, 개발 중 데이터 디버깅에 가장 많이 활용된 도구이기도 하다.

---

## 3. 타임아웃 체인의 복잡성

이 프로젝트에서 내가 가장 많이 머리를 싸맨 문제는 타임아웃 설정이다. 단일 서비스의 타임아웃은 간단하다. 하지만 18개 컨테이너가 체인으로 연결된 환경에서, 각 레이어의 타임아웃이 일관되지 않으면 예측 불가능한 실패가 발생한다.

우리 시스템의 요청 흐름은 이렇다:

```
Frontend (axios) -> Nginx (proxy) -> API Gateway (Spring Cloud) -> AI Service (FastAPI) -> Docling (PDF 파싱)
```

Sprint 12 사용자 테스트에서 대용량 PDF가 전부 실패한 원인을 분석하면서, 나는 이 체인의 각 링크별 타임아웃을 정리했다.

| 레이어 | 변경 전 | 변경 후 |
|--------|:-------:|:-------:|
| Frontend axios | 120,000ms | 1,200,000ms |
| Nginx proxy_send/read_timeout (API) | 300s | 1,200s |
| Nginx upload proxy_send/read_timeout | 600s | 1,200s |
| Docling parse_timeout | 300s | 1,200s |
| Gateway response-timeout | 120s | **미적용** |
| Resilience4j TimeLimiter | 120s | **미적용** |

여기서 교훈은 명확하다. **타임아웃 체인에서 가장 짧은 링크가 전체를 결정한다.** Frontend가 120초에 끊기면, 뒤에서 아무리 기다려도 소용없다. Nginx가 300초에 끊기면, AI Service가 1200초를 설정해도 의미 없다.

나는 이것을 "End-to-End Timeout Chain Diagram"으로 문서화했다. 각 레이어의 타임아웃 값, 데이터 흐름 방향, 병목 지점을 한 그림에 담았다. 운영자 매뉴얼(`03_operator_manual.md`) Section 10에 "타임아웃 설정 가이드"로 포함시켰다. 이 다이어그램이 있으면, 향후 타임아웃 관련 이슈가 발생했을 때 어떤 레이어를 먼저 확인해야 하는지 즉시 파악할 수 있다.

미적용으로 남은 Gateway response-timeout(120s)과 Resilience4j TimeLimiter(120s)는 KI-001로 등록되었다. 별도 Gateway 컨테이너 빌드가 필요했기 때문에 Sprint 12 마감일에 포함하지 못한 것인데, 이것은 나의 판단 실수이기도 하다. Gateway 재빌드를 일찍 시도했더라면 해결할 수 있었을 것이다. 타임아웃 체인 분석을 Sprint 11에 했어야 했는데, Sprint 12 사용자 테스트 날에야 비로소 전체 그림을 파악한 것이 아쉽다.

이 경험에서 나는 "타임아웃은 인프라가 아니라 아키텍처 문제"라는 것을 배웠다. 개별 서비스의 타임아웃은 각 팀이 설정하지만, 전체 체인의 일관성은 누군가가 end-to-end로 관리해야 한다. 그 역할이 DevOps에게 있었는데, 내가 더 일찍 체인 전체를 조망했어야 했다.

---

## 4. /metrics 404 -- 설정은 있었으나 구현은 없었다

이 프로젝트에서 가장 부끄러운 사건 중 하나다. Prometheus가 AI Service를 스크래핑하도록 `prometheus.yml`에 타겟을 설정해놓았다. `ai-service:8000`이 타겟이었고, `/metrics` 엔드포인트를 긁어가도록 했다. 설정은 완벽했다. 문제는 AI Service에 `/metrics` 엔드포인트가 존재하지 않았다는 것이다.

Prometheus의 타겟 상태를 확인하면 ai-service가 "DOWN"으로 표시되어 있었다. 404 Not Found. Prometheus가 정직하게 "이 엔드포인트 없는데요?"라고 말하고 있었지만, 나는 Sprint 10까지 이것을 확인하지 않았다.

원인은 이렇다. Spring Boot 서비스(Backend, Gateway)는 Actuator를 의존성에 추가하면 자동으로 `/actuator/prometheus` 엔드포인트가 생긴다. 반면 FastAPI 기반의 AI Service는 `prometheus-fastapi-instrumentator`를 명시적으로 설치하고 코드에서 `Instrumentator().instrument(app)`을 호출해야 한다. Spring Boot의 자동 설정에 익숙해진 나머지, FastAPI도 비슷할 것이라고 가정한 것이다.

이 문제는 사전점검 기존 이슈로 등록되어 있다(기존 이슈 1번: ai-service `/metrics` 미구현). `prometheus-fastapi-instrumentator`를 설치하고 app.py에 한 줄을 추가하면 해결되는 간단한 작업이었지만, Sprint 12 마감 시점에 우선순위가 낮아서 미처리로 남았다.

이 사건은 Infra Engineer의 회고에서도 언급될 "Nori 미적용 사고"와 같은 맥락이다. **"설정했다고 동작하는 것이 아니다."** Prometheus 설정 파일에 타겟을 추가한 것으로 모니터링이 완성된 것이 아니었다. 실제로 Prometheus UI에서 타겟 상태를 확인하고, 메트릭이 수집되는지 검증했어야 했다.

이 경험 이후 나는 "Observability 자체의 관측"이라는 개념을 갖게 되었다. 모니터링 시스템이 올바르게 동작하는지를 모니터링해야 한다. Prometheus가 모든 타겟을 정상적으로 스크래핑하고 있는지, Grafana가 데이터를 받고 있는지, Loki가 로그를 수집하고 있는지. 관측 도구의 관측 가능성. 메타-Observability라고 할 수 있다.

마찬가지로 Elasticsearch Prometheus exporter도 미설치 상태였고(기존 이슈 2번), Jaeger 서비스 계측도 미적용이었다(기존 이슈 3번). Observability 스택의 인프라는 구축했지만, 각 서비스와의 통합이 부족했다. 이것은 "인프라 구축"과 "인프라 활용" 사이의 간극이다. 도구를 설치하는 것과 도구를 제대로 쓰는 것은 다른 문제다.

---

## 5. 아쉬운 점과 팀원들에게

가장 큰 아쉬움은 **Observability 스택의 완성도**다. 5개 도구를 모두 Docker Compose에 올렸지만, 실질적으로 "운영 가능 수준"에 도달한 것은 Prometheus + Grafana 조합뿐이다. Jaeger는 계측 미적용, Loki/Promtail은 WSL2 경로 이슈, AI Service /metrics는 미구현. 인프라를 "올리는 것"에 집중하다가 "쓰는 것"을 소홀히 했다. 다음 프로젝트에서는 "Observability readiness checklist"를 만들어서, 도구 설치 -> 서비스 계측 -> 대시보드 검증 -> 알림 설정까지 한 사이클을 완주하고 싶다.

둘째 아쉬움은 **알림(Alerting) 규칙의 부재**다. AlertManager 컨테이너는 Docker Compose에 포함되어 있었지만, 실질적인 알림 규칙을 정의하지 못했다. "검색 응답 시간이 3초를 넘으면 Slack으로 알림", "컨테이너 메모리 사용률이 90%를 넘으면 경고" 같은 규칙이 있었어야 했다. Grafana에서 시각적으로 확인하는 것과, 알림이 자동으로 오는 것은 완전히 다른 차원의 운영이다.

셋째, **CI/CD의 실전 배포 활용도**가 낮았다. deploy-staging, deploy-production 워크플로우를 만들었지만, 실제 배포는 대부분 수동으로(`docker compose up -d --build`) 이루어졌다. WSL2 로컬 환경이라는 특수성 때문이기도 하지만, CI/CD가 진짜 빛을 발하는 것은 "버튼 하나로 프로덕션에 배포하고, 문제 발생 시 자동 롤백"하는 파이프라인이다. 그 수준에는 도달하지 못했다.

팀원들에게.

**Infra Engineer에게**: 당신과 나는 가장 밀접하게 협업한 사이다. Docker Compose 환경을 당신이 구축하고, 그 위에 나의 CI/CD와 Observability를 올렸다. "infra는 환경 구축, devops는 운영 자동화"라는 역할 분담이 대부분 잘 작동했지만, 타임아웃 체인 같은 "인프라와 운영의 경계" 문제에서는 더 긴밀한 소통이 필요했다. 다음에는 주간 인프라-DevOps 싱크 미팅을 하면 좋겠다.

**QA Engineer에게**: CI에서 174개 테스트가 매번 돌아가는 것이 당연하게 느껴질 수도 있지만, 그 테스트 코드를 작성하고 유지한 당신의 노력에 감사한다. CI/CD의 가치는 결국 "무엇을 자동으로 검증하느냐"에 달려 있고, 그 "무엇"을 만든 것은 QA다.

**Backend Developer에게**: Spring Boot Actuator 덕분에 Backend와 Gateway의 메트릭 수집은 순탄했다. `/actuator/health`, `/actuator/prometheus` 엔드포인트가 기본 제공되는 것의 편리함을 새삼 느꼈다. FastAPI에서도 비슷한 수준의 자동 설정이 가능하도록, `prometheus-fastapi-instrumentator`를 기본 의존성으로 포함시키는 것을 다음에는 초기 설계에 반영해야 한다.

**RAG Engineer에게**: AI Service의 `/metrics` 미구현이 나의 가장 큰 실수 중 하나인데, 이것은 당신의 잘못이 아니라 내가 요구사항을 제때 전달하지 못한 탓이다. "이 서비스에 이 엔드포인트가 필요하다"를 Sprint 초기에 명확히 커뮤니케이션했어야 했다.

이 프로젝트를 통해 나는 "DevOps는 도구가 아니라 문화"라는 진부한 말의 진정한 의미를 체감했다. GitHub Actions 워크플로우를 10개 만드는 것보다, 팀원 모두가 "CI가 통과해야 머지한다"는 문화를 공유하는 것이 더 중요했다. Prometheus와 Grafana를 올리는 것보다, "대시보드를 매일 확인하는 습관"이 더 중요했다. 도구는 수단이고, 문화가 목적이다. 41일이라는 짧은 프로젝트에서 문화까지 정착시키기는 어려웠지만, 그 씨앗은 뿌렸다고 생각한다.

---

*작성: DevOps Engineer Agent (Sonnet 4.6) | 2026-02-19*
