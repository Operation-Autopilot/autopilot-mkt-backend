# Discovery

Discovery profile endpoints manage the data collected during the guided discovery conversation. The agent builds this profile progressively as it learns about the user's facility, needs, and constraints. This profile drives robot recommendations.

## GET /discovery/profiles/:session_id

Retrieve the discovery profile for a given session.

**Auth required:** No (for anonymous sessions) / Yes (for linked sessions)

### Request

```http
GET /api/v1/discovery/profiles/sess_abc123 HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### Path Parameters

| Parameter    | Type   | Description                                    |
|--------------|--------|------------------------------------------------|
| `session_id` | string | The session ID associated with the profile.    |

### Response

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "session_id": "sess_abc123",
  "facility_type": "warehouse",
  "facility_size": "50000 sqft",
  "cleaning_approach": "autonomous",
  "priorities": ["efficiency", "low_noise", "minimal_supervision"],
  "constraints": ["narrow_aisles", "24_7_operation"],
  "budget": {
    "min": 15000,
    "max": 35000,
    "currency": "USD"
  },
  "timeline": "within_3_months",
  "additional_notes": "Need to handle both wet and dry floor types. Concrete and epoxy surfaces.",
  "completion_percentage": 85,
  "created_at": "2026-01-15T10:30:00Z",
  "updated_at": "2026-01-15T11:15:00Z"
}
```

### Errors

| Code | Detail                                          |
|------|-------------------------------------------------|
| 404  | `"Discovery profile not found for this session"` |

---

## PUT /discovery/profiles/:session_id

Update the discovery profile for a session. Fields are merged with existing data. This endpoint is typically called by the agent as it extracts information from the conversation, but can also be called directly.

**Auth required:** No (for anonymous sessions) / Yes (for linked sessions)

### Request

```http
PUT /api/v1/discovery/profiles/sess_abc123 HTTP/1.1
Content-Type: application/json
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...

{
  "facility_type": "warehouse",
  "facility_size": "50000 sqft",
  "cleaning_approach": "autonomous",
  "priorities": ["efficiency", "low_noise", "minimal_supervision"],
  "budget": {
    "min": 15000,
    "max": 35000,
    "currency": "USD"
  }
}
```

### Path Parameters

| Parameter    | Type   | Description                                    |
|--------------|--------|------------------------------------------------|
| `session_id` | string | The session ID associated with the profile.    |

### Body Parameters

All fields are optional. Only provided fields are updated.

| Field                | Type     | Description                                              |
|----------------------|----------|----------------------------------------------------------|
| `facility_type`      | string   | Type of facility (e.g., `"warehouse"`, `"hospital"`, `"office"`, `"retail"`, `"school"`, `"hotel"`). |
| `facility_size`      | string   | Size description (e.g., `"50000 sqft"`, `"large"`).     |
| `cleaning_approach`  | string   | Preferred approach: `"autonomous"`, `"semi_autonomous"`, or `"manual_assist"`. |
| `priorities`         | string[] | Ordered list of priorities (e.g., `"efficiency"`, `"low_noise"`, `"minimal_supervision"`, `"thorough_cleaning"`, `"speed"`). |
| `constraints`        | string[] | Operational constraints (e.g., `"narrow_aisles"`, `"24_7_operation"`, `"fragile_floors"`, `"heavy_foot_traffic"`). |
| `budget`             | object   | Budget range with `min`, `max` (numbers), and `currency` (string). |
| `timeline`           | string   | Purchase timeline: `"immediate"`, `"within_1_month"`, `"within_3_months"`, `"within_6_months"`, `"exploring"`. |
| `additional_notes`   | string   | Free-text notes about specific requirements.             |

### Response

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "session_id": "sess_abc123",
  "facility_type": "warehouse",
  "facility_size": "50000 sqft",
  "cleaning_approach": "autonomous",
  "priorities": ["efficiency", "low_noise", "minimal_supervision"],
  "constraints": [],
  "budget": {
    "min": 15000,
    "max": 35000,
    "currency": "USD"
  },
  "timeline": null,
  "additional_notes": null,
  "completion_percentage": 65,
  "created_at": "2026-01-15T10:30:00Z",
  "updated_at": "2026-01-15T11:00:00Z"
}
```

### Errors

| Code | Detail                                    |
|------|-------------------------------------------|
| 404  | `"Session not found"`                     |
| 422  | Validation error on fields                |

## Discovery Profile Schema

| Field                  | Type     | Description                                              |
|------------------------|----------|----------------------------------------------------------|
| `session_id`           | string   | Associated session ID.                                   |
| `facility_type`        | string   | Type of facility.                                        |
| `facility_size`        | string   | Facility size description.                               |
| `cleaning_approach`    | string   | Preferred cleaning approach.                             |
| `priorities`           | string[] | Ordered list of user priorities.                         |
| `constraints`          | string[] | Operational constraints.                                 |
| `budget`               | object   | Budget range (`min`, `max`, `currency`).                 |
| `timeline`             | string   | Purchase timeline.                                       |
| `additional_notes`     | string   | Free-text notes.                                         |
| `completion_percentage`| integer  | How complete the profile is (0-100).                     |
| `created_at`           | string   | ISO 8601 creation timestamp.                             |
| `updated_at`           | string   | ISO 8601 last update timestamp.                          |

## Facility Types

| Value         | Description              |
|---------------|--------------------------|
| `warehouse`   | Warehouse or distribution center. |
| `hospital`    | Hospital or healthcare facility.  |
| `office`      | Office building.                  |
| `retail`      | Retail store or shopping center.  |
| `school`      | School or university campus.      |
| `hotel`       | Hotel or hospitality venue.       |
| `airport`     | Airport terminal.                 |
| `manufacturing` | Manufacturing facility.         |

## Timeline Values

| Value              | Description                  |
|--------------------|------------------------------|
| `immediate`        | Ready to purchase now.       |
| `within_1_month`   | Within the next month.       |
| `within_3_months`  | Within the next 3 months.    |
| `within_6_months`  | Within the next 6 months.    |
| `exploring`        | Just exploring options.      |
