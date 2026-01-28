# STORY-055: 보안 테스트 (XSS, SQL Injection, Auth)

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | (미정) |
| **Epic** | EPIC-004 |
| **Status** | To Do |
| **Priority** | High |
| **Story Points** | 3 |
| **Assignee** | QA |
| **Sprint** | 4 |

---

## User Story

**As a** QA 엔지니어,
**I want** XSS, SQL Injection, 인증 우회 등 보안 취약점을 검증하는 자동화 테스트를 작성,
**So that** 보안 취약점이 배포 전에 자동으로 감지되어 시스템 안전성을 보장할 수 있음.

---

## Acceptance Criteria

- [ ] **Given** 검색 입력 필드에 XSS 공격 벡터(`<script>alert(1)</script>`) 전송, **When** 서버 응답 수신, **Then** 스크립트가 실행되지 않고 새니타이징 처리됨
- [ ] **Given** 검색 쿼리에 SQL Injection 패턴(`' OR 1=1 --`) 전송, **When** 서버 처리, **Then** SQL 실행되지 않고 정상 에러 응답 반환
- [ ] **Given** SSE 스트리밍 엔드포인트에 인증 토큰 없이 요청, **When** 서버 수신, **Then** 401 Unauthorized 응답 반환
- [ ] **Given** 만료된 JWT 토큰으로 요청, **When** 서버 검증, **Then** 401 응답과 함께 token expired 메시지
- [ ] **Given** 보안 테스트 스위트 전체 실행, **When** CI 파이프라인, **Then** 모든 보안 테스트 통과

---

## Tasks

- [ ] XSS Injection 테스트 케이스 작성 (Stored XSS, Reflected XSS)
- [ ] SQL Injection 테스트 케이스 작성 (Classic, Blind, Time-based)
- [ ] NoSQL Injection 테스트 케이스 작성 (Elasticsearch query injection)
- [ ] SSE Auth Token 필수 검증 테스트 작성
- [ ] JWT 만료/변조/없음 케이스별 테스트 작성
- [ ] CORS 설정 검증 테스트 작성
- [ ] Rate Limiting 검증 테스트 (있는 경우)
- [ ] 보안 테스트 리포트 템플릿 작성
- [ ] CI 파이프라인에 보안 테스트 단계 추가

---

## 기술 노트

### 문제점 (Sprint 03 리뷰에서 도출)

Sprint 03에서 기능 테스트는 수행했으나 **보안 테스트가 전혀 없는 상태**:

1. **입력 새니타이징 미확인** - 검색 쿼리에 악성 스크립트 삽입 시 동작 미검증
2. **인증 경계 미테스트** - SSE 엔드포인트에 미인증 접근 시 동작 미확인
3. **Injection 방어 미검증** - SQL/NoSQL Injection 방어 여부 미확인

### 테스트 케이스 목록

```
XSS 테스트
├── Reflected XSS: <script>alert(1)</script>
├── Stored XSS: <img onerror="alert(1)" src=x>
├── DOM XSS: javascript:alert(1)
└── SVG XSS: <svg onload="alert(1)">

SQL Injection 테스트
├── Classic: ' OR 1=1 --
├── Union-based: ' UNION SELECT * FROM users --
├── Blind: ' AND 1=1 --
└── Time-based: ' AND SLEEP(5) --

Auth 테스트
├── No Token: 401 확인
├── Expired Token: 401 + expired 메시지
├── Malformed Token: 401 + invalid 메시지
├── Wrong Signature: 401 확인
└── Revoked Token: 401 확인 (있는 경우)
```

### 도구

- **pytest** + **requests** - 백엔드 보안 테스트
- **OWASP ZAP** (선택) - 자동 스캔
- **Custom scripts** - XSS/SQLi 페이로드 생성

### 영향 범위

- `tests/security/` - 신규 보안 테스트 디렉토리
- `tests/security/test_xss.py` - XSS 테스트
- `tests/security/test_injection.py` - Injection 테스트
- `tests/security/test_auth.py` - 인증 테스트
- `.github/workflows/ci.yml` - 보안 테스트 단계 추가

---

## 테스트 계획

- [ ] XSS Test: 5종 이상 공격 벡터 차단 확인
- [ ] SQLi Test: 4종 이상 패턴 방어 확인
- [ ] NoSQL Injection Test: Elasticsearch 쿼리 인젝션 방어
- [ ] Auth Test: 토큰 없음/만료/변조/잘못된 서명 거부
- [ ] CORS Test: 허용되지 않은 Origin 요청 거부
- [ ] Report: 보안 테스트 결과 리포트 생성

---

## 참고 자료

- Sprint 03 완료 리뷰에서 도출 - 보안 테스트 부재
- [STORY-053 보안 강화](./STORY-053-security-hardening.md) - 연관 Story
- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
