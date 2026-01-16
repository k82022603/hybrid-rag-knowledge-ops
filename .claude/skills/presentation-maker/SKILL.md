# Presentation Maker Skill

## Overview
전문적인 비즈니스 및 기술 프레젠테이션을 제작하기 위한 comprehensive guide입니다. PowerPoint(PPTX), Marp 기반 마크다운, 그리고 시각적 스토리보드를 모두 지원합니다.

## When to Use This Skill
다음과 같은 경우에 이 skill을 사용합니다:
- 비즈니스 프레젠테이션 제작
- 기술 문서 발표 자료 준비
- 프로젝트 제안서 또는 보고서 슬라이드
- 교육/워크샵 자료 생성
- UI/UX 스토리보드 제작
- 시스템 아키텍처 설명 자료
- 슬라이드 편집 및 수정
- 차트, 표, 이미지 삽입
- 발표자 노트 추가
- 템플릿 사용

사용 예시:
- "AI 트렌드 프레젠테이션 5장 만들어줘"
- "분기 실적 보고 PPT 만들어줘 (차트 포함)"
- "UI스토리보드_발표자료_OceanDepths.pptx 파일을 참고해서 UI스토리보드_발표자료_TechInnovation.pptx 만들어줘"

---

## 필수 라이브러리

### 기본 Import (모든 프레젠테이션에 필수)
```python
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.dml.color import RGBColor
import os
```

### 확장 Import (고급 기능)
```python
# 차트 생성
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION

# 이미지 처리
from PIL import Image

# 텍스트 자동 크기 조정
from pptx.enum.text import MSO_AUTO_SIZE
```

### 라이브러리 설치
```bash
pip install python-pptx Pillow
```

---

## Theme Factory (테마 팩토리)

### 10가지 사전 정의 테마

각 테마는 완전한 컬러 팔레트와 사용 권장 분야를 포함합니다.

#### 1. Ocean Depths (오션 뎁스)
**권장**: 기업용, 전문적, 금융, 컨설팅
```python
OCEAN_DEPTHS = {
    'primary': RGBColor(0, 102, 153),      # #006699 - 깊은 바다 블루
    'secondary': RGBColor(0, 153, 204),    # #0099CC - 밝은 청록
    'accent': RGBColor(255, 102, 0),       # #FF6600 - 생동감 오렌지
    'dark': RGBColor(0, 51, 102),          # #003366 - 다크 네이비
    'light': RGBColor(204, 229, 255),      # #CCE5FF - 연한 하늘색
    'text': RGBColor(33, 33, 33),          # #212121 - 텍스트
    'white': RGBColor(255, 255, 255)       # #FFFFFF - 화이트
}
```

#### 2. Tech Innovation (테크 이노베이션)
**권장**: 기술, 스타트업, IT, 개발
```python
TECH_INNOVATION = {
    'primary': RGBColor(46, 125, 50),      # #2E7D32 - 녹색 (성장)
    'secondary': RGBColor(129, 199, 132),  # #81C784 - 연한 녹색
    'accent': RGBColor(255, 152, 0),       # #FF9800 - 오렌지
    'dark': RGBColor(27, 94, 32),          # #1B5E20 - 진한 녹색
    'light': RGBColor(232, 245, 233),      # #E8F5E9 - 민트
    'text': RGBColor(33, 33, 33),          # #212121
    'white': RGBColor(255, 255, 255)
}
```

#### 3. Modern Minimalist (모던 미니멀)
**권장**: 깔끔한 디자인, 미니멀리즘, 모던
```python
MODERN_MINIMALIST = {
    'primary': RGBColor(33, 33, 33),       # #212121 - 차콜
    'secondary': RGBColor(97, 97, 97),     # #616161 - 미디엄 그레이
    'accent': RGBColor(255, 87, 34),       # #FF5722 - 딥 오렌지
    'dark': RGBColor(0, 0, 0),             # #000000 - 블랙
    'light': RGBColor(250, 250, 250),      # #FAFAFA - 오프화이트
    'text': RGBColor(33, 33, 33),
    'white': RGBColor(255, 255, 255)
}
```

#### 4. Sunset Boulevard (선셋 대로)
**권장**: 창의적, 활기찬, 마케팅, 이벤트
```python
SUNSET_BOULEVARD = {
    'primary': RGBColor(255, 87, 34),      # #FF5722 - 딥 오렌지
    'secondary': RGBColor(255, 193, 7),    # #FFC107 - 앰버
    'accent': RGBColor(156, 39, 176),      # #9C27B0 - 퍼플
    'dark': RGBColor(191, 54, 12),         # #BF360C - 다크 오렌지
    'light': RGBColor(255, 243, 224),      # #FFF3E0 - 크림
    'text': RGBColor(33, 33, 33),
    'white': RGBColor(255, 255, 255)
}
```

