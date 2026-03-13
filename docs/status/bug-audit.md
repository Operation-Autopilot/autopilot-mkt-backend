---
title: Bug Audit — March 2026
---

# Bug Audit — March 2026

Comprehensive analysis of all known bugs across git history, frontend code, and backend code. 73 issues tracked in DMMS, categorized by severity and user impact, organized into a 7-sprint fix plan.

> **Note:** The initial audit identified 60 bugs. 13 additional issues were filed during subsequent development sprints — see [Issues Tracker](./issues.md) for the full registry with live status.

<div class="stats-grid">
  <div class="stat-card"><div class="stat-value">73</div><div class="stat-label">Bugs Found</div></div>
  <div class="stat-card"><div class="stat-value">18</div><div class="stat-label">Critical</div></div>
  <div class="stat-card"><div class="stat-value">21</div><div class="stat-label">High</div></div>
  <div class="stat-card"><div class="stat-value">29</div><div class="stat-label">Medium</div></div>
  <div class="stat-card"><div class="stat-value">5</div><div class="stat-label">Low</div></div>
  <div class="stat-card"><div class="stat-value">25</div><div class="stat-label">Resolved</div></div>
  <div class="stat-card"><div class="stat-value">48</div><div class="stat-label">Open</div></div>
</div>

→ See **[Issues Tracker](./issues.md)** for the full bug registry with live status.
→ See **[Sprints](./sprints.md)** for the 7-sprint fix queue.

---

## Why Workflow-Rooted?

Most bugs in this system are **interaction bugs** — they only surface when specific sequences of events happen (e.g., answer → sign up mid-flow → return → checkout). File-by-file fixes miss these.

This audit organizes bugs by the user journey they break, not the file they live in.

---

## User Workflows & Decision Trees

### W1 — Anonymous Discovery → ROI

```
[Land on site]
    ↓
[Chat loads — greeting appears]
    ├── E-07 ✅ FIXED: greeting regenerated on refresh (8s load)
    ├── E-03 ❌ OPEN: blank chat if backend returns 0 messages
    ↓
[Answer discovery questions via chips / free text]
    ├── E-06 ✅ FIXED: company name re-asked every message
    ├── E-09 ✅ FIXED: agent assumes facility type without asking
    ├── E-11 ❌ OPEN: token budget warning fires too late
    ↓
[4+ answers → "Show Me" chip appears]
    ↓
[Click "Show Me" → transition to ROI]
    ├── E-01 ❌ OPEN: isTransitioningRef stuck if error → can't retry
    ↓
[ROI page loads — recommendations ranked]
    ├── B-02 ✅ FIXED: wrong robot recommended for <$2k spend
    ├── B-03 ✅ FIXED: unknown spend → $0 ROI (now uses hourly rate / facility benchmarks)
    ├── B-01 ❌ OPEN: robot at exact budget midpoint penalized (-15)
    ├── B-07 ✅ FIXED: robots silently dropped on UUID parse failure
    ├── F-02 ❌ OPEN: ROI value race condition (two concurrent fetches)
    ├── F-03 ✅ FIXED: coverageRate null crash (transformer always returns number)
    ↓
[Top robot auto-selected (lime ring)]
    ├── C-01 ✅ FIXED: stale robot from prior session shown instead
    ↓
[User browses / toggles monthly↔yearly]
    ├── F-01 ❌ OPEN: timeframe prop not synced after programmatic change
    ↓
[Proceed to Greenlight →]
    ├── D-03 ❌ OPEN: crash if robot catalog empty (no null guard)
```

---

### W2 — Anonymous → Signs Up Mid-Flow → Checkout

