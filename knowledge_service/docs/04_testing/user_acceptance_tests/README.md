# User Acceptance Tests (UAT)

사용자 수락 테스트 가이드 및 결과서 관리 폴더

---

## 폴더 구조

```
user_acceptance_tests/
├── README.md                                        # 이 파일
├── 00_full_cycle_test_guide.md                      # Full Cycle 테스트 가이드 (마스터)
├── 01_authentication_login_test_2026-02-04.md       # 인증/로그인 테스트 결과 ✅
├── 02_document_upload_test_YYYY-MM-DD.md            # 문서 업로드 테스트 (예정)
├── 03_document_processing_test_YYYY-MM-DD.md        # 문서 처리 테스트 (예정)
├── 04_search_functionality_test_YYYY-MM-DD.md       # 검색 기능 테스트 (예정)
├── 05_rag_chat_test_YYYY-MM-DD.md                   # RAG 대화 테스트 (예정)
├── 06_knowledge_graph_test_YYYY-MM-DD.md            # Knowledge Graph 테스트 (예정)
├── 07_monitoring_dashboard_test_YYYY-MM-DD.md       # 모니터링 테스트 (예정)
└── ...
```

---

## 파일 명명 규칙

```
{순번}_{테스트영역}_{날짜}.md

예시:
- 00_full_cycle_test_guide.md          # 테스트 가이드 (순번 00)
- 01_authentication_login_test_2026-02-04.md
- 02_document_upload_test_2026-02-05.md
```

---

## 테스트 진행 현황

| # | 테스트 영역 | 가이드 섹션 | 상태 | 날짜 | 결과 |
|---|------------|-------------|------|------|------|
| 00 | Full Cycle Test Guide | - | 마스터 문서 | - | - |
| 01 | Authentication & Login | 4.1 | **완료** | 2026-02-04 | ✅ PASS |
| 02 | Document Upload | 4.2 | **완료** | 2026-02-04 | ✅ PASS |
| 03 | Document Processing | 4.3 | 예정 | - | ⏸️ AI Service 연동 필요 |
| 04 | Search Functionality | 4.4 | 예정 | - | ⏸️ 임베딩 파이프라인 필요 |
| 05 | RAG Chat (Q&A) | 4.5 | 예정 | - | ⏸️ 임베딩 파이프라인 필요 |
| 06 | Knowledge Graph | 4.6 | 예정 | - | ⏸️ Neo4j 동기화 필요 |
| 07 | Monitoring Dashboard | 5 | 예정 | - | - |

### 다음 단계 (임베딩 파이프라인)

문서 업로드 완료 후 자동 처리 파이프라인 구현 필요:

```
[PostgreSQL: uploaded] → [AI Service] → [Elasticsearch] + [Neo4j]
```

| 단계 | 설명 | 상태 |
|------|------|------|
| 문서 파싱 | Unstructured로 텍스트 추출 | 예정 |
| 청킹 | 의미 단위로 분할 | 예정 |
| 임베딩 | 벡터 생성 (DeepSeek/OpenAI) | 예정 |
| ES 저장 | Elasticsearch 벡터 인덱싱 | 예정 |
| Neo4j 저장 | Knowledge Graph 동기화 | 예정 |

---

## 테스트 계정 정보

| 계정 | Email | Password | 권한 |
|------|-------|----------|------|
| Admin | admin@example.com | admin1234 | ADMIN, USER |

---

## 테스트 환경

- **URL**: http://localhost
- **Environment**: Development (Docker Compose)
- **Version**: Sprint 07

---

## 문서 유형

| 유형 | 순번 | 설명 |
|------|------|------|
| **가이드** | 00 | 테스트 시나리오 및 절차 정의 |
| **결과서** | 01~ | 실제 테스트 수행 결과 기록 |

---

*Last Updated: 2026-02-04*
