# Sprint 05: 품질 완성 + 프로덕션 준비

## 스프린트 정보

| 항목 | 값 |
|------|-----|
| **기간** | 2026-01-30 ~ 2026-02-07 (1주) |
| **Velocity (계획)** | 26 pts (7 Stories) |
| **Velocity (실제)** | - |
| **Status** | planned |
| **Jira Sprint ID** | - |
| **근거** | Sprint 04 미완료 이월 + Known Issues 해결 |

---

## 스프린트 목표

> **프로덕션 준비도 75% → 90% 달성 + 품질 게이트 완성**

핵심 목표:
1. RAG 품질 측정 체계 확립 (RAGAS 통합)
2. Frontend 테스트 커버리지 확장 (25% → 60%)
3. 파이프라인 안정성 강화 (타임아웃, Circuit Breaker)
4. Docker E2E 100% 달성 (Keycloak realm 설정)
5. 접근성 WCAG 2.1 AA 준수

---

## Sprint 04 이월 항목

| Story | SP | 담당 | 이월 사유 |
|-------|:--:|------|----------|
| STORY-058 | 5 | RAG | Sprint 04 범위 초과 |
| STORY-059 | 5 | Frontend | Sprint 04 범위 초과 |
| STORY-060 | 3 | RAG | Sprint 04 범위 초과 |
| STORY-061 | 3 | RAG | Sprint 04 범위 초과 |
| STORY-062 | 2 | Frontend | Sprint 04 범위 초과 |

**이월 합계**: 18 SP

---

## 백로그

### P0 - Critical (Day 1-2)

| Priority | ID | Jira | 제목 | Points | Assignee | Status |
|----------|-----|------|------|--------|----------|--------|
| P0 | STORY-064 | SCRUM-64 | Keycloak Realm 설정 (Docker E2E 100%) | 3 | Infra | **Done** |
| P0 | STORY-058 | SCRUM-48 | RAGAS 평가 프레임워크 통합 | 5 | RAG | **Done** |

**소계**: 8 pts (2 Stories)

### P1 - High (Day 3-4)

| Priority | ID | Jira | 제목 | Points | Assignee | Status |
|----------|-----|------|------|--------|----------|--------|
| P1 | STORY-061 | SCRUM-51 | 파이프라인 타임아웃 + Circuit Breaker | 3 | RAG | **Done** |
| P1 | STORY-059 | SCRUM-49 | Frontend 테스트 커버리지 확장 (25%→60%) | 5 | Frontend | **Done** |
| P1 | STORY-060 | SCRUM-50 | Planner 전략 유효화 + 검색 캐싱 | 3 | RAG | **Done** |

**소계**: 11 pts (3 Stories)

### P2 - Medium (Day 5)

| Priority | ID | Jira | 제목 | Points | Assignee | Status |
|----------|-----|------|------|--------|----------|--------|
| P2 | STORY-062 | SCRUM-52 | 접근성 WCAG 2.1 AA 보완 | 2 | Frontend | **Done** |
| P2 | STORY-063 | SCRUM-53 | Docling Docker 이미지 최적화 (8.5GB→?) | 5 | Infra/ETL | **Done** |

**소계**: 7 pts (2 Stories)

---

## 신규 Story

### STORY-064: Keycloak Realm 설정

**목적**: Docker E2E 17건 실패 해결 (401 Unauthorized)

