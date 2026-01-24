# MUI to Tailwind CSS 마이그레이션 가이드

**버전**: 1.0
**작성일**: 2026-01-25
**작성자**: Claude (Opus 4.5)
**목적**: MUI 컴포넌트를 Tailwind CSS + Headless UI로 전환하기 위한 실무 가이드

---

## 1. 개요

### 1.1 마이그레이션 결정

| 항목 | 내용 |
|------|------|
| **결정일** | 2026-01-25 |
| **Before** | MUI v5/v6 (Material-UI) |
| **After** | Tailwind CSS 3.4+ + Headless UI + Heroicons |
| **전환 기간** | 4 Phase, 8-11주 예상 |

### 1.2 Tech Stack 변경

| 역할 | Before (MUI) | After (Tailwind) |
|------|-------------|------------------|
| **스타일링** | `@mui/material` sx prop | Tailwind utility classes |
| **컴포넌트** | MUI Components | Headless UI + Custom |
| **아이콘** | `@mui/icons-material` | Heroicons |
| **테마** | MUI ThemeProvider | `tailwind.config.js` |
| **CSS-in-JS** | Emotion | 없음 (순수 CSS) |

---

## 2. 컴포넌트 매핑 테이블

### 2.1 레이아웃 컴포넌트

| MUI | Tailwind/Headless UI | 변환 예시 |
|-----|---------------------|-----------|
| `<Box>` | `<div>` + classes | `<Box sx={{ p: 2 }}>` → `<div className="p-2">` |
| `<Container>` | `<div className="container mx-auto">` | 중앙 정렬 컨테이너 |
| `<Grid container>` | `<div className="grid grid-cols-12 gap-4">` | 12컬럼 그리드 |
| `<Grid item xs={6}>` | `<div className="col-span-6">` | 그리드 아이템 |
| `<Stack direction="row">` | `<div className="flex flex-row gap-2">` | Flexbox |
| `<Stack direction="column">` | `<div className="flex flex-col gap-2">` | Flexbox |
| `<Paper>` | `<div className="bg-white rounded-lg shadow-md p-4">` | 카드 스타일 |
| `<Divider>` | `<hr className="border-t border-gray-200 my-4">` | 구분선 |

### 2.2 입력 컴포넌트

| MUI | Tailwind/Headless UI | Headless UI 사용 |
|-----|---------------------|------------------|
| `<TextField>` | Headless UI `<Input>` | ✅ 권장 |
| `<Select>` | Headless UI `<Listbox>` | ✅ 필수 |
| `<Autocomplete>` | Headless UI `<Combobox>` | ✅ 필수 |
| `<Checkbox>` | Headless UI `<Checkbox>` | ✅ 권장 |
| `<Radio>` | Headless UI `<RadioGroup>` | ✅ 필수 |
| `<Switch>` | Headless UI `<Switch>` | ✅ 필수 |
| `<Button>` | `<button>` + Tailwind | 커스텀 |
| `<IconButton>` | `<button>` + Tailwind | 커스텀 |

### 2.3 데이터 표시 컴포넌트

| MUI | Tailwind/Headless UI | 비고 |
|-----|---------------------|------|
| `<Typography variant="h1">` | `<h1 className="text-4xl font-bold">` | HTML 시맨틱 |
| `<Typography variant="body1">` | `<p className="text-base">` | 본문 텍스트 |
| `<Chip>` | `<span className="badge">` | 커스텀 배지 |
| `<Avatar>` | `<img className="rounded-full">` | 커스텀 |
| `<List>` | `<ul className="divide-y">` | HTML 리스트 |
| `<ListItem>` | `<li className="py-3">` | 리스트 아이템 |
| `<Table>` | `<table className="min-w-full">` | HTML 테이블 |
| `<Tooltip>` | Custom + Floating UI | 커스텀 필요 |
| `<Badge>` | `<span className="badge">` | 커스텀 배지 |

### 2.4 피드백 컴포넌트

| MUI | Tailwind/Headless UI | Headless UI 사용 |
|-----|---------------------|------------------|
| `<Dialog>` | Headless UI `<Dialog>` | ✅ 필수 |
| `<Menu>` | Headless UI `<Menu>` | ✅ 필수 |
| `<Popover>` | Headless UI `<Popover>` | ✅ 필수 |
| `<Snackbar>` | Custom Toast | 커스텀 필요 |
| `<Alert>` | `<div role="alert">` + Tailwind | 커스텀 |
| `<CircularProgress>` | Custom Spinner | 커스텀 |
| `<LinearProgress>` | `<div className="progress-bar">` | 커스텀 |
| `<Skeleton>` | `<div className="animate-pulse">` | Tailwind animate |

