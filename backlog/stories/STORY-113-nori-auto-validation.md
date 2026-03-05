# STORY-113: Nori 플러그인 자동 검증 테스트 (_analyze API 기반)

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | - |
| **Epic** | 테스트 자동화 |
| **Status** | Done |
| **Priority** | P0 |
| **Story Points** | 2 |
| **Assignee** | QA |
| **Sprint** | Sprint 09 |

---

## User Story

**As a** QA Engineer,
**I want** Nori 플러그인 동작을 CI/CD에서 자동으로 검증하기를,
**So that** 2026-02-13과 같은 32일간 미발견 Nori 미적용 사고가 재발하지 않는다.

---

## 배경

2026-02-13 사고: ES Dockerfile에 Nori 플러그인 미설치 → 32일간 standard analyzer로만 동작.
3건의 코드 리뷰에서 미발견 (코드만 보고 실동작 미검증).

**교훈**: "설계서에 적혀 있다고 구현된 것이 아니다."

---

## Acceptance Criteria

- [x] ES `_analyze` API 호출로 nori_tokenizer 실제 동작 검증 테스트 작성
- [x] 한국어 텍스트 형태소 분석 결과 검증 (standard analyzer와 다른 결과 확인)
- [ ] CI/CD 파이프라인에 Nori 검증 스텝 추가 → **DevOps 이관 (STORY-118 병합)**
- [ ] 검증 실패 시 파이프라인 중단 및 Slack 알림 → **DevOps 이관**

---

## Tasks

- [x] `tests/integration/test_nori_analyzer.py` 작성 — 4클래스 14메서드
- [x] `_analyze` API 호출: `POST /{index}/_analyze` with `nori_tokenizer`
- [x] 기대 토큰 목록 검증 (standard vs nori 결과 비교) — 14/14 PASS (TEST_MODE=docker)
- [ ] GitHub Actions workflow에 Nori 검증 스텝 추가 → DevOps 이관
- [ ] 실패 시 Slack alerts 채널 알림 연동 → DevOps 이관

> **완료 메모** (2026-03-05): 실제 인덱스 analyzer 이름이 `nori_analyzer`가 아닌 `korean_analyzer` (nori_tokenizer + nori_part_of_speech 필터 조합)임을 확인하여 테스트 수정 완료. CI/CD 파이프라인 연동은 STORY-118(DevOps)에 이관.

---

## 기술 노트

### 구현 방향
```python
# 검증 예시
response = es_client.indices.analyze(
    index="knowledge_chunks",
    body={"tokenizer": "nori_tokenizer", "text": "한국어 형태소 분석 테스트"}
)
tokens = [t["token"] for t in response["tokens"]]
assert "한국어" in tokens or len(tokens) > 1  # standard는 공백 분리만
```

### 영향 범위
- `knowledge_service/src/tests/integration/`
- `.github/workflows/ci.yml`

---

## 테스트 계획

- [x] TEST_MODE=docker 환경에서 실행 (Mock 금지)
- [x] ES 컨테이너 기동 상태에서 통합 테스트 실행 — 14/14 PASS

---

## 의존성

- **선행**: Docker 환경 Health Check
- **관련**: DevOps CI/CD 파이프라인 수정 협업
