# Presentation Maker Skill 사용 가이드

## 이게 뭔가요?

이 skill은 **Claude가 전문적인 PPT를 만들 수 있도록 가르치는 교과서**입니다.

### 간단히 말하면
- **SKILL.md** = Claude가 읽는 "PPT 만들기 요리책"
- **README.md** (이 파일) = 사람이 읽는 "사용 설명서"

Claude에게 "presentation-maker skill 이용해서 PPT 만들어줘"라고 하면,
Claude가 SKILL.md를 읽고 전문적인 프레젠테이션을 만들어줍니다!

---

## 주요 기능

### 1. 6가지 테마 팔레트

| 테마 | 주요 색상 | 추천 용도 |
|------|----------|----------|
| **Tech Innovation** | Green 계열 | AI, 개발, 기술 발표 |
| **Ocean Depths** | Blue 계열 | 비즈니스, 경영, 금융 |
| **Forest Canopy** | Green/Brown | ESG, 환경, 지속가능 |
| **Arctic Frost** | Cyan 계열 | 의료, 헬스케어, 과학 |
| **Sunset Boulevard** | Orange 계열 | 마케팅, 광고, 이벤트 |
| **Midnight Galaxy** | Indigo 계열 | 게임, 엔터테인먼트, VR/AR |

### 2. 테마 자동 선택

테마를 지정하지 않으면 **내용을 분석하여 자동으로 적절한 테마를 선택**합니다!

```
# 테마 자동 선택 예시
"AI 시스템 설계 발표 자료 만들어줘"
→ Tech Innovation 테마 자동 적용

"ESG 지속가능경영 보고서 발표 자료 만들어줘"
→ Forest Canopy 테마 자동 적용
```

### 3. PPT 도형 기반 다이어그램

python-pptx의 네이티브 도형 기능으로 다이어그램을 생성합니다:
- 아키텍처 다이어그램
- 플로우 차트
- 비교 테이블
- 프로세스 다이어그램
- 계층 구조도

### 4. 한글 최적화

- **폰트**: 맑은 고딕 (Windows), Noto Sans KR (Mac/Linux)
- **행간**: 한글에 적합한 1.6-1.8 배수
- **글자 크기**: 제목 32-44pt, 본문 10-14pt

---

## 파일 구조

```
.claude/skills/presentation-maker/
├── SKILL.md          ← Claude가 읽는 가이드 (모든 노하우)
├── README.md         ← 이 파일 (사용 설명서)
└── LLM 기반 AI 에이전트 기초와 실습-20251018.pptx  ← 참조 예제
```

---

## 사용 방법

### 기본 사용법

```
"presentation-maker skill 이용해서 발표 자료 만들어줘"
```

### 테마 지정

```
"presentation-maker skill 이용해서 발표 자료 만들어줘
- Tech Innovation 테마 적용해줘"
```

### 상세 요청 예시

```
presentation-maker skill 이용해서 발표 자료 만들어줘
- 제목: AI 기반 RAG 시스템 설계
- 표지 포함 10장 이내
- 폰트: 맑은 고딕
- Tech Innovation 테마 적용
- 아키텍처 도식화는 PPT 도형 기능 사용
- 도식화에 상세 설명 추가해줘
```

---

## 추천 프롬프트 템플릿

### 1. 기술 발표용

```
presentation-maker skill 이용해서 기술 발표 자료 만들어줘:
- 제목: "마이크로서비스 아키텍처 설계"
- 내용: [참고할 문서 경로 또는 설명]
- 슬라이드: 10장 이내
- 테마: Tech Innovation
- 아키텍처 다이어그램 상세하게 그려줘
- 각 컴포넌트에 설명 추가해줘
```

```
presentation-maker skill 이용해서 knowledge_service\docs\02_design\hybrid_rag_platform_detailed_design.md 발표 자료 만들어줘
- Brown 계열 테마 사용해줘. 
- 아키텍처 도식화 상세하게 그려주고, 자세한 설명 추가해줘.
- 아키텍처 장점에 대한 페이지 만들어줘.
- 스토리지 장점 부각시켜줘
```

```
presentation-maker skill 이용해서 knowledge_service\docs\02_design\ui_storyboard 아래 문서들 참조하여 발표 자료 만들어줘
- 브라운 계열 테마 사용해줘. 
- 각 페이지 마다 스토리 보드 상세한 설명 우측에 박스로 추가해줘
- 웹코더 및 개발자 주의사항 추가해줘
```

### 2. 비즈니스 발표용

```
presentation-maker skill 이용해서 비즈니스 발표 자료 만들어줘:
- 제목: "2026년 사업 계획"
- 대상: 경영진
- 슬라이드: 15장
- 테마: Ocean Depths
- 재무 데이터 표 포함
- 간결하고 임팩트 있게
```

### 3. 문서 기반 자동 생성

```
presentation-maker skill 이용해서 [문서 경로] 발표 자료 만들어줘
- 표지 포함 10장 이내
- 테마: 자동 선택
- 아키텍처 도식화 상세하게
- 핵심 내용 요약해서
```

