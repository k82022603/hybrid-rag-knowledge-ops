# Claude Code Development Guidelines

🤖 Hybrid RAG Knowledge Operations 프로젝트의 Claude Code 기반 개발 규칙

---

## 📋 프로젝트 개요

- **프로젝트명**: Hybrid RAG Knowledge Operations
- **기술스택**: Python 3.11+, LangGraph, Neo4j, Elasticsearch, PostgreSQL
- **목표**: Graph RAG 기반 지능형 지식 검색 시스템
- **AI 도구**: Claude Code, DeepSeek, OpenAI o1/GPT-4o

---

## 🎯 개발 원칙

### 1. 코드 우선주의 (Code First)
- Claude Code를 최우선 개발 도구로 사용
- 수동 코딩보다 자연어 지시로 AI 기반 생성 선호
- 프롬프트는 구체적이고 명확하게 작성

### 2. 구조화된 폴더 관리
```
hybrid-rag-knowledge-ops/
├── knowledge_service/
│   ├── src/app/               # 비즈니스 로직
│   ├── src/scripts/           # 초기화 스크립트
│   ├── data/                  # 입력 데이터
│   ├── docs/                  # 프로젝트 문서
│   │   ├── 01_planning/       # 구현 계획
│   │   ├── 02_design/         # 기술 설계 및 검토
│   │   │   └── technical_assessment/  # 기술 검토 문서
│   │   └── work_logs/         # 작업 일지 (git 추적)
│   └── results/               # 실행 결과
├── infrastructure/            # 인프라 설정
│   └── docker/                # Docker 설정
├── scripts/                   # 공통 유틸 스크립트
│   ├── create_worklog.ps1     # 작업 일지 생성 (PowerShell)
│   ├── create_worklog.sh      # 작업 일지 생성 (Bash)
│   ├── commit_worklog.ps1     # 작업 일지 커밋 (PowerShell)
│   ├── commit_worklog.sh      # 작업 일지 커밋 (Bash)
│   └── daily_worklog.ps1      # 통합 스크립트 (생성+커밋+푸시)
└── storage/                   # 실제 DB 저장소 (git 제외)
```

### 3. 단일 진실 공급원 (Single Source of Truth)
- **PostgreSQL**: 마스터 레코드, 시계열 데이터
- **Neo4j**: 관계 그래프
- **Elasticsearch**: 벡터 + 메타데이터 통합 저장

### 4. 비용 의식 (Cost Awareness)
- DeepSeek-V3.2 활용으로 93% 비용 절감
- 불필요한 API 호출 최소화
- 캐시 히트 최적화

---

## 🔧 프롬프트 작성 가이드

### ❌ 나쁜 프롬프트
```
"메타데이터 추출 함수 만들어줘"
```

### ✅ 좋은 프롬프트
```
"knowledge_service/src/app/services/metadata_extraction.py에
DeepSeek-V3.2 Non-thinking 모드를 사용한 메타데이터 추출 함수를 추가해줘.

요구사항:
- 함수명: extract_temporal_metadata
- 입력: document_text (str), use_deepseek (bool)
- 출력: dict with keys:
  - document_type: str
  - project_name: str
  - valid_start_date: YYYY-MM-DD
  - valid_end_date: YYYY-MM-DD
  - entities: dict
  - summary: str

구현 세부사항:
- API 키는 환경변수 DEEPSEEK_API_KEY에서 로드
- 타임아웃: 30초
- 재시도 로직: 3회 (exponential backoff)
- 에러 핸들링: 실패 시 None 반환
- 추출된 메타데이터는 PostgreSQL + Elasticsearch + Neo4j에 자동 저장
- 로깅: INFO 레벨에서 프로세스 추적"
```

---

## 📝 개발 패턴

### Pattern 1: 기능 추가
```bash
claude-code "
[파일 경로]에 [기능 설명]을 추가해줘.
- 입력: [파라미터]
- 출력: [반환값]
- 사이드 이펙트: [DB 저장 등]
- 에러 핸들링: [예외 처리]
"
```