### 2.5 네비게이션 컴포넌트

| MUI | Tailwind/Headless UI | Headless UI 사용 |
|-----|---------------------|------------------|
| `<Tabs>` | Headless UI `<Tab>` | ✅ 필수 |
| `<AppBar>` | `<header className="fixed top-0">` | 커스텀 |
| `<Drawer>` | Headless UI `<Dialog>` | ✅ 권장 |
| `<Breadcrumbs>` | `<nav aria-label="breadcrumb">` | 커스텀 |
| `<Pagination>` | Custom | 커스텀 필요 |
| `<Link>` | React Router `<Link>` + Tailwind | 라이브러리 연동 |

---

## 3. Headless UI 활용 가이드

### 3.1 필수 사용 컴포넌트

접근성(a11y)이 복잡한 컴포넌트는 **반드시 Headless UI 사용**:

| 컴포넌트 | 이유 | ARIA 패턴 |
|----------|------|----------|
| **Dialog** | 포커스 트랩, ESC 닫기 | `role="dialog"` |
| **Menu** | 키보드 네비게이션 | `role="menu"` |
| **Listbox (Select)** | 옵션 선택, 키보드 | `role="listbox"` |
| **Combobox** | 검색 + 선택 조합 | `role="combobox"` |
| **Tab** | 패널 전환, 화살표 키 | `role="tablist"` |
| **RadioGroup** | 그룹 선택, 화살표 키 | `role="radiogroup"` |
| **Switch** | 토글 상태 | `role="switch"` |
| **Popover** | 외부 클릭 닫기 | 위치 계산 |
| **Disclosure** | 아코디언, 접기/펼치기 | `aria-expanded` |
| **Transition** | 애니메이션 (Dialog와 함께) | - |

### 3.2 커스텀 구현 컴포넌트

직접 구현해도 접근성 구현이 간단한 컴포넌트:

| 컴포넌트 | 구현 난이도 | 접근성 요구사항 |
|----------|------------|----------------|
| **Button** | 낮음 | `type`, `disabled` |
| **Card** | 낮음 | 시맨틱 마크업 |
| **Badge/Chip** | 낮음 | - |
| **Avatar** | 낮음 | `alt` 텍스트 |
| **Progress** | 중간 | `role="progressbar"` |
| **Alert** | 중간 | `role="alert"` |
| **Toast** | 중간 | `aria-live="polite"` |
| **Tooltip** | 높음 | Floating UI 권장 |

### 3.3 Headless UI 설치 및 설정

```bash
# 설치
npm install @headlessui/react

# 권장 추가 패키지
npm install @floating-ui/react  # Tooltip, Popover 위치 계산
npm install @heroicons/react    # 아이콘
```

---

## 4. 아이콘 매핑 (MUI → Heroicons)

### 4.1 공통 아이콘 매핑

| MUI Icon | Heroicons (Outline) | Heroicons (Solid) |
|----------|--------------------|--------------------|
| `SearchIcon` | `MagnifyingGlassIcon` | `MagnifyingGlassIcon` |
| `PersonIcon` | `UserIcon` | `UserIcon` |
| `HomeIcon` | `HomeIcon` | `HomeIcon` |
| `SettingsIcon` | `Cog6ToothIcon` | `Cog6ToothIcon` |
| `DeleteIcon` | `TrashIcon` | `TrashIcon` |
| `EditIcon` | `PencilIcon` | `PencilSquareIcon` |
| `AddIcon` | `PlusIcon` | `PlusIcon` |
| `CloseIcon` | `XMarkIcon` | `XMarkIcon` |
| `MenuIcon` | `Bars3Icon` | `Bars3Icon` |
| `ExpandMoreIcon` | `ChevronDownIcon` | `ChevronDownIcon` |
| `ChevronRightIcon` | `ChevronRightIcon` | `ChevronRightIcon` |
| `SendIcon` | `PaperAirplaneIcon` | `PaperAirplaneIcon` |
| `AttachFileIcon` | `PaperClipIcon` | `PaperClipIcon` |
| `DownloadIcon` | `ArrowDownTrayIcon` | `ArrowDownTrayIcon` |
| `UploadIcon` | `ArrowUpTrayIcon` | `ArrowUpTrayIcon` |
| `RefreshIcon` | `ArrowPathIcon` | `ArrowPathIcon` |
| `CheckIcon` | `CheckIcon` | `CheckIcon` |
| `ErrorIcon` | `ExclamationCircleIcon` | `ExclamationCircleIcon` |
| `WarningIcon` | `ExclamationTriangleIcon` | `ExclamationTriangleIcon` |
| `InfoIcon` | `InformationCircleIcon` | `InformationCircleIcon` |
| `ArticleIcon` | `DocumentTextIcon` | `DocumentTextIcon` |
| `FolderIcon` | `FolderIcon` | `FolderIcon` |
| `SmartToyIcon` | `CpuChipIcon` | `CpuChipIcon` |
| `TimerIcon` | `ClockIcon` | `ClockIcon` |

