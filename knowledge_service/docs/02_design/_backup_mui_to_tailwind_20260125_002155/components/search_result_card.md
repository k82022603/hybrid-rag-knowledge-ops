# Search Result Card - UI Component Design

## Document Information

| Item | Content |
|------|---------|
| **Document Name** | Search Result Card Component Design |
| **Version** | 1.0 |
| **Created** | 2026-01-24 |
| **Author** | WebDesigner Agent |
| **Status** | Draft |
| **Related Docs** | [UI Design System Guide](../ui_design_system_guide.md), [Frontend Design](../frontend_detailed_design.md), [Search Storyboard](../ui_storyboard/02_search.md) |

---

## Verbalized Sampling Analysis

### Stage 1: Requirements Analysis

**Core Requirements**:
- RAG 검색 결과를 표시하는 카드 컴포넌트
- 표시 정보: 문서 제목, 요약/스니펫, 관련도 점수, 출처, 문서 타입 아이콘, 날짜
- React 18 + TypeScript 기반
- 반응형 디자인 (Desktop, Tablet, Mobile)
- 다크모드 지원

**Key Keywords**: RAG, relevance score, snippet highlight, source attribution, document type

### Stage 2: Cliche Identification (Anti-Pattern List)

| Cliche | Problem | Prevalence |
|--------|---------|------------|
| **Bootstrap Card with Blue Header** | 차별화 실패, 지루함 | 매우 높음 |
| **무조건 Box Shadow** | 모든 카드에 그림자 남발 | 높음 |
| **Star Rating 5개** | 검색 관련도와 맞지 않음 | 중간 |
| **Progress Bar로 점수 표시** | 공간 낭비, 시각적 혼란 | 중간 |
| **Thumbnail 강제 표시** | 문서 기반 서비스에 불필요 | 높음 |
| **Hover시 전체 카드 확대** | 과도한 인터랙션 | 중간 |
| **Badge 남발** | "NEW", "HOT" 등 의미 없는 라벨 | 높음 |
| **균일한 카드 높이** | 스니펫 길이 다양성 무시 | 중간 |

### Stage 3: Creative Alternatives

#### Alternative A: "Confidence Ring" Design
```
┌────────────────────────────────────────────────────────────┐
│  [○]  Document Title                              92%     │
│  │    ├─ ring animation shows confidence                  │
│  ↓                                                        │
│  Snippet text with **highlighted keywords**...            │
│                                                           │
│  📁 Source  │  📅 Date  │  PDF                           │
└────────────────────────────────────────────────────────────┘
- 관련도를 원형 프로그레스로 표시
- 미니멀하지만 정보 밀도 높음
```

#### Alternative B: "Source First" Design
```
┌────────────────────────────────────────────────────────────┐
│  📄 PDF │ frontend-guide.pdf                              │
│  ──────────────────────────────────────────────────────── │
│  React Component Design Patterns                   [92%]  │
│                                                           │
│  "컴포넌트 설계 시 **단일 책임 원칙**을 적용하면..."       │
│                                                           │
│  작성자 김개발 • 2026-01-10 • 조회 234                    │
└────────────────────────────────────────────────────────────┘
- 출처를 최상단에 배치하여 신뢰도 강조
- 기업 내부 문서 검색에 적합
```

#### Alternative C: "Contextual Relevance" Design (SELECTED)
```
┌────────────────────────────────────────────────────────────┐
│  ┌──┐                                                     │
│  │▣ │  React Component Design Patterns                    │
│  └──┘                                                     │
│  ──────────────────────────────────────────────────────── │
│  │  컴포넌트 설계 시 **단일 책임 원칙**을 적용하면        │
│  │  재사용성이 높아집니다. Container와 Presentational...   │
│  ───────────────────────────────────────────────────────  │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ 📁 프론트엔드   │  📅 2026-01-10  │  👤 김개발     │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                           │
│  [  92% 관련도  ]  ━━━━━━━━━━━━━━━━━━░░░░                 │
│                                     ▲ subtle indicator    │
│                         ☆ 북마크     🔗 공유              │
└────────────────────────────────────────────────────────────┘
```

### Stage 4: Final Selection

**Selected Design**: Alternative C - "Contextual Relevance"

**Selection Rationale**:
1. 문서 타입 아이콘이 시각적 앵커 역할 (빠른 스캔)
2. 관련도 점수가 하단에 위치하여 "검증 완료" 느낌 부여
3. 메타데이터가 명확히 구분된 영역에 배치
4. 스니펫 영역의 좌측 border로 "인용" 맥락 강조
5. 액션 버튼이 우측 하단에 자연스럽게 배치

---

## Component Specification

### 1. Visual Design

#### 1.1 Layout Structure

