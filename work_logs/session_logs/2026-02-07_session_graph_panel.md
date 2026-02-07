# Session Log - 2026-02-07 (Graph Panel)

**Session ID**: 2026-02-07_session_graph_panel
**시작 시간**: -
**종료 시간**: -
**모델**: Claude Opus 4.6 (claude-opus-4-6)
**Sprint**: Sprint 08 (Day 2) - 후속 세션

---

## 세션 요약

Sprint 08 Day 2 후속 세션. 이전 세션 미완료 커밋을 완료하고, **GraphPanel `/api/v1/graph/subgraph` 500 에러**를 API Gateway 라우트 추가로 해결했다. Neo4j `query_subgraph()` 메서드를 전면 리팩토링하여 38 nodes / 111 edges 정상 반환을 확인했으나, **entity_name이 파일명으로 전송되는 문제**(ISSUE-011)는 미해결 상태로 Day 3에서 이어서 진행한다.

---

## 완료된 작업

### 1. 이전 세션 커밋 완료

**커밋**: `3e63561`

#### 상세 내용
- 이전 세션에서 미완료된 git commit 실행
- 커밋 메시지: `[FEAT] Graph Search 3단계 매칭 + Source Type 배지 + Graph 시각화 패널`
- 22 files changed, +3,745 / -243 lines
- 포함 범위: search.py (3-stage matching + RRF fix), rag_pipeline.py, rag_workflow.py, auth.py, 프론트엔드 전체, 문서 4건

### 2. AI Service 컨테이너 충돌 해결

#### 문제
- 이전 세션 백그라운드 빌드 태스크 6건 + 에이전트 2건이 잔존
- 유령 컨테이너 `15171c26def1_kp-ai-service` 이름 충돌 발생

#### 해결
- `docker rm -f 15171c26def1_kp-ai-service`로 유령 컨테이너 제거
- `docker-compose up -d ai-service` 정상 가동 확인

### 3. GraphPanel `/api/v1/graph/subgraph` 500 에러 해결

**파일**: `knowledge_service/gateway/src/main/resources/application.yml`

#### 문제
- 브라우저에서 Graph 버튼 클릭 시 500 Internal Server Error 발생
- API Gateway `application.yml`에 `/api/v1/graph/**` 라우트가 없음
- catch-all `/api/v1/**` 라우트가 Backend(SpringBoot)로 전달
- Backend에는 graph API가 존재하지 않으므로 500 반환

#### 해결
- local 프로필 + docker 프로필 모두에 `graph-service` 라우트 추가
- `Path=/api/v1/graph/**` -> AI Service (`http://ai-service:8000`)로 매핑
- Gateway 빌드 + 재시작 후 200 OK 확인

#### 수정 내용 (application.yml)
```yaml
# graph-service 라우트 추가 (local + docker 프로필)
- id: graph-service
  uri: http://ai-service:8000
  predicates:
    - Path=/api/v1/graph/**
```

### 4. Neo4j Subgraph API 데이터 불완전 문제 해결

**파일**: `knowledge_service/src/app/storage/neo4j_storage.py` (`query_subgraph()`)

#### 문제
- 첫 번째 테스트 시 nodes=7 (name=None), edges=0
- `edges_out`이 항상 빈 배열 (relationships 파싱 코드 없음)
- `_node_to_dict()`가 `dict(node)` -> properties만 반환, id/name/type/labels 누락
- Cypher 쿼리가 `->` (outgoing만) -> 양방향 관계 탐색 필요

#### 해결: `query_subgraph()` 전면 리팩토링
| 항목 | 변경 전 | 변경 후 |
|------|---------|---------|
| 관계 방향 | `->` (outgoing만) | `-[r]-` (양방향) |
| 노드 정보 | properties만 | id, name, type, labels, properties 포함 |
| 엣지 파싱 | 코드 없음 (항상 빈 배열) | 실제 relationship에서 source, target, type 파싱 |
| 중복 처리 | 없음 | `seen_ids` set으로 중복 노드 제거 |

#### 검증 결과
| 지표 | 변경 전 | 변경 후 |
|------|---------|---------|
| Nodes | 7 (name=None) | 38 (정상 name) |
| Edges | 0 | 111 |
| API 응답 | 불완전 | 완전한 그래프 데이터 |

### 5. GraphPanel entity_name 매핑 오류 조사 (프론트엔드)

**파일**: 4개 프론트엔드 파일 수정

#### 문제
- Graph 버튼 클릭 시 `entity_name: "test_doc_2.txt"` (파일명)이 전송됨
- 실제 엔티티 이름 대신 문서 파일명이 사용되어 subgraph API에서 0 results 반환

#### 원인 추정
- 백엔드 SSE가 `graph_context` (snake_case)로 보내는데 프론트엔드가 `graphContext` (camelCase)만 체크
- SSE 응답의 `graph_context.related_entities` 데이터가 프론트엔드까지 올바르게 전달되지 않음

