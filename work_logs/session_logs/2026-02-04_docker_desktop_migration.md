# Session Log - Docker Desktop D: 드라이브 이동

## Session Info
| 항목 | 값 |
|------|---|
| **날짜** | 2026-02-04 (화) |
| **시작** | 22:18 KST |
| **종료** | 00:38 KST (2026-02-05) |
| **에이전트** | Claude Code (Opus 4.5) |
| **주제** | Docker Desktop 데이터 D: 드라이브 이동 |

---

## 배경

C: 드라이브 공간 부족으로 Docker Desktop 데이터를 D: 드라이브로 이동 필요.

---

## 시도한 방법들

### 1. Junction 링크 방식 (실패)
```powershell
wsl --shutdown
cmd /c rmdir "C:\Users\KTDS\AppData\Local\Docker\wsl"
cmd /c mklink /J "C:\Users\KTDS\AppData\Local\Docker\wsl" "D:\Docker\wsl"
```

**문제**: `settings.json`의 `dataFolder` 설정과 충돌

### 2. settings.json dataFolder 설정 (실패)
```json
{
  "dataFolder": "D:\\Docker\\wsl",
  "wslEngineEnabled": true
}
```

**문제**: Junction과 동시 사용 시 충돌

### 3. 기존 91GB vhdx 복구 시도 (실패)
- 기존 데이터: `D:\Docker\wsl\disk\docker_data.vhdx` (91GB)
- Docker Engine 시작 실패 (4분+ 타임아웃)
- 로그: `still waiting for init control API to respond after 3m57s`

**원인 추정**: vhdx 파일이 현재 Docker Desktop 버전과 호환되지 않음

### 4. Factory Reset (성공)
- Docker Desktop 초기화
- D: 드라이브 `dataFolder` 설정 유지
- 모든 이미지/컨테이너 새로 빌드

---

## 최종 해결 과정

1. **Docker Desktop Factory Reset** 실행
2. **settings.json** 확인 (dataFolder: D:\Docker\wsl)
3. **이미지 빌드**
   ```bash
   cd infrastructure/docker
   docker-compose build
   ```
4. **서비스 시작**
   ```bash
   docker-compose up -d
   ```
5. **접속 확인**: http://localhost → 200 OK

---

## 빌드된 이미지

| 이미지 | 크기 |
|--------|------|
| ai-service | 11.8GB |
| backend | 581MB |
| api-gateway | 459MB |
| frontend | 96.4MB |
| nginx | 74.2MB |

---

## 시작된 컨테이너 (18개)

| 레이어 | 컨테이너 | 상태 |
|--------|----------|:----:|
| **Application** | nginx, frontend, api-gateway, backend, ai-service | ✅ healthy |
| **Auth** | keycloak, keycloak-db | ✅ healthy |
| **Data** | postgresql, neo4j, elasticsearch, redis, minio | ✅ healthy |
| **Observability** | prometheus, grafana, loki, promtail, jaeger, kibana | ✅ healthy |

---

## 교훈

1. **Junction + dataFolder 동시 사용 금지**: 둘 중 하나만 사용
2. **vhdx 호환성 주의**: Docker Desktop 버전 간 vhdx 파일 호환 문제 있음
3. **docker-compose.yml의 가치**: IaC 덕분에 Factory Reset 후에도 빠른 복구 가능
4. **과감한 결정**: 복구에 너무 오래 매달리지 말고, 재생성이 빠르면 선택

---

## 관련 파일

- `infrastructure/docker/docker-compose.yml` - 18개 컨테이너 정의
- `C:\Users\KTDS\AppData\Roaming\Docker\settings.json` - Docker Desktop 설정

---

## 다음 단계

- [x] Docker Desktop D: 드라이브 설정 완료
- [x] 프로젝트 컨테이너 빌드 완료
- [x] 18개 컨테이너 시작 완료
- [x] 프론트엔드 접속 확인 완료
- [ ] 개발 환경 정상 작동 검증 (다음 세션)

---

*Logged: 2026-02-05 00:38 KST*
*Author: Claude Code (Opus 4.5)*
