# Web Design System Skill 사용 가이드

## 🎯 이게 뭔가요?

웹 기획자와 디자이너를 위한 **AI 디자인 파트너**입니다.

### 핵심 차별점
**Verbalized Sampling 기법**으로 뻔한 디자인을 피하고 독창적인 결과물을 만듭니다!

```
일반 AI: "파란색 그라데이션 + shadcn/ui로 만들게요"
         → 천편일률적 디자인 😔

이 Skill: "먼저 가장 뻔한 디자인 5가지를 말해줘
          → 그것들을 완전히 피하면서 창의적으로 만들어줘"
         → 독창적이고 차별화된 디자인! 🎨✨
```

### 간단히 말하면
- **SKILL.md** = Claude가 읽는 "웹 디자인 바이블"
- **README.md** (이 파일) = 사람이 읽는 "사용 설명서"

---

## 📂 설치 위치

### ✅ 올바른 위치
```bash
~/.claude/skills/web-design-system/
├── SKILL.md          ← Claude가 읽는 디자인 가이드
└── README.md         ← 이 파일
```

### 설치 방법
```bash
# 1. .claude/skills 디렉토리 생성 (없다면)
mkdir -p ~/.claude/skills

# 2. web-design-system 폴더 복사
cp -r web-design-system ~/.claude/skills/

# 3. 확인
ls -la ~/.claude/skills/web-design-system/
# SKILL.md  README.md 가 보이면 성공!
```

---

## 🌟 왜 이 Skill을 써야 하나요?

### ❌ 일반 AI의 문제점
```
"랜딩 페이지 만들어줘"
→ 보라색 그라데이션 (#667eea → #764ba2)
→ shadcn/ui 기본 컴포넌트
→ 중앙 정렬 + 3개 박스
→ 경쟁사와 똑같은 디자인 😫
```

### ✅ 이 Skill을 쓰면
```
"랜딩 페이지 만들어줘. web-design-system skill 사용해서"

Claude: "먼저 뻔한 디자인을 식별할게요:
        1. 파란색→보라색 그라데이션
        2. 중앙 정렬 히어로
        3. shadcn/ui 카드
        
        이것들을 피하고, 대신:
        - 딥 포레스트 색상 (#0D3B2E + #E8B54D)
        - 비대칭 레이아웃
        - 커스텀 디자인 시스템
        
        으로 만들게요!" 🎨✨
```

---

## 💬 사용 방법

### 기본 사용법

```
"[요청 내용]. web-design-system skill 참고해서 만들어줘"
```

**핵심 키워드:** `web-design-system skill 참고` 또는 `web-design-system skill 사용`

---

## 🎨 Verbalized Sampling 프롬프트

### 🔥 추천 프롬프트 템플릿

#### 1️⃣ 완전 자동 모드 (간편)
```
"스타트업 랜딩 페이지 만들어줘. 
web-design-system skill 사용해서 
뻔한 디자인 피하고 독창적으로 만들어줘"
```

#### 2️⃣ 가이드 모드 (추천 ⭐⭐⭐)
```
"이커머스 상품 리스트 페이지 만들어줘. 
web-design-system skill 참고하되:

1. 먼저 이커머스 사이트에서 가장 흔한 디자인 5가지 말해줘
2. 그것들을 완전히 피하면서 창의적인 대안 3가지 제안해줘
3. 가장 독창적인 것을 선택하고, 왜 창의적인지 설명해줘
4. 그 디자인으로 완성해줘 (HTML/CSS 또는 React)"
```

#### 3️⃣ 세밀 제어 모드 (고급)
```
"SaaS 대시보드 만들어줘. web-design-system skill 사용:

피해야 할 것:
- 보라색 그라데이션
- Material-UI 느낌
- 카드 그리드 레이아웃

대신 시도할 것:
- 자연에서 영감받은 색상
- 비대칭 레이아웃
- 커스텀 컴포넌트

요구사항:
- 한글 최적화 (Pretendard 폰트)
- 접근성 WCAG 2.1 AA
- 반응형 디자인
- React + styled-components"
```

---

## ✨ 주요 기능

### 1. 🚫 Verbalized Sampling (핵심!)
뻔한 디자인을 먼저 식별하고 피하기

**작동 원리:**
```
Step 1: "가장 흔한 디자인 패턴은?"
        → AI가 리스트 생성

Step 2: "그것들을 피하고 창의적인 대안은?"
        → AI가 독창적 아이디어 제시

Step 3: "왜 이게 창의적인지 설명"
        → AI의 창의성 리미터 해제!

Step 4: "품질 검증하면서 생성"
        → 접근성, 한글 최적화 보장
```