#### 5. Forest Canopy (포레스트 캐노피)
**권장**: 자연친화적, 환경, 지속가능성, ESG
```python
FOREST_CANOPY = {
    'primary': RGBColor(56, 142, 60),      # #388E3C - 포레스트 그린
    'secondary': RGBColor(139, 195, 74),   # #8BC34A - 라이트 그린
    'accent': RGBColor(121, 85, 72),       # #795548 - 브라운
    'dark': RGBColor(27, 94, 32),          # #1B5E20 - 다크 그린
    'light': RGBColor(241, 248, 233),      # #F1F8E9 - 라이트 그린
    'text': RGBColor(33, 33, 33),
    'white': RGBColor(255, 255, 255)
}
```

#### 6. Golden Hour (골든 아워)
**권장**: 따뜻한, 환대, 호텔, F&B, 럭셔리
```python
GOLDEN_HOUR = {
    'primary': RGBColor(255, 160, 0),      # #FFA000 - 앰버
    'secondary': RGBColor(255, 202, 40),   # #FFCA28 - 골드
    'accent': RGBColor(121, 85, 72),       # #795548 - 브라운
    'dark': RGBColor(255, 111, 0),         # #FF6F00 - 다크 앰버
    'light': RGBColor(255, 248, 225),      # #FFF8E1 - 크림
    'text': RGBColor(62, 39, 35),          # #3E2723 - 다크 브라운
    'white': RGBColor(255, 255, 255)
}
```

#### 7. Arctic Frost (아틱 프로스트)
**권장**: 청결, 헬스케어, 의료, 제약, 과학
```python
ARCTIC_FROST = {
    'primary': RGBColor(3, 169, 244),      # #03A9F4 - 라이트 블루
    'secondary': RGBColor(79, 195, 247),   # #4FC3F7 - 스카이 블루
    'accent': RGBColor(0, 188, 212),       # #00BCD4 - 시안
    'dark': RGBColor(1, 87, 155),          # #01579B - 다크 블루
    'light': RGBColor(225, 245, 254),      # #E1F5FE - 아이스 블루
    'text': RGBColor(33, 33, 33),
    'white': RGBColor(255, 255, 255)
}
```

#### 8. Desert Rose (데저트 로즈)
**권장**: 우아한, 패션, 뷰티, 라이프스타일
```python
DESERT_ROSE = {
    'primary': RGBColor(194, 24, 91),      # #C2185B - 핑크
    'secondary': RGBColor(236, 64, 122),   # #EC407A - 로즈
    'accent': RGBColor(255, 193, 7),       # #FFC107 - 골드
    'dark': RGBColor(136, 14, 79),         # #880E4F - 다크 핑크
    'light': RGBColor(252, 228, 236),      # #FCE4EC - 라이트 핑크
    'text': RGBColor(33, 33, 33),
    'white': RGBColor(255, 255, 255)
}
```

#### 9. Botanical Garden (보타니컬 가든)
**권장**: 생동감, 자연, 유기농, 웰니스
```python
BOTANICAL_GARDEN = {
    'primary': RGBColor(0, 150, 136),      # #009688 - 틸
    'secondary': RGBColor(77, 182, 172),   # #4DB6AC - 민트
    'accent': RGBColor(255, 112, 67),      # #FF7043 - 코랄
    'dark': RGBColor(0, 77, 64),           # #004D40 - 다크 틸
    'light': RGBColor(224, 242, 241),      # #E0F2F1 - 라이트 틸
    'text': RGBColor(33, 33, 33),
    'white': RGBColor(255, 255, 255)
}
```

#### 10. Midnight Galaxy (미드나잇 갤럭시)
**권장**: 극적인, 엔터테인먼트, 게임, 미디어
```python
MIDNIGHT_GALAXY = {
    'primary': RGBColor(63, 81, 181),      # #3F51B5 - 인디고
    'secondary': RGBColor(121, 134, 203),  # #7986CB - 라벤더
    'accent': RGBColor(255, 64, 129),      # #FF4081 - 핑크
    'dark': RGBColor(26, 35, 126),         # #1A237E - 다크 인디고
    'light': RGBColor(232, 234, 246),      # #E8EAF6 - 라이트 인디고
    'text': RGBColor(255, 255, 255),       # 다크 배경용 화이트 텍스트
    'white': RGBColor(255, 255, 255)
}
```

