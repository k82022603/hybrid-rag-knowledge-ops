# Claude Code Development Guidelines

🤖 Hybrid RAG Knowledge Operations 프로젝트 개발 규칙

**Version**: 2.3 | **Updated**: 2026-01-15

---

## 📋 프로젝트 개요

| 항목 | 내용 |
|------|------|
| **프로젝트** | Graph RAG 기반 지능형 지식 검색 시스템 |
| **기술스택** | Python 3.11+, SpringBoot 3.x, React 18, LangGraph |
| **데이터베이스** | PostgreSQL (SSOT), Neo4j (Graph), Elasticsearch (Vector) |
| **런타임 LLM** | DeepSeek V3.2 (95% 비용 절감) |

---

## 🗂️ 폴더 구조 및 파일 생성 규칙

```
hybrid-rag-knowledge-ops/
├── knowledge_service/
│   ├── src/app/
│   │   ├── api/routes/      # API 엔드포인트
│   │   ├── services/        # 비즈니스 로직
│   │   ├── models/          # 데이터 모델
│   │   ├── core/            # 핵심 기능
│   │   └── utils/           # 유틸리티
│   ├── src/tests/           # 테스트 코드
│   ├── docs/
│   │   ├── 01_planning/     # 구현 계획
│   │   ├── 02_design/       # 기술 설계
│   │   └── results/         # 실행 결과
│   └── ...
├── work_logs/               # 📝 작업 일지 관리
│   ├── daily_logs/          # 일일 작업 일지 (YYYY/MM-Month/)
│   ├── vibe_logs/           # 바이브 코딩 일지 (영감/아이디어)
│   └── README.md
└── infrastructure/          # 인프라 설정
```

### 파일 명명 규칙
- **Python 파일**: `snake_case.py`
- **클래스**: `PascalCase`
- **함수/변수**: `snake_case`
- **상수**: `UPPER_SNAKE_CASE`

---

## 🔧 프롬프트 작성 가이드

### ❌ 나쁜 프롬프트
```
"메타데이터 추출 함수 만들어줘"
```

### ✅ 좋은 프롬프트
```
"knowledge_service/src/app/services/metadata_extraction.py에
메타데이터 추출 함수를 추가해줘.

요구사항:
- 함수명: extract_temporal_metadata
- 입력: document_text (str)
- 출력: dict (document_type, project_name, valid_start_date, valid_end_date)
- API 키: 환경변수 DEEPSEEK_API_KEY
- 에러 핸들링: 실패 시 None 반환, 로깅 필수"
```

**핵심**: 파일 경로 + 함수명 + 입출력 + 에러 처리를 명시

---

## 🔐 보안 규칙

```python
# ✅ 필수
api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    raise ValueError("API key not set")

# ❌ 금지
api_key = "sk-xxx..."  # 하드코딩 절대 금지
```

- API 키는 반드시 환경변수 사용
- 민감 데이터는 `.env` 파일에 저장 (git 제외)
- 입력값 검증 필수

---

## 🔄 커밋 메시지 형식

```
[TYPE] 간단한 설명 (50자 이내)

- 변경 사항 1
- 변경 사항 2

관련 이슈: #123
```

### 타입
| 타입 | 용도 |
|------|------|
| `[FEAT]` | 새 기능 |
| `[FIX]` | 버그 수정 |
| `[REFACTOR]` | 코드 재구성 |
| `[TEST]` | 테스트 추가 |
| `[DOCS]` | 문서 수정 |
| `[CHORE]` | 빌드, 의존성 |

---

## ✅ 코드 품질 체크리스트

새 기능 추가 시 확인:

- [ ] docstring 작성
- [ ] type hints 추가
- [ ] 에러 핸들링 추가
- [ ] 로깅 추가
- [ ] 유닛 테스트 작성 (80%+ 커버리지)
- [ ] Black/isort 스타일 정렬

---

## 📝 작업 일지

```powershell
# 생성
.\scripts\create_worklog.ps1

# 커밋
.\scripts\commit_worklog.ps1
```

**위치**: `work_logs/daily_logs/YYYY/MM-Month/YYYY-MM-DD.md`

---

## 🌿 브랜치 전략

| 브랜치 | 용도 |
|--------|------|
| `main` | 프로덕션 (보호됨) |
| `develop` | 개발 통합 |
| `feature/*` | 기능 개발 |
| `fix/*` | 버그 수정 |

---

## 📚 참고 문서

- [PLAN.md](./PLAN.md) - 프로젝트 계획 및 현재 상태
- [README.md](./README.md) - 프로젝트 소개 및 설치 가이드
- [상세 설계서](./knowledge_service/docs/02_design/hybrid_rag_platform_detailed_design.md)
