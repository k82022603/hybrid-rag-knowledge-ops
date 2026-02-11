# 장애 보고서: AI Service 기동 실패

**Incident ID**: INC-2026-02-02-001
**발생 일시**: 2026-02-02
**작성자**: Infra Engineer Agent
**심각도**: Medium (서비스 기동 불가)
**상태**: 조치 중 (In Progress)

---

## 1. 장애 요약

| 항목 | 내용 |
|------|------|
| **영향 서비스** | AI Service (kp-ai-service), Backend (kp-backend) |
| **영향 범위** | AI 기능 전체 (RAG 검색, 임베딩, LLM 응답) |
| **근본 원인** | Python 의존성 누락 (email-validator) |
| **복구 방법** | pyproject.toml 수정 후 컨테이너 재빌드 |

---

## 2. 장애 상세

### 2.1 Primary Failure: AI Service (kp-ai-service)

**증상**:
```
ImportError: email-validator is not installed, run `pip install pydantic[email]`
```

**발생 위치**:
- Pydantic 모델에서 `EmailStr` 타입 사용 시
- FastAPI 라우터 초기화 단계

**원인 분석**:
1. Pydantic v2에서 `EmailStr` 타입을 사용하려면 `email-validator` 패키지가 필요
2. `pyproject.toml`에 `pydantic`만 명시되어 있고 `email-validator`가 누락됨
3. 컨테이너 빌드 시 해당 패키지가 설치되지 않아 런타임 오류 발생

**영향**:
- AI Service 컨테이너 시작 실패
- FastAPI 애플리케이션 초기화 중단
- 모든 AI 관련 API 엔드포인트 접근 불가

### 2.2 Secondary Failure: Backend (kp-backend)

**증상**:
```
io.netty.resolver.dns.DnsResolveContext.finishResolve:
[/10.89.2.9:51820] Failed to resolve 'ai-service' after 2 queries
```

**발생 위치**:
- Spring Cloud Gateway의 AI Service 라우팅 설정
- Resilience4j Circuit Breaker 트리거

**원인 분석**:
1. AI Service 컨테이너가 정상 기동되지 않음
2. Docker 내부 DNS에서 'ai-service' 호스트명 해결 실패
3. Backend가 AI Service로 요청 라우팅 시 Connection Refused

**영향**:
- `/api/v1/ai/**` 경로 라우팅 실패
- Circuit Breaker OPEN 상태 전환
- Fallback 응답 또는 503 Service Unavailable

---

## 3. 타임라인

| 시간 | 이벤트 |
|------|--------|
| 2026-02-02 | AI Service 컨테이너 시작 시도 |
| 2026-02-02 | ImportError 발생으로 기동 실패 |
| 2026-02-02 | Backend에서 DNS 해결 실패 로그 확인 |
| 2026-02-02 | 근본 원인 분석 완료 |
| 2026-02-02 | pyproject.toml 수정 및 재빌드 시작 |

---

## 4. 조치 사항

### 4.1 즉시 조치 (Immediate Actions)

**pyproject.toml 수정**:
```toml
# Before
dependencies = [
    "pydantic>=2.0",
    ...
]

# After
dependencies = [
    "pydantic[email]>=2.0",  # email-validator 포함
    ...
]
```

**컨테이너 재빌드**:
```bash
cd infrastructure/docker
docker compose build ai-service --no-cache
docker compose up -d ai-service
```

### 4.2 검증 단계 (Verification)

```bash
# 1. AI Service 컨테이너 상태 확인
docker ps --filter "name=kp-ai-service" --format "table {{.Names}}\t{{.Status}}"

# 2. Health Check 확인
curl -s http://localhost:8000/health | jq

# 3. Backend DNS 해결 확인
docker exec kp-backend nslookup ai-service

# 4. API 엔드포인트 테스트
curl -s http://localhost:8080/api/v1/ai/health
```

### 4.3 예상 결과

- AI Service: `healthy` 상태로 전환
- Backend: Circuit Breaker `CLOSED` 상태로 복구
- API: 정상 응답 (200 OK)

---

## 5. 근본 원인 분석 (RCA)

### 5.1 왜 이 문제가 발생했는가?

```
Level 1: AI Service 시작 실패
    ↓ Why?
Level 2: ImportError - email-validator not installed
    ↓ Why?
Level 3: pydantic[email] 대신 pydantic만 설치됨
    ↓ Why?
Level 4: pyproject.toml에 optional dependency 미명시
    ↓ Why?
Level 5: EmailStr 사용 시 필요한 패키지 확인 누락
```

### 5.2 예방 조치 (Preventive Actions)

| 조치 | 담당 | 우선순위 |
|------|------|----------|
| 의존성 검증 테스트 추가 | QA | High |
| Dockerfile에 설치 검증 단계 추가 | DevOps | Medium |
| CI 파이프라인에 import 테스트 추가 | DevOps | Medium |
| 의존성 문서화 강화 | Doc | Low |

---

## 6. 영향도 평가

### 6.1 서비스 영향

| 기능 | 영향 | 비고 |
|------|------|------|
| 문서 검색 | X (불가) | AI Service 의존 |
| 문서 업로드 | X (불가) | 임베딩 생성 불가 |
| LLM 채팅 | X (불가) | DeepSeek 연동 불가 |
| 문서 목록 조회 | O (가능) | Backend 직접 처리 |
| 사용자 인증 | O (가능) | Keycloak 독립 |

### 6.2 사용자 영향

- 개발 환경: 개발팀 AI 기능 테스트 불가
- 스테이징 환경: 해당 없음 (미배포)
- 프로덕션 환경: 해당 없음 (미배포)

---

## 7. 관련 파일

| 파일 | 설명 |
|------|------|
| `knowledge_service/pyproject.toml` | Python 의존성 정의 |
| `infrastructure/docker/docker-compose.yml` | Docker Compose 설정 |
| `knowledge_service/src/app/api/routes/` | FastAPI 라우터 (EmailStr 사용) |

---

## 8. 교훈 (Lessons Learned)

### 8.1 기술적 교훈

1. **Pydantic v2 Optional Dependencies**: `EmailStr`, `HttpUrl` 등 특수 타입은 별도 패키지 필요
2. **Docker 빌드 검증**: 빌드 성공과 런타임 성공은 다름 - 앱 시작까지 검증 필요
3. **Cascading Failure**: 하나의 서비스 장애가 다른 서비스에 연쇄 영향

### 8.2 프로세스 교훈

1. **의존성 변경 시 빌드 테스트**: 새 타입/기능 사용 시 패키지 요구사항 확인
2. **Health Check 모니터링**: 컨테이너 시작 후 health 상태까지 확인
3. **로그 통합**: 여러 서비스의 로그를 통합 모니터링하여 연관 장애 파악

---

## 9. 후속 조치 (Follow-up Actions)

| 번호 | 조치 | 담당 | 기한 | 상태 |
|------|------|------|------|------|
| 1 | pyproject.toml 수정 및 커밋 | RAG Engineer | 2026-02-02 | 진행 중 |
| 2 | AI Service 재빌드 및 배포 | Infra | 2026-02-02 | 대기 |
| 3 | 의존성 import 테스트 추가 | QA | 2026-02-03 | 계획 |
| 4 | CI에 smoke test 추가 | DevOps | 2026-02-05 | 계획 |

---

## 10. 변경 이력

| 날짜 | 버전 | 변경 내용 |
|------|------|----------|
| 2026-02-02 | 1.0 | 초기 보고서 작성 |

---

**검토자**: Tech Lead
**승인자**: PM
