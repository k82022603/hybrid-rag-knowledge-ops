# Session Log - 2026-03-09

**Session ID**: 2026-03-09_uat_perf_tuning
**시작 시간**: 10:52
**종료 시간**: 17:32 (진행 중)
**모델**: Claude Opus 4.6 (claude-opus-4-6)

---

## 세션 요약

UAT 18건 전수 PASS, Chat API 성능 튜닝, Graph RRF 후보 수 제한, SCRUM-101 source_type 오버라이드 버그 수정, UI 소스코드 점검, "< Graph" 의도된 동작 문서화

---

## 완료된 작업

### 1. Docker 컨테이너 기동 및 환경 점검 (주요)

#### 상세 내용
- 21개 전체 컨테이너 시작 (모두 Exited 상태에서 기동)
- 핵심 서비스 헬스체크 확인: Nginx, API Gateway, AI Service, Frontend
- 로그인 API 정상 확인 (admin@example.com / admin123!)

### 2. QA 주도 UAT 사용자 테스트 (주요)

#### 상세 내용
- **총 18건 테스트**, 최종 **18/18 PASS (100%)**
- 테스트 범위: 인증(2), Frontend(3), 검색(3), RAG Chat(1), 보안(3), 인프라(4), 그래프(1), 사용자(1)
- TC-07 RAG Chat: 초기 FAIL (73초 타임아웃) → 성능 튜닝 후 PASS (80초 응답)
- QA Agent가 별도로 23건 확장 테스트 수행 (스트리밍, 멀티턴, 추가 에지케이스)

### 3. Chat API 성능 튜닝 (주요)

#### TechLead 분석 결과
- 6가지 병목 지점 확인, 핵심: **Reranker 이중 실행** (SearchService + HybridRetriever에서 2회)
- 전체 콜스택 추적: Nginx → Gateway → AI Service → RAGWorkflow → HybridRetriever → SearchService

#### 적용된 최적화 (5건)
| ID | 내용 | 파일 |
|----|------|------|
| P0-1 | Reranker 이중 실행 제거 (`skip_reranking=True`) | `search.py`, `retriever.py` |
| P0-2 | Reranker 후보 수 50→15건 제한 | `search.py`, `retriever.py` |
| P1-1 | ES 검색 `request_timeout=10` 명시 | `search.py` |
| P1-2 | ONNX Runtime 스레드 2코어 제한 | `bge_reranker.py` |
| P1-3 | 타임아웃 확대 (Reranker 60초, Nginx 180초, Gateway 180초) | `search.py`, `default.conf`, `application.yml` |

#### Reranker 스킵 시도 및 원복
- Chat 경로에서 Reranker=None으로 비활성화: 38초 응답 (검색 781ms!)
- **사용자 판단**: 품질(score 0.98+)을 위해 Reranker ON 유지, 원복 완료
- CPU 33초는 안고 가야 할 제약, GPU 도입 시 해결

### 4. Nginx 방어 코드 추가 (주요)

#### 상세 내용
- **문제**: Observability 컨테이너(Grafana 등) 중지 시 Nginx upstream DNS resolve 실패 → 재시작 루프
- **수정**: Docker DNS resolver(`127.0.0.11`) 설정 + Grafana upstream 변수 방식(`set $grafana_upstream`)
- **결과**: Grafana 중지 상태에서도 Nginx healthy 유지

### 5. 불필요 컨테이너 중지 (부가)

#### 상세 내용
- Infra Agent 투입하여 Observability 10개 컨테이너 중지
- 21개 → 11개(핵심만) 운영으로 리소스 절감

### 6. Graph 검색 RRF 후보 수 제한 (중요 — 사용자 피드백 기반)

#### 배경 (사용자 피드백)
- 하이브리드 검색(4-way RRF: vector + keyword + sparse + graph) 결과에서 **Graph가 primary source인 결과가 지나치게 많음**
- 사용자 원문: "무조건 graph만 뒤지는 것처럼 보인다"
- UI에서 직접 검색 결과를 확인하며 발견한 **검색 품질 + UX 이슈**