### Pattern 2: 버그 수정
```bash
claude-code "
[파일 경로]의 [함수명]에서 발생하는 [버그 증상]을 수정해줘.
현상: [어떻게 동작하는가]
기대: [어떻게 동작해야 하는가]
근본원인 추측: [가능한 원인]
"
```

### Pattern 3: 테스트 작성
```bash
claude-code "
[파일 경로]에 대한 유닛 테스트를 pytest로 작성해줘.
테스트 케이스:
1. [정상 케이스]
2. [엣지 케이스]
3. [에러 케이스]
목표 커버리지: 80%+
"
```

### Pattern 4: 리팩토링
```bash
claude-code "
[파일 경로]의 [부분]을 리팩토링해줘.
목표:
- 코드 가독성 향상
- 중복 제거
- 성능 개선
제약조건:
- 외부 API 변화 없음
- 100% 역호환성 유지
"
```

---

## 🗂️ 파일 생성 규칙

### 새 파일 생성이 필요한 경우
1. **데이터 모델** → `knowledge_service/src/app/models/`
2. **API 엔드포인트** → `knowledge_service/src/app/api/routes/`
3. **비즈니스 로직** → `knowledge_service/src/app/services/`
4. **핵심 기능** → `knowledge_service/src/app/core/`
5. **유틸리티** → `knowledge_service/src/app/utils/`
6. **테스트** → `knowledge_service/src/tests/`
7. **문서** → `knowledge_service/docs/`
   - 구현 계획: `docs/01_planning/`
   - 기술 설계: `docs/02_design/`
   - 기술 검토: `docs/02_design/technical_assessment/`
   - 작업 일지: `docs/work_logs/YYYY/MM-Month/`
8. **스크립트** → `scripts/` (프로젝트 루트)

### 파일 명명 규칙
- **Python**: snake_case (e.g., `metadata_extraction.py`)
- **클래스**: PascalCase (e.g., `MetadataExtractor`)
- **함수/변수**: snake_case
- **상수**: UPPER_SNAKE_CASE

---

## 🔐 보안 가이드

### API 키 관리
```python
# ✅ 올바른 방식
api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    raise ValueError("DEEPSEEK_API_KEY is not set")

# ❌ 절대 금지
api_key = "sk-xxx..."  # 하드코딩 금지!
```

### 데이터 검증
```python
# ✅ 입력 검증
if not document_text or len(document_text) == 0:
    raise ValueError("document_text cannot be empty")

# ❌ 검증 없음
def process(text):
    return text.split()  # IndexError 위험
```

---

## 💾 데이터베이스 작업

### PostgreSQL 작업
```python
# ✅ 올바른 방식
try:
    with get_db_connection() as conn:
        conn.execute(insert_query)
        conn.commit()
except Exception as e:
    logger.error(f"DB insert failed: {e}")
    conn.rollback()
    raise

# ❌ 에러 처리 없음
conn.execute(query)
```

### Elasticsearch 작업
```python
# ✅ 메타데이터 포함 저장
doc = {
    "text": chunk_text,
    "vector_field": embedding,
    "metadata": {
        "project_name": "ProjectA",
        "valid_start_date": "2023-01-01",
        "valid_end_date": "2024-12-31",
        "entities": {...}
    }
}
es.index(index="pdf-documents", document=doc)
```

### Neo4j 작업
```python
# ✅ 관계 생성
with driver.session() as session:
    session.run(
        "CREATE (p:Person {name: $name})-[:CREATED]->(k:Knowledge {id: $id})",
        name=author, id=knowledge_id
    )
```

---

## 🧪 테스트 가이드

### 테스트 작성 원칙
1. **3가지 타입**: Unit, Integration, E2E
2. **범위**: 최소 80% 코드 커버리지
3. **명명규칙**: `test_[함수명]_[시나리오]`

