---
name: enterprise-ppt-generator
description: 대기업 제안서/신청서용 전문 PPT 생성. 아키텍처 도식화, 비교표, 테마 선택 지원. KERIS 스타일 기반.
user-invocable: true
arguments:
  - name: source
    description: 원본 마크다운 파일 경로 또는 주제
    required: true
  - name: theme
    description: "테마 선택 (1: Ocean Depths, 2: Golden Hour, 3: Tech Innovation)"
    required: false
    default: "1"
---

# Enterprise PPT Generator Skill

대기업 제안서, 예외 신청서, 기술 보고서 등 전문적인 비즈니스 프레젠테이션을 생성합니다.
KERIS 스타일 기반으로 아키텍처 도식화, 비교표, 설명 패널 등을 포함합니다.

## 사용법

```
/enterprise-ppt-generator <source> [--theme <1|2|3>]
```

### 예시
- `/enterprise-ppt-generator 01.문서작업/proposal.md --theme 1`
- `/enterprise-ppt-generator "클라우드 전환 제안서" --theme 2`

## 사용 가능한 테마 (3종)

| 번호 | 테마명 | 설명 | 권장 용도 |
|------|--------|------|-----------|
| **1** | Ocean Depths (오션 뎁스) | 깊은 바다 블루 계열 | 기업용, 전문적, 금융, 컨설팅 |
| **2** | Golden Hour (골든 아워) | 따뜻한 앰버/브라운 계열 | 호텔, F&B, 럭셔리, 따뜻한 분위기 |
| **3** | Tech Innovation (테크 이노베이션) | 녹색/성장 계열 | 기술, 스타트업, IT, 개발 |

## 핵심 기능

### 1. 아키텍처 도식화 슬라이드
- MSA 전환 아키텍처 (AS-IS → TO-BE)
- Istio Multi-Primary 토폴로지
- mTLS 인증서 관리 체계
- 클라우드 네이티브 아키텍처
- N2SF Zero Trust 보안 아키텍처
- DR 센터 구성 (Active-Active / Active-Standby)
- DevSecOps CI/CD 파이프라인
- RPA + AI 통합 아키텍처

### 2. 비교표 슬라이드
- 대기업 vs 중소기업 역량 비교
- AS-IS vs TO-BE 비교
- TCO 비교 분석

### 3. 설명 패널
- 연한 녹색 배경의 번호 리스트 설명
- 도식화 옆에 상세 설명 배치

## 슬라이드 크기

- 와이드스크린: 13.333" x 7.5" (16:9)

## 테마 정의

### 1. Ocean Depths (오션 뎁스)
```python
OCEAN_DEPTHS = {
    'name': 'Ocean Depths (오션 뎁스)',
    'description': '기업용, 전문적, 금융, 컨설팅',
    'primary': RGBColor(0, 102, 153),      # #006699 - 깊은 바다 블루
    'secondary': RGBColor(0, 153, 204),    # #0099CC - 밝은 청록
    'accent': RGBColor(0, 51, 102),        # #003366 - 다크 네이비
    'dark': RGBColor(33, 33, 33),          # #212121 - 텍스트
    'light': RGBColor(204, 229, 255),      # #CCE5FF - 연한 하늘색
    'light2': RGBColor(230, 242, 255),     # #E6F2FF - 더 연한 하늘색
    'header_text': RGBColor(255, 255, 255),
    'table_header': RGBColor(0, 102, 153),
    'table_alt': RGBColor(230, 242, 255),
    'cover_bg': RGBColor(0, 51, 102),
    'cover_deco': RGBColor(0, 102, 153),
    'cover_title': RGBColor(255, 255, 255), # #FFFFFF - 화이트 (배경 대비)
    'box_fill': RGBColor(0, 102, 153),
    'box_fill2': RGBColor(0, 153, 204),
    'box_fill3': RGBColor(0, 51, 102),
    'arrow': RGBColor(255, 102, 0),
    'success': RGBColor(46, 125, 50),
    'warning': RGBColor(255, 152, 0),
    'danger': RGBColor(211, 47, 47),
}
```

### 2. Golden Hour (골든 아워)
```python
GOLDEN_HOUR = {
    'name': 'Golden Hour (골든 아워)',
    'description': '따뜻한, 환대, 호텔, F&B, 럭셔리',
    'primary': RGBColor(255, 160, 0),      # #FFA000 - 앰버
    'secondary': RGBColor(255, 111, 0),    # #FF6F00 - 다크 앰버
    'accent': RGBColor(121, 85, 72),       # #795548 - 브라운
    'dark': RGBColor(62, 39, 35),          # #3E2723 - 다크 초콜릿
    'light': RGBColor(255, 248, 225),      # #FFF8E1 - 크림
    'light2': RGBColor(255, 243, 224),     # #FFF3E0 - 더 연한 크림
    'header_text': RGBColor(255, 248, 225),
    'table_header': RGBColor(141, 110, 99),
    'table_alt': RGBColor(239, 235, 233),
    'cover_bg': RGBColor(62, 39, 35),
    'cover_deco': RGBColor(121, 85, 72),
    'cover_title': RGBColor(255, 160, 0),  # #FFA000 - 앰버 (대비 양호)
    'box_fill': RGBColor(121, 85, 72),
    'box_fill2': RGBColor(161, 136, 127),
    'box_fill3': RGBColor(62, 39, 35),
    'arrow': RGBColor(255, 160, 0),
    'success': RGBColor(46, 125, 50),
    'warning': RGBColor(255, 152, 0),
    'danger': RGBColor(211, 47, 47),
}
```

