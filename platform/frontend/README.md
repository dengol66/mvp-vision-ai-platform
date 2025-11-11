# Platform Frontend

Modern frontend for Vision AI Training Platform using Next.js 15 and React 18.

## Features

- ✅ Next.js 15 with App Router
- ✅ TypeScript for type safety
- ✅ Tailwind CSS with design tokens
- ✅ SUIT font for Korean + Inter for Latin
- ✅ shadcn/ui component library
- ✅ React Query for data fetching
- ✅ Zustand for state management
- ✅ Design system compliance

## Quick Start

### 1. Install Dependencies

```bash
pnpm install
```

### 2. Configure Environment

```bash
cp .env.local.example .env.local
# Edit .env.local with your backend API URL
```

### 3. Run Development Server

```bash
pnpm dev
```

Open http://localhost:3000 in your browser.

## Project Structure

```
frontend/
├── app/                    # Next.js app directory
│   ├── layout.tsx         # Root layout (fonts, metadata)
│   ├── page.tsx           # Home page
│   ├── globals.css        # Global styles (design tokens)
│   └── training/          # Training pages
├── components/            # React components
│   ├── ui/               # shadcn/ui components
│   ├── training/         # Training-specific components
│   └── layout/           # Layout components
├── lib/                   # Utilities
│   ├── api/              # API client
│   ├── hooks/            # Custom React hooks
│   └── utils.ts          # Helper functions
├── fonts/                # Local fonts (SUIT)
└── public/               # Static assets
```

## Design System

All components follow the design system defined in `../docs/frontend/DESIGN_SYSTEM.md`:

- **Colors**: HSL-based CSS variables (Primary, Success, Warning, etc.)
- **Typography**: SUIT (Korean) + Inter (Latin)
- **Spacing**: 4px base unit (only multiples of 4)
- **Components**: shadcn/ui with CVA variants
- **Accessibility**: WCAG 2.1 AA compliance

Preview the design system: `../docs/frontend/design-preview.html`

## Development

### Run Tests

```bash
pnpm test
```

### Lint

```bash
pnpm lint
```

### Format

```bash
pnpm format
```

### Build

```bash
pnpm build
pnpm start  # Production server
```

## Migrating from MVP

This frontend reuses components from `../../mvp/frontend/` but with:

1. ✅ Design tokens applied (no hardcoded colors)
2. ✅ SUIT font for Korean
3. ✅ Improved accessibility (ARIA attributes)
4. ✅ Responsive design (mobile-first)
5. ✅ shadcn/ui components

See `../docs/development/IMPLEMENTATION_PLAN.md` for migration guide.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API URL | `http://localhost:8000/api/v1` |
| `NEXT_PUBLIC_WS_URL` | WebSocket URL | `ws://localhost:8000/ws` |
| `NEXT_PUBLIC_ENVIRONMENT` | Environment | `development` |

## License

Copyright © 2025 Vision AI Platform Team