### 테스트 실행
```bash
# 모든 테스트 실행
poetry run pytest

# 특정 파일 테스트
poetry run pytest src/tests/test_search_engine.py

# 커버리지 리포트
poetry run pytest --cov=src/app
```

---

## 📦 의존성 관리

### 새 패키지 추가
```bash
# 개발 중 추가
poetry add langchain langchain-elasticsearch

# 개발 전용 패키지
poetry add --group dev pytest pytest-cov black

# pyproject.toml에 추가되며 poetry.lock 생성
```

### 버전 제약
- **핵심 의존성**: 메이저 버전 고정 (e.g., `langchain>=0.3.0,<0.4.0`)
- **부수 의존성**: 마이너 버전 고정 (e.g., `pytest>=7.0.0`)

---

## 🚀 배포 가이드

### 개발 환경
```bash
cd knowledge_service

# Python 의존성 설치
poetry install

# API 서버 시작 (권장)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 또는 CLI 모드
python src/app/main.py
```

### Docker 배포
```bash
cd infrastructure/docker
docker-compose up -d

# 상태 확인
docker-compose ps
docker-compose logs -f elasticsearch

# 데이터베이스 초기화
cd ../../knowledge_service
python src/scripts/init_databases.py
```

---

## 📊 로깅 및 모니터링

### 로깅 레벨
```python
import logging

logger = logging.getLogger(__name__)

logger.debug("상세 개발 정보")      # 개발 중
logger.info("시스템 동작 정보")     # 일반 실행
logger.warning("주의할 상황")       # 경고
logger.error("오류 발생")          # 에러
logger.critical("치명적 오류")      # 치명적
```

### 비용 추적
```python
from app.utils.cost_tracker import CostTracker

tracker = CostTracker()
with tracker.track("entity_extraction", model="deepseek-chat"):
    result = llm.invoke(prompt)

print(tracker.get_total_cost())
```

---

## 🔄 커밋 가이드

### 커밋 메시지 형식
```
[TYPE] 간단한 설명 (50자 이내)

상세 설명 (필요시)
- 변경 사항 1
- 변경 사항 2

관련 이슈: #123
```

### 타입 분류
- `[FEAT]` - 새 기능
- `[FIX]` - 버그 수정
- `[REFACTOR]` - 코드 재구성
- `[TEST]` - 테스트 추가
- `[DOCS]` - 문서 수정
- `[CHORE]` - 빌드, 의존성 등

### 좋은 커밋
```
[FEAT] Add temporal metadata extraction with DeepSeek

- Implement extract_temporal_metadata function
- Support both thinking and non-thinking modes
- Auto-save to PostgreSQL + Elasticsearch + Neo4j
- Add comprehensive error handling and retry logic

Resolves #45
```

---

## 📝 작업 일지 시스템

### 작업 일지 작성 원칙
1. **일일 기록**: 매일 작업 내용을 체계적으로 기록
2. **템플릿 활용**: 자동 생성되는 템플릿 사용
3. **Git 추적**: 작업 일지는 git으로 버전 관리
4. **자동화**: PowerShell/Bash 스크립트로 생성 및 커밋 자동화

### 작업 일지 생성
```powershell
# PowerShell (Windows)
.\scripts\create_worklog.ps1

# 특정 날짜 작업 일지 생성
.\scripts\create_worklog.ps1 -Date "2026-01-15"
```

```bash
# Bash (Linux/Mac)
./scripts/create_worklog.sh

# 특정 날짜 작업 일지 생성
./scripts/create_worklog.sh 2026-01-15
```

### 작업 일지 커밋
```powershell
# PowerShell
.\scripts\commit_worklog.ps1
```

```bash
# Bash
./scripts/commit_worklog.sh
```

### 통합 워크플로우 (생성 + 커밋 + 푸시)
```powershell
# PowerShell
.\scripts\daily_worklog.ps1 -Commit -Push
```

### 작업 일지 폴더 구조
```
docs/work_logs/
├── 2026/
│   ├── 01-January/
│   │   ├── 2026-01-12.md
│   │   └── 2026-01-13.md
│   └── 02-February/
│       └── 2026-02-01.md
└── README.md
```

