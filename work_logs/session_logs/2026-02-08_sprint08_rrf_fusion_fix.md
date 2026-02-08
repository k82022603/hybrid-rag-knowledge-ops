# Session Log - 2026-02-08

**Session ID**: 2026-02-08_sprint08_rrf_fusion_fix
**시작 시간**: 14:30 (이전 세션 컨텍스트 이어서)
**종료 시간**: 16:34
**모델**: Claude Opus 4.6 (claude-opus-4-6)

---

## 세션 요약

RRF Fusion source_type 추적 버그 수정, TechLead 코드 리뷰, PM 백로그 등록, rrf_fusion.py 동기화 수정 및 배포

---

## 완료된 작업

### 1. RRF Fusion source_type 추적 버그 수정 (STORY-091 - 주요)

#### 상세 내용
- **근본 원인**: `_rrf_fusion()`이 `result.source`는 갱신하지만 `metadata["search_source"]`는 미갱신 → API SearchResult 모델에 `source` 필드 없음 → 프론트엔드가 항상 "vector"로 표시
- `search.py._rrf_fusion()`: `metadata["search_source"] = primary_source` 동기화 추가
- `routes/search.py`: API SearchResult 모델에 `source_type` 필드 추가, 3개 엔드포인트(hybrid/semantic/keyword) 모두 적용
- `searchService.ts`: `r.source_type` 우선 매핑으로 변경
- AI Service 리빌드 및 배포 완료

### 2. rrf_fusion.py primary_source 동기화 수정 (주요)

#### 상세 내용
- TechLead 리뷰에서 발견된 Medium 이슈: 독립 모듈 `rrf_fusion.py`의 `fuse_search_results()`에 `primary_source` 갱신 로직 없음
- `fuse_search_results()` 메서드에 primary_source 결정 + `result.source` / `metadata["search_source"]` 갱신 로직 추가
- AI Service 2차 리빌드 및 배포 완료

### 3. SearchFilters 개선 (부가)

#### 상세 내용
- Project 드롭다운 제거 (백엔드 미지원)
- 한글 로컬라이제이션 적용
- 문서 유형에 HWP, Markdown 추가

### 4. KeywordSearch Graph 버튼 조건 개선 (부가)

#### 상세 내용
- graphContext가 있거나 sourceType이 'graph'인 경우에만 Graph 버튼 표시
- ISSUE-011 파일명 엔티티 필터 로직 적용

### 5. TechLead RRF Fusion 전반 검토 (부가)

#### 상세 내용
- 에이전트를 통한 RRF fusion 코드 전반 리뷰
- **판정**: APPROVE
- Medium 이슈 1건 (rrf_fusion.py primary_source → 수정 완료)
- Low 이슈 1건 (keyword BM25 highlight 유실 → 향후 개선)

### 6. PM 백로그 등록 (부가)

#### 상세 내용
- STORY-091~095 (5건, 16 SP) 백로그 스토리 파일 생성
- Sprint 08 문서에 Discovered Issues 섹션 추가
- Slack 알림 전송 (#proj-hrkp-dev)

### 7. Hybrid Search Neo4j 통합 검증 (부가)

#### 상세 내용
- hybrid_search → _graph_search → _neo4j_query → Cypher 실행 파이프라인 확인
- Graceful degradation (Neo4j 미연결 시 빈 결과 반환) 정상 동작 확인
- 별도 수정 불필요 판정

### 8. MinIO 문서 다운로드 아키텍처 분석 (부가)

#### 상세 내용
- MinIO S3 호환 저장소 구조 확인 (`minio://documents/{document_id}/{filename}`)
- `get_file_url()` presigned URL (1시간 유효) 방식 분석
- 영구 URL 방안 제안: 백엔드 프록시 `/api/v1/documents/{id}/download` (JWT 인증 유지)

---

## 주요 결정사항

| 결정 | 내용 | 근거 |
|------|------|------|
| source_type API 필드 추가 | SearchResult 모델에 source_type 필드 명시적 추가 | metadata 내부 search_source만으로는 프론트엔드 매핑 불안정 |
| MinIO 영구 URL 방식 | 백엔드 프록시 방식 권장 | JWT 인증 유지 + presigned URL 만료 문제 해결 |
| rrf_fusion.py 동기화 | search.py와 동일한 primary_source 로직 추가 | VIP Agent가 이 모듈 사용, 소스 표시 일관성 확보 |

---

## 변경된 파일 목록

```
knowledge_service/
├── src/app/
│   ├── api/routes/search.py          # source_type 필드 추가
│   ├── services/search.py            # metadata.search_source 동기화
│   └── services/rrf_fusion.py        # primary_source 갱신 로직 추가
├── frontend/src/
│   ├── services/searchService.ts     # source_type 우선 매핑
│   ├── components/search/SearchFilters.tsx  # Project 제거, 한글화
│   └── features/search/KeywordSearch.tsx    # Graph 버튼 조건 개선
backlog/
├── stories/STORY-091~095.md          # 5건 신규 생성
└── sprints/sprint-08.md              # Discovered Issues 섹션 추가
```

---

## 현재 프로젝트 상태

### 인프라 상태
| 항목 | 값 |
|------|-----|
| 총 컨테이너 | 18개 (전체 Running) |
| AI Service | Healthy (2차 리빌드 배포 완료) |
| Frontend | Healthy (docker cp 배포 완료) |
| Neo4j | Healthy |
| Elasticsearch | Healthy |

### Sprint 상태
| 항목 | 값 |
|------|-----|
| Sprint | 08 (Day 3) |
| STORY-091 | Done (RRF Fusion 수정) |
| STORY-092~095 | To Do (신규 발견) |
| 신규 백로그 SP | 16 SP |

---

## 다음 작업 (Action Items)

### P1 (High)
1. STORY-092: 문서 다운로드 링크 구현 (`/api/v1/documents/{id}/download` 백엔드 프록시)

### P2 (Medium)
2. STORY-093: Content Viewer 모달 (청크 전문 조회)
3. STORY-094: 문서 제목 추출 개선 (ETL 파이프라인)
4. STORY-095: camelCase/snake_case 잔존 4건 수정

### P3 (Low)
5. Keyword BM25 highlight 메타데이터 병합 (TechLead Low 이슈)

---

## 리스크 모니터링

| 리스크 | 확률 | 영향 | 상태 | 대응 |
|--------|------|------|------|------|
| 검색 결과 사용성 부족 | Med | High | Open | STORY-092~094로 개선 예정 |
| camelCase/snake_case 불일치 잔존 | Low | Med | Monitoring | STORY-095로 추적 |

---

## 사용된 도구 및 에이전트

| 도구/에이전트 | 용도 |
|--------------|------|
| TechLead (tech-lead) | RRF Fusion 전반 코드 리뷰 |
| PM (project-manager) | STORY-091~095 백로그 등록 |
| Explore (general-purpose) | Neo4j 통합 검증, MinIO 구조 분석 |
| Explore (general-purpose) | camelCase/snake_case 전수 조사 |

---

## 세션 통계

| 항목 | 값 |
|------|-----|
| 수정된 파일 | 6개 (Python 3, TypeScript 3) |
| 신규 생성 파일 | 5개 (백로그 스토리) |
| 배포 횟수 | 3회 (Frontend 1, AI Service 2) |
| 에이전트 사용 | 5개 (TechLead, PM, Explore x3) |

---

*기록자: Claude Code (Opus 4.6)*
*기록 시간: 2026-02-08 16:34 KST*
