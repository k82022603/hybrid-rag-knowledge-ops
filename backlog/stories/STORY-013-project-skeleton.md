# STORY-013: 프로젝트 골격 생성

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-13 |
| **Epic** | EPIC-000 Infrastructure |
| **Status** | To Do |
| **Priority** | High |
| **Story Points** | 5 |
| **Assignee** | Backend, Frontend, MLRag |
| **Sprint** | 1 |

---

## 사용자 스토리

**As a** 개발자
**I want** 각 서비스의 프로젝트 골격이 미리 준비되어 있기를
**So that** 즉시 기능 개발을 시작할 수 있다

---

## Acceptance Criteria

### AC1: Backend 프로젝트 (SpringBoot)
```gherkin
Given Backend 프로젝트 디렉토리가 준비되면
When 빌드 명령어를 실행하면
Then Gradle 빌드가 성공한다
And Health Check API가 응답한다
```

### AC2: AI Service 프로젝트 (FastAPI)
```gherkin
Given AI Service 프로젝트가 준비되면
When Poetry install 후 실행하면
Then FastAPI 서버가 정상 기동된다
And /health 엔드포인트가 응답한다
```

### AC3: Frontend 프로젝트 (React + Vite)
```gherkin
Given Frontend 프로젝트가 준비되면
When npm install && npm run dev 실행하면
Then Vite 개발 서버가 시작된다
And 브라우저에서 접속 가능하다
```

### AC4: API Gateway 프로젝트
```gherkin
Given API Gateway 프로젝트가 준비되면
When Gradle 빌드 후 실행하면
Then Spring Cloud Gateway가 기동된다
And 라우팅 설정이 적용된다
```

---

## 기술 명세

### 프로젝트 구조

```
hybrid-rag-knowledge-ops/
├── backend/
│   ├── api-gateway/           # Spring Cloud Gateway
│   │   ├── build.gradle.kts
│   │   └── src/main/...
│   └── backend-service/       # Main Backend
│       ├── build.gradle.kts
│       └── src/main/...
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
├── ai-service/                # FastAPI + LangGraph
│   ├── pyproject.toml
│   └── src/app/
└── knowledge_service/         # 기존 Python 서비스 (마이그레이션 예정)
```

### 기술 스택

| 서비스 | 프레임워크 | 버전 |
|--------|-----------|------|
| Backend | Spring Boot | 3.2.x |
| API Gateway | Spring Cloud Gateway | 4.x |
| Frontend | React + Vite | 18.x + 5.x |
| AI Service | FastAPI + LangGraph | 0.109+ |

### 공통 설정

| 항목 | 설정 |
|------|------|
| 린터 (Java) | Checkstyle, SpotBugs |
| 린터 (Python) | ruff, black |
| 린터 (TS) | ESLint + Prettier |
| 테스트 (Java) | JUnit 5, Mockito |
| 테스트 (Python) | pytest, pytest-cov |
| 테스트 (TS) | Vitest |

---

## 작업 분해

- [ ] Backend (SpringBoot) 프로젝트 초기화
- [ ] API Gateway 프로젝트 초기화
- [ ] Frontend (React + Vite) 프로젝트 초기화
- [ ] AI Service (FastAPI) 프로젝트 초기화
- [ ] 공통 설정 (린터, 포맷터)
- [ ] Docker 빌드 스크립트
- [ ] Health Check API 구현
- [ ] 기동 테스트

---

## 참고 자료

- [스프린트 실행 계획서 - 프로젝트 골격](../../docs/02_스프린트_실행_계획서.md#14-프로젝트-골격-생성)
- [백엔드 상세 설계서](../../knowledge_service/docs/02_design/backend_detailed_design.md)
- [프론트엔드 상세 설계서](../../knowledge_service/docs/02_design/frontend_detailed_design.md)
