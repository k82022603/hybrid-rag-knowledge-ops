# Sprint 03 기술 부채 (Tech Debt)

> **출처**: Sprint 03 Day 1 TechLead 코드 리뷰 (2026-01-27)
> **리뷰 보고서**: `knowledge_service/docs/results/sprint03_day1_code_review.md`

---

## TECH-DEBT-001: Neo4j 엔티티 저장 전략 패턴 리팩토링

| 항목 | 값 |
|------|-----|
| **Story** | STORY-006 |
| **파일** | `knowledge_service/src/app/storage/neo4j_storage.py` L275-339 |
| **등급** | Medium |
| **유형** | 리팩토링 |
| **대상 Sprint** | Sprint 04 |

**현상**: `_save_entities_by_label`에서 라벨별 Cypher 분기가 4개 if/elif/else 체인으로 구현됨

**개선**: 전략 패턴 또는 딕셔너리 매핑으로 리팩토링하여 새로운 엔티티 타입 추가 시 확장성 개선

---

## TECH-DEBT-002: Neo4j query_subgraph 파라미터화 쿼리

| 항목 | 값 |
|------|-----|
| **Story** | STORY-006 |
| **파일** | `knowledge_service/src/app/storage/neo4j_storage.py` L707 |
| **등급** | Medium |
| **유형** | 보안 강화 |
| **대상 Sprint** | Sprint 04 |

**현상**: 문자열 연결로 Cypher depth를 주입 (`str(depth)`) - 현재는 정수형이라 Cypher 인젝션 위험 낮음

**개선**: 파라미터화 쿼리로 전환. `apoc.path.subgraphAll` 사용 가능 시 고려

---

## TECH-DEBT-003: Keycloak 토큰 확장 인터페이스 정의

| 항목 | 값 |
|------|-----|
| **Story** | STORY-040 |
| **파일** | `knowledge_service/frontend/src/auth/keycloak.ts` |
| **등급** | Medium |
| **유형** | 타입 안전성 |
| **대상 Sprint** | Sprint 04 |

**현상**: `(tokenParsed as any).department` 등 `any` 캐스팅으로 토큰 필드 접근

**개선**: Keycloak 토큰 확장 인터페이스(`interface ExtendedKeycloakTokenParsed`) 정의하여 타입 안전성 확보

---

## TECH-DEBT-004: 테스트 계정 정보 환경 변수 분리

| 항목 | 값 |
|------|-----|
| **Story** | STORY-040 |
| **파일** | `knowledge_service/frontend/src/pages/LoginPage.tsx` |
| **등급** | Medium |
| **유형** | 보안 개선 |
| **대상 Sprint** | Sprint 04 |

**현상**: 개발 모드에서 테스트 계정 비밀번호가 코드에 하드코딩됨

**개선**: `VITE_DEV_TEST_USERNAME`, `VITE_DEV_TEST_PASSWORD` 등 환경 변수로 분리. `.env.development`에서 관리

---

## 요약

| ID | 등급 | 유형 | Story | 대상 Sprint |
|----|------|------|-------|-------------|
| TECH-DEBT-001 | Medium | 리팩토링 | STORY-006 | Sprint 04 |
| TECH-DEBT-002 | Medium | 보안 강화 | STORY-006 | Sprint 04 |
| TECH-DEBT-003 | Medium | 타입 안전성 | STORY-040 | Sprint 04 |
| TECH-DEBT-004 | Medium | 보안 개선 | STORY-040 | Sprint 04 |