#### 수정 파일
| 파일 | 변경 내용 |
|------|----------|
| `frontend/src/shared/api/sse.ts` | `graph_context` (snake_case) 타입 추가 |
| `frontend/src/features/search/hooks/useStreamingSearch.ts` | `graph_context` -> `graphContext` 매핑 변환 |
| `frontend/src/features/search/types.ts` | `GraphNode.name` 필드 추가 |
| `frontend/src/features/search/components/GraphPanel.tsx` | `n.name \|\| n.label \|\| n.id` 우선순위 적용 |

#### 결과
- 프론트 빌드 + Nginx 배포 완료
- 여전히 `test_doc_2.txt` 전송 -> **ISSUE-011로 등록** (Day 3 이어서 해결)

### 6. PM 마감 스탠드업 미팅

- Slack `proj-hrkp-standup` 채널에 마감 스탠드업 전송
- Day 2 성과 및 미해결 이슈 보고

---

## 기술적 발견

### API Gateway 라우트 순서 중요성
- Spring Cloud Gateway는 라우트를 순서대로 평가
- catch-all `/api/v1/**` 라우트보다 구체적인 `/api/v1/graph/**` 라우트를 **앞에** 배치해야 함
- 순서가 잘못되면 catch-all이 먼저 매칭되어 의도하지 않은 서비스로 전달

### Neo4j `query_subgraph()` 설계 교훈
- `dict(node)`는 Neo4j 노드의 properties만 반환하며, `id`, `labels` 등 메타데이터는 별도 접근 필요
- `node.id`, `node.labels`로 메타데이터를 명시적으로 추출해야 완전한 노드 정보 확보
- 양방향 관계 (`-[r]-`)를 사용해야 그래프의 전체 연결 구조가 반환됨

### SSE snake_case vs camelCase 불일치
- Python 백엔드는 snake_case (`graph_context`)로 SSE 데이터 전송
- TypeScript 프론트엔드는 camelCase (`graphContext`)를 기대
- SSE 파싱 레이어에서 케이스 변환 매핑이 필수

### 유령 컨테이너 발생 원인
- 동시 빌드/재시작 시 이전 컨테이너가 이름을 점유한 채 종료되지 않는 경우 발생
- `docker rm -f`로 강제 제거 후 재시작으로 해결

---

## E2E 검증 결과

| 테스트 항목 | 결과 | 비고 |
|------------|------|------|
| AI Service 컨테이너 가동 | PASS | 유령 컨테이너 제거 후 정상 |
| Gateway graph-service 라우트 | PASS | `/api/v1/graph/subgraph` -> 200 OK |
| Subgraph API 응답 | PASS | 38 nodes, 111 edges 정상 반환 |
| GraphPanel UI 렌더링 | PARTIAL | 그래프 시각화는 동작하나 entity_name이 파일명 |
| entity_name 정확성 | FAIL | ISSUE-011, Day 3에서 해결 예정 |

---

## 변경된 파일 목록

### 커밋된 파일 (3e63561 - 이전 세션 작업)

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `knowledge_service/src/app/services/search.py` | MODIFY | 3단계 매칭 전략 + RRF primary source 결정 |
| `knowledge_service/src/app/services/rag_pipeline.py` | MODIFY | graph_context 전달 로직 추가 |
| `knowledge_service/src/app/agents/rag_workflow.py` | MODIFY | graph_context 전달 로직 추가 |
| `knowledge_service/src/app/api/routes/auth.py` | MODIFY | 3중 인증 전략 |
| `knowledge_service/src/app/api/routes/search.py` | MODIFY | source_type 필터링 |
| `knowledge_service/frontend/` (13 files) | MODIFY/CREATE | Source Type 배지 + GraphPanel |
| `knowledge_service/docs/` (3 files) | CREATE | 구현문서, UAT 타임라인, ISSUE-010 |
| `work_logs/session_logs/2026-02-07_session.md` | CREATE | 세션로그 |

### 미커밋 파일 (이번 세션 작업)

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `knowledge_service/gateway/src/main/resources/application.yml` | MODIFY | graph-service 라우트 추가 (local + docker) |
| `knowledge_service/src/app/storage/neo4j_storage.py` | MODIFY | `query_subgraph()` 전면 리팩토링 (양방향, 노드/엣지 완전 파싱) |
| `knowledge_service/frontend/src/shared/api/sse.ts` | MODIFY | `graph_context` snake_case 타입 추가 |
| `knowledge_service/frontend/src/features/search/hooks/useStreamingSearch.ts` | MODIFY | `graph_context` -> `graphContext` 매핑 변환 |
| `knowledge_service/frontend/src/features/search/types.ts` | MODIFY | `GraphNode.name` 필드 추가 |
| `knowledge_service/frontend/src/features/search/components/GraphPanel.tsx` | MODIFY | `n.name \|\| n.label \|\| n.id` 우선순위 적용 |

---

## 미해결 이슈

### ISSUE-011: GraphPanel entity_name이 파일명으로 전송됨

