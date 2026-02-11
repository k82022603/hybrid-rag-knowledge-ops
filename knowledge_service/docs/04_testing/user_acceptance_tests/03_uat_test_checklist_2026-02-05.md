# UAT Test Checklist - 2026-02-05

**Version**: 1.0.0
**Date**: 2026-02-05
**Environment**: Development (Docker Compose)
**Prepared By**: QA Agent

---

## Table of Contents

1. [Test Environment Status](#1-test-environment-status)
2. [Pre-Test Checklist](#2-pre-test-checklist)
3. [Test Account Information](#3-test-account-information)
4. [UAT Test Scenarios](#4-uat-test-scenarios)
   - 4.1 [Authentication & Login](#41-authentication--login)
   - 4.2 [Document Upload](#42-document-upload)
   - 4.3 [Document Processing](#43-document-processing)
   - 4.4 [Search Functionality](#44-search-functionality)
   - 4.5 [Dashboard Features](#45-dashboard-features)
   - 4.6 [Logout & Session](#46-logout--session)
5. [Test Result Recording Template](#5-test-result-recording-template)
6. [Issue Reporting Template](#6-issue-reporting-template)
7. [Quick Reference](#7-quick-reference)

---

## 1. Test Environment Status

### 1.1 Docker Container Status (as of 2026-02-05)

| Service | Container | Port | Status |
|---------|-----------|------|--------|
| Nginx (Reverse Proxy) | kp-nginx | 80, 443 | UP (healthy) |
| API Gateway | kp-api-gateway | 8080 | UP (healthy) |
| Backend | kp-backend | 8081 | UP (healthy) |
| AI Service | kp-ai-service | 8000 | UP (healthy) |
| Frontend | kp-frontend | (via Nginx) | UP (healthy) |
| PostgreSQL | kp-postgresql | 5432 | UP (healthy) |
| Redis | kp-redis | 6379 | UP (healthy) |
| Elasticsearch | kp-elasticsearch | 9200 | UP (green) |
| Neo4j | kp-neo4j | 7474, 7687 | UP (healthy) |
| MinIO | kp-minio | 9000, 9001 | UP (healthy) |
| Keycloak | kp-keycloak | 8180 | UP (healthy) |
| Grafana | kp-grafana | 3001 | UP (healthy) |
| Kibana | kp-kibana | 5601 | UP (healthy) |
| Prometheus | kp-prometheus | 9090 | UP (healthy) |
| Jaeger | kp-jaeger | 16686 | UP (healthy) |
| Loki | kp-loki | 3100 | UP (healthy) |
| Promtail | kp-promtail | - | UP |

### 1.2 Health Check Results

| Service | Endpoint | Response |
|---------|----------|----------|
| Gateway | http://localhost:8080/actuator/health | `{"status":"UP"}` |
| Backend | http://localhost:8081/actuator/health | `{"status":"UP"}` |
| AI Service | http://localhost:8000/api/v1/health | `{"status":"healthy"}` |
| Elasticsearch | http://localhost:9200/_cluster/health | `{"status":"green"}` |

---

## 2. Pre-Test Checklist

### 2.1 Environment Preparation

| # | Item | Command/Action | Check |
|---|------|----------------|-------|
| 1 | Docker Compose Running | `docker ps --format "table {{.Names}}\t{{.Status}}"` | [ ] |
| 2 | All Containers Healthy | Check "healthy" status for all services | [ ] |
| 3 | Nginx Accessible | http://localhost | [ ] |
| 4 | Gateway Health OK | http://localhost:8080/actuator/health | [ ] |
| 5 | Backend Health OK | http://localhost:8081/actuator/health | [ ] |
| 6 | AI Service Health OK | http://localhost:8000/api/v1/health | [ ] |
| 7 | Elasticsearch Green | http://localhost:9200/_cluster/health | [ ] |

### 2.2 Required Tools

| Tool | Purpose | Status |
|------|---------|--------|
| Web Browser (Chrome/Edge) | UI Testing | [ ] |
| Developer Tools (F12) | Network/Console inspection | [ ] |
| curl/httpie (optional) | API Testing | [ ] |

### 2.3 Test Data Preparation

| Item | Description | Ready |
|------|-------------|-------|
| Test PDF file | Sample PDF for upload testing | [ ] |
| Test TXT file | Plain text document for upload | [ ] |
| Test PPTX file | PowerPoint presentation | [ ] |
| Test Search Queries | "RAG", "Knowledge Graph", etc. | [ ] |

---

## 3. Test Account Information

### 3.1 Direct Login Account (Recommended)

| Field | Value |
|-------|-------|
| **Email** | admin@example.com |
| **Password** | admin1234 |
| **Roles** | ADMIN, USER |
| **Auth Method** | Direct (HS256 JWT) |

### 3.2 Keycloak Admin Console (Optional)

| Field | Value |
|-------|-------|
| **URL** | http://localhost:8180/admin |
| **Admin Username** | admin |
| **Admin Password** | admin |
| **Realm** | knowledge-platform |

---

## 4. UAT Test Scenarios

### 4.1 Authentication & Login

**Test ID**: UAT-01
**Priority**: P0 (Critical)
**Previous Result**: PASS (2026-02-04)

| Step | Action | Expected Result | Pass/Fail | Notes |
|------|--------|-----------------|-----------|-------|
| 1.1 | Navigate to http://localhost | Login page displayed | [ ] | |
| 1.2 | Verify login form elements | Email, Password fields visible | [ ] | |
| 1.3 | Enter email: admin@example.com | Email accepted | [ ] | |
| 1.4 | Enter password: admin1234 | Password masked | [ ] | |
| 1.5 | Click Login button | Loading indicator | [ ] | |
| 1.6 | Wait for redirect | Dashboard displayed | [ ] | |
| 1.7 | Check user info in header | "adminuser" or email shown | [ ] | |
| 1.8 | Verify localStorage | accessToken exists | [ ] | F12 > Application > Local Storage |

**API Verification** (Optional):

```bash
# Login API Test
curl -X POST "http://localhost:8080/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin1234"}'
```

---

### 4.2 Document Upload

**Test ID**: UAT-02
**Priority**: P0 (Critical)
**Previous Result**: PASS (2026-02-04)
**Prerequisite**: UAT-01 PASS (Logged in)

| Step | Action | Expected Result | Pass/Fail | Notes |
|------|--------|-----------------|-----------|-------|
| 2.1 | Click "Upload" in navigation | Upload page displayed | [ ] | |
| 2.2 | Verify drag & drop zone | Drop zone with icon visible | [ ] | |
| 2.3 | Click "Browse files" or drag file | File picker opens | [ ] | |
| 2.4 | Select test file (PDF/TXT/PPTX) | File name displayed in list | [ ] | |
| 2.5 | Verify file info | Size, type shown | [ ] | |
| 2.6 | Click "Upload All" | Progress bar appears | [ ] | |
| 2.7 | Wait for upload completion | Status shows "Completed" | [ ] | |
| 2.8 | Verify in "Recent Uploads" | Uploaded file listed | [ ] | May need page refresh |

**Supported File Formats**:

| Format | Extension | Max Size | Test |
|--------|-----------|----------|------|
| PDF | .pdf | 50MB | [ ] |
| DOCX | .docx | 50MB | [ ] |
| PPTX | .pptx | 50MB | [ ] |
| TXT | .txt | 50MB | [ ] |
| Markdown | .md | 50MB | [ ] |
| HTML | .html | 50MB | [ ] |
| HWP | .hwp | 50MB | [ ] |

---

### 4.3 Document Processing

**Test ID**: UAT-03
**Priority**: P1 (High)
**Prerequisite**: UAT-02 PASS (Document uploaded)

| Step | Action | Expected Result | Pass/Fail | Notes |
|------|--------|-----------------|-----------|-------|
| 3.1 | Navigate to Knowledge page | Document list displayed | [ ] | |
| 3.2 | Find uploaded document | Document in list | [ ] | |
| 3.3 | Check processing status | Status indicator shown | [ ] | |
| 3.4 | Wait for processing (if needed) | Status changes to "completed" | [ ] | May take 30s-2min |
| 3.5 | Click on document | Document detail view | [ ] | |
| 3.6 | Verify metadata extracted | Type, date, keywords shown | [ ] | |

**Processing Status Reference**:

| Status | Description | Visual |
|--------|-------------|--------|
| uploaded | File saved, awaiting processing | Yellow/Orange |
| processing | Currently being processed | Blue/Spinning |
| completed | Ready for search | Green |
| failed | Processing error | Red |

**Note**: Full document processing (embedding) pipeline may require additional AI Service configuration. Check current implementation status before testing.

---

### 4.4 Search Functionality

**Test ID**: UAT-04
**Priority**: P0 (Critical)
**Prerequisite**: UAT-03 PASS (Documents processed)

#### 4.4.1 UI Search Tests

| Step | Action | Expected Result | Pass/Fail | Notes |
|------|--------|-----------------|-----------|-------|
| 4.1 | Click "Search" in navigation | Search page displayed | [ ] | |
| 4.2 | Enter keyword: "RAG" | Query accepted | [ ] | |
| 4.3 | Press Enter or click Search | Loading indicator | [ ] | |
| 4.4 | View search results | Results list displayed | [ ] | |
| 4.5 | Check result relevance | Related content shown | [ ] | |
| 4.6 | Click on a result | Detail view opens | [ ] | |

#### 4.4.2 Search Type Tests

| Search Type | Query Example | Expected Behavior | Pass/Fail |
|-------------|---------------|-------------------|-----------|
| Keyword | "PostgreSQL" | Exact term matches | [ ] |
| Semantic | "database management" | Conceptually related | [ ] |
| Hybrid | "knowledge graph applications" | Combined results | [ ] |

**API Search Test** (Optional):

```bash
# Get access token first
TOKEN=$(curl -s -X POST "http://localhost:8080/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin1234"}' | jq -r '.accessToken')

# Hybrid Search
curl -X POST "http://localhost:8080/api/v1/search/hybrid" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"RAG system","top_k":5}'
```

---

### 4.5 Dashboard Features

**Test ID**: UAT-05
**Priority**: P1 (High)
**Prerequisite**: UAT-01 PASS (Logged in)

| Step | Action | Expected Result | Pass/Fail | Notes |
|------|--------|-----------------|-----------|-------|
| 5.1 | Navigate to Dashboard | Dashboard page displayed | [ ] | |
| 5.2 | Check statistics cards | Document count, etc. shown | [ ] | |
| 5.3 | Verify Total Documents | Count matches uploads | [ ] | |
| 5.4 | Check Completed Documents | Reflects processing status | [ ] | |
| 5.5 | Verify charts/graphs | Data visualized | [ ] | If implemented |

**Dashboard Statistics Reference**:

| Metric | Description | Expected |
|--------|-------------|----------|
| Total Documents | All uploaded documents | >= 0 |
| Completed Documents | Successfully processed | >= 0 |
| Pending Documents | Awaiting processing | >= 0 |
| Failed Documents | Processing failed | >= 0 |
| Total Searches | Search query count | >= 0 |
| Active Users | Currently active users | >= 1 |

---

### 4.6 Logout & Session

**Test ID**: UAT-06
**Priority**: P1 (High)
**Prerequisite**: UAT-01 PASS (Logged in)

| Step | Action | Expected Result | Pass/Fail | Notes |
|------|--------|-----------------|-----------|-------|
| 6.1 | Click user profile/menu | Dropdown appears | [ ] | |
| 6.2 | Click "Logout" | Confirmation or immediate | [ ] | |
| 6.3 | Verify redirect | Login page displayed | [ ] | |
| 6.4 | Check localStorage cleared | accessToken removed | [ ] | F12 > Application |
| 6.5 | Try accessing protected page | Redirected to login | [ ] | Type dashboard URL directly |
| 6.6 | Re-login successful | Dashboard accessible again | [ ] | |

---

## 5. Test Result Recording Template

### Test Execution Summary

| Date | Tester | Start Time | End Time | Duration |
|------|--------|------------|----------|----------|
| 2026-02-05 | | | | |

### Test Results by Scenario

| Test ID | Test Name | Total Steps | Passed | Failed | Blocked | Result |
|---------|-----------|-------------|--------|--------|---------|--------|
| UAT-01 | Authentication & Login | 8 | | | | |
| UAT-02 | Document Upload | 8 | | | | |
| UAT-03 | Document Processing | 6 | | | | |
| UAT-04 | Search Functionality | 12 | | | | |
| UAT-05 | Dashboard Features | 5 | | | | |
| UAT-06 | Logout & Session | 6 | | | | |
| **Total** | | **45** | | | | |

### Overall Pass Rate

```
Pass Rate = (Passed Steps / Total Steps) x 100
         = ( ___ / 45 ) x 100
         = ____ %
```

---

## 6. Issue Reporting Template

### Issue Template

```markdown
### Issue #___

**Test ID**: UAT-XX
**Step**: X.X
**Severity**: Critical / High / Medium / Low
**Status**: Open / In Progress / Resolved

**Summary**: [One-line description]

**Steps to Reproduce**:
1.
2.
3.

**Expected Result**:

**Actual Result**:

**Screenshot**: [Attach if applicable]

**Browser**: Chrome / Edge / Firefox
**Browser Version**:

**Notes**:

**Reported By**:
**Reported Date**: 2026-02-05
```

### Issue Severity Guide

| Severity | Description | Examples |
|----------|-------------|----------|
| **Critical** | System unusable, data loss | Login fails, data corruption |
| **High** | Major feature broken | Upload fails, search returns no results |
| **Medium** | Feature impaired but workaround exists | UI display issue, slow response |
| **Low** | Minor issue, cosmetic | Typo, alignment issue |

---

## 7. Quick Reference

### 7.1 Access URLs

| Service | URL | Notes |
|---------|-----|-------|
| **Frontend** | http://localhost | Main application |
| **API Gateway** | http://localhost:8080 | API endpoints |
| **Swagger UI** | http://localhost:8080/swagger-ui.html | API documentation |
| **AI Service Docs** | http://localhost:8000/docs | FastAPI docs |
| **Grafana** | http://localhost:3001 | Monitoring dashboards |
| **Kibana** | http://localhost:5601 | Log search |
| **Neo4j Browser** | http://localhost:7474 | Graph visualization |
| **MinIO Console** | http://localhost:9001 | Object storage |
| **Keycloak Admin** | http://localhost:8180/admin | Identity management |
| **Jaeger UI** | http://localhost:16686 | Distributed tracing |
| **Prometheus** | http://localhost:9090 | Metrics |

### 7.2 Health Check Commands

```bash
# All-in-one health check
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "^kp-"

# Individual service checks
curl -s http://localhost:8080/actuator/health | jq .status
curl -s http://localhost:8081/actuator/health | jq .status
curl -s http://localhost:8000/api/v1/health | jq .status
curl -s http://localhost:9200/_cluster/health | jq .status
```

### 7.3 Log Viewing Commands

```bash
# View specific service logs
docker logs -f kp-backend --tail=100
docker logs -f kp-api-gateway --tail=100
docker logs -f kp-ai-service --tail=100
docker logs -f kp-nginx --tail=100

# View all logs
docker-compose logs -f --tail=50
```

### 7.4 Service Restart Commands

```bash
cd /mnt/d/Users/KTDS/Documents/06.과제/hybrid-rag-knowledge-ops/infrastructure/docker

# Restart specific service
docker-compose restart kp-backend
docker-compose restart kp-ai-service

# Restart all services
docker-compose down && docker-compose up -d
```

---

## Appendix: Previous Test Results

### UAT History

| Date | Test | Result | Notes |
|------|------|--------|-------|
| 2026-02-04 | UAT-01 Authentication | PASS | Gateway JWT relay fixed |
| 2026-02-04 | UAT-02 Document Upload | PASS | MinIO storage implemented |
| 2026-02-05 | UAT-03 Document Processing | PENDING | Embedding pipeline status TBD |
| 2026-02-05 | UAT-04 Search Functionality | PENDING | Requires processed documents |

### Known Issues & Limitations

| ID | Description | Workaround | Status |
|----|-------------|------------|--------|
| 1 | Document processing (embedding) may require manual trigger | Check AI Service logs | TBD |
| 2 | Search results depend on indexed documents | Upload and wait for processing | Expected |
| 3 | Real-time updates may need page refresh | Manually refresh page | Expected |

---

*Document Created: 2026-02-05*
*Author: QA Agent*
*Environment: Development (Docker Compose)*
