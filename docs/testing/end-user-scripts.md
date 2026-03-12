---
title: End-User Testing Scripts
---

# End-User Testing Scripts

Manual end-user testing scripts for the Autopilot Marketplace. Organized by functional area. Fixture data sourced from real HubSpot Closed Won/Lost deals and Fireflies transcripts.

**Priority legend:** **P0** = must pass before any release | **P1** = must pass before customer-facing launch | **P2** = important but can trail

::: tip CSV Available
A CSV version of these scripts is available at [`end-user-scripts.csv`](./end-user-scripts.csv) for import into Google Sheets or other tools.
:::

---

## 1. Anonymous Session & Navigation

| # | Test Case | User Role | Preconditions | Steps | Expected Result | Priority |
|---|-----------|-----------|---------------|-------|-----------------|----------|
| 1 | First visit creates anonymous session | Anonymous | Clean browser, no cookies | Open marketplace URL → wait for page load | Session cookie `sb-session` set; `autopilot_session_token` in localStorage; Discovery phase active; chat greeting appears | P0 |
| 2 | Session persists on page refresh | Anonymous | Active session | Interact with chat (send 1 message) → refresh browser | Same session restored; chat history intact; discovery answers preserved; no duplicate session in DB | P0 |
| 3 | Desktop 3-column layout renders | Anonymous | Desktop viewport (>768px) | Open marketplace at 1280px width | Three columns visible: Marketplace (left) \| Profile (center) \| Chat (right); no overflow or scroll issues | P0 |
| 4 | Progress bar shows Discovery phase | Anonymous | Fresh session | Observe header progress bar | Step 1 "Discovery" highlighted; Steps 2 "ROI" and 3 "Greenlight" dimmed; clicking dimmed steps does nothing | P1 |
| 5 | Direct URL to root loads correctly | Anonymous | No prior session | Navigate directly to `/` | Discovery phase loads; chat panel initializes with greeting; marketplace grid renders with 13 robots | P1 |

---

## 2. Discovery Chat — Success Flows

Uses fixture data from 5 real Closed Won customers. All 7 discovery fields must be completed to unlock ROI.

| # | Test Case | User Role | Preconditions | Steps | Expected Result | Priority |
|---|-----------|-----------|---------------|-------|-----------------|----------|
| 6 | Calabasas PB Club — full discovery (J-01) | Anonymous | Fresh session | Enter via chat: company_name="Calabasas Pickleball Club", company_type="Pickleball Club", courts_count="12+", method="Other", frequency="Daily", duration="4hr", monthly_spend="$2k-$5k" | All 7 answers appear in profile panel; progress reaches 100%; "Show Me" chip appears; chat confirms readiness for ROI | P0 |
| 7 | Pickledilly Skokie — full discovery (J-02) | Anonymous | Fresh session | Enter via chat: company_name="Pickledilly Skokie", company_type="Pickleball Club", courts_count="12+", method="Sweep", frequency="3-4x/week", duration="4hr", monthly_spend="<$2k" | All answers captured; "Show Me" chip appears after 7th answer; profile cards match entered values | P0 |
| 8 | Rally House PBC — full discovery (J-03) | Anonymous | Fresh session | Enter via chat: company_name="Rally House Pickleball Club", company_type="Pickleball Club", courts_count="Other" (11), method="Sweep", frequency="Daily", duration="4hr", monthly_spend="$2k-$5k" | "Other" court count accepted with custom value; all answers stored in session; "Show Me" chip renders | P0 |
| 9 | PickleBOS — full discovery (J-04) | Anonymous | Fresh session | Enter via chat: company_name="PickleBOS", company_type="Pickleball Club", courts_count="Other" (11), method="Sweep", frequency="3-4x/week", duration="2hr", monthly_spend="$2k-$5k" | Discovery completes; "Show Me" chip appears; progress bar at 100% | P1 |
| 10 | Victory Pickleball — full discovery (J-05) | Anonymous | Fresh session | Enter via chat: company_name="Victory Pickleball", company_type="Pickleball Club", courts_count="12+", method="Sweep", frequency="3-4x/week", duration="4hr", monthly_spend="<$2k" | All 7 answers captured correctly; transition chip available | P1 |
| 11 | Discovery → ROI transition via "Show Me" chip | Anonymous | All 7 answers completed | Click "Show Me" chip in chat | Phase transitions to ROI; progress bar updates to step 2; ROI view renders with 3 robot recommendations; chat shows transition message | P0 |
| 12 | Quick-reply chips work for all question types | Anonymous | Fresh session, first question asked | Click chip options instead of typing (e.g., "Pickleball Club", "$2k-$5k", "Daily") | Each chip sends correct value; answer appears in profile panel; next question appears; no duplicate messages | P0 |