```
[In ROI or Greenlight, not signed in]
    ↓
[Clicks profile icon → signup modal]
    ├── C-04 ✅ FIXED: phase not preserved through signup
    ↓
[Signs up → tokens stored → modal closes]
    ├── C-05 ✅ FIXED: company null if API response missing company_id
    ↓
[Session claimed → discovery data transferred]
    ├── C-07 ✅ FIXED: extraction races claim (atomic signup + inline extraction + redirect guard)
    ├── C-08 ❌ OPEN: conversation transfer unverified (silent failure)
    ├── E-10 ✅ FIXED: background extraction updates anonymous session post-claim
    ↓
[Returned to correct phase]
    ↓
[Selects payment method, clicks checkout]
    ├── D-01 ❌ OPEN: Stripe double-submit (two rapid clicks)
    ├── D-02 ✅ FIXED: auth race → checkout never fires after signup
    ├── D-07 ❌ OPEN: monthly lease (card) checkout disabled
    ↓
[Redirected to Stripe / Gynger]
    ├── A-02 ✅ FIXED: anonymous checkout may use wrong Stripe env
    ↓
[Returns to /checkout/success]
    └── Confirmation shown ✅
```

---

### W3 — Return Authenticated User (Logout → Login)

```
[Was authenticated, logs out]
    ├── C-09 ❌ OPEN: logout cleanup in two places can diverge
    ├── C-03 ✅ FIXED: conversation_id not cleared → different user picks it up
    ↓
[Logs back in]
    ├── C-02 ✅ FIXED: chat history not restored after re-login
    ├── C-12 ✅ FIXED: login fails if discovery profile doesn't exist
    ↓
[Previous session loaded — answers appear]
    ├── C-13 ❌ OPEN: session cache written to stale auth key
    ↓
[ROI page — correct robot selected]
    ├── C-01 ✅ FIXED: stale robot from old session shown
    ↓
[Chat shows previous messages ✅]
    ├── C-10 ❌ OPEN: stale conversation_id survives 401/403
```

---

### W4 — Reset Session ("Start Over")

```
[User types "restart" or clicks reset button]
    ├── E-02 ❌ OPEN: exact match only — "Start Over" (capitalized) ignored
    ↓
[handleResetSession fires]
    ├── E-04 ❌ OPEN: UI cleared before API call — blank on failure
    ├── E-05 ❌ OPEN: old conversation ID not cleared in localStorage first
    ↓
[Backend session cleared]
    ├── C-01 ✅ FIXED: selectedRobotId not cleared (stale lime ring)
    ↓
[New greeting generated → fresh session ✅]
```

---

### W5 — Manual Answer Edit → ROI Re-evaluation

```
[User edits an answer card in profile panel]
    ↓
[Answer synced to backend → cache busted]
    ├── B-04 ✅ FIXED: stale cache not invalidated on answer change
    ↓
[User navigates to ROI]
    ├── F-05 ❌ OPEN: marketplace filters don't re-apply for new sqft
    ├── B-10 ❌ OPEN: ROI ignores selected robot from greenlight session
    ↓
[New recommendations ranked from fresh data ✅]
```

---

### W6 — Greenlight Team Invitation

```
[User enters team member emails]
    ↓
[Clicks "Send Invites"]
    ├── D-04 ❌ OPEN: spinner never stops if invitation fails after signup
    ├── D-05 ❌ OPEN: inputs cleared before API confirms success
    ↓
[Email sent, member added to company]
    └── Invite in company_members table ✅
```

---

## Bug Categories

### A — Security / Data Integrity (5 bugs)

| ID | Title | Sev | Status |
|----|-------|-----|--------|
| A-01 | Session claim no ownership validation | <span class="badge-critical">critical</span> | <span class="badge-open">open</span> |
| A-02 | is_test_account=None → wrong Stripe env | <span class="badge-critical">critical</span> | <span class="badge-completed">resolved</span> |
| A-03 | Stripe webhook replay | <span class="badge-critical">critical</span> | <span class="badge-completed">resolved</span> |
| A-04 | Mutable default BackgroundTasks | <span class="badge-critical">critical</span> | <span class="badge-completed">resolved</span> |
| A-05 | DualAuth never rejects unauthenticated | <span class="badge-high">high</span> | <span class="badge-open">open</span> |

### B — Recommendation & ROI Logic (10 bugs)

See [Issues Tracker](./issues.md) — filter category ROI.