**Acceptance Criteria**:
- [ ] \`knowledge-platform\` realm 자동 생성
- [ ] 테스트 사용자 계정 등록 (testuser/password)
- [ ] realm-export.json 작성 및 Docker Compose 연동
- [ ] Docker E2E 98/98 (100%) 달성

**담당**: Infra
**SP**: 3

---

## 일일 계획

### Day 1 (2026-01-30)

| 시간 | 작업 | 담당 |
|------|------|------|
| 09:00 | Sprint 05 킥오프 미팅 | PM |
| 09:30 | STORY-064 착수: Keycloak realm 설계 | Infra |
| 10:00 | STORY-058 착수: ragas 패키지 연동 | RAG |
| 14:00 | STORY-064: realm-export.json 작성 | Infra |
| 16:00 | Docker E2E 재검증 | QA |

### Day 2 (2026-01-31)

| 시간 | 작업 | 담당 |
|------|------|------|
| 09:00 | 스탠드업 미팅 | PM |
| 09:30 | STORY-064 완료: Docker E2E 100% 확인 | Infra/QA |
| 10:00 | STORY-058: faithfulness/relevancy 메트릭 구현 | RAG |
| 14:00 | STORY-058: Ground truth 데이터셋 생성 | RAG |
| 16:00 | P0 완료 확인 | PM |

### Day 3 (2026-02-03)

| 시간 | 작업 | 담당 |
|------|------|------|
| 09:00 | 스탠드업 미팅 | PM |
| 09:30 | STORY-058 완료: 평가 보고서 생성 | RAG |
| 10:00 | STORY-061 착수: timeout 설정 | RAG |
| 14:00 | STORY-059 착수: Frontend 테스트 확장 | Frontend |
| 16:00 | STORY-061: Circuit Breaker 구현 | RAG |

### Day 4 (2026-02-04)

| 시간 | 작업 | 담당 |
|------|------|------|
| 09:00 | 스탠드업 미팅 | PM |
| 09:30 | STORY-061 완료: 장애 시나리오 테스트 | RAG/QA |
| 10:00 | STORY-059: 컴포넌트 테스트 작성 | Frontend |
| 14:00 | STORY-060 착수: 캐싱 전략 구현 | RAG |
| 16:00 | STORY-059 완료: 커버리지 60% 달성 | Frontend |

### Day 5 (2026-02-05)

| 시간 | 작업 | 담당 |
|------|------|------|
| 09:00 | 스탠드업 미팅 | PM |
| 09:30 | STORY-060 완료: 캐시 히트율 검증 | RAG |
| 10:00 | STORY-062 착수: 접근성 감사 | Frontend |
| 14:00 | STORY-063 착수: Docling 이미지 최적화 | Infra/ETL |
| 16:00 | Sprint 리뷰 준비 | PM |

### Day 6 (2026-02-06) - Buffer

| 시간 | 작업 | 담당 |
|------|------|------|
| 09:00 | P2 잔여 작업 완료 | All |
| 14:00 | 통합 테스트 | QA |
| 16:00 | Sprint 리뷰 & 회고 | PM |

---

## 기술 의존성

### Keycloak Realm 설정
- [ ] realm-export.json 템플릿 작성
- [ ] Docker Compose 볼륨 마운트 설정
- [ ] 테스트 사용자 자격증명 환경변수화

### RAGAS 통합
- [x] ragas 패키지 설치 확인 (pyproject.toml)
- [ ] Ground truth QA 쌍 30개+ 준비
- [ ] OpenAI API 키 설정 (RAGAS 평가용)

### Circuit Breaker
- [ ] resilience4j 또는 tenacity 선정
- [ ] 장애 시나리오 정의 (타임아웃, 연결 실패)

### Frontend 테스트
- [ ] Testing Library + Vitest 설정 확인
- [ ] MSW 모킹 패턴 표준화

---

## Definition of Done

각 Story 완료 기준:
- [ ] 모든 Acceptance Criteria 충족
- [ ] 단위 테스트 작성 (커버리지 80%+)
- [ ] 코드 리뷰 완료 (TechLead)
- [ ] 기존 테스트 회귀 없음 (CI 통과)
- [ ] 문서 업데이트
- [ ] Jira 상태 Done 전환
- [ ] Slack 완료 알림

---

## 리스크 및 대응

| 유형 | 설명 | 영향 | 대응 | 상태 |
|------|------|------|------|------|
| Risk | Keycloak realm 설정 복잡성 | High | 기존 realm-export 참조 | Open |
| Risk | RAGAS 점수 목표 미달 | Medium | 프롬프트 튜닝 | Open |
| Risk | Frontend 커버리지 60% 미달 | Medium | 핵심 컴포넌트 집중 | Open |
| Risk | Docling 이미지 최적화 한계 | Low | Multi-stage 빌드 | Open |

---

## 메트릭 목표

| 메트릭 | 현재 | 목표 | 측정 방법 |
|--------|------|------|-----------|
| 프로덕션 준비도 | 75% | 90% | 팀 리뷰 |
| Docker E2E | 82.7% | 100% | pytest |
| Contract Tests | 121 | 121+ | pytest |
| Frontend 커버리지 | 25% | 60%+ | vitest |
| RAGAS Faithfulness | - | ≥ 0.7 | ragas |
| RAGAS Relevancy | - | ≥ 0.7 | ragas |

---

## 산출물

### AI Service
\`\`\`
ai_service/src/
├── evaluation/
│   ├── ragas_evaluator.py        # STORY-058
│   └── ground_truth/             # STORY-058
│       └── qa_pairs.json
├── services/
│   └── cache_service.py          # STORY-060
└── utils/
    └── circuit_breaker.py        # STORY-061
\`\`\`

### Frontend
\`\`\`
frontend/src/
├── __tests__/
│   ├── components/               # STORY-059
│   └── hooks/                    # STORY-059
└── accessibility/
    └── a11y-report.md            # STORY-062
\`\`\`

### Infrastructure
\`\`\`
infrastructure/
├── docker/
│   └── keycloak/
│       └── realm-export.json     # STORY-064
└── docling/
    └── Dockerfile.optimized      # STORY-063
\`\`\`

---

## 참고 자료

- [Sprint 04 작업일지](../../work_logs/daily_logs/2026/01-January/2026-01-29.md)
- [Sprint 04 세션로그](../../work_logs/session_logs/2026/01-January/2026-01-29_sprint04_day5_parallel.md)
- [ADR-001 직렬화 전략](../../knowledge_service/docs/02_design/adr/ADR-001-serialization-strategy.md)
- [ADR-002 검색 API 인증](../../knowledge_service/docs/02_design/adr/ADR-002-search-api-authentication.md)
- [ADR-003 Auth 보안](../../knowledge_service/docs/02_design/adr/ADR-003-auth-endpoint-security.md)
