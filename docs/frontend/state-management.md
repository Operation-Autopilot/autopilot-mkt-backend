---
title: State Management
---

# State Management

The frontend uses a combination of **React Context** for local/session state and **TanStack React Query** for server state. This separation keeps UI state close to the component tree while leveraging React Query's caching and synchronization for API data.

## Context Providers

### SessionContext.tsx

`SessionContext` holds all session-level state that drives the application's phase system and user journey.

**State shape:**

| Field | Type | Description |
|---|---|---|
| `currentPhase` | `'DISCOVERY' \| 'ROI' \| 'GREENLIGHT'` | The active phase of the user journey |
| `answers` | `Record<string, any>` | Discovery answers collected from user interactions |
| `selectedRobotId` | `string \| null` | Currently selected robot for evaluation |
| `greenlightState` | `object` | Checkout state including selected options and stakeholder info |

**Key behaviors:**

- `currentPhase` determines which content views are rendered in the center column
- `answers` are populated through the AI agent conversation and ProfileWidget edits
- `selectedRobotId` is set when a user selects a robot from the marketplace
- `greenlightState` accumulates configuration and stakeholder data during the Greenlight phase
- Phase transitions are dispatched from conversation hooks when the agent signals a phase change

**Usage:**

```tsx
import { useSession } from '../state/context/SessionContext';

function MyComponent() {
  const { currentPhase, answers, selectedRobotId } = useSession();
  // ...
}
```

### AuthContext.tsx

`AuthContext` manages authentication state via Supabase.

**State shape:**

| Field | Type | Description |
|---|---|---|
| `user` | `User \| null` | Supabase user object |
| `session` | `Session \| null` | Active Supabase session with tokens |
| `company` | `Company \| null` | Associated company information |
| `isLoading` | `boolean` | Auth state initialization flag |

**Key behaviors:**

- Initializes by checking for an existing Supabase session on mount
- Listens to Supabase auth state changes and updates accordingly
- Provides `signIn`, `signUp`, and `signOut` methods
- Company information is fetched after successful authentication
- Wraps the entire application to ensure auth state is available everywhere

**Usage:**

```tsx
import { useAuth } from '../state/context/AuthContext';

function MyComponent() {
  const { user, company, signOut } = useAuth();
  // ...
}
```

## QueryProvider.tsx

`QueryProvider` configures TanStack React Query for the application.

**Configuration:**

- Sets up the `QueryClient` with default options for stale time, retry behavior, and refetch policies
- Wraps the application tree to provide the query client to all components
- Enables React Query Devtools in development mode

**Conventions:**

- All API data fetching uses `useQuery` or `useMutation` hooks
- Query keys follow the pattern `['resource', ...params]` (e.g., `['robots']`, `['robot', robotId]`)
- Mutations invalidate related queries on success to keep the UI in sync
- Loading and error states from queries are handled at the component level

## State Flow Summary

```
┌─────────────────────────────────────────────┐
│              AuthContext                     │
│  (user, session, company)                   │
├─────────────────────────────────────────────┤
│              SessionContext                  │
│  (currentPhase, answers, selectedRobotId,   │
│   greenlightState)                          │
├─────────────────────────────────────────────┤
│              QueryProvider                   │
│  (React Query: robots, ROI data, etc.)      │
├─────────────────────────────────────────────┤
│              App.tsx + Components            │
└─────────────────────────────────────────────┘
```

Context state flows downward through providers. Components read context via hooks and dispatch updates through context actions. Server data is accessed through React Query hooks, which handle caching and background refetching independently.
