# [부록 A] Neo4j 설치 가이드 (WSL2 + Docker Desktop) 상세본

> [22_neo4j_construction_guide_wsl2.md](./22_neo4j_construction_guide_wsl2.md)의 **§4~§6 (Docker Compose · 컨테이너 기동) 부분을 처음 접하는 사용자도 따라할 수 있도록 풀어쓴 상세 첨부**입니다.

| 항목 | 내용 |
|------|------|
| **문서 ID** | DESIGN-22-A |
| **상위 문서** | [22_neo4j_construction_guide_wsl2.md](./22_neo4j_construction_guide_wsl2.md) |
| **작성일** | 2026-04-22 |
| **작성자** | 클로드 (Claude Code) |
| **대상 환경** | Windows 11 + WSL2 Ubuntu + Docker Desktop |
| **작업 계정** | `ktds` (sudo 비밀번호: `ktds`) |
| **설치 방식** | Docker Compose 단일 컨테이너 (Community Edition) |

---

## 변경 이력

| 버전 | 일자 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0 | 2026-04-22 | 클로드 | 초안 — 사전점검부터 첫 쿼리까지 단계별 상세 |

---

## 목차

- [A.0 설치 옵션 비교 — 왜 Docker인가](#a0-설치-옵션-비교--왜-docker인가)
- [A.1 사전 환경 점검 (10분)](#a1-사전-환경-점검-10분)
- [A.2 Docker Desktop + WSL2 통합 확인](#a2-docker-desktop--wsl2-통합-확인)
- [A.3 WSL2 메모리 튜닝 (.wslconfig)](#a3-wsl2-메모리-튜닝-wslconfig)
- [A.4 작업 디렉토리 권한 점검](#a4-작업-디렉토리-권한-점검)
- [A.5 기존 Neo4j 컨테이너와의 충돌 사전 확인](#a5-기존-neo4j-컨테이너와의-충돌-사전-확인)
- [A.6 Neo4j 이미지 사전 Pull (선택)](#a6-neo4j-이미지-사전-pull-선택)
- [A.7 Docker Compose 파일 생성 (라인별 해설)](#a7-docker-compose-파일-생성-라인별-해설)
- [A.8 환경변수 파일 (.env) 생성](#a8-환경변수-파일-env-생성)
- [A.9 첫 기동 — 단계별 검증](#a9-첫-기동--단계별-검증)
- [A.10 cypher-shell 첫 접속](#a10-cypher-shell-첫-접속)
- [A.11 Browser UI 접속 (Windows 측)](#a11-browser-ui-접속-windows-측)
- [A.12 플러그인(APOC + n10s) 설치 검증](#a12-플러그인apoc--n10s-설치-검증)
- [A.13 비밀번호 변경 (운영 시 필수)](#a13-비밀번호-변경-운영-시-필수)
- [A.14 자동 시작 (Windows 부팅 시) 옵션](#a14-자동-시작-windows-부팅-시-옵션)
- [A.15 백업/복구 절차](#a15-백업복구-절차)
- [A.16 제거 절차 (Uninstall)](#a16-제거-절차-uninstall)
- [A.17 설치 체크리스트](#a17-설치-체크리스트)
- [A.18 자주 묻는 질문 (FAQ)](#a18-자주-묻는-질문-faq)

---

## A.0 설치 옵션 비교 — 왜 Docker인가

| 방식 | 장점 | 단점 | 권장 여부 |
|------|------|------|-----------|
| **Docker Compose** ⭐ | 격리/이식성, 다중 인스턴스 공존, plugins 자동 설치 | Docker 학습 필요 | ✅ **본 가이드 채택** |
| Native Linux 패키지 (.deb) | 호스트 자원 최대 활용 | 다중 버전 공존 어려움, 의존성 충돌 | ❌ 본 환경 부적합 |
| Windows MSI | GUI 설치 | WSL2 ↔ Windows 경로/포트 변환 복잡 | ❌ |
| Neo4j Desktop | UI 편의성 | 라이선스 (개발용 무료, 상업용 제한) | △ 학습용만 |
| AuraDB (클라우드) | 운영 부담 0 | 인터넷 필요, 비용 | △ 별도 검토 |

> **결정 근거**: 기존 프로젝트(`kp-neo4j`)와 신규 프로젝트(`serag-neo4j`)가 **동일 호스트에서 공존**해야 하므로 Docker 격리가 필수.

---

## A.1 사전 환경 점검 (10분)

### A.1.1 WSL2 버전 확인

**Windows PowerShell** (관리자 권한):

```powershell
wsl --version
# 예상: WSL 버전 2.x.x 이상
wsl --list --verbose
# 예상:
#   NAME      STATE       VERSION
# * Ubuntu    Running     2
```

> ⚠️ `VERSION`이 `1`이면 WSL2로 변환:
> ```powershell
> wsl --set-version Ubuntu 2
> ```

### A.1.2 WSL2 진입 및 OS 확인

```bash
# Windows 터미널 → WSL Ubuntu 진입
wsl

# 또는 직접 ktds 계정으로
wsl -u ktds

# 확인
whoami           # → ktds
uname -a         # → Linux DESKTOP-JE4TNAH 6.6.87.2-microsoft-standard-WSL2 ...
pwd              # → /home/ktds (또는 다른 위치)
```

### A.1.3 sudo 동작 확인

```bash
sudo -v
# 비밀번호 입력: ktds
# 오류 없으면 정상
```

### A.1.4 시스템 자원 확인

```bash
# CPU
nproc                     # 권장 4 이상

# 메모리
free -h                   # 권장 8GB 이상 (전체)

# 디스크
df -h /home              # 최소 5GB 여유
```

| 자원 | 최소 | 권장 |
|------|------|------|
| CPU | 2 cores | 4 cores |
| RAM | 4 GB | 8 GB+ (기존 kp-neo4j 동시 실행 시) |
| Disk | 5 GB | 10 GB+ |

---

## A.2 Docker Desktop + WSL2 통합 확인

### A.2.1 Windows 측 설정 확인

1. **Docker Desktop 실행** → 우측 상단 ⚙️ Settings
2. **Resources → WSL Integration** 확인
   - ✅ `Enable integration with my default WSL distro`
   - ✅ Ubuntu 토글 ON
3. **Apply & Restart**

### A.2.2 WSL2에서 Docker CLI 확인

```bash
# WSL2 진입 후
docker version
# Client: Docker Engine - Community + Server: Docker Desktop ...

docker info | head -20
# 오류 없으면 정상

docker run --rm hello-world
# "Hello from Docker!" 출력
```

> ❌ `Cannot connect to the Docker daemon` 오류:
> - Docker Desktop이 실행 중인지 확인
> - Settings → Resources → WSL Integration에서 Ubuntu 토글 재활성화
> - WSL 재시작: PowerShell에서 `wsl --shutdown` 후 다시 `wsl`

### A.2.3 docker compose v2 확인

```bash
docker compose version
# Docker Compose version v2.x.x

# v1 (docker-compose) 명령은 deprecated — v2 사용 권장
```

---

## A.3 WSL2 메모리 튜닝 (.wslconfig)

### A.3.1 왜 필요한가

기본 WSL2는 호스트 메모리의 50%를 사용합니다. 기존 `kp-neo4j`(2G heap) + 신규 `serag-neo4j`(1G heap) + Docker 자체 + 기타 = **최소 6GB 필요**.

### A.3.2 .wslconfig 작성 (Windows 측)

**Windows 사용자 폴더에 작성**: `C:\Users\<UserName>\.wslconfig`

WSL2 안에서 작성하려면:

```bash
# WSL2에서 Windows 사용자 폴더 접근
ls /mnt/c/Users/

# 본인의 Windows 사용자명 확인 후
WIN_USER="<본인_사용자명>"
cat > "/mnt/c/Users/$WIN_USER/.wslconfig" <<'EOF'
[wsl2]
memory=8GB
processors=4
swap=2GB
localhostForwarding=true
EOF

cat "/mnt/c/Users/$WIN_USER/.wslconfig"
```

### A.3.3 적용

**PowerShell (관리자)**:

```powershell
wsl --shutdown
# 30초 대기 후
wsl
```

**WSL2 재진입 후 확인**:

```bash
free -h
# total: 약 8.0Gi 표시되면 적용됨
```

### A.3.4 본 프로젝트의 기존 설정 활용

> 💡 `MEMORY.md`에 따르면 본 프로젝트는 이미 `hybrid-rag` WSL2 프로파일(14GB / 4GB swap / 8 CPU)을 사용 중입니다.
> ```bash
> # 본 프로젝트 루트에서
> ./scripts/switch-wslconfig.sh hybrid-rag
> ```

---

## A.4 작업 디렉토리 권한 점검

### A.4.1 디렉토리 생성 및 소유권 확인

```bash
cd /home/ktds
ls -la SearcheRAGWithGraphRAG 2>/dev/null

# 없으면 생성
mkdir -p SearcheRAGWithGraphRAG
cd SearcheRAGWithGraphRAG
pwd                     # → /home/ktds/SearcheRAGWithGraphRAG

# 소유권: ktds:ktds 여야 함
ls -ld .
# drwxr-xr-x  ... ktds ktds ...
```

### A.4.2 소유권 수정 (필요 시)

```bash
sudo chown -R ktds:ktds /home/ktds/SearcheRAGWithGraphRAG
```

### A.4.3 Docker 그룹 가입 확인

```bash
groups ktds | grep docker
# docker가 포함되어야 sudo 없이 docker 명령 사용 가능

# 없으면 추가
sudo usermod -aG docker ktds
# 적용을 위해 WSL 재시작 필요
```

> **주의**: WSL2 + Docker Desktop 환경에서는 보통 자동으로 docker 그룹이 설정되어 있습니다. 그래도 안 되면 위 명령 후 `wsl --shutdown` → 재진입.

---

## A.5 기존 Neo4j 컨테이너와의 충돌 사전 확인

### A.5.1 실행 중인 Neo4j 컨테이너 확인

```bash
docker ps --filter "name=neo4j" --format "table {{.Names}}\t{{.Image}}\t{{.Ports}}\t{{.Status}}"
```

**예상 출력 (본 프로젝트 가동 중인 경우)**:
```
NAMES       IMAGE                  PORTS                                            STATUS
kp-neo4j    neo4j:5.15-community   0.0.0.0:7474->7474/tcp, 0.0.0.0:7687->7687/tcp   Up 2 hours
```

### A.5.2 사용 중인 포트 확인

```bash
# 7474, 7475, 7687, 7688 점유 여부
ss -tlnp 2>/dev/null | grep -E ":(7474|7475|7687|7688)\s" || echo "모두 비어있음"

# Windows 측에서 점유한 포트 확인 (PowerShell)
# netstat -ano | findstr "7474 7475 7687 7688"
```

| 포트 | 점유자 | 처리 |
|------|--------|------|
| 7474 | `kp-neo4j` (기존) | 그대로 둠 — 신규는 7475 사용 |
| 7687 | `kp-neo4j` (기존) | 그대로 둠 — 신규는 7688 사용 |
| 7475 | 비어있어야 함 | 신규 컨테이너용 |
| 7688 | 비어있어야 함 | 신규 컨테이너용 |

### A.5.3 컨테이너 이름 충돌 확인

```bash
# serag-neo4j가 이미 있는지 (있으면 안 됨)
docker ps -a --filter "name=serag-neo4j" --format "{{.Names}}"

# 있으면 제거 (데이터 보존)
docker stop serag-neo4j 2>/dev/null
docker rm serag-neo4j 2>/dev/null
```

### A.5.4 네트워크 이름 충돌 확인

```bash
# serag-net이 이미 있는지
docker network ls | grep serag-net

# 있으면 제거
docker network rm serag-net 2>/dev/null
```

---

## A.6 Neo4j 이미지 사전 Pull (선택)

> 인터넷 환경이 좋지 않거나, 기동 시간을 단축하고 싶으면 미리 다운로드.

### A.6.1 이미지 다운로드

```bash
docker pull neo4j:5.18-community

# 다운로드 확인
docker images neo4j
# REPOSITORY   TAG              IMAGE ID       CREATED   SIZE
# neo4j        5.18-community   ...            ...       ~600MB
```

### A.6.2 이미지 검증

```bash
# 메타데이터 확인
docker inspect neo4j:5.18-community --format '{{.Config.Env}}' | tr ',' '\n' | head -20

# 빠른 동작 확인 (포트 노출 없이)
docker run --rm neo4j:5.18-community neo4j --version
# 5.18.x
```

### A.6.3 버전 호환성 표

| Neo4j | APOC | n10s (neosemantics) | 비고 |
|-------|------|---------------------|------|
| 5.15.x | 5.15.x | 5.15.x | **기존 프로젝트 사용 중** |
| 5.18.x | 5.18.x | 5.18.x | **본 가이드 권장** (n10s 환경변수 자동 설치 안정화) |
| 5.20.x | 5.20.x | 5.20.x | 최신, 일부 procedure 변경 |

> 💡 본 가이드는 **5.18.x를 채택**합니다. 환경변수 `NEO4J_PLUGINS=["apoc","n10s"]`만으로 자동 설치되며, OWL import 안정성이 검증된 버전입니다.

---

## A.7 Docker Compose 파일 생성 (라인별 해설)

### A.7.1 디렉토리 준비

```bash
cd /home/ktds/SearcheRAGWithGraphRAG
mkdir -p docker
cd docker
```

### A.7.2 파일 생성

`/home/ktds/SearcheRAGWithGraphRAG/docker/docker-compose.yml`:

```yaml
services:
  serag-neo4j:                          # ① 서비스 이름 (DNS 명)
    image: neo4j:5.18-community         # ② 이미지 + 태그 명시 (latest 금지)
    container_name: serag-neo4j         # ③ 고정 컨테이너 이름 (kp-neo4j와 분리)
    restart: unless-stopped             # ④ 수동 중지 외에는 자동 재시작

    ports:
      - "7475:7474"                     # ⑤ Browser UI: host:7475 → container:7474
      - "7688:7687"                     # ⑥ Bolt Driver: host:7688 → container:7687

    environment:
      # ─── 인증 ───
      NEO4J_AUTH: ${NEO4J_AUTH:-neo4j/serag-pass-1234}     # ⑦ 초기 비밀번호
      NEO4J_dbms_security_auth__minimum__password__length: "4"

      # ─── 플러그인 자동 설치 ───
      NEO4J_PLUGINS: '["apoc","n10s"]'                     # ⑧ 컨테이너 시작 시 자동 다운로드

      # ─── 메모리 (기존 kp-neo4j와 동시 실행 고려) ───
      NEO4J_server_memory_heap_initial__size: "512m"       # ⑨ JVM Heap 초기
      NEO4J_server_memory_heap_max__size: "1G"             # ⑩ JVM Heap 최대
      NEO4J_server_memory_pagecache_size: "512m"           # ⑪ Page Cache (디스크 I/O 가속)

      # ─── 보안: APOC/n10s procedure 호출 권한 ───
      NEO4J_dbms_security_procedures_unrestricted: "apoc.*,n10s.*"
      NEO4J_dbms_security_procedures_allowlist:    "apoc.*,n10s.*"
      NEO4J_apoc_import_file_enabled: "true"
      NEO4J_apoc_export_file_enabled: "true"
      NEO4J_apoc_import_file_use__neo4j__config: "true"

      # ─── Import 디렉토리 (OWL Turtle 파일 위치) ───
      NEO4J_server_directories_import: "/import"           # ⑫ 컨테이너 내부 경로

    volumes:
      - serag_neo4j_data:/data                             # ⑬ 데이터 (영구)
      - serag_neo4j_logs:/logs                             # ⑭ 로그
      - serag_neo4j_plugins:/plugins                       # ⑮ 플러그인 jar 캐시
      - ../ontology:/import:ro                             # ⑯ OWL 파일 마운트 (RO)
      - ../cypher:/cypher:ro                               # ⑰ Cypher 스크립트 (선택)

    networks:
      - serag-net                                          # ⑱ 전용 네트워크

    healthcheck:                                           # ⑲ Docker 헬스체크
      test: ["CMD", "cypher-shell", "-u", "neo4j", "-p", "serag-pass-1234", "RETURN 1"]
      interval: 10s                                        # 10초마다
      timeout: 5s
      retries: 12                                          # 12회 = 2분
      start_period: 30s                                    # 시작 후 30초는 실패 무시

networks:
  serag-net:
    name: serag-net
    driver: bridge

volumes:
  serag_neo4j_data:    { name: serag_neo4j_data }
  serag_neo4j_logs:    { name: serag_neo4j_logs }
  serag_neo4j_plugins: { name: serag_neo4j_plugins }
```

### A.7.3 라인별 해설

| 번호 | 항목 | 설명 |
|------|------|------|
| ① | 서비스명 | docker compose 명령에서 사용 |
| ② | 이미지 태그 | `latest` 금지 — 재현성 확보 |
| ③ | container_name | 고정값으로 다른 docker 명령에서 식별 |
| ④ | restart 정책 | 컨테이너 비정상 종료 시 자동 재시작 |
| ⑤⑥ | 포트 매핑 | **host_port:container_port** 형식 |
| ⑦ | NEO4J_AUTH | 형식: `username/password`. `.env`로 오버라이드 |
| ⑧ | NEO4J_PLUGINS | JSON 배열 — 컨테이너 첫 시작 시 자동 다운로드 |
| ⑨⑩ | Heap | 1GB로 제한 (기존 2G + 신규 1G = 3G) |
| ⑪ | Page Cache | 메모리 기반 디스크 캐시 |
| ⑫ | import 경로 | `n10s.onto.import.fetch('file:///import/...')` 시 사용 |
| ⑬⑭⑮ | named volume | 컨테이너 삭제 후에도 보존 |
| ⑯ | bind mount RO | 호스트의 ontology 폴더를 읽기전용으로 노출 |
| ⑰ | bind mount RO | Cypher 스크립트도 컨테이너에서 직접 읽기 가능 |
| ⑱ | network | 다른 컨테이너와 통신 시 활용 (현재는 단일 컨테이너) |
| ⑲ | healthcheck | `docker ps`의 STATUS 컬럼에 `(healthy)` 표시 |

### A.7.4 환경변수 명명 규칙 (Neo4j 5.x)

| Neo4j 설정 키 | 환경변수명 |
|---------------|-----------|
| `dbms.security.auth_minimum_password_length` | `NEO4J_dbms_security_auth__minimum__password__length` |
| `server.memory.heap.max_size` | `NEO4J_server_memory_heap_max__size` |
| `server.directories.import` | `NEO4J_server_directories_import` |

> **규칙**:
> - `.` → `_`
> - `_` → `__` (언더스코어 두 개)
> - 접두사 `NEO4J_`

---

## A.8 환경변수 파일 (.env) 생성

### A.8.1 .env 작성

```bash
cd /home/ktds/SearcheRAGWithGraphRAG

cat > .env <<'EOF'
# Neo4j 인증
NEO4J_AUTH=neo4j/serag-pass-1234
NEO4J_USER=neo4j
NEO4J_PASSWORD=serag-pass-1234

# 접속 URI (호스트에서 사용)
NEO4J_BOLT_URI=bolt://localhost:7688
NEO4J_HTTP_URI=http://localhost:7475
EOF

chmod 600 .env             # 다른 사용자 접근 차단
ls -la .env                # -rw------- ktds ktds
```

### A.8.2 .gitignore 추가 (저장소 사용 시)

```bash
cat > .gitignore <<'EOF'
.env
.venv/
__pycache__/
*.pyc
docker/plugins/
EOF
```

---

## A.9 첫 기동 — 단계별 검증

### A.9.1 기동 명령

```bash
cd /home/ktds/SearcheRAGWithGraphRAG/docker
docker compose up -d
```

**예상 출력**:
```
[+] Running 4/4
 ✔ Network serag-net               Created
 ✔ Volume "serag_neo4j_data"       Created
 ✔ Volume "serag_neo4j_logs"       Created
 ✔ Container serag-neo4j           Started
```

### A.9.2 컨테이너 상태 확인

```bash
docker ps --filter "name=serag-neo4j"
```

**상태 변화**:
1. `Up 5 seconds (health: starting)` — 초기화 중
2. `Up 30 seconds (healthy)` ✅ — 준비 완료

### A.9.3 시작 로그 확인

```bash
docker logs serag-neo4j 2>&1 | head -50
```

**정상 로그 키워드**:
- `Installing Plugin 'apoc' from ...`
- `Installing Plugin 'n10s' from ...`
- `Started.` (마지막 줄)

### A.9.4 헬스체크 대기 (스크립트)

```bash
for i in {1..24}; do
  status=$(docker inspect -f '{{.State.Health.Status}}' serag-neo4j 2>/dev/null)
  echo "[$i/24] $status"
  [ "$status" = "healthy" ] && break
  sleep 5
done
```

### A.9.5 두 컨테이너 공존 확인

```bash
docker ps --filter "name=neo4j" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

**예상 출력**:
```
NAMES         STATUS                  PORTS
kp-neo4j      Up 3 hours (healthy)    0.0.0.0:7474->7474/tcp, 0.0.0.0:7687->7687/tcp
serag-neo4j   Up 1 minute (healthy)   0.0.0.0:7475->7474/tcp, 0.0.0.0:7688->7687/tcp
```

---

## A.10 cypher-shell 첫 접속

### A.10.1 컨테이너 내부 접속

```bash
docker exec -it serag-neo4j cypher-shell -u neo4j -p serag-pass-1234
```

**프롬프트**:
```
Connected to Neo4j using Bolt protocol version 5.0 at neo4j://localhost:7687 as user neo4j.
neo4j@neo4j>
```

### A.10.2 첫 쿼리

```cypher
neo4j@neo4j> RETURN 'Hello Neo4j' AS msg, datetime() AS now;

+----------------------------------------------------------+
| msg          | now                                       |
+----------------------------------------------------------+
| "Hello Neo4j"| 2026-04-22T10:30:00.123456000+00:00       |
+----------------------------------------------------------+

neo4j@neo4j> :exit
Bye!
```

### A.10.3 호스트(WSL2)에서 직접 접속 (선택)

```bash
# cypher-shell 호스트에 설치
sudo apt-get update && sudo apt-get install -y cypher-shell

# 접속
cypher-shell -a bolt://localhost:7688 -u neo4j -p serag-pass-1234
```

> 💡 보통은 컨테이너 내부 cypher-shell만으로 충분합니다.

---

## A.11 Browser UI 접속 (Windows 측)

### A.11.1 브라우저 접속

**Windows의 Chrome/Edge** 주소창:
```
http://localhost:7475
```

### A.11.2 로그인

| 필드 | 값 |
|------|-----|
| Connect URL | `bolt://localhost:7688` (자동 입력됨, 필요 시 수정) |
| Username | `neo4j` |
| Password | `serag-pass-1234` |

> ⚠️ **첫 로그인 시 비밀번호 변경 화면**이 나올 수 있습니다 (Neo4j 정책). 동일하게 `serag-pass-1234`로 두거나 강력한 비밀번호로 변경 (§A.13).

### A.11.3 첫 명령 실행

Browser 상단 입력창:
```cypher
:server status
```

실행하면 연결 상태 표시.

```cypher
RETURN 'UI 동작 OK' AS msg
```

### A.11.4 두 UI 동시 사용

| 프로젝트 | URL |
|----------|-----|
| hybrid-rag-knowledge-ops | http://localhost:**7474** |
| SearcheRAGWithGraphRAG | http://localhost:**7475** |

> 두 탭을 열어 동시에 작업 가능 — **로그인 정보가 다르므로 혼동 주의**.

---

## A.12 플러그인(APOC + n10s) 설치 검증

### A.12.1 설치된 plugins 확인

```bash
docker exec serag-neo4j ls -la /plugins/
```

**예상 출력** (자동 다운로드된 jar):
```
apoc-5.18.0-core.jar
neosemantics-5.18.0.jar
```

### A.12.2 APOC 동작 확인

```bash
docker exec serag-neo4j cypher-shell -u neo4j -p serag-pass-1234 \
  "RETURN apoc.version() AS apoc_version;"
```

예상: `5.18.0` 또는 유사 버전.

### A.12.3 n10s 동작 확인

```bash
docker exec serag-neo4j cypher-shell -u neo4j -p serag-pass-1234 \
  "CALL n10s.graphconfig.show() YIELD param, value RETURN param, value LIMIT 5;"
```

> ❌ `Unknown procedure 'n10s.graphconfig.show'` 오류 시:
> 1. `NEO4J_PLUGINS` 환경변수에 `"n10s"` 포함 확인
> 2. `NEO4J_dbms_security_procedures_unrestricted: "n10s.*"` 포함 확인
> 3. 컨테이너 재시작: `docker compose restart serag-neo4j`

### A.12.4 procedures 카운트

```bash
docker exec serag-neo4j cypher-shell -u neo4j -p serag-pass-1234 \
  "SHOW PROCEDURES YIELD name WHERE name STARTS WITH 'apoc' OR name STARTS WITH 'n10s' RETURN substring(name,0,4) AS plugin, count(*) AS cnt;"
```

**예상 출력**:
```
plugin  cnt
"apoc"  ~400
"n10s"  ~80
```

---

## A.13 비밀번호 변경 (운영 시 필수)

### A.13.1 강력한 비밀번호 생성

```bash
# 32자 랜덤
openssl rand -base64 24
# 예: aB3xK9mP+vQz... (이 값을 안전하게 보관)
```

### A.13.2 변경 명령

```bash
NEW_PWD="여기에_생성한_비밀번호"
docker exec serag-neo4j cypher-shell -u neo4j -p serag-pass-1234 \
  "ALTER CURRENT USER SET PASSWORD FROM 'serag-pass-1234' TO '$NEW_PWD';"
```

### A.13.3 .env 업데이트

```bash
sed -i "s|serag-pass-1234|$NEW_PWD|g" /home/ktds/SearcheRAGWithGraphRAG/.env
cat /home/ktds/SearcheRAGWithGraphRAG/.env
```

### A.13.4 docker-compose.yml의 healthcheck도 갱신 필요

```bash
sed -i "s|serag-pass-1234|$NEW_PWD|g" /home/ktds/SearcheRAGWithGraphRAG/docker/docker-compose.yml
docker compose -f /home/ktds/SearcheRAGWithGraphRAG/docker/docker-compose.yml up -d
```

> ⚠️ **본 가이드의 학습용 환경**에서는 `serag-pass-1234` 그대로 사용해도 무방합니다 (외부 노출 없음).

---

## A.14 자동 시작 (Windows 부팅 시) 옵션

### A.14.1 Docker Desktop 자동 시작

**Windows Docker Desktop** → Settings → General → ✅ `Start Docker Desktop when you sign in to your computer`

### A.14.2 컨테이너 자동 시작

`docker-compose.yml`에 `restart: unless-stopped` 이미 설정되어 있으므로:
- Docker Desktop 시작 → 자동으로 `serag-neo4j` 기동
- 명시적으로 `docker compose down` 한 경우만 정지 상태 유지

### A.14.3 WSL2 자동 시작 (선택)

**Task Scheduler 등록** (PowerShell 관리자):

```powershell
$action = New-ScheduledTaskAction -Execute "wsl.exe" -Argument "-d Ubuntu -u ktds -- echo WSL Started"
$trigger = New-ScheduledTaskTrigger -AtLogon
Register-ScheduledTask -TaskName "WSL2 Auto Start" -Action $action -Trigger $trigger -RunLevel Highest
```

---

## A.15 백업/복구 절차

### A.15.1 데이터 덤프 (오프라인)

```bash
# 1. 컨테이너 중지
docker compose -f /home/ktds/SearcheRAGWithGraphRAG/docker/docker-compose.yml stop

# 2. 덤프 (Neo4j 5.x admin 명령)
docker run --rm \
  -v serag_neo4j_data:/data \
  -v /home/ktds/SearcheRAGWithGraphRAG/backup:/backup \
  neo4j:5.18-community \
  neo4j-admin database dump neo4j --to-path=/backup

# 3. 재기동
docker compose -f /home/ktds/SearcheRAGWithGraphRAG/docker/docker-compose.yml start

# 4. 백업 파일 확인
ls -lh /home/ktds/SearcheRAGWithGraphRAG/backup/
# neo4j.dump (수십 MB ~ 수 GB)
```

### A.15.2 복구

```bash
# 1. 컨테이너 중지
docker compose stop

# 2. load
docker run --rm \
  -v serag_neo4j_data:/data \
  -v /home/ktds/SearcheRAGWithGraphRAG/backup:/backup \
  neo4j:5.18-community \
  neo4j-admin database load neo4j --from-path=/backup --overwrite-destination=true

# 3. 재기동
docker compose start
```

### A.15.3 자동 백업 (cron)

```bash
crontab -e
# 매일 새벽 3시 백업
0 3 * * * /home/ktds/SearcheRAGWithGraphRAG/scripts/backup.sh > /tmp/serag-backup.log 2>&1
```

---

## A.16 제거 절차 (Uninstall)

### A.16.1 컨테이너만 제거 (데이터 보존)

```bash
cd /home/ktds/SearcheRAGWithGraphRAG/docker
docker compose down       # 컨테이너 + 네트워크 제거, 볼륨 보존
```

### A.16.2 볼륨까지 제거 (전체 초기화)

```bash
docker compose down -v    # 볼륨까지 제거
docker volume ls | grep serag
docker volume rm serag_neo4j_data serag_neo4j_logs serag_neo4j_plugins 2>/dev/null
```

### A.16.3 이미지 제거

```bash
docker rmi neo4j:5.18-community
```

### A.16.4 작업 폴더 제거

```bash
cd ~
rm -rf /home/ktds/SearcheRAGWithGraphRAG
```

> ⚠️ **확인 사항**: 기존 `kp-neo4j`(hybrid-rag-knowledge-ops 프로젝트)는 영향받지 않음.

---

## A.17 설치 체크리스트

### Phase 1: 사전 환경
- [ ] WSL2 Ubuntu 진입 (`whoami` → ktds)
- [ ] sudo 동작 (`sudo -v`)
- [ ] Docker Desktop 실행 중 (`docker version`)
- [ ] Docker WSL Integration 활성화
- [ ] WSL2 메모리 8GB 이상 (`free -h`)

### Phase 2: 충돌 회피
- [ ] 기존 `kp-neo4j` 확인 (포트 7474/7687)
- [ ] 신규 포트(7475/7688) 비어있음
- [ ] 동일 이름 컨테이너 없음

### Phase 3: 파일 작성
- [ ] `/home/ktds/SearcheRAGWithGraphRAG` 생성
- [ ] `docker/docker-compose.yml` 작성
- [ ] `.env` 작성 (chmod 600)
- [ ] `ontology/hrkp-ontology.ttl` 작성

### Phase 4: 기동
- [ ] `docker compose up -d` 성공
- [ ] `docker ps` → `(healthy)` 표시
- [ ] cypher-shell 접속 성공
- [ ] Browser UI 접속 성공 (http://localhost:7475)

### Phase 5: 플러그인
- [ ] `/plugins/`에 apoc, n10s jar 존재
- [ ] `apoc.version()` 호출 성공
- [ ] `n10s.graphconfig.show()` 호출 성공

### Phase 6: 마무리 (선택)
- [ ] 비밀번호 변경
- [ ] 자동 시작 설정
- [ ] 백업 cron 등록

---

## A.18 자주 묻는 질문 (FAQ)

### Q1. Docker Desktop 없이 WSL2 안에서 Docker만 설치하면 안 되나요?

**A.** 가능하지만 비권장. Docker Desktop이 WSL2 통합 + 리소스 관리를 자동화해주므로 본 가이드는 Docker Desktop을 전제로 합니다. 굳이 분리하려면 `dockerd`를 systemd 서비스로 직접 운영해야 하며, WSL2의 init 시스템 한계로 부팅 시 자동 시작이 까다롭습니다.

### Q2. 포트를 변경하지 않고 기존 kp-neo4j를 끄면 되지 않나요?

**A.** 가능하지만 비권장. 두 프로젝트가 **동시 가동**되는 시나리오를 가정하므로 포트 분리가 안전합니다. 굳이 끄려면:
```bash
docker stop kp-neo4j
docker compose -f .../docker/docker-compose.yml up -d serag-neo4j  # 7474/7687로 수정 후
```
하지만 본 프로젝트(hybrid-rag) 작업 시 매번 토글해야 하므로 비효율적.

### Q3. neo4j:5.18-enterprise를 써도 되나요?

**A.** 안 됩니다. Enterprise는 라이선스가 필요합니다. 본 가이드는 **Community Edition**을 사용하며, 단일 데이터베이스 / 일부 클러스터 기능 제외 / 기본 보안만 사용 가능. 학습/개발 용도로는 충분합니다.

### Q4. WSL2의 localhost:7475가 Windows에서 안 보입니다.

**A.** 다음 순서로 점검:
1. `docker ps`로 `0.0.0.0:7475->7474/tcp` 확인
2. WSL2의 IP 확인: `ip addr show eth0 | grep inet`
3. Windows 측 방화벽: 인바운드 규칙에서 7475 허용
4. WSL 재시작: PowerShell `wsl --shutdown` → 재진입
5. `.wslconfig`에 `localhostForwarding=true` 설정 확인

### Q5. 플러그인 자동 설치가 실패합니다 (인터넷 차단 환경).

**A.** 수동 설치 절차:
```bash
# 1. 호스트에서 jar 다운로드
mkdir -p /home/ktds/SearcheRAGWithGraphRAG/docker/plugins-manual
cd /home/ktds/SearcheRAGWithGraphRAG/docker/plugins-manual
wget https://github.com/neo4j/apoc/releases/download/5.18.0/apoc-5.18.0-core.jar
wget https://github.com/neo4j-labs/neosemantics/releases/download/5.18.0/neosemantics-5.18.0.jar

# 2. docker-compose.yml 수정
# NEO4J_PLUGINS 환경변수 제거하고 volumes에 추가:
# - ./plugins-manual:/plugins:ro

# 3. 재기동
docker compose up -d --force-recreate
```

### Q6. 메모리 부족으로 컨테이너가 죽습니다.

**A.** 우선순위:
1. `.wslconfig`에서 메모리 8GB 이상 할당
2. `serag-neo4j`의 heap을 512MB로 더 낮춤 (`NEO4J_server_memory_heap_max__size: "512m"`)
3. 기존 `kp-neo4j` 일시 정지: `docker stop kp-neo4j`
4. Docker Desktop Settings → Resources → Memory 상향

### Q7. 백업이 너무 큽니다 (수 GB).

**A.** 다음을 확인:
1. `MATCH (n) RETURN labels(n)[0], count(*)` 로 노드 수 확인
2. 불필요한 임시 노드 정리: `MATCH (n:TempNode) DETACH DELETE n`
3. 압축 백업: `tar czf backup.tar.gz neo4j.dump`
4. 정기적으로 오래된 백업 삭제 (`find backup/ -mtime +30 -delete`)

### Q8. 두 Neo4j 컨테이너 사이에 데이터를 마이그레이션하려면?

**A.**
```bash
# 1. kp-neo4j → 덤프
docker exec kp-neo4j neo4j-admin database dump neo4j --to-path=/data/dump

# 2. 호스트로 복사
docker cp kp-neo4j:/data/dump/neo4j.dump /tmp/

# 3. serag-neo4j에 복사
docker cp /tmp/neo4j.dump serag-neo4j:/var/lib/neo4j/import/

# 4. serag-neo4j에 로드 (컨테이너 중지 후)
docker compose stop serag-neo4j
docker run --rm -v serag_neo4j_data:/data \
  -v /tmp:/backup neo4j:5.18-community \
  neo4j-admin database load neo4j --from-path=/backup --overwrite-destination=true
docker compose start serag-neo4j
```

---

## 문서 끝

> 본 부록은 [22_neo4j_construction_guide_wsl2.md](./22_neo4j_construction_guide_wsl2.md)의 **설치 단계만 별도로 상세화**한 문서입니다.
> 설치가 완료되면 22번 본문의 §7 (스키마 부트스트랩) 이후 단계를 진행하세요.