```
┌─────────────────────────────────────────────────────────────────┐
│ 16px padding                                                    │
│  ┌────────────────────────────────────────────────────────────┐│
│  │                                                            ││
│  │  ┌────┐                                                    ││
│  │  │Icon│  Document Title (H4 - 20px semi-bold)      [...]  ││
│  │  │ 48 │                                                    ││
│  │  └────┘                                                    ││
│  │         8px gap                                            ││
│  │                                                            ││
│  │  ┌─────────────────────────────────────────────────────┐  ││
│  │  │ 3px │ Snippet text (Body 2 - 14px regular)          │  ││
│  │  │ bdr │ Max 3 lines with ellipsis...                  │  ││
│  │  │     │ **Highlighted** keywords in bold              │  ││
│  │  └─────────────────────────────────────────────────────┘  ││
│  │                                                            ││
│  │  ┌─────────────────────────────────────────────────────┐  ││
│  │  │ 📁 Source  │  📅 Date  │  👤 Author  │  👁 Views   │  ││
│  │  └─────────────────────────────────────────────────────┘  ││
│  │                                                            ││
│  │  ┌───────────────────────────────┐  ┌──────────────────┐  ││
│  │  │ 92% Relevance  ━━━━━━━━━░░░░░ │  │ ☆ Save  🔗 Share│  ││
│  │  └───────────────────────────────┘  └──────────────────┘  ││
│  │                                                            ││
│  └────────────────────────────────────────────────────────────┘│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 1.2 Dimensions

| Element | Desktop | Tablet | Mobile |
|---------|---------|--------|--------|
| Card Width | 100% (max 800px) | 100% | 100% |
| Card Padding | 20px | 16px | 12px |
| Icon Size | 48x48px | 40x40px | 36x36px |
| Title Font | 20px | 18px | 16px |
| Snippet Lines | 3 | 2 | 2 |
| Border Radius | 12px | 10px | 8px |

#### 1.3 Color Tokens

```typescript
// Light Mode
const searchCardLight = {
  background: '#FFFFFF',
  border: '#E8EEF3',
  borderHover: '#CBD5E1',

  // Title
  titleColor: '#1E293B',

  // Snippet
  snippetBg: '#F8FAFC',
  snippetBorder: '#3B82F6',  // Primary blue for quote indicator
  snippetText: '#475569',
  highlightBg: '#FEF3C7',     // Soft yellow for keyword highlight
  highlightText: '#92400E',

  // Metadata
  metadataText: '#64748B',
  metadataIconColor: '#94A3B8',

  // Relevance
  relevanceBarBg: '#E2E8F0',
  relevanceBarFill: '#10B981',  // Green for high relevance
  relevanceBarMedium: '#F59E0B', // Amber for medium
  relevanceBarLow: '#EF4444',   // Red for low

  // Actions
  actionIconDefault: '#94A3B8',
  actionIconHover: '#3B82F6',
  actionIconActive: '#1D4ED8',
};

// Dark Mode
const searchCardDark = {
  background: '#1E293B',
  border: '#334155',
  borderHover: '#475569',

  titleColor: '#F1F5F9',

  snippetBg: '#0F172A',
  snippetBorder: '#60A5FA',
  snippetText: '#CBD5E1',
  highlightBg: '#451A03',
  highlightText: '#FCD34D',

  metadataText: '#94A3B8',
  metadataIconColor: '#64748B',

  relevanceBarBg: '#334155',
  relevanceBarFill: '#34D399',
  relevanceBarMedium: '#FBBF24',
  relevanceBarLow: '#F87171',

  actionIconDefault: '#64748B',
  actionIconHover: '#60A5FA',
  actionIconActive: '#93C5FD',
};
```

---

### 2. Document Type Icons

| Type | Icon | Color (Light) | Color (Dark) |
|------|------|---------------|--------------|
| PDF | `PictureAsPdf` | #DC2626 | #F87171 |
| Word | `Description` | #2563EB | #60A5FA |
| Excel | `TableChart` | #059669 | #34D399 |
| PowerPoint | `Slideshow` | #EA580C | #FB923C |
| Markdown | `Code` | #7C3AED | #A78BFA |
| Confluence | `Article` | #0052CC | #4C9AFF |
| Notion | `StickyNote2` | #1F2937 | #E5E7EB |
| Default | `InsertDriveFile` | #6B7280 | #9CA3AF |

```typescript
const documentTypeConfig: Record<string, { icon: string; color: string }> = {
  'pdf': { icon: 'PictureAsPdf', color: '#DC2626' },
  'docx': { icon: 'Description', color: '#2563EB' },
  'doc': { icon: 'Description', color: '#2563EB' },
  'xlsx': { icon: 'TableChart', color: '#059669' },
  'xls': { icon: 'TableChart', color: '#059669' },
  'pptx': { icon: 'Slideshow', color: '#EA580C' },
  'ppt': { icon: 'Slideshow', color: '#EA580C' },
  'md': { icon: 'Code', color: '#7C3AED' },
  'confluence': { icon: 'Article', color: '#0052CC' },
  'notion': { icon: 'StickyNote2', color: '#1F2937' },
  'default': { icon: 'InsertDriveFile', color: '#6B7280' },
};
```

---

### 3. Relevance Score Display

#### 3.1 Score Thresholds

| Range | Label | Color | Description |
|-------|-------|-------|-------------|
| 90-100% | Excellent | Green (#10B981) | 매우 높은 관련도 |
| 70-89% | Good | Blue (#3B82F6) | 높은 관련도 |
| 50-69% | Fair | Amber (#F59E0B) | 보통 관련도 |
| 0-49% | Low | Gray (#6B7280) | 낮은 관련도 |

#### 3.2 Visual Indicator

```
High (90%+):    [92%] ━━━━━━━━━━━━━━━━━━━░░  (Green filled)
Good (70-89%):  [78%] ━━━━━━━━━━━━━━━░░░░░░  (Blue filled)
Fair (50-69%):  [55%] ━━━━━━━━━━░░░░░░░░░░░  (Amber filled)
Low (<50%):     [35%] ━━━━━━░░░░░░░░░░░░░░░  (Gray filled)
```

---

### 4. Interaction States

#### 4.1 Card States

| State | Visual Change |
|-------|---------------|
| **Default** | `border: 1px solid $border`, `background: $background` |
| **Hover** | `border-color: $borderHover`, `box-shadow: 0 4px 12px rgba(0,0,0,0.05)` |
| **Focus** | `outline: 2px solid $primary`, `outline-offset: 2px` |
| **Active** | `transform: scale(0.99)`, `box-shadow: none` |
| **Selected** | `border-color: $primary`, `background: $primaryLight/10` |

#### 4.2 Action Button States

```css
/* Bookmark Button */
.bookmark-btn {
  /* Default */
  color: var(--action-icon-default);

  /* Hover */
  &:hover {
    color: var(--action-icon-hover);
    background: var(--action-hover-bg);
  }

  /* Active (Bookmarked) */
  &.active {
    color: #F59E0B; /* Amber */
  }
}

