<script setup>
import { ref, defineAsyncComponent } from 'vue'

const activeTab = ref('journey')

const tabs = [
  { id: 'journey',  label: 'User Journey' },
  { id: 'features', label: 'Features' },
  { id: 'data',     label: 'Data & State' },
  { id: 'api',      label: 'API Reference' },
]

const UserJourneyMap = defineAsyncComponent(() =>
  import('./flow/diagrams/UserJourneyMap.vue')
)

// ── Tab 1: Phase banner + transitions ────────────────────────────────────────

const phases = [
  {
    name: 'Discovery',
    badge: 'badge-active',
    desc: 'AI chat collects facility context via 7 guided questions. Answers are stored in session state and drive all downstream calculations.',
    details: ['Chat Q&A with quick-reply chips', '7 answer keys (sqft, spend, method…)', '≥ 4 answers needed to proceed', 'Data lives in sessions.answers JSONB'],
  },
  {
    name: 'ROI',
    badge: 'badge-planned',
    desc: 'Backend scores all 13 robots against the collected answers and returns a ranked top-3 with match % and projected savings.',
    details: ['Recommendation scoring (deterministic)', 'ROI formula: min(gross + efficiency, cost)', 'Monthly / yearly toggle', 'User picks robot → persisted to session'],
  },
  {
    name: 'Greenlight',
    badge: 'badge-completed',
    desc: 'User reviews their robot selection, optionally invites team members, chooses a payment method, and proceeds to checkout.',
    details: ['Auth required before checkout', 'Stripe (purchase) or Gynger (financing)', 'Team invite via email (Resend)', 'Session claimed → discovery_profiles'],
  },
]

const transitions = [
  {
    from: 'Discovery',
    to: 'ROI',
    trigger: 'Click "Show Me" chip',
    condition: '≥ 4 of 7 answers filled',
    fires: 'generateTransitionMessage() + setPhase(ROI)',
  },
  {
    from: 'ROI',
    to: 'Greenlight',
    trigger: 'Click "Proceed to Greenlight →"',
    condition: 'selectedRobotId is set',
    fires: 'setPhase(GREENLIGHT)',
  },
  {
    from: 'Greenlight',
    to: 'Auth modal',
    trigger: 'Click "Proceed to Checkout"',
    condition: 'Not authenticated',
    fires: 'savePhaseForAuthTransition() + show signup modal',
  },
  {
    from: 'Auth modal',
    to: 'Greenlight',
    trigger: 'Signup / login complete',
    condition: 'isAuthenticated = true',
    fires: 'POST /sessions/claim + restore pending phase',
  },
  {
    from: 'Any',
    to: 'Discovery',
    trigger: '"Start Over" / "restart" / "reset"',
    condition: 'Any phase',
    fires: 'Session reset → phase = DISCOVERY, answers = {}',
  },
]

// ── Tab 2: Features ───────────────────────────────────────────────────────────

