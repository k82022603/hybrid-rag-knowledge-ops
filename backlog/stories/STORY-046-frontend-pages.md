# STORY-046: Frontend 미구현 4개 페이지 구현

## 메타데이터
| 항목 | 내용 |
|------|------|
| **Story ID** | STORY-046 |
| **Jira ID** | SCRUM-38 |
| **Epic** | EPIC-04: Frontend UI |
| **Sprint** | Sprint 02 |
| **Story Points** | 8 |
| **Priority** | High |
| **Status** | Done |
| **Assignee** | Frontend Developer |
| **Created** | 2026-01-26 |

## User Story
**As a** 사용자
**I want** 북마크, 프로필, 관리자, 문서업로드 페이지를 사용
**So that** 시스템의 모든 기능에 접근할 수 있다

## 구현 대상 페이지

### 1. BookmarkPage (`/bookmarks`)
- 북마크된 문서 목록 조회
- 폴더별 분류 (default, important, read-later)
- 북마크 추가/삭제
- 검색 및 필터링

### 2. ProfilePage (`/profile`)
- 사용자 프로필 조회/수정
- 비밀번호 변경
- 활동 이력 조회
- 알림 설정 관리

### 3. AdminPage (`/admin`)
- RequireAdmin 권한 필요
- 사용자 관리 (목록, 역할 변경, 비활성화)
- 시스템 설정 관리
- 감사 로그 조회
- 시스템 통계 대시보드

### 4. DocumentUploadPage (`/upload`)
- 파일 드래그 & 드롭 업로드
- 지원 포맷: PDF, DOCX, PPTX, HWP, MD
- 메타데이터 입력 (프로젝트, 카테고리, 태그)
- 업로드 진행 상태 표시

## 기술 스택
- React 18 + TypeScript
- Tailwind CSS + Headless UI
- React Router v6
- useAuth hook (Keycloak/Direct Login)

## 완료 기준 (DoD)
- [ ] 4개 페이지 컴포넌트 작성 완료
- [ ] 서비스 레이어 (API 연동) 작성
- [ ] App.tsx 라우팅 등록
- [ ] Sidebar 네비게이션 추가
- [ ] 반응형 디자인 적용
- [ ] 설계서 UI 사양 준수

## 관련 스토리
- STORY-040: Frontend Keycloak 연동
- STORY-041: Dashboard UI
- STORY-042: Search UI 컴포넌트
