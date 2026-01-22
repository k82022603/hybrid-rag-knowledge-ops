# Backend 설계서 검토 결과

---

## 문서 정보

| 항목 | 내용 |
|------|------|
| **검토일** | 2026-01-22 |
| **검토자** | Backend Agent (Claude Opus 4.5) |
| **검토 대상** | backend_detailed_design.md, api_integration_design.md, authentication_authorization_detailed_design.md |
| **검토 범위** | 구현 가능성, 누락 내용, 불일치/모순, 개선 제안 |

---

## 1. 검토 요약

### 1.1 전체 평가

| 설계서 | 완성도 | 구현 가능성 | 비고 |
|--------|:------:|:----------:|------|
| backend_detailed_design.md | 95% | 높음 | SSE, Saga, Rate Limiting 포함 |
| api_integration_design.md | 92% | 높음 | Internal/External API 통합 |
| authentication_authorization.md | 93% | 높음 | Keycloak + PKCE 완비 |

### 1.2 종합 의견

세 문서 모두 **구현 가능한 수준의 상세한 설계**를 제공하고 있습니다. 특히:
- 코드 예시가 풍부하여 개발자가 즉시 참고 가능
- Mermaid 다이어그램으로 아키텍처/플로우 이해 용이
- 예외 처리, 에러 코드, 테스트 전략까지 포함

---

## 2. backend_detailed_design.md 검토

### 2.1 구현 가능성: 높음

**강점:**
- JPA Entity 설계가 상세하며 Index, Soft Delete, Auditing 포함
- Resilience4j 설정이 구체적 (Circuit Breaker, Retry, Rate Limiter)
- SSE 스트리밍 연동 설계 포함 (LangGraph 호환)
- 테스트 전략 (Unit, Integration, API Test) 예시 코드 제공

**구현 준비 완료 항목:**
- [x] Gradle 멀티모듈 구조
- [x] JPA Entity (Knowledge, User, Bookmark, ChatConversation)
- [x] Repository (JPQL, Criteria API, Custom)
- [x] Service Layer (트랜잭션, 이벤트 발행)
- [x] AI Service Client (WebClient + Resilience4j)
- [x] 예외 처리 (BusinessException 계층)

### 2.2 누락된 내용

| 항목 | 중요도 | 설명 |
|------|:------:|------|
| **파일 업로드 처리** | 중 | multipart/form-data 처리 로직 미상세 |
| **캐시 무효화 전략** | 중 | Redis 캐시 eviction 정책 미명시 |
| **벌크 작업 API** | 하 | 다중 삭제/상태 변경 API 미포함 |
| **검색 인덱스 동기화** | 중 | Knowledge 변경 시 ES 동기화 상세 로직 |

### 2.3 불일치/모순

| 위치 | 내용 | 권장 조치 |
|------|------|----------|
| 섹션 7.2 User Entity | `passwordHash` 필드 존재하나 OAuth만 사용 | OAuth 전용이면 필드 제거 또는 주석 보완 |
| 섹션 10.3 AI Client | `chunkId` 타입이 일부 UUID, 일부 String | UUID로 통일 (문서 v1.1에서 수정됨, 재확인 필요) |

### 2.4 개선 제안

1. **Connection Pool 모니터링 추가**
   - HikariCP 메트릭을 Prometheus로 노출
   ```yaml
   management:
     metrics:
       enable:
         hikaricp: true
   ```

2. **Retry 로직에 Jitter 추가**
   - 동시 재시도로 인한 thundering herd 방지
   ```yaml
   resilience4j:
     retry:
       instances:
         aiService:
           enableRandomizedWait: true
   ```

3. **API 버저닝 전략 명시**
   - URI 버저닝 (`/api/v1/`) 외에 Header 버저닝 지원 여부 결정

---

## 3. api_integration_design.md 검토

### 3.1 구현 가능성: 높음

