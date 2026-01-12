# Knowledge Service

Graph RAG 기반 지능형 지식 검색 서비스 - LangGraph, Neo4j, Elasticsearch를 활용한 Python 백엔드

## 📁 폴더 구조

```
knowledge_service/
├── src/                          # Python 소스코드
│   ├── app/                      # FastAPI 애플리케이션
│   │   ├── api/                  # REST API 엔드포인트
│   │   ├── core/                 # 핵심 로직 (검색, 그래프, 임베딩)
│   │   ├── services/             # 비즈니스 로직
│   │   ├── models/               # 데이터 모델
│   │   └── utils/                # 유틸리티
│   ├── scripts/                  # 초기화 및 데이터 처리 스크립트
│   └── tests/                    # 테스트 코드
├── data/                         # 입력 데이터
│   ├── documents/                # PDF 등 원본 파일
│   ├── sample/                   # 샘플 데이터
│   └── fixtures/                 # 테스트 데이터
├── docs/                         # 문서
│   ├── API.md
│   ├── ARCHITECTURE.md
│   ├── SETUP.md
│   └── images/
├── results/                      # 실행 결과 (임시)
│   ├── search_logs/
│   ├── metadata_exports/
│   └── cost_reports/
├── .antigravity/                 # Antigravity 규칙
├── .claude/                      # Claude Code 설정
├── .agent/                       # 워크플로우
├── pyproject.toml
├── CLAUDE.md                     # 프로젝트 Claude 규칙
└── README.md
```

## 🚀 빠른 시작

```bash
# 의존성 설치
poetry install

# 데이터베이스 초기화
python src/scripts/init_databases.py

# 애플리케이션 실행
python src/app/main.py
```

## 📚 주요 문서

- [API Reference](./docs/api_reference.md) - REST API 엔드포인트
- [Architecture Overview](./docs/architecture_overview.md) - 시스템 구조
- [Getting Started](./docs/getting_started.md) - 환경 설정

## 🛠 개발 규칙

[CLAUDE.md](./CLAUDE.md)를 참고하세요.