const features = [
  {
    label: 'CHAT',
    name: 'Discovery Chat',
    sees: [
      'Right-column chat panel (desktop) / FAB + bottom sheet (mobile)',
      'Quick-reply chips below each message',
      'AI asks questions one by one',
    ],
    happens: [
      'POST /conversations/{id}/messages',
      'Response includes chips + discoveryState',
      'ready_for_roi=true → injects "Show Me" chip',
      'Async task extracts answers → sessions.answers JSONB',
    ],
  },
  {
    label: 'BOT',
    name: 'Robot Marketplace',
    sees: [
      'Left-column grid of 13 robot cards',
      'Filter panel: price, size, method, environment, navigation',
      'Click card → flip → specs; "Select Unit" button',
    ],
    happens: [
      'GET /robots (public, no auth)',
      'Select → onRobotSelect() → PUT /sessions/me',
      'GET /robots/filters for filter metadata',
      'Selected robot shown with lime ring in ROI view',
    ],
  },
  {
    label: 'PROF',
    name: 'Profile Panel',
    sees: [
      'Editable answer cards grouped by Company, Facility, Operations, Economics, Context',
      'Middle column (desktop) / "Profile" tab (mobile)',
    ],
    happens: [
      'Renders from session.answers',
      'Edit → updateAnswer(key, answer) → PUT /sessions/me',
      'Changes immediately invalidate ROI cache',
      'Auth users: PUT /discovery instead',
    ],
  },
  {
    label: 'ROI',
    name: 'ROI View',
    sees: [
      'Top-3 robots ranked by match score (0–100 %)',
      'Labels: RECOMMENDED / BEST VALUE / UPGRADE / ALTERNATIVE',
      'Savings breakdown: current cost → net savings → hours saved',
      'Monthly / yearly toggle',
    ],
    happens: [
      'POST /roi/recommendations/session (anon) or /discovery (auth)',
      'POST /roi/calculate for selected robot',
      'net_savings = min(gross + efficiency_bonus, cost)',
      'Auth: results cached 1 hr (keyed by answers_hash SHA-256)',
    ],
  },
  {
    label: 'CHKOUT',
    name: 'Greenlight / Checkout',
    sees: [
      'Selected robot summary + savings recap',
      'Team invite form',
      '"Purchase Outright" (Stripe) or "Finance with Gynger"',
    ],
    happens: [
      'Stripe: POST /checkout/session → window.location.href',
      'Gynger: open blank tab sync → POST /checkout/gynger-session → new tab',
      'Order row created (status: pending) before redirect',
      'Webhook → order status → completed / payment_pending',
    ],
  },
  {
    label: 'AUTH',
    name: 'Auth (Signup / Login)',
    sees: [
      'Top-right profile button: anon → signup modal; auth → dropdown',
      'Signup: email, password, display name, company name',
    ],
    happens: [
      'POST /auth/signup → profiles + company row',
      'POST /auth/login → JWT tokens (skips email verify)',
      'Tokens in localStorage: autopilot_auth_tokens/user/company',
      'POST /sessions/claim → merges anon session → discovery_profiles',
    ],
  },
  {
    label: 'FLOOR',
    name: 'Floor Plan Upload',
    sees: [
      'Upload image option during discovery',
      'After analysis: sqft + monthly_spend auto-populated',
    ],
    happens: [
      'POST /floor-plans/analyze (multipart, ≤ 10 MB)',
      'Image stored in Supabase Storage (robot-images bucket)',
      'GPT-4o Vision → zones, dimensions, surfaces',
      'Result cached in localStorage (max 2 MB)',
    ],
  },
  {
    label: 'TEAM',
    name: 'Company & Team',
    sees: [
      'Company created automatically on signup',
      'Team member list; "Invite by email" button',
    ],
    happens: [
      'POST /companies/{id}/invitations → email via Resend',
      'POST /invitations/{id}/accept → company_members row',
      'Only owner role can invite or remove members',
      'Role enforcement (Owner vs GM) is not yet implemented',
    ],
  },
]

// ── Tab 3: Data & State ───────────────────────────────────────────────────────

const localStorageKeys = [
  { key: 'autopilot_session_token',         stores: '64-char anonymous session token',      owner: 'SessionContext', cleared: 'No — session persists',   note: 'Stored as SHA-256 hash in DB' },
  { key: 'autopilot_conversation_id',        stores: 'Chat conversation UUID',               owner: 'Chat',           cleared: 'No',                     note: 'Fallback: GET /conversations/current' },
  { key: 'autopilot_auth_tokens',            stores: 'JWT access + refresh tokens',          owner: 'AuthContext',    cleared: 'Yes',                    note: '' },
  { key: 'autopilot_auth_user',              stores: 'User profile (id, email, name)',       owner: 'AuthContext',    cleared: 'Yes',                    note: '' },
  { key: 'autopilot_auth_company',           stores: 'Company data',                         owner: 'AuthContext',    cleared: 'Yes',                    note: '' },
  { key: 'autopilot_pending_phase',          stores: 'Phase to restore after auth',          owner: 'Auth transition',cleared: 'After restore',          note: 'Set before signup modal opens' },
  { key: 'autopilot_floor_plan_analysis',    stores: 'Floor plan result JSON',               owner: 'Floor plan',     cleared: 'On session reset',       note: 'Max 2 MB; skipped if larger' },
]

