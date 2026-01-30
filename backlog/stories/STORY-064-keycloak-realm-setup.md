# STORY-064: Keycloak Realm 설정 (Docker E2E 100%)

## Story 정보

| 항목 | 값 |
|------|-----|
| **ID** | STORY-064 |
| **Jira** | SCRUM-64 |
| **Epic** | EPIC-000 Infrastructure |
| **Sprint** | Sprint 05 |
| **Points** | 3 |
| **Priority** | P0 - Critical |
| **Assignee** | Infra |
| **Status** | Done |

---

## 배경

Sprint 04 Day 5 Docker E2E 테스트에서 17건 실패 (82.7%)가 발생했습니다.
모든 실패는 **401 Unauthorized** 오류로, Keycloak realm이 Docker 환경에서 
자동 설정되지 않아 발생한 문제입니다.

Mock 모드에서는 인증을 모킹하여 100% 통과하지만, 실제 Docker 환경에서는
Keycloak이 `knowledge-platform` realm을 가지고 있지 않아 인증이 실패합니다.

---

## 목표

Docker 환경에서 Keycloak realm을 자동 설정하여 E2E 테스트 100% 통과

---

## Acceptance Criteria

- [x] `hybrid-rag` realm이 컨테이너 시작 시 자동 생성됨 (환경변수 통일)
- [x] 테스트 사용자 계정 (test-user/test-password, testuser/testpass 등) 자동 등록
- [x] realm-export.json 파일 작성 및 버전 관리
- [x] Docker Compose에서 realm import 설정 추가
- [x] Docker E2E 테스트 26/26 (100%) 통과 ✅
- [x] 기존 Mock 모드 테스트 회귀 없음 ✅

### 2026-01-30 작업 내역

**수정된 파일**:
| 파일 | 변경 내용 |
|------|----------|
| `frontend/.env` | realm: `hybrid-rag`, client: `knowledge-frontend` |
| `frontend/.env.development` | realm: `hybrid-rag`, client: `knowledge-frontend` |
| `frontend/.env.example` | realm: `hybrid-rag`, client: `knowledge-frontend` |
| `frontend/src/auth/keycloak.ts` | 기본값 `hybrid-rag` realm으로 변경 |
| `docker-compose.yml` | Frontend Keycloak 환경변수 추가 |

**생성된 문서**:
- `infrastructure/docker/keycloak/README.md` - Keycloak 설정 가이드
- `knowledge_service/docs/07_maintenance/keycloak_admin_guide.md` - 관리자 가이드

---

## 기술 요구사항

### 1. realm-export.json 생성

```json
{
  "realm": "knowledge-platform",
  "enabled": true,
  "users": [
    {
      "username": "testuser",
      "enabled": true,
      "credentials": [
        {
          "type": "password",
          "value": "password"
        }
      ],
      "realmRoles": ["user"]
    }
  ],
  "clients": [
    {
      "clientId": "knowledge-frontend",
      "publicClient": true,
      "redirectUris": ["http://localhost:3000/*"],
      "webOrigins": ["http://localhost:3000"]
    }
  ]
}
```

### 2. Docker Compose 수정

```yaml
kp-keycloak:
  image: quay.io/keycloak/keycloak:23.0
  command:
    - start-dev
    - --import-realm
  volumes:
    - ./keycloak/realm-export.json:/opt/keycloak/data/import/realm-export.json:ro
```

### 3. 환경변수 설정

```env
# .env.test
KEYCLOAK_ADMIN=admin
KEYCLOAK_ADMIN_PASSWORD=admin
KC_REALM=knowledge-platform
```

---

## 테스트 계획

1. **단위 테스트**: realm-export.json 유효성 검증
2. **통합 테스트**: Keycloak 컨테이너 기동 후 realm 확인
3. **E2E 테스트**: Docker 모드 전체 실행 (98/98 목표)

---

## 산출물

```
infrastructure/docker/
└── keycloak/
    ├── realm-export.json     # Realm 설정 파일
    └── README.md             # 설정 가이드
```

---

## 의존성

- kp-keycloak 컨테이너
- kp-keycloak-db (PostgreSQL)

---

## 참고 자료

- [Keycloak Import/Export Docs](https://www.keycloak.org/server/importExport)
- [Sprint 04 Docker E2E 실패 분석](../../work_logs/daily_logs/2026/01-January/2026-01-29.md)
