# STORY-010: Docker Compose 환경 구성

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-10 |
| **Epic** | EPIC-000 Infrastructure |
| **Status** | To Do |
| **Priority** | Critical |
| **Story Points** | 5 |
| **Assignee** | DevOps |
| **Sprint** | 1 |

---

## 사용자 스토리

**As a** 개발자
**I want** 단일 명령어로 전체 개발 환경을 기동할 수 있기를
**So that** 로컬에서 통합 테스트를 수행할 수 있다

---

## Acceptance Criteria

### AC1: Docker Compose 파일 구성
```gherkin
Given Docker Compose 파일이 작성되어 있을 때
When `docker-compose up -d` 명령어를 실행하면
Then 18개 컨테이너가 정상적으로 시작된다
And 모든 컨테이너가 healthy 상태가 된다
```

### AC2: 네트워크 및 볼륨 설정
```gherkin
Given Docker Compose가 실행 중일 때
When 컨테이너 간 통신을 시도하면
Then hybrid-rag-network를 통해 서비스명으로 접근 가능하다
And 데이터 볼륨이 영구 저장된다
```

### AC3: 환경 변수 템플릿
```gherkin
Given .env.example 파일이 존재할 때
When 개발자가 .env 파일을 생성하면
Then 모든 필요한 환경 변수가 문서화되어 있다
And 기본값 또는 예시가 제공된다
```

---

## 기술 명세

### 파일 구조
```
infrastructure/
├── docker-compose.yml           # 메인 설정
├── docker-compose.override.yml  # 로컬 개발용 오버라이드
├── .env.example                 # 환경 변수 템플릿
├── nginx/
│   └── nginx.conf
├── init-db/
│   └── 01-init.sql
└── prometheus/
    └── prometheus.yml
```

### 레이어별 구성
| Layer | 서비스 | 의존성 |
|-------|--------|--------|
| Application | nginx, frontend, api-gateway, backend, ai-service | Data, Auth |
| Auth | keycloak | postgresql |
| Data | postgresql, elasticsearch, neo4j, redis, minio | - |
| Observability | prometheus, grafana, loki, promtail, jaeger | - |

---

## 작업 분해

- [ ] docker-compose.yml 작성 (Application Layer)
- [ ] docker-compose.yml 작성 (Data Layer)
- [ ] docker-compose.yml 작성 (Auth Layer)
- [ ] docker-compose.yml 작성 (Observability Layer)
- [ ] 네트워크 및 볼륨 설정
- [ ] .env.example 작성
- [ ] nginx.conf 작성
- [ ] Health check 설정
- [ ] 기동 테스트

---

## 참고 자료

- [스프린트 실행 계획서 - Docker Compose 구성](../../docs/02_스프린트_실행_계획서.md#13-docker-compose-구성)
