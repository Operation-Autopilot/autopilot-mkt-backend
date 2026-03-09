---
title: UI Phase System
---

# UI Phase System

The Autopilot Marketplace guides users through a three-phase journey: **Discovery**, **ROI**, and **Greenlight**. Each phase changes the content displayed in the center column while the chat interface remains persistent.

## Phase Overview

```
Discovery  ──>  ROI  ──>  Greenlight
   │              │            │
   │              │            │
   v              v            v
 Browse &      Analyze      Configure &
 Profile       Savings       Purchase
```

Phase transitions are **triggered by the AI agent conversation flow**, not by manual user navigation. The agent determines when a user has completed enough of a phase to advance and sends a phase transition message that the frontend interprets.

## Discovery Phase

**Purpose:** Understand the user's needs and help them find the right automation robot.

**Active components:**

- **AgentChat** -- The AI agent asks questions to understand the user's workflow, pain points, and automation goals
- **RobotMarketplace** -- Users browse the robot catalog, apply filters, and explore options
- **ProfileWidget** -- Displays editable answer cards that reflect the user's responses; users can refine answers at any time

**State used:**

- `answers` in `SessionContext` accumulates user responses
- `selectedRobotId` is set when a user picks a robot to evaluate
- Quick reply chips in the chat guide users through structured discovery questions

**Transition to ROI:** The agent triggers the transition once it has gathered enough information about the user's needs and they have selected a robot. A phase transition message is sent through the conversation, and `currentPhase` updates to `'ROI'`.

## ROI Phase

**Purpose:** Present data-driven analysis of the selected robot's value proposition.

**Active components:**

- **AgentChat** -- The agent walks through the ROI analysis, explains projections, and answers questions
- **ROIView** -- Dashboard displaying savings visualizations, cost comparisons, and payback period data

**Key data points displayed:**

- Projected time savings (hours/week, hours/year)
- Cost comparison between current manual process and automation
- Payback period calculation and timeline
- Efficiency gain percentages

**State used:**

- ROI data is fetched via React Query based on the `selectedRobotId` and `answers`
- The agent references specific data points in the conversation

**Transition to Greenlight:** Once the user has reviewed the ROI analysis and expressed intent to proceed, the agent triggers the transition to `'GREENLIGHT'`.

## Greenlight Phase

**Purpose:** Finalize the robot configuration, identify stakeholders, and complete the purchase.

**Active components:**

- **AgentChat** -- The agent guides the user through final configuration and checkout steps
- **GreenlightView** -- Displays the option summary, stakeholder identification form, and Stripe checkout integration

**Workflow:**

1. **Option summary** -- Review the selected robot, configuration, and pricing
2. **Stakeholder identification** -- Identify team members who will be involved in deployment
3. **Checkout** -- Complete payment via Stripe integration

**State used:**

- `greenlightState` in `SessionContext` tracks selected options and stakeholder information
- Stripe session is created via the backend API
- `CheckoutSuccess` component renders after successful payment

## Phase Transition Mechanics

Phase transitions flow through the conversation system:

1. The AI agent determines a phase is complete based on conversation context
2. The backend sends a message with a phase transition signal
3. `useConversation` hook detects the transition message
4. The hook updates `currentPhase` in `SessionContext`
5. `App.tsx` re-renders the appropriate content for the new phase
6. `ProgressBar` updates to reflect the new active phase

Users cannot manually skip phases or navigate backward. The agent-driven flow ensures users have the information they need before advancing.
