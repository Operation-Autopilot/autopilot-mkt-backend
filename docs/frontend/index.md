---
title: Frontend Overview
---

# Frontend Overview

The Autopilot Marketplace frontend is a **React 18 + TypeScript** single-page application built with **Vite**. It provides a conversational commerce experience where users discover, evaluate, and deploy automation robots through an AI-guided workflow.

## Tech Stack

| Technology | Purpose |
|---|---|
| React 18 | UI framework |
| TypeScript | Type safety |
| Vite | Build tooling and dev server |
| Tailwind CSS (CDN) | Utility-first styling |
| React Context | Local/session state |
| TanStack React Query | Server state and caching |
| Supabase | Authentication |

## Key Directories

```
src/
├── api/              # API client functions (backend at api.tryautopilot.com)
├── components/       # React components (pages, widgets, modals)
├── state/
│   ├── context/      # React Context providers (SessionContext, AuthContext)
│   └── hooks/        # Custom hooks (useConversation, useRobots, useIsMobile)
└── App.tsx           # Main layout, phase routing, and chat state
```

## Application Layout

`App.tsx` serves as the main layout orchestrator. It manages phase routing and chat state at the top level.

### Desktop (>= 768px)

The desktop layout uses a **3-column design**:

```
┌──────────────┬───────────────────┬──────────────┐
│  Marketplace │     Content       │     Chat     │
│   (Left)     │    (Center)       │   (Right)    │
└──────────────┴───────────────────┴──────────────┘
```

- **Left column** -- Robot marketplace catalog and filters
- **Center column** -- Phase-specific content (Discovery profile, ROI dashboard, Greenlight checkout)
- **Right column** -- Persistent AI agent chat interface

### Mobile (< 768px)

The mobile layout uses **tab navigation** with a **bottom sheet chat**:

- A tab bar switches between primary views (Marketplace, Profile, etc.)
- The AI chat is accessed via a floating action button (FAB) that opens a slide-up bottom sheet overlay
- Unread message indicators keep users aware of agent activity

## Phase System

The application is organized around three sequential phases that guide users through the purchasing journey:

1. **Discovery** -- Chat with the AI agent, browse the robot marketplace, build a profile
2. **ROI** -- Review savings analysis, cost comparisons, and payback period data
3. **Greenlight** -- Confirm options, identify stakeholders, and complete checkout via Stripe

Phase transitions are driven by the AI agent conversation flow rather than manual navigation. See [UI Phases](./ui-phases.md) for details.

## API Communication

All backend communication targets `api.tryautopilot.com`. API calls are wrapped in dedicated client functions under `src/api/` and consumed through TanStack React Query hooks for automatic caching, refetching, and loading state management.

## Authentication

User authentication is handled by **Supabase**. Auth state is managed through `AuthContext` and includes user identity, session tokens, and associated company information.
