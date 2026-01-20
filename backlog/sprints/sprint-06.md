# Sprint 06: Deployment + Documentation

## 스프린트 정보

| 항목 | 값 |
|------|-----|
| **기간** | 2026-03-31 ~ 2026-04-11 (2주) |
| **Velocity (계획)** | 21 pts |
| **Velocity (실제)** | - |
| **Status** | planned |
| **Jira Sprint ID** | 40 |

---

## 스프린트 목표

> **Staging/Production 배포 + 운영 문서화 + 기술 이전**

핵심 목표:
1. Staging 환경 배포 및 2일 이상 안정성 검증
2. Production Blue-Green 배포 완료
3. 운영 가이드 및 장애 대응 매뉴얼 작성
4. 사용자 매뉴얼 및 교육 자료 준비
5. 기술 이전 및 인수인계 완료

---

## 선행 조건

Sprint 5 완료 항목 (필수):
- [ ] Ragas 평가 파이프라인 (STORY-060)
- [ ] 검색 품질 평가 (STORY-061)
- [ ] 성능 부하 테스트 (STORY-062)
- [ ] 최적화 및 튜닝 (STORY-063)
- [ ] 보안 취약점 스캔 (STORY-064)
- [ ] 품질 게이트 자동화 (STORY-065)

**품질 게이트 통과 필수**:
- [ ] Faithfulness >= 0.9
- [ ] P95 Latency < 3초
- [ ] Critical 보안 취약점 0개

---

## 백로그

### Epic 006: Deployment & Documentation (21 pts)

| Priority | ID | Jira | 제목 | Points | Assignee | Status |
|----------|-----|------|------|--------|----------|--------|
| P0 | STORY-070 | SCRUM-71 | Staging 환경 배포 | 5 | DevOps | To Do |
| P0 | STORY-071 | SCRUM-72 | Production 배포 | 5 | DevOps | To Do |
| P0 | STORY-072 | SCRUM-73 | 운영 문서 작성 | 5 | TechLead | To Do |
| P1 | STORY-073 | SCRUM-74 | 사용자 매뉴얼 | 3 | TechLead | To Do |
| P1 | STORY-074 | SCRUM-75 | 기술 이전 및 교육 | 3 | All | To Do |

### Stretch (여유 시 추가)

| ID | 제목 | Points |
|----|------|--------|
| - | 동영상 교육 자료 제작 | 5 |
| - | API 클라이언트 SDK | 3 |
| - | 관리자 대시보드 고도화 | 3 |

---

## 기술 의존성 (사전 준비)

### Staging 환경
- [ ] Docker 호스트 서버 준비
- [ ] 네트워크 설정
- [ ] SSL 인증서 발급

### Production 환경
- [ ] 운영 서버 준비
- [ ] 로드밸런서 설정
- [ ] DNS 설정
- [ ] 백업 스토리지

---

## 일일 계획

### Week 1

#### Day 1 (03-31, Mon)
- [ ] 스프린트 킥오프 미팅
- [ ] STORY-070 착수: Staging 환경 준비
- [ ] 배포 체크리스트 최종 검토

#### Day 2 (04-01, Tue)
- [ ] STORY-070: Docker 이미지 배포
- [ ] STORY-070: 데이터 마이그레이션

#### Day 3 (04-02, Wed)
- [ ] STORY-070: 스모크 테스트
- [ ] STORY-070: Staging 모니터링 설정

#### Day 4 (04-03, Thu)
- [ ] STORY-070: Staging 안정성 검증 (Day 1)
- [ ] STORY-072 착수: 시스템 아키텍처 문서

#### Day 5 (04-04, Fri)
- [ ] STORY-070: Staging 안정성 검증 (Day 2)
- [ ] STORY-070 완료
- [ ] Week 1 리뷰

### Week 2

#### Day 6 (04-07, Mon)
- [ ] STORY-071 착수: Production 환경 준비
- [ ] STORY-072: 운영 가이드 작성

#### Day 7 (04-08, Tue)
- [ ] STORY-071: Blue 환경 배포
- [ ] STORY-072: 장애 대응 매뉴얼

#### Day 8 (04-09, Wed)
- [ ] STORY-071: Green 전환 (Traffic switch)
- [ ] STORY-072: 백업/복구 절차
- [ ] STORY-073 착수: 사용자 매뉴얼

#### Day 9 (04-10, Thu)
- [ ] STORY-071: Production 모니터링
- [ ] STORY-072, 073 완료
- [ ] STORY-074 착수: 기술 이전 세션

#### Day 10 (04-11, Fri)
- [ ] STORY-071 완료
- [ ] STORY-074: 운영자 교육
- [ ] 프로젝트 종료 보고서
- [ ] 최종 스프린트 리뷰 & 회고

---

## Definition of Done

각 Story 완료 기준:
- [ ] 모든 Acceptance Criteria 충족
- [ ] 문서 리뷰 완료
- [ ] 이해관계자 승인
- [ ] 인수인계 체크리스트 완료

---

## 리스크 및 블로커

| 유형 | 설명 | 영향 | 대응 | 상태 |
|------|------|------|------|------|
| Risk | 배포 실패 | Critical | 롤백 계획 준비 | Open |
| Risk | 문서 누락 | Medium | 체크리스트 검토 | Open |
| Risk | 교육 시간 부족 | Low | 동영상 자료 | Open |
| Blocker | 품질 게이트 미통과 | Critical | Sprint 5 재작업 | Monitoring |