const dbTables = [
  { table: 'sessions',             stores: 'Anonymous state: answers, phase, robot selection, greenlight JSONB', linkedTo: 'conversations, orders' },
  { table: 'discovery_profiles',   stores: 'Authenticated state (mirrors sessions), cached_recommendations',    linkedTo: 'profiles, conversations' },
  { table: 'robot_catalog',        stores: '22 robots (13 active), Stripe IDs, pricing, specs',                 linkedTo: 'orders (via line_items)' },
  { table: 'conversations',        stores: 'Chat metadata (conversation ID, profile/session FK)',                linkedTo: 'sessions or discovery_profiles' },
  { table: 'messages',             stores: 'Chat messages (role, content, timestamp)',                          linkedTo: 'conversations' },
  { table: 'orders',               stores: 'Checkout: status, payment_provider, line_items JSONB, Stripe/Gynger IDs', linkedTo: 'sessions, profiles' },
  { table: 'profiles',             stores: 'User profiles (1:1 with auth.users), is_test_account',             linkedTo: 'discovery_profiles, companies' },
  { table: 'companies',            stores: 'Company records',                                                   linkedTo: 'profiles via company_members' },
  { table: 'floor_plan_analysis',  stores: 'Upload metadata + GPT-4o Vision results (zones, dimensions)',      linkedTo: 'sessions or profiles' },
]

const stateMatrix = [
  { field: 'currentPhase',        reactState: true,  localStorage: 'autopilot_pending_phase (auth only)',  sessions: 'sessions.phase', discovery: 'discovery_profiles.phase' },
  { field: 'answers (all keys)',  reactState: true,  localStorage: '—',                                    sessions: 'sessions.answers JSONB', discovery: 'discovery_profiles.answers JSONB' },
  { field: 'selectedRobotId',     reactState: true,  localStorage: '—',                                    sessions: 'sessions.selected_product_ids[0]', discovery: 'discovery_profiles.selected_product_ids[0]' },
  { field: 'conversationId',      reactState: true,  localStorage: 'autopilot_conversation_id',            sessions: 'sessions.conversation_id', discovery: 'discovery_profiles.conversation_id' },
  { field: 'greenlight answers',  reactState: true,  localStorage: '—',                                    sessions: 'sessions.greenlight JSONB', discovery: 'discovery_profiles.greenlight JSONB' },
  { field: 'session token',       reactState: true,  localStorage: 'autopilot_session_token',              sessions: 'sessions.session_token (hash)', discovery: '— (not needed after claim)' },
  { field: 'floor plan result',   reactState: true,  localStorage: 'autopilot_floor_plan_analysis',        sessions: '—', discovery: 'discovery_profiles.answers (sqft, spend merged in)' },
  { field: 'recommendations',     reactState: true,  localStorage: '—',                                    sessions: '—', discovery: 'discovery_profiles.cached_recommendations (1 hr TTL)' },
]

// ── Tab 4: API Reference ──────────────────────────────────────────────────────

const apiEndpoints = [
  { what: 'Get / create session',          endpoint: 'GET / POST /sessions/me',                   auth: 'Anonymous (X-Session-Token)' },
  { what: 'Update session',                endpoint: 'PUT /sessions/me',                          auth: 'Anonymous' },
  { what: 'Claim session after login',     endpoint: 'POST /sessions/claim',                      auth: 'JWT + session token' },
  { what: 'Auth discovery profile',        endpoint: 'GET / PUT /discovery',                      auth: 'JWT' },
  { what: 'Send chat message',             endpoint: 'POST /conversations/{id}/messages',          auth: 'Either' },
  { what: 'Phase transition message',      endpoint: 'POST /conversations/{id}/transition',        auth: 'Either' },
  { what: 'List robots',                   endpoint: 'GET /robots',                               auth: 'None' },
  { what: 'Robot filter metadata',         endpoint: 'GET /robots/filters',                       auth: 'None' },
  { what: 'Recommendations (anon)',        endpoint: 'POST /roi/recommendations/session',          auth: 'Anonymous' },
  { what: 'Recommendations (auth)',        endpoint: 'POST /roi/recommendations/discovery',        auth: 'JWT' },
  { what: 'Calculate ROI',                 endpoint: 'POST /roi/calculate',                       auth: 'Either' },
  { what: 'Stripe checkout',               endpoint: 'POST /checkout/session',                    auth: 'Either' },
  { what: 'Gynger financing',              endpoint: 'POST /checkout/gynger-session',             auth: 'Either' },
  { what: 'Analyze floor plan',            endpoint: 'POST /floor-plans/analyze',                 auth: 'Either' },
  { what: 'Signup',                        endpoint: 'POST /auth/signup',                         auth: 'None' },
  { what: 'Login',                         endpoint: 'POST /auth/login',                          auth: 'None' },
]

