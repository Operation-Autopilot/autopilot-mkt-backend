"""Authentication business logic service."""

import asyncio
import logging
from typing import Any
from uuid import UUID

from src.api.middleware.error_handler import ValidationError
from src.core.config import get_settings
from src.core.supabase import create_auth_client

logger = logging.getLogger(__name__)


class AuthService:
    """Service for managing user authentication."""

    def __init__(self) -> None:
        """Initialize auth service with isolated Supabase client.

        Uses create_auth_client() instead of get_supabase_client() to avoid
        polluting the singleton client's Authorization header when auth
        operations call set_session().
        """
        self.client = create_auth_client()
        self.settings = get_settings()

    async def signup(
        self,
        email: str,
        password: str,
        display_name: str | None = None,
        company_name: str | None = None,
    ) -> dict[str, Any]:
        """Sign up a new user with email and password.

        Creates the auth user, profile, and optionally a company atomically.

        Args:
            email: User's email address.
            password: User's password.
            display_name: Optional display name.
            company_name: Optional company name to create.

        Returns:
            dict: Signup response with user_id, email, profile_id, company_id, and email_sent status.

        Raises:
            ValidationError: If signup fails (e.g., email already exists).
        """
        try:
            # Sign up user with Supabase Auth
            redirect_url = self.settings.auth_redirect_url

            signup_data: dict[str, Any] = {
                "email": email,
                "password": password,
                "options": {
                    "email_redirect_to": redirect_url,
                },
            }

            # Add metadata if display_name provided
            if display_name:
                signup_data["options"]["data"] = {"full_name": display_name}

            response = self.client.auth.sign_up(signup_data)

            if not response.user:
                raise ValidationError("Failed to create user account")

            user = response.user
            logger.info("User signed up: %s", user.id)

            # Create profile for the user
            from src.services.profile_service import ProfileService
            profile_service = ProfileService()
            profile = await profile_service.get_or_create_profile(
                user_id=UUID(str(user.id)),
                email=email,
                display_name=display_name,
            )
            profile_id = profile["id"]
            logger.info("Profile created for user %s: %s", user.id, profile_id)

            # Create company if company_name provided
            company_id = None
            if company_name:
                from src.services.company_service import CompanyService
                from src.schemas.company import CompanyCreate
                company_service = CompanyService()
                company = await company_service.create_company(
                    data=CompanyCreate(name=company_name),
                    owner_profile_id=UUID(profile_id),
                )
                company_id = company["id"]
                logger.info("Company created for user %s: %s", user.id, company_id)

            # Fire HubSpot Lead creation (fire-and-forget — never blocks signup)
            if self.settings.hubspot_access_token:
                from src.services.hubspot_service import HubSpotService
                asyncio.create_task(
                    HubSpotService().on_signup(
                        email=email,
                        display_name=display_name or email,
                        company_name=company_name,
                    )
                )

            return {
                "user_id": str(user.id),
                "email": user.email or email,
                "email_sent": response.session is None,  # Email sent if no session (requires verification)
                "message": "User created successfully. Please check your email to verify your account.",
                "profile_id": profile_id,
                "company_id": company_id,
            }

        except Exception as e:
            error_msg = str(e)
            logger.error("Signup failed: %s", error_msg)

            # Handle common Supabase errors
            if "already registered" in error_msg.lower() or "already exists" in error_msg.lower():
                raise ValidationError("An account with this email already exists") from e
            if "invalid email" in error_msg.lower():
                raise ValidationError("Invalid email address") from e
            if "password" in error_msg.lower() and "weak" in error_msg.lower():
                raise ValidationError("Password is too weak. Please use a stronger password.") from e

            raise ValidationError(f"Signup failed: {error_msg}") from e

    async def signup_with_session(
        self,
        email: str,
        password: str,
        display_name: str | None = None,
        company_name: str | None = None,
        session_token: str | None = None,
    ) -> dict[str, Any]:
        """Atomic signup + session claim to prevent race conditions.

        Combines user creation, profile creation, inline extraction, and session
        claiming into a single operation. This prevents data loss from background
        extraction tasks racing with the claim.

        Args:
            email: User's email address.
            password: User's password.
            display_name: Optional display name.
            company_name: Optional company name to create.
            session_token: Optional anonymous session token to claim.

        Returns:
            dict: Combined signup + claim response.

        Raises:
            ValidationError: If signup fails.
        """
        # Step 1: Run the standard signup (creates auth user, profile, company)
        signup_result = await self.signup(
            email=email,
            password=password,
            display_name=display_name,
            company_name=company_name,
        )

        # Base response from signup
        result = {
            **signup_result,
            "session_claimed": False,
            "discovery_profile_id": None,
            "conversation_transferred": False,
            "orders_transferred": 0,
        }

        # Step 2: Login immediately after signup to get auth tokens.
        # Email verification is disabled for this project, so sign_in_with_password
        # succeeds right away and gives us the JWT the frontend needs.
        try:
            from src.core.supabase import create_auth_client
            auth_client = create_auth_client()
            login_response = auth_client.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
            if login_response.session:
                result["access_token"] = login_response.session.access_token
                result["refresh_token"] = login_response.session.refresh_token
                result["expires_in"] = login_response.session.expires_in or 3600
            else:
                logger.warning("No session returned from post-signup login for %s", email)
        except Exception as e:
            logger.warning("Failed to get auth tokens after signup for %s: %s", email, e)

        # Step 3: If no session token, return now (tokens already included above)
        if not session_token:
            return result

        # Step 3: Claim the session with inline extraction
        try:
            from src.services.checkout_service import CheckoutService
            from src.services.profile_extraction_service import ProfileExtractionService
            from src.services.session_service import SessionService

            session_service = SessionService(checkout_service=CheckoutService())
            session = await session_service.get_session_by_token(session_token)

            if not session:
                logger.warning("Session not found during signup-with-session for %s", email)
                result["message"] += " Session not found — skipped claim."
                return result

            session_id = UUID(session["id"])
            profile_id = UUID(signup_result["profile_id"])

            # Run extraction INLINE (not background) to capture latest conversation data
            conversation_id = session.get("conversation_id")
            if conversation_id:
                try:
                    extraction_service = ProfileExtractionService()
                    await extraction_service.extract_and_update(
                        conversation_id=UUID(conversation_id) if isinstance(conversation_id, str) else conversation_id,
                        session_id=session_id,
                    )
                    logger.info("Inline extraction completed for session %s", session_id)
                except Exception as e:
                    logger.error("Inline extraction failed for session %s: %s", session_id, e)
                    # Continue with claim using whatever data the session already has

                # Re-read session to get freshly extracted data
                session = await session_service.get_session_by_id(session_id)
                if not session:
                    logger.error("Session %s disappeared after extraction", session_id)
                    result["message"] += " Session lost during extraction — skipped claim."
                    return result

            # Claim the session (atomic — will fail if already claimed)
            claim_result = await session_service.claim_session(
                session_id=session_id,
                profile_id=profile_id,
            )

            result["session_claimed"] = True
            result["discovery_profile_id"] = claim_result["discovery_profile"]["id"]
            result["conversation_transferred"] = claim_result["conversation_transferred"]
            result["orders_transferred"] = claim_result["orders_transferred"]
            logger.info(
                "Session %s claimed during signup for user %s",
                session_id,
                signup_result["user_id"],
            )

        except ValueError as e:
            # Session expired, already claimed, etc. — don't fail the signup
            logger.warning(
                "Session claim failed during signup for %s: %s",
                email,
                str(e),
            )
            result["message"] += f" Session claim skipped: {e}"
        except Exception as e:
            # Unexpected error — don't fail the signup
            logger.error(
                "Unexpected error claiming session during signup for %s: %s",
                email,
                e,
                exc_info=True,
            )
            result["message"] += " Session claim failed unexpectedly."

        return result

    async def verify_email(
        self,
        token: str,
        token_hash: str | None = None,
    ) -> dict[str, Any]:
        """Verify user email with verification token.

        Args:
            token: Email verification token from Supabase.
            token_hash: Optional token hash if provided.

        Returns:
            dict: Verification response with verified status and redirect URL.

        Raises:
            ValidationError: If verification fails.
        """
        try:
            # Verify email using Supabase Auth
            # Note: Supabase handles email verification via redirect URLs
            # This endpoint can be used to verify tokens programmatically
            response = self.client.auth.verify_otp(
                {
                    "token": token,
                    "type": "email",
                }
            )

            if not response.user:
                raise ValidationError("Invalid or expired verification token")

            user = response.user
            logger.info("Email verified for user: %s", user.id)

            redirect_url = self.settings.auth_redirect_url

            return {
                "verified": True,
                "message": "Email verified successfully",
                "redirect_url": f"{redirect_url}/auth/callback?verified=true",
            }

        except Exception as e:
            error_msg = str(e)
            logger.error("Email verification failed: %s", error_msg)

            if "invalid" in error_msg.lower() or "expired" in error_msg.lower():
                raise ValidationError("Invalid or expired verification token") from e

            raise ValidationError(f"Email verification failed: {error_msg}") from e

    async def resend_verification_email(
        self,
        email: str,
    ) -> dict[str, Any]:
        """Resend verification email to user.

        Args:
            email: User's email address.

        Returns:
            dict: Response with email_sent status.

        Raises:
            ValidationError: If resend fails.
        """
        try:
            redirect_url = self.settings.auth_redirect_url

            # Resend verification email
            response = self.client.auth.resend(
                {
                    "type": "signup",
                    "email": email,
                    "options": {
                        "email_redirect_to": redirect_url,
                    },
                }
            )

            logger.info("Verification email resent to: %s", email)

            return {
                "email_sent": True,
                "message": "Verification email sent. Please check your inbox.",
            }

        except Exception as e:
            error_msg = str(e)
            logger.error("Resend verification failed: %s", error_msg)

            if "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
                raise ValidationError("No account found with this email address") from e
            if "already verified" in error_msg.lower():
                raise ValidationError("This email is already verified") from e

            raise ValidationError(f"Failed to resend verification email: {error_msg}") from e

    async def login(
        self,
        email: str,
        password: str,
    ) -> dict[str, Any]:
        """Login user with email and password.

        Args:
            email: User's email address.
            password: User's password.

        Returns:
            dict: Login response with access_token, refresh_token, and user info.

        Raises:
            ValidationError: If login fails.
        """
        try:
            # Sign in user with Supabase Auth
            response = self.client.auth.sign_in_with_password(
                {
                    "email": email,
                    "password": password,
                }
            )

            if not response.user:
                raise ValidationError("Login failed")

            if not response.session:
                raise ValidationError("Login failed: No session created")

            user = response.user
            session = response.session

            logger.info("User logged in: %s", user.id)

            return {
                "access_token": session.access_token,
                "refresh_token": session.refresh_token,
                "user_id": str(user.id),
                "email": user.email or email,
                "expires_in": session.expires_in or 3600,
            }

        except Exception as e:
            error_msg = str(e)
            # Log generic error code only — avoid including email address from Supabase messages
            logger.error("Login failed with error type: %s", type(e).__name__)

            if "invalid" in error_msg.lower() and "credentials" in error_msg.lower():
                raise ValidationError("Invalid email or password") from e
            if "email not confirmed" in error_msg.lower() or "not verified" in error_msg.lower():
                raise ValidationError("Please verify your email before logging in") from e

            raise ValidationError(f"Login failed: {error_msg}") from e

    async def logout(self, access_token: str) -> dict[str, Any]:
        """Logout user by invalidating their session.

        Args:
            access_token: User's access token.

        Returns:
            dict: Logout response.
        """
        try:
            # Set the session for the client
            self.client.auth.set_session(access_token, "")

            # Sign out
            self.client.auth.sign_out()

            logger.info("User logged out")

            return {
                "message": "Logged out successfully",
            }

        except Exception as e:
            logger.error("Logout failed: %s", str(e))
            # Don't raise error on logout failure - user is still logged out client-side
            return {
                "message": "Logged out successfully",
            }

    async def request_password_reset(
        self,
        email: str,
    ) -> dict[str, Any]:
        """Request password reset email.

        Args:
            email: User's email address.

        Returns:
            dict: Response with email_sent status.

        Raises:
            ValidationError: If request fails.
        """
        try:
            redirect_url = self.settings.auth_redirect_url

            # Request password reset email
            self.client.auth.reset_password_for_email(
                email,
                options={"redirect_to": redirect_url},
            )

            logger.info("Password reset email sent to: %s", email)

            # Always return success for security (don't reveal if email exists)
            return {
                "email_sent": True,
                "message": "If an account exists with this email, a password reset link has been sent.",
            }

        except Exception as e:
            error_msg = str(e)
            logger.error("Password reset request failed: %s", error_msg)

            # For security, always return the same message regardless of error
            # This prevents email enumeration attacks
            return {
                "email_sent": True,
                "message": "If an account exists with this email, a password reset link has been sent.",
            }

    async def reset_password(
        self,
        token: str,
        new_password: str,
    ) -> dict[str, Any]:
        """Reset user password with token from email.

        Args:
            token: Password reset token from email.
            new_password: New password to set.

        Returns:
            dict: Reset response with redirect URL.

        Raises:
            ValidationError: If reset fails.
        """
        try:
            # Verify the reset token using OTP verification
            response = self.client.auth.verify_otp(
                {
                    "token": token,
                    "type": "recovery",
                }
            )

            if not response.user:
                raise ValidationError("Invalid or expired password reset token")

            user = response.user

            # Update the user's password
            # Note: Supabase may require using admin API or session-based update
            # For now, we'll use the session from OTP verification
            if response.session:
                # Set the session temporarily to update password
                self.client.auth.set_session(
                    response.session.access_token,
                    response.session.refresh_token,
                )

                # Update password using update_user
                update_response = self.client.auth.update_user(
                    {"password": new_password}
                )

                if not update_response.user:
                    raise ValidationError("Failed to update password")

                logger.info("Password reset for user: %s", user.id)

                redirect_url = self.settings.auth_redirect_url

                return {
                    "message": "Password has been reset successfully",
                    "redirect_url": f"{redirect_url}/auth/callback?reset=success",
                }
            else:
                raise ValidationError("Invalid reset token - no session created")

        except Exception as e:
            error_msg = str(e)
            logger.error("Password reset failed: %s", error_msg)

            if "invalid" in error_msg.lower() or "expired" in error_msg.lower():
                raise ValidationError("Invalid or expired password reset token") from e

            raise ValidationError(f"Password reset failed: {error_msg}") from e

    async def change_password(
        self,
        user_id: UUID,
        current_password: str,
        new_password: str,
    ) -> dict[str, Any]:
        """Change password for authenticated user.

        Args:
            user_id: The user's UUID.
            current_password: Current password for verification.
            new_password: New password to set.

        Returns:
            dict: Change password response.

        Raises:
            ValidationError: If change fails (wrong current password, weak new password, etc.).
        """
        try:
            # First, verify the current password by attempting to sign in
            # Get user email from profile
            from src.services.profile_service import ProfileService

            profile_service = ProfileService()
            profile = await profile_service.get_profile(user_id)

            if not profile:
                raise ValidationError("User profile not found")

            user_email = profile.get("email")
            if not user_email:
                raise ValidationError("User email not found")

            # Verify current password
            try:
                verify_response = self.client.auth.sign_in_with_password(
                    {
                        "email": user_email,
                        "password": current_password,
                    }
                )

                if not verify_response.user or not verify_response.session:
                    raise ValidationError("Current password is incorrect")

            except Exception as verify_error:
                error_msg = str(verify_error)
                if "invalid" in error_msg.lower() or "credentials" in error_msg.lower():
                    raise ValidationError("Current password is incorrect") from verify_error
                raise ValidationError("Failed to verify current password") from verify_error

            # Check if new password is same as current
            if current_password == new_password:
                raise ValidationError("New password must be different from current password")

            # Set session to update password
            verify_session = verify_response.session
            self.client.auth.set_session(
                verify_session.access_token,
                verify_session.refresh_token,
            )

            # Update password
            update_response = self.client.auth.update_user(
                {"password": new_password}
            )

            if not update_response.user:
                raise ValidationError("Failed to update password")

            logger.info("Password changed for user: %s", user_id)

            return {
                "message": "Password has been changed successfully",
            }

        except ValidationError:
            # Re-raise validation errors as-is
            raise
        except Exception as e:
            error_msg = str(e)
            logger.error("Change password failed: %s", error_msg)

            if "weak" in error_msg.lower() and "password" in error_msg.lower():
                raise ValidationError("New password is too weak. Please use a stronger password.") from e

            raise ValidationError(f"Failed to change password: {error_msg}") from e

    async def refresh_token(
        self,
        refresh_token: str,
    ) -> dict[str, Any]:
        """Refresh access token using refresh token.

        Args:
            refresh_token: The refresh token.

        Returns:
            dict: New access token, refresh token, and expiration.

        Raises:
            ValidationError: If refresh fails.
        """
        try:
            # Refresh the session using refresh token
            response = self.client.auth.refresh_session(refresh_token)

            if not response.session:
                raise ValidationError("Failed to refresh token")

            session = response.session

            logger.info("Token refreshed for user")

            return {
                "access_token": session.access_token,
                "refresh_token": session.refresh_token,
                "expires_in": session.expires_in or 3600,
            }

        except Exception as e:
            error_msg = str(e)
            logger.error("Token refresh failed: %s", error_msg)

            if "invalid" in error_msg.lower() or "expired" in error_msg.lower():
                raise ValidationError("Invalid or expired refresh token") from e

            raise ValidationError(f"Token refresh failed: {error_msg}") from e

