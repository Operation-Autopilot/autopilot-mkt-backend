---
title: Mobile Implementation
---

# Mobile Implementation

The mobile experience adapts the desktop 3-column layout into a tab-based navigation with a bottom sheet chat overlay. The breakpoint is **768px**, detected by the `useIsMobile` hook.

## Breakpoint Strategy

All mobile/desktop switching is driven by the `useIsMobile` hook, which monitors the `(max-width: 767px)` media query. Components conditionally render mobile or desktop variants based on this hook's return value.

```tsx
const isMobile = useIsMobile();
return isMobile ? <MobileLayout /> : <DesktopLayout />;
```

There is no separate mobile route tree. The same components adapt their rendering based on the breakpoint.

## Mobile Layout Structure

```
┌─────────────────────────────┐
│         Header / Phase      │
├─────────────────────────────┤
│                             │
│                             │
│      Active Tab Content     │
│    (Marketplace or Profile) │
│                             │
│                             │
├─────────────────────────────┤
│  Marketplace  │   Profile   │  <-- MobileTabBar
└─────────────────┬───────────┘
                  │
              [Chat FAB]  <-- ChatFAB (floating)
```

## MobileTabBar.tsx

Tab navigation bar fixed to the bottom of the screen during the Discovery phase.

**Tabs:**

- **Marketplace** -- Shows the robot catalog (RobotMarketplace)
- **Profile** -- Shows the discovery profile widget (ProfileWidget)

**Behaviors:**

- Fixed position at the bottom of the viewport
- Highlights the active tab
- Tab set may change based on the current phase (e.g., ROI phase shows the ROI dashboard instead)

## ChatFAB.tsx

Floating action button that opens the chat bottom sheet.

**Features:**

- Positioned in the bottom-right corner, above the tab bar
- Displays an **unread badge** showing the count of unread agent messages
- Uses the `fab-pulse` CSS animation to draw attention when new messages arrive
- Tapping the FAB opens `MobileBottomSheet` with the chat interface

**Unread message tracking:**

The FAB tracks unread messages by comparing the total message count with the count at the time the user last closed the bottom sheet. Any new agent messages received while the sheet is closed increment the unread badge.

## MobileBottomSheet.tsx

Slide-up overlay that contains the full chat interface on mobile.

**Specifications:**

| Property | Value |
|---|---|
| Height | 85% of viewport height |
| Entry animation | Slide up from bottom |
| Exit animation | Slide down |
| Dismiss gesture | Drag down to dismiss |
| Backdrop | Semi-transparent overlay |

**Behaviors:**

- Opens when the ChatFAB is tapped
- Contains the full `AgentChat` component adapted for mobile
- Drag-to-dismiss: users can grab the handle at the top and drag downward to close
- The backdrop overlay closes the sheet when tapped
- When closed, unread count resets and the FAB updates accordingly
- Scroll within the chat is independent of the sheet's drag gesture

**Drag interaction:**

The sheet includes a drag handle bar at the top. Dragging downward past a threshold (approximately 30% of sheet height) triggers dismissal. Dragging upward or releasing before the threshold snaps the sheet back to full height.

## Mobile Adaptations by Phase

### Discovery (Mobile)

- MobileTabBar switches between Marketplace and Profile
- ChatFAB provides access to the AI agent
- Bottom sheet chat is the primary interaction method

### ROI (Mobile)

- ROIView renders as the main content (full screen, scrollable)
- ChatFAB remains available for agent questions
- Tab bar may show a single ROI tab

### Greenlight (Mobile)

- GreenlightView renders as the main content
- Checkout flow is adapted for single-column layout
- ChatFAB remains available for support during checkout