---

## 테마 자동 선택 알고리즘

사용자가 테마를 지정하지 않은 경우, 콘텐츠를 분석하여 적절한 테마를 자동 선택합니다.

### 키워드 기반 테마 매칭
```python
def auto_select_theme(content_text, title=""):
    """
    콘텐츠와 제목을 분석하여 적절한 테마를 자동 선택

    Args:
        content_text: 프레젠테이션 전체 콘텐츠 텍스트
        title: 프레젠테이션 제목

    Returns:
        테마명 (str), 테마 팔레트 (dict)
    """
    text = (content_text + " " + title).lower()

    # 키워드-테마 매핑
    theme_keywords = {
        'tech_innovation': [
            'ai', '인공지능', 'ml', '머신러닝', 'api', '개발', 'developer',
            '코드', 'code', '프로그래밍', 'software', '소프트웨어', 'devops',
            '클라우드', 'cloud', '데이터', 'data', 'tech', '기술', 'it',
            'rag', 'llm', '딥러닝', 'deep learning', 'python', 'java',
            '시스템', 'system', '아키텍처', 'architecture', '플랫폼', 'platform'
        ],
        'ocean_depths': [
            '기업', 'enterprise', '비즈니스', 'business', '전략', 'strategy',
            '금융', 'finance', '투자', 'investment', '컨설팅', 'consulting',
            '경영', 'management', '조직', 'organization', '리더십', 'leadership',
            '분기', 'quarter', '실적', 'performance', '보고', 'report'
        ],
        'forest_canopy': [
            '환경', 'environment', '지속가능', 'sustainable', 'esg', '친환경',
            'green', '탄소', 'carbon', '에너지', 'energy', '재활용', 'recycle',
            '자연', 'nature', '생태', 'ecology', '기후', 'climate'
        ],
        'arctic_frost': [
            '의료', 'medical', '헬스케어', 'healthcare', '병원', 'hospital',
            '제약', 'pharmaceutical', '바이오', 'bio', '임상', 'clinical',
            '과학', 'science', '연구', 'research', '실험', 'experiment'
        ],
        'sunset_boulevard': [
            '마케팅', 'marketing', '광고', 'advertising', '캠페인', 'campaign',
            '브랜드', 'brand', '이벤트', 'event', '프로모션', 'promotion',
            '소셜', 'social', '미디어', 'media', '콘텐츠', 'content'
        ],
        'desert_rose': [
            '패션', 'fashion', '뷰티', 'beauty', '화장품', 'cosmetic',
            '라이프스타일', 'lifestyle', '디자인', 'design', '럭셔리', 'luxury'
        ],
        'golden_hour': [
            '호텔', 'hotel', '관광', 'tourism', '여행', 'travel',
            '레스토랑', 'restaurant', 'f&b', '음식', 'food', '서비스', 'service'
        ],
        'botanical_garden': [
            '웰니스', 'wellness', '건강', 'health', '유기농', 'organic',
            '요가', 'yoga', '명상', 'meditation', '피트니스', 'fitness'
        ],
        'midnight_galaxy': [
            '게임', 'game', '엔터테인먼트', 'entertainment', '미디어', 'media',
            '영화', 'movie', '음악', 'music', '스트리밍', 'streaming',
            'vr', 'ar', '메타버스', 'metaverse'
        ],
        'modern_minimalist': [
            '미니멀', 'minimal', '심플', 'simple', '모던', 'modern',
            '깔끔', 'clean', '디자인', 'design'
        ]
    }

    # 점수 계산
    scores = {theme: 0 for theme in theme_keywords}

    for theme, keywords in theme_keywords.items():
        for keyword in keywords:
            if keyword in text:
                scores[theme] += 1

    # 최고 점수 테마 선택
    best_theme = max(scores, key=scores.get)

    # 점수가 0이면 기본 테마 사용
    if scores[best_theme] == 0:
        best_theme = 'ocean_depths'  # 기본값: 범용적인 Ocean Depths

    # 테마 팔레트 반환
    theme_palettes = {
        'tech_innovation': TECH_INNOVATION,
        'ocean_depths': OCEAN_DEPTHS,
        'forest_canopy': FOREST_CANOPY,
        'arctic_frost': ARCTIC_FROST,
        'sunset_boulevard': SUNSET_BOULEVARD,
        'desert_rose': DESERT_ROSE,
        'golden_hour': GOLDEN_HOUR,
        'botanical_garden': BOTANICAL_GARDEN,
        'midnight_galaxy': MIDNIGHT_GALAXY,
        'modern_minimalist': MODERN_MINIMALIST
    }

    return best_theme, theme_palettes[best_theme]
```

