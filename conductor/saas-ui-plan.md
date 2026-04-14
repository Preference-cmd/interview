# SaaS UI Implementation Plan: Claude-inspired Design System

## Objective
To transform the current Next.js `frontend` application into a sophisticated, warm, and professional SaaS interface by implementing the design system specified in `DESIGN.md`, utilizing Tailwind CSS as the styling engine.

## Key Files & Context
- **Design Spec**: `frontend/DESIGN.md`
- **Dependencies**: `frontend/package.json`
- **Styling Configuration**: `frontend/tailwind.config.ts` (To be created), `frontend/app/globals.css`, `frontend/postcss.config.mjs`
- **Typography & Layout**: `frontend/app/layout.tsx`
- **Views & Components**: `frontend/app/page.tsx`, `frontend/components/AlertList.tsx`, `frontend/components/DashboardCharts.tsx`, `frontend/components/StateBadge.tsx`, `frontend/components/StoreList.tsx`, `frontend/components/StoreTimeline.tsx`

## Implementation Steps

### Step 1: Tailwind CSS Installation & Configuration
- Install `tailwindcss`, `postcss`, and `autoprefixer` dependencies.
- Initialize `tailwind.config.ts` and `postcss.config.mjs`.
- Configure `tailwind.config.ts` with custom design tokens from `DESIGN.md`:
  - **Colors**: `parchment` (`#f5f4ed`), `ivory` (`#faf9f5`), `terracotta` (`#c96442`), `anthropic-near-black` (`#141413`), `olive-gray` (`#5e5d59`), `border-cream` (`#f0eee6`), `warm-sand` (`#e8e6dc`), etc.
  - **Typography**: Add `anthropic-serif` (fallback to Georgia) and `anthropic-sans` (fallback to Arial/system).
  - **Shadows**: Add custom ring shadows (`0 0 0 1px #d1cfc5`) and whisper shadows (`0 4px 24px rgba(0,0,0,0.05)`).
  - **Radii**: Update border radius values (`comfortably-rounded`: 8px, `generously-rounded`: 12px, `very-rounded`: 16px).
- Add Tailwind directives to `frontend/app/globals.css`.

### Step 2: Global Typography & Theme Setup
- Update `frontend/app/layout.tsx` to set the base typography to Anthropic Sans, with the `parchment` background color and `anthropic-near-black` text color.
- Ensure global line height is set to `relaxed` (1.60) for body text as per editorial requirements.
- Clean up any existing Geist font imports if they conflict with the specified system typography.

### Step 3: Main Dashboard Layout Refactoring
- Refactor `frontend/app/page.tsx` and the layout structure to implement a modern SaaS sidebar navigation layout.
- Combine modern SaaS layout with the warm editorial pacing:
  - Sidebar: Introduce a left sidebar for primary functional navigation (Dashboard, Stores, Alerts) using `bg-ivory` or `bg-parchment` with a warm `border-r border-border-cream`.
  - Header/Top Bar: Use a minimal top bar or rely on the sidebar for global actions.
  - Main Content Area: Use `bg-parchment` for the canvas.
  - Spacing: Apply generous whitespace/padding using Tailwind's spacing scale (e.g., base unit 8px).

### Step 4: Component Overhaul
- **Cards (KPIs & Containers)**: Update to use `bg-ivory`, `border-border-cream`, and whisper shadows. Titles should use `anthropic-serif` with a weight of 500.
- **Buttons & Interactive Elements**: Refactor standard blue buttons to use `bg-warm-sand` (secondary) or `bg-terracotta` (primary) with appropriate ring shadows on hover/focus.
- **Tables & Lists (`StoreList.tsx`, `AlertList.tsx`, `StoreTimeline.tsx`)**: Apply warm border dividers (`border-border-cream`), update typography to Anthropic Sans, and use the correct neutral text grays (`olive-gray` for secondary text, `stone-gray` for metadata).
- **Badges (`StateBadge.tsx`)**: Convert inline styling to Tailwind utility classes, ensuring badge text scales correctly.
- **Charts (`DashboardCharts.tsx`)**: Update Recharts configurations to map to the new warm color palette, minimizing the use of default bright blues/greens in favor of harmonized tones where possible.

### Step 5: Responsive & Accessibility Validation
- Ensure single-column stacking for mobile (`<479px` and `<768px`) with responsive margins.
- Validate generous touch targets (min 44x44px for actionable items).
- Verify Focus Blue (`#3898ec`) is correctly applied to input/button focus rings for accessibility.

## Verification & Testing
- Run Next.js dev server to verify successful Tailwind integration.
- Visually compare the refactored dashboard against the guidelines in `DESIGN.md`, specifically looking for:
  - Absence of pure white (`#ffffff`) or cool blue-gray backgrounds on the main canvas.
  - Consistent use of Serif for headings and Sans for UI elements.
  - Correct implementation of ring and whisper shadows over traditional drop shadows.
- Verify interactive states (hover/focus) on all buttons and actionable elements.
- Check responsive behavior on mobile and tablet viewport sizes.