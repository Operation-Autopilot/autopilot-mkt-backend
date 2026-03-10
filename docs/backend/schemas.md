---
title: Pydantic Schemas
---

# Pydantic Schemas

All schemas use **Pydantic v2** with `ConfigDict(from_attributes=True)` to support initialization from ORM objects. Fields marked `?` are optional with `default=None`.

Schema files live in `src/schemas/`. Each file corresponds to one resource domain.

---

## auth.py

| Model | Key Fields |
|-------|-----------|
| `UserContext` | `user_id: UUID`, `email?: str`, `role?: str` |
| `TokenPayload` | `sub: str`, `email?: str`, `exp: int`, `iat: int` |
| `SignupRequest` | `email: EmailStr`, `password: str` (8–100 chars), `display_name?: str`, `company_name?: str` |
| `SignupResponse` | `user_id: str`, `email: str`, `message: str`, `email_sent: bool`, `profile_id?: str` |
| `VerifyEmailRequest` | `token: str`, `token_hash?: str` |
| `LoginRequest` | `email: EmailStr`, `password: str` |
| `LoginResponse` | `access_token: str`, `refresh_token?: str`, `user_id: str`, `email: str`, `expires_in: int` |
| `RefreshTokenRequest` | `refresh_token: str` |
| `RefreshTokenResponse` | `access_token: str`, `refresh_token?: str`, `expires_in: int` |
| `ForgotPasswordRequest` | `email: EmailStr` |
| `ResetPasswordRequest` | `token: str`, `new_password: str` (8–100 chars) |
| `ChangePasswordRequest` | `current_password: str`, `new_password: str` (8–100 chars) |

---

## checkout.py

| Model | Key Fields |
|-------|-----------|
| `OrderLineItemSchema` | `product_id: str`, `product_name: str`, `quantity: int` (≥1), `unit_amount_cents: int`, `stripe_price_id: str` |
| `OrderResponse` | `id: UUID`, `profile_id?: UUID`, `session_id?: UUID`, `status: str`, `line_items: list[OrderLineItemSchema]`, `total_cents: int`, `currency: str`, `stripe_subscription_id?: str`, `completed_at?: datetime`, `created_at: datetime` |
| `OrderListResponse` | `items: list[OrderResponse]` |
| `CheckoutSessionCreate` | `product_id: UUID`, `success_url: HttpUrl`, `cancel_url: HttpUrl`, `customer_email?: str` |
| `CheckoutSessionResponse` | `checkout_url: str`, `order_id: UUID`, `stripe_session_id: str`, `is_test_mode: bool` |
| `GyngerSessionCreate` | `product_id: UUID`, `success_url: HttpUrl`, `cancel_url: HttpUrl`, `customer_email?: str` |
| `GyngerSessionResponse` | `application_url: str`, `order_id: UUID`, `gynger_application_id: str` |

---

## common.py

| Model | Key Fields |
|-------|-----------|
| `HealthResponse` | `status: HealthStatus` (healthy/unhealthy), `timestamp: datetime`, `version: str` |
| `CheckResult` | `name: str`, `healthy: bool`, `latency_ms?: float`, `error?: str` |
| `ReadinessResponse` | `status: HealthStatus`, `timestamp: datetime`, `checks: list[CheckResult]` |
| `ErrorDetail` | `loc?: list[str]`, `msg: str`, `type: str` |
| `ErrorResponse` | `error: str`, `message: str`, `details?: list[ErrorDetail]`, `request_id?: str`, `timestamp: datetime` |

---

## company.py

| Model | Key Fields |
|-------|-----------|
| `CompanyCreate` | `name: str` (1–255 chars) |
| `CompanyResponse` | `id: UUID`, `name: str`, `owner_id: UUID`, `created_at: datetime` |
| `MemberProfile` | `id: UUID`, `display_name?: str`, `email?: str` |
| `CompanyMemberResponse` | `id: UUID`, `company_id: UUID`, `profile_id: UUID`, `role: str`, `joined_at: datetime`, `profile: MemberProfile` |
| `InvitationCreate` | `email: EmailStr` |
| `InvitationResponse` | `id: UUID`, `company_id: UUID`, `email: str`, `status: InvitationStatus`, `expires_at: datetime`, `created_at: datetime` |
| `InvitationWithCompany` | (extends `InvitationResponse`) + `company_name: str` |

---

## conversation.py

