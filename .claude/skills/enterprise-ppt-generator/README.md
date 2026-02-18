# Enterprise PPT Generator

대기업 제안서, 예외 신청서, 기술 보고서 등 전문적인 비즈니스 프레젠테이션을 생성하는 Claude Code Skill입니다.

## 사용 방법

### 방법 1: 슬래시 명령어로 직접 호출

```
/enterprise-ppt-generator <원본파일 또는 주제> [--theme <1|2|3>]
```

**예시:**
```
/enterprise-ppt-generator 01.문서작업/proposal.md --theme 1
/enterprise-ppt-generator "클라우드 전환 제안서" --theme 2
/enterprise-ppt-generator large_enterprise_technical_necessity.md
```

### 방법 2: 자연어로 요청

Claude에게 자연스럽게 요청하면 자동으로 skill이 적용됩니다.

**예시:**
```
"enterprise-ppt-generator skill 사용해서 제안서 PPT 만들어줘"
"이 마크다운 문서를 PPT로 변환해줘 (Golden Hour 테마로)"
"대기업 참여제한 예외신청서 프레젠테이션 생성해줘"
```

### 방법 3: template.py 직접 실행

Python 스크립트를 직접 실행할 수도 있습니다.

```bash
# skill 디렉토리로 이동
cd .claude/skills/enterprise-ppt-generator

# 테마 선택하여 실행
python3 template.py 1 output.pptx   # Ocean Depths
python3 template.py 2 output.pptx   # Golden Hour
python3 template.py 3 output.pptx   # Tech Innovation
```

---

## 테마 선택

| 번호 | 테마명 | 색상 계열 | 권장 용도 |
|------|--------|----------|-----------|
| **1** | Ocean Depths | 블루 | 기업용, 금융, 컨설팅, 공식 발표 |
| **2** | Golden Hour | 앰버/브라운 | 호텔, F&B, 럭셔리, 따뜻한 분위기 |
| **3** | Tech Innovation | 그린 | 기술, 스타트업, IT, 개발 |

---

## 실제 사용 예시

### 예시 1: 마크다운 문서를 PPT로 변환

**사용자 요청:**
```
enterprise-ppt-generator skill 이용해서
01.문서작업/large_enterprise_technical_necessity.md 보고 자료 만들어줘
- Golden Hour 테마 사용해줘
- 아키텍처 도식화 상세하게 그려줘
```

**Claude 동작:**
1. 원본 마크다운 파일 분석
2. 슬라이드 구조 설계 (표지, 목차, 본문, 결론)
3. python-pptx 코드 생성
4. PPT 파일 생성 및 저장

### 예시 2: 주제만으로 PPT 생성

**사용자 요청:**
```
/enterprise-ppt-generator "MSA 전환 제안서" --theme 3
```

**Claude 동작:**
1. 주제 분석
2. 슬라이드 내용 구성
3. Tech Innovation 테마 적용
4. PPT 파일 생성

### 예시 3: 기존 PPT 스타일 참고

**사용자 요청:**
```
KERIS_PPT_Generator 스타일로 새로운 제안서 PPT 만들어줘
- Ocean Depths 테마
- 아키텍처 도식화 포함
- 비교표 슬라이드 추가
```

---

## 생성되는 슬라이드 구성

### 기본 구조

1. **표지** - 제목, 부제목, 날짜
2. **목차** - 섹션 목록
3. **본문 슬라이드**
   - 아키텍처 도식화
   - 비교표 (AS-IS vs TO-BE)
   - 역량 비교 (대기업 vs 중소기업)
4. **결론** - 요약 및 제언

### 슬라이드 레이아웃

```
┌─────────────────────────────────────────────────────────┐
│ [슬라이드 제목]                    [섹션 제목]           │ ← 헤더
├─────────────────────────────────────────────────────────┤
│ 소제목                                                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────────┐  ┌──────────────────┐     │
│  │   도식화 / 테이블         │  │ 설명 패널        │     │
│  │   (좌측 8~9")            │  │ (우측 3~4")      │     │
│  │                         │  │ 1. 설명 1        │     │
│  │                         │  │ 2. 설명 2        │     │
│  │                         │  │ 3. 설명 3        │     │
│  └─────────────────────────┘  └──────────────────┘     │
│                                                         │
├─────────────────────────────────────────────────────────┤
│ 효과/요약                                                │
└─────────────────────────────────────────────────────────┘
```

---

## 포함된 아키텍처 도식화

skill에서 생성 가능한 아키텍처 다이어그램:

| 다이어그램 | 설명 |
|-----------|------|
| MSA 전환 아키텍처 | AS-IS (모놀리식) → TO-BE (마이크로서비스) |
| Istio Multi-Primary 토폴로지 | 17개 사이트 독립 Control Plane |
| mTLS 인증서 관리 체계 | Root CA → Intermediate CA → Workload Certs |
| 클라우드 네이티브 아키텍처 | K8s + GitOps + Observability |
| N2SF Zero Trust 보안 | PEP/PDP + C/S/O 등급별 보안 |
| DR 센터 구성 | Active-Active / Active-Standby |
| DevSecOps CI/CD 파이프라인 | Code → Build → Scan → Deploy |
| RPA + AI 통합 아키텍처 | Brity RPA + FabriX 생성AI |

---

## 커스터마이징

### 테마 색상 변경

`template.py`의 `THEMES` 딕셔너리를 수정하여 색상을 변경할 수 있습니다:

```python
THEMES = {
    1: {
        'name': 'My Custom Theme',
        'primary': RGBColor(0, 102, 153),      # 원하는 색상으로 변경
        'secondary': RGBColor(0, 153, 204),
        'cover_title': RGBColor(255, 255, 255),
        # ...
    },
}
```

### 새로운 슬라이드 추가

`EnterprisePPTGenerator` 클래스에 새로운 메서드를 추가:

```python
def create_custom_slide(self, title, content):
    slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
    self.add_header(slide, title, "섹션명")
    # 커스텀 내용 추가
    return slide
```

---

## 사전 요구사항

```bash
pip install python-pptx
```

---

## 파일 구조

```
.claude/skills/enterprise-ppt-generator/
├── SKILL.md      # Skill 정의 및 상세 가이드
├── template.py   # Python 클래스 템플릿
└── README.md     # 사용 방법 안내 (이 파일)
```

---

## 출력 파일

- **위치**: 원본 파일과 동일한 디렉토리 또는 지정된 경로
- **형식**: `.pptx` (Microsoft PowerPoint)
- **크기**: 와이드스크린 16:9 (13.333" x 7.5")

---

## 문제 해결

### python-pptx 설치 오류

```bash
pip install --upgrade pip
pip install python-pptx
```

### 한글 깨짐

Windows 환경에서 "맑은 고딕" 폰트가 필요합니다. 다른 환경에서는 `FONT_NAME` 변수를 변경:

```python
FONT_NAME = "Noto Sans KR"  # 또는 시스템에 설치된 한글 폰트
```

### 테마 번호 오류

테마 번호는 1, 2, 3 중 하나를 선택해야 합니다.

---

## 관련 Skill

- `presentation-maker`: 일반적인 프레젠테이션 생성 (12종 테마)
- `mermaid-diagrams`: Mermaid 다이어그램 생성

---

## 버전 정보

- v1.0: 2026년 1월 30일
- KERIS PPT Generator 기반
- 3종 테마 지원
- 아키텍처 도식화 + 설명 패널 레이아웃
