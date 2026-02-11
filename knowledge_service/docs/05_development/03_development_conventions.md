# 개발 컨벤션

## Development Conventions

**버전**: 1.0
**작성일**: 2026-01-20
**작성자**: TechLead Agent

---

## 1. 코드 스타일 가이드

### 1.1 Python (AI Service)

**도구**: Black, isort, flake8

```bash
poetry run black src/
poetry run isort src/
poetry run flake8 src/
```

**규칙**:
- 줄 길이: 100자
- 들여쓰기: 4 spaces
- Docstring: Google 스타일
- Type hints 필수

### 1.2 Java (Backend/Gateway)

**규칙**:
- 줄 길이: 120자
- 들여쓰기: 4 spaces
- Lombok 사용 권장

### 1.3 TypeScript (Frontend)

**도구**: ESLint, Prettier

```bash
npm run lint
npm run format
```

---

## 2. 커밋 메시지 규칙

### 2.1 형식

```
[TYPE] 간단한 설명 (50자 이내)

- 변경 사항 1
- 변경 사항 2

관련 이슈: HRKP-123
```

### 2.2 타입

| 타입 | 용도 |
|------|------|
| [FEAT] | 새 기능 |
| [FIX] | 버그 수정 |
| [REFACTOR] | 리팩토링 |
| [TEST] | 테스트 |
| [DOCS] | 문서 |
| [CHORE] | 빌드/설정 |
| [STYLE] | 포맷팅 |
| [HOTFIX] | 긴급 수정 |

---

## 3. 브랜치 전략

### 3.1 브랜치 구조

```
main (production)
├── develop (integration)
│   ├── feature/HRKP-123-search-api
│   └── fix/HRKP-456-timeout
├── release/v1.0.0
└── hotfix/HRKP-999-security
```

### 3.2 브랜치 명명 규칙

| 유형 | 패턴 |
|------|------|
| 기능 | feature/HRKP-{번호}-{설명} |
| 버그 | fix/HRKP-{번호}-{설명} |
| 핫픽스 | hotfix/HRKP-{번호}-{설명} |
| 릴리스 | release/v{버전} |

---

## 4. PR 가이드라인

### 4.1 PR 규칙

- **크기**: 변경 파일 10개 이하, 500줄 이하
- **리뷰어**: 최소 1명 (main은 2명)
- **CI 통과**: 모든 테스트 및 린트 통과 필수

---

## 5. 코드 리뷰 체크리스트

- [ ] 요구사항 충족
- [ ] 에러 핸들링
- [ ] 코드 가독성
- [ ] 테스트 커버리지 80%+
- [ ] 보안 취약점 없음

---

## 6. 테스트 규칙

### 6.1 커버리지 목표

| 계층 | 최소 | 목표 |
|------|------|------|
| 서비스 | 80% | 90% |
| 컨트롤러 | 70% | 80% |
| 유틸리티 | 90% | 95% |

### 6.2 테스트 구조 (Given-When-Then)

```python
def test_search_returns_results():
    # Given
    query = "test"
    
    # When
    results = search(query)
    
    # Then
    assert len(results) > 0
```

---

## 관련 문서

- [개발 환경 설정](./development_environment_setup.md)
- [빠른 시작 가이드](./quick_start_guide.md)
- [CLAUDE.md](../../../CLAUDE.md)

---

**문서 버전**: 1.0 | **최종 수정**: 2026-01-20 | **작성자**: TechLead Agent
