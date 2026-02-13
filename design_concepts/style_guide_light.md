# KnowledgeOps Style Guide (Light Theme)

## 1. Typography
**Font Family**: [Inter](https://fonts.google.com/specimen/Inter)
- **Headings**: `font-weight: 600` (SemiBold) or `700` (Bold)
- **Body**: `font-weight: 400` (Regular)
- **Small Text**: `font-weight: 500` (Medium) for labels

## 2. Color Palette

### Base Colors
- **Background**: `#F9FAFB` (Tailwind `gray-50`)
- **Surface (Cards/Sidebar)**: `#FFFFFF` (White)
- **Borders**: `#E5E7EB` (Tailwind `gray-200`)

### Brand Colors (Indigo & Blue Gradient)
- **Primary**: `#4F46E5` (Tailwind `indigo-600`)
- **Secondary**: `#2563EB` (Tailwind `blue-600`)
- **Gradient**: `bg-gradient-to-r from-indigo-500 to-blue-600`

### Text Colors
- **Primary Text**: `#111827` (Tailwind `gray-900`) - Headings, active states
- **Secondary Text**: `#4B5563` (Tailwind `gray-600`) - Body text, inactive icons
- **Muted Text**: `#9CA3AF` (Tailwind `gray-400`) - Placeholders, metadata

### Functional Colors
- **Success**: `#10B981` (Tailwind `green-500`)
- **Warning**: `#F59E0B` (Tailwind `yellow-500`)
- **Danger**: `#EF4444` (Tailwind `red-500`)

## 3. UI Components

### Navigation / Sidebar
- **Background**: White with right border.
- **Item Default**: Text Gray-600, transparent background.
- **Item Hover**: `bg-gray-50`, `text-indigo-600`.
- **Item Active**: `bg-indigo-50`, `text-indigo-600`, Border-right `3px solid indigo-600`.

### Cards & Containers
- **Style**: White background, `rounded-xl`.
- **Shadow**: `shadow-sm` for default state, `shadow-md` for hover.
- **Border**: Thin border `border-gray-100`.

### Buttons
- **Primary**: Gradient or solid Indigo. White text. `rounded-lg`.
- **Secondary/Ghost**: White background, Indigo text, soft hover `bg-gray-50`.

### Inputs
- **Style**: White background, `border-gray-300`, `rounded-lg`.
- **Focus**: `ring-2 ring-indigo-500 border-transparent`.

## 4. Iconography
- **Style**: Outline / Stroke icons (e.g., Heroicons).
- **Stroke Width**: 2px.
- **Size**: Typically `w-5 h-5` or `w-6 h-6`.

## 5. Content Page Styling
For documentation, articles, and knowledge base entries.

### Typography
- **H1 Page Title**: `text-3xl font-bold text-gray-900 mb-6`
- **H2 Section**: `text-2xl font-semibold text-gray-800 mt-8 mb-4`
- **H3 Subsection**: `text-xl font-medium text-gray-800 mt-6 mb-3`
- **Paragraphs**: `text-gray-600 leading-relaxed mb-4`
- **Links**: `text-indigo-600 hover:text-indigo-800 underline decoration-indigo-200 hover:decoration-indigo-600 transition-all`

### Structural Elements
- **Blockquotes**: `border-l-4 border-indigo-500 pl-4 py-2 italic text-gray-700 bg-gray-50 rounded-r-lg`
- **Lists**:
  - `list-disc list-inside space-y-1 text-gray-600 marker:text-indigo-500`
  - `list-decimal list-inside space-y-1 text-gray-600 marker:font-medium`

### Code & Technical
- **Inline Code**: `bg-gray-100 text-pink-600 px-1.5 py-0.5 rounded text-sm font-mono`
- **Code Blocks**:
  - Background: `#1F2937` (Gray-800) for contrast or `#F3F4F6` (Gray-100) for subtle.
  - Text: White (if dark bg) or Gray-800 (if light bg).
  - Padding: `p-4 rounded-lg overflow-x-auto`.

### Tables
- **Container**: `border border-gray-200 rounded-lg overflow-hidden`
- **Header**: `bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider px-6 py-3`
- **Rows**: `bg-white border-b border-gray-200 hover:bg-gray-50 transition-colors`
- **Cells**: `px-6 py-4 text-sm text-gray-600`

---
*Reference: Derived from `light_theme.html` implementation.*
