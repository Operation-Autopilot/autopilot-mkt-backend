# Robots

Robot catalog endpoints provide access to the marketplace inventory. Users can browse, filter, and get personalized recommendations based on their discovery profile.

## GET /robots

List robots in the catalog with optional filters.

**Auth required:** No

### Request

```http
GET /api/v1/robots?type=floor_scrubber&min_price=5000&max_price=50000&features=autonomous,mapping&limit=10&offset=0 HTTP/1.1
```

### Query Parameters

| Parameter   | Type    | Default | Description                                              |
|-------------|---------|---------|----------------------------------------------------------|
| `type`      | string  | —       | Filter by robot type (e.g., `floor_scrubber`, `vacuum`, `window_cleaner`, `disinfection`). |
| `min_price` | number  | —       | Minimum price in USD.                                    |
| `max_price` | number  | —       | Maximum price in USD.                                    |
| `features`  | string  | —       | Comma-separated list of required features.               |
| `limit`     | integer | 20      | Maximum items to return.                                 |
| `offset`    | integer | 0       | Number of items to skip.                                 |

### Response

```http
HTTP/1.1 200 OK
Content-Type: application/json

[
  {
    "id": "robot_abc123",
    "name": "CleanBot Pro X500",
    "manufacturer": "RoboClean Industries",
    "type": "floor_scrubber",
    "price": 24999.00,
    "currency": "USD",
    "description": "Industrial autonomous floor scrubber for large facilities.",
    "features": ["autonomous", "mapping", "obstacle_avoidance", "wet_dry"],
    "coverage_sqft": 50000,
    "battery_hours": 8,
    "image_url": "https://cdn.autopilot.com/robots/cleanbot-pro-x500.jpg",
    "created_at": "2026-01-01T00:00:00Z"
  },
  {
    "id": "robot_def456",
    "name": "SweepMaster 3000",
    "manufacturer": "AutoSweep Co.",
    "type": "floor_scrubber",
    "price": 18500.00,
    "currency": "USD",
    "description": "Mid-range floor scrubber with smart navigation.",
    "features": ["autonomous", "mapping", "scheduling"],
    "coverage_sqft": 30000,
    "battery_hours": 6,
    "image_url": "https://cdn.autopilot.com/robots/sweepmaster-3000.jpg",
    "created_at": "2026-01-05T00:00:00Z"
  }
]
```

---

## GET /robots/:id

Retrieve detailed information about a specific robot.

**Auth required:** No

### Request

```http
GET /api/v1/robots/robot_abc123 HTTP/1.1
```

### Path Parameters

| Parameter | Type   | Description       |
|-----------|--------|-------------------|
| `id`      | string | The robot ID.     |

### Response

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": "robot_abc123",
  "name": "CleanBot Pro X500",
  "manufacturer": "RoboClean Industries",
  "type": "floor_scrubber",
  "price": 24999.00,
  "currency": "USD",
  "description": "Industrial autonomous floor scrubber for large facilities. Features LiDAR mapping, obstacle avoidance, and supports both wet and dry cleaning modes.",
  "features": ["autonomous", "mapping", "obstacle_avoidance", "wet_dry"],
  "specifications": {
    "coverage_sqft": 50000,
    "battery_hours": 8,
    "weight_lbs": 350,
    "dimensions": "48x30x36 in",
    "water_tank_gallons": 15,
    "noise_level_db": 65,
    "charging_time_hours": 4
  },
  "warranty": {
    "duration_months": 24,
    "type": "comprehensive"
  },
  "image_url": "https://cdn.autopilot.com/robots/cleanbot-pro-x500.jpg",
  "gallery_urls": [
    "https://cdn.autopilot.com/robots/cleanbot-pro-x500-side.jpg",
    "https://cdn.autopilot.com/robots/cleanbot-pro-x500-top.jpg"
  ],
  "created_at": "2026-01-01T00:00:00Z"
}
```

### Errors

| Code | Detail                    |
|------|---------------------------|
| 404  | `"Robot not found"`       |

---

## GET /robots/recommendations

Get personalized robot recommendations based on the user's discovery profile. The recommendation engine considers facility type, size, priorities, budget, and other discovery data.

**Auth required:** Yes

### Request

```http
GET /api/v1/robots/recommendations?session_id=sess_abc123&limit=5 HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### Query Parameters

| Parameter    | Type    | Default | Description                                               |
|--------------|---------|---------|-----------------------------------------------------------|
| `session_id` | string  | —       | Session ID with a completed discovery profile.            |
| `limit`      | integer | 5       | Maximum number of recommendations to return.              |

### Response

```http
HTTP/1.1 200 OK
Content-Type: application/json

[
  {
    "robot": {
      "id": "robot_abc123",
      "name": "CleanBot Pro X500",
      "manufacturer": "RoboClean Industries",
      "type": "floor_scrubber",
      "price": 24999.00,
      "currency": "USD",
      "description": "Industrial autonomous floor scrubber for large facilities.",
      "features": ["autonomous", "mapping", "obstacle_avoidance", "wet_dry"],
      "image_url": "https://cdn.autopilot.com/robots/cleanbot-pro-x500.jpg"
    },
    "match_score": 0.95,
    "match_reasons": [
      "Covers your facility size of 50,000 sq ft",
      "Within your budget range",
      "Supports autonomous operation as prioritized"
    ]
  },
  {
    "robot": {
      "id": "robot_ghi789",
      "name": "IndustriClean A1",
      "manufacturer": "TechClean Corp",
      "type": "floor_scrubber",
      "price": 32000.00,
      "currency": "USD",
      "description": "Premium industrial cleaning robot with AI-powered navigation.",
      "features": ["autonomous", "ai_navigation", "mapping", "analytics"],
      "image_url": "https://cdn.autopilot.com/robots/industriclean-a1.jpg"
    },
    "match_score": 0.88,
    "match_reasons": [
      "Exceeds coverage requirements",
      "Advanced AI navigation matches your priorities",
      "Slightly above budget but offers best-in-class features"
    ]
  }
]
```

### Errors

| Code | Detail                                          |
|------|-------------------------------------------------|
| 401  | `"Invalid authentication credentials"`          |
| 404  | `"Discovery profile not found for this session"` |

## Robot Schema

| Field            | Type     | Description                                     |
|------------------|----------|-------------------------------------------------|
| `id`             | string   | Unique robot identifier.                        |
| `name`           | string   | Robot product name.                             |
| `manufacturer`   | string   | Manufacturing company name.                     |
| `type`           | string   | Robot category/type.                            |
| `price`          | number   | Price in the specified currency.                |
| `currency`       | string   | Price currency (ISO 4217).                      |
| `description`    | string   | Product description.                            |
| `features`       | string[] | List of feature tags.                           |
| `specifications` | object   | Detailed technical specifications.              |
| `warranty`       | object   | Warranty details.                               |
| `image_url`      | string   | Primary product image URL.                      |
| `gallery_urls`   | string[] | Additional product image URLs.                  |
| `created_at`     | string   | ISO 8601 creation timestamp.                    |
