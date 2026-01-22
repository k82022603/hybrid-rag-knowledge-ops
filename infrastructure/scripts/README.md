# Infrastructure Scripts

백업, 복원, 유지보수를 위한 인프라 스크립트 모음입니다.

## 스크립트 목록

| 스크립트 | 설명 |
|----------|------|
| `backup.sh` | PostgreSQL, Elasticsearch, Neo4j, MinIO 자동 백업 |
| `restore.sh` | 백업 데이터 복원 |
| `backup.cron.example` | Crontab 설정 예시 |

---

## backup.sh - 자동 백업 스크립트

### 기능

- **PostgreSQL**: `pg_dump`를 사용한 SQL 백업 (gzip 압축)
- **Elasticsearch**: Snapshot API를 사용한 스냅샷 생성
- **Neo4j**: APOC 확장을 사용한 Cypher/JSON 내보내기
- **MinIO**: mc (MinIO Client)를 사용한 버킷 미러링

### 사전 요구사항

1. Docker 컨테이너가 실행 중이어야 합니다
2. 환경 변수가 설정되어 있어야 합니다 (`.env` 파일)

### 필수 환경 변수

```bash
# PostgreSQL
DB_PASSWORD=your_password
DB_USERNAME=knowledge
DB_NAME=knowledge

# Neo4j
NEO4J_PASSWORD=your_password
NEO4J_USER=neo4j

# MinIO
MINIO_ACCESS_KEY=your_access_key
MINIO_SECRET_KEY=your_secret_key

# 선택적
BACKUP_DIR=/path/to/backups
BACKUP_RETENTION_DAYS=7
```

### 사용법

```bash
# 전체 백업 실행
./backup.sh

# 특정 서비스만 백업
./backup.sh --postgresql
./backup.sh --elasticsearch
./backup.sh --neo4j
./backup.sh --minio

# 사용자 정의 백업 디렉토리 및 보존 기간
./backup.sh -d /data/backups -r 14

# 도움말
./backup.sh --help
```

### 백업 파일 위치

```
backups/
  YYYY-MM-DD/
    backup_YYYYMMDD_HHMMSS.log       # 백업 로그
    postgresql_YYYYMMDD_HHMMSS.sql.gz  # PostgreSQL 백업
    elasticsearch/
      indices_list.txt               # 인덱스 목록
      all_mappings.json              # 매핑 정보
      snapshot_info.json             # 스냅샷 정보
    neo4j_YYYYMMDD_HHMMSS.tar.gz     # Neo4j 백업
    minio_YYYYMMDD_HHMMSS.tar.gz     # MinIO 백업
```

### 자동 정리

- 기본 7일 이상된 백업 자동 삭제
- `BACKUP_RETENTION_DAYS` 환경 변수로 조정 가능
- `-r` 옵션으로 런타임에 지정 가능

---

## restore.sh - 복원 스크립트

### 사용법

```bash
# PostgreSQL 복원
./restore.sh postgresql ./backups/2026-01-22/postgresql_20260122_020000.sql.gz

# Elasticsearch 복원 (스냅샷 이름 지정)
./restore.sh elasticsearch snapshot_20260122_020000

# Neo4j 복원
./restore.sh neo4j ./backups/2026-01-22/neo4j_20260122_020000.tar.gz

# MinIO 복원
./restore.sh minio ./backups/2026-01-22/minio_20260122_020000.tar.gz

# 도움말
./restore.sh --help
```

### 주의사항

- 복원 시 기존 데이터가 **삭제**됩니다
- 복원 전 확인 프롬프트가 표시됩니다
- 운영 환경에서는 충분한 테스트 후 사용하세요

---

## Cron 설정

### 설치 방법

```bash
# 방법 1: crontab 직접 편집
crontab -e
# 아래 내용 추가:
0 2 * * * /opt/knowledge-platform/infrastructure/scripts/backup.sh >> /var/log/knowledge-backup.log 2>&1

# 방법 2: cron.d에 파일 복사
sudo cp backup.cron.example /etc/cron.d/knowledge-platform-backup
sudo chmod 644 /etc/cron.d/knowledge-platform-backup
```

### 권장 스케줄

| 작업 | 스케줄 | 설명 |
|------|--------|------|
| 일일 전체 백업 | `0 2 * * *` | 매일 새벽 2시 |
| 주간 추가 백업 | `0 3 * * 0` | 일요일 새벽 3시 |
| 로그 정리 | `0 4 1 * *` | 매월 1일 새벽 4시 |

---

## 문제 해결

### 자주 발생하는 문제

1. **컨테이너를 찾을 수 없음**
   ```
   ERROR: PostgreSQL container 'kp-postgresql' is not running
   ```
   - Docker 컨테이너가 실행 중인지 확인: `docker ps`

2. **비밀번호 미설정**
   ```
   ERROR: DB_PASSWORD environment variable is not set
   ```
   - `.env` 파일에 비밀번호가 설정되어 있는지 확인

3. **Elasticsearch 스냅샷 실패**
   - Elasticsearch에 스냅샷 리포지토리가 등록되어 있는지 확인
   - 클러스터 상태 확인: `curl http://localhost:9200/_cluster/health`

4. **Neo4j APOC 오류**
   - Neo4j에 APOC 플러그인이 설치되어 있는지 확인
   - 컨테이너 로그 확인: `docker logs kp-neo4j`

### 로그 확인

```bash
# 최근 백업 로그 확인
tail -100 /var/log/knowledge-backup.log

# 백업 디렉토리의 로그 확인
cat ./backups/YYYY-MM-DD/backup_*.log
```

---

## 참고

- [인프라 상세 설계서](../../knowledge_service/docs/02_design/infrastructure_detailed_design.md)
- [Docker Compose 설정](../docker/docker-compose.yml)