---

## 3. Discovery Chat — Failure & Edge Flows

Uses fixture data from 5 real Closed Lost deals. Tests graceful handling of edge-case inputs.

| # | Test Case | User Role | Preconditions | Steps | Expected Result | Priority |
|---|-----------|-----------|---------------|-------|-----------------|----------|
| 13 | Goldcoast PBC — small facility, low spend (J-06) | Anonymous | Fresh session | Enter: company_name="Goldcoast PBC", company_type="Pickleball Club", courts_count="6", method="Sweep", frequency="3-4x/week", duration="2hr", monthly_spend="<$2k" → proceed to ROI | ROI calculator renders without crash; savings may show low/negative values in red text; no blank page or 500 error | P0 |
| 14 | The Peak — zero labor cost inputs (J-09) | Anonymous | Fresh session | Enter: company_name="The Peak", company_type="Pickleball Club", courts_count="6", method="Other" (member labor), frequency="Weekly", duration="1hr", monthly_spend="<$2k" → proceed to ROI | ROI handles zero/minimal spend without NaN or division errors; savings display in red if negative; no undefined values in UI | P0 |
| 15 | Corpus Christi AC — non-target facility type (J-10) | Anonymous | Fresh session | Enter: company_name="Corpus Christi Athletic Club", company_type="Other" (Athletic Club), courts_count="Other" (mixed), method="Other" (mixed floors), frequency="Daily", duration="4hr", monthly_spend="$2k-$5k" → proceed to ROI | Recommendations still render (may not be ideal match); no empty state crash; match scores reflect poor fit with lower percentages | P1 |
| 16 | 3rd Shot PB — mid-chat abandonment (J-08) | Anonymous | 4 of 7 answers entered | Answer 4 questions → close browser tab → reopen marketplace URL | Session restored from cookie; previously answered fields preserved in profile panel; chat history shows prior messages; can resume answering remaining questions | P0 |
| 17 | Session reset via chat command | Anonymous | 5+ answers entered | Type "start over" or "restart" in chat | Phase resets to Discovery; all answers cleared; profile panel shows empty cards; chat shows reset confirmation; `selectedRobotId` cleared | P1 |

---

## 4. Discovery Profile Panel

| # | Test Case | User Role | Preconditions | Steps | Expected Result | Priority |
|---|-----------|-----------|---------------|-------|-----------------|----------|
| 18 | Edit answer directly on profile card | Anonymous | At least 3 chat answers entered | Click edit icon on "Company Name" card → change value → save | Updated value reflected immediately in profile panel; chat does not re-ask the question; session updated in DB | P0 |
| 19 | Profile card edits propagate to ROI | Anonymous | All 7 answers entered, in ROI phase | Navigate back to Discovery → edit monthly_spend from "$2k-$5k" to "$5k-$10k" → return to ROI | ROI recalculates with new spend value; savings numbers update; no stale cached values displayed | P0 |
| 20 | Floor plan upload and analysis | Anonymous | Discovery phase active | Click floor plan upload area → select image (<10MB) → click "Analyze Floor Plan" | Upload completes; GPT-4o Vision analysis returns; sqft and/or monthly_spend auto-populated in profile cards; analysis stored in localStorage | P1 |
| 21 | Floor plan clear and re-upload | Anonymous | Floor plan analysis complete | Click "Clear Analysis" → upload a different floor plan image | Previous analysis removed; new analysis replaces old values; localStorage updated; profile cards reflect new values | P2 |

