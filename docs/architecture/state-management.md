# Frontend State Management

The frontend uses a combination of React Context for client-side state and TanStack React Query for server state. This separation keeps the codebase clean: Context handles ephemeral UI and session state, while React Query manages cached server data with automatic refetching and synchronization.

## Architecture Overview

<StateProviders />

<details>
<summary>Text fallback</summary>

```
QueryClientProvider → AuthProvider → SessionProvider → App Routes
```

</details>

## React Context Providers

### AuthContext

Manages user authentication state via Supabase Auth. Provides the current user object, auth loading state, and sign-in/sign-out methods.

```typescript
// src/context/AuthContext.tsx

interface AuthContextType {
  user: User | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Listen for Supabase auth state changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        setUser(session?.user ?? null);
        setLoading(false);
      }
    );
    return () => subscription.unsubscribe();
  }, []);

  // ... signIn, signUp, signOut implementations

  return (
    <AuthContext.Provider value={{ user, loading, signIn, signUp, signOut }}>
      {children}
    </AuthContext.Provider>
  );
};
```

### SessionContext

Tracks the current procurement session state: which phase the user is in, their accumulated answers, the selected robot, and greenlight status.

```typescript
// src/context/SessionContext.tsx

interface SessionContextType {
  sessionId: string | null;
  currentPhase: "discovery" | "roi" | "greenlight";
  answers: Record<string, any>;
  selectedRobotId: string | null;
  greenlightState: GreenlightState;
  setPhase: (phase: string) => void;
  updateAnswers: (updates: Record<string, any>) => void;
  selectRobot: (robotId: string) => void;
  resetSession: () => void;
}

export const SessionProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [currentPhase, setCurrentPhase] = useState<Phase>("discovery");
  const [answers, setAnswers] = useState<Record<string, any>>({});
  const [selectedRobotId, setSelectedRobotId] = useState<string | null>(null);
  const [greenlightState, setGreenlightState] = useState<GreenlightState>({
    approved: false,
    roiScore: null,
    recommendation: null,
  });

  const updateAnswers = (updates: Record<string, any>) => {
    setAnswers(prev => ({ ...prev, ...updates }));
  };

  // ... other methods

  return (
    <SessionContext.Provider value={{
      sessionId, currentPhase, answers,
      selectedRobotId, greenlightState,
      setPhase: setCurrentPhase,
      updateAnswers, selectRobot: setSelectedRobotId,
      resetSession,
    }}>
      {children}
    </SessionContext.Provider>
  );
};
```

## TanStack React Query

React Query manages all server state: fetching, caching, background refetching, and mutation. The `QueryClientProvider` wraps the app with a configured client.

### Configuration

```typescript
// src/providers/QueryProvider.tsx

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,      // 5 minutes before data is considered stale
      retry: 1,                        // Retry failed requests once
      refetchOnWindowFocus: false,     // Don't refetch on tab focus
    },
  },
});

export const QueryProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <QueryClientProvider client={queryClient}>
    {children}
  </QueryClientProvider>
);
```

### Query Key Conventions

Query keys follow a hierarchical pattern for predictable cache invalidation:

```typescript
// Query key factory
const queryKeys = {
  robots: {
    all: ["robots"] as const,
    detail: (id: string) => ["robots", id] as const,
    catalog: (filters: Filters) => ["robots", "catalog", filters] as const,
  },
  conversations: {
    all: ["conversations"] as const,
    bySession: (sessionId: string) => ["conversations", sessionId] as const,
  },
  sessions: {
    all: ["sessions"] as const,
    detail: (id: string) => ["sessions", id] as const,
  },
};
```

## Custom Hooks

Custom hooks encapsulate query logic and provide clean interfaces to components.

### useConversation

Manages the chat interaction: fetches history and provides a mutation for sending messages.

```typescript
// src/hooks/useConversation.ts

export function useConversation(sessionId: string) {
  const history = useQuery({
    queryKey: queryKeys.conversations.bySession(sessionId),
    queryFn: () => api.getConversationHistory(sessionId),
  });

  const sendMessage = useMutation({
    mutationFn: (message: string) => api.sendMessage(sessionId, message),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.conversations.bySession(sessionId),
      });
    },
  });

  return { history: history.data, isLoading: history.isLoading, sendMessage };
}
```

### useRobots

Fetches and filters the robot catalog.

```typescript
// src/hooks/useRobots.ts

export function useRobots(filters?: RobotFilters) {
  return useQuery({
    queryKey: queryKeys.robots.catalog(filters),
    queryFn: () => api.getRobots(filters),
  });
}
```

### useIsMobile

Responsive breakpoint detection.

```typescript
// src/hooks/useIsMobile.ts

export function useIsMobile(breakpoint = 768) {
  const [isMobile, setIsMobile] = useState(window.innerWidth < breakpoint);

  useEffect(() => {
    const handler = () => setIsMobile(window.innerWidth < breakpoint);
    window.addEventListener("resize", handler);
    return () => window.removeEventListener("resize", handler);
  }, [breakpoint]);

  return isMobile;
}
```

### useTheme

Manages light/dark theme preference.

```typescript
// src/hooks/useTheme.ts

export function useTheme() {
  const [theme, setTheme] = useState<"light" | "dark">(
    () => (localStorage.getItem("theme") as "light" | "dark") ?? "light"
  );

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    localStorage.setItem("theme", theme);
  }, [theme]);

  return { theme, toggleTheme: () => setTheme(t => t === "light" ? "dark" : "light") };
}
```

## Data Flow Between Context and React Query

Context and React Query serve different purposes and interact at defined boundaries:

1. **AuthContext** provides the user token that React Query uses in API calls.
2. **SessionContext** provides the `sessionId` used as a query key parameter.
3. **React Query mutations** may trigger Context updates (e.g., a phase transition API call updates `SessionContext.currentPhase`).

```
AuthContext.user.token ──▶ API client Authorization header ──▶ React Query fetches
SessionContext.sessionId ──▶ Query key parameter ──▶ React Query fetches
React Query mutation success ──▶ SessionContext.setPhase() ──▶ UI re-render
```

This architecture keeps server state (what the backend knows) separate from client state (what the UI needs to render), while ensuring they stay synchronized.
