# GPT-5.4 출시 영향 분석

**날짜**: 2026-03-06
**출처**: OpenAI GPT-5.4 공식 발표 (2026-03-05)
**분석**: 데일리 스탠드업 부주제 논의 결과

---

## GPT-5.4 핵심 사양

| 항목 | 내용 |
|------|------|
| 출시일 | 2026-03-05 |
| 변형 | GPT-5.4 / GPT-5.4 Thinking / GPT-5.4 Pro |
| 컨텍스트 | 1M tokens (API) |
| 가격 | $2.50/$15 (일반) / $30/$180 (Pro) per 1M tokens |
| Computer Use | OSWorld 75.0% (인간 72.4% 초과) |
| 브라우저 | Online-Mind2Web 92.8% |
| 코딩 | SWE-Bench Pro 57.7% |
| 할루시네이션 | 개별 주장 33% 감소, 전체 응답 18% 오류 감소 (vs GPT-5.2) |
| Tool Search | 토큰 사용량 47% 절감 |
| 전문 업무 | 44개 직종 83%에서 인간 수준 이상 |
| ARC-AGI-2 (Pro) | 83.3% |

## 핵심 신기능

1. **네이티브 Computer Use** - Playwright 코드 + 스크린샷 기반 마우스/키보드 제어
2. **Tool Search** - 도구 정의를 온디맨드 검색 (전체 로딩 불필요, 47% 토큰 절감)
3. **ChatGPT for Excel/Sheets** - 스프레드시트 내장 AI (베타)

---

## 프로젝트 영향 분석

### 1. 런타임 LLM 전략 -> DeepSeek V3.2 유지

| 비교 | DeepSeek V3.2 | GPT-5.4 | 격차 |
|------|--------------|---------|------|
| Input | ~$0.14/1M | $2.50/1M | 18x |
| Output | ~$0.28/1M | $15.00/1M | 54x |

- RAG Faithfulness 기반 -> 검색 품질 > LLM 성능
- DeepSeek로 Faithfulness 0.85+ 달성 중
- 고난도 분석(정책 비교 등)에 한정하여 GPT-5.4 Pro 선택적 검토 가능

### 2. Tool Search 개념 -> Sprint 11~12 파일럿

- classify_query_type 정적 분류 -> 의미 기반 동적 선택 메타 레이어로 진화
- 적용: ES 벡터검색 / BM25 / Neo4j 그래프 탐색 중 동적 선택
- RAG 파이프라인 레벨에서 우선 적용, 효과 측정 후 확대

### 3. Computer Use E2E -> Sprint 12~13 검토

- Playwright 스크립트의 재현 가능성/CI 통합성 우위 유지
- AI-assisted 탐색적 테스트, 시각적 회귀 테스트, 접근성 보조 가능성
- Claude Computer Use vs GPT-5.4 비교 평가 필요

---

## 경쟁 환경 모니터링 (2026-03 기준)

| 모델 | 강점 | 가격 (I/O per 1M) |
|------|------|-------------------|
| GPT-5.4 | Computer Use(75%), Tool Search, 1M ctx | $2.50/$15 |
| Claude Opus 4.6 | SWE-Bench, MMMU Pro(85.1%), Agent Teams | $5/$25 |
| Gemini 3.1 Pro | GPQA Diamond(94.3%), 2M ctx | $2/$12 |

**결론**: 단일 모델 독주 없음. 용도별 최적 모델 선택 전략 유효.

---

## 백로그 등록 항목

| Sprint | 항목 | SP |
|--------|------|-----|
| 11~12 | Tool Search 기반 동적 검색 전략 메타 레이어 | 5 |
| 12~13 | AI-assisted E2E Testing 파일럿 | 5 |

---

*기록자: Claude Code (Opus 4.6)*