### 테마 자동 선택 요약표

| 콘텐츠 유형 | 추천 테마 | 주요 키워드 |
|------------|----------|------------|
| 기술/개발 | Tech Innovation | AI, 개발, 시스템, 아키텍처 |
| 기업/비즈니스 | Ocean Depths | 기업, 전략, 실적, 보고 |
| 환경/ESG | Forest Canopy | 지속가능, 환경, 친환경 |
| 의료/과학 | Arctic Frost | 의료, 헬스케어, 연구 |
| 마케팅/이벤트 | Sunset Boulevard | 마케팅, 캠페인, 브랜드 |
| 패션/뷰티 | Desert Rose | 패션, 뷰티, 라이프스타일 |
| 호텔/F&B | Golden Hour | 호텔, 관광, 서비스 |
| 웰니스/건강 | Botanical Garden | 웰니스, 건강, 유기농 |
| 게임/엔터 | Midnight Galaxy | 게임, 엔터테인먼트, 미디어 |
| 미니멀/모던 | Modern Minimalist | 미니멀, 심플, 모던 |

---

## Core Principles

### 1. 한국어 콘텐츠 최적화
- **폰트 설정**: Pretendard, Noto Sans KR, 맑은 고딕 등 한글 가독성이 우수한 폰트 사용. 사용자가 지정하지 않으면 기본값은 맑은 고딕입니다.
- **행간 조정**: 한글은 영문보다 20-30% 더 넓은 행간 필요 (1.6-1.8)하지만, 행간 조정은 하지 않습니다.
- **글자 크기**:
  - 표지 제목: 40pt
  - 표지 부제목: 16pt
  - 제목: 24pt
  - 부제목: 16pt
  - 본문: 레벨에 따라 8pt, 12pt, 14pt, 16pt
  - 캡션: 10pt

### 2. 시각적 계층 구조
```
명확한 정보 계층:
┌─────────────────────────┐
│  제목 (Primary Color)    │ ← 가장 눈에 띄게
├─────────────────────────┤
│  핵심 메시지 (강조)       │ ← 두 번째로 강조
├─────────────────────────┤
│  세부 내용 (본문) 또는 도식화 이미지 │ ← 읽기 편한 크기 (높이 13cm/너비 22cm)
└─────────────────────────┘
│  출처/참고 (작게)         │ ← 보조 정보


**세부 내용 우측에 "설명" 추가 작성** : 사각형 박스 width 8.5cm, height 13cm background color 226, 240, 217 (연한 톤) 도형효과 바깥쪽 테두리 color 226, 240, 217 (연한 톤), 설명 추가는 1,2,3,4 번호 붙여 서술형으로 작성

단, 샘플 파일이 있는 경우 샘플 파일을 참고하여 작성해주세요.
```

### 3. 색상 대비
- **텍스트와 배경 대비비**: 최소 4.5:1 (WCAG AA 기준)
- **강조 색상**: 스파링하게 사용 (전체의 10-20%)
- **일관성**: 같은 의미는 같은 색상 사용

---

## PPTX 도형 기반 다이어그램 생성

### 핵심: 이미지 대신 PPTX 도형 사용

이미지 파일 대신 python-pptx의 도형 기능을 사용하면:
- 편집 가능한 벡터 도형 생성
- 외부 이미지 파일 불필요
- 확대/축소 시 품질 유지
- PPTX 파일 내에서 직접 수정 가능

### 화살표 생성 함수
```python
def add_arrow(slide, x1, y1, x2, y2, color=None, width=4):
    """
    슬라이드에 화살표 추가

    Args:
        slide: 대상 슬라이드
        x1, y1: 시작점 (Inches)
        x2, y2: 끝점 (Inches)
        color: 선 색상 (RGBColor)
        width: 선 두께 (Pt)
    """
    connector = slide.shapes.add_connector(
        MSO_CONNECTOR.STRAIGHT,
        Inches(x1), Inches(y1),
        Inches(x2), Inches(y2)
    )
    connector.line.color.rgb = color or RGBColor(255, 102, 0)
    connector.line.width = Pt(width)
    connector.line.end_arrow_type = 2  # 화살표 머리
    return connector
```