const debuggingScenarios = [
  {
    symptom: 'Robot not selected / no robot shown in ROI',
    causes: [
      'selectedRobotId === "" — auto-select fires only in ROIView when empty + recs loaded',
      'Check sessions.selected_product_ids in DB',
    ],
  },
  {
    symptom: 'Wrong savings numbers',
    causes: [
      'Savings come from POST /roi/calculate, not the frontend',
      'Fallback if answers missing: currentMonthlyCost = 4330',
      'Check monthly_spend and duration/frequency answer keys in session',
    ],
  },
  {
    symptom: 'Phase not advancing (stuck on Discovery)',
    causes: [
      'ready_for_roi requires ≥ 4 answers — check sessions.answers for null/empty keys',
      'Greenlight requires selectedRobotId to be non-empty',
    ],
  },
  {
    symptom: 'Stuck at signup modal before checkout',
    causes: [
      'Check localStorage autopilot_pending_phase',
      'After login: SessionContext effect restores it',
      'If missing: phase was not saved before modal opened',
    ],
  },
  {
    symptom: 'Checkout not redirecting (Stripe)',
    causes: [
      'window.location.href — not blocked by popups',
      '5 s timeout resets spinner if redirect fails',
      'Check for checkout_url in POST /checkout/session response',
    ],
  },
  {
    symptom: 'Checkout not redirecting (Gynger)',
    causes: [
      'Tab opened synchronously BEFORE API call — popup blockers can still block it',
      'Falls back to same-tab redirect if popup was blocked',
      'Check for application_url in POST /checkout/gynger-session response',
    ],
  },
  {
    symptom: 'Chat broken / no response',
    causes: [
      'Check localStorage autopilot_conversation_id — invalid UUID falls back to GET /conversations/current',
      'Rate limits: 15 req/min (anon), 100/min (auth)',
      'Token budget exhausted: 75 k/day (anon), 250 k/day (auth)',
    ],
  },
  {
    symptom: 'Recommendations not loading',
    causes: [
      'Need ≥ 1 answer in session for scoring to run',
      'Auth cache: 1 hr TTL keyed by answers_hash — answer changes bust cache',
      'Check discovery_profiles.cached_recommendations in DB',
    ],
  },
]
</script>

