"""Application configuration management using Pydantic Settings."""

from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Model presets for quick switching via OPENAI_MODEL_PRESET env var
MODEL_PRESETS = {
    "performance": {
        "openai_model": "gpt-4o-mini",
        "openai_model_fast": "gpt-4o-mini",
        "openai_model_scoring": "gpt-4o-mini",
    },
    "balanced": {
        "openai_model": "gpt-4o",
        "openai_model_fast": "gpt-4o-mini",
        "openai_model_scoring": "gpt-4o-mini",
    },
    "quality": {
        "openai_model": "gpt-4o",
        "openai_model_fast": "gpt-4o",
        "openai_model_scoring": "gpt-4o",
    },
    "gpt5-nano": {
        "openai_model": "gpt-5-nano",
        "openai_model_fast": "gpt-5-nano",
        "openai_model_scoring": "gpt-5-nano",
    },
    "gpt5-mini": {
        "openai_model": "gpt-5-mini",
        "openai_model_fast": "gpt-5-nano",
        "openai_model_scoring": "gpt-5-nano",
    },
}


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All settings can be overridden via environment variables.
    Required settings will raise validation errors if not provided.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_file_priority="env_file",  # .env file takes precedence over shell env vars
    )

    # Application
    app_name: str = Field(default="autopilot-backend", description="Application name")
    app_env: str = Field(default="development", description="Environment (development/staging/production)")
    debug: bool = Field(default=False, description="Enable debug mode")

    # Server
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8080, description="Server port")

    # CORS
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:5173,https://autopilot-marketplace-discovery-to.vercel.app,https://autopilot-marketplace-lfvsmsod4-sachins-projects-5aeecb17.vercel.app,https://autopilot-marketplace-one.vercel.app,https://www.autopilot-marketplace.com",
        description="Comma-separated list of allowed CORS origins",
    )

    # Auth redirects
    auth_redirect_url: str = Field(
        ...,
        description="Redirect URL after email verification (set via AUTH_REDIRECT_URL env var)",
    )

    # Supabase
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_secret_key: str = Field(..., description="Supabase secret key for backend operations")
    supabase_signing_key_jwk: str = Field(..., description="Supabase signing key JWK (JSON string) for JWT token verification")

    # OpenAI
    openai_api_key: str = Field(..., description="OpenAI API key")
    openai_model: str = Field(default="gpt-4o", description="OpenAI model to use for main conversations")
    openai_model_fast: str = Field(default="gpt-4o-mini", description="Fast OpenAI model for simple tasks (greetings, etc)")
    openai_model_scoring: str = Field(default="gpt-4o-mini", description="OpenAI model for recommendation scoring")
    openai_model_preset: str | None = Field(default=None, description="Model preset name (performance/balanced/quality/gpt5-nano/gpt5-mini). Overrides individual model settings.")
    max_context_messages: int = Field(default=20, description="Max messages to include in context")
    mock_openai: bool | None = Field(default=None, description="Mock OpenAI responses for local testing (saves tokens). Auto-enabled in development, disabled in production.")

    # Pinecone
    pinecone_api_key: str = Field(..., description="Pinecone API key")
    pinecone_environment: str = Field(..., description="Pinecone environment")
    pinecone_index_name: str = Field(default="autopilot-products", description="Pinecone index name")
    embedding_model: str = Field(default="text-embedding-3-small", description="OpenAI embedding model")

    # Session
    session_cookie_name: str = Field(default="autopilot_session", description="Session cookie name")
    session_cookie_max_age: int = Field(default=2592000, description="Session cookie max age in seconds (30 days)")
    session_cookie_secure: bool = Field(default=True, description="Use secure cookies (HTTPS only)")
    session_expiry_days: int = Field(default=30, description="Days until session expires")

    # Rate Limiting
    rate_limit_anonymous_requests: int = Field(default=15, description="Max requests per window for anonymous users")
    rate_limit_authenticated_requests: int = Field(default=100, description="Max requests per window for authenticated users")
    rate_limit_window_seconds: int = Field(default=60, description="Rate limit window in seconds")

    # Token Budgets (OpenAI usage limits)
    # Note: Each message exchange uses ~2,500-3,500 tokens (discovery response + extraction)
    # Generous limits to avoid interrupting user flow during discovery/ROI exploration
    token_budget_anonymous_daily: int = Field(default=75000, description="Max tokens per day for anonymous sessions")
    token_budget_authenticated_daily: int = Field(default=250000, description="Max tokens per day for authenticated users")

    # Request Size Limits
    max_request_body_size: int = Field(default=11534336, description="Max request body size in bytes (11MB, supports floor plan uploads)")
    max_message_length: int = Field(default=4000, description="Max message content length in characters")

    # LLM Recommendations
    use_llm_recommendations: bool = Field(default=True, description="Use LLM for intelligent recommendations (fallback to manual if False)")
    recommendation_cache_ttl: int = Field(default=3600, description="TTL for recommendation cache in seconds (1 hour)")
    recommendation_cache_size: int = Field(default=500, description="Maximum cached recommendation entries")
    llm_scoring_max_candidates: int = Field(default=8, description="Max robots to send to LLM for scoring (after RAG pre-filter)")

    # Stripe
    stripe_secret_key: str = Field(default="", description="Stripe secret API key (production)")
    stripe_secret_key_test: str = Field(default="", description="Stripe test secret API key (for test accounts in production)")
    stripe_webhook_secret: str = Field(default="", description="Stripe webhook signing secret (production)")
    stripe_webhook_secret_test: str = Field(default="", description="Stripe test webhook signing secret (for test accounts)")
    stripe_publishable_key: str = Field(default="", description="Stripe publishable key (for frontend)")

    # Gynger B2B Financing
    gynger_api_key: str = Field(default="", description="Gynger vendor API key")
    gynger_api_url: str = Field(default="https://api.gynger.io/v1", description="Gynger API base URL")  # TODO: confirm with Gynger docs
    gynger_webhook_secret: str = Field(default="", description="Gynger webhook signing secret")

    # Email (Resend)
    resend_api_key: str = Field(default="", description="Resend API key for sending emails")
    email_from_address: str = Field(
        default="Autopilot <noreply@operationautopilot.com>",
        description="From address for transactional emails",
    )

    # Frontend
    frontend_url: str = Field(
        default="http://localhost:3000",
        description="Frontend application URL for email links",
    )

    # Admin
    admin_email_domain: str = Field(default="", description="Email domain for admin access (e.g. tryautopilot.com)")

    # HubSpot OAuth
    hubspot_client_id: str = Field(default="", description="HubSpot OAuth client ID")
    hubspot_client_secret: str = Field(default="", description="HubSpot OAuth client secret")
    hubspot_redirect_uri: str = Field(default="", description="HubSpot OAuth redirect URI")

    # Fireflies
    fireflies_api_key: str = Field(default="", description="Fireflies workspace API key")

    # Token encryption at rest (base64-encoded 32-byte key)
    encryption_key: str = Field(default="", description="Base64-encoded 32-byte key for token encryption at rest")

    @model_validator(mode="after")
    def set_mock_openai_default(self) -> "Settings":
        """Set mock_openai based on environment if not explicitly set via MOCK_OPENAI env var.
        
        - Production (APP_ENV=production): Always False (unless MOCK_OPENAI env var is explicitly set)
        - Development/Staging: True (unless MOCK_OPENAI env var is explicitly set)
        
        If MOCK_OPENAI env var is set, pydantic-settings already parsed it to a bool,
        so we only set the default if it's None.
        """
        # If MOCK_OPENAI was explicitly set via env var, it's already a bool (not None)
        # Only set default if it's None (meaning env var wasn't set)
        if self.mock_openai is None:
            # Production: always False
            # Development/Staging: True  
            self.mock_openai = self.app_env != "production"
        
        return self

    @model_validator(mode="after")
    def apply_model_preset(self) -> "Settings":
        """Apply model preset if set, overriding individual model settings."""
        if self.openai_model_preset and self.openai_model_preset in MODEL_PRESETS:
            preset = MODEL_PRESETS[self.openai_model_preset]
            self.openai_model = preset["openai_model"]
            self.openai_model_fast = preset["openai_model_fast"]
            self.openai_model_scoring = preset["openai_model_scoring"]
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins string into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app_env == "production"

    @property
    def is_stripe_test_mode(self) -> bool:
        """Check if using Stripe test keys."""
        return self.stripe_secret_key.startswith("sk_test_")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings singleton.

    Returns:
        Settings: Application settings instance.

    Note:
        Settings are cached using lru_cache for performance.
        Call get_settings.cache_clear() to reload settings.
    """
    return Settings()