### 둥근 박스 생성 함수
```python
def add_rounded_box(slide, left, top, width, height, text,
                    fill_color, text_color=None, font_size=20, font_name="맑은 고딕"):
    """
    둥근 모서리 박스 추가

    Args:
        slide: 대상 슬라이드
        left, top: 위치 (Inches)
        width, height: 크기 (Inches)
        text: 박스 내 텍스트
        fill_color: 배경색 (RGBColor)
        text_color: 텍스트색 (RGBColor, 기본값: 흰색)
        font_size: 폰트 크기 (Pt)
        font_name: 폰트 이름
    """
    if text_color is None:
        text_color = RGBColor(255, 255, 255)

    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(left), Inches(top),
        Inches(width), Inches(height)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    shape.line.color.rgb = RGBColor(0, 51, 102)  # 테두리
    shape.line.width = Pt(2)

    # 텍스트 설정
    text_frame = shape.text_frame
    text_frame.text = text
    text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE

    paragraph = text_frame.paragraphs[0]
    paragraph.font.size = Pt(font_size)
    paragraph.font.color.rgb = text_color
    paragraph.font.name = font_name
    paragraph.font.bold = True
    paragraph.alignment = PP_ALIGN.CENTER

    return shape
```

### 시스템 아키텍처 다이어그램 생성 예제
```python
def create_architecture_diagram_slide(prs, theme):
    """
    시스템 아키텍처 다이어그램 슬라이드 생성 (도형 사용)
    """
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # 빈 레이아웃

    # 헤더 바
    header = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0), Inches(0),
        Inches(10), Inches(0.8)
    )
    header.fill.solid()
    header.fill.fore_color.rgb = theme['secondary']
    header.line.color.rgb = theme['secondary']

    # 제목
    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.15), Inches(9), Inches(0.5))
    tf = title_box.text_frame
    tf.text = "시스템 아키텍처"
    p = tf.paragraphs[0]
    p.font.size = Pt(36)
    p.font.bold = True
    p.font.color.rgb = theme['white']
    p.font.name = "맑은 고딕"

    # Frontend Layer
    add_rounded_box(slide, 0.5, 1.2, 9, 0.8,
                   "Frontend Layer\nReact 18 + TypeScript",
                   theme['secondary'], font_size=22)

    # API Gateway
    add_rounded_box(slide, 0.5, 2.3, 9, 0.7,
                   "API Gateway - Spring Cloud Gateway",
                   theme['primary'], font_size=20)

    # Service Layer
    services = [
        ("Knowledge\nService", 0.5),
        ("Search\nService", 2.9),
        ("User\nService", 5.3),
        ("AI Service\n(FastAPI)", 7.7)
    ]

    for name, x in services:
        add_rounded_box(slide, x, 3.4, 2.2, 1.0, name, theme['accent'], font_size=16)

    # Database Layer
    databases = [
        ("PostgreSQL", 0.5),
        ("Elasticsearch", 2.9),
        ("Neo4j", 5.3),
        ("Redis", 7.7)
    ]

    for name, x in databases:
        add_rounded_box(slide, x, 4.8, 2.2, 0.9, name, theme['dark'], font_size=18)

    # 화살표 추가
    arrow_x = [1.6, 4.0, 6.4, 8.8]

    for x in arrow_x:
        add_arrow(slide, x, 2.0, x, 2.3, theme['accent'])  # Frontend -> Gateway
        add_arrow(slide, x, 3.0, x, 3.4, theme['accent'])  # Gateway -> Services
        add_arrow(slide, x, 4.4, x, 4.8, theme['accent'])  # Services -> DB

    return slide
```