/* Share Button */
.share-btn {
  /* Hover */
  &:hover {
    color: var(--primary);
    background: var(--primary-light-10);
  }
}
```

#### 4.3 Keyword Highlight Animation

```css
.keyword-highlight {
  background: var(--highlight-bg);
  color: var(--highlight-text);
  padding: 0 4px;
  border-radius: 2px;
  font-weight: 600;

  /* Subtle pulse on first render */
  animation: highlight-pulse 1s ease-out;
}

@keyframes highlight-pulse {
  0% { background: var(--highlight-bg); }
  50% { background: color-mix(in srgb, var(--highlight-bg), white 30%); }
  100% { background: var(--highlight-bg); }
}
```

---

### 5. Responsive Breakpoints

```typescript
const breakpoints = {
  mobile: '0px',      // 0 - 599px
  tablet: '600px',    // 600 - 899px
  desktop: '900px',   // 900px+
};

// Card layout changes
const responsiveStyles = {
  mobile: {
    flexDirection: 'column',
    iconPosition: 'inline',
    metadataLayout: 'stacked',
    actionsPosition: 'full-width',
  },
  tablet: {
    flexDirection: 'row',
    iconPosition: 'left',
    metadataLayout: 'inline',
    actionsPosition: 'right',
  },
  desktop: {
    flexDirection: 'row',
    iconPosition: 'left',
    metadataLayout: 'inline',
    actionsPosition: 'right',
  },
};
```

---

### 6. Accessibility (WCAG 2.1 AA)

#### 6.1 ARIA Attributes

```tsx
<article
  role="article"
  aria-label={`검색 결과: ${title}`}
  tabIndex={0}
>
  <header>
    <h3 id={`title-${id}`}>{title}</h3>
  </header>

  <blockquote aria-describedby={`title-${id}`}>
    {snippet}
  </blockquote>

  <footer>
    <dl aria-label="문서 정보">
      <dt className="sr-only">출처</dt>
      <dd>{source}</dd>
      <dt className="sr-only">작성일</dt>
      <dd><time dateTime={date}>{formattedDate}</time></dd>
    </dl>

    <div aria-label={`관련도 ${score}%`} role="meter"
         aria-valuenow={score} aria-valuemin={0} aria-valuemax={100}>
      <span className="sr-only">{score}% 관련도</span>
    </div>

    <div role="group" aria-label="액션">
      <button aria-label={isBookmarked ? '북마크 해제' : '북마크 추가'}>
        {/* Icon */}
      </button>
      <button aria-label="공유하기">
        {/* Icon */}
      </button>
    </div>
  </footer>
</article>
```

#### 6.2 Keyboard Navigation

| Key | Action |
|-----|--------|
| `Tab` | 다음 카드로 이동 |
| `Shift + Tab` | 이전 카드로 이동 |
| `Enter` / `Space` | 카드 상세 페이지로 이동 |
| `B` | 북마크 토글 (focused card) |
| `S` | 공유 메뉴 열기 (focused card) |

#### 6.3 Color Contrast

| Element | Foreground | Background | Ratio | Status |
|---------|------------|------------|-------|--------|
| Title | #1E293B | #FFFFFF | 12.6:1 | Pass |
| Snippet | #475569 | #F8FAFC | 7.1:1 | Pass |
| Metadata | #64748B | #FFFFFF | 4.9:1 | Pass |
| Highlight | #92400E | #FEF3C7 | 5.3:1 | Pass |

---

## TypeScript Interface

```typescript
// types/search.types.ts