---

## 5. Robot Marketplace & Filters

| # | Test Case | User Role | Preconditions | Steps | Expected Result | Priority |
|---|-----------|-----------|---------------|-------|-----------------|----------|
| 22 | All 13 active robots display | Anonymous | Page loaded | Scroll through marketplace grid | 13 robot cards visible: CC1 Pro, CC1, MT1 Vac, Neo 2W, Kas, Phantas, Vacuum 40, C40, C30, T7AMR, T380AMR, T300, T600; each shows image, name, monthly price | P0 |
| 23 | Sort by price low to high | Anonymous | Marketplace visible | Select "Price (Low→High)" from sort dropdown | Cards reorder: C30 ($399) first → T7AMR ($1800) last; order is stable on re-sort | P1 |
| 24 | Filter by size category | Anonymous | Marketplace visible | Open filter drawer → select "Small" size toggle | Only small-category robots shown; count badge updates; "Clear All" button appears | P1 |
| 25 | Robot card flip to specs | Anonymous | Marketplace visible | Hover over a robot card → click card | Card flips to reveal specs: function, coverage rate, runtime, ideal environment, key strengths | P0 |
| 26 | Select robot from marketplace | Anonymous | Marketplace visible | Click "Select Unit" on CC1 Pro card | Robot selected (lime ring indicator); `selectedRobotId` updated in session; selection persists across tab changes | P0 |
| 27 | Grid vs List view toggle | Anonymous | Marketplace visible, grid mode default | Click list view toggle icon | Layout switches to single-column list view; all 13 robots still visible; toggle back to grid restores 2-column layout | P2 |

---

## 6. ROI View & Recommendations

| # | Test Case | User Role | Preconditions | Steps | Expected Result | Priority |
|---|-----------|-----------|---------------|-------|-----------------|----------|
| 28 | 3 recommendations render with scores | Anonymous | Transitioned to ROI phase | Observe ROI view | 3 robot cards displayed with labels (RECOMMENDED / BEST VALUE / UPGRADE / ALTERNATIVE); each shows match score as "N% Match"; first auto-selected if no prior selection | P0 |
| 29 | Match score displays as percentage (not multiplied) | Anonymous | ROI phase active | Read match score on recommendation cards | Score shows as "85% Match" (not "8500%"); values are 0-100 range; rounded to nearest integer | P0 |
| 30 | Monthly/yearly savings toggle | Anonymous | ROI phase, robot selected | Click "Yearly" toggle → observe savings → click "Monthly" | Yearly shows 12x monthly values; toggle switches cleanly; no flash of incorrect content between toggles | P0 |
| 31 | Select different robot updates ROI | Anonymous | ROI phase, first robot auto-selected | Click a different recommendation card → observe savings section | Savings recalculate for newly selected robot; current monthly cost, net savings, and hours saved all update; selected card shows lime ring | P0 |
| 32 | Negative ROI displays in red (no hard block) | Anonymous | ROI phase with low-spend inputs (use The Peak fixture: <$2k spend, 6 courts) | Observe savings display | Savings shown in red text; no "Go/No-Go" gate blocking progression; "Proceed to Greenlight" button still accessible | P0 |
| 33 | Back to Discovery from ROI | Anonymous | ROI phase active | Click "← Back to Discovery" link | Phase reverts to Discovery; progress bar updates; profile panel and chat visible; answers preserved | P1 |
| 34 | Recommendation caching (auth user) | Authenticated | ROI phase, recommendations loaded | Navigate away → return to ROI within 1 hour without changing answers | Recommendations load from cache (faster); same scores and rankings as before; cache keyed by answers_hash | P2 |