#### 원인 분석
- Graph 검색이 `top_k * 2 = 20건`을 RRF에 넣고 있었음
- Graph 가중치(0.8)와 높은 후보 수(20건)가 결합되어, graph에서 높은 순위로 반환된 청크들이 RRF 점수에서 우위를 점함
- 결과적으로 최종 결과의 primary source가 대부분 Graph로 결정

#### 해결 방안 — 후보 수 제한 (가중치 조절 아닌 설계적 접근)
- `config.py`: `graph_search_top_k: int = Field(default=3)` 설정값 분리
- `search.py`: `top_k=top_k * 2` 를 `top_k=settings.graph_search_top_k` 로 변경
- **가중치(0.8)는 그대로 유지** — RRF 부스트 효과는 보존하면서 후보 수만 제한

#### 설계 철학
> 가중치를 낮추면 Graph의 RRF 기여 자체가 줄어들지만,
> 후보 수를 제한하면 "Graph가 진짜 관련 있는 소수의 청크만 RRF에 참여"하게 됨.
> 이 방식이 가중치 조절보다 정교하며, Graph의 가치를 훼손하지 않음.

#### RRF 채널별 최종 설정

| 채널 | 가중치 | RRF 후보 수 | 비고 |
|------|--------|-----------|------|
| vector | 1.0 | top_k * 2 (20건) | 기존 유지 |
| keyword | 1.0 | top_k * 2 (20건) | 기존 유지 |
| sparse | 0.7 | top_k * 2 (20건) | 기존 유지 |
| graph | 0.8 | **3건 (신규 제한)** | `graph_search_top_k` 설정으로 분리 |

#### 효과
- Graph primary source 결과가 자연스럽게 **최대 1~2건**으로 제한
- Vector/Keyword가 대부분의 primary source가 됨
- Graph 가중치(0.8)는 그대로 유지 → RRF 부스트 효과는 보존
- 채널별 가중치 변경 없이, 후보 수 제한만으로 해결

#### 테스트 결과 (리빌드 후 검증)
| 항목 | 변경 전 | 변경 후 |
|------|---------|---------|
| Graph primary | 8/10 (80%) | 0/10 (0%) |
| Vector primary | 1/10 (10%) | 7/10 (70%) |
| Keyword primary | 1/10 (10%) | 3/10 (30%) |

### 7. 메모리 정리 가이드 작성 및 QA 재테스트 (주요)

#### 상세 내용
- `docs/05_development/03_pre_test_resource_cleanup.md` (DEV-003) 작성/보강
  - Linux file cache 해제 (`drop_caches`) 절차 추가
  - PowerShell 명령어: `wsl -u root sh -c "echo 3 > /proc/sys/vm/drop_caches"`
  - WSL2 메모리 반환 불가 구조적 한계 문서화 (Section 7)
  - Claude(Main) 워크플로우: 사용자에게 `drop_caches` 요청 → 확인 → QA 위임
- QA 에이전트 프롬프트에 리소스 정리 필수 규칙 추가
- 리소스 정리 후 QA 재테스트: **12/12 PASS**, Chat API 80초 → 47초 (41% 개선)

#### WSL2 메모리 검증 (사용자와 공동)
| 측정 위치 | 항목 | drop_caches 전 | drop_caches 후 |
|----------|------|----------------|----------------|
| WSL2 내부 | buff/cache | 5.6 GiB | 2.4 GiB (**-3.2 GiB**) |
| WSL2 내부 | free | 707 MiB | 3.2 GiB (**+2.5 GiB**) |
| Windows | 사용 중 | 13.1 GB | 13.3 GB (**변화 없음**) |

### 8. RummiArena 프로젝트 운영 가이드 작성 (부가)

#### 상세 내용
- RummiArena 프로젝트의 컨테이너 운영 가이드 신규 작성
- 위치: `/mnt/d/.../RummiArena/docs/06-operations/01-container-operations-guide.md`
- hybrid-rag와 병행 운용 금지 원칙, 프로젝트 전환 체크리스트 포함
- 포트 충돌 테이블 (5432, 3000, 8080), 메모리 예산 (~4GB)

