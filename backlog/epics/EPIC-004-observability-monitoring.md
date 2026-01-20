# EPIC-004: Observability & Monitoring

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-50 |
| **Status** | ready |
| **Priority** | High |
| **Owner** | TBD |
| **Target Sprint** | Sprint 4 |
| **Total Story Points** | 24 |

---

## 요약

Prometheus/Grafana 메트릭, Loki 로깅, Jaeger 트레이싱으로 구성된 Observability 스택 구축. 시스템 상태 모니터링, RAG 품질 대시보드, 장애 탐지 및 알림 체계 구현.

---

## 배경 및 목표

### 배경
- 분산 시스템의 상태 가시성 확보 필요
- RAG 파이프라인 품질 지표 실시간 모니터링
- 장애 발생 시 신속한 원인 파악 및 대응

### 목표
- 통합 Observability 대시보드 구축
- 주요 SLA 지표 실시간 추적
- 자동 알림 및 장애 탐지 체계 구축

### 성공 지표
- [ ] 모든 서비스 메트릭 수집
- [ ] RAG 품질 대시보드 구축
- [ ] 알림 규칙 10개 이상 설정
- [ ] 분산 트레이싱 정상 동작

---

## User Stories

| ID | Jira | 제목 | Points | Status | Sprint |
|----|------|------|--------|--------|--------|
| STORY-050 | SCRUM-51 | Prometheus 메트릭 수집 | 5 | To Do | 4 |
| STORY-051 | SCRUM-52 | Grafana 대시보드 구성 | 5 | To Do | 4 |
| STORY-052 | SCRUM-53 | Loki 로그 집계 | 5 | To Do | 4 |
| STORY-053 | SCRUM-54 | Jaeger 분산 트레이싱 | 5 | To Do | 4 |
| STORY-054 | SCRUM-55 | 알림 규칙 및 Alertmanager | 4 | To Do | 4 |

---

## 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Observability Architecture                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                         Services                                │   │
│  │  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐   │   │
│  │  │Frontend│  │API GW  │  │Backend │  │AI Svc  │  │DB Layer│   │   │
│  │  └───┬────┘  └───┬────┘  └───┬────┘  └───┬────┘  └───┬────┘   │   │
│  └──────┼──────────┼──────────┼──────────┼──────────┼──────────┘   │
│         │          │          │          │          │               │
│         ▼          ▼          ▼          ▼          ▼               │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Collection Layer                             │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │   │
│  │  │ Prometheus  │  │  Promtail   │  │ OpenTelemetry Collector │ │   │
│  │  │ (Metrics)   │  │  (Logs)     │  │      (Traces)           │ │   │
│  │  └──────┬──────┘  └──────┬──────┘  └────────────┬────────────┘ │   │
│  └─────────┼───────────────┼──────────────────────┼────────────────┘   │
│            │               │                      │                     │
│            ▼               ▼                      ▼                     │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     Storage Layer                               │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │   │
│  │  │ Prometheus  │  │    Loki     │  │   Jaeger    │             │   │
│  │  │   TSDB      │  │   Store     │  │   Store     │             │   │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │   │
│  └─────────┼───────────────┼─────────────────┼─────────────────────┘   │
│            │               │                 │                         │
│            └───────────────┼─────────────────┘                         │
│                            ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      Grafana                                    │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │   │
│  │  │System Dash  │  │ RAG Dash    │  │ Alert Rules │             │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 기술 요구사항

### 기술 스택
| 구성요소 | 기술 | 버전 |
|----------|------|------|
| Metrics | Prometheus | 2.48 |
| Visualization | Grafana | 10.2 |
| Logging | Loki + Promtail | 2.9 |
| Tracing | Jaeger | 1.51 |
| Alerting | Alertmanager | 0.26 |

### 수집 메트릭
| 카테고리 | 메트릭 |
|----------|--------|
| System | CPU, Memory, Disk, Network |
| Application | Request rate, Latency, Error rate |
| RAG Quality | Faithfulness, Relevancy, Context scores |
| Business | Search count, User sessions |

### 대시보드 목록
| 대시보드 | 용도 |
|----------|------|
| System Overview | 전체 시스템 상태 |
| API Performance | API 응답시간/에러율 |
| RAG Quality | RAG 품질 지표 |
| Error Analysis | 에러 분석 |
| SLA Monitoring | SLA 준수 현황 |

### 알림 규칙
| 규칙 | 조건 | 심각도 |
|------|------|--------|
| High Error Rate | error_rate > 5% | Critical |
| Slow Response | p95_latency > 3s | Warning |
| Low Faithfulness | faithfulness < 0.85 | Warning |
| Service Down | up == 0 | Critical |

---

## 선행 조건 (Sprint 3 완료 필요)

- [ ] 모든 서비스 정상 동작
- [ ] Prometheus/Grafana 컨테이너 기동 (STORY-010)
- [ ] Backend/AI Service 메트릭 노출

---

## 리스크 및 의존성

### 리스크
| 리스크 | 영향 | 대응 |
|--------|------|------|
| 메트릭 카디널리티 폭발 | High | 레이블 최소화 |
| 로그 볼륨 과다 | Medium | 샘플링, 보존기간 설정 |
| 트레이스 오버헤드 | Low | 샘플링 비율 조정 |

### 의존성
- [ ] Docker 네트워크 설정
- [ ] 서비스 메트릭 엔드포인트 구현

---

## 참고 자료

- [인프라 상세 설계서](../../knowledge_service/docs/02_design/infrastructure_detailed_design.md)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [Grafana Dashboard Examples](https://grafana.com/grafana/dashboards/)
