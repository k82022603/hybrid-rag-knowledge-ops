# STORY-063: Docling 라이브러리 Docker 이미지 포함 및 테스트 활성화

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-53 |
| **Epic** | EPIC-001 |
| **Status** | To Do |
| **Priority** | Medium |
| **Story Points** | 3 |
| **Assignee** | Infra (Primary), ETL (Secondary) |
| **Sprint** | 4 |

---

## User Story

**As a** ETL 엔지니어,
**I want** Docker 이미지에 Docling 라이브러리가 사전 설치되어 있어,
**So that** PDF/DOCX/PPTX 문서 파싱 기능을 테스트하고 프로덕션에서 사용할 수 있음.

---

## 배경

- `knowledge_service/pyproject.toml`에 `docling = "^2.60.0"`으로 선언되어 있음
- 실제 환경에 설치되지 않아 `TestDoclingAdapter::test_parse_pdf_with_tables` 등 테스트가 skip 중
- PyTorch 의존성이 있어 무거움 - Docker 이미지에 사전 포함 필요
- Docling은 PDF, DOCX, PPTX 등 다양한 문서 포맷의 파싱을 지원하는 라이브러리

---

## Acceptance Criteria

- [ ] **Given** Docker 이미지가 빌드됨, **When** `python -c "import docling"` 실행, **Then** 에러 없이 성공
- [ ] **Given** Docling이 설치된 환경, **When** `TestDoclingAdapter` 테스트 스위트 실행, **Then** 전체 PASS (skip 없음)
- [ ] **Given** Docker 이미지 빌드 완료, **When** 이미지 크기 비교, **Then** PyTorch CPU only 빌드로 크기 최적화 확인
- [ ] **Given** Docling 라이브러리, **When** PDF/DOCX/PPTX 파일 파싱, **Then** 테이블 포함 구조화된 데이터 추출 성공

---

## Tasks

### Infra Engineer (Primary)
- [ ] knowledge_service Dockerfile에 `docling>=2.60.0` 설치 추가
- [ ] PyTorch CPU 전용 빌드로 이미지 크기 최적화 (`--extra-index-url https://download.pytorch.org/whl/cpu`)
- [ ] Docker 이미지 빌드 및 크기 검증
- [ ] `import docling` 성공 확인

### ETL Engineer (Secondary)
- [ ] `TestDoclingAdapter` skip 마크 제거 (`@pytest.mark.skipif` 또는 `pytest.importorskip` 조건 수정)
- [ ] PDF/DOCX/PPTX 파싱 통합 테스트 실행 및 검증
- [ ] 테스트 결과 문서화

---

## 기술 노트

### 구현 방향

1. **Dockerfile 수정** (Infra):
   - PyTorch CPU only 인덱스를 우선 사용하여 GPU 관련 패키지 제외
   - `docling>=2.60.0` pip install 추가
   - 멀티스테이지 빌드로 최종 이미지 크기 최소화

2. **테스트 활성화** (ETL):
   - `test_parse_pdf_with_tables` 등 skip 조건 제거
   - 테스트용 샘플 문서 (PDF/DOCX/PPTX) 확인

### Dockerfile 수정 예시

```dockerfile
# PyTorch CPU only
RUN pip install --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    docling>=2.60.0
```

### 영향 범위

- `knowledge_service/Dockerfile` (또는 관련 Docker 빌드 파일)
- `knowledge_service/pyproject.toml` (이미 선언됨, 변경 불필요)
- `knowledge_service/src/tests/` (skip 마크 제거)
- Docker 이미지 크기 증가 예상 (PyTorch CPU ~500MB)

---

## 테스트 계획

- [ ] Unit Test: `TestDoclingAdapter::test_parse_pdf_with_tables` PASS 확인
- [ ] Integration Test: PDF/DOCX/PPTX 각 포맷별 파싱 테스트
- [ ] Docker Test: 빌드된 이미지에서 `import docling` 성공 확인
- [ ] Size Test: 이미지 크기 비교 (before/after)

---

## 참고 자료

- [Docling GitHub](https://github.com/DS4SD/docling)
- [PyTorch CPU Only Installation](https://pytorch.org/get-started/locally/)
- `knowledge_service/pyproject.toml` - 패키지 선언 확인
- `knowledge_service/src/tests/` - TestDoclingAdapter 위치