### 비교 다이어그램 생성 (2열 패널)
```python
def create_comparison_diagram_slide(prs, theme, title, left_title, left_items, right_title, right_items):
    """
    좌우 비교 다이어그램 슬라이드 생성
    """
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # 헤더
    header = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(10), Inches(0.8)
    )
    header.fill.solid()
    header.fill.fore_color.rgb = theme['secondary']
    header.line.color.rgb = theme['secondary']

    # 제목
    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.15), Inches(9), Inches(0.5))
    tf = title_box.text_frame
    tf.text = title
    p = tf.paragraphs[0]
    p.font.size = Pt(36)
    p.font.bold = True
    p.font.color.rgb = theme['white']
    p.font.name = "맑은 고딕"

    # 왼쪽 패널
    left_panel = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(0.3), Inches(1.0), Inches(4.6), Inches(5.8)
    )
    left_panel.fill.solid()
    left_panel.fill.fore_color.rgb = theme['light']
    left_panel.line.color.rgb = theme['primary']
    left_panel.line.width = Pt(4)

    # 왼쪽 헤더
    left_header = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(0.3), Inches(1.0), Inches(4.6), Inches(0.8)
    )
    left_header.fill.solid()
    left_header.fill.fore_color.rgb = theme['primary']
    left_header.line.color.rgb = theme['primary']

    # 왼쪽 제목
    lt = slide.shapes.add_textbox(Inches(0.5), Inches(1.2), Inches(4.2), Inches(0.4))
    lt.text_frame.text = left_title
    lt.text_frame.paragraphs[0].font.size = Pt(28)
    lt.text_frame.paragraphs[0].font.bold = True
    lt.text_frame.paragraphs[0].font.color.rgb = theme['white']
    lt.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

    # 왼쪽 내용
    y = 2.2
    for item in left_items:
        tb = slide.shapes.add_textbox(Inches(0.6), Inches(y), Inches(4), Inches(0.4))
        tb.text_frame.text = item
        p = tb.text_frame.paragraphs[0]
        p.font.size = Pt(18)
        p.font.color.rgb = theme['text']
        p.font.name = "맑은 고딕"
        y += 0.6

    # 오른쪽 패널 (동일한 방식으로 생성)
    right_panel = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(5.1), Inches(1.0), Inches(4.6), Inches(5.8)
    )
    right_panel.fill.solid()
    right_panel.fill.fore_color.rgb = theme['light']
    right_panel.line.color.rgb = theme['secondary']
    right_panel.line.width = Pt(4)

    right_header = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(5.1), Inches(1.0), Inches(4.6), Inches(0.8)
    )
    right_header.fill.solid()
    right_header.fill.fore_color.rgb = theme['secondary']
    right_header.line.color.rgb = theme['secondary']

    rt = slide.shapes.add_textbox(Inches(5.3), Inches(1.2), Inches(4.2), Inches(0.4))
    rt.text_frame.text = right_title
    rt.text_frame.paragraphs[0].font.size = Pt(28)
    rt.text_frame.paragraphs[0].font.bold = True
    rt.text_frame.paragraphs[0].font.color.rgb = theme['white']
    rt.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

    y = 2.2
    for item in right_items:
        tb = slide.shapes.add_textbox(Inches(5.4), Inches(y), Inches(4), Inches(0.4))
        tb.text_frame.text = item
        p = tb.text_frame.paragraphs[0]
        p.font.size = Pt(18)
        p.font.color.rgb = theme['text']
        p.font.name = "맑은 고딕"
        y += 0.6

    return slide
```

---

## 슬라이드 레이아웃 템플릿

### 1. 표지 슬라이드 (테마 적용)
```python
def create_title_slide(prs, title, subtitle, theme):
    """
    표지 슬라이드 생성 (테마 적용)
    """
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # 배경
    bg = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0), Inches(0), Inches(10), Inches(7.5)
    )
    bg.fill.solid()
    bg.fill.fore_color.rgb = theme['dark']
    bg.line.color.rgb = theme['dark']

    # 장식 요소
    deco = slide.shapes.add_shape(
        MSO_SHAPE.OVAL,
        Inches(6), Inches(5), Inches(5), Inches(3)
    )
    deco.fill.solid()
    deco.fill.fore_color.rgb = theme['primary']
    deco.line.color.rgb = theme['primary']

    # 제목
    title_box = slide.shapes.add_textbox(Inches(1), Inches(2.5), Inches(8), Inches(1.2))
    tf = title_box.text_frame
    tf.text = title
    p = tf.paragraphs[0]
    p.font.size = Pt(54)
    p.font.bold = True
    p.font.color.rgb = theme['white']
    p.font.name = "맑은 고딕"
    p.alignment = PP_ALIGN.CENTER

    # 부제목
    sub_box = slide.shapes.add_textbox(Inches(1), Inches(4), Inches(8), Inches(0.8))
    sf = sub_box.text_frame
    sf.text = subtitle
    sp = sf.paragraphs[0]
    sp.font.size = Pt(28)
    sp.font.color.rgb = theme['light']
    sp.font.name = "맑은 고딕"
    sp.alignment = PP_ALIGN.CENTER

    return slide
```