### 3. Tech Innovation (테크 이노베이션)
```python
TECH_INNOVATION = {
    'name': 'Tech Innovation (테크 이노베이션)',
    'description': '기술, 스타트업, IT, 개발',
    'primary': RGBColor(46, 125, 50),      # #2E7D32 - 녹색
    'secondary': RGBColor(129, 199, 132),  # #81C784 - 연한 녹색
    'accent': RGBColor(27, 94, 32),        # #1B5E20 - 진한 녹색
    'dark': RGBColor(33, 33, 33),          # #212121 - 텍스트
    'light': RGBColor(232, 245, 233),      # #E8F5E9 - 민트
    'light2': RGBColor(241, 248, 233),     # #F1F8E9 - 더 연한 민트
    'header_text': RGBColor(255, 255, 255),
    'table_header': RGBColor(46, 125, 50),
    'table_alt': RGBColor(232, 245, 233),
    'cover_bg': RGBColor(27, 94, 32),
    'cover_deco': RGBColor(46, 125, 50),
    'cover_title': RGBColor(255, 255, 255), # #FFFFFF - 화이트 (배경 대비)
    'box_fill': RGBColor(46, 125, 50),
    'box_fill2': RGBColor(129, 199, 132),
    'box_fill3': RGBColor(27, 94, 32),
    'arrow': RGBColor(255, 152, 0),
    'success': RGBColor(46, 125, 50),
    'warning': RGBColor(255, 152, 0),
    'danger': RGBColor(211, 47, 47),
}
```

## 핵심 함수

### 헤더 추가
```python
def add_header(self, slide, slide_title, section_title):
    """헤더 바 + 슬라이드 제목 + 섹션 제목"""
    header = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
        Inches(0), Inches(0), Inches(13.333), Inches(0.8))
    header.fill.solid()
    header.fill.fore_color.rgb = self.theme['accent']
    header.line.fill.background()

    # 슬라이드 제목 (좌측)
    title_box = slide.shapes.add_textbox(Inches(0.4), Inches(0.18), Inches(8), Inches(0.5))
    p = title_box.text_frame.paragraphs[0]
    p.text = slide_title
    p.font.size = Pt(24)
    p.font.bold = True
    p.font.color.rgb = self.theme['header_text']
    p.font.name = "맑은 고딕"

    # 섹션 제목 (우측)
    section_box = slide.shapes.add_textbox(Inches(8.5), Inches(0.22), Inches(4.5), Inches(0.45))
    sp = section_box.text_frame.paragraphs[0]
    sp.text = section_title
    sp.font.size = Pt(14)
    sp.font.color.rgb = self.theme['light']
    sp.font.name = "맑은 고딕"
    sp.alignment = PP_ALIGN.RIGHT
```

### 설명 패널 (연한 녹색 배경)
```python
def add_explanation_panel(self, slide, left, top, width, height, items, title="설명"):
    """
    도식화 옆에 배치되는 설명 패널
    연한 녹색 배경 (#E2F0D9) + 번호 리스트
    """
    panel = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(left), Inches(top), Inches(width), Inches(height))
    panel.fill.solid()
    panel.fill.fore_color.rgb = RGBColor(226, 240, 217)  # 연한 녹색
    panel.line.color.rgb = RGBColor(196, 220, 187)
    panel.line.width = Pt(2)

    # 제목
    title_box = slide.shapes.add_textbox(Inches(left + 0.15), Inches(top + 0.1),
        Inches(width - 0.3), Inches(0.35))
    p = title_box.text_frame.paragraphs[0]
    p.text = title
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = self.theme['accent']
    p.font.name = "맑은 고딕"

    # 내용 (번호 리스트)
    y = top + 0.45
    for i, item in enumerate(items, 1):
        item_box = slide.shapes.add_textbox(Inches(left + 0.15), Inches(y),
            Inches(width - 0.3), Inches(0.6))
        tf = item_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = f"{i}. {item}"
        p.font.size = Pt(9)
        p.font.color.rgb = self.theme['dark']
        p.font.name = "맑은 고딕"
        y += 0.55
```

