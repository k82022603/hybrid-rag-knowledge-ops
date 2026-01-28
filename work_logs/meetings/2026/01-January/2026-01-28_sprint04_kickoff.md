# Sprint 04 킥오프 미팅

**날짜**: 2026-01-28
**시간**: 킥오프 미팅
**채널**: #proj-hrkp-standup
**유형**: Sprint Kickoff

---

## 참석자

| Agent | 역할 | 상태 |
|-------|------|------|
| PM | Product Manager | ✅ 참석 |
| TechLead | Technical Lead | ✅ 참석 |
| Backend | Backend Developer | ✅ 참석 |
| Frontend | Frontend Developer | ✅ 참석 |
| RAG | ML/RAG Engineer | ✅ 참석 |
| QA | QA Engineer | ✅ 참석 |
| DevOps | DevOps Engineer | ✅ 참석 |
| Infra | Infrastructure Engineer | ✅ 참석 |

---

## 스프린트 개요

| 항목 | 값 |
|------|-----|
| **스프린트** | Sprint 04: Sprint 03 보완 + 품질 강화 |
| **기간** | 2026-01-29 ~ (2주) |
| **Velocity (계획)** | 52 pts (13 Stories) |
| **목표** | 프로덕션 준비도 65% → 85% 달성 |

### 핵심 목표

1. SSE 프로토콜 수정 (EventSource GET → fetch+ReadableStream POST)
2. RAG 파이프라인 통합 (ai_service ↔ knowledge_service 연결)
3. 보안 강화 (JWT Secret, 입력 검증, 기본 자격증명 제거)
4. 서비스 간 통합/보안 테스트 확립
5. RAGAS 평가 프레임워크 통합

---

## 에이전트별 Sprint 04 계획

### PM (Product Manager)

- Sprint 04 전체 조율 및 진행 관리
- 13개 스토리 Jira 동기화 완료 (SCRUM-40 ~ SCRUM-52)
- 일일 스탠드업 진행, 블로커 해소
- 리스크: SSE 전환 회귀, 파이프라인 통합 성능

### TechLead (Technical Lead)

- Sprint 03 리뷰에서 도출된 기술 부채 16건 → 8건 이하 목표
- 코드 리뷰 집중: SSE 프로토콜, RAG 파이프라인 통합, 보안 설정
- 아키텍처 검증: ai_service ↔ knowledge_service 통신 방식

### Backend (1 Story, 3pts)

| Jira | Story | Points | 내용 |
|------|-------|--------|------|
| SCRUM-43 | STORY-053 | 3 | 보안 강화 (JWT Secret, 입력 검증, 기본 자격증명 제거) |

- JWT Secret 환경변수화 (하드코딩 제거)
- Spring Security 입력 검증 패턴 적용
- 기본 자격증명(admin/admin) 제거

### Frontend (4 Stories, 15pts)

| Jira | Story | Points | 내용 |
|------|-------|--------|------|
| SCRUM-40 | STORY-050 | 5 | SSE 프로토콜 수정 (fetch+ReadableStream 전환) |
| SCRUM-46 | STORY-056 | 3 | ErrorBoundary + 성능 최적화 |
| SCRUM-49 | STORY-059 | 5 | Frontend 테스트 커버리지 25%→60% |
| SCRUM-52 | STORY-062 | 2 | 접근성 (WCAG 2.1 AA) 보완 |

- Week 1: SSE 프로토콜 전환 (fetch+ReadableStream)
- Week 2: ErrorBoundary, 테스트 확장, 접근성 보완

### RAG (6 Stories, 24pts)

| Jira | Story | Points | 내용 |
|------|-------|--------|------|
| SCRUM-41 | STORY-051 | 8 | RAG 파이프라인 통합 (ai_service ↔ knowledge_service) |
| SCRUM-42 | STORY-052 | 2 | Reranker async 전환 (asyncio.to_thread) |
| SCRUM-47 | STORY-057 | 5 | Generator 대화이력 전달 + 진정한 스트리밍 |
| SCRUM-48 | STORY-058 | 5 | RAGAS 평가 프레임워크 통합 |
| SCRUM-50 | STORY-060 | 3 | Planner 전략 유효화 + 검색 캐싱 |
| SCRUM-51 | STORY-061 | 3 | 파이프라인 타임아웃 + Circuit Breaker |

- Week 1: 파이프라인 통합 (STORY-051) + Reranker async (STORY-052)
- Week 2: 스트리밍/대화이력 + RAGAS + 캐싱 + 장애 대응

### QA (2 Stories, 8pts)

