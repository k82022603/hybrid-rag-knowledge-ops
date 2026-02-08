# STORY-098: [FEAT] Administration 페이지에 Redis Cache Reset 기능 추가

## 메타데이터

| 항목 | 값 |
|------|-----|
| **ID** | STORY-098 |
| **Epic** | EPIC-006 Administration |
| **Status** | To Do |
| **Priority** | Medium |
| **Story Points** | 3 |
| **Assignee** | Backend/Frontend |
| **Sprint** | - |

---

## User Story

**As a** 시스템 관리자,
**I want** Administration 페이지에서 Redis 캐시를 리셋할 수 있길,
**So that** 검색 결과 구조 변경이나 데이터 업데이트 후 캐시를 수동 무효화할 수 있습니다.

---

## Problem Statement

검색 결과 구조 변경, 데이터 재색인 등의 작업 후 Redis 캐시에 이전 결과가 남아있어 수동으로 `docker exec kp-redis redis-cli FLUSHALL`을 실행해야 함. Administration UI에서 클릭 한 번으로 캐시를 리셋할 수 있어야 함.

---

## Acceptance Criteria

- [ ] **Given** Administration 페이지, **When** Cache Reset 버튼 클릭 시, **Then** Redis 캐시가 전체 무효화됨
- [ ] **Given** Cache Reset 요청, **When** 성공 시, **Then** 성공 토스트 메시지 표시 및 삭제된 키 수 표시
- [ ] **Given** Cache Reset 요청, **When** Redis 연결 실패 시, **Then** 에러 메시지 표시
- [ ] **Given** 관리자가 아닌 사용자, **When** Cache Reset 시도 시, **Then** 권한 부족 에러 (403)

---

## Tasks

- [ ] Backend: `POST /api/v1/admin/cache/reset` 엔드포인트 구현
- [ ] Backend: Redis FLUSHALL 또는 선택적 키 패턴 삭제
- [ ] Frontend: Administration 페이지에 Cache 관리 섹션 추가
- [ ] Frontend: Reset 버튼 + 확인 다이얼로그 + 결과 토스트

---

## 기술 노트

### 구현 방향

1. **API 엔드포인트**: `POST /api/v1/admin/cache/reset`
   - 옵션: `pattern` 파라미터로 선택적 삭제 가능 (기본: 전체)
   - Redis `FLUSHALL` 또는 `KEYS pattern` + `DEL`
   - 관리자 권한 필수 (role=admin)

2. **Frontend**: Administration 페이지의 시스템 관리 섹션에 추가
   - 확인 다이얼로그: "정말 캐시를 초기화하시겠습니까?"
   - 성공 시: "캐시가 초기화되었습니다 (N개 키 삭제)"

### 영향 범위
- `knowledge_service/src/app/api/routes/admin.py` - 새 엔드포인트
- `knowledge_service/frontend/src/pages/Administration.tsx` - UI 추가
