# STORY-012: 인증 인프라 (Keycloak)

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-12 |
| **Epic** | EPIC-000 Infrastructure |
| **Status** | Done |
| **Priority** | High |
| **Story Points** | 5 |
| **Assignee** | Backend, DevOps |
| **Sprint** | 1 |

---

## 사용자 스토리

**As a** 개발자
**I want** OAuth 2.0 기반 인증 시스템이 설정되어 있기를
**So that** 보안이 적용된 API를 개발할 수 있다

---

## Acceptance Criteria

### AC1: Keycloak Realm 설정
```gherkin
Given Keycloak 컨테이너가 시작되면
When 관리자 콘솔에 접속하면
Then hybrid-rag-realm이 생성되어 있다
And OAuth 2.0 클라이언트가 설정되어 있다
```

### AC2: 사용자 역할 정의
```gherkin
Given Realm이 설정되어 있을 때
When 사용자 역할을 확인하면
Then ADMIN, MEMBER, VIEWER 역할이 존재한다
And 각 역할에 적절한 권한이 할당되어 있다
```

### AC3: 테스트 사용자
```gherkin
Given 역할이 설정되어 있을 때
When 초기 사용자가 생성되면
Then admin@example.com (ADMIN) 계정이 존재한다
And 로그인 및 토큰 발급이 가능하다
```

---

## 기술 명세

### Realm 설정
```json
{
  "realm": "hybrid-rag-realm",
  "enabled": true,
  "sslRequired": "external",
  "registrationAllowed": false,
  "loginWithEmailAllowed": true,
  "duplicateEmailsAllowed": false,
  "resetPasswordAllowed": true,
  "editUsernameAllowed": false,
  "bruteForceProtected": true
}
```

### Client 설정
| 항목 | 값 |
|------|-----|
| Client ID | hybrid-rag-client |
| Client Protocol | openid-connect |
| Access Type | confidential |
| Valid Redirect URIs | http://localhost:3000/*, http://localhost:8080/* |
| Web Origins | http://localhost:3000, http://localhost:8080 |

### 역할 정의
| 역할 | 권한 |
|------|------|
| ADMIN | 전체 관리 (사용자, 지식, 시스템) |
| MEMBER | 지식 CRUD, 검색 |
| VIEWER | 검색, 조회만 |

---

## 작업 분해

- [ ] Realm JSON 설정 파일 작성
- [ ] Client 설정
- [ ] 역할 정의
- [ ] 초기 사용자 생성 스크립트
- [ ] Keycloak 자동 import 설정
- [ ] 토큰 발급 테스트

---

## 참고 자료

- [인증/인가 설계서](../../knowledge_service/docs/02_design/03_authentication_authorization_detailed_design.md)
- [Keycloak 공식 문서](https://www.keycloak.org/documentation)