/**
 * 문서 타입 enum
 */
export type DocumentType =
  | 'pdf'
  | 'docx'
  | 'doc'
  | 'xlsx'
  | 'xls'
  | 'pptx'
  | 'ppt'
  | 'md'
  | 'confluence'
  | 'notion'
  | 'default';

/**
 * 검색 결과 아이템 인터페이스
 */
export interface SearchResultItem {
  /** 고유 ID */
  id: string;

  /** 문서 제목 */
  title: string;

  /** 검색어가 포함된 텍스트 스니펫 */
  snippet: string;

  /** 하이라이트할 키워드 배열 */
  highlightKeywords: string[];

  /** 관련도 점수 (0-100) */
  relevanceScore: number;

  /** 문서 출처 (카테고리 또는 시스템) */
  source: string;

  /** 문서 타입 */
  documentType: DocumentType;

  /** 작성/수정일 (ISO 8601) */
  date: string;

  /** 작성자 이름 */
  author?: string;

  /** 조회수 */
  viewCount?: number;

  /** 북마크 여부 */
  isBookmarked?: boolean;

  /** 문서 URL */
  url: string;

  /** 원본 파일명 */
  fileName?: string;
}

/**
 * SearchResultCard Props
 */
export interface SearchResultCardProps {
  /** 검색 결과 데이터 */
  result: SearchResultItem;

  /** 카드 클릭 핸들러 */
  onClick?: (result: SearchResultItem) => void;

  /** 북마크 토글 핸들러 */
  onBookmarkToggle?: (id: string, isBookmarked: boolean) => void;

  /** 공유 버튼 핸들러 */
  onShare?: (result: SearchResultItem) => void;

  /** 선택된 상태 여부 */
  isSelected?: boolean;

  /** 로딩 상태 (Skeleton 표시) */
  isLoading?: boolean;

  /** 커스텀 className */
  className?: string;
}
```

---

## React Component Code

```tsx
// components/search/SearchResultCard/SearchResultCard.tsx

import React, { memo, useMemo, useCallback } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  IconButton,
  Tooltip,
  Skeleton,
  useTheme,
  alpha,
} from '@mui/material';
import {
  BookmarkBorder as BookmarkOutlinedIcon,
  Bookmark as BookmarkFilledIcon,
  Share as ShareIcon,
  MoreHoriz as MoreIcon,
  PictureAsPdf,
  Description,
  TableChart,
  Slideshow,
  Code,
  Article,
  StickyNote2,
  InsertDriveFile,
} from '@mui/icons-material';
import { format, parseISO } from 'date-fns';
import { ko } from 'date-fns/locale';

import type { SearchResultCardProps, DocumentType } from '@/types/search.types';

// Document type icon mapping
const documentTypeIcons: Record<DocumentType, React.ElementType> = {
  pdf: PictureAsPdf,
  docx: Description,
  doc: Description,
  xlsx: TableChart,
  xls: TableChart,
  pptx: Slideshow,
  ppt: Slideshow,
  md: Code,
  confluence: Article,
  notion: StickyNote2,
  default: InsertDriveFile,
};

const documentTypeColors: Record<DocumentType, string> = {
  pdf: '#DC2626',
  docx: '#2563EB',
  doc: '#2563EB',
  xlsx: '#059669',
  xls: '#059669',
  pptx: '#EA580C',
  ppt: '#EA580C',
  md: '#7C3AED',
  confluence: '#0052CC',
  notion: '#1F2937',
  default: '#6B7280',
};

// Relevance score color utility
const getRelevanceColor = (score: number, isDark: boolean): string => {
  if (score >= 90) return isDark ? '#34D399' : '#10B981';
  if (score >= 70) return isDark ? '#60A5FA' : '#3B82F6';
  if (score >= 50) return isDark ? '#FBBF24' : '#F59E0B';
  return isDark ? '#9CA3AF' : '#6B7280';
};

// Highlight keywords in snippet
const highlightSnippet = (
  text: string,
  keywords: string[],
  theme: 'light' | 'dark'
): React.ReactNode => {
  if (!keywords.length) return text;

  const highlightBg = theme === 'dark' ? '#451A03' : '#FEF3C7';
  const highlightColor = theme === 'dark' ? '#FCD34D' : '#92400E';

  const regex = new RegExp(`(${keywords.join('|')})`, 'gi');
  const parts = text.split(regex);

  return parts.map((part, index) => {
    const isHighlight = keywords.some(
      (kw) => kw.toLowerCase() === part.toLowerCase()
    );

    if (isHighlight) {
      return (
        <Box
          key={index}
          component="mark"
          sx={{
            backgroundColor: highlightBg,
            color: highlightColor,
            px: 0.5,
            borderRadius: 0.25,
            fontWeight: 600,
          }}
        >
          {part}
        </Box>
      );
    }
    return part;
  });
};

/**
 * SearchResultCard Component
 *
 * RAG 검색 결과를 표시하는 카드 컴포넌트
 * Verbalized Sampling 기법을 적용한 "Contextual Relevance" 디자인
 */