| Jira | Story | Points | 내용 |
|------|-------|--------|------|
| SCRUM-44 | STORY-054 | 5 | 서비스 간 통합 테스트 (Contract Test) |
| SCRUM-45 | STORY-055 | 3 | 보안 테스트 (XSS, SQL Injection, Auth) |

- Backend ↔ AI Service ↔ Knowledge Service 계약 테스트
- OWASP Top 10 기반 보안 테스트

### DevOps

- Sprint 03 CI/CD 감사 결과 기반 개선
- GitHub Actions 워크플로우 최적화
- 빌드/배포 파이프라인 안정화

### Infra

- DEV/STAGE/PROD 환경 분리 준비
- Docker Compose 프로파일 정리
- JWT Secret Docker Secret 방식 전환 지원

---

## 워크로드 분배

| Agent | Stories | Points | 비중 |
|-------|---------|--------|------|
| RAG | 6 | 24 | 46% |
| Frontend | 4 | 15 | 29% |
| QA | 2 | 8 | 15% |
| Backend | 1 | 3 | 6% |
| **합계** | **13** | **52** | **100%** (지원: TechLead, DevOps, Infra) |

---

## 일정 계획

### Week 1 (P0 Critical, 18pts)

| Day | 주요 활동 |
|-----|----------|
| Day 1 | STORY-050 착수 (SSE 설계), STORY-051 착수 (파이프라인 아키텍처), STORY-053 착수 (JWT) |
| Day 2 | SSE 구현, RetrieverNode↔HybridRetriever 연결, Reranker async (STORY-052) |
| Day 3 | useSearchChat 리팩토링, LLM Service 어댑터, STORY-052 완료 |
| Day 4 | STORY-050 완료, Planner→Retriever→Generator 연결, STORY-053 완료 |
| Day 5 | STORY-051 완료 (E2E 파이프라인), Week 1 리뷰 |

### Week 2 (P1 High + P2 Medium, 34pts)

| Day | 주요 활동 |
|-----|----------|
| Day 6 | STORY-054 착수 (Contract Test), STORY-056 착수, STORY-057 착수 |
| Day 7 | STORY-055 착수 (보안 테스트), 토큰 스트리밍 구현 |
| Day 8 | STORY-054 완료, STORY-058 착수 (RAGAS), ErrorBoundary 최적화 |
| Day 9 | STORY-056 완료, STORY-057 완료, RAGAS 메트릭 연동 |
| Day 10 | STORY-058 완료, P2 착수, 전체 통합 검증, 스프린트 리뷰 |

---

## 리스크 및 대응

| 리스크 | 영향 | 대응 |
|--------|------|------|
| SSE 전환 시 기존 UI 회귀 | High | 기존 useSearchChat wrapper 유지, 회귀 테스트 |
| 파이프라인 통합 시 성능 저하 | High | 벤치마크 테스트 선행 |
| JWT Secret 노출 | Critical | 환경변수 강제, Docker 프로파일 수정 |
| RAGAS 점수 목표 미달 | Medium | 프롬프트 튜닝 + few-shot 예시 |
| P2 Stories 미완료 | Low | Sprint 05로 이월 가능 |

---

## 메트릭 목표

| 메트릭 | 현재 | 목표 |
|--------|------|------|
| 프로덕션 준비도 | 65% | 85% |
| 기술 부채 | 16건 | < 8건 |
| 테스트 커버리지 (Frontend) | 25-30% | 60%+ |
| 보안 취약점 | 2건 | 0건 |
| RAG 파이프라인 통합 | 미연결 | 완전 통합 |
| RAGAS Faithfulness | 미측정 | ≥ 0.7 |
| RAGAS Relevancy | 미측정 | ≥ 0.7 |

---

## 액션 아이템

| # | 액션 | 담당 | 기한 |
|---|------|------|------|
| 1 | fetch+ReadableStream 라이브러리 선정 | Frontend | Day 1 |
| 2 | ai_service ↔ knowledge_service HTTP 통신 방식 확정 | RAG + TechLead | Day 1 |
| 3 | JWT Secret 환경변수 주입 방식 확정 | Backend + Infra | Day 1 |
| 4 | ragas 패키지 호환성 확인 | RAG | Day 6 |
| 5 | Ground truth 데이터셋 준비 (30+ QA 쌍) | RAG + QA | Day 6 |

---

## 참고 자료

- [Sprint 03 완료 리뷰](./2026-01-28_sprint03_completion_review.md)
- [DevOps 파이프라인 감사](./2026-01-28_devops_pipeline_audit.md)
- [Sprint 04 백로그](../../backlog/sprints/sprint-04.md)
- [상세 설계서 v2.4](../../knowledge_service/docs/02_design/hybrid_rag_platform_detailed_design.md)
