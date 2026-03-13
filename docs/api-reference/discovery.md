# Discovery

Discovery profile endpoints manage the structured data collected during the guided discovery conversation. The agent builds this profile progressively as it learns about the user's facility, cleaning methods, and budget. This profile drives robot recommendations and ROI calculations.

> **Note:** Anonymous users interact via the [Sessions API](./sessions.md) (`GET/PUT /api/v1/sessions/me`). The endpoints below are for **authenticated users** whose discovery data is stored in the `discovery_profiles` table, scoped to their company when applicable (migration 026).

## GET /api/v1/discovery

Get the authenticated user's discovery profile. Creates one automatically if it doesn't exist. For company members, returns the shared company discovery profile.

**Auth required:** Yes (JWT Bearer token)

### Request

```http
GET /api/v1/discovery HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### Response

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "profile_id": "660e8400-e29b-41d4-a716-446655440001",
  "company_id": "770e8400-e29b-41d4-a716-446655440002",
  "current_question_index": 5,
  "phase": "roi",
  "answers": {
    "company_name": {
      "questionId": "q1",
      "key": "company_name",
      "label": "Company Name",
      "value": "Calabasas Pickleball Club",
      "group": "Company"
    },
    "monthly_spend": {
      "questionId": "q6",
      "key": "monthly_spend",
      "label": "Monthly Cleaning Spend",
      "value": "$2k-$5k",
      "group": "Economics"
    }
  },
  "roi_inputs": {
    "monthly_spend": 3500,
    "sqft": 8000,
    "hours_per_clean": 4,
    "cleans_per_week": 7
  },
  "selected_product_ids": ["880e8400-e29b-41d4-a716-446655440003"],
  "timeframe": "monthly",
  "greenlight": null,
  "created_at": "2026-03-10T10:30:00Z",
  "updated_at": "2026-03-10T11:15:00Z",
  "ready_for_roi": true
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | `uuid` | Discovery profile unique identifier |
| `profile_id` | `uuid` | Associated user profile ID |
| `company_id` | `uuid \| null` | Associated company ID (shared across company members) |
| `current_question_index` | `integer` | Current question index in discovery flow |
| `phase` | `string` | Current phase: `discovery`, `roi`, or `greenlight` |
| `answers` | `object` | Discovery answers keyed by question key (see Answer Schema below) |
| `roi_inputs` | `object \| null` | ROI calculation inputs (monthly_spend, sqft, hours, frequency) |
| `selected_product_ids` | `uuid[]` | Selected robot IDs from recommendations |
| `timeframe` | `string \| null` | ROI display timeframe: `monthly` or `yearly` |
| `greenlight` | `object \| null` | Greenlight phase data (team members, target date) |
| `ready_for_roi` | `boolean` | Whether 5+ of 6 required questions are answered |
| `created_at` | `datetime` | Profile creation timestamp |
| `updated_at` | `datetime` | Last update timestamp |

---

## PUT /api/v1/discovery

Update the authenticated user's discovery profile. All fields are optional — only provided fields are updated. For company members, updates the shared company discovery profile.

**Auth required:** Yes (JWT Bearer token)

### Request

```http
PUT /api/v1/discovery HTTP/1.1
Content-Type: application/json
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...

{
  "current_question_index": 6,
  "phase": "roi",
  "answers": {
    "company_name": {
      "questionId": "q1",
      "key": "company_name",
      "label": "Company Name",
      "value": "Calabasas Pickleball Club",
      "group": "Company"
    }
  },
  "selected_product_ids": ["880e8400-e29b-41d4-a716-446655440003"],
  "timeframe": "yearly"
}
```

### Body Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `current_question_index` | `integer` | No | Current question index (≥ 0) |
| `phase` | `string` | No | Phase: `discovery`, `roi`, or `greenlight` |
| `answers` | `object` | No | Discovery answers keyed by question key |
| `roi_inputs` | `object` | No | ROI calculation inputs |
| `selected_product_ids` | `uuid[]` | No | Selected robot IDs |
| `timeframe` | `string` | No | `monthly` or `yearly` |
| `greenlight` | `object` | No | Greenlight phase data |

### Response

Returns the updated `DiscoveryProfileResponse` (same shape as GET).

### Errors

| Code | Detail |
|------|--------|
| 401 | Not authenticated |
| 404 | `"Discovery profile not found"` |
| 422 | Validation error on fields |

---

## Discovery Answer Schema

Each answer in the `answers` object follows this structure:

| Field | Type | Description |
|-------|------|-------------|
| `questionId` | `string` | Unique question identifier |
| `key` | `string` | Answer key (e.g., `company_name`, `monthly_spend`) |
| `label` | `string` | Human-readable label |
| `value` | `string` | The user's answer |
| `group` | `string` | Answer group: `Company`, `Facility`, `Operations`, `Economics`, or `Context` |

### Required Question Keys

The `ready_for_roi` flag requires 5+ of these 6 keys to be answered:

| Key | Group | Description |
|-----|-------|-------------|
| `company_type` | Company | Facility type (e.g., Pickleball Club, Warehouse) |
| `sqft` | Facility | Approximate facility size |
| `method` | Operations | Current cleaning method |
| `frequency` | Operations | Cleaning frequency |
| `duration` | Operations | Hours per cleaning session |
| `monthly_spend` | Economics | Current monthly cleaning spend |

> `company_name` is also collected but does not count toward the ROI readiness gate. For company members, `company_name` is considered answered from their company profile.

---

## Anonymous Discovery (via Sessions API)

Anonymous users who haven't signed up yet store discovery data in the **sessions** table via:

- `GET /api/v1/sessions/me` — retrieve session with `answers` JSONB field
- `PUT /api/v1/sessions/me` — update session answers, phase, selected_product_ids

When the user signs up, `POST /api/v1/sessions/me/claim` transfers the anonymous session data to a `discovery_profiles` row.

See [Sessions API](./sessions.md) for full details.