### 9. SCRUM-101 source_type 오버라이드 버그 수정 (주요 - Critical)

#### 상세 내용
- **근본 원인**: `search.py`, `rag_workflow.py`에서 `contributing_sources`에 "graph" 포함 시 `source_type="graph"` 강제 설정
- **결과**: UI에서 모든 검색 결과가 Graph primary source로 표시
- **수정**: RRF가 계산한 실제 primary source(`r.source`)를 그대로 사용
- **추가**: `rag_pipeline.py`에서 graph_context를 graph primary뿐 아니라 matched_entities 있는 모든 소스에 연결
- **검증**: UI에서 Vector 3/Keyword 2 정상 분포 확인

### 10. UI 소스코드 점검 및 프론트엔드 수정 (주요)

#### 상세 내용
- TechLead + Frontend 에이전트 합동 점검
- `SourceCitation.tsx`: sourceType 배지가 Graph 버튼과 독립적으로 항상 표시되도록 수정
- `SearchResultCard.tsx`: SOURCE_TYPE_CONFIG 맵 추가, 헤더에 소스 타입 배지 표시
- `useChatSearch.ts`, `useStreamingSearch.ts`, `sse.ts`: hasEmbedding 필드 매핑 추가
- QA 소스코드 점검: `rag_pipeline.py` graph_context 일관성 수정 발견 및 적용

### 11. "< Graph" 버튼 의도된 동작 문서화 (주요)

#### 상세 내용
- 사용자 확인: "의도된 것이다"로 명시 요청
- `04_user_manual.md` §3.5: 검색 결과 UI 태그 설명 신규 섹션 추가
- `34_graph_search_rrf_tuning.md` §5.3~5.5: 프론트엔드 태그, SCRUM-101 제거, 검증 포인트
- "< Graph" 버튼 = 그래프 시각화 패널 열기 (source type 표시가 아님)

### 12. OPS-035 Reranker 이중 실행 트러블슈팅 문서 (주요)

#### 상세 내용
- `docs/07_maintenance/35_reranker_dual_execution_troubleshooting.md` 신규 작성
- **분류**: 구현 오류 (Implementation Defect) — 설계 오류가 아님
- **근거**: STORY-032 테스트 계획서에서 Reranker 통합 대상은 `HybridRetriever`만 명시, `SearchService`는 수정 대상 아님
- **원인**: 구현 시 `SearchService.hybrid_search()`에 설계 외 Reranker 중복 구현
- 초기 "설계 오류(Architecture Defect)"로 잘못 분류 → 사용자 지적 → "구현 오류" 정정

---

## 주요 결정사항

| 결정 | 내용 | 근거 |
|------|------|------|
| Reranker ON 유지 | Chat 경로에서 Reranker 스킵하지 않고 유지 | 검색 품질 score 0.98+ 확보 (사용자 판단) |
| 타임아웃 180초 | Nginx/Gateway 120→180초 확대 | Chat: 검색(1s)+Reranker(33s)+LLM(30s)=65s, 여유 포함 |
| ONNX 2코어 제한 | 전체 CPU 점유 → 2코어로 제한 | Healthcheck 응답 보장, 컨테이너 재시작 방지 |
| Nginx upstream 방어 | 변수 방식 lazy resolve 적용 | 중지된 서비스가 Nginx를 죽이지 않도록 |
| **Graph RRF 후보 수 3건 제한** | **가중치(0.8) 유지 + 후보 수만 제한** | **사용자 피드백: "graph만 뒤지는 것처럼 보인다" — 가중치 조절보다 후보 수 제한이 더 정교한 접근** |
| 테스트 전 drop_caches 필수 | Claude(Main)이 사용자에게 요청 후 확인 | WSL2 내부 buff/cache가 3~6GiB 점유, 테스트 전 해제 필수 |
| hybrid-rag/RummiArena 병행 금지 | 프로젝트 전환 시 반드시 이전 프로젝트 down | 16GB RAM에서 양쪽 컨테이너 병행 운용 불가 |
| **SCRUM-101 오버라이드 제거** | **RRF primary source를 downstream에서 임의 변경하지 않음** | **모든 결과가 Graph로 표시되는 버그 — RRF 결과 존중** |
| **"< Graph" 버튼 = 의도된 동작** | **source type 표시가 아닌 그래프 시각화 패널 열기 버튼** | **사용자 확인: "의도된 것이다"** |
| **Reranker 이중 실행 = 구현 오류** | **설계(STORY-032)는 HybridRetriever에만 명시** | **SearchService 중복 구현은 설계 범위 외 — 구현 오류** |