### 2. 콘텐츠 슬라이드 (테마 적용)
```python
def create_content_slide(prs, title, content_lines, theme):
    """
    일반 콘텐츠 슬라이드 생성 (테마 적용)
    """
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # 헤더 바
    header = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0), Inches(0), Inches(10), Inches(1)
    )
    header.fill.solid()
    header.fill.fore_color.rgb = theme['primary']
    header.line.color.rgb = theme['primary']

    # 제목
    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.2), Inches(9), Inches(0.6))
    tf = title_box.text_frame
    tf.text = title
    p = tf.paragraphs[0]
    p.font.size = Pt(40)
    p.font.bold = True
    p.font.color.rgb = theme['white']
    p.font.name = "맑은 고딕"

    # 내용
    content_box = slide.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(8.4), Inches(5.5))
    cf = content_box.text_frame
    cf.word_wrap = True

    for line in content_lines:
        p = cf.add_paragraph()
        p.text = line
        p.font.size = Pt(20)
        p.font.color.rgb = theme['text']
        p.font.name = "맑은 고딕"
        p.space_after = Pt(12)

    return slide
```

### 3. 2열 레이아웃 (테마 적용)
```python
def create_two_column_slide(prs, title, left_items, right_items, theme):
    """
    2열 레이아웃 슬라이드 생성 (테마 적용)
    """
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # 헤더 바
    header = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0), Inches(0), Inches(10), Inches(1)
    )
    header.fill.solid()
    header.fill.fore_color.rgb = theme['primary']
    header.line.color.rgb = theme['primary']

    # 제목
    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.2), Inches(9), Inches(0.6))
    tf = title_box.text_frame
    tf.text = title
    p = tf.paragraphs[0]
    p.font.size = Pt(40)
    p.font.bold = True
    p.font.color.rgb = theme['white']
    p.font.name = "맑은 고딕"

    # 왼쪽 패널
    left_panel = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(0.5), Inches(1.5), Inches(4.25), Inches(5.5)
    )
    left_panel.fill.solid()
    left_panel.fill.fore_color.rgb = theme['light']
    left_panel.line.color.rgb = theme['primary']
    left_panel.line.width = Pt(3)

    left_text = slide.shapes.add_textbox(Inches(0.8), Inches(1.8), Inches(3.7), Inches(5))
    ltf = left_text.text_frame
    ltf.word_wrap = True

    for item in left_items:
        p = ltf.add_paragraph()
        p.text = item
        p.font.size = Pt(18)
        p.font.color.rgb = theme['text']
        p.font.name = "맑은 고딕"
        p.space_after = Pt(10)

    # 오른쪽 패널
    right_panel = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(5.25), Inches(1.5), Inches(4.25), Inches(5.5)
    )
    right_panel.fill.solid()
    right_panel.fill.fore_color.rgb = theme['light']
    right_panel.line.color.rgb = theme['secondary']
    right_panel.line.width = Pt(3)

    right_text = slide.shapes.add_textbox(Inches(5.55), Inches(1.8), Inches(3.7), Inches(5))
    rtf = right_text.text_frame
    rtf.word_wrap = True

    for item in right_items:
        p = rtf.add_paragraph()
        p.text = item
        p.font.size = Pt(18)
        p.font.color.rgb = theme['text']
        p.font.name = "맑은 고딕"
        p.space_after = Pt(10)

    return slide
```

---

## 완전한 프레젠테이션 생성 플로우

### 테마 자동 선택 + 프레젠테이션 생성
```python
def create_full_presentation(title, subtitle, sections, output_path, user_theme=None):
    """
    전체 프레젠테이션 생성 (테마 자동 선택 포함)

    Args:
        title: 프레젠테이션 제목
        subtitle: 부제목
        sections: 슬라이드 섹션 리스트
        output_path: 저장 경로
        user_theme: 사용자 지정 테마 (없으면 자동 선택)
    """
    # 콘텐츠에서 텍스트 추출
    content_text = title + " " + subtitle
    for section in sections:
        if 'data' in section:
            if isinstance(section['data'], list):
                content_text += " " + " ".join(section['data'])
            elif isinstance(section['data'], str):
                content_text += " " + section['data']

    # 테마 선택
    if user_theme:
        theme_name = user_theme
        theme = get_theme_by_name(user_theme)
    else:
        theme_name, theme = auto_select_theme(content_text, title)
        print(f"자동 선택된 테마: {theme_name}")

    # 프레젠테이션 생성
    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(7.5)

    # 표지
    create_title_slide(prs, title, subtitle, theme)

    # 섹션별 슬라이드 생성
    for section in sections:
        if section['type'] == 'content':
            create_content_slide(prs, section['title'], section['data'], theme)
        elif section['type'] == 'two_column':
            create_two_column_slide(prs, section['title'],
                                   section['data']['left'],
                                   section['data']['right'], theme)
        elif section['type'] == 'architecture':
            create_architecture_diagram_slide(prs, theme)
        elif section['type'] == 'comparison':
            create_comparison_diagram_slide(prs, theme,
                                           section['title'],
                                           section['data']['left_title'],
                                           section['data']['left_items'],
                                           section['data']['right_title'],
                                           section['data']['right_items'])

    # 저장
    prs.save(output_path)
    print(f"프레젠테이션 저장 완료: {output_path}")
    print(f"적용된 테마: {theme_name}")
    print(f"총 슬라이드 수: {len(prs.slides)}")

    return prs
```

