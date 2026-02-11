# Session Log - 2026-02-11 (Session 2)

**Session ID**: 2026-02-11_gateway_graph_bugfix
**시작 시간**: ~15:00 KST (이전 세션에서 연속)
**종료 시간**: 19:41 KST
**모델**: Claude Opus 4.6 (claude-opus-4-6)

---

## 세션 요약

Gateway 405 오류 + 그래프 시각화 빈 결과 + Lucene 특수문자 파싱 오류 등 **연관된 3건의 버그**를 근본 원인 분석 후 수정하고, Bug Fix Report를 작성한 세션.

---

## 완료된 작업

### 1. STORY-108 file_hash 중복 방지 + 검색 응답 개선 (주요)

#### 상세 내용
- `file_hash` 기반 문서 중복 업로드 방지 로직 구현
- 검색 응답에 `title`, `contributing_sources` 필드 추가
- 커밋: `09090f2`

### 2. Gateway 405 Method Not Allowed 수정 (주요)

#### 상세 내용
- **증상**: POST `/api/v1/search/chat` → 405 (Spring Boot 형식 에러)
- **원인 1**: `FallbackController.java`에서 `@GetMapping` + `@PostMapping` 스택 → WebFlux에서 GET만 등록
- **원인 2**: Circuit Breaker `slow-call-duration-threshold: 5s`가 LLM 호출(15~50초)을 모두 slow로 판정 → OPEN → fallback 라우팅
- **수정**: `@RequestMapping(method = {GET, POST})` 통일 + CB 임계값 조정 (30s/10/90)
- 커밋: `eb40cda`

### 3. 그래프 시각화 빈 결과 수정 (주요)

#### 상세 내용
- **증상**: 검색 결과 그래프 아이콘 클릭 → `nodes: [], edges: []`
- **근본 원인**: RRF 융합에서 Vector(1st) 결과만 저장, Graph(3rd)의 `matched_entities` 유실
- **수정 3건**:
  1. `search.py` - RRF 융합 시 `matched_entities` 병합
  2. `rag_workflow.py` - `_extract_entities_from_title()` 키워드 분리 (불용어/날짜 필터링)
  3. `neo4j_storage.py` - `query_subgraph()` 3단계 fallback (fulltext → CONTAINS → document title)
- **추가 발견**: Redis 캐시가 stale 메타데이터 반환 → `FLUSHDB`로 해결
- 커밋: `eb40cda`

### 4. Lucene 특수문자 이스케이프 수정 (주요)

#### 상세 내용
- **증상**: `CI/CD` subgraph 조회 → 500 `TokenMgrError: Lexical error ... Encountered: <EOF> after prefix "/CD"`
- **원인**: Neo4j fulltext 쿼리가 Lucene Query Parser 사용, `/`가 정규식 구분자로 해석
- **수정**: `_escape_lucene()` 함수 추가 (`+ - && || ! ( ) { } [ ] ^ " ~ * ? : \ /` 이스케이프)
- **검증**: `CI/CD` → 3 nodes, 3 edges 정상 반환
- 커밋: `b4278fa`

### 5. Bug Fix Report 작성 (부가)

#### 상세 내용
- `docs/07_maintenance/21_bugfix_report_2026-02-11_gateway_405_graph_empty.md` 작성
- Mermaid 다이어그램으로 원인 분석, 데이터 흐름, 수정 전/후 도식화
- Bug #1 (Gateway 405), Bug #2 (그래프 빈 결과), Bug #3 (Lucene 특수문자) 포함
- 커밋: `994e78b`, `88e7989`

### 6. 프로젝트 문서 정리 (부가)

#### 상세 내용
- `docs/01_planning/` 파일 번호 매기기 정리
- RAGAS v6 평가 완료, results 폴더 정리
- 커밋: `30e837c`, `bf337ee`

---

## 주요 결정사항

| 결정 | 내용 | 근거 |
|------|------|------|
| RRF metadata 병합 | 중복 chunk_id에서 후순위 소스의 matched_entities를 기존 결과에 병합 | Vector 우선 저장으로 Graph metadata 유실 방지 |
| CB threshold 30s | slow-call-duration-threshold를 5s → 30s | LLM 호출 평균 15~50초, 5s면 100% slow 판정 |
| 3단계 subgraph fallback | fulltext → CONTAINS → document title 역추적 | 엔티티명이 정확하지 않아도 관련 그래프 반환 |
| Lucene 이스케이프 | fulltext 쿼리 전 모든 특수문자 이스케이프 | `/`, `+`, `:` 등이 Lucene 연산자로 해석되는 문제 |
| Redis FLUSHDB | 코드 수정 후 캐시 전체 클리어 | 메타데이터 구조 변경 시 stale cache가 잘못된 결과 반환 |