export const SearchResultCard = memo<SearchResultCardProps>(
  ({
    result,
    onClick,
    onBookmarkToggle,
    onShare,
    isSelected = false,
    isLoading = false,
    className,
  }) => {
    const theme = useTheme();
    const isDark = theme.palette.mode === 'dark';

    // Memoized values
    const IconComponent = useMemo(
      () => documentTypeIcons[result.documentType] || documentTypeIcons.default,
      [result.documentType]
    );

    const iconColor = useMemo(
      () => documentTypeColors[result.documentType] || documentTypeColors.default,
      [result.documentType]
    );

    const relevanceColor = useMemo(
      () => getRelevanceColor(result.relevanceScore, isDark),
      [result.relevanceScore, isDark]
    );

    const formattedDate = useMemo(() => {
      try {
        return format(parseISO(result.date), 'yyyy-MM-dd', { locale: ko });
      } catch {
        return result.date;
      }
    }, [result.date]);

    const highlightedSnippet = useMemo(
      () =>
        highlightSnippet(
          result.snippet,
          result.highlightKeywords,
          isDark ? 'dark' : 'light'
        ),
      [result.snippet, result.highlightKeywords, isDark]
    );

    // Handlers
    const handleCardClick = useCallback(() => {
      onClick?.(result);
    }, [onClick, result]);

    const handleBookmarkClick = useCallback(
      (e: React.MouseEvent) => {
        e.stopPropagation();
        onBookmarkToggle?.(result.id, !result.isBookmarked);
      },
      [onBookmarkToggle, result.id, result.isBookmarked]
    );

    const handleShareClick = useCallback(
      (e: React.MouseEvent) => {
        e.stopPropagation();
        onShare?.(result);
      },
      [onShare, result]
    );

    const handleKeyDown = useCallback(
      (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick?.(result);
        }
        if (e.key === 'b' || e.key === 'B') {
          onBookmarkToggle?.(result.id, !result.isBookmarked);
        }
        if (e.key === 's' || e.key === 'S') {
          onShare?.(result);
        }
      },
      [onClick, onBookmarkToggle, onShare, result]
    );

    // Loading skeleton
    if (isLoading) {
      return (
        <Card
          className={className}
          sx={{
            p: { xs: 1.5, sm: 2, md: 2.5 },
            borderRadius: { xs: 1, sm: 1.25, md: 1.5 },
          }}
        >
          <CardContent>
            <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start' }}>
              <Skeleton variant="rounded" width={48} height={48} />
              <Box sx={{ flex: 1 }}>
                <Skeleton variant="text" width="60%" height={28} />
                <Skeleton variant="text" width="100%" />
                <Skeleton variant="text" width="80%" />
                <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
                  <Skeleton variant="text" width={80} />
                  <Skeleton variant="text" width={80} />
                  <Skeleton variant="text" width={80} />
                </Box>
              </Box>
            </Box>
          </CardContent>
        </Card>
      );
    }

    return (
      <Card
        component="article"
        role="article"
        aria-label={`검색 결과: ${result.title}`}
        tabIndex={0}
        onClick={handleCardClick}
        onKeyDown={handleKeyDown}
        className={className}
        sx={{
          cursor: 'pointer',
          transition: 'all 0.2s ease-in-out',
          border: 1,
          borderColor: isSelected
            ? 'primary.main'
            : isDark
            ? 'grey.800'
            : 'grey.200',
          backgroundColor: isSelected
            ? alpha(theme.palette.primary.main, 0.05)
            : 'background.paper',

          '&:hover': {
            borderColor: isDark ? 'grey.700' : 'grey.400',
            boxShadow: isDark
              ? '0 4px 12px rgba(0,0,0,0.3)'
              : '0 4px 12px rgba(0,0,0,0.05)',
          },

          '&:focus': {
            outline: `2px solid ${theme.palette.primary.main}`,
            outlineOffset: 2,
          },

          '&:active': {
            transform: 'scale(0.995)',
            boxShadow: 'none',
          },

          borderRadius: { xs: 1, sm: 1.25, md: 1.5 },
        }}
      >
        <CardContent
          sx={{
            p: { xs: 1.5, sm: 2, md: 2.5 },
            '&:last-child': { pb: { xs: 1.5, sm: 2, md: 2.5 } },
          }}
        >
          {/* Header: Icon + Title */}
          <Box
            sx={{
              display: 'flex',
              gap: { xs: 1.5, sm: 2 },
              alignItems: 'flex-start',
              mb: 1.5,
            }}
          >
            {/* Document Type Icon */}
            <Box
              sx={{
                width: { xs: 36, sm: 40, md: 48 },
                height: { xs: 36, sm: 40, md: 48 },
                borderRadius: 1,
                backgroundColor: alpha(iconColor, 0.1),
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}
            >
              <IconComponent
                sx={{
                  fontSize: { xs: 20, sm: 24, md: 28 },
                  color: iconColor,
                }}
              />
            </Box>

            {/* Title */}
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Typography
                variant="h4"
                component="h3"
                id={`title-${result.id}`}
                sx={{
                  fontSize: { xs: '1rem', sm: '1.125rem', md: '1.25rem' },
                  fontWeight: 600,
                  color: 'text.primary',
                  lineHeight: 1.3,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  display: '-webkit-box',
                  WebkitLineClamp: 2,
                  WebkitBoxOrient: 'vertical',
                }}
              >
                {result.title}
              </Typography>

              {result.fileName && (
                <Typography
                  variant="caption"
                  sx={{
                    color: 'text.secondary',
                    display: 'block',
                    mt: 0.25,
                  }}
                >
                  {result.fileName}
                </Typography>
              )}
            </Box>

            {/* More Options */}
            <IconButton
              size="small"
              aria-label="더보기"
              onClick={(e) => e.stopPropagation()}
              sx={{ flexShrink: 0 }}
            >
              <MoreIcon fontSize="small" />
            </IconButton>
          </Box>

          {/* Snippet with Quote Style */}
          <Box
            component="blockquote"
            aria-describedby={`title-${result.id}`}
            sx={{
              m: 0,
              p: 1.5,
              pl: 2,
              borderLeft: 3,
              borderColor: 'primary.main',
              backgroundColor: isDark ? 'grey.900' : 'grey.50',
              borderRadius: '0 4px 4px 0',
              mb: 2,
            }}
          >
            <Typography
              variant="body2"
              sx={{
                color: 'text.secondary',
                lineHeight: 1.6,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                display: '-webkit-box',
                WebkitLineClamp: { xs: 2, md: 3 },
                WebkitBoxOrient: 'vertical',
              }}
            >
              {highlightedSnippet}
            </Typography>
          </Box>

          {/* Metadata Row */}
          <Box
            component="dl"
            aria-label="문서 정보"
            sx={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: { xs: 1, sm: 2 },
              mb: 2,
              m: 0,
            }}
          >
            {/* Source */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <Typography
                component="dt"
                sx={{
                  position: 'absolute',
                  width: 1,
                  height: 1,
                  padding: 0,
                  margin: -1,
                  overflow: 'hidden',
                  clip: 'rect(0, 0, 0, 0)',
                  whiteSpace: 'nowrap',
                  border: 0,
                }}
              >
                출처
              </Typography>
              <Typography
                component="dd"
                variant="caption"
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 0.5,
                  color: 'text.secondary',
                  m: 0,
                }}
              >
                <Box component="span" sx={{ opacity: 0.7 }}>
                  📁
                </Box>
                {result.source}
              </Typography>
            </Box>

            {/* Date */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <Typography
                component="dt"
                sx={{
                  position: 'absolute',
                  width: 1,
                  height: 1,
                  padding: 0,
                  margin: -1,
                  overflow: 'hidden',
                  clip: 'rect(0, 0, 0, 0)',
                  whiteSpace: 'nowrap',
                  border: 0,
                }}
              >
                작성일
              </Typography>
              <Typography
                component="dd"
                variant="caption"
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 0.5,
                  color: 'text.secondary',
                  m: 0,
                }}
              >
                <Box component="span" sx={{ opacity: 0.7 }}>
                  📅
                </Box>
                <time dateTime={result.date}>{formattedDate}</time>
              </Typography>
            </Box>

            {/* Author */}
            {result.author && (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                <Typography
                  component="dt"
                  sx={{
                    position: 'absolute',
                    width: 1,
                    height: 1,
                    padding: 0,
                    margin: -1,
                    overflow: 'hidden',
                    clip: 'rect(0, 0, 0, 0)',
                    whiteSpace: 'nowrap',
                    border: 0,
                  }}
                >
                  작성자
                </Typography>
                <Typography
                  component="dd"
                  variant="caption"
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 0.5,
                    color: 'text.secondary',
                    m: 0,
                  }}
                >
                  <Box component="span" sx={{ opacity: 0.7 }}>
                    👤
                  </Box>
                  {result.author}
                </Typography>
              </Box>
            )}

            {/* View Count */}
            {result.viewCount !== undefined && (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                <Typography
                  component="dt"
                  sx={{
                    position: 'absolute',
                    width: 1,
                    height: 1,
                    padding: 0,
                    margin: -1,
                    overflow: 'hidden',
                    clip: 'rect(0, 0, 0, 0)',
                    whiteSpace: 'nowrap',
                    border: 0,
                  }}
                >
                  조회수
                </Typography>
                <Typography
                  component="dd"
                  variant="caption"
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 0.5,
                    color: 'text.secondary',
                    m: 0,
                  }}
                >
                  <Box component="span" sx={{ opacity: 0.7 }}>
                    👁
                  </Box>
                  {result.viewCount.toLocaleString()}
                </Typography>
              </Box>
            )}
          </Box>

          {/* Footer: Relevance + Actions */}
          <Box
            sx={{
              display: 'flex',
              flexDirection: { xs: 'column', sm: 'row' },
              gap: { xs: 1.5, sm: 2 },
              alignItems: { xs: 'stretch', sm: 'center' },
              justifyContent: 'space-between',
            }}
          >
            {/* Relevance Score */}
            <Box
              role="meter"
              aria-label={`관련도 ${result.relevanceScore}%`}
              aria-valuenow={result.relevanceScore}
              aria-valuemin={0}
              aria-valuemax={100}
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 1,
                flex: { xs: 1, sm: 'none' },
              }}
            >
              <Typography
                variant="caption"
                sx={{
                  fontWeight: 600,
                  color: relevanceColor,
                  minWidth: 45,
                }}
              >
                {result.relevanceScore}%
              </Typography>

              <Box
                sx={{
                  flex: 1,
                  maxWidth: 150,
                  height: 6,
                  backgroundColor: isDark ? 'grey.800' : 'grey.200',
                  borderRadius: 3,
                  overflow: 'hidden',
                }}
              >
                <Box
                  sx={{
                    width: `${result.relevanceScore}%`,
                    height: '100%',
                    backgroundColor: relevanceColor,
                    borderRadius: 3,
                    transition: 'width 0.3s ease-out',
                  }}
                />
              </Box>

              <Typography
                variant="caption"
                sx={{ color: 'text.secondary' }}
              >
                관련도
              </Typography>
            </Box>

            {/* Action Buttons */}
            <Box
              role="group"
              aria-label="액션"
              sx={{
                display: 'flex',
                gap: 0.5,
                justifyContent: { xs: 'flex-end', sm: 'flex-start' },
              }}
            >
              <Tooltip
                title={result.isBookmarked ? '북마크 해제' : '북마크 추가'}
              >
                <IconButton
                  size="small"
                  onClick={handleBookmarkClick}
                  aria-label={
                    result.isBookmarked ? '북마크 해제' : '북마크 추가'
                  }
                  sx={{
                    color: result.isBookmarked ? '#F59E0B' : 'text.secondary',
                    '&:hover': {
                      color: result.isBookmarked
                        ? '#D97706'
                        : 'primary.main',
                      backgroundColor: alpha(
                        theme.palette.primary.main,
                        0.1
                      ),
                    },
                  }}
                >
                  {result.isBookmarked ? (
                    <BookmarkFilledIcon fontSize="small" />
                  ) : (
                    <BookmarkOutlinedIcon fontSize="small" />
                  )}
                </IconButton>
              </Tooltip>

              <Tooltip title="공유하기">
                <IconButton
                  size="small"
                  onClick={handleShareClick}
                  aria-label="공유하기"
                  sx={{
                    color: 'text.secondary',
                    '&:hover': {
                      color: 'primary.main',
                      backgroundColor: alpha(
                        theme.palette.primary.main,
                        0.1
                      ),
                    },
                  }}
                >
                  <ShareIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </Box>
          </Box>
        </CardContent>
      </Card>
    );
  }
);