---

## 산출물

### 배포 스크립트
```
scripts/
├── deploy/
│   ├── deploy-staging.sh           # STORY-070
│   ├── deploy-production.sh        # STORY-071
│   ├── rollback.sh
│   └── healthcheck.sh
└── migration/
    ├── migrate-data.sh
    └── backup-db.sh
```

### 운영 문서
```
docs/operations/
├── architecture/
│   └── system-architecture.md      # STORY-072
├── guides/
│   ├── operations-guide.md
│   ├── troubleshooting.md
│   └── monitoring-guide.md
├── procedures/
│   ├── incident-response.md
│   └── backup-recovery.md
└── runbooks/
    ├── deployment-runbook.md
    └── maintenance-runbook.md
```

### 사용자 문서
```
docs/user/
├── quick-start.md                  # STORY-073
├── user-manual.md
├── faq.md
└── tutorials/
    ├── search-tutorial.md
    └── admin-tutorial.md
```

### 교육 자료
```
docs/training/
├── presentations/
│   ├── system-overview.pptx        # STORY-074
│   ├── user-training.pptx
│   └── admin-training.pptx
└── hands-on/
    ├── lab-exercises.md
    └── demo-scripts.md
```

---

## 배포 체크리스트

### 사전 준비 (배포 3일 전)
- [ ] 모든 테스트 통과 (Unit, Integration, E2E)
- [ ] 품질 게이트 통과 (Ragas, 성능, 보안)
- [ ] 배포 스크립트 검증 (Staging에서 테스트)
- [ ] 롤백 계획 문서화
- [ ] 배포 시간 공지 (최소 24시간 전)

### 배포 당일
- [ ] 데이터베이스 백업 완료
- [ ] 모니터링 대시보드 준비
- [ ] 온콜 담당자 지정
- [ ] 커뮤니케이션 채널 확인

### 배포 실행
- [ ] Docker 이미지 Pull
- [ ] 환경 변수 확인
- [ ] 컨테이너 순차 시작
- [ ] 헬스체크 통과
- [ ] 스모크 테스트

### 배포 후 (30분간)
- [ ] 에러 로그 확인
- [ ] 성능 지표 확인
- [ ] 사용자 접속 확인
- [ ] 배포 완료 공지

### 롤백 트리거
- [ ] 에러율 > 5%
- [ ] P95 지연시간 > 10초
- [ ] 핵심 기능 장애

---

## 문서 체크리스트

### 운영 문서 (STORY-072)
- [ ] 시스템 아키텍처 다이어그램
- [ ] 컴포넌트별 설명
- [ ] 네트워크 구성도
- [ ] 인프라 구성 상세
- [ ] 운영 절차 (시작/정지/재시작)
- [ ] 로그 위치 및 분석 방법
- [ ] 메트릭 및 알림 설명
- [ ] 장애 유형별 대응 절차
- [ ] 에스컬레이션 프로세스
- [ ] 백업 주기 및 방법
- [ ] 복구 절차 (RTO/RPO 명시)

### 사용자 문서 (STORY-073)
- [ ] Quick Start (5분 안에 시작)
- [ ] 기능별 상세 설명
- [ ] 스크린샷 포함
- [ ] FAQ (최소 20개)
- [ ] 문제 해결 가이드

### 교육 자료 (STORY-074)
- [ ] 시스템 개요 PPT
- [ ] 사용자 교육 PPT
- [ ] 관리자 교육 PPT
- [ ] 실습 가이드
- [ ] 데모 시나리오

---

## 메트릭 목표

| 메트릭 | 목표 | 측정 방법 |
|--------|------|-----------|
| Staging 안정성 | 2일 무장애 | 모니터링 |
| Production 배포 | 1시간 이내 | 배포 시간 |
| 롤백 시간 | 5분 이내 | 테스트 |
| 문서 완성도 | 100% | 체크리스트 |

---

## 스프린트 리뷰

### 완료된 항목
- (스프린트 종료 후 작성)

### 미완료 항목
- (스프린트 종료 후 작성)

### 데모 노트
- (스프린트 종료 후 작성)

---

## 회고 (Retrospective)

### Keep (계속할 것)
-

### Problem (문제점)
-

### Try (시도할 것)
-

---

## 프로젝트 종료 체크리스트

- [ ] 모든 Sprint Story 완료
- [ ] Production 안정 운영 확인
- [ ] 운영 문서 인수인계 완료
- [ ] 사용자 교육 완료
- [ ] 종료 보고서 작성
- [ ] 레슨 런드 정리
- [ ] 소스 코드 아카이빙
- [ ] 프로젝트 회고 완료

---

## 참고 자료

- [EPIC-006: Deployment & Documentation](../epics/EPIC-006-deployment-documentation.md)
- [스프린트 실행 계획서](../../docs/02_스프린트_실행_계획서.md)
- [인프라 상세 설계서](../../knowledge_service/docs/02_design/infrastructure_detailed_design.md)
- [Blue-Green Deployment](https://martinfowler.com/bliki/BlueGreenDeployment.html)
