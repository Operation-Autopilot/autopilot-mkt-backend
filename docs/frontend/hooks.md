---
title: Custom Hooks
---

# Custom Hooks

Custom hooks live in `src/state/hooks/` and encapsulate reusable logic across components.

## useConversation.ts

The primary hook for managing the AI chat experience. Handles all aspects of the conversation lifecycle.

**Returns:**

| Property | Type | Description |
|---|---|---|
| `messages` | `Message[]` | Array of conversation messages (user and agent) |
| `sendMessage` | `(text: string) => void` | Send a user message to the agent |
| `isTyping` | `boolean` | Whether the agent is currently composing a response |
| `quickReplies` | `string[]` | Available quick reply chip options |
| `selectQuickReply` | `(reply: string) => void` | Send a quick reply as a message |

**Behaviors:**

- Manages the WebSocket or polling connection to the backend conversation API
- Appends new messages to the thread and triggers re-renders
- Displays typing indicators while the agent is generating a response
- Parses agent messages for quick reply chip data and surfaces them
- Detects **phase transition messages** from the agent and updates `currentPhase` in `SessionContext`
- Handles reconnection and error recovery

**Phase transition detection:**

When the agent sends a message signaling a phase change, this hook intercepts it and dispatches the appropriate state update. This is the mechanism that drives the entire phase system from the conversation flow.

**Usage:**

```tsx
const { messages, sendMessage, isTyping, quickReplies, selectQuickReply } = useConversation();
```

## useRobots.ts

Handles robot data fetching and caching via TanStack React Query.

**Returns:**

| Property | Type | Description |
|---|---|---|
| `robots` | `Robot[]` | Array of available robots |
| `isLoading` | `boolean` | Whether robot data is being fetched |
| `error` | `Error \| null` | Any fetch error |
| `refetch` | `() => void` | Manually trigger a refetch |

**Behaviors:**

- Fetches the robot catalog from `api.tryautopilot.com`
- Caches results with React Query (avoids redundant fetches)
- Supports filtering parameters passed as hook arguments
- Returns loading and error states for UI feedback

**Usage:**

```tsx
const { robots, isLoading } = useRobots();
```

## useIsMobile.ts

Detects whether the viewport is at or below the mobile breakpoint.

**Returns:**

| Property | Type | Description |
|---|---|---|
| `isMobile` | `boolean` | `true` when viewport width is less than 768px |

**Behaviors:**

- Listens to window resize events
- Uses `matchMedia` for the `(max-width: 767px)` query
- Debounces resize events to avoid excessive re-renders
- Used throughout the app to switch between desktop and mobile layouts

**Usage:**

```tsx
const isMobile = useIsMobile();

return isMobile ? <MobileLayout /> : <DesktopLayout />;
```

## useTheme.ts

Manages theme state and preferences.

**Returns:**

| Property | Type | Description |
|---|---|---|
| `theme` | `'light' \| 'dark'` | Current active theme |
| `toggleTheme` | `() => void` | Switch between light and dark themes |

**Behaviors:**

- Reads the user's system preference on initialization
- Persists theme choice to `localStorage`
- Applies the appropriate Tailwind `dark:` class to the document root
- Provides reactive theme state for components that need conditional styling

**Usage:**

```tsx
const { theme, toggleTheme } = useTheme();
```