<template>
  <div class="context-map-page">

    <!-- Tab bar -->
    <div class="cm-tab-bar">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        :class="['cm-tab-btn', { active: activeTab === tab.id }]"
        @click="activeTab = tab.id"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- ── Tab 1: User Journey ── -->
    <div v-show="activeTab === 'journey'" class="cm-tab-content">

      <div class="stats-grid cm-phase-banner">
        <div v-for="phase in phases" :key="phase.name" class="stat-card cm-phase-card">
          <div class="stat-value">
            <span :class="['badge', phase.badge]">{{ phase.name }}</span>
          </div>
          <div class="stat-label">{{ phase.desc }}</div>
          <ul class="cm-phase-details">
            <li v-for="d in phase.details" :key="d">{{ d }}</li>
          </ul>
        </div>
      </div>

      <h3>Flow Diagram</h3>
      <ClientOnly>
        <UserJourneyMap />
        <template #fallback>
          <div class="cm-diagram-loading">Loading diagram&hellip;</div>
        </template>
      </ClientOnly>

      <h3>Phase Transitions</h3>
      <table class="dmms-table">
        <thead>
          <tr>
            <th>From</th>
            <th>To</th>
            <th>Trigger</th>
            <th>Condition</th>
            <th>What fires</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in transitions" :key="t.from + t.to">
            <td><code>{{ t.from }}</code></td>
            <td><code>{{ t.to }}</code></td>
            <td>{{ t.trigger }}</td>
            <td>{{ t.condition }}</td>
            <td><code>{{ t.fires }}</code></td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- ── Tab 2: Features ── -->
    <div v-show="activeTab === 'features'" class="cm-tab-content">
      <div class="cm-features-grid">
        <div v-for="f in features" :key="f.name" class="cm-feature-card">
          <div class="cm-feature-header">
            <span class="cm-feature-label">{{ f.label }}</span>
            <span class="cm-feature-name">{{ f.name }}</span>
          </div>
          <div class="cm-feature-body">
            <div class="cm-feature-section">
              <div class="cm-section-title">What the user sees</div>
              <ul>
                <li v-for="s in f.sees" :key="s">{{ s }}</li>
              </ul>
            </div>
            <div class="cm-feature-section">
              <div class="cm-section-title">What happens</div>
              <ul>
                <li v-for="s in f.happens" :key="s">{{ s }}</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Tab 3: Data & State ── -->
    <div v-show="activeTab === 'data'" class="cm-tab-content">

      <h3>localStorage Keys</h3>
      <table class="dmms-table">
        <thead>
          <tr>
            <th>Key</th>
            <th>Stores</th>
            <th>Owner</th>
            <th>Cleared on logout?</th>
            <th>Note</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="k in localStorageKeys" :key="k.key">
            <td><code>{{ k.key }}</code></td>
            <td>{{ k.stores }}</td>
            <td>{{ k.owner }}</td>
            <td>{{ k.cleared }}</td>
            <td>{{ k.note || '—' }}</td>
          </tr>
        </tbody>
      </table>

      <h3>Database Tables</h3>
      <table class="dmms-table">
        <thead>
          <tr>
            <th>Table</th>
            <th>Stores</th>
            <th>Linked to</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in dbTables" :key="t.table">
            <td><code>{{ t.table }}</code></td>
            <td>{{ t.stores }}</td>
            <td>{{ t.linkedTo }}</td>
          </tr>
        </tbody>
      </table>

      <h3>State Persistence Matrix</h3>
      <table class="dmms-table">
        <thead>
          <tr>
            <th>Field</th>
            <th>React state</th>
            <th>localStorage</th>
            <th>sessions table</th>
            <th>discovery_profiles</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="m in stateMatrix" :key="m.field">
            <td><code>{{ m.field }}</code></td>
            <td>
              <span v-if="m.reactState" class="badge badge-active">yes</span>
              <span v-else class="badge badge-low">no</span>
            </td>
            <td>{{ m.localStorage }}</td>
            <td>{{ m.sessions }}</td>
            <td>{{ m.discovery }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- ── Tab 4: API Reference ── -->
    <div v-show="activeTab === 'api'" class="cm-tab-content">

      <h3>API Quick Reference</h3>
      <table class="dmms-table">
        <thead>
          <tr>
            <th>What</th>
            <th>Endpoint</th>
            <th>Auth method</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="e in apiEndpoints" :key="e.endpoint">
            <td>{{ e.what }}</td>
            <td><code>{{ e.endpoint }}</code></td>
            <td>{{ e.auth }}</td>
          </tr>
        </tbody>
      </table>

      <h3>Common Debugging Scenarios</h3>
      <details
        v-for="s in debuggingScenarios"
        :key="s.symptom"
        class="cm-debug-detail"
      >
        <summary>{{ s.symptom }}</summary>
        <ul>
          <li v-for="c in s.causes" :key="c">{{ c }}</li>
        </ul>
      </details>
    </div>

  </div>
</template>

<style scoped>
/* Tab bar */
.cm-tab-bar {
  display: flex;
  gap: 0;
  border-bottom: 2px solid var(--vp-c-divider);
  margin-bottom: 1.5rem;
  overflow-x: auto;
}

.cm-tab-btn {
  padding: 0.6rem 1.25rem;
  font-size: 0.875rem;
  font-weight: 600;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  color: var(--vp-c-text-2);
  cursor: pointer;
  white-space: nowrap;
  transition: color 0.15s, border-color 0.15s;
}

.cm-tab-btn:hover {
  color: var(--vp-c-text-1);
}

.cm-tab-btn.active {
  color: var(--vp-c-brand-1);
  border-bottom-color: var(--vp-c-brand-1);
}

/* Tab content */
.cm-tab-content {
  padding: 0.25rem 0;
}

/* Phase banner */
.cm-phase-banner {
  grid-template-columns: repeat(3, 1fr);
  margin-bottom: 1.5rem;
}

.cm-phase-card {
  text-align: left;
  padding: 1rem 1.25rem;
}

.cm-phase-card .stat-value {
  margin-bottom: 0.5rem;
}

.cm-phase-card .stat-label {
  font-size: 0.8rem;
  line-height: 1.5;
  color: var(--vp-c-text-2);
  text-transform: none;
  letter-spacing: 0;
  margin-bottom: 0.75rem;
}

.cm-phase-details {
  margin: 0;
  padding-left: 1.1rem;
  font-size: 0.78rem;
  color: var(--vp-c-text-3);
  line-height: 1.6;
}

/* Diagram loading state */
.cm-diagram-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 450px;
  background: var(--vp-c-bg-alt);
  border-radius: 8px;
  color: var(--vp-c-text-3);
  font-style: italic;
}