**강점:**
- External/Internal API 명확한 분리
- Request/Response 예시가 상세함
- SSE 스트리밍 응답 형식 정의
- 에러 코드 체계화 (COM, KNW, USR, AUTH, AI)

**API 완성도:**
- [x] Auth API (OAuth2.0 + PKCE)
- [x] Knowledge CRUD API
- [x] Search API (Hybrid, Chat Streaming)
- [x] User API
- [x] Bookmark API
- [x] Dashboard API

### 3.2 누락된 내용

| 항목 | 중요도 | 설명 |
|------|:------:|------|
| **파일 다운로드 API** | 중 | `/api/v1/files/{fileId}` 상세 스펙 미정의 |
| **Batch Export API** | 하 | 대량 내보내기 시 비동기 처리 방식 |
| **Webhook 설계** | 하 | 외부 시스템 연동용 이벤트 통지 |
| **GraphQL 옵션** | 하 | REST 외 GraphQL 지원 여부 |

### 3.3 불일치/모순

| 위치 | 내용 | 권장 조치 |
|------|------|----------|
| 4.2.3 지식 등록 | Content-Type이 `multipart/form-data`이나 일부 필드가 JSON처럼 기술 | 명확히 구분 (form field vs JSON body) |
| 4.3.2 채팅 검색 | `history` 필드와 `conversationId` 둘 다 사용 | 서버 측에서 히스토리 관리 시 `history` 필드 불필요 가능 |

### 3.4 개선 제안

1. **Pagination 커서 기반 옵션 추가**
   - 대용량 데이터에서 offset 방식보다 효율적
   ```yaml
   Query Parameters:
     - cursor: string (optional) - 다음 페이지 커서
   ```

2. **API Rate Limit 헤더 명시**
   - 클라이언트가 남은 요청 수 확인 가능
   ```yaml
   Response Headers:
     X-RateLimit-Limit: 100
     X-RateLimit-Remaining: 95
     X-RateLimit-Reset: 1705200000
   ```

3. **Idempotency Key 지원**
   - POST 요청 중복 방지
   ```yaml
   Request Headers:
     X-Idempotency-Key: unique-request-id
   ```

---

## 4. authentication_authorization_detailed_design.md 검토

### 4.1 구현 가능성: 높음

**강점:**
- Keycloak 설정 상세 (Realm, Client, Role)
- JWT 토큰 구조와 클레임 명세
- Token Rotation, Blacklist 전략 포함
- 프론트엔드 PKCE 플로우 코드 예시

**보안 기능:**
- [x] PKCE (Authorization Code Flow)
- [x] Token Blacklist (Redis)
- [x] Refresh Token Rotation
- [x] RBAC (Role-Based Access Control)
- [x] Rate Limiting

### 4.2 누락된 내용

| 항목 | 중요도 | 설명 |
|------|:------:|------|
| **MFA (Multi-Factor Authentication)** | 중 | TOTP/SMS 인증 추가 방법 |
| **IP 기반 접근 제어** | 하 | 특정 IP 대역 차단/허용 |
| **로그인 이력 감사** | 중 | 로그인 실패/성공 이력 저장 |
| **비밀번호 정책 UI 가이드** | 하 | 프론트엔드 비밀번호 강도 표시 |

### 4.3 불일치/모순

| 위치 | 내용 | 권장 조치 |
|------|------|----------|
| 섹션 4.1.1 Access Token | `exp` 필드가 Unix timestamp인데 API 응답은 ISO 8601 | 문서 내 일관성 확인 (JWT 내부는 Unix, API 응답은 ISO 8601) |
| 섹션 5.1 vs 6.1 | User Service와 Gateway 둘 다 JWT 검증 | Gateway에서만 검증 권장 (중복 제거) |

### 4.4 개선 제안

1. **세션 동시 접속 제한**
   - 동일 계정 다중 디바이스 로그인 제어
   ```yaml
   Keycloak Realm Settings:
     ssoSessionMaxCount: 3  # 최대 3개 세션
   ```

