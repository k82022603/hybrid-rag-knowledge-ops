# STORY-109: docker-compose.yml ai-service 메모리 설정 현행화

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | - (Jira 이슈 한도 초과) |
| **Epic** | - |
| **Status** | To Do |
| **Priority** | Medium |
| **Story Points** | 1 |
| **Assignee** | Infra |
| **Sprint** | 08 |
| **Origin** | 스탠드업 액션 아이템 (2026-02-09) |

---

## User Story

**As a** 인프라 엔지니어,
**I want** docker-compose.yml의 ai-service 메모리 설정이 실제 운영 데이터 기반으로 현행화되어,
**So that** OOM 방지와 자원 효율성이 보장된다.

---

## Acceptance Criteria

- [ ] **Given** 실측 데이터(peak 9.3GB→2.9GB 임베딩 비활성화)가 있으면, **When** docker-compose.yml을 업데이트하면, **Then** mem_limit/mem_reservation이 적절히 설정된다
- [ ] **Given** 설정이 변경되면, **When** 컨테이너를 재시작하면, **Then** 정상 가동되고 OOM이 발생하지 않는다

---

## Tasks

- [ ] 실측 메모리 프로파일 기반 설정값 도출
- [ ] docker-compose.yml ai-service 메모리 설정 업데이트
- [ ] 운영매뉴얼에 설정 근거 문서화

---

## 참고 자료

- [스탠드업 2026-02-09](../../work_logs/standups/2026/02-February/2026-02-09_11-05.md)
- 임베딩 비활성화 시 peak 2.9GB, 활성화 시 9.3GB