| Model | Key Fields |
|-------|-----------|
| `ConversationCreate` | `title?: str` (max 255), `metadata?: dict` |
| `ConversationResponse` | `id: UUID`, `profile_id?: UUID`, `title: str`, `phase: ConversationPhase`, `metadata: dict`, `message_count: int`, `last_message_at?: datetime`, `created_at: datetime` |
| `ConversationListResponse` | `conversations: list[ConversationResponse]`, `next_cursor?: str`, `has_more: bool` |
| `CurrentConversationResponse` | `conversation: ConversationResponse`, `is_new: bool`, `messages: list[dict]` |

---

## discovery.py

| Model | Key Fields |
|-------|-----------|
| `DiscoveryProfileUpdate` | `current_question_index?: int`, `phase?: SessionPhase`, `answers?: dict[str, DiscoveryAnswerSchema]`, `roi_inputs?: ROIInputsSchema`, `selected_product_ids?: list[UUID]`, `greenlight?: GreenlightSchema` |
| `DiscoveryProfileResponse` | `id: UUID`, `profile_id: UUID`, `current_question_index: int`, `phase: str`, `answers: dict`, `roi_inputs?: ROIInputsSchema`, `selected_product_ids: list[UUID]`, `ready_for_roi: bool`, `created_at: datetime` |

---

## floor_plan.py

### Enums

| Enum | Values |
|------|--------|
| `FloorPlanStatus` | `pending`, `processing`, `completed`, `failed` |
| `ZoneType` | `court`, `circulation`, `auxiliary`, `excluded` |
| `SurfaceType` | `sport_court_acrylic`, `rubber_tile`, `modular`, `concrete`, `other` |
| `CleaningMode` | `dry_vacuum`, `dry_sweep`, `wet_scrub`, `wet_vacuum` |
| `ObstructionHandling` | `virtual_boundary`, `no_go_zone`, `navigate_around` |

### Extracted Features

| Model | Key Fields |
|-------|-----------|
| `FacilityDimensionsSchema` | `length_ft: float`, `width_ft: float`, `total_sqft: float`, `confidence: float` (0–1) |
| `CourtSchema` | `label: str`, `sqft: float`, `surface_type: SurfaceType`, `confidence: float` |
| `FeatureSummarySchema` | `total_court_sqft: float`, `total_cleanable_sqft: float`, `court_count: int` |
| `ExtractedFeaturesSchema` | `facility_dimensions?: FacilityDimensionsSchema`, `courts: list[CourtSchema]`, `summary: FeatureSummarySchema` |
| `CostEstimateSchema` | `total_monthly_cost: float`, `total_daily_cost: float`, `estimated_robot_count?: int` |

### API Responses

| Model | Key Fields |
|-------|-----------|
| `FloorPlanUploadResponse` | `id: UUID`, `status: FloorPlanStatus`, `file_name: str`, `created_at: datetime` |
| `FloorPlanAnalysisResponse` | `id: UUID`, `status: FloorPlanStatus`, `extracted_features?: ExtractedFeaturesSchema`, `extraction_confidence?: str`, `cost_estimate?: CostEstimateSchema`, `tokens_used?: int`, `created_at: datetime` |
| `FloorPlanListResponse` | `analyses: list[FloorPlanAnalysisResponse]`, `total: int` |

---

## message.py

| Model | Key Fields |
|-------|-----------|
| `MessageCreate` | `content: str` (≥1 char, max enforced by `MAX_MESSAGE_LENGTH` config) |
| `MessageResponse` | `id: UUID`, `conversation_id: UUID`, `role: MessageRole`, `content: str`, `metadata: dict`, `created_at: datetime` |
| `DiscoveryState` | `ready_for_roi: bool`, `answered_keys: list[str]`, `missing_keys: list[str]`, `progress_percent: int` |
| `MessageWithAgentResponse` | `user_message: MessageResponse`, `agent_message: MessageResponse`, `chips: list[str]`, `discovery_state?: DiscoveryState` |
| `MessageListResponse` | `messages: list[MessageResponse]`, `next_cursor?: str`, `has_more: bool` |

---

## profile.py

| Model | Key Fields |
|-------|-----------|
| `ProfileUpdate` | `display_name?: str`, `avatar_url?: str` |
| `SetTestAccountRequest` | `is_test_account: bool` |
| `ProfileResponse` | `id: UUID`, `user_id: UUID`, `is_test_account: bool`, `created_at: datetime` |
| `CompanySummary` | `id: UUID`, `name: str`, `role: str`, `joined_at: datetime` |
| `ProfileWithCompanies` | (extends `ProfileResponse`) + `companies: list[CompanySummary]` |