Key open items: dead `elif` in budget scoring (B-01). B-03 (unknown spend) and B-07 (UUID parse failure) resolved.

### C — Auth & Session Transitions (14 bugs)

Largest category. 8 resolved (C-02, C-03, C-04, C-05, C-07, C-10, C-12 + auth token race), 6 still open.
Key pattern: state scattered across backend, SessionContext, localStorage, and AuthContext — multiple sync points without clear ownership.

### D — Checkout & Payment (7 bugs)

D-02 (auth race on checkout) resolved. 2 still critical-adjacent: Stripe double-submit (D-01) and monthly lease disabled (D-07).

### E — Chat / Agent (12 bugs)

5 high-severity resolved (greeting regeneration, 30s latency, extraction blocking, background extraction race, inline extraction). 7 remain open, mostly around state machine reliability.

### F — Display (8 bugs)

F-03 (`coverageRate` null crash) resolved. Rest are medium/low UX issues.

### G — Infrastructure (4 bugs)

G-04 (silent extraction failures) resolved. 3 remain open: session expiry duplication (G-01), cache race (G-02), wrong message count (G-03).

---

## 7-Sprint Fix Plan

Bugs marked ✅ have been resolved. Remaining bugs in each sprint are still planned.

| Sprint | Focus | Bugs | Status |
|--------|-------|------|--------|
| 1 | Security & Payment | A-01, ~~A-02~~ ✅, A-05, D-01, D-03 | <span class="badge-planned">planned</span> |
| 2 | Recommendation Quality | B-01, ~~B-03~~ ✅, ~~B-07~~ ✅, B-10 | <span class="badge-planned">planned</span> |
| 3 | Auth & Session Transitions | ~~C-07~~ ✅, C-08, C-09, ~~C-10~~ ✅, ~~C-12~~ ✅, C-13, C-14 | <span class="badge-planned">planned</span> |
| 4 | Chat & Agent State | E-01, E-02, E-04, E-05, ~~E-10~~ ✅ | <span class="badge-planned">planned</span> |
| 5 | ROI & Marketplace Display | F-01, F-02, ~~F-03~~ ✅, F-05, F-06 | <span class="badge-planned">planned</span> |
| 6 | Checkout Edge Cases | ~~D-02~~ ✅, D-04, D-05, D-06, D-07 | <span class="badge-planned">planned</span> |
| 7 | Infrastructure & Polish | G-01, G-02, G-03, ~~G-04~~ ✅, B-08, F-07, F-08 | <span class="badge-planned">planned</span> |

---

## Test User Profiles (Regression Suite)

Each profile should produce a deterministic, correct recommendation after Sprint 2:

| Profile | Inputs | Expected #1 Robot |
|---------|--------|-------------------|
| Pickleball Club | type=club, method=sweep, spend=<$2k, sqft=8000 | CC1 or C40 |
| Warehouse | type=warehouse, method=vacuum, spend=$5-10k, sqft=50000 | T7AMR or T380AMR |
| Hospital | type=healthcare, method=mop, spend=$2-5k, sqft=20000 | Neo 2W or Phantas |
| Restaurant | type=restaurant, method=sweep, spend=$2-5k, sqft=3000 | Phantas or CC1 |
| School | type=school, method=sweep, spend=<$2k, sqft=15000 | CC1 or Kas |

---

## Recurring Bug Patterns

**1. State scattered across 4 locations** (33 bugs, ~55%)
Backend DB ↔ SessionContext ↔ localStorage ↔ AuthContext — no single source of truth.
Every auth transition is a potential desync.

**2. Async ordering without guarantees** (12 bugs, ~20%)
Multiple operations fire concurrently without coordination (extraction vs claim, double-submit, chat init vs session load).

**3. Silent failures** (8 bugs, ~13%)
Errors are swallowed or logged but not surfaced — UUID drops, extraction failures, conversation transfer misses.

**4. Hardcoded defaults** (4 bugs, ~7%)
Same value in multiple places (session expiry, spend defaults) — diverges when one is updated.