| 항목 | 내용 |
|------|------|
| **심각도** | Medium |
| **영향** | Graph 시각화 패널에서 실제 엔티티 기반 subgraph를 조회하지 못함 |
| **증상** | Graph 버튼 클릭 시 `entity_name: "test_doc_2.txt"` 전송 -> 0 results |
| **원인 추정** | 백엔드 SSE `graph_context.related_entities` 데이터가 프론트엔드까지 올바르게 전달되지 않음 |

#### Day 3 조사 방향
1. `rag_workflow.py`에서 `_build_sources()` 내 `graph_context`가 SSE 소스에 포함되는지 추적
2. `rag_pipeline.py`에서 `graph_context.related_entities` 실제 전달 여부 확인
3. SSE 응답 원본에서 `graph_context` 필드 존재 여부 검증 (curl로 직접 확인)
4. 프론트엔드에서 entity_name 결정 로직 재점검

---

## 주요 결정사항

| 결정 | 내용 | 근거 |
|------|------|------|
| Gateway 라우트 분리 | `/api/v1/graph/**`를 별도 라우트로 추가 | catch-all 라우트로 인한 잘못된 서비스 라우팅 방지 |
| `query_subgraph()` 전면 리팩토링 | 양방향 + 완전 노드/엣지 파싱 | 기존 코드가 불완전한 데이터만 반환하여 점진적 수정보다 전면 교체가 효율적 |
| ISSUE-011 Day 3 이관 | entity_name 문제를 별도 이슈로 분리 | 백엔드 SSE 데이터 흐름 전체를 재추적해야 하는 복잡한 문제 |
| snake_case 매핑 레이어 추가 | SSE 파싱에서 케이스 변환 | Python(snake) -> TypeScript(camel) 불일치 근본 해결 |

---

## 컨테이너 빌드/배포 이력

| 서비스 | 빌드 횟수 | 사유 |
|--------|-----------|------|
| AI Service | 2회 | 1차: 컨테이너 충돌 해결, 2차: `query_subgraph()` 리팩토링 반영 |
| API Gateway | 1회 | `graph-service` 라우트 추가 |
| Frontend (Nginx) | 2회 | 1차: snake_case 매핑 추가, 2차: GraphPanel name 우선순위 수정 |

---

## 리스크 모니터링

| 리스크 | 확률 | 영향 | 상태 | 대응 |
|--------|------|------|------|------|
| ISSUE-011 entity_name 오류 | High | Med | Open | Day 3에서 백엔드 SSE 데이터 흐름 전체 추적 |
| Gateway 라우트 순서 | Low | High | Resolved | 구체적 라우트를 catch-all 앞에 배치 |
| Neo4j subgraph 성능 | Med | Low | Monitoring | 대규모 그래프에서 양방향 탐색 성능 확인 필요 |
| 미커밋 파일 6개 | Med | Med | Open | Day 3 시작 시 커밋 필요 |

---

## 다음 작업 (Action Items)

### P0 (Critical)
1. 미커밋 파일 6개 git commit 실행

### P1 (High)
2. ISSUE-011 해결: entity_name 파일명 -> 실제 엔티티명 수정
   - 백엔드 SSE `graph_context.related_entities` 데이터 흐름 추적
   - `rag_workflow.py` `_build_sources()` 디버깅

### P2 (Medium)
3. GraphPanel E2E 전체 검증 (entity_name 수정 후)
4. Neo4j subgraph 대규모 데이터 성능 테스트

---

## 사용된 도구 및 에이전트

| 도구/에이전트 | 용도 |
|--------------|------|
| Bash | Docker 컨테이너 관리 (rm, build, up), Gateway 빌드, 프론트엔드 빌드/배포 |
| Read/Edit | application.yml, neo4j_storage.py, sse.ts, useStreamingSearch.ts, types.ts, GraphPanel.tsx 수정 |
| Git | 이전 세션 커밋 완료 (3e63561) |
| Slack (MCP) | 마감 스탠드업 미팅 (proj-hrkp-standup) |

---

## 세션 통계

| 항목 | 값 |
|------|-----|
| 완료 작업 | 5개 (커밋 완료, 컨테이너 해결, Gateway 라우트, Subgraph 리팩토링, 프론트엔드 수정) |
| 미해결 작업 | 1개 (ISSUE-011 entity_name) |
| 커밋된 파일 | 22개 (이전 세션 작업) |
| 미커밋 파일 | 6개 (이번 세션 작업) |
| 컨테이너 빌드 | 5회 (AI Service 2, Gateway 1, Frontend 2) |
| E2E 검증 | 3/5 PASS, 1 PARTIAL, 1 FAIL |
| 발견 버그 | 3개 (Gateway 라우트 누락, Subgraph 불완전, entity_name 오류) |
| 수정 버그 | 2개 (Gateway, Subgraph) |
| 이관 버그 | 1개 (ISSUE-011) |

---

*작성: Claude Code (Opus 4.6)*
*작성일: 2026-02-07*
