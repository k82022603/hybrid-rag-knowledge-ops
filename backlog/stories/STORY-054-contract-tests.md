# STORY-054: 서비스 간 통합 테스트 (Contract Test)

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-44 |
| **Epic** | EPIC-004 |
| **Status** | In Progress |
| **Priority** | High |
| **Story Points** | 5 |
| **Assignee** | QA |
| **Sprint** | 4 |

---

## User Story

**As a** QA 엔지니어,
**I want** Backend, AI Service, Knowledge Service 간 API 계약을 검증하는 Contract Test를 작성,
**So that** 서비스 간 인터페이스 변경 시 호환성 깨짐을 조기에 감지할 수 있음.

---

## Acceptance Criteria

- [ ] **Given** Backend -> AI Service 검색 API 호출 시, **When** 요청/응답 스키마가 계약과 다름, **Then** 테스트 실패 및 위반 내역 리포트
- [ ] **Given** AI Service -> Knowledge Service Retriever API 호출 시, **When** 요청/응답 스키마가 계약과 다름, **Then** 테스트 실패 및 위반 내역 리포트
- [ ] **Given** SSE 이벤트 스트림, **When** 이벤트 포맷이 계약(type, content, sources, done)과 다름, **Then** 테스트 실패
- [ ] **Given** CI 파이프라인 실행, **When** Contract Test 단계, **Then** 3개 서비스 간 계약 테스트가 자동 실행
- [ ] **Given** 계약 위반 감지, **When** CI 파이프라인 실행, **Then** 빌드 실패 및 위반 상세 정보 출력

---

## Tasks

- [ ] Backend -> AI Service 계약 정의 (OpenAPI 또는 Pact)
- [ ] AI Service -> Knowledge Service 계약 정의
- [ ] SSE 이벤트 포맷 계약 정의 (이벤트 타입, 필드)
- [ ] Consumer-side Contract Test 작성 (Backend가 AI Service 호출)
- [ ] Provider-side Contract Test 작성 (AI Service가 계약 충족 확인)
- [ ] Knowledge Service Provider 검증 테스트 작성
- [ ] SSE 이벤트 포맷 검증 테스트 작성
- [ ] CI 파이프라인에 Contract Test 단계 추가
- [ ] 계약 위반 시 Slack 알림 설정

---

## 기술 노트

### 문제점 (Sprint 03 리뷰에서 도출)

Sprint 03에서 3개 서비스(Backend, AI Service, Knowledge Service)를 독립적으로 개발했으나:

1. **서비스 간 인터페이스 불일치** - Backend가 기대하는 AI Service 응답 형식과 실제 응답이 다름
2. **SSE 이벤트 포맷 비표준화** - Frontend가 기대하는 이벤트 구조와 Backend가 전송하는 구조가 다를 수 있음
3. **통합 시점에서만 문제 발견** - 개별 서비스 테스트는 통과하지만 통합 시 실패

### 계약 테스트 전략

```
┌──────────────┐    계약     ┌──────────────┐    계약     ┌──────────────┐
│   Backend    │ ◄────────► │  AI Service  │ ◄────────► │  Knowledge   │
│  (Consumer)  │            │ (Provider/   │            │   Service    │
│              │            │  Consumer)   │            │  (Provider)  │
└──────────────┘            └──────────────┘            └──────────────┘
       │
       │ SSE 계약
       ▼
┌──────────────┐
│   Frontend   │
│  (Consumer)  │
└──────────────┘
```

### 계약 정의 예시

```json
// Backend -> AI Service 계약
{
  "request": {
    "method": "POST",
    "path": "/api/v1/search",
    "body": {
      "query": "string (required)",
      "top_k": "integer (optional, default: 5)",
      "conversation_history": "array (optional)"
    }
  },
  "response": {
    "status": 200,
    "body": {
      "answer": "string (required)",
      "sources": "array<Source> (required)",
      "metadata": "object (optional)"
    }
  }
}
```

### 도구 선택

- **Pact** (권장) - Consumer-Driven Contract Testing
- **또는** OpenAPI Schema Validation + JSON Schema 검증
- CI 통합: GitHub Actions에 Contract Test job 추가

### 영향 범위

- `tests/contract/` - 신규 Contract Test 디렉토리
- `.github/workflows/ci.yml` - Contract Test 단계 추가
- `docs/contracts/` - 계약 정의 문서

---

## 테스트 계획

- [ ] Contract Test: Backend -> AI Service 요청/응답 스키마 검증
- [ ] Contract Test: AI Service -> Knowledge Service 요청/응답 스키마 검증
- [ ] Contract Test: SSE 이벤트 포맷 (token, sources, done) 검증
- [ ] CI Test: 파이프라인에서 Contract Test 자동 실행 확인
- [ ] Regression Test: 의도적 계약 위반 시 빌드 실패 확인

---

## 참고 자료

- Sprint 03 완료 리뷰에서 도출 - 서비스 간 인터페이스 불일치 문제
- [API 통합 설계서](../../knowledge_service/docs/02_design/api_integration_design.md)
- [Pact Contract Testing](https://docs.pact.io/)
