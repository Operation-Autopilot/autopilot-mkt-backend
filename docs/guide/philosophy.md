---
title: Development Philosophy
---

# Development Philosophy

The principles and design decisions that guide how Autopilot Marketplace is built.

## Agent-First Design

The AI agent is the primary interface, not a bolted-on feature. Every architectural decision should support the agent's ability to conduct natural conversations, retrieve relevant products, and produce structured outputs. The UI exists to present what the agent generates, not to replace it.

## Structured Output from Conversations

Conversations are not open-ended chat. Each phase (Discovery, ROI, Greenlight) is designed to produce specific structured data: buyer requirements, product shortlists, ROI projections, and procurement summaries. The agent extracts and organizes this data as the conversation progresses.

## Rapid Iteration

Ship small changes frequently. The architecture is designed for fast deployment cycles on GCP Cloud Run via Docker. Prefer working software over comprehensive documentation. Measure agent effectiveness through real buyer interactions and iterate accordingly.

## Layer Isolation

The backend follows a strict layered architecture:

```
API (Routers) → Services → Models → Schemas → Core
```

Each layer has a single responsibility:

- **Routers** handle HTTP concerns: request parsing, response formatting, status codes
- **Services** contain business logic and orchestrate operations across models
- **Models** define database entities and data access
- **Schemas** define request/response shapes using Pydantic
- **Core** holds shared configuration, utilities, and cross-cutting concerns

Layers only depend downward. A router calls a service, never another router. A service calls models and schemas, never a router. This isolation makes the codebase testable and keeps changes localized.

## Single Responsibility

Each module, class, and function should do one thing. If a function is doing validation, database access, and response formatting, it should be split. This is enforced through code size guidelines rather than rigid rules.

## Code Size Guidelines

These limits serve as signals, not hard rules. When a file or function exceeds them, it usually means the code is doing too much and should be split.

| Scope    | Target   |
| -------- | -------- |
| File     | < 300 lines |
| Function | < 30 lines  |

Smaller units are easier to read, test, and review. When in doubt, split.
