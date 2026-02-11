# Monitoring & Alerting Operations Guide

---

## Document Information

| Item | Content |
|------|---------|
| **Document Name** | Monitoring & Alerting Operations Guide |
| **Version** | 1.0 |
| **Created** | 2026-02-04 |
| **Author** | DevOps Engineer (Claude Code) |
| **Status** | Active |
| **Related STORY** | STORY-079 |
| **Related Docs** | [Observability Design](../02_design/14_observability_detailed_design.md), [Infrastructure Design](../02_design/10_infrastructure_detailed_design.md) |

---

## Table of Contents

1. [Overview](#1-overview)
2. [Monitoring Stack Architecture](#2-monitoring-stack-architecture)
3. [Prometheus Configuration](#3-prometheus-configuration)
4. [Grafana Dashboards](#4-grafana-dashboards)
5. [Alert Rules Reference](#5-alert-rules-reference)
6. [AlertManager Configuration](#6-alertmanager-configuration)
7. [Slack Integration](#7-slack-integration)
8. [SLA Monitoring](#8-sla-monitoring)
9. [Operations Runbook](#9-operations-runbook)
10. [Troubleshooting Guide](#10-troubleshooting-guide)

---

## 1. Overview

### 1.1 Purpose

This guide provides comprehensive documentation for operating the monitoring and alerting infrastructure of the Knowledge Platform. It covers:

- Prometheus metrics collection and alert rules
- Grafana dashboard usage and customization
- AlertManager configuration and Slack integration
- SLA/SLO monitoring and error budget tracking
- Incident response procedures

### 1.2 Monitoring Stack Components

| Component | Version | Port | Purpose |
|-----------|---------|------|---------|
| Prometheus | v2.48.0 | 9090 | Metrics collection and alerting |
| Grafana | v10.2.0 | 3001 | Visualization and dashboards |
| Loki | v2.9.0 | 3100 | Log aggregation |
| Promtail | v2.9.0 | - | Log collection agent |
| Jaeger | v1.52 | 16686 | Distributed tracing |
| AlertManager | v0.26.0 | 9093 | Alert routing and notification |

### 1.3 Access URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| Grafana | http://localhost:3001 | admin / (GRAFANA_ADMIN_PASSWORD) |
| Prometheus | http://localhost:9090 | No auth (internal only) |
| AlertManager | http://localhost:9093 | No auth (internal only) |
| Jaeger UI | http://localhost:16686 | No auth |
| Kibana | http://localhost:5601 | No auth |

---

## 2. Monitoring Stack Architecture

### 2.1 Data Flow

```
+------------------+     +------------------+     +------------------+
|   Applications   |     |    Prometheus    |     |    Grafana       |
|                  |     |                  |     |                  |
| - Backend        +---->+ - Scrape metrics +---->+ - Dashboards     |
| - AI Service     |     | - Evaluate rules |     | - Alerting UI    |
| - API Gateway    |     | - Store TSDB     |     | - Explore        |
+------------------+     +--------+---------+     +------------------+
                                  |
                                  v
                         +--------+---------+
                         |   AlertManager   |
                         |                  |
                         | - Route alerts   |
                         | - Group alerts   |
                         | - Send to Slack  |
                         +------------------+
```

### 2.2 Container Network

All monitoring containers are on the `kp-monitoring` network with access to:
- `kp-backend` network for scraping application metrics
- External Slack webhook for notifications

---

## 3. Prometheus Configuration

### 3.1 File Locations

| File | Path | Purpose |
|------|------|---------|
| Main config | `infrastructure/docker/prometheus/prometheus.yml` | Scrape targets, global settings |
| Alert rules | `infrastructure/docker/prometheus/rules/alert-rules.yml` | All alerting rules |
| Legacy alerts | `infrastructure/docker/prometheus/rules/alerts.yml` | (Deprecated) Original alerts |

### 3.2 Scrape Targets

| Job Name | Target | Metrics Path | Labels |
|----------|--------|--------------|--------|
| prometheus | localhost:9090 | /metrics | service: prometheus |
| api-gateway | api-gateway:8080 | /actuator/prometheus | layer: application |
| backend | backend:8081 | /actuator/prometheus | layer: application |
| ai-service | ai-service:8000 | /metrics | layer: application |
| keycloak | keycloak:8080 | /metrics | layer: auth |
| elasticsearch | elasticsearch:9200 | /_prometheus/metrics | layer: database |
| neo4j | neo4j:2004 | /metrics | layer: database |
| loki | loki:3100 | /metrics | layer: monitoring |
| jaeger | jaeger:14269 | /metrics | layer: monitoring |

### 3.3 Adding New Scrape Target

```yaml
# Add to prometheus.yml under scrape_configs
- job_name: 'new-service'
  metrics_path: '/metrics'
  scrape_interval: 15s
  static_configs:
    - targets: ['new-service:8080']
      labels:
        service: 'new-service'
        layer: 'application'
```

### 3.4 Reload Configuration

```bash
# Hot reload (no restart required)
curl -X POST http://localhost:9090/-/reload

# Or restart container
docker restart kp-prometheus
```

---

## 4. Grafana Dashboards

### 4.1 Available Dashboards

| Dashboard | UID | Description |
|-----------|-----|-------------|
| System Overview | kp-system-overview | Service health, container resources, active alerts |
| Application Metrics | kp-application-metrics | Request rates, latency, error rates, JVM metrics |
| Database Metrics | kp-database-metrics | PostgreSQL, Elasticsearch, Redis, Neo4j health |
| RAG & SLA | kp-rag-sla | SLA compliance, RAG pipeline, LLM metrics |

### 4.2 Dashboard Locations

```
infrastructure/docker/grafana/dashboards/
├── system-overview.json
├── application-metrics.json
├── database-metrics.json
└── rag-sla-dashboard.json
```

### 4.3 Key Panels by Dashboard

#### System Overview
- Service Health Status (8 services)
- CPU Usage by Service
- Memory Usage by Service
- Container Network I/O
- Active Alerts List

#### Application Metrics
- Request Rate by Service
- Error Rate (Backend, AI Service)
- Latency Percentiles (P50, P95, P99)
- Circuit Breaker Status
- HTTP Status Code Distribution
- JVM Heap Memory & Threads

#### Database Metrics
- Database Health (PostgreSQL, ES, Neo4j, Redis)
- Elasticsearch Cluster Health & Document Count
- Redis Memory Usage & Cache Hit Rate
- Neo4j Graph Size & Memory

#### RAG & SLA Dashboard
- 24h/7d/30d Availability
- Error Budget Remaining
- Search Latency SLO
- RAG Component Latency
- LLM Token Usage & Cost
- Search Relevance Score Distribution

### 4.4 Creating Custom Dashboards

1. Go to Grafana > Create > Dashboard
2. Add panels using Prometheus queries
3. Save dashboard
4. Export JSON for version control:
   ```
   Dashboard Settings > JSON Model > Copy to clipboard
   ```
5. Save to `infrastructure/docker/grafana/dashboards/`

---

## 5. Alert Rules Reference

### 5.1 Alert Categories

| Category | Severity Range | Description |
|----------|---------------|-------------|
| container-health | Critical | Container up/down, restart count |
| resource-usage | Warning-Critical | CPU, memory, disk |
| application-health | Warning-Critical | Error rate, latency, circuit breaker |
| database-health | Warning-Critical | DB connectivity, cluster health |
| ai-service | Warning-Critical | AI latency, LLM errors, processing queue |
| sla-alerts | Warning-Critical | Availability, error budget |
| security-alerts | Warning-Critical | Auth failures, rate limiting |
| observability-health | Warning | Monitoring stack health |

### 5.2 Critical Alerts (Immediate Action Required)

| Alert | Condition | For | Action |
|-------|-----------|-----|--------|
| ContainerDown | up == 0 | 30s | Check container logs, restart |
| CriticalServiceDown | up{job=backend/ai-service/postgresql/elasticsearch} == 0 | 15s | Immediate investigation |
| HighErrorRate | 5xx rate > 5% | 5min | Check application logs |
| SLAViolation | availability < 99.9% | 5min | Incident response |
| CircuitBreakerOpen | state == 1 | 1min | Check downstream service |
| AuthenticationBruteForce | auth failures > 10/min | 2min | Block IP, investigate |

### 5.3 Warning Alerts (Investigation Required)

| Alert | Condition | For | Action |
|-------|-----------|-----|--------|
| ElevatedErrorRate | 5xx rate > 1% | 10min | Monitor, investigate if persists |
| HighLatency | P95 > 5s | 5min | Check dependencies |
| HighMemoryUsage | > 85% | 5min | Scale or optimize |
| LowDiskSpace | < 15% free | 5min | Cleanup or expand |
| ErrorBudgetHalfConsumed | > 50% used | 1h | Review deployment velocity |

### 5.4 Adding New Alert Rule

```yaml
# Add to alert-rules.yml
- alert: NewAlertName
  expr: |
    your_prometheus_query > threshold
  for: 5m
  labels:
    severity: warning
    category: application
    team: backend
  annotations:
    summary: "Brief description"
    description: "Detailed description with {{ $value }}"
    runbook_url: "https://wiki/runbook/new-alert"
```

---

## 6. AlertManager Configuration

### 6.1 Configuration File

Location: `infrastructure/docker/alertmanager/alertmanager.yml`

### 6.2 Routing Hierarchy

```
default-slack (all alerts)
├── critical-pager (severity: critical)
├── database-slack (category: database)
├── ai-service-slack (category: ai)
├── security-slack (category: security)
├── sla-slack (category: sla)
├── warning-slack (severity: warning)
└── info-slack (severity: info)
```

### 6.3 Receivers Overview

| Receiver | Channel | Icon | Use Case |
|----------|---------|------|----------|
| default-slack | #proj-hrkp-alerts | :bell: | All unrouted alerts |
| critical-pager | #proj-hrkp-alerts | :rotating_light: | Critical + @channel |
| database-slack | #proj-hrkp-alerts | :database: | Database issues |
| ai-service-slack | #proj-hrkp-alerts | :robot_face: | AI service issues |
| security-slack | #proj-hrkp-alerts | :lock: | Security events |
| sla-slack | #proj-hrkp-alerts | :chart_with_upwards_trend: | SLA violations |
| warning-slack | #proj-hrkp-alerts | :warning: | Warning level |
| info-slack | #proj-hrkp-dev | :information_source: | Informational |

### 6.4 Inhibition Rules

Prevents alert storms by suppressing lower-priority alerts:

1. Critical suppresses Warning (same alertname/job)
2. Critical suppresses Info (same alertname/job)
3. Warning suppresses Info (same alertname/job)
4. ContainerDown suppresses resource alerts
5. Service Down suppresses performance alerts

---

## 7. Slack Integration

### 7.1 Webhook Configuration

Set the `SLACK_WEBHOOK_URL` environment variable:

```bash
# In .env file
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T.../B.../xxx
```

### 7.2 Channel Mapping

| Alert Type | Slack Channel | Urgency |
|------------|--------------|---------|
| Critical/Page | #proj-hrkp-alerts | Immediate (with @channel) |
| Warning | #proj-hrkp-alerts | Within 1 hour |
| Info | #proj-hrkp-dev | Business hours |

### 7.3 Alert Message Format

```
:rotating_light: CRITICAL: ContainerDown
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@channel
*CRITICAL ALERT*
*Alert:* Container backend is down
*Description:* Container backend (kp-backend) has been down for more than 30 seconds
*Time:* 2026-02-04 15:30:00 KST
*Runbook:* https://wiki/runbook/container-down
```

### 7.4 Testing Slack Integration

```bash
# Test AlertManager config
docker exec kp-alertmanager amtool check-config /etc/alertmanager/alertmanager.yml

# Send test alert
curl -X POST http://localhost:9093/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '[{
    "labels": {"alertname": "TestAlert", "severity": "warning"},
    "annotations": {"summary": "Test alert from AlertManager"}
  }]'
```

---

## 8. SLA Monitoring

### 8.1 SLA Definitions

| Metric | Target | Calculation |
|--------|--------|-------------|
| Availability | 99.9% | 1 - (5xx / total requests) |
| Search Latency P95 | < 500ms | 95th percentile response time |
| Error Rate | < 0.1% | 5xx responses / total |

### 8.2 Error Budget

```
Monthly Error Budget = 100% - 99.9% = 0.1%
Allowed Downtime = 30 days * 24h * 60min * 0.1% = 43.2 minutes/month

Weekly Budget = 43.2 / 4 = ~10.8 minutes/week
```

### 8.3 Key PromQL Queries

```promql
# 24-hour Availability
(1 - (
  sum(rate(http_server_requests_seconds_count{status=~"5.."}[24h]))
  /
  sum(rate(http_server_requests_seconds_count[24h]))
)) * 100

# Error Budget Remaining (30d)
100 - ((
  sum(rate(http_server_requests_seconds_count{status=~"5.."}[30d]))
  /
  sum(rate(http_server_requests_seconds_count[30d]))
) / 0.001 * 100)

# Search Latency P95
histogram_quantile(0.95,
  rate(http_server_requests_seconds_bucket{uri=~"/api/v1/search.*"}[5m])
)
```

### 8.4 SLA Dashboard Panels

The RAG & SLA Dashboard (kp-rag-sla) includes:
- Real-time availability gauge (24h, 7d)
- Error budget remaining percentage
- Availability trend over time
- Latency SLO compliance

---

## 9. Operations Runbook

### 9.1 Daily Checks

| Time | Task | Tool |
|------|------|------|
| 09:00 | Review overnight alerts | Slack #proj-hrkp-alerts |
| 09:15 | Check System Overview dashboard | Grafana |
| 09:30 | Verify all services UP | Grafana System Overview |
| 17:00 | Review error budget consumption | Grafana RAG & SLA |

### 9.2 Weekly Checks

| Day | Task | Deliverable |
|-----|------|-------------|
| Monday | Review SLA compliance | SLA report |
| Wednesday | Check disk space trends | Capacity forecast |
| Friday | Review alert trends | Alert tuning recommendations |

### 9.3 Incident Response Process

```
1. DETECT
   └── AlertManager notification → Slack

2. TRIAGE (15 min max)
   ├── Assess severity (Critical/Warning)
   ├── Identify affected services
   └── Assign incident owner

3. DIAGNOSE
   ├── Grafana: Check metrics dashboards
   ├── Loki: Search related logs
   ├── Jaeger: Trace request flow
   └── Identify root cause

4. MITIGATE
   ├── Apply immediate fix (restart, rollback)
   ├── Notify stakeholders
   └── Document actions taken

5. RESOLVE
   ├── Verify services recovered
   ├── Close alert
   └── Update incident ticket

6. POST-MORTEM (within 48h)
   ├── Document timeline
   ├── Identify root cause
   ├── Define prevention measures
   └── Update runbooks/alerts
```

### 9.4 Common Operations

#### Restart Monitoring Stack
```bash
cd infrastructure/docker
docker-compose restart prometheus grafana alertmanager loki
```

#### Check Prometheus Targets
```bash
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'
```

#### Silence Alert (maintenance)
```bash
# Via AlertManager API
curl -X POST http://localhost:9093/api/v1/silences \
  -H "Content-Type: application/json" \
  -d '{
    "matchers": [{"name": "alertname", "value": "ContainerDown", "isRegex": false}],
    "startsAt": "2026-02-04T10:00:00Z",
    "endsAt": "2026-02-04T12:00:00Z",
    "createdBy": "devops",
    "comment": "Planned maintenance"
  }'
```

#### Export Dashboard
```bash
# Export all dashboards
curl -H "Authorization: Bearer $GRAFANA_TOKEN" \
  http://localhost:3001/api/dashboards/uid/kp-system-overview \
  | jq '.dashboard' > system-overview-export.json
```

---

## 10. Troubleshooting Guide

### 10.1 Common Issues

#### Prometheus Not Scraping Target

**Symptoms**: Target shows as DOWN in Prometheus targets page

**Diagnosis**:
```bash
# Check target connectivity
docker exec kp-prometheus wget -q -O- http://backend:8081/actuator/prometheus

# Check Prometheus logs
docker logs kp-prometheus --tail 100
```

**Resolution**:
1. Verify target container is running
2. Check network connectivity between prometheus and target
3. Verify metrics endpoint is accessible
4. Check firewall/security group rules

#### Grafana Dashboard Not Loading

**Symptoms**: Dashboard shows "No data" or loading spinner

**Diagnosis**:
```bash
# Test Prometheus connection from Grafana
docker exec kp-grafana wget -q -O- http://prometheus:9090/api/v1/query?query=up

# Check Grafana logs
docker logs kp-grafana --tail 100
```

**Resolution**:
1. Verify Prometheus datasource configuration
2. Check time range selection
3. Test query in Prometheus UI first
4. Verify dashboard JSON syntax

#### Alerts Not Firing

**Symptoms**: Expected alert not appearing despite condition being met

**Diagnosis**:
```bash
# Check alert evaluation in Prometheus
curl http://localhost:9090/api/v1/rules | jq '.data.groups[].rules[] | select(.name=="AlertName")'

# Check AlertManager
curl http://localhost:9093/api/v1/alerts
```

**Resolution**:
1. Verify alert rule syntax
2. Check `for` duration - alert may still be pending
3. Verify alert is not silenced
4. Check inhibition rules

#### Slack Notifications Not Received

**Symptoms**: Alerts fire but no Slack message

**Diagnosis**:
```bash
# Test webhook directly
curl -X POST $SLACK_WEBHOOK_URL \
  -H "Content-Type: application/json" \
  -d '{"text": "Test message from AlertManager"}'

# Check AlertManager logs
docker logs kp-alertmanager --tail 100
```

**Resolution**:
1. Verify SLACK_WEBHOOK_URL is set correctly
2. Check webhook URL hasn't expired
3. Verify channel exists and bot has access
4. Check AlertManager receiver configuration

### 10.2 Emergency Procedures

#### Complete Monitoring Stack Failure

```bash
# 1. Stop all monitoring containers
docker-compose stop prometheus grafana alertmanager loki promtail

# 2. Clear potentially corrupted data
docker volume rm kp-prometheus-data kp-grafana-data kp-loki-data

# 3. Restart with fresh data
docker-compose up -d prometheus grafana alertmanager loki promtail

# 4. Restore Grafana dashboards (auto-provisioned from files)
# 5. Verify all targets are scraping
```

#### High Cardinality Causing Prometheus OOM

```bash
# 1. Identify high cardinality metrics
curl 'http://localhost:9090/api/v1/status/tsdb' | jq '.data.seriesCountByMetricName | to_entries | sort_by(-.value) | .[0:10]'

# 2. Temporarily increase memory
# Edit docker-compose.yml: prometheus memory limit

# 3. Add relabeling to drop high-cardinality labels
# Edit prometheus.yml scrape_configs

# 4. Restart with new config
docker-compose restart prometheus
```

---

## Appendix

### A. Useful PromQL Queries

```promql
# Service availability (5m window)
avg_over_time(up{job="backend"}[5m])

# Request rate by endpoint
sum(rate(http_server_requests_seconds_count[5m])) by (uri)

# Memory usage percentage
(container_memory_usage_bytes / container_spec_memory_limit_bytes) * 100

# Top 5 slowest endpoints
topk(5, histogram_quantile(0.95, rate(http_server_requests_seconds_bucket[5m])))
```

### B. Configuration Files Reference

| File | Description |
|------|-------------|
| prometheus.yml | Prometheus scrape config |
| alert-rules.yml | All alert rules |
| alertmanager.yml | Alert routing and receivers |
| datasources.yml | Grafana data sources |
| dashboards.yml | Grafana dashboard provisioning |
| *.json | Grafana dashboard definitions |

### C. Port Reference

| Port | Service | Protocol |
|------|---------|----------|
| 9090 | Prometheus | HTTP |
| 3001 | Grafana | HTTP |
| 9093 | AlertManager | HTTP |
| 3100 | Loki | HTTP |
| 16686 | Jaeger UI | HTTP |
| 5601 | Kibana | HTTP |

---

**Document maintained by**: DevOps Team
**Last updated**: 2026-02-04
**Review cycle**: Monthly
