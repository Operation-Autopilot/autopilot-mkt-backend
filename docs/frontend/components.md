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

## Widget Components

### ProfileWidget.tsx

Editable discovery answer cards that build the user's automation profile.

- Renders cards based on answers collected during Discovery phase
- Each card is editable, allowing users to refine their responses
- Cards update `answers` in `SessionContext` when modified
- Visual layout adapts to the number of completed answers

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