### 테이블 추가
```python
def add_table(self, slide, headers, rows, start_y=1.5, col_widths=None):
    """
    비교표/데이터 테이블 생성
    헤더: 테마 색상 배경
    행: 홀짝 줄무늬
    """
    num_cols = len(headers)
    num_rows = len(rows) + 1
    if col_widths is None:
        col_widths = [12.3 / num_cols] * num_cols

    table_height = 0.4 + len(rows) * 0.35
    table = slide.shapes.add_table(num_rows, num_cols,
        Inches(0.5), Inches(start_y),
        Inches(sum(col_widths)), Inches(min(table_height, 5.5))).table

    # 헤더 스타일
    for j, header in enumerate(headers):
        cell = table.cell(0, j)
        cell.text = header
        cell.fill.solid()
        cell.fill.fore_color.rgb = self.theme['table_header']
        p = cell.text_frame.paragraphs[0]
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = self.theme['header_text']
        p.font.name = "맑은 고딕"
        p.alignment = PP_ALIGN.CENTER
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE

    # 데이터 행
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = table.cell(i + 1, j)
            cell.text = str(val)
            cell.fill.solid()
            cell.fill.fore_color.rgb = self.theme['table_alt'] if i % 2 == 1 else self.theme['light']
            p = cell.text_frame.paragraphs[0]
            p.font.size = Pt(10)
            p.font.color.rgb = self.theme['dark']
            p.font.name = "맑은 고딕"
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
```

### 둥근 박스 추가
```python
def add_rounded_box(self, slide, left, top, width, height, text,
                    fill_color, text_color=None, font_size=10, bold=True):
    """아키텍처 도식화용 둥근 박스"""
    if text_color is None:
        text_color = RGBColor(255, 255, 255)

    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(left), Inches(top), Inches(width), Inches(height))
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    shape.line.color.rgb = self.theme['dark']
    shape.line.width = Pt(1)

    tf = shape.text_frame
    tf.word_wrap = True
    tf.paragraphs[0].text = text
    tf.paragraphs[0].font.size = Pt(font_size)
    tf.paragraphs[0].font.color.rgb = text_color
    tf.paragraphs[0].font.name = "맑은 고딕"
    tf.paragraphs[0].font.bold = bold
    tf.paragraphs[0].alignment = PP_ALIGN.CENTER
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    return shape
```

### 화살표 추가
```python
def add_arrow(self, slide, x1, y1, x2, y2, color=None, width=2):
    """연결선/화살표 추가"""
    connector = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,
        Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    connector.line.color.rgb = color or self.theme['arrow']
    connector.line.width = Pt(width)
    return connector
```

## 슬라이드 구조

### 기본 구조
```
┌─────────────────────────────────────────────────────────┐
│ [슬라이드 제목 (왼쪽)]           [섹션 제목 (오른쪽)]      │ ← 헤더 (0.8")
├─────────────────────────────────────────────────────────┤
│ 소제목                                                   │ ← 소제목 (0.4")
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────────┐  ┌──────────────────┐     │
│  │   도식화 / 테이블         │  │ 설명 패널        │     │
│  │   (8~9")                 │  │ (3~4")          │     │
│  │                         │  │ 1. xxx          │     │
│  │                         │  │ 2. xxx          │     │
│  │                         │  │ 3. xxx          │     │
│  └─────────────────────────┘  └──────────────────┘     │
│                                                         │
├─────────────────────────────────────────────────────────┤
│ 효과/요약 (하단)                                         │
└─────────────────────────────────────────────────────────┘
```

## 폰트 설정

```python
FONT = {
    'title': 24,      # 헤더 제목
    'section': 14,    # 섹션 제목
    'subtitle': 14,   # 소제목
    'body': 11,       # 본문
    'table': 10,      # 테이블
    'small': 9,       # 작은 텍스트
    'diagram': 10,    # 도식화 텍스트
}
FONT_NAME = "맑은 고딕"
```

## 아키텍처 도식화 예시

### MSA 전환 아키텍처
- 좌측: AS-IS (모놀리식)
- 중앙: 화살표 (전환)
- 우측: TO-BE (MSA 구조)
  - API Gateway
  - Service Mesh (Istio)
  - Microservices (회계/예산/급여/인사)
  - Event Bus (Kafka)
  - Database per Service
  - Observability Stack
- 우측 패널: 설명 4개 항목

### DR 센터 구성
- 좌우 비교 레이아웃
- 평상시 (Normal) vs 재해시 (Disaster)
- Active-Standby 전환 표현
- 동기화 화살표 + 상태 변화

## 참고 코드

skill 디렉토리의 `template.py`에 전체 클래스 구조가 포함되어 있습니다.

## 출력 파일

- 위치: 원본 파일과 동일한 디렉토리 또는 `output/`
- 파일명: `<제목>_<테마명>.pptx`

## 사전 요구사항

```bash
pip install python-pptx
```

## 문제 해결

### 한글 깨짐
- Windows: "맑은 고딕" 폰트 확인
- 다른 환경: `FONT_NAME` 변수를 "Noto Sans KR" 등으로 변경

### 슬라이드 크기
```python
prs.slide_width = Inches(13.333)   # 16:9 와이드스크린
prs.slide_height = Inches(7.5)
```