2. **API Key 인증 옵션**
   - 서비스 계정 또는 외부 시스템용
   ```yaml
   X-Api-Key: service-account-key
   ```

3. **CORS 설정 동적화**
   - 환경별 허용 도메인 관리
   ```yaml
   cors:
     allowed-origins: ${CORS_ALLOWED_ORIGINS:http://localhost:5173}
   ```

---

## 5. 문서 간 일관성 검토

### 5.1 정합성 확인 결과

| 항목 | backend_detailed | api_integration | auth_detailed | 상태 |
|------|:----------------:|:---------------:|:-------------:|:----:|
| UUID ID 타입 | O | O | O | 일치 |
| ISO 8601 Timestamp | O | O | O (API) | 일치 |
| 에러 코드 체계 | O | O | O | 일치 |
| Rate Limiting | O | O | O | 일치 |
| Resilience4j | O | O (언급) | - | 일치 |

### 5.2 불일치 사항

1. **UserRole Enum**
   - backend_detailed: `ADMIN, USER, VIEWER`
   - auth_detailed: `USER, KNOWLEDGE_MANAGER, ADMIN`
   - **권장**: auth_detailed 기준으로 통일 (계층적 역할)

2. **API 경로**
   - backend_detailed: `/api/v1/chat/stream`
   - api_integration: `/api/v1/search/chat`
   - **권장**: api_integration 기준으로 통일 (Search 도메인 하위)

---

## 6. 구현 우선순위 제안

### Phase 1: 핵심 기능 (Week 1-2)

| 순서 | 항목 | 근거 |
|:----:|------|------|
| 1 | JPA Entity + Repository | 데이터 계층 기반 |
| 2 | Knowledge CRUD Service | 핵심 비즈니스 로직 |
| 3 | Spring Security + JWT | 모든 API의 전제 조건 |
| 4 | AI Service Client (WebClient) | 검색 기능 의존 |

### Phase 2: 검색/채팅 (Week 3-4)

| 순서 | 항목 | 근거 |
|:----:|------|------|
| 5 | Search API (Hybrid) | 주요 사용자 기능 |
| 6 | Chat API (SSE Streaming) | 대화형 검색 |
| 7 | Resilience4j 적용 | 안정성 확보 |

### Phase 3: 부가 기능 (Week 5-6)

| 순서 | 항목 | 근거 |
|:----:|------|------|
| 8 | Bookmark API | 사용자 편의 |
| 9 | Dashboard API | 통계/모니터링 |
| 10 | 캐싱 (Redis) | 성능 최적화 |

---

## 7. 결론

### 7.1 검토 결과 요약

| 구분 | 결과 |
|------|------|
| **구현 가능성** | 높음 - 코드 예시 풍부, 즉시 개발 착수 가능 |
| **누락 사항** | 경미 - 파일 업로드, 캐시 무효화 등 보완 필요 |
| **불일치 사항** | 경미 - UserRole, API 경로 통일 필요 |
| **문서 간 정합성** | 양호 - 대부분 일관성 유지 |

### 7.2 권장 조치

1. **즉시 조치 (Blocking)**
   - UserRole Enum 통일 (auth_detailed 기준)
   - API 경로 통일 (api_integration 기준)

2. **개발 중 보완**
   - 파일 업로드 처리 상세화
   - 캐시 무효화 전략 추가

3. **후속 검토**
   - 성능 테스트 결과 반영
   - 운영 환경 설정 검증

---

## 8. 부록

### 8.1 검토 시 참고한 문서

- [상세 설계서](../hybrid_rag_platform_detailed_design.md)
- [에러 코드 표준](../error_code_standards.md)
- [인프라 설계서](../infrastructure_detailed_design.md)
- [Observability 설계서](../observability_detailed_design.md)

### 8.2 검토 이력

| 버전 | 일자 | 검토자 | 내용 |
|------|------|--------|------|
| 1.0 | 2026-01-22 | Backend Agent | 초기 검토 |

---

*이 문서는 Backend Agent에 의해 자동 생성되었습니다.*
