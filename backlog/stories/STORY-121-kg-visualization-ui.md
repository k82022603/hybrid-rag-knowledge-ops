# STORY-121: KG 시각화 UI — Neo4j 실데이터 연동

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | - |
| **Epic** | Knowledge Graph 고도화 |
| **Status** | To Do |
| **Priority** | P2 |
| **Story Points** | 5 |
| **Assignee** | Frontend/WebDesigner |
| **Sprint** | Sprint 09 |

---

## User Story

**As a** 지식 검색 사용자,
**I want** 검색 결과와 연관된 지식 그래프를 시각적으로 탐색하기를,
**So that** 문서 간 관계와 엔티티 연결을 직관적으로 파악할 수 있다.

---

## 배경

- `react-force-graph-2d` 라이브러리 이미 설치됨
- GraphPanel 컴포넌트 기구현 (검색 출처 엔티티만 표시)
- STORY-112(Phase 3 실행) + STORY-088(Entity 라벨 수정) 완료 후 실데이터 연동 가능

---

## Acceptance Criteria

- [ ] KnowledgePage에 전체 그래프 탐색 뷰 추가
- [ ] 노드 타입별 필터 (Entity, Document, Person, Technology 등)
- [ ] 노드 클릭 시 관련 문서 연결
- [ ] WebDesigner Verbalized Sampling 디자인 적용 (일반적인 노드-엣지 클리셰 회피)
- [ ] WCAG 2.1 AA 접근성 준수

---

## Tasks

- [ ] KnowledgePage 그래프 탐색 뷰 컴포넌트 설계 (WebDesigner 협업)
- [ ] Neo4j Graph API 엔드포인트 연동
- [ ] 노드 타입별 색상/아이콘 시각화
- [ ] 필터 UI 구현 (Headless UI 기반)
- [ ] 성능 최적화 (노드 수 제한, 가상화)

---

## 의존성

- **선행**: STORY-112 (Phase 3 엔티티 추출), STORY-088 (Entity 라벨 수정), STORY-124 (Neo4j 스키마 통합)
- **협업**: WebDesigner (디자인 스펙), Backend (Graph API)