### 4.2 아이콘 사용법

```tsx
// MUI 방식 (Before)
import SearchIcon from '@mui/icons-material/Search';
<SearchIcon sx={{ fontSize: 24 }} />

// Heroicons 방식 (After)
import { MagnifyingGlassIcon } from '@heroicons/react/24/outline';
<MagnifyingGlassIcon className="h-6 w-6" />

// Solid 버전 (채워진 아이콘)
import { MagnifyingGlassIcon } from '@heroicons/react/24/solid';
```

---

## 5. 스타일 매핑

### 5.1 Spacing (간격)

| MUI sx | Tailwind | 값 |
|--------|----------|-----|
| `p: 1` | `p-1` | 4px |
| `p: 2` | `p-2` | 8px |
| `p: 3` | `p-3` | 12px |
| `p: 4` | `p-4` | 16px |
| `m: 'auto'` | `m-auto` | auto |
| `gap: 2` | `gap-2` | 8px |

### 5.2 Typography (타이포그래피)

| MUI variant | Tailwind |
|-------------|----------|
| `variant="h1"` | `text-4xl font-bold` |
| `variant="h2"` | `text-3xl font-bold` |
| `variant="h3"` | `text-2xl font-bold` |
| `variant="h4"` | `text-xl font-semibold` |
| `variant="h5"` | `text-lg font-semibold` |
| `variant="h6"` | `text-base font-semibold` |
| `variant="body1"` | `text-base` |
| `variant="body2"` | `text-sm` |
| `variant="caption"` | `text-xs text-gray-500` |

### 5.3 Colors (색상)

| MUI | Tailwind |
|-----|----------|
| `color="primary"` | `text-primary-600` / `bg-primary-600` |
| `color="secondary"` | `text-secondary-600` / `bg-secondary-600` |
| `color="error"` | `text-red-600` / `bg-red-600` |
| `color="warning"` | `text-yellow-600` / `bg-yellow-600` |
| `color="info"` | `text-blue-600` / `bg-blue-600` |
| `color="success"` | `text-green-600` / `bg-green-600` |
| `color="text.primary"` | `text-gray-900` |
| `color="text.secondary"` | `text-gray-600` |
| `color="text.disabled"` | `text-gray-400` |

### 5.4 반응형 (Responsive)

| MUI sx | Tailwind |
|--------|----------|
| `{ xs: 'none', md: 'block' }` | `hidden md:block` |
| `{ xs: 12, md: 6 }` (Grid) | `col-span-12 md:col-span-6` |
| `{ xs: 'column', md: 'row' }` | `flex-col md:flex-row` |

### 5.5 다크 모드

| MUI | Tailwind |
|-----|----------|
| `ThemeProvider mode="dark"` | `dark:` prefix |
| `bgcolor: 'background.paper'` | `bg-white dark:bg-gray-800` |
| `color: 'text.primary'` | `text-gray-900 dark:text-white` |

---

## 6. 컴포넌트 변환 예시

### 6.1 Button

```tsx
// MUI (Before)
import { Button } from '@mui/material';

<Button variant="contained" color="primary" startIcon={<SearchIcon />}>
  검색
</Button>

// Tailwind (After)
import { MagnifyingGlassIcon } from '@heroicons/react/24/outline';

<button className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
  <MagnifyingGlassIcon className="h-5 w-5" />
  검색
</button>
```

### 6.2 Card

```tsx
// MUI (Before)
import { Card, CardContent, Typography } from '@mui/material';

<Card sx={{ mb: 2, '&:hover': { boxShadow: 3 } }}>
  <CardContent>
    <Typography variant="h6">{title}</Typography>
    <Typography variant="body2" color="text.secondary">{summary}</Typography>
  </CardContent>
</Card>

// Tailwind (After)
<div className="bg-white rounded-lg shadow-md mb-4 hover:shadow-lg transition-shadow">
  <div className="p-4">
    <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
    <p className="text-sm text-gray-600 mt-2">{summary}</p>
  </div>
</div>
```

