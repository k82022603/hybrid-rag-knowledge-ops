# NEXUS Style Guide (Dark Theme)

## 1. Typography
**Font Family (Display)**: [Exo 2](https://fonts.google.com/specimen/Exo+2) (Headings, Branding)
**Font Family (Body)**: [Roboto](https://fonts.google.com/specimen/Roboto) (Interface Text)

- **Headings**: `font-weight: 700` (Bold)
- **Body**: `font-weight: 400` (Regular)
- **Monospace**: For identifiers, code (e.g., `DOC-8821`)

## 2. Color Palette

### Base Colors (Deep Space)
- **Background**: `#0f111a` (Tailwind `dark-200`)
- **Surface**: `rgba(30, 41, 59, 0.4)` (Backdrop Blur `blur-lg`) - Glassmorphism panels
- **Borders**: `rgba(255, 255, 255, 0.05)` (White/5)

### Brand / Neon Accent Colors
- **Cyan**: `#06b6d4` (Tailwind `cyan-500` / `neon-cyan`)
- **Purple**: `#a855f7` (Tailwind `purple-500` / `neon-purple`)
- **Pink**: `#ec4899` (Tailwind `pink-500` / `neon-pink`)

### Text Colors
- **Primary Text**: `#e2e8f0` (Tailwind `gray-200`)
- **Secondary Text**: `#94a3b8` (Tailwind `gray-400`)
- **Muted Text**: `#64748b` (Tailwind `gray-500`)
- **Glow Text**: `text-shadow: 0 0 10px rgba(6, 182, 212, 0.5)`

## 3. UI Components

### Glassmorphism Panels
- **Background**: Semitransparent slate (`rgba(30, 41, 59, 0.4)`).
- **Blur**: `backdrop-blur-sm` or `backdrop-blur-md`.
- **Border**: Thin, subtle white border.
- **Shadow**: Soft shadow + optional glow on hover.

### Navigation / Sidebar
- **Background**: Glass panel or transparent.
- **Item Default**: Text Gray-400.
- **Item Hover**: White text, background `white/5`.
- **Item Active**: `border-l-2 border-cyan-500`, specific gradient background, text `cyan-400`.

### Cards & Stats
- **Style**: Rounded `2xl`, glassmorphism.
- **Interactive**: Hover creates a border glow (`border-neon-cyan/30` etc.).
- **Typography**: Large font sizes for numbers (`text-3xl`).

### Buttons & Inputs
- **Inputs**: Dark background `bg-black/40`, border `white/10`.
- **Focus**: Ring `neon-cyan` with glow effect.
- **Buttons**: Icon-only or minimal text. Often use glowing icons.

### Effects
- **Gradients**: `radial-gradient` for ambient background glow.
- **Animations**: `animate-pulse` for status indicators.
- **Shadows**: Colored shadows to simulate neon light (e.g., `shadow-[0_0_8px_#ec4899]`).

## 4. Iconography
- **Style**: Minimalist strokes.
- **Color**: Often match the neon accent color of the section.
- **Size**: Variable, often `w-6 h-6`.

## 5. Content Page Styling
For documentation, articles, and knowledge base entries.

### Typography
- **H1 Page Title**: `text-3xl font-display font-bold text-white mb-6 bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400`
- **H2 Section**: `text-2xl font-display font-semibold text-neon-cyan mt-10 mb-4 border-b border-white/10 pb-2`
- **H3 Subsection**: `text-xl font-medium text-neon-purple mt-8 mb-3`
- **Paragraphs**: `text-gray-300 leading-relaxed mb-4`
- **Links**: `text-neon-cyan hover:text-white transition-colors border-b border-neon-cyan/30 hover:border-neon-cyan`

### Structural Elements
- **Blockquotes**: `border-l-4 border-neon-purple/50 pl-4 py-2 italic text-gray-400 bg-white/5 rounded-r-lg`
- **Lists**:
  - `list-disc list-inside space-y-2 text-gray-300 marker:text-neon-cyan`
  - `list-decimal list-inside space-y-2 text-gray-300 marker:text-neon-purple`

### Code & Technical
- **Inline Code**: `bg-white/10 text-neon-pink px-1.5 py-0.5 rounded text-sm font-mono border border-white/5`
- **Code Blocks**:
  - Background: `#000000` (Black) or `#0a0b12` (Dark-300).
  - Border: `border border-white/10` or `border border-neon-purple/20`.
  - Text: `#e2e8f0` (Gray-200).
  - Padding: `p-4 rounded-xl relative overflow-hidden`.
  - Effect: Optional "Scanline" overlay or corner glow.

### Tables
- **Container**: `glass-panel rounded-xl overflow-hidden`
- **Header**: `bg-white/5 text-left text-xs font-display font-medium text-neon-cyan uppercase tracking-wider px-6 py-4`
- **Rows**: `border-b border-white/5 hover:bg-white/5 transition-colors`
- **Cells**: `px-6 py-4 text-sm text-gray-300`

---
*Reference: Derived from `dark_theme.html` implementation.*
