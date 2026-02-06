# Session Log - 2026-02-06

**Session ID**: session-2026-02-06-uat-scenario
**시작 시간**: 16:00 KST
**종료 시간**: 진행 중
**모델**: Claude Opus 4.6 (claude-opus-4-6)
**Sprint**: Sprint 07

---

## 세션 요약

이전 세션(session_gateway_routing_uat)에서 식별된 Gateway 라우팅 블로커를 모두 해결하고, 전체 서비스 검증을 PASS한 뒤, UAT(사용자 수용 테스트) 시나리오 재설계에 착수한 세션. Gateway Documents 라우팅 추가, Keycloak issuer-uri 불일치 수정, 볼륨 마운트 적용 등 인프라 안정화 작업을 완료하고, UI 기반 브라우저 테스트와 대량 파일 처리 테스트 시나리오를 설계 중.

---

## 이전 세션에서 완료된 작업 (이월 결과)

### 1. Gateway `/api/v1/documents/**` -> AI Service 라우팅 추가

#### 상세 내용
- 이전 세션에서 식별된 블로커: `/api/v1/documents/**` 요청이 Backend catch-all에 걸림
- Gateway `application.yml`에 AI Service 전용 라우팅 규칙 추가
- 라우팅 우선순위 조정으로 기존 API 경로 보호

**결과**: Documents API가 Gateway를 경유하여 AI Service로 정상 전달 (200 OK)

### 2. Keycloak issuer-uri 불일치 수정

#### 상세 내용
- 문제: Docker 내부 URL과 외부 URL이 달라 JWT 검증 실패
- Docker 내부 네트워크에서의 Keycloak 접근 URL과 브라우저에서의 외부 URL 분리 설정
- `spring.security.oauth2.resourceserver.jwt.issuer-uri` 설정 수정

**결과**: Keycloak SSO 인증 정상 작동 (admin/admin123 로그인 확인)

### 3. Gateway application.yml 볼륨 마운트

#### 상세 내용
- Gateway 컨테이너에 `application.yml` 볼륨 마운트 추가
- 빌드 없이 설정 변경 사항을 즉시 적용 가능하도록 구성
- `docker-compose.yml`에 볼륨 마운트 항목 추가

**결과**: Gateway 설정 변경 시 컨테이너 재빌드 불필요

### 4. 전체 서비스 검증 PASS

#### 상세 내용

| 서비스 | 검증 항목 | 결과 |
|--------|----------|------|
| Frontend | React UI 접근 | 200 OK |
| Gateway | Spring Cloud Gateway 라우팅 | 200 OK |
| Keycloak | SSO 로그인 (admin/admin123) | 200 OK |
| Documents API | Gateway 경유 문서 API | 200 OK |
| AI Service | FastAPI 헬스체크 | 200 OK |
| Backend | SpringBoot API | 200 OK |

**결과**: 전체 18개 컨테이너 healthy, 모든 서비스 정상 응답

---

## 현재 진행 중인 작업

### 5. UAT 테스트 시나리오 재설계

#### 5-1. UI 기반 브라우저 테스트 시나리오

기존 UAT 체크리스트를 기반으로 실제 브라우저 환경에서 수행할 수동 테스트 시나리오 재설계 중.

| # | 시나리오 | 테스트 내용 | 상태 |
|---|---------|-----------|------|
| TC-01 | Keycloak SSO 로그인 | 브라우저에서 React UI 접근 -> Keycloak 리다이렉트 -> admin/admin123 로그인 -> 토큰 발급 확인 | 설계 중 |
| TC-02 | 문서 업로드 (단건) | 로그인 후 UI에서 단일 문서 업로드 -> 파일 전송 -> 처리 상태 확인 | 설계 중 |
| TC-03 | 문서 업로드 (다건) | 대량 파일 업로드 -> 청킹 + 임베딩 파이프라인 트리거 확인 | 설계 중 |
| TC-04 | 문서 검색 (키워드) | 검색 UI에서 키워드 입력 -> 검색 결과 반환 확인 | 설계 중 |
| TC-05 | 문서 검색 (하이브리드) | Vector + Graph + Keyword 통합 검색 결과 확인 | 설계 중 |
| TC-06 | SSE 실시간 상태 | 문서 처리 중 SSE 스트리밍으로 실시간 상태 업데이트 확인 | 설계 중 |

#### 5-2. 대량 파일 청킹 + 임베딩 + Retriever 테스트

터미널 기반으로 대량 파일 처리 파이프라인을 직접 검증하는 시나리오 설계 중.

| # | 테스트 항목 | 검증 내용 |
|---|-----------|----------|
| LT-01 | 대량 파일 업로드 | 10+ 파일 동시 업로드 시 큐 처리 확인 |
| LT-02 | 청킹 파이프라인 | 문서 파싱 -> 청크 분할 -> ES 인덱싱 정상 여부 |
| LT-03 | 임베딩 생성 | BGE-M3 임베딩 벡터 생성 및 ES 저장 확인 |
| LT-04 | Retriever 성능 | Hybrid Search (Vector + Keyword + Graph) 응답 시간 및 정확도 |
| LT-05 | 실패 문서 재시도 | 처리 실패 문서의 자동 재시도 메커니즘 검증 |

---

## 시스템 상태

### Docker 컨테이너 (18개 전체 healthy)

| 항목 | 상태 |
|------|------|
| 컨테이너 수 | 18개 |
| 전체 상태 | healthy |
| AI Service | healthy (deepseek, es, neo4j, postgresql 모두 정상) |
| Gateway | healthy (라우팅 규칙 업데이트 적용) |
| Keycloak | healthy (SSO 인증 정상) |

