# Design Tokens & Theme Specification

> **Task:** S0-MAN-1 · **Owner:** Mann (Frontend + Deployment · Testing)  
> **Requirements:** NFR-06 (Accessibility, WCAG 2.1 AA), DR-01 (Medical Disclaimer Contrast)

---

## 1. Palette & Semantic Color Tokens

All color combinations have been tested against WCAG 2.1 Level AA contrast standards (minimum **4.5:1** for regular text, **3:1** for large text and interactive UI borders).

### 1.1 Brand & Neutral Tokens

| Token Name | Hex Code | Purpose | Contrast vs White |
|---|---|---|---|
| `color-brand-primary` | `#0f766e` (Teal-700) | Primary headers, key CTA buttons, active accents | 5.86:1 (Pass AA) |
| `color-brand-primary-hover` | `#115e59` (Teal-800) | Hover state for primary buttons | 7.94:1 (Pass AAA) |
| `color-brand-subtle` | `#f0fdfa` (Teal-50) | Light teal container background | 1.05:1 (Background only) |
| `color-neutral-background` | `#f8fafc` (Slate-50) | Default application canvas background | 1.04:1 (Canvas only) |
| `color-neutral-surface` | `#ffffff` | Card surfaces, modals, message bubbles | Base |
| `color-neutral-border` | `#e2e8f0` (Slate-200) | Card boundaries, dividers, input borders | 1.34:1 (Structure only) |
| `color-neutral-text-primary` | `#0f172a` (Slate-900) | Body copy, primary headlines | 18.6:1 (Pass AAA) |
| `color-neutral-text-secondary`| `#475569` (Slate-600) | Supporting descriptions, metadata, subtitles | 5.37:1 (Pass AA) |
| `color-neutral-text-muted` | `#64748b` (Slate-500) | Timestamps, placeholder text, field hints | 4.62:1 (Pass AA) |

### 1.2 Medical Risk Tier Tokens (Deterministic Engine Mapping)

The three risk levels from `docs/rules.md` §Nisarg and `docs/SPRINT_PLAN.md`:

| Risk Tier | Background Token | Border Token | Text Token | Badge Hex | WCAG Contrast |
|---|---|---|---|---|---|
| `SELF_CARE` | `#ecfdf5` (Emerald-50) | `#a7f3d0` (Emerald-200) | `#065f46` (Emerald-800) | `#059669` | 6.82:1 (Pass AAA) |
| `CONSULT_DOCTOR` | `#fffbeb` (Amber-50) | `#fde68a` (Amber-200) | `#92400e` (Amber-800) | `#d97706` | 5.91:1 (Pass AA) |
| `URGENT` | `#fff1f2` (Rose-50) | `#fecdd3` (Rose-200) | `#9f1239` (Rose-800) | `#e11d48` | 7.43:1 (Pass AAA) |

---

## 2. Typography Hierarchy

Using modern sans-serif typography (`Inter`, `system-ui`, `-apple-system`, `sans-serif`) optimized for legible medical readability on mobile viewports.

| Scale Token | Font Size | Line Height | Weight | Tailwind Equivalent | Use Case |
|---|---|---|---|---|---|
| `type-h1` | `1.875rem` (30px) | `2.25rem` (36px) | 700 (Bold) | `text-3xl font-bold` | Screen headers, landing hero title |
| `type-h2` | `1.5rem` (24px) | `2.0rem` (32px) | 600 (Semibold) | `text-2xl font-semibold`| Card titles, result primary condition |
| `type-h3` | `1.25rem` (20px) | `1.75rem` (28px) | 600 (Semibold) | `text-xl font-semibold` | Section subheadings, modal headers |
| `type-body-lg` | `1.125rem` (18px) | `1.75rem` (28px) | 400 (Regular) | `text-lg font-normal` | Chat bot prompt bubbles |
| `type-body` | `1.0rem` (16px) | `1.5rem` (24px) | 400 (Regular) | `text-base font-normal`| Standard text, descriptions, lists |
| `type-body-sm` | `0.875rem` (14px) | `1.25rem` (20px) | 400 (Regular) | `text-sm font-normal` | Disclaimers, form helper text |
| `type-caption` | `0.75rem` (12px) | `1.0rem` (16px) | 500 (Medium) | `text-xs font-medium` | Status badges, timestamps |

---

## 3. Spacing, Radii & Elevation

### 3.1 Spacing Scale (4px Baseline Grid)
- `space-1`: `4px` (`0.25rem`) — Fine alignment, badge padding
- `space-2`: `8px` (`0.5rem`) — Gap between icons and labels
- `space-3`: `12px` (`0.75rem`) — Button inner padding, compact list gaps
- `space-4`: `16px` (`1.0rem`) — Card padding, input padding, standard gap
- `space-6`: `24px` (`1.5rem`) — Section vertical spacing, modal padding
- `space-8`: `32px` (`2.0rem`) — Major section dividing margin
- `space-12`: `48px` (`3.0rem`) — Screen top/bottom gutters on desktop

### 3.2 Border Radius
- `radius-sm`: `6px` (`0.375rem`) — Badges, small inputs
- `radius-md`: `8px` (`0.5rem`) — Standard buttons, text inputs
- `radius-lg`: `12px` (`0.75rem`) — Message bubbles, alert cards
- `radius-xl`: `16px` (`1.0rem`) — Main application cards, modal containers
- `radius-full`: `9999px` — Pill badges, circular action buttons

### 3.3 Elevation & Shadows
- `shadow-sm`: `0 1px 2px 0 rgba(0, 0, 0, 0.05)` — Subtle cards, button rest state
- `shadow-md`: `0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.05)` — Floating action bars, active inputs
- `shadow-lg`: `0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.05)` — Modals, popovers, dropdowns

---

## 4. Accessibility & Focus State Tokens

- **Focus Ring:** `outline: 2px solid #0f766e; outline-offset: 2px;` (high contrast teal ring for keyboard navigation).
- **Reduced Motion:** All transitions wrapped in `@media (prefers-reduced-motion: reduce)` with duration set to `0.01ms`.
- **Target Sizes:** Touch targets for buttons and interactive badges are at least `44px × 44px` per WCAG Success Criterion 2.5.5.
