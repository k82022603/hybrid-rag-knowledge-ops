# STORY-102: WSL 메모리 동적 추정 가이드/도구

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-95 |
| **Epic** | - |
| **Status** | Closed - Project Completed (2026-02-18) |
| **Priority** | P2 - Medium |
| **Story Points** | 3 |
| **Assignee** | Infra/DevOps |
| **Sprint** | 09 |
| **Origin** | 아이디어 검토 (2026-02-09) |

---

## User Story

**As a** 시스템 운영자,
**I want** 파일 업로드 전에 필요 메모리를 사전 추정할 수 있어,
**So that** WSL 메모리 설정을 적절히 조정하고 OOM을 방지할 수 있다.

---

## Acceptance Criteria

- [ ] **Given** 파일 크기와 유형이 입력되면, **When** 추정 도구를 실행하면, **Then** 예상 peak 메모리가 출력된다
- [ ] **Given** 현재 WSL 메모리 설정이 부족하면, **When** pre-flight check를 실행하면, **Then** wslconfig 조정 권고가 출력된다
- [ ] **Given** 추정 결과가 나오면, **When** docker-compose 설정에 반영하면, **Then** 컨테이너 메모리 리밋이 적절히 설정된다

---

## Tasks

- [ ] 파일 유형별 메모리 계수 테이블 (MB → peak GB)
- [ ] pre-flight check CLI 스크립트
- [ ] wslconfig 자동 조정 제안 기능
- [ ] docker-compose 메모리 리밋 자동 계산
- [ ] 운영매뉴얼 통합

---

## 기술 노트

### 실측 데이터
| 파일 | 크기 | Peak 메모리 | 비율 |
|------|------|------------|------|
| 79MB PDF | 79MB | 3.2GB | 40.5x |
| 11MB 프레젠테이션 | 11MB | 3.7GB | 336.4x |

### 평가
- **실현 가능성**: High (기존 측정 데이터 기반)
- **ROI**: 중간 (운영 안정성 개선, OOM 방지)
- **리스크**: 낮음 (보수적 추정 + 안전 마진)

---

## 참고 자료

- [운영매뉴얼 v2.0](../../knowledge_service/docs/07_maintenance/)