### 6.3 TextField with Headless UI

```tsx
// MUI (Before)
import { TextField } from '@mui/material';

<TextField
  label="이메일"
  value={email}
  onChange={(e) => setEmail(e.target.value)}
  error={!!error}
  helperText={error}
/>

// Tailwind + Headless UI (After)
import { Field, Input, Label, Description } from '@headlessui/react';

<Field>
  <Label className="block text-sm font-medium text-gray-700">이메일</Label>
  <Input
    type="email"
    value={email}
    onChange={(e) => setEmail(e.target.value)}
    className={`mt-1 block w-full rounded-md border px-3 py-2 shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500 ${
      error
        ? 'border-red-500 focus:border-red-500'
        : 'border-gray-300 focus:border-primary-500'
    }`}
  />
  {error && (
    <Description className="mt-1 text-sm text-red-600">{error}</Description>
  )}
</Field>
```

### 6.4 Dialog with Headless UI

```tsx
// MUI (Before)
import { Dialog, DialogTitle, DialogContent, DialogActions, Button } from '@mui/material';

<Dialog open={open} onClose={handleClose}>
  <DialogTitle>확인</DialogTitle>
  <DialogContent>정말 삭제하시겠습니까?</DialogContent>
  <DialogActions>
    <Button onClick={handleClose}>취소</Button>
    <Button onClick={handleDelete} color="error">삭제</Button>
  </DialogActions>
</Dialog>

// Tailwind + Headless UI (After)
import { Dialog, DialogPanel, DialogTitle, Transition, TransitionChild } from '@headlessui/react';

<Transition show={open}>
  <Dialog onClose={handleClose} className="relative z-50">
    {/* Backdrop */}
    <TransitionChild
      enter="ease-out duration-300"
      enterFrom="opacity-0"
      enterTo="opacity-100"
      leave="ease-in duration-200"
      leaveFrom="opacity-100"
      leaveTo="opacity-0"
    >
      <div className="fixed inset-0 bg-black/30" />
    </TransitionChild>

    {/* Dialog */}
    <div className="fixed inset-0 flex items-center justify-center p-4">
      <TransitionChild
        enter="ease-out duration-300"
        enterFrom="opacity-0 scale-95"
        enterTo="opacity-100 scale-100"
        leave="ease-in duration-200"
        leaveFrom="opacity-100 scale-100"
        leaveTo="opacity-0 scale-95"
      >
        <DialogPanel className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
          <DialogTitle className="text-lg font-semibold text-gray-900">
            확인
          </DialogTitle>
          <p className="mt-2 text-sm text-gray-600">
            정말 삭제하시겠습니까?
          </p>
          <div className="mt-4 flex justify-end gap-2">
            <button
              onClick={handleClose}
              className="px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-lg"
            >
              취소
            </button>
            <button
              onClick={handleDelete}
              className="px-4 py-2 text-sm text-white bg-red-600 hover:bg-red-700 rounded-lg"
            >
              삭제
            </button>
          </div>
        </DialogPanel>
      </TransitionChild>
    </div>
  </Dialog>
</Transition>
```

### 6.5 Select with Headless UI Listbox