/* Features grid */
.cm-features-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}

@media (max-width: 768px) {
  .cm-features-grid {
    grid-template-columns: 1fr;
  }
  .cm-phase-banner {
    grid-template-columns: 1fr;
  }
}

.cm-feature-card {
  border: 1px solid var(--vp-c-divider);
  border-radius: 8px;
  overflow: hidden;
  background: var(--vp-c-bg-soft);
}

.cm-feature-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  background: var(--vp-c-bg-alt);
  border-bottom: 1px solid var(--vp-c-divider);
}

.cm-feature-label {
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--vp-c-brand-1);
  background: color-mix(in srgb, var(--vp-c-brand-1) 12%, transparent);
  padding: 0.15rem 0.45rem;
  border-radius: 3px;
  white-space: nowrap;
}

.cm-feature-name {
  font-weight: 600;
  font-size: 0.9rem;
  color: var(--vp-c-text-1);
}

.cm-feature-body {
  padding: 0.75rem 1rem;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem 1rem;
}

.cm-section-title {
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--vp-c-text-3);
  margin-bottom: 0.35rem;
}

.cm-feature-body ul {
  margin: 0;
  padding-left: 1rem;
  font-size: 0.8rem;
  color: var(--vp-c-text-2);
  line-height: 1.6;
}

/* Debugging details */
.cm-debug-detail {
  border: 1px solid var(--vp-c-divider);
  border-radius: 6px;
  margin-bottom: 0.5rem;
  background: var(--vp-c-bg-soft);
  overflow: hidden;
}

.cm-debug-detail summary {
  padding: 0.75rem 1rem;
  cursor: pointer;
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--vp-c-text-1);
  list-style: none;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  user-select: none;
}

.cm-debug-detail summary::before {
  content: '\25B6';
  font-size: 0.6rem;
  color: var(--vp-c-brand-1);
  transition: transform 0.15s;
}

.cm-debug-detail[open] summary::before {
  transform: rotate(90deg);
}

.cm-debug-detail ul {
  margin: 0;
  padding: 0.5rem 1rem 0.75rem 2rem;
  font-size: 0.82rem;
  color: var(--vp-c-text-2);
  line-height: 1.7;
  border-top: 1px solid var(--vp-c-divider);
  background: var(--vp-c-bg);
}
</style>
