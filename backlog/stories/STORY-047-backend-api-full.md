# STORY-047: Backend API 32개 전체 구현

## 메타데이터
| 항목 | 내용 |
|------|------|
| **Story ID** | STORY-047 |
| **Epic** | EPIC-03: Backend API |
| **Sprint** | Sprint 02 |
| **Story Points** | 13 |
| **Priority** | High |
| **Status** | In Progress |
| **Assignee** | Backend Developer |
| **Created** | 2026-01-26 |

## User Story
**As a** 프론트엔드/AI 서비스 개발자
**I want** 모든 백엔드 API가 구현되어 있길
**So that** 프론트엔드와 AI 서비스가 완전한 기능을 제공할 수 있다

## API 구현 목록 (32개)

### Knowledge API (8개)
| # | Method | Path | 설명 |
|---|--------|------|------|
| 1 | POST | /api/v1/documents | 문서 업로드 |
| 2 | GET | /api/v1/documents | 문서 목록 조회 |
| 3 | GET | /api/v1/documents/{id} | 문서 상세 조회 |
| 4 | DELETE | /api/v1/documents/{id} | 문서 삭제 |
| 5 | GET | /api/v1/documents/{id}/status | 문서 처리 상태 |
| 6 | GET | /api/v1/documents/{id}/chunks | 문서 청크 조회 |
| 7 | GET | /api/v1/categories | 카테고리 목록 |
| 8 | GET | /api/v1/projects | 프로젝트 목록 |

### Search API (6개)
| # | Method | Path | 설명 |
|---|--------|------|------|
| 9 | POST | /api/v1/search | 하이브리드 검색 |
| 10 | POST | /api/v1/search/chat | 대화형 검색 |
| 11 | GET | /api/v1/search/chat/stream | SSE 스트리밍 |
| 12 | GET | /api/v1/search/history | 검색 이력 |
| 13 | GET | /api/v1/search/suggestions | 검색 자동완성 |
| 14 | POST | /api/v1/search/feedback | 검색 피드백 |

### Users API (5개)
| # | Method | Path | 설명 |
|---|--------|------|------|
| 15 | GET | /api/v1/users/me | 내 프로필 조회 |
| 16 | PUT | /api/v1/users/me | 프로필 수정 |
| 17 | PUT | /api/v1/users/me/password | 비밀번호 변경 |
| 18 | GET | /api/v1/users/me/activities | 활동 이력 |
| 19 | GET/PUT | /api/v1/users/me/notifications | 알림 설정 |

### Bookmarks API (4개)
| # | Method | Path | 설명 |
|---|--------|------|------|
| 20 | GET | /api/v1/bookmarks | 북마크 목록 |
| 21 | POST | /api/v1/bookmarks | 북마크 추가 |
| 22 | DELETE | /api/v1/bookmarks/{id} | 북마크 삭제 |
| 23 | PUT | /api/v1/bookmarks/{id} | 북마크 수정 |

### Dashboard API (3개)
| # | Method | Path | 설명 |
|---|--------|------|------|
| 24 | GET | /api/v1/dashboard/stats | 통계 요약 |
| 25 | GET | /api/v1/dashboard/recent | 최근 활동 |
| 26 | GET | /api/v1/dashboard/popular | 인기 검색 |

### Export API (2개)
| # | Method | Path | 설명 |
|---|--------|------|------|
| 27 | POST | /api/v1/export/search | 검색결과 내보내기 |
| 28 | GET | /api/v1/export/document/{id} | 문서 내보내기 |

### Admin API (4개)
| # | Method | Path | 설명 |
|---|--------|------|------|
| 29 | GET | /api/v1/admin/users | 사용자 관리 목록 |
| 30 | PUT | /api/v1/admin/users/{id}/roles | 역할 변경 |
| 31 | GET | /api/v1/admin/system | 시스템 설정 |
| 32 | GET | /api/v1/admin/audit-logs | 감사 로그 |

## 기술 스택
- Java 17 + SpringBoot 3.x
- Spring WebFlux (R2DBC Reactive)
- Mono/Flux 반응형 패턴
- PostgreSQL (R2DBC)

## 아키텍처 레이어
```
Controller → Service → Repository → Entity
                    → DTO (Request/Response)
```

## 완료 기준 (DoD)
- [ ] Entity 클래스 전체 구현
- [ ] Repository 인터페이스 전체 구현
- [ ] Service 클래스 전체 구현
- [ ] Controller 클래스 전체 구현
- [ ] DTO (Request/Response) 전체 구현
- [ ] Gradle 빌드 성공
- [ ] 설계서 API 사양 준수

## 관련 스토리
- STORY-001: Document Upload API (일부 구현)
- STORY-024: Direct Login API (완료)
- STORY-044: Backend Search Service