---

## 변경된 파일 목록

```
knowledge_service/
├── gateway/
│   └── src/main/java/.../FallbackController.java   # @RequestMapping 통일
│   └── src/main/resources/application.yml           # CB 임계값 조정
├── src/app/
│   ├── agents/rag_workflow.py                       # _extract_entities_from_title 개선
│   ├── services/search.py                           # RRF matched_entities 병합
│   └── storage/neo4j_storage.py                     # 3단계 fallback + Lucene escape
└── docs/07_maintenance/
    └── 21_bugfix_report_2026-02-11_*.md             # Bug Fix Report (3건)
```

---

## 커밋 히스토리 (이 세션)

| 커밋 | 메시지 | 상태 |
|------|--------|------|
| `09090f2` | STORY-108 file_hash 중복 방지 + 검색 응답 개선 | pushed |
| `30e837c` | 프로젝트 문서 전체 정리 + RAGAS v6 평가 완료 | pushed |
| `bf337ee` | 01_planning 번호매기기 + 참조 링크 업데이트 | pushed |
| `eb40cda` | Gateway 405 + 그래프 시각화 빈 결과 수정 | **미푸시** |
| `994e78b` | Bug Fix Report 초안 작성 | **미푸시** |
| `b4278fa` | Lucene 특수문자 이스케이프 수정 | **미푸시** |
| `88e7989` | Bug Fix Report에 Bug #3 추가 | **미푸시** |

---

## 현재 프로젝트 상태

### 인프라 상태
| 항목 | 값 |
|------|-----|
| 총 컨테이너 | 18개 |
| AI Service | 가동 중 (kp-ai-service) |
| Redis | 가동 중 (FLUSHDB 완료) |
| Neo4j | 가동 중 (fulltext index 정상) |
| Gateway | 가동 중 (CB 설정 갱신 필요 - 컨테이너 재시작) |

### Sprint 상태
| 항목 | 값 |
|------|-----|
| Sprint | Sprint 01 |
| STORY-108 | file_hash dedup 완료 |
| ISSUE-011 | 그래프 패널 엔티티명 - 수정 완료 |

---

## 다음 작업 (Action Items)

### P0 (Critical)
1. **미푸시 커밋 4건 push** - `eb40cda` ~ `88e7989`

### P1 (High)
2. **Gateway 컨테이너 재빌드** - CB 설정 변경 반영 위해 `docker-compose build gateway && docker-compose up -d gateway`
3. **E2E 검증** - Nginx 경유 Chat → Graph 클릭 → Subgraph 반환 전체 플로우

### P2 (Medium)
4. **KG Entity Extraction 확장** - 현재 5개 Knowledge 노드만 엔티티 연결, 전체 문서로 확대 필요
5. **Lucene 특수문자 단위 테스트** - `CI/CD`, `C++`, `"quoted"` 등 케이스 추가

---

## 리스크 모니터링

| 리스크 | 확률 | 영향 | 상태 | 대응 |
|--------|------|------|------|------|
| Redis 캐시 stale | Med | Med | Resolved | 코드 수정 후 FLUSHDB 절차화 |
| CB 재발 (LLM 지연) | Low | High | Monitoring | threshold 30s로 상향, 모니터링 대시보드 권장 |
| Neo4j fulltext 특수문자 | Low | Med | Resolved | _escape_lucene() 적용 |
| Gateway 미재빌드 | Med | Med | Open | 다음 세션에서 컨테이너 재빌드 필요 |

---

## 기술 메모 (다음 세션 참조)

### Neo4j CALL 서브쿼리 제약
- `WITH e AS center` (aliasing) 불가 → 변수명을 처음부터 `center`로 선언해야 함
- `Importing WITH should consist only of simple references to outside variables`

### Redis 캐시 키 구조
- 검색 결과 캐시가 metadata 포함하여 저장됨
- 코드에서 metadata 구조 변경 시 반드시 FLUSHDB 필요

### Lucene 이스케이프 범위
- `_escape_lucene()`은 `query_subgraph()`의 fulltext 쿼리에만 적용
- 향후 다른 fulltext 쿼리 추가 시에도 동일 이스케이프 필요

---

## 세션 통계

| 항목 | 값 |
|------|-----|
| 수정된 파일 | 5개 |
| 신규 생성 파일 | 1개 (Bug Fix Report) |
| 커밋 수 | 7개 (이 세션) |
| 미푸시 커밋 | 4개 |
| 수정한 버그 | 3건 |

---

*기록자: Claude Code (Opus 4.6)*
*기록 시간: 2026-02-11 19:41 KST*