---

## 변경된 파일 목록

```
knowledge_service/
├── src/app/
│   ├── api/routes/search.py          # Reranker ON 유지 (원복)
│   ├── services/search.py            # P0-1 skip_reranking, P0-2 후보 제한, P1-1 ES timeout, Reranker timeout 60s, Graph RRF 후보 수 제한
│   ├── core/config.py                # graph_search_top_k=3 설정 추가 (Graph RRF 후보 수 분리)
│   └── rag/
│       ├── retriever.py              # P0-1 skip_reranking=True, P0-2 fetch_k/rerank 제한
│       └── bge_reranker.py           # P1-2 ONNX 2코어 제한
├── gateway/src/main/resources/
│   └── application.yml               # response-timeout 120→180s
├── docs/04_testing/13_user_acceptance_test/
│   └── 01_uat_2026-03-09.md          # UAT 보고서 (신규)
├── docs/05_development/
│   └── 03_pre_test_resource_cleanup.md  # DEV-003 리소스 정리 가이드 (보강)
├── docs/07_maintenance/
│   └── 34_graph_search_rrf_tuning.md    # OPS-034 Graph 검색 RRF 튜닝 가이드 (신규, 중요)
infrastructure/docker/
├── nginx/
│   ├── nginx.conf                    # Docker DNS resolver 추가
│   └── conf.d/default.conf           # Grafana 변수 upstream, search timeout 180s
.claude/agents/
└── qa-engineer.md                    # Mock 금지 규칙 + 리소스 정리 필수 추가
knowledge_service/
├── src/app/
│   ├── api/routes/search.py          # SCRUM-101 graph 오버라이드 제거
│   ├── agents/rag_workflow.py        # SCRUM-101 오버라이드 제거 + hasEmbedding
│   └── services/rag_pipeline.py      # graph_context 일관성 수정 (모든 소스에 적용)
├── frontend/src/
│   ├── features/search/components/
│   │   ├── SourceCitation.tsx         # sourceType 배지 항상 표시, Graph 버튼 독립
│   │   └── SearchResultCard.tsx       # SOURCE_TYPE_CONFIG 맵, 소스 타입 배지
│   ├── features/search/hooks/
│   │   ├── useChatSearch.ts           # hasEmbedding 필드 매핑
│   │   └── useStreamingSearch.ts      # hasEmbedding 필드 매핑
│   └── shared/api/sse.ts             # hasEmbedding 인터페이스 추가
├── docs/08_deliverables/
│   └── 04_user_manual.md             # §3.5 검색 결과 UI 태그 설명 (의도된 동작 명시)
└── docs/07_maintenance/
    └── 34_graph_search_rrf_tuning.md  # §5.3~5.5 프론트엔드/SCRUM-101/검증 추가
work_logs/
├── 01_daily_logs/2026/03-March/
│   └── 2026-03-09.md                 # 작업 #9~#11 추가
└── 02_session_logs/
    └── 2026-03-09_uat_perf_tuning.md  # 이 세션 로그 (업데이트)
```

---

## 현재 프로젝트 상태

### 인프라 상태
| 항목 | 값 |
|------|-----|
| 총 컨테이너 | 21개 (12 실행 + 9 중지) |
| 핵심 서비스 | 12개 Running (ai-service, backend, gateway, frontend, nginx, ES, Neo4j, PG, Redis, Keycloak, keycloak-db, minio) |
| 중지된 서비스 | 9개 (grafana, prometheus, promtail, loki, jaeger, kibana, nginx-exporter, postgres-exporter, redis-exporter) |