---

## 7. Greenlight & Checkout

| # | Test Case | User Role | Preconditions | Steps | Expected Result | Priority |
|---|-----------|-----------|---------------|-------|-----------------|----------|
| 35 | Greenlight view renders summary | Authenticated | ROI phase complete, robot selected | Click "Proceed to Greenlight →" | Greenlight view shows: selected robot name, purchase price, savings summary, team invitation form, payment options (Purchase + Gynger) | P0 |
| 36 | Auth required before checkout | Anonymous | ROI complete, clicked "Proceed to Greenlight" | Attempt to proceed to checkout | Signup modal appears; `autopilot_pending_phase` saved to localStorage; after signup, phase restores to Greenlight | P0 |
| 37 | Purchase via Stripe (card) | Authenticated | Greenlight view, "Purchase" selected | Click "Proceed to Secure Checkout" → complete Stripe test checkout (card 4242 4242 4242 4242) | Redirected to Stripe hosted checkout; after payment, redirected to `/checkout/success`; order created in DB with status "completed", payment_provider "stripe" | P0 |
| 38 | Purchase via Stripe — declined card | Authenticated | Greenlight view, "Purchase" selected | Click "Proceed to Secure Checkout" → enter declined test card (4000 0000 0000 0002) | Stripe shows decline error; no order created with "completed" status; user can retry with different card | P0 |
| 39 | Finance with Gynger | Authenticated | Greenlight view, "Finance with Gynger" selected | Click "Apply for Gynger Financing" | New tab opens to Gynger application URL; order created in DB with payment_provider "gynger", status "pending"; original tab shows confirmation state | P0 |
| 40 | Gynger popup blocked fallback | Authenticated | Popup blocker enabled | Click "Apply for Gynger Financing" with popup blocker on | Falls back to same-tab redirect; Gynger application URL loads in current tab; order still created correctly | P1 |
| 41 | Team member invitation (optional) | Authenticated | Greenlight view active | Enter team member: email, first name, last name, role → submit invitation | Invitation sent via Resend email; success confirmation shown; can proceed to checkout without waiting for acceptance | P1 |
| 42 | Target deployment date picker | Authenticated | Greenlight view active | Click target date field → select a date or type "next month" in chat | Date captured and displayed in greenlight summary; date persisted to session; does not block checkout | P2 |

---

## 8. Authentication

| # | Test Case | User Role | Preconditions | Steps | Expected Result | Priority |
|---|-----------|-----------|---------------|-------|-----------------|----------|
| 43 | New user signup | Anonymous | No existing account | Click profile button → fill signup form (email, password, full name, company name) → submit | Account created; JWT tokens stored in localStorage (`autopilot_auth_tokens`); profile button shows user initials; modal closes | P0 |
| 44 | Login with valid credentials | Registered user | Account exists | Click profile button → switch to "Sign In" → enter credentials → submit | Authenticated; tokens in localStorage; anonymous session claimed via `POST /sessions/claim`; discovery answers preserved from anonymous session | P0 |
| 45 | Login with wrong password | Registered user | Account exists | Enter correct email, wrong password → submit | Error banner shown in modal; no redirect; modal stays open for retry | P0 |
| 46 | Session claim preserves discovery data | Anonymous → Authenticated | 5+ discovery answers entered as anonymous | Complete signup | All prior answers transfer to `discovery_profiles`; profile panel unchanged; phase preserved; no data loss | P0 |
| 47 | Auth-before-checkout phase restore | Anonymous | Reached Greenlight phase, prompted to sign up | Complete signup in modal | `autopilot_pending_phase` read from localStorage; phase restored to Greenlight; checkout resumes without re-entering robot selection | P0 |
| 48 | Logout and re-login | Authenticated | Logged in with active session | Click profile dropdown → "Logout" → log back in with same credentials | Logout clears tokens from localStorage; re-login restores authenticated state; discovery profile data still accessible | P1 |

---

