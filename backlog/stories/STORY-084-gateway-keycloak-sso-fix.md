# STORY-084: Gateway Keycloak SSO Routing Fix

## Story Information

| Item | Value |
|------|-------|
| **ID** | STORY-084 |
| **Jira** | SCRUM-80 |
| **Epic** | EPIC-000 Infrastructure |
| **Sprint** | Sprint 08 |
| **Points** | 3 |
| **Priority** | P0 - Critical |
| **Assignee** | Backend |
| **Status** | Done |

---

## Background

After Sprint 07's deployment preparation, the API Gateway was not properly routing Keycloak SSO authentication requests. Users could not log in through the gateway endpoint, though direct Keycloak access worked fine.

---

## User Story

**As a** platform user,
**I want** SSO login to work seamlessly through the API Gateway,
**So that** I can access the platform with a single login experience.

---

## Acceptance Criteria

- [x] **Given** a user at the login page, **When** clicking SSO login, **Then** request is routed through Gateway to Keycloak
- [x] **Given** successful Keycloak authentication, **When** token is issued, **Then** Gateway properly relays the token
- [x] **Given** an authenticated session, **When** accessing protected resources, **Then** Gateway validates the token correctly
- [x] **Given** direct Keycloak access, **When** testing existing flow, **Then** no regression observed

---

## Technical Details

### Root Cause
Gateway `application.yml` had incorrect route predicates for Keycloak SSO endpoints. The `/api/v1/auth/**` pattern was not matching the actual Keycloak OAuth2 flow endpoints.

### Fix Applied
- Updated route predicates in `gateway/src/main/resources/application.yml`
- Configured proper path filters for Keycloak realm endpoints
- Enabled token relay filter for SSO flow
- Added CORS configuration for SSO redirect URIs

### Files Changed
| File | Change |
|------|--------|
| `gateway/src/main/resources/application.yml` | Route predicates and filters updated |

---

## Completion Date

2026-02-06

---

## References

- [Backend Detailed Design](../../knowledge_service/docs/02_design/06_backend_detailed_design.md)
- [Authentication Design](../../knowledge_service/docs/02_design/03_authentication_authorization_detailed_design.md)