SearchResultCard.displayName = 'SearchResultCard';

export default SearchResultCard;
```

---

## Storybook Stories

```tsx
// components/search/SearchResultCard/SearchResultCard.stories.tsx

import type { Meta, StoryObj } from '@storybook/react';
import { action } from '@storybook/addon-actions';
import { SearchResultCard } from './SearchResultCard';

const meta: Meta<typeof SearchResultCard> = {
  title: 'Components/Search/SearchResultCard',
  component: SearchResultCard,
  parameters: {
    layout: 'padded',
    docs: {
      description: {
        component: 'RAG 검색 결과를 표시하는 카드 컴포넌트. Verbalized Sampling 기법을 적용한 "Contextual Relevance" 디자인.',
      },
    },
  },
  tags: ['autodocs'],
  argTypes: {
    result: {
      description: '검색 결과 데이터',
    },
    isSelected: {
      control: 'boolean',
      description: '선택된 상태 여부',
    },
    isLoading: {
      control: 'boolean',
      description: '로딩 상태 (Skeleton 표시)',
    },
  },
};

export default meta;
type Story = StoryObj<typeof SearchResultCard>;

// Default story
export const Default: Story = {
  args: {
    result: {
      id: '1',
      title: 'React 컴포넌트 설계 패턴 가이드',
      snippet: '컴포넌트 설계 시 단일 책임 원칙을 적용하면 재사용성이 높아집니다. Container와 Presentational 패턴을 활용하여 비즈니스 로직과 UI를 분리하세요.',
      highlightKeywords: ['컴포넌트', '설계', '단일 책임 원칙'],
      relevanceScore: 92,
      source: '프론트엔드',
      documentType: 'md',
      date: '2026-01-15',
      author: '김개발',
      viewCount: 234,
      isBookmarked: false,
      url: '/knowledge/1',
      fileName: 'react-component-patterns.md',
    },
    onClick: action('onClick'),
    onBookmarkToggle: action('onBookmarkToggle'),
    onShare: action('onShare'),
  },
};

