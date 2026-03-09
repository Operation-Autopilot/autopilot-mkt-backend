---
title: Frontend Testing
---

# Frontend Testing

The frontend test suite uses **Vitest** as the test runner, **React Testing Library** for rendering and interacting with components, and **MSW (Mock Service Worker)** for API mocking.

## Running Tests

```bash
# Run the full suite
npm test

# Run in watch mode (re-runs on file changes)
npm run test:watch

# Run a specific file
npx vitest run src/components/Chat.test.tsx

# Run with coverage
npx vitest run --coverage
```

## Vitest Configuration

Vitest is configured with the `jsdom` environment so that DOM APIs are available in tests. Configuration lives in `vite.config.ts` or a dedicated `vitest.config.ts`:

```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
  },
});
```

## React Testing Library

Components are tested by rendering them and asserting on what the user sees, not on internal implementation details:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ProfileCard } from "./ProfileCard";

test("displays the company name", () => {
  render(<ProfileCard company="Acme Corp" role="Vendor" />);
  expect(screen.getByText("Acme Corp")).toBeInTheDocument();
});

test("calls onEdit when the edit button is clicked", async () => {
  const handleEdit = vi.fn();
  render(<ProfileCard company="Acme Corp" role="Vendor" onEdit={handleEdit} />);

  await userEvent.click(screen.getByRole("button", { name: /edit/i }));
  expect(handleEdit).toHaveBeenCalledOnce();
});
```

## MSW (Mock Service Worker)

MSW intercepts outgoing HTTP requests at the network level, providing realistic API mocking without patching `fetch` or `axios`.

### Setup

The test setup file (`src/test/setup.ts`) starts and stops the MSW server:

```ts
import { beforeAll, afterAll, afterEach } from "vitest";
import { server } from "./mocks/server";

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

### Defining Handlers

Request handlers are defined in `src/test/mocks/handlers.ts`:

```ts
import { http, HttpResponse } from "msw";

export const handlers = [
  http.get("/api/conversations", () => {
    return HttpResponse.json([
      { id: "conv-1", title: "First conversation" },
      { id: "conv-2", title: "Second conversation" },
    ]);
  }),

  http.post("/api/conversations", async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({ id: "conv-new", ...body }, { status: 201 });
  }),
];
```

### Overriding Handlers Per Test

For specific test scenarios, override handlers within the test:

```ts
import { server } from "../test/mocks/server";
import { http, HttpResponse } from "msw";

test("shows error state when API fails", async () => {
  server.use(
    http.get("/api/conversations", () => {
      return HttpResponse.json({ detail: "Unauthorized" }, { status: 401 });
    })
  );

  render(<ConversationList />);
  expect(await screen.findByText(/unauthorized/i)).toBeInTheDocument();
});
```

## Test File Conventions

- Test files live next to the source files they test: `Component.tsx` and `Component.test.tsx`.
- Shared test utilities and MSW setup live in `src/test/`.
- Use `vi.fn()` for mock functions and `vi.spyOn()` for spying on existing methods.
