# Session Log - 2026-02-11

**Session ID**: 2026-02-11_ragas_v6_doc_cleanup
**시작 시간**: 02:50 KST
**종료 시간**: 04:35 KST
**모델**: Claude Opus 4.6 (claude-opus-4-6)

---

## 세션 요약

RAGAS v6 50쿼리 평가 실행 (JWT 자동 갱신으로 v5 ERR 이슈 해결) + knowledge_service/docs/ 전체 문서 정리 (6개 폴더 번호 매기기 + 재구성). 팀원 2명(RAG Engineer, ETL Engineer) SCRUM-101/103 완료 후 shutdown.

---

## 이전 상태

- RAGAS v5: 50쿼리 중 8건 JWT 만료 ERR (Q43~Q50)
- docs/ 폴더: 번호 체계 없이 파일 산재, results/ 폴더에 혼재
- SCRUM-101 (Graph Search), SCRUM-103 (Reranker) 진행 중

---

## 완료된 작업

### 1. RAGAS v6 50쿼리 평가

**스크립트**: `knowledge_service/scripts/rcsv_comparison_eval_v4.py` (신규)

| 개선사항 | 상세 |
|---------|------|
| JWT 자동 갱신 | 15쿼리마다 재로그인 (TOKEN_REFRESH_INTERVAL=15) |
| 데이터 품질 분석 | GLYPH 아티팩트 탐지 (DataQualityAnalyzer 클래스) |
| Reranker 상태 확인 | 사전 health check |
| LLM Judge 재시도 | DeepSeek API 에러 시 3회 retry |

**결과 비교 (v5 → v6)**:

| 항목 | v5 | v6 | 변화 |
|------|-----|-----|------|
| JWT 에러 | 8/50 (16%) | **0/50** | 완전 해결 |
| HIGH 등급 | 15건 (35.7%) | **33건 (66.0%)** | +30.3%p |
| NONE 등급 | 11건 (26.2%) | **5건 (10.0%)** | -16.2%p |

**도메인별 HIGH 비율**:
- entity_relation: 100% (3/3)
- factual: 100% (7/7)
- comparative: 100% (2/2)
- legal: 87.5% (7/8)
- multi_hop: 75% (3/4)
- semantic: 66.7% (4/6)
- graph_entity: 35.3% (6/17) ← 개선 필요
- keyword: 33.3% (1/3)

**결과 파일**: `04_testing/ragas/results/hrkp_ragas_v6_report_2026-02-11.md`

### 2. rag_quality_improvement_manual.md v4.0 업데이트

`knowledge_service/docs/07_maintenance/20_rag_quality_improvement_manual.md` (v3.0 → v4.0):
- Section 3 추가: ONNX Runtime 최적화 (벤치마크, 흐름도, 트러블슈팅)
- Section 9 추가: 데이터 품질 이슈 및 대응 (GLYPH 아티팩트, 문서 편향)
- 전체 12개 섹션으로 재구성

### 3. 문서 정리 (6개 폴더)

| 폴더 | 작업 내용 | 파일 수 |
|------|----------|---------|
| `04_testing/` | 67개 파일 → 12개 폴더 재구성, 신규 3개(ragas/, analysis/, staging/) | 67 |
| `docs/results/` | 전체 파일 이동 후 폴더 삭제 | 8→0 |
| `05_development/` | 생성일 순서 번호 매기기 (01~11) | 11 |
| `06_deployment/` | 생성일 순서 번호 매기기 (01~13) | 13 |
| `07_maintenance/` | 생성일 순서 번호 매기기 (01~20) | 20 |
| `02_design/` | 설계문서 16개 번호 매기기, 리뷰 4개 이동, tech_assessment 5개 정리 | 16+9 |

**참조 링크 업데이트**: CLAUDE.md, PLAN.md, README.md 등 100개+ 파일

### 4. CLAUDE.md broken 링크 수정

- `./docs/claude_code_virtual_team_alm_guide/` → `./docs/technical_assessment/claude_code_virtual_team_alm_guide/`
- `01_unit_integration_test_plan.md` → `test_plans/00_unit_integration_test_plan.md`

### 5. 팀원 작업 완료 (Agent Teams)

**RAG Engineer - SCRUM-103**:
- Reranker 전 경로 일관 연결 검증
- 버그 3건 수정: /chat/stream Reranker 미경유, 싱글톤 패턴 결함, 로그 카운트 오류
- 수정 파일: search.py, rag_workflow.py, retriever.py

**ETL Engineer - SCRUM-101**:
- Graph Search source_type 미출현 근본 원인 해결
- Neo4j chunk_id NULL 99.9% → COALESCE(c.chunk_id, c.id) 수정
- RRF Graph 가중치 0.3 → 0.8 조정
- 수정 파일: search.py, config.py, search.py(routes)

---

## 교훈

### nohup 필수 (재확인)
- `docker exec -d`로 실행한 v6 평가가 셸 끊김으로 중단됨
- `docker exec bash -c 'nohup python3 -u ... > log 2>&1 &'`로 재실행하여 해결
- Memory에 이미 기록된 교훈이었으나 재발

### v6 평가 핵심 인사이트
- JWT 자동 갱신만으로 HIGH 비율 35.7% → 66.0% 상승 (v5 ERR 구간 복구)
- graph_entity 도메인은 chunk_id NULL 이슈 (ETL SCRUM-101 수정)와 관련
- keyword 도메인 약세는 지식베이스 문서 부족이 원인 (데이터 이슈)

---

## 수정된 파일 요약

### 신규 파일
- `knowledge_service/scripts/rcsv_comparison_eval_v4.py` - RAGAS v6 평가 스크립트
- `04_testing/ragas/results/hrkp_ragas_v6_2026-02-11.json` - 평가 결과 JSON
- `04_testing/ragas/results/hrkp_ragas_v6_report_2026-02-11.md` - 평가 보고서
- `work_logs/session_logs/2026-02-11_ragas_v6_doc_cleanup.md` - 본 세션 로그

### 수정 파일
- `CLAUDE.md` - broken 링크 수정 + 참조 경로 업데이트
- `knowledge_service/docs/07_maintenance/20_rag_quality_improvement_manual.md` - v4.0
- 100개+ 마크다운 파일 - 문서 정리에 따른 경로 참조 업데이트

### 파일 이동/이름 변경
- `04_testing/`: 30개 파일 폴더별 재배치
- `05_development/`: 11개 파일 번호 매기기
- `06_deployment/`: 13개 파일 번호 매기기
- `07_maintenance/`: 20개 파일 번호 매기기
- `02_design/`: 16개 설계문서 + 4개 리뷰 + 5개 기술평가 정리
- `docs/results/`: 8개 파일 이동, 폴더 삭제