// High relevance
export const HighRelevance: Story = {
  args: {
    ...Default.args,
    result: {
      ...Default.args!.result!,
      relevanceScore: 98,
    },
  },
};

// Medium relevance
export const MediumRelevance: Story = {
  args: {
    ...Default.args,
    result: {
      ...Default.args!.result!,
      relevanceScore: 65,
    },
  },
};

// Low relevance
export const LowRelevance: Story = {
  args: {
    ...Default.args,
    result: {
      ...Default.args!.result!,
      relevanceScore: 35,
    },
  },
};

// PDF document
export const PDFDocument: Story = {
  args: {
    ...Default.args,
    result: {
      ...Default.args!.result!,
      documentType: 'pdf',
      fileName: '시스템-아키텍처-설계서.pdf',
      title: '시스템 아키텍처 설계서 v2.0',
    },
  },
};

// Excel document
export const ExcelDocument: Story = {
  args: {
    ...Default.args,
    result: {
      ...Default.args!.result!,
      documentType: 'xlsx',
      fileName: '2026년-예산-계획.xlsx',
      title: '2026년 예산 계획서',
    },
  },
};

// Bookmarked
export const Bookmarked: Story = {
  args: {
    ...Default.args,
    result: {
      ...Default.args!.result!,
      isBookmarked: true,
    },
  },
};