### 2. 🎨 창의적 색상 팔레트
```
❌ 피할 것:
- 보라색 그라데이션 (#667eea → #764ba2)
- SaaS 파란색 (#3b82f6)
- 민트/핑크 (#4ade80 + #f472b6)

✅ 제안할 것:
- 딥 포레스트 (#0D3B2E + #E8B54D)
- 테라코타 선셋 (#C85C3C + #F4E3D3)
- 미드나잇 애쉬 (#2C3539 + #C4C4C4)
```

### 3. 🧩 독창적 레이아웃
- 브로큰 그리드 (Broken Grid)
- 비대칭 디자인
- 겹치는 요소 (Overlapping)
- 예상치 못한 스크롤 방향

### 4. 🇰🇷 한글 최적화
- Pretendard Variable 폰트
- 행간 1.6-1.8 (영문보다 넓게)
- word-break: keep-all
- 자간 -0.01em

### 5. ♿ 접근성 보장
- WCAG 2.1 AA 준수
- 색상 대비 4.5:1 이상
- 키보드 네비게이션
- 스크린 리더 지원
- 터치 타겟 44x44px

### 6. 📱 반응형 디자인
- 모바일 퍼스트
- Fluid Typography
- Container Queries
- 자동 반응형 그리드

### 7. 🌙 다크 모드 (v2.0 NEW!)
- 세심하게 조정된 색상 체계
- 밝기 기반 엘리베이션 (그림자 대신)
- 시스템 설정 자동 감지
- 부드러운 전환 효과

### 8. 🎬 모션 디자인 (v2.0 NEW!)
- 의도적인 타이밍 시스템
- Entrance/Feedback/Guidance 애니메이션
- Reduced Motion 지원
- 스태거 효과

### 9. ⚡ Core Web Vitals (v2.0 NEW!)
- LCP ≤ 2.5s 최적화
- CLS ≤ 0.1 방지
- INP ≤ 200ms 최적화

### 10. 🧪 테스트 도구 (v2.0 NEW!)
- 접근성: axe DevTools, Lighthouse, WAVE
- 성능: PageSpeed Insights, WebPageTest
- 크로스 브라우저: Playwright, BrowserStack

---

## 📖 실전 예제

### 예제 1: 스타트업 랜딩 페이지
```
"AI 스타트업 랜딩 페이지 만들어줘. 
web-design-system skill 참고:

1. 먼저 AI 스타트업 랜딩에서 가장 흔한 디자인 5가지 말해줘
2. 그것들을 완전히 피하는 대안 3가지 제안해줘
3. 가장 창의적인 걸로 만들어줘

요구사항:
- 히어로 섹션
- 기능 소개 (3-4개)
- CTA 섹션
- HTML/CSS 한 파일로
- 한글 최적화"
```

**예상 결과:**
- ✅ 딥 포레스트 색상 (보라색 그라데이션 대신)
- ✅ 비대칭 히어로 레이아웃 (중앙 정렬 대신)
- ✅ 브로큰 그리드 Feature 섹션
- ✅ 언더라인 확장 버튼 (둥근 버튼 대신)

### 예제 2: 이커머스 상품 리스트
```
"럭셔리 패션몰 상품 리스트 페이지 만들어줘.
web-design-system skill 사용:

피해야 할 것:
- 카드 그리드 (동일 크기)
- 드롭 그림자
- 중앙 정렬

대신:
- 브로큰 그리드
- 비대칭 레이아웃
- 미니멀한 스타일

React + styled-components로"
```

### 예제 3: 관리자 대시보드
```
"프로젝트 관리 대시보드 만들어줘.
web-design-system skill 참고:

1. 먼저 대시보드에서 가장 흔한 패턴 5가지
2. 그것들 피하고 독창적인 대안 3가지
3. 가장 실용적이면서 창의적인 걸로 만들어줘

포함 요소:
- 사이드바 네비게이션
- KPI 카드
- 차트 영역
- 데이터 테이블

한글 + 다크 모드 지원"
```

### 예제 4: 포트폴리오 사이트
```
"웹 디자이너 포트폴리오 사이트 만들어줘.
web-design-system skill 사용해서 독창적으로:

- 뻔한 포트폴리오 디자인 피하기
- 타이포그래피가 주인공
- 극단적 크기 대비
- 예상치 못한 인터랙션

React + Framer Motion"
```

---

## 🎨 디자인 안티패턴 (피해야 할 것)

### ❌ 절대 금지 목록

