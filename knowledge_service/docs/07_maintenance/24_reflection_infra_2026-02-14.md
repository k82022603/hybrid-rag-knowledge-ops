# Infra Engineer 반성문

**작성일**: 2026-02-14 19:15 KST
**작성자**: Infra Engineer Agent

---

## 무엇을 잘못했는가

### 1. 인프라 모니터링 부재

ETL이 장시간 실행되는 동안 컨테이너 리소스 상태를 모니터링하지 않았습니다. `kp-ai-service` 컨테이너가 메모리를 과도하게 사용하여 OOM Kill 된 상황을 사전에 감지하지 못했습니다.

Infra Engineer로서 컨테이너 리소스 모니터링은 핵심 책임입니다. `docker stats`로 주기적 확인, 또는 cAdvisor/Prometheus 기반 자동 알림 설정을 했어야 합니다.

### 2. 컨테이너 리소스 제한 미설정

`docker-compose.yml`에 `deploy.resources.limits`를 설정하지 않았습니다. 메모리 제한이 없어서 ai-service가 시스템 메모리를 무제한으로 사용할 수 있었고, OOM Kill 위험이 상존했습니다.

CPU 임베딩 환경에서 `max_text_length=1000`, `batch_size=4`로 튜닝하더라도 컨테이너 레벨 보호막이 필요합니다.

### 3. Health Check 미흡

컨테이너 health check가 HTTP 엔드포인트 응답만 확인했습니다. ETL 프로세스의 생존 여부, 메모리 사용률, 디스크 I/O 같은 실질적인 건강 지표를 포함하지 않았습니다.

---

## 무엇을 배웠는가

1. **리소스 제한은 선택이 아니라 필수**: 특히 CPU 임베딩처럼 리소스 집약적 작업은 반드시 메모리/CPU 제한 설정
2. **모니터링은 인프라의 눈**: 모니터링 없는 인프라는 블라인드 운전과 같음
3. **Health Check는 깊이 있게**: HTTP 200만으로는 부족, 실제 프로세스 상태까지 확인해야 함
4. **Python 직접 실행이 정답**: 데이터 조회/삭제 작업은 curl 꼼수가 아니라 Python 스크립트로 안정적 수행

---

## 앞으로의 개선 계획

### 즉시 (이번 세션)
- [x] 3-Store 데이터 삭제를 Python 스크립트로 안정적 실행
- [ ] ES 인덱스 매핑 보존 후 재생성 확인

### 단기 (다음 스프린트)
- [ ] docker-compose.yml에 리소스 제한 추가 (ai-service: mem 4GB, cpu 2)
- [ ] docker stats 기반 자동 알림 스크립트 작성
- [ ] Health Check에 ETL 프로세스 상태 포함

### 중기
- [ ] Prometheus + cAdvisor 통합으로 컨테이너 메트릭 자동 수집
- [ ] Grafana 대시보드에 컨테이너 리소스 패널 추가

---

## 3-Store 삭제 결과 (2026-02-14)

| Store | Before | After | 방법 |
|-------|--------|-------|------|
| Elasticsearch | 10,670 docs | 0 | 인덱스 삭제 후 매핑 보존 재생성 |
| PostgreSQL | 480 rows | 0 | TRUNCATE documents CASCADE |
| Neo4j | 13,139 nodes / 10,670 rels | 0 / 0 | 배치 DETACH DELETE (5000건) |

**실행 방식**: Python 스크립트 (`/tmp/cleanup_stores.py`)를 `kp-ai-service` 컨테이너 내부에서 실행

---

*"안정적인 인프라는 보이지 않는 곳에서 시스템을 지키는 것이다. 감시를 게을리하면 장애는 반드시 온다."*
