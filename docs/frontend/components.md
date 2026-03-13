---
title: Component Inventory
---

# Component Inventory

All components live under `src/components/`. This page catalogs the major components, their responsibilities, and key props.

## Core Application Components

### AgentChat.tsx

The AI chat interface that serves as the primary interaction point throughout all phases.

- Renders the conversation message thread (user and agent messages)
- Handles message input, sending, and display of typing indicators
- Displays quick reply chips for guided responses
- Manages auto-scrolling and message grouping
- Adapts between inline panel (desktop) and bottom sheet (mobile)

### RobotMarketplace.tsx

The robot catalog with browsing and filtering capabilities.

- Displays available automation robots as browsable cards
- Provides filter controls (category, price range, capabilities)
- Supports search functionality
- Handles robot selection, which updates `selectedRobotId` in session state
- Integrates with the comparison drawer for side-by-side evaluation

### ROIView.tsx

The ROI analysis dashboard shown during the ROI phase.

- Visualizes projected savings and efficiency gains
- Displays cost comparison charts (current process vs. automated)
- Shows payback period calculations and timelines
- Pulls data from backend ROI analysis endpoints via React Query

### GreenlightView.tsx

The checkout and deployment view for the Greenlight phase.

- Summarizes selected robot options and configuration
- Provides stakeholder identification workflow
- Integrates Stripe for payment processing
- Displays deployment timeline and next steps

## Discovery Components (`src/components/discovery/`)

### DiscoveryProfilePanel.tsx

Main discovery answer panel shown in the center column during Discovery phase.

- Renders all collected answers as editable `ProfileCard` components
- Groups cards by category (Company, Facility, Operations, Economics, Context)
- Shows progress toward ROI readiness
- Integrates floor plan uploader

### ProfileCard.tsx

Individual editable discovery answer card.

- Renders a single answer with edit/save/cancel controls
- Updates `answers` in `SessionContext` when modified
- Visual layout adapts based on answer group and edit state

### FloorPlanUploader.tsx

Drag-and-drop floor plan upload with GPT-4o Vision analysis.

- Accepts image files (< 10MB)
- Calls `POST /api/v1/floor-plans/analyze` for Vision analysis
- Auto-fills sqft and monthly_spend from analysis results
- Stores analysis in localStorage for persistence

### ProgressBar.tsx

Phase indicator displayed in the application header.

- Shows the three phases: Discovery, ROI, Greenlight
- Highlights the current active phase from `SessionContext.currentPhase`
- Provides visual progression feedback
- Non-interactive (phase transitions are agent-driven)

### ComparisonDrawer.tsx

Side-by-side robot comparison panel.

- Slides in as a drawer overlay
- Compares two or more selected robots across key dimensions
- Displays feature matrices, pricing differences, and fit scores
- Can be triggered from the marketplace view

## Modal and Utility Components

### SignupModal.tsx

User registration modal.

- Handles new user sign-up flow via Supabase auth
- Collects user and company information
- Manages form validation and error states
- Redirects to the main application on successful registration

### CheckoutSuccess.tsx

Post-checkout confirmation screen.

- Displayed after successful Stripe payment in the Greenlight phase
- Shows order summary and confirmation details
- Provides next steps and deployment information
- Includes links to support and documentation

### ErrorBoundary.tsx

Top-level error boundary for graceful failure handling.

- Catches unhandled React rendering errors
- Displays a user-friendly error message with recovery options
- Logs error details for debugging
- Prevents full application crashes from propagating

## Mobile Components (`src/components/mobile/`)

### ChatFAB.tsx

Floating action button for opening chat on mobile viewports.

- Positioned bottom-right on mobile (< 768px)
- Shows unread message count badge
- Triggers `MobileBottomSheet` on tap

### MobileBottomSheet.tsx

Slide-up chat overlay for mobile viewports.

- Opens at 85% viewport height
- Contains full `AgentChat` functionality (messages, chips, input)
- Drag-down gesture to dismiss
- Manages focus and scroll locking

### MobileTabBar.tsx

Bottom tab bar for switching between Marketplace and Profile views on mobile.

- Two tabs: Marketplace (robot grid) and Profile (discovery cards)
- Active tab highlighted with lime accent
- Replaces the desktop 3-column layout on narrow viewports

## Shared Components (`src/components/shared/`)

### ErrorAlert.tsx

Reusable error message display component.

- Renders error text with appropriate styling
- Used across multiple views for API error feedback

### ExpandedRobotView.tsx

Robot detail modal/expanded view.

- Shows full specs: function, coverage rate, runtime, ideal environment, key strengths
- Displays recommendation context when available (match score, label)
- Triggered from marketplace card click or ROI recommendation selection

### LoadingPage.tsx

Full-page loading state component.

- Shown during lazy-loaded component resolution (ROIView, GreenlightView)
- Animated spinner with Autopilot branding

### SelectionBadge.tsx

Visual badge indicating a selected robot.

- Lime ring indicator on selected robot cards
- Used in both marketplace grid and ROI recommendation cards

### AcceptInvitation.tsx

Team invitation acceptance flow.

- Handles invitation token from URL
- Creates account or links to existing account
- Joins the inviting company