---

## 테마별 키워드 가이드

테마 자동 선택시 다음 키워드를 인식합니다:

### Tech Innovation (기술)
```
AI, 인공지능, ML, 머신러닝, API, 개발, 코드, 클라우드, 데이터,
RAG, LLM, 시스템, 아키텍처, 플랫폼, Python, Java, DevOps
```

### Ocean Depths (비즈니스)
```
기업, 비즈니스, 전략, 금융, 투자, 컨설팅, 경영, 조직, 리더십,
분기, 실적, 보고서, 매출, ROI
```

### Forest Canopy (환경)
```
환경, 지속가능, ESG, 친환경, 탄소, 에너지, 재활용, 자연, 생태, 기후
```

### Arctic Frost (의료/과학)
```
의료, 헬스케어, 병원, 제약, 바이오, 임상, 과학, 연구, 실험
```

### Sunset Boulevard (마케팅)
```
마케팅, 광고, 캠페인, 브랜드, 이벤트, 프로모션, 소셜, 미디어, 콘텐츠
```

### Midnight Galaxy (엔터테인먼트)
```
게임, 엔터테인먼트, 영화, 음악, 스트리밍, VR, AR, 메타버스
```

---

## 생성된 예제 파일들

### UI Storyboard 프레젠테이션
```
knowledge_service/docs/02_design/ui_storyboard/UI_Storyboard_Presentation.pptx
- Tech Innovation 테마
- 10 슬라이드
- UI/UX 설계 내용
```

### 상세 설계서 프레젠테이션 (Green)
```
knowledge_service/docs/02_design/Hybrid_RAG_Platform_Design_v2.3.pptx
- Tech Innovation 테마
- 10 슬라이드
- 시스템 아키텍처 중심
```

### 상세 설계서 프레젠테이션 (Brown)
```
knowledge_service/docs/02_design/Hybrid_RAG_Platform_Design_Brown.pptx
- Brown Earth 테마
- 10 슬라이드
- 저장소별 장점 부각
- 상세 아키텍처 다이어그램
```

---

## 디자인 베스트 프랙티스

### 해야 할 것
- 한 슬라이드 = 하나의 핵심 메시지
- 불릿 포인트 최대 6개
- 충분한 여백
- 일관된 색상과 폰트
- 도형 기반 다이어그램 활용
- 각 도형에 설명 텍스트 추가

### 피해야 할 것
- 너무 많은 텍스트 (문단 형태)
- 작은 폰트 (10pt 미만)
- 여러 폰트 혼용
- 복잡한 다이어그램 (단순화 필요)
- 외부 이미지 파일 의존 (도형 사용 권장)

---

## 기술 요구사항

### 필수 라이브러리

```bash
pip install python-pptx pillow
```

### 선택적 라이브러리 (Marp 사용시)

```bash
npm install -g @marp-team/marp-cli
```

### 시스템 요구사항

- Python 3.8+
- 한글 폰트 설치됨 (맑은 고딕 또는 Noto Sans KR)

---

## 문제 해결

### Q1: 한글이 깨져요
**A:** 시스템에 한글 폰트가 설치되어 있는지 확인
- Windows: 맑은 고딕 (기본 설치됨)
- Mac: Noto Sans KR 설치 권장
- Linux: `apt install fonts-noto-cjk`

### Q2: 다이어그램이 잘 안 보여요
**A:** PPT 도형 기능 사용을 요청하세요
```
"도식화는 PPT 도형 기능을 사용해서 만들어줘"
```

### Q3: 특정 테마를 사용하고 싶어요
**A:** 테마 이름을 명시하세요
```
"Ocean Depths 테마로 만들어줘"
```

### Q4: 슬라이드 수를 조절하고 싶어요
**A:** 원하는 슬라이드 수를 명시하세요
```
"표지 포함 10장 이내로 만들어줘"
```

---

## 업데이트 이력

### v2.0 (2026-01-15)
- 6가지 테마 팔레트 추가
- 테마 자동 선택 알고리즘 구현
- PPT 도형 기반 다이어그램 강화
- 다양한 생성 예제 추가
- Brown Earth 테마 추가
- 저장소별 장점 부각 기능

### v1.0 (2026-01-15)
- 최초 버전
- PowerPoint (PPTX) 생성 기능
- Marp Markdown 지원
- 한글 최적화
- 3가지 기본 색상 팔레트

---

## 마무리

이 skill을 사용하면:
- **시간 절약**: 30분 → 5분
- **전문적 디자인**: 일관된 스타일
- **한글 최적화**: 읽기 편한 발표 자료
- **자동화**: 테마 자동 선택, 도형 자동 생성

**시작하기:**
```
"presentation-maker skill 이용해서 발표 자료 만들어줘"
```

---

**작성:** 2026-01-15
**버전:** 2.0
**위치:** `.claude/skills/presentation-maker/`
