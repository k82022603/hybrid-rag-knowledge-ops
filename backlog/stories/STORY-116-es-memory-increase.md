# STORY-116: ES 메모리 512MB → 1GB 증설

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | - |
| **Epic** | 인프라 안정성 |
| **Status** | To Do |
| **Priority** | P1 |
| **Story Points** | 1 |
| **Assignee** | Infra |
| **Sprint** | Sprint 09 |

---

## Acceptance Criteria

- [ ] `docker-compose.yml` ES 메모리 제한 512MB → 1GB 변경
- [ ] ES_JAVA_OPTS heap 설정 조정 (-Xms512m -Xmx512m → -Xms1g -Xmx1g)
- [ ] 변경 후 ES 컨테이너 정상 기동 확인
- [ ] 96K 청크 인덱스 쿼리 안정성 확인

---

## Tasks

- [ ] `docker-compose.yml` 수정
- [ ] ES 환경변수 `ES_JAVA_OPTS` 업데이트
- [ ] 재시작 후 안정성 확인

---

## 기술 노트

```yaml
elasticsearch:
  environment:
    - ES_JAVA_OPTS=-Xms1g -Xmx1g
  mem_limit: 2g
```

---

## 의존성

- **선행**: 없음
- **관련**: STORY-112 Phase 3 실행 시 인덱싱 부하 대비