// Selected state
export const Selected: Story = {
  args: {
    ...Default.args,
    isSelected: true,
  },
};

// Loading state
export const Loading: Story = {
  args: {
    ...Default.args,
    isLoading: true,
  },
};

// Long title
export const LongTitle: Story = {
  args: {
    ...Default.args,
    result: {
      ...Default.args!.result!,
      title: 'React 애플리케이션에서 상태 관리를 효과적으로 수행하기 위한 Redux Toolkit과 React Query를 활용한 패턴 가이드 및 Best Practices',
    },
  },
};

// Long snippet
export const LongSnippet: Story = {
  args: {
    ...Default.args,
    result: {
      ...Default.args!.result!,
      snippet: '컴포넌트 설계 시 단일 책임 원칙을 적용하면 재사용성이 높아집니다. Container와 Presentational 패턴을 활용하여 비즈니스 로직과 UI를 분리하세요. 이 패턴은 테스트 작성을 쉽게 만들고, 컴포넌트의 역할을 명확하게 정의합니다. 또한 성능 최적화를 위해 React.memo와 useMemo를 적절히 활용하는 것이 중요합니다.',
    },
  },
};
```

---

## Usage Example

```tsx
// pages/SearchPage.tsx

import { useState } from 'react';
import { Box, Stack, Typography } from '@mui/material';
import { SearchResultCard } from '@/components/search/SearchResultCard';
import type { SearchResultItem } from '@/types/search.types';

export const SearchPage = () => {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const searchResults: SearchResultItem[] = [
    {
      id: '1',
      title: 'React 컴포넌트 설계 패턴 가이드',
      snippet: '컴포넌트 설계 시 단일 책임 원칙을 적용하면...',
      highlightKeywords: ['컴포넌트', '설계'],
      relevanceScore: 92,
      source: '프론트엔드',
      documentType: 'md',
      date: '2026-01-15',
      author: '김개발',
      viewCount: 234,
      isBookmarked: false,
      url: '/knowledge/1',
    },
    // ... more results
  ];

  const handleCardClick = (result: SearchResultItem) => {
    setSelectedId(result.id);
    // Navigate to detail page
  };

  const handleBookmarkToggle = (id: string, isBookmarked: boolean) => {
    // Update bookmark state
    console.log(`Bookmark ${id}: ${isBookmarked}`);
  };

  const handleShare = (result: SearchResultItem) => {
    // Open share dialog
    navigator.clipboard.writeText(window.location.origin + result.url);
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" gutterBottom>
        "React" 검색 결과 ({searchResults.length}건)
      </Typography>

      <Stack spacing={2}>
        {searchResults.map((result) => (
          <SearchResultCard
            key={result.id}
            result={result}
            isSelected={selectedId === result.id}
            onClick={handleCardClick}
            onBookmarkToggle={handleBookmarkToggle}
            onShare={handleShare}
          />
        ))}
      </Stack>
    </Box>
  );
};
```

---

## Testing Checklist

- [ ] Light/Dark 모드 전환 테스트
- [ ] 반응형 레이아웃 테스트 (Mobile, Tablet, Desktop)
- [ ] 키보드 네비게이션 테스트
- [ ] 스크린 리더 테스트 (VoiceOver, NVDA)
- [ ] 색상 대비비 검증 (axe-core)
- [ ] 클릭/호버/포커스 상태 테스트
- [ ] 긴 텍스트 truncation 테스트
- [ ] Loading skeleton 테스트
- [ ] 북마크 토글 테스트
- [ ] 공유 기능 테스트

---

## Handoff Notes for Frontend

1. **컴포넌트 위치**: `src/components/search/SearchResultCard/`
2. **필수 의존성**: `@mui/material`, `@mui/icons-material`, `date-fns`
3. **Type Definition**: `src/types/search.types.ts`
4. **Storybook**: 모든 상태별 스토리 작성 완료
5. **테마 통합**: MUI 테마 시스템 사용 (color tokens)
6. **성능 고려**: `React.memo`, `useMemo`, `useCallback` 적용

---

*WebDesigner Agent - Verbalized Sampling Applied*