```tsx
// MUI (Before)
import { Select, MenuItem, FormControl, InputLabel } from '@mui/material';

<FormControl fullWidth>
  <InputLabel>문서 유형</InputLabel>
  <Select value={type} onChange={(e) => setType(e.target.value)}>
    <MenuItem value="all">전체</MenuItem>
    <MenuItem value="manual">매뉴얼</MenuItem>
    <MenuItem value="guide">가이드</MenuItem>
  </Select>
</FormControl>

// Tailwind + Headless UI (After)
import { Listbox, ListboxButton, ListboxOption, ListboxOptions, Label } from '@headlessui/react';
import { ChevronDownIcon, CheckIcon } from '@heroicons/react/24/outline';

const options = [
  { value: 'all', label: '전체' },
  { value: 'manual', label: '매뉴얼' },
  { value: 'guide', label: '가이드' },
];

<Listbox value={type} onChange={setType}>
  <Label className="block text-sm font-medium text-gray-700">문서 유형</Label>
  <div className="relative mt-1">
    <ListboxButton className="relative w-full cursor-pointer rounded-lg bg-white py-2 pl-3 pr-10 text-left border border-gray-300 shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500">
      <span className="block truncate">
        {options.find(o => o.value === type)?.label}
      </span>
      <span className="absolute inset-y-0 right-0 flex items-center pr-2">
        <ChevronDownIcon className="h-5 w-5 text-gray-400" />
      </span>
    </ListboxButton>
    <ListboxOptions className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-lg bg-white py-1 shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
      {options.map((option) => (
        <ListboxOption
          key={option.value}
          value={option.value}
          className={({ active }) =>
            `relative cursor-pointer select-none py-2 pl-10 pr-4 ${
              active ? 'bg-primary-100 text-primary-900' : 'text-gray-900'
            }`
          }
        >
          {({ selected }) => (
            <>
              <span className={`block truncate ${selected ? 'font-medium' : 'font-normal'}`}>
                {option.label}
              </span>
              {selected && (
                <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-primary-600">
                  <CheckIcon className="h-5 w-5" />
                </span>
              )}
            </>
          )}
        </ListboxOption>
      ))}
    </ListboxOptions>
  </div>
</Listbox>
```

---

## 7. 마이그레이션 체크리스트

### 7.1 Phase 1: 환경 설정 (1주)

- [ ] Tailwind CSS 설치 및 설정
- [ ] `tailwind.config.js` 커스텀 테마 정의
- [ ] Headless UI 설치
- [ ] Heroicons 설치
- [ ] PostCSS 설정
- [ ] VSCode 확장 설치 (Tailwind IntelliSense)

### 7.2 Phase 2: 신규 컴포넌트 (2-3주)

- [ ] 공통 Button 컴포넌트
- [ ] 공통 Card 컴포넌트
- [ ] 공통 Input 컴포넌트
- [ ] Dialog 컴포넌트 (Headless UI)
- [ ] Select 컴포넌트 (Headless UI)
- [ ] Toast/Notification 컴포넌트
- [ ] Loading Spinner 컴포넌트

### 7.3 Phase 3: 기존 컴포넌트 전환 (4-6주)

- [ ] Dashboard 페이지
- [ ] Search 페이지 (Chat, Keyword)
- [ ] Knowledge 관리 페이지
- [ ] Admin 페이지
- [ ] 공통 레이아웃 (Header, Sidebar)
- [ ] 폼 컴포넌트 전환

### 7.4 Phase 4: MUI 제거 (1주)

- [ ] MUI 의존성 제거
- [ ] Emotion 의존성 제거
- [ ] 사용하지 않는 코드 정리
- [ ] 번들 크기 검증
- [ ] 최종 테스트

---

## 8. 주의사항

### 8.1 접근성 (Accessibility)

| 항목 | MUI | Tailwind |
|------|-----|----------|
| ARIA 속성 | 자동 | 수동 또는 Headless UI |
| 포커스 관리 | 자동 | Headless UI 권장 |
| 키보드 네비게이션 | 자동 | Headless UI 권장 |
| 색상 대비 | 자동 | 수동 검증 필요 |

**권장**: 복잡한 인터랙션 컴포넌트는 반드시 Headless UI 사용

### 8.2 성능 고려사항

```bash
# 번들 분석
npm run build -- --analyze

# 기대 효과
- MUI 제거: ~200KB 감소
- Emotion 제거: ~50KB 감소
- Tailwind (PurgeCSS): ~10KB 미만
```

### 8.3 테스트 전략

| 테스트 유형 | 도구 | 검증 항목 |
|------------|------|----------|
| **Unit** | Vitest + RTL | 컴포넌트 렌더링 |
| **A11y** | axe-core | 접근성 위반 |
| **Visual** | Storybook | 스타일 일관성 |
| **E2E** | Playwright | 사용자 플로우 |

---

## 9. 참고 자료

- [Tailwind CSS 공식 문서](https://tailwindcss.com/docs)
- [Headless UI 공식 문서](https://headlessui.com/)
- [Heroicons 아이콘 검색](https://heroicons.com/)
- [Tailwind UI 컴포넌트](https://tailwindui.com/)
- [Frontend 상세 설계서](../02_design/frontend_detailed_design.md)
- [MUI vs Tailwind 비교 분석](../../../docs/technical_assessment/Guides/검토결과_MUI_vs_Tailwind_비교분석.md)

---

**문서 버전**: 1.0
**최종 수정**: 2026-01-25