#### 색상
- 보라색 그라데이션 (#667eea → #764ba2)
- 파란색 → 보라색 (#4facfe → #00f2fe)
- SaaS 파란색 (#3b82f6)
- 네온 다크모드 (#00ffff, #ff00ff)

#### 레이아웃
- 중앙 정렬 히어로 + CTA
- 3개 박스 Feature
- 지그재그 교차 섹션
- 동일한 카드 그리드

#### 컴포넌트
- shadcn/ui 기본 스타일
- Material-UI 느낌
- Bootstrap 버튼
- 8px 둥근 모서리 카드

#### 타이포그래피
- Inter + Inter (헤딩 + 본문 모두)
- Montserrat Bold 제목
- Poppins everywhere
- ALL CAPS 제목

---

## 🛠️ 고급 기능

### 1. 컴포넌트별 요청
```
"독창적인 CTA 버튼 3가지 제안해줘.
web-design-system skill 참고:
- shadcn/ui 스타일 피하기
- 언더라인, 네온, 모피즘 스타일
- 각각 왜 독창적인지 설명
- React 컴포넌트로"
```

### 2. 디자인 시스템 구축
```
"브랜드 디자인 시스템 만들어줘.
web-design-system skill 사용:

포함 항목:
- 색상 팔레트 (뻔한 것 피하고)
- 타이포그래피 스케일
- 간격 시스템
- 컴포넌트 라이브러리
- 사용 가이드

CSS Variables로"
```

### 3. 애니메이션 & 인터랙션
```
"마이크로 인터랙션 5가지 만들어줘.
web-design-system skill 참고:

- 로딩 애니메이션 (스피너 말고)
- 호버 효과 (그림자 말고)
- 스크롤 애니메이션
- 페이지 전환

CSS + JavaScript"
```

---

## 🇰🇷 한글 웹사이트 특화

### 자동 적용되는 최적화
- ✅ Pretendard Variable 폰트
- ✅ 행간 1.6-1.8
- ✅ word-break: keep-all
- ✅ 자간 -0.01em
- ✅ 폰트 웨이트 조정

### 한글 + 영문 혼용 시
```
"한영 혼용 타이포그래피 시스템 만들어줘.
web-design-system skill 참고:
- 한글: Pretendard
- 영문/숫자: Inter
- 폰트 폴백 전략"
```

---

## 🆘 문제 해결

### Q1: Claude가 여전히 보라색 그라데이션을 사용해요
**A:** 프롬프트에 명시적으로 금지를 추가하세요
```
"절대 사용 금지:
- 보라색 그라데이션
- shadcn/ui
- Material-UI 느낌

web-design-system skill 참고해서 독창적으로"
```

### Q2: skill을 찾지 못해요
**A:** 폴더 위치 확인
```bash
ls -la ~/.claude/skills/web-design-system/
# SKILL.md와 README.md가 있어야 함
```

### Q3: 한글 폰트가 깨져요
**A:** 브라우저에서 Pretendard 폰트 로드 확인
```html
<link rel="stylesheet" 
  href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.min.css">
```

### Q4: 디자인이 여전히 뻔해요
**A:** Verbalized Sampling을 명시적으로 요청
```
"먼저 가장 뻔한 디자인 5가지 말하고,
그것들을 완전히 피해서 만들어줘.
web-design-system skill 사용"
```

### Q5: 접근성이 걱정돼요
**A:** 자동으로 WCAG 2.1 AA를 준수합니다
```
"접근성 체크리스트 포함해서 만들어줘.
web-design-system skill 참고"
```

---

## 📊 비교표

| 항목 | 일반 AI | web-design-system skill |
|------|---------|-------------------------|
| **색상** | 보라색 그라데이션 | 독창적 팔레트 |
| **레이아웃** | 중앙 정렬 | 비대칭, 브로큰 그리드 |
| **컴포넌트** | shadcn/ui | 커스텀 디자인 |
| **한글** | 부족한 최적화 | Pretendard + 행간 1.7 |
| **접근성** | 불확실 | WCAG 2.1 AA 보장 |
| **창의성** | ⭐⭐☆☆☆ | ⭐⭐⭐⭐⭐ |

---

## 💡 프로 팁

### 팁 1: 경쟁사 분석 활용
```
"[경쟁사 URL]과 완전히 다른 디자인으로 만들어줘.
web-design-system skill 사용해서
경쟁사 디자인 패턴을 먼저 분석하고,
그것과 정반대로 만들어줘"
```

### 팁 2: 브랜드 가이드 제공
```
"우리 브랜드 키워드:
- 자연, 성장, 신뢰
- 따뜻하지만 전문적
- 미니멀하지만 친근한

web-design-system skill로
브랜드 정체성 반영한 디자인 시스템 만들어줘"
```

### 팁 3: 점진적 개선
```
1차: "기본 랜딩 페이지 만들어줘"
2차: "web-design-system skill로 더 독창적으로 개선해줘"
3차: "가장 뻔한 부분 3가지 찾아서 대체해줘"
```

### 팁 4: 여러 버전 비교
```
"3가지 완전히 다른 디자인 방향성 제시해줘.
web-design-system skill 참고:
1. 미니멀 & 모던
2. 볼드 & 다이나믹
3. 엘레강트 & 클래식

각각 색상, 레이아웃, 타이포그래피 설명"
```

---

## 🎓 학습 자료

### 디자인 영감
- [Awwwards](https://www.awwwards.com/) - 독창적 웹 디자인
- [Dribbble](https://dribbble.com/) - UI/UX 영감
- [Behance](https://www.behance.net/) - 디자인 포트폴리오

### 색상 도구
- [Coolors](https://coolors.co/) - 색상 팔레트 생성
- [Adobe Color](https://color.adobe.com/) - 색상 조합
- [Contrast Checker](https://webaim.org/resources/contrastchecker/)

### 타이포그래피
- [Google Fonts](https://fonts.google.com/)
- [Pretendard](https://github.com/orioncactus/pretendard)
- [Typography Guidelines](https://typography.hangeul.org/)

### 접근성
- [WCAG 2.1](https://www.w3.org/WAI/WCAG21/quickref/)
- [A11y Project](https://www.a11yproject.com/)

---

## 🚀 시작하기

### 1단계: 설치 확인
```bash
ls ~/.claude/skills/web-design-system/
```

### 2단계: 첫 프롬프트
```
"간단한 랜딩 페이지 만들어줘.
web-design-system skill 참고해서
뻔한 디자인 피하고 독창적으로"
```

### 3단계: 결과 확인
- ✅ 독창적인 색상 사용?
- ✅ 비대칭 레이아웃?
- ✅ 한글 최적화?
- ✅ 접근성 준수?

### 4단계: 세밀 조정
```
"좋은데, 더 대담하게 만들어줘.
가장 보수적인 부분 3가지를
더 창의적으로 바꿔줘"
```

---

## 📝 체크리스트

디자인 생성 전 확인:

### 준비 사항
- [ ] skill 설치 확인 (`~/.claude/skills/web-design-system/`)
- [ ] 프롬프트에 `web-design-system skill` 키워드 포함
- [ ] 피해야 할 디자인 명시 (선택)
- [ ] 요구사항 정리 (한글, 접근성 등)

### 생성 후 확인
- [ ] 보라색 그라데이션 없음
- [ ] shadcn/ui 느낌 없음
- [ ] 독창적인 색상 조합
- [ ] 비대칭 또는 브로큰 그리드
- [ ] 한글 최적화 (Pretendard + 행간)
- [ ] 접근성 (대비비 4.5:1)
- [ ] 반응형 디자인

---

## 🎁 보너스: VS Design Diverge 비교

이 skill은 Xavier Choi의 VS Design Diverge에서 영감을 받았습니다.

| 특징 | VS Design Diverge | web-design-system |
|------|-------------------|-------------------|
| **플랫폼** | Claude Code | Claude Web/Desktop |
| **목적** | 프론트엔드 개발 | 웹 기획/디자인 |
| **핵심 기법** | Verbalized Sampling | Verbalized Sampling |
| **출력** | 실행 가능한 코드 | 디자인 + 코드 |
| **한글** | 일부 지원 | 완전 최적화 |

---

## 📞 피드백 & 개선

이 skill을 사용하면서:
- 더 좋은 색상 팔레트 발견했나요?
- 새로운 레이아웃 패턴이 필요한가요?
- 더 피해야 할 안티패턴이 있나요?

Claude와 대화하면서 함께 skill을 발전시켜보세요!

---

## 📜 변경 이력

### v2.0 (2026-01-15)
- 🌙 **다크 모드 디자인** 가이드 추가
- 🎬 **모션 디자인 원칙** 추가 (타이밍 시스템, Reduced Motion)
- ⚡ **Core Web Vitals** 최적화 가이드 추가
- 🌐 **브라우저 호환성** 매트릭스 및 폴백 가이드
- 🧪 **테스트 도구** 섹션 추가
- 📚 참고 자료 확장

### v1.0 (2026-01-15)
- 초기 버전
- Verbalized Sampling 기법
- 한글 최적화
- 접근성 (WCAG 2.1 AA)
- 반응형 디자인

---

**작성:** 2026-01-15
**버전:** 2.0
**위치:** `.claude/skills/web-design-system/`

**영감:** [VS Design Diverge by Xavier Choi](https://www.threads.com/@internetbasedboy/post/DTg3KVUgSyP)
