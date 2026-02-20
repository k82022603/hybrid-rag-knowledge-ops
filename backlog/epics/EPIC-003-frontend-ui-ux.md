# EPIC-003: Frontend UI/UX

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-40 |
| **Status** | Closed - Project Completed (2026-02-18) |
| **Priority** | High |
| **Owner** | TBD |
| **Target Sprint** | Sprint 3 |
| **Total Story Points** | 18 |

---

## 요약

React 18 + **Tailwind CSS** 기반의 지식 검색 플랫폼 프론트엔드 구현. Keycloak 연동 인증, 대시보드, 채팅 모드 검색, SSE 스트리밍 응답 등 핵심 UI 컴포넌트 개발.

> **전환 공지** (2026-01-25): MUI에서 Tailwind CSS + Headless UI로 전환 결정.
> 마이그레이션 가이드: [MUI to Tailwind 마이그레이션 가이드](../../knowledge_service/docs/05_development/06_mui_to_tailwind_migration.md)

---

## 배경 및 목표

### 배경
- 사용자 친화적인 검색 인터페이스 필요
- 실시간 응답 스트리밍으로 UX 향상
- Keycloak 기반 SSO 인증 연동

### 목표
- 직관적인 채팅 모드 검색 UI 제공
- SSE 스트리밍으로 실시간 응답 표시
- 모바일 반응형 디자인 지원

### 성공 지표
- [ ] Keycloak 로그인/로그아웃 정상 동작
- [ ] 검색 응답 SSE 스트리밍 동작
- [ ] Lighthouse Performance Score >= 80
- [ ] 주요 화면 E2E 테스트 통과

---

## User Stories

| ID | Jira | 제목 | Points | Status | Sprint |
|----|------|------|--------|--------|--------|
| STORY-040 | SCRUM-29 | Frontend Keycloak 연동 | 5 | Review | 3 |
| STORY-041 | SCRUM-30 | Dashboard UI | 5 | To Do | 3 |
| STORY-042 | SCRUM-31 | Search UI 컴포넌트 | 5 | To Do | 3 |
| STORY-043 | SCRUM-32 | SSE 스트리밍 응답 | 3 | To Do | 3 |

---

## 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Frontend Architecture                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                        React 18 + Vite                           │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │   Auth      │  │  Dashboard  │  │   Search    │  │   Admin     │   │
│  │ (Keycloak)  │  │   Page      │  │   Page      │  │   Page      │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                     Shared Components                            │  │
│  │  ┌─────────┐  ┌──────────┐  ┌────────┐  ┌──────────────────┐    │  │
│  │  │ Header  │  │ Sidebar  │  │ Chat   │  │ Source Citation  │    │  │
│  │  └─────────┘  └──────────┘  └────────┘  └──────────────────┘    │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                     State Management (Zustand)                   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                     API Client (Axios + SSE)                     │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 기술 요구사항

### 기술 스택
| 구성요소 | 기술 | 버전 | 비고 |
|----------|------|------|------|
| Framework | React | 18.x | |
| Build Tool | Vite | 5.x | |
| **Styling** | **Tailwind CSS** | **3.4+** | **MUI에서 전환 (2026-01-25)** |
| **UI Components** | **Headless UI** | **2.x** | **접근성 지원** |
| **Icons** | **Heroicons** | **2.x** | **MUI Icons에서 전환** |
| State | Zustand | 4.x | |
| Auth | Keycloak JS | 26.x | |
| Testing | Vitest + Playwright | Latest | |

### 페이지 구성
| 페이지 | 경로 | 설명 |
|--------|------|------|
| Login | /login | Keycloak 리다이렉트 |
| Dashboard | / | 메인 대시보드 |
| Chat Search | /search/chat | 채팅 모드 검색 |
| Keyword Search | /search/keyword | 키워드 검색 |
| Knowledge List | /knowledge | 지식 목록 |
| Admin | /admin | 관리자 설정 |

### 성능 요구사항
| 항목 | 목표 |
|------|------|
| First Contentful Paint | < 1.5초 |
| Time to Interactive | < 3초 |
| Lighthouse Score | >= 80 |

---

## 선행 조건 (Sprint 2 완료 필요)

- [ ] Frontend 프로젝트 골격 생성 (STORY-013)
- [ ] Keycloak Realm/Client 설정 (STORY-012)
- [ ] API Gateway 라우팅 구현 (STORY-021)

---

## 리스크 및 의존성

### 리스크
| 리스크 | 영향 | 대응 |
|--------|------|------|
| SSE 브라우저 호환성 | Low | Polyfill 적용 |
| Keycloak 토큰 만료 | Medium | Silent refresh 구현 |
| 번들 크기 증가 | Low | 코드 스플리팅 |

### 의존성
- [ ] Backend Search API 완료
- [ ] SSE 엔드포인트 구현

---

## 참고 자료

- [Frontend 상세 설계서](../../knowledge_service/docs/02_design/02_frontend_detailed_design.md)
- [UI Storyboard](../../knowledge_service/docs/02_design/ui_storyboard/)
- [Keycloak JS Adapter](https://www.keycloak.org/docs/latest/securing_apps/#_javascript_adapter)