## 9. Nonlinear / Session Behavior

| # | Test Case | User Role | Preconditions | Steps | Expected Result | Priority |
|---|-----------|-----------|---------------|-------|-----------------|----------|
| 49 | Repeat visitor — session resume (NL-01) | Anonymous | Previous session with 3 answers | Close browser → reopen marketplace URL (same browser) | Session restored from cookie; 3 prior answers visible in profile panel; chat history intact; can continue discovery | P0 |
| 50 | Mid-ROI edit — change answers and return (NL-02) | Anonymous | In ROI phase with recommendations | Click "← Back to Discovery" → edit court count from 8 to 20 → return to ROI via "Show Me" | New recommendations generated for 20 courts (not cached 8-court result); match scores and savings update; no stale data in UI | P0 |
| 51 | Mid-checkout edit — back to change facility (NL-03) | Authenticated | In Greenlight phase | Use browser Back button → change facility type and court count → re-proceed to Greenlight | Updated values appear in Greenlight summary; no duplicate draft orders in DB; price reflects updated configuration | P0 |
| 52 | Browser back/forward navigation | Anonymous | In ROI phase | Press browser Back → then Forward | Phase state correct at each step; no JavaScript errors; no blank pages; chat panel re-renders correctly | P1 |
| 53 | Multiple tabs same session | Anonymous | Active session | Open marketplace in second tab | Both tabs share session via cookie; changes in tab 1 reflected on refresh in tab 2; no session conflicts | P2 |

---

## 10. Mobile Viewport

| # | Test Case | User Role | Preconditions | Steps | Expected Result | Priority |
|---|-----------|-----------|---------------|-------|-----------------|----------|
| 54 | Mobile tab bar — Marketplace vs Profile | Anonymous | Mobile viewport (375px) | Tap "Marketplace" tab → tap "Profile" tab | Tabs switch content correctly; Marketplace shows robot grid (1 column); Profile shows discovery cards; active tab highlighted | P0 |
| 55 | Mobile chat FAB and bottom sheet | Anonymous | Mobile viewport | Tap floating chat button (bottom-right) | Bottom sheet opens at 85% height; chat fully functional; can send messages and tap chips; drag down to dismiss | P0 |
| 56 | Mobile full checkout flow | Authenticated | Mobile viewport, all discovery complete | Complete full flow: Discovery → ROI → Greenlight → Stripe checkout | All phases navigable on mobile; no broken layouts; inputs reachable; Stripe checkout page renders correctly on mobile | P0 |
| 57 | Mobile unread chat badge | Anonymous | Mobile viewport, chat closed | Receive agent response while chat sheet is closed | Unread count badge appears on FAB; badge clears when chat opened; count accurate for multiple unread messages | P1 |

---

## 11. Error States & Edge Cases

| # | Test Case | User Role | Preconditions | Steps | Expected Result | Priority |
|---|-----------|-----------|---------------|-------|-----------------|----------|
| 58 | Rate limit hit (anonymous) | Anonymous | Active session | Send 16+ messages within 60 seconds | "Sending messages too quickly" error shown in chat; no 500 error; can resume after cooldown | P0 |
| 59 | Token budget exceeded | Anonymous | Active session, high usage | Send messages until 75k daily token budget exhausted | "Reached daily conversation limit" message; chat input disabled; marketplace and profile still functional | P1 |
| 60 | Network error during chat | Anonymous | Active session | Disconnect network → send message → reconnect | "Couldn't connect to the server" error in chat; message not lost; can resend after reconnection | P1 |
| 61 | Checkout API called without auth | Anonymous | Not authenticated | Directly call `POST /checkout/session` without JWT | Returns 401/403; no order created; no Stripe session initiated | P0 |
| 62 | Invalid conversation ID in localStorage | Anonymous | Active session | Manually corrupt `autopilot_conversation_id` in localStorage → send message | Fallback to `GET /conversations/current`; new conversation created if needed; no permanent broken state | P2 |
