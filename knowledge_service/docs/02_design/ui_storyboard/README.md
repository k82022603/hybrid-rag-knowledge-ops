# UI 스토리보드
## 사내 지식 검색 시스템 UI/UX Design

**버전**: 1.0
**작성일**: 2026-01-15

---

## 개요

이 폴더는 사내 지식 검색 시스템의 UI 스토리보드를 포함합니다.

## 파일 목록

| 파일 | 설명 |
|------|------|
| `01_login_dashboard.md` | 로그인, 대시보드 화면 |
| `02_search.md` | 검색 화면 (채팅/검색 모드) |
| `03_knowledge_management.md` | 지식 관리 화면 (목록/상세/작성/수정) |
| `04_profile_admin.md` | 프로필, 설정, 관리자 화면 |
| `presentation.md` | **Marp 프레젠테이션 (PPT 변환 가능)** |

---

## PPT 변환 방법

### 방법 1: Marp CLI (권장)

```bash
# Marp CLI 설치 (Node.js 필요)
npm install -g @marp-team/marp-cli

# PPTX로 변환
marp presentation.md --pptx -o presentation.pptx

# PDF로 변환
marp presentation.md --pdf -o presentation.pdf

# HTML로 변환
marp presentation.md -o presentation.html
```

### 방법 2: 온라인 도구

1. [Marp Web](https://web.marp.app/) 접속
2. `presentation.md` 내용 복사하여 붙여넣기
3. 우측 상단 메뉴 → Export → PPTX/PDF 다운로드

### 방법 3: npx로 바로 실행 (설치 없이)

```bash
# 설치 없이 바로 PPTX 변환
npx @marp-team/marp-cli presentation.md --pptx -o presentation.pptx
```

---

## 화면 목록

### 1. 인증 및 대시보드
- 로그인 페이지
- 메인 대시보드

### 2. 검색
- 채팅 모드 (RAG 기반)
- 검색 모드 (키워드 검색)

### 3. 지식 관리
- 지식 목록
- 지식 상세
- 지식 작성/수정

### 4. 개인화 및 관리
- 프로필
- 북마크
- 관리자 페이지

---

## 디자인 원칙

1. **직관적인 네비게이션**: 3클릭 내 모든 기능 접근
2. **일관된 디자인 언어**: Material Design 기반
3. **반응형 레이아웃**: Desktop, Tablet, Mobile 지원
4. **접근성 고려**: WCAG 2.1 AA 수준
