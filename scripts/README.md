# Scripts - Slack & Monitoring 스크립트 관리

## Slack 메시지 전송

| 스크립트 | 위치 | 용도 |
|---------|------|------|
| `send_slack.sh` | `scripts/` | 핵심 Slack 전송 (서브에이전트용) |
| `slack_channels.conf` | `scripts/` | 채널 ID 설정 |
| `slack-notify.sh` | `.claude/hooks/` | Claude Code 훅 알림 |

### 사용법
```bash
# 서브 에이전트/스크립트에서 Slack 메시지 전송
./scripts/send_slack.sh <channel> <agent_name> <message>

# 채널: dev, standup, alerts, general
./scripts/send_slack.sh dev Backend "작업 완료: STORY-022"
./scripts/send_slack.sh standup 클로드 "스탠드업 시작"
```

### 채널 ID
| 채널 | ID | 약칭 |
|------|-----|------|
| proj-hrkp-dev | C0A9WGCD733 | dev |
| proj-hrkp-standup | C0A9B7HDEUB | standup |
| proj-hrkp-alerts | C0A9WGEVB97 | alerts |
| proj-hrkp-general | C0AABTM716U | general |

---

## ETL 모니터링

| 스크립트 | 위치 | 간격 | Slack | 용도 |
|---------|------|------|-------|------|
| `etl_phase1_monitor.sh` | `knowledge_service/scripts/` | 15분 | dev | Phase 1 (파싱+청킹) |
| `etl_v2_monitor.sh` | `knowledge_service/scripts/` | 15분 | dev | 전체 ETL v2 |
| `etl_monitor_slack.sh` | `scripts/` | - | dev | ETL Slack 통합 |
| `embedding_monitor.sh` | `knowledge_service/scripts/` | 10분 | - | 임베딩 전용 |
| `embedding_monitor_v2.sh` | `knowledge_service/scripts/` | 10분 | - | 임베딩 v2 |

### 모니터 실행/종료
```bash
# 실행 (호스트에서)
nohup bash knowledge_service/scripts/etl_phase1_monitor.sh > /tmp/etl_phase1_monitor.log 2>&1 &

# 실행 중인 모니터 확인
ps aux | grep "etl.*monitor\|embedding.*monitor" | grep -v grep

# 종료
kill <PID>
```

### ETL 실행 (컨테이너 내부)
```bash
# Phase 1: 파싱+청킹 (임베딩 OFF)
docker exec kp-ai-service bash -c "nohup python3 /app/scripts/run_etl_phase1_chunks.py > /tmp/etl_phase1.log 2>&1 &"

# Full ETL: 파싱+청킹+임베딩+엔티티
docker exec kp-ai-service bash -c "nohup python3 /app/scripts/run_etl_full.py > /tmp/etl_full_v2.log 2>&1 &"

# 로그 확인
docker exec kp-ai-service tail -20 /tmp/etl_phase1.log
```

---

## 세션 전환 시 체크리스트

1. `ps aux | grep monitor | grep -v grep` → 이전 모니터 프로세스 확인
2. 불필요한 모니터 kill
3. 필요한 모니터 재시작
4. Slack 첫 보고 확인