---

## Marp Markdown Presentations

### 기본 구조
```markdown
---
marp: true
theme: default
paginate: true
backgroundColor: #fff
style: |
  section {
    font-family: 'Pretendard', 'Noto Sans KR', 'Segoe UI', sans-serif;
  }
  h1 {
    color: #1976D2;
    font-size: 2.5em;
  }
  h2 {
    color: #424242;
    border-bottom: 3px solid #1976D2;
    padding-bottom: 0.3em;
  }
---

# 메인 타이틀
## 부제목

**작성자 이름**
날짜

---

# 섹션 제목

내용 시작...
```

### Marp → PPTX 변환 (CLI)
```bash
# Marp CLI 설치 (필요시)
npm install -g @marp-team/marp-cli

# PPTX 변환
marp presentation.md --pptx -o presentation.pptx

# PDF 변환
marp presentation.md --pdf -o presentation.pdf

# HTML 변환
marp presentation.md --html -o presentation.html
```

---

## 파일 저장 규칙

1. **사용자 지정 디렉토리/파일명**: 사용자가 지정한 대로 저장
2. **파일명만 지정**: 현재 디렉토리에 저장
3. **미지정**: 현재 디렉토리에 적절한 파일명으로 저장 (예: `presentation_{제목}.pptx`)

```python
import os

def get_output_path(user_path=None, title="presentation"):
    """출력 경로 결정"""
    if user_path:
        # 사용자 지정 경로 사용
        if os.path.isdir(user_path):
            return os.path.join(user_path, f"{title}.pptx")
        return user_path
    else:
        # 현재 디렉토리에 저장
        return f"{title}.pptx"
```

---

## 품질 체크리스트

### 콘텐츠
- [ ] 각 슬라이드에 명확한 제목이 있는가?
- [ ] 한 슬라이드 = 하나의 핵심 메시지인가?
- [ ] 불릿 포인트가 6개 이하인가?
- [ ] 전문 용어에 설명이 있는가?

### 디자인
- [ ] 한글 폰트가 적절한가? (맑은 고딕 등)
- [ ] 색상 대비가 충분한가? (4.5:1 이상)
- [ ] 일관된 색상 체계를 사용하는가?
- [ ] 여백이 적절한가? (너무 빽빽하지 않은가)

### 기술
- [ ] 다이어그램이 정렬되어 있는가?
- [ ] 표가 읽기 쉬운가?
- [ ] 코드 블록이 고정폭 폰트를 사용하는가?

### 접근성
- [ ] 텍스트와 배경 대비가 충분한가?
- [ ] 폰트 크기가 충분한가? (최소 18pt)

---

## 문제 해결

### 한글 폰트 깨짐
```python
# 시스템 폰트 확인
# Windows: C:\Windows\Fonts\malgun.ttf
# 대체 폰트 사용
font_name = "맑은 고딕"  # Windows 기본
```

### 슬라이드 크기
```python
# 16:9 비율 (권장)
prs.slide_width = Inches(10)
prs.slide_height = Inches(5.625)

# 4:3 비율
prs.slide_width = Inches(10)
prs.slide_height = Inches(7.5)
```

---

## 참고 자료

- [python-pptx 공식 문서](https://python-pptx.readthedocs.io/)
- [Marp 공식 사이트](https://marp.app/)
- [색상 대비 체커](https://webaim.org/resources/contrastchecker/)

---

## 마무리

이 스킬을 사용하여:
1. **요구사항 파악** (발표 목적, 대상, 시간)
2. **테마 선택** (사용자 지정 또는 자동 선택)
3. **구조 설계** (섹션, 슬라이드 수)
4. **콘텐츠 작성** (핵심 메시지 중심)
5. **도형 기반 다이어그램 생성** (편집 가능한 벡터)
6. **검토 및 수정** (체크리스트 확인)

전문적이고 효과적인 프레젠테이션을 만들 수 있습니다!