### 메모리 사용 현황
| 항목 | 값 |
|------|-----|
| 시스템 메모리 | 13Gi 총, 7.6Gi 사용 (53%) |
| Swap 사용 | 1.9Gi / 4.0Gi (48%) |
| ES 메모리 | 1.45GiB / 2.5GiB (58%) |
| AI Service | 3.05GiB / 9GiB (34%) |
| Neo4j | 802MiB / 2GiB (39%) |
| Docker 이미지 | 36.26GB (31개) |
| Docker 빌드 캐시 | 18.06GB |

### ES 데이터
| 항목 | 값 |
|------|-----|
| knowledge_chunks | 42,612 청크 |
| Neo4j Entity | 91,673개 |
| Neo4j 관계 | 746,667개 |

---

## 다음 작업 (Action Items)

### P1 (High)
1. SSE 스트리밍 엔드포인트 수정 — workflow 완료 전 부분 응답 yield (QA BUG-02)
2. Docker 빌드 캐시 정리 (18GB 회수 가능)
3. QA 에이전트 프롬프트 업데이트 (Mock 금지 규칙 추가 — 이전 세션 Pending)

### P2 (Medium)
4. search_type enum 검증 추가 (QA BUG-04)
5. Neo4j 외부 인증 패스워드 동기화 (QA BUG-03)
6. Reranker 경량 모델(MiniLM) 또는 INT8 양자화 검토
7. ONNX 코어 수 4코어로 상향 테스트 (메모리 충분 시)

### P3 (Low)
8. k6 부하 테스트 (P95 Latency 검증)
9. 중지된 Observability 서비스의 Nginx upstream 전부 변수 방식 변환

---

## 리스크 모니터링

| 리스크 | 확률 | 영향 | 상태 | 대응 |
|--------|------|------|------|------|
| Chat 응답 80초 UX | High | High | Monitoring | GPU 도입 or 경량 Reranker 전환 |
| 메모리 53% 사용 | Med | Med | Monitoring | 불필요 컨테이너 중지 완료, 빌드 캐시 정리 필요 |
| Swap 48% 사용 | Med | Med | Monitoring | .wslconfig 메모리 상향 검토 |
| SSE 스트리밍 미작동 | Med | Med | Open | workflow 부분 응답 리팩토링 필요 |

---

## 사용된 도구 및 에이전트

| 도구/에이전트 | 용도 |
|--------------|------|
| QA Engineer Agent | UAT 23건 테스트 실행 + 보고서 작성 |
| TechLead Agent | Chat API 성능 병목 6건 분석 |
| RAG Engineer Agent | 성능 튜닝 5건 구현 |
| Infra Engineer Agent | 불필요 컨테이너 10개 중지 |

---

## 세션 통계

| 항목 | 값 |
|------|-----|
| 수정된 파일 | 20개 |
| 신규 생성 파일 | 6개 (UAT 보고서, 세션 로그, 리소스 정리 가이드, RRF 튜닝 가이드, RummiArena 운영 가이드, OPS-035 트러블슈팅) |
| Docker 빌드 | 7회 (ai-service 5회, frontend 1회, nginx 1회) |
| 에이전트 투입 | 9개 (QA x2, TechLead x2, RAG, Infra, Frontend, CodeDocumenter x2) |
| UAT 테스트 | 18/18 PASS (100%) |
| 리소스 정리 후 QA 재테스트 | 12/12 PASS, Chat 80→47초 (41% 개선) |
| SCRUM-101 수정 | Backend 2파일 + Frontend 5파일 + 문서 2파일 |
| OPS-035 | Reranker 이중 실행 트러블슈팅 (구현 오류 분류) |
| 커밋 | 4건 (9b500a3, 73a684b, 68fcd34, d2bbbdd) |

---

*기록자: Claude Code (Opus 4.6)*
*기록 시간: 2026-03-09 17:48 KST (마감 보완)*