---

## robot.py

| Model | Key Fields |
|-------|-----------|
| `RobotFilters` | `sort: RobotSortField`, `price_min?: float`, `price_max?: float`, `category?: str`, `methods?: list[str]`, `surfaces?: list[str]`, `search?: str`, `page: int` (≥1), `page_size: int` (1–100) |
| `RobotResponse` | `id: UUID`, `name: str`, `manufacturer: str`, `category: str`, `modes: list[str]`, `surfaces: list[str]`, `monthly_lease: Decimal`, `monthlyLease: float` (computed camelCase), `purchase_price: Decimal`, `time_efficiency: Decimal`, `coverageRate?: float`, `image_url?: str`, `active: bool` |
| `FilterMetadata` | `sort_options`, `price_ranges`, `sizes`, `methods`, `surfaces`, `categories` (each: `list[FilterOption]`) |
| `RobotListResponse` | `items: list[RobotResponse]`, `total: int` |

---

## roi.py

| Model | Key Fields |
|-------|-----------|
| `ROIInputs` | `labor_rate: float` (≥0, default 25.0), `utilization: float` (0–1), `maintenance_factor: float` (0–1), `manual_monthly_spend: float` (≥0), `manual_monthly_hours: float` (≥0) |
| `ROICalculationRequest` | `robot_id: UUID`, `answers: dict[str, DiscoveryAnswer]`, `roi_inputs?: ROIInputs`, `timeframe: "monthly" \| "yearly"` |
| `SavingsBreakdown` | `current_monthly_cost: float`, `robot_lease_cost: float`, `gross_savings: float`, `net_savings: float` |
| `ROICalculation` | `estimated_monthly_savings: float`, `estimated_yearly_savings: float`, `roi_percent: float`, `payback_months?: float`, `savings_breakdown?: SavingsBreakdown`, `confidence: "high" \| "medium" \| "low"`, `algorithm_version: str` |
| `ROICalculationResponse` | `robot_id: UUID`, `robot_name: str`, `calculation: ROICalculation`, `calculated_at: datetime` |
| `RobotRecommendation` | `robot_id: UUID`, `robot_name: str`, `rank: int`, `label: str`, `match_score: float` (0–100), `reasons: list[RecommendationReason]`, `summary: str`, `projected_roi: ROICalculation` |
| `RecommendationsResponse` | `recommendations: list[RobotRecommendation]`, `other_options: list[OtherRobotOption]`, `total_robots_evaluated: int`, `algorithm_version: str` |
| `GreenlightConfirmRequest` | `selected_robot_id: UUID`, `payment_method: "card" \| "paypal" \| "bank"`, `customer_email: str` |
| `GreenlightConfirmResponse` | `success: bool`, `next_step: "checkout" \| "contact_sales" \| "schedule_demo"`, `checkout_url?: str` |

---

## session.py

| Model | Key Fields |
|-------|-----------|
| `DiscoveryAnswerSchema` | `questionId: int`, `key: str`, `label: str`, `value: str`, `group: "Company" \| "Facility" \| "Operations" \| "Economics" \| "Context"` |
| `ROIInputsSchema` | `laborRate: float`, `utilization: float`, `maintenanceFactor: float`, `manualMonthlySpend: float`, `manualMonthlyHours: float` |
| `GreenlightSchema` | `target_start_date?: str`, `team_members: list[TeamMemberSchema]`, `payment_method?: "card" \| "paypal" \| "bank"` |
| `SessionUpdate` | `current_question_index?: int`, `phase?: SessionPhase`, `answers?: dict[str, DiscoveryAnswerSchema]`, `roi_inputs?: ROIInputsSchema`, `selected_product_ids?: list[UUID]`, `greenlight?: GreenlightSchema` |
| `SessionResponse` | `id: UUID`, `session_token?: str`, `phase: str`, `answers: dict`, `selected_product_ids: list[UUID]`, `conversation_id?: UUID`, `expires_at: datetime`, `ready_for_roi: bool` |
| `SessionClaimResponse` | `message: str`, `discovery_profile_id: UUID`, `conversation_transferred: bool`, `orders_transferred: int` |