### 서비스 엔드포인트 확인

| 서비스 | URL | 상태 |
|--------|-----|------|
| Frontend (React) | http://localhost:3000 | 200 OK |
| Gateway | http://localhost:8080 | 200 OK |
| Keycloak | http://localhost:9090 | 200 OK |
| AI Service (직접) | http://localhost:8000 | 200 OK |
| Documents API (Gateway 경유) | http://localhost:8080/api/v1/documents | 200 OK |

### Elasticsearch 인덱스

| 항목 | 값 |
|------|-----|
| knowledge_chunks | 18 chunks |
| Keyword Search | 10건, 39ms |
| Hybrid Search | Vector 10 + Keyword 10 -> Fused 5, 837ms |

---

## 변경된 파일 목록

이전 세션에서 변경되어 현재 미커밋 상태인 파일:

```
infrastructure/docker/
├── docker-compose.yml                    # Gateway 볼륨 마운트 추가

backend/gateway/src/main/resources/
└── application.yml                       # Documents 라우팅 추가, issuer-uri 수정
```

---

## 주요 결정사항

| 결정 | 내용 | 근거 |
|------|------|------|
| UAT 시나리오 재설계 | 기존 45 스텝 체크리스트를 UI 기반 + 터미널 기반으로 분리 | 브라우저 테스트와 파이프라인 성능 테스트의 관심사 분리 |
| Keycloak SSO 경유 테스트 | AI Service 자체 인증 대신 Keycloak SSO로 통합 | Gateway 라우팅 구조에 맞춤, 실제 운영 환경과 동일 |
| 대량 파일 테스트 추가 | 10+ 파일 동시 업로드 시나리오 포함 | P2 Phase 4에서 구현된 SSE + 재시도 기능 검증 필요 |

---

## 리스크 모니터링

| 리스크 | 확률 | 영향 | 상태 | 대응 |
|--------|------|------|------|------|
| 대량 파일 업로드 시 메모리 부족 | Med | High | Open | AI Service 컨테이너 메모리 제한 모니터링 |
| SSE 연결 타임아웃 | Low | Med | Open | 장시간 처리 시 reconnect 메커니즘 확인 |
| Keycloak 토큰 만료 시 UI 처리 | Med | Med | Open | refresh token 플로우 확인 필요 |
| 대량 청킹 시 ES 인덱싱 지연 | Med | Med | Open | bulk indexing 배치 크기 튜닝 |

---

## 커밋 히스토리 (최근)

```
b85b253 [FIX] 검증 단계에서 발견된 버그 3건 수정 + 테스트 942건 전체 통과
4932f10 [FEAT] P2 Phase 4: SSE 실시간 상태 스트리밍 + 실패 문서 재시도
514a53d [FIX] P1 Phase 3: ES 필드명 수정 + 업로드 후 처리 상태 UI
177990b [FEAT] P0 Phase 2: 파일 업로드 후 자동 처리 파이프라인 트리거 (TASK-02)
6728a4b [FEAT] P0 Phase 1: SearchService 클라이언트 연결, PostgreSQL 문서 저장소, 백그라운드 워커 활성화
```

---

## 이전 세션과의 연속성

```
[세션 1] opus46_update_check (10:30-10:41)
    └── Opus 4.6 전환 확인

[세션 2] session_gateway_routing_uat (11:00~)
    ├── Agent Teams 설정 완료
    ├── docker-compose.yml 커밋
    ├── UAT 블로커 2건 식별
    │   ├── Gateway Documents 라우팅 누락
    │   └── Keycloak issuer-uri 불일치
    └── 다음 작업: 블로커 해결 → UAT 실행

[세션 3] session_uat_scenario_design (16:00~)  ← 현재
    ├── 블로커 2건 모두 해결 완료
    ├── 전체 서비스 검증 PASS
    └── UAT 시나리오 재설계 진행 중
```

---

## 다음 작업 (Action Items)

### P0 (Critical)
1. UAT 시나리오 재설계 완료 (UI 기반 + 터미널 기반)
2. Keycloak SSO 브라우저 로그인 E2E 테스트 실행

### P1 (High)
3. 대량 파일 업로드 + 청킹 + 임베딩 파이프라인 테스트
4. SSE 실시간 상태 스트리밍 검증
5. 실패 문서 재시도 메커니즘 검증

### P2 (Medium)
6. Hybrid Search 성능 벤치마크 (응답 시간, 정확도)
7. 변경된 파일 (application.yml, docker-compose.yml) 커밋

---

## 사용된 도구 및 에이전트

| 도구/에이전트 | 용도 |
|--------------|------|
| Bash | Docker 상태 확인, curl 테스트, Slack 알림 |
| Read/Edit | Gateway application.yml 수정, docker-compose.yml 수정 |
| Slack (send_slack.sh) | 작업 시작/완료 알림 |

---

## 세션 통계

| 항목 | 값 |
|------|-----|
| 이전 세션 이월 블로커 해결 | 2건 (Documents 라우팅, issuer-uri) |
| 서비스 검증 PASS | 6개 서비스 (Frontend, Gateway, Keycloak, Documents API, AI Service, Backend) |
| UAT 시나리오 설계 중 | UI 6개 + 터미널 5개 = 총 11개 시나리오 |
| 변경된 파일 | 2개 (application.yml, docker-compose.yml) |

---

*작성: Claude Code (Documenter Agent, Opus 4.6)*
*작성일: 2026-02-06 16:00 KST*