### 작업 일지 템플릿
```markdown
# Work Log - YYYY-MM-DD

## 📌 Today's Focus
- [ ] 주요 작업 1
- [ ] 주요 작업 2

## ✅ Completed Tasks
1. **작업명**
   - 상세 내용

## 💡 Key Decisions
-

## 🐛 Issues & Blockers
- (없음)

## 📚 Learnings
-

## 📅 Next Steps
- [ ] 내일 작업 1

## 📊 Time Spent
-

## 🔗 References
-
```

### 작업 일지 Best Practices
1. **매일 작성**: 작업 종료 전에 반드시 작성
2. **구체적 기록**: "버그 수정"보다 "Elasticsearch RRF 라이선스 문제 해결 (Platinum → ranx 라이브러리)"
3. **의사결정 기록**: 중요한 기술 선택과 이유를 명시
4. **다음 단계 명시**: 내일 할 일을 미리 정리
5. **참조 링크**: 관련 이슈, PR, 문서 링크 추가

---

## 🤝 협업 규칙

### Code Review
1. 모든 PR은 최소 1명 리뷰 필수
2. 60라인 이상은 2명 리뷰
3. 보안, 성능, 테스트 관점에서 검토
4. 스타일은 Black, isort로 자동 정렬

### Branch 전략
- `main` - 프로덕션 (보호됨)
- `develop` - 개발 통합 브랜치
- `feature/*` - 기능 개발
- `fix/*` - 버그 수정
- `chore/*` - 기타 작업

---

## 🐛 디버깅 팁

### 로그 추적
```python
# 시작과 종료 지점 기록
logger.info(f"[START] Processing document: {doc_id}")
try:
    result = process_document(doc)
    logger.info(f"[SUCCESS] Document {doc_id} processed")
except Exception as e:
    logger.error(f"[ERROR] Document {doc_id} failed: {e}", exc_info=True)
```

### 디버그 모드
```bash
# DEBUG=true로 실행
DEBUG=true LOG_LEVEL=DEBUG python src/app/main.py
```

### REPL에서 테스트
```bash
poetry shell
python
>>> from app.services.metadata_extraction import extract_temporal_metadata
>>> result = extract_temporal_metadata("test document")
>>> print(result)
```

---

## 📚 참고 자료

- [LangGraph 문서](https://python.langchain.com/docs/langgraph/)
- [Neo4j Python Driver](https://neo4j.com/docs/api/python-driver/current/)
- [Elasticsearch Python Client](https://www.elastic.co/guide/en/elasticsearch/client/python-api/current/index.html)
- [DeepSeek API](https://platform.deepseek.com/api-docs)
- [Claude API](https://docs.anthropic.com/)

---

## ✅ 체크리스트

새 기능을 추가할 때마다 확인:

- [ ] 함수/클래스에 docstring 작성
- [ ] 유닛 테스트 작성 (80%+ 커버리지)
- [ ] 에러 핸들링 추가
- [ ] 로깅 추가
- [ ] type hints 추가
- [ ] 문서 업데이트
- [ ] Black/isort 스타일 정렬
- [ ] pytest 통과
- [ ] 보안 검증

---

## 📋 문서 버전 정보

**Last Updated**: 2026-01-12
**Version**: 2.0

### 변경 이력
- **v2.0 (2026-01-12)**:
  - 프로젝트 폴더 구조 업데이트 (`knowledge_service/` 중심)
  - 작업 일지 시스템 추가 (스크립트 및 워크플로우)
  - 문서 구조 확장 (`01_planning/`, `02_design/`, `work_logs/`)
  - 개발 가이드 업데이트 (uvicorn 실행 방법 추가)
  - 파일 경로 및 명명 규칙 명확화

- **v1.0 (2026-01-11)**:
  - 초기 버전 작성
  - 기본 개발 원칙 및 프롬프트 가이드
  - 커밋 규칙 및 협업 가이드
