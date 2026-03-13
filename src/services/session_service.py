"""Session business logic service."""

import hashlib
import logging
import secrets
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID

from src.core.supabase import get_supabase_client
from src.schemas.session import SessionUpdate
from src.services.base_service import BaseService

if TYPE_CHECKING:
    from src.services.checkout_service import CheckoutService

logger = logging.getLogger(__name__)


class SessionService(BaseService):
    """Service for managing anonymous user sessions."""

    TOKEN_LENGTH = 64  # Length of session token in characters

    def __init__(self, checkout_service: "CheckoutService | None" = None) -> None:
        """Initialize session service with Supabase client.

        Args:
            checkout_service: Optional checkout service for order transfer on claim.
        """
        self.client = get_supabase_client()
        self._checkout_service = checkout_service

    def _generate_token(self) -> str:
        """Generate a cryptographically secure session token.

        Returns:
            str: A 64-character hex token.
        """
        return secrets.token_hex(self.TOKEN_LENGTH // 2)

    @staticmethod
    def _hash_token(token: str) -> str:
        """Hash a session token using SHA-256 for secure storage.

        Args:
            token: The raw session token.

        Returns:
            str: The hex-encoded SHA-256 hash of the token.
        """
        return hashlib.sha256(token.encode()).hexdigest()

    async def create_session(self) -> tuple[dict[str, Any], str]:
        """Create a new session with a unique token.

        Returns:
            tuple: (session_data, session_token)
        """
        token = self._generate_token()
        token_hash = self._hash_token(token)

        session_data = {
            "session_token": token_hash,  # store hash, not raw token
            "current_question_index": 0,
            "phase": "discovery",
            "answers": {},
            "selected_product_ids": [],
            "metadata": {},
        }

        query = (
            self.client.table("sessions")
            .insert(session_data)
        )
        response = await self._execute_sync(query)

        if not response.data:
            raise ValueError("Database operation returned no data")
        return response.data[0], token  # return raw token to caller

    async def get_session_by_token(self, token: str) -> dict[str, Any] | None:
        """Get a session by its token.

        Returns None if session not found or expired.

        Args:
            token: The session token from cookie.

        Returns:
            dict | None: The session data or None if not found/expired.
        """
        token_hash = self._hash_token(token)
        query = (
            self.client.table("sessions")
            .select("*")
            .eq("session_token", token_hash)
            .maybe_single()
        )
        response = await self._execute_sync(query)

        if not response or not response.data:
            return None

        session = response.data

        # Check if session is expired
        expires_at = session.get("expires_at")
        if expires_at:
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if expires_at < datetime.now(timezone.utc):
                return None

        return session

    async def get_session_by_id(self, session_id: UUID) -> dict[str, Any] | None:
        """Get a session by its ID.

        Args:
            session_id: The session UUID.

        Returns:
            dict | None: The session data or None if not found.
        """
        query = (
            self.client.table("sessions")
            .select("*")
            .eq("id", str(session_id))
            .maybe_single()
        )
        response = await self._execute_sync(query)

        return response.data if response and response.data else None

    async def update_session(
        self,
        session_id: UUID,
        data: SessionUpdate,
    ) -> dict[str, Any] | None:
        """Update a session.

        Args:
            session_id: The session UUID.
            data: The fields to update.

        Returns:
            dict | None: The updated session data or None if not found.
        """
        update_data = data.model_dump(exclude_unset=True, exclude_none=True)

        # Convert nested Pydantic models to dicts for JSONB storage
        if "answers" in update_data:
            update_data["answers"] = {
                k: v.model_dump() if hasattr(v, "model_dump") else v
                for k, v in update_data["answers"].items()
            }
        if "roi_inputs" in update_data and update_data["roi_inputs"]:
            roi = update_data["roi_inputs"]
            update_data["roi_inputs"] = roi.model_dump() if hasattr(roi, "model_dump") else roi
        if "greenlight" in update_data and update_data["greenlight"]:
            greenlight = update_data["greenlight"]
            if hasattr(greenlight, "model_dump"):
                greenlight_dict = greenlight.model_dump()
                # Convert nested team_members Pydantic models
                if "team_members" in greenlight_dict:
                    greenlight_dict["team_members"] = [
                        m.model_dump() if hasattr(m, "model_dump") else m
                        for m in greenlight_dict["team_members"]
                    ]
                update_data["greenlight"] = greenlight_dict
            else:
                update_data["greenlight"] = greenlight

        # Convert UUID list to string list for PostgreSQL
        if "selected_product_ids" in update_data:
            update_data["selected_product_ids"] = [
                str(uid) for uid in update_data["selected_product_ids"]
            ]

        if not update_data:
            # No changes, return current session
            return await self.get_session_by_id(session_id)

        query = (
            self.client.table("sessions")
            .update(update_data)
            .eq("id", str(session_id))
        )
        response = await self._execute_sync(query)

        return response.data[0] if response.data else None

    async def is_session_valid(self, token: str) -> bool:
        """Check if a session token is valid and not expired.

        Args:
            token: The session token to validate.

        Returns:
            bool: True if session is valid and not expired.
        """
        session = await self.get_session_by_token(token)

        if not session:
            return False

        # Check if session is expired
        expires_at = session.get("expires_at")
        if expires_at:
            # Parse the timestamp string
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if expires_at < datetime.now(timezone.utc):
                return False

        # Check if session has been claimed
        if session.get("claimed_by_profile_id"):
            return False

        return True

    async def set_conversation(
        self,
        session_id: UUID,
        conversation_id: UUID,
    ) -> dict[str, Any] | None:
        """Set the conversation ID for a session.

        Args:
            session_id: The session UUID.
            conversation_id: The conversation UUID to link.

        Returns:
            dict | None: The updated session data or None if not found.
        """
        query = (
            self.client.table("sessions")
            .update({"conversation_id": str(conversation_id)})
            .eq("id", str(session_id))
        )
        response = await self._execute_sync(query)

        return response.data[0] if response.data else None

    async def check_conflict(
        self,
        session_id: UUID,
        profile_id: UUID,
    ) -> dict[str, Any]:
        """Check if both anonymous session and account have meaningful data.

        Args:
            session_id: The anonymous session UUID.
            profile_id: The authenticated user's profile UUID.

        Returns:
            dict with has_conflict, anonymous summary, and account summary.
        """
        # Get anonymous session data
        session = await self.get_session_by_id(session_id)
        anon_answers = session.get("answers", {}) if session else {}
        anon_phase = session.get("phase", "discovery") if session else "discovery"

        # Count anonymous conversation messages
        anon_msg_count = 0
        conversation_id = session.get("conversation_id") if session else None
        if conversation_id:
            msg_query = (
                self.client.table("messages")
                .select("id", count="exact")
                .eq("conversation_id", str(conversation_id))
            )
            msg_response = await self._execute_sync(msg_query)
            anon_msg_count = msg_response.count if msg_response.count else 0

        # Get account discovery profile
        dp_query = (
            self.client.table("discovery_profiles")
            .select("*")
            .eq("profile_id", str(profile_id))
            .limit(1)
        )
        dp_response = await self._execute_sync(dp_query)
        acct_profile = dp_response.data[0] if dp_response.data else None

        acct_answers = acct_profile.get("answers", {}) if acct_profile else {}
        acct_phase = acct_profile.get("phase", "discovery") if acct_profile else "discovery"

        # Count account conversation messages
        acct_msg_count = 0
        conv_query = (
            self.client.table("conversations")
            .select("id")
            .eq("profile_id", str(profile_id))
            .limit(1)
        )
        conv_response = await self._execute_sync(conv_query)
        if conv_response.data:
            acct_conv_id = conv_response.data[0]["id"]
            acct_msg_query = (
                self.client.table("messages")
                .select("id", count="exact")
                .eq("conversation_id", str(acct_conv_id))
            )
            acct_msg_response = await self._execute_sync(acct_msg_query)
            acct_msg_count = acct_msg_response.count if acct_msg_response.count else 0

        anon_summary = {
            "message_count": anon_msg_count,
            "answer_count": len(anon_answers),
            "phase": anon_phase,
        }
        acct_summary = {
            "message_count": acct_msg_count,
            "answer_count": len(acct_answers),
            "phase": acct_phase,
        }

        # Conflict = both sides have meaningful data
        anon_meaningful = anon_msg_count > 0 or len(anon_answers) > 0 or anon_phase != "discovery"
        acct_meaningful = acct_msg_count > 0 or len(acct_answers) > 0 or acct_phase != "discovery"

        return {
            "has_conflict": anon_meaningful and acct_meaningful,
            "anonymous": anon_summary,
            "account": acct_summary,
        }

    async def claim_session(
        self,
        session_id: UUID,
        profile_id: UUID,
        company_id: UUID | None = None,
        merge_strategy: str = "keep_account",
    ) -> dict[str, Any]:
        """Claim a session and merge its data to a user profile.

        This transfers all session data (answers, ROI inputs, selections) to
        the user's discovery profile, transfers conversation ownership, and
        transfers any orders to the user's profile.

        Args:
            session_id: The session UUID to claim.
            profile_id: The profile UUID to claim the session for.
            company_id: Optional company UUID for company-scoped discovery.
            merge_strategy: "keep_account" preserves existing profile data (default),
                "keep_session" overwrites with anonymous session data.

        Returns:
            dict: Result containing discovery_profile, conversation_transferred,
                and orders_transferred count.

        Raises:
            ValueError: If session not found, already claimed, or expired.
        """
        # Get the session
        session = await self.get_session_by_id(session_id)
        if not session:
            raise ValueError("Session not found")

        # Check if expired
        expires_at = session.get("expires_at")
        if expires_at:
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if expires_at < datetime.now(timezone.utc):
                raise ValueError("Session has expired")

        # Resolve company_id if not provided
        if not company_id:
            try:
                from src.services.company_service import CompanyService
                company_service = CompanyService()
                company = await company_service.get_user_company(profile_id)
                if company:
                    company_id = UUID(company["id"])
            except Exception as e:
                logger.warning("Failed to resolve company for session claim: %s", e)

        # Atomically claim the session — prevents double-claim race condition
        # The WHERE clause ensures only one request can succeed
        claim_query = (
            self.client.table("sessions")
            .update({"claimed_by_profile_id": str(profile_id)})
            .eq("id", str(session_id))
            .is_("claimed_by_profile_id", "null")
        )
        claim_response = await self._execute_sync(claim_query)
        if not claim_response.data:
            raise ValueError("Session has already been claimed")

        # Create or update discovery profile with session data
        discovery_profile = await self._create_or_update_discovery_profile(
            profile_id=profile_id,
            session=session,
            company_id=company_id,
            merge_strategy=merge_strategy,
        )

        # Transfer conversation ownership if exists
        conversation_transferred = False
        conversation_id = session.get("conversation_id")
        if conversation_id:
            try:
                await self._transfer_conversation_ownership(
                    conversation_id=UUID(conversation_id) if isinstance(conversation_id, str) else conversation_id,
                    profile_id=profile_id,
                    merge_strategy=merge_strategy,
                )
                conversation_transferred = True
            except Exception as e:
                logger.warning("Failed to transfer conversation %s: %s", conversation_id, e)
                conversation_transferred = False

        # Transfer orders to the profile if checkout service is available
        orders_transferred = 0
        if self._checkout_service:
            orders_transferred = await self._checkout_service.transfer_orders_to_profile(
                session_id=session_id,
                profile_id=profile_id,
            )

        return {
            "discovery_profile": discovery_profile,
            "conversation_transferred": conversation_transferred,
            "orders_transferred": orders_transferred,
        }

    async def _create_or_update_discovery_profile(
        self,
        profile_id: UUID,
        session: dict[str, Any],
        company_id: UUID | None = None,
        merge_strategy: str = "keep_account",
    ) -> dict[str, Any]:
        """Create or update a discovery profile from session data.

        Args:
            profile_id: The profile UUID.
            session: The session data to copy.
            company_id: Optional company UUID for company-scoped profiles.
            merge_strategy: "keep_account" preserves existing profile data,
                "keep_session" overwrites with session data.

        Returns:
            dict: The created or updated discovery profile.
        """
        # Check if discovery profile exists (company-scoped or personal)
        existing_profile = None
        if company_id:
            query = (
                self.client.table("discovery_profiles")
                .select("*")
                .eq("company_id", str(company_id))
                .maybe_single()
            )
            response = await self._execute_sync(query)
            if response and response.data:
                existing_profile = response.data

        if not existing_profile:
            query = (
                self.client.table("discovery_profiles")
                .select("*")
                .eq("profile_id", str(profile_id))
            )
            existing = await self._execute_sync(query)
            if existing.data:
                existing_profile = existing.data[0]

        if existing_profile:
            merged_data: dict[str, Any] = {}

            if merge_strategy == "keep_session":
                # Session data overwrites account data
                session_index = session.get("current_question_index", 0)
                if session_index:
                    merged_data["current_question_index"] = session_index

                session_phase = session.get("phase", "discovery")
                if session_phase != "discovery":
                    merged_data["phase"] = session_phase

                session_answers = session.get("answers", {}) or {}
                if session_answers:
                    merged_data["answers"] = session_answers

                if session.get("roi_inputs"):
                    merged_data["roi_inputs"] = session["roi_inputs"]

                session_products = session.get("selected_product_ids", []) or []
                if session_products:
                    merged_data["selected_product_ids"] = session_products

                if session.get("timeframe"):
                    merged_data["timeframe"] = session["timeframe"]

                if session.get("greenlight"):
                    merged_data["greenlight"] = session["greenlight"]
            else:
                # keep_account: only update empty/default fields, preserve existing progress
                session_index = session.get("current_question_index", 0)
                existing_index = existing_profile.get("current_question_index", 0)
                if session_index > existing_index:
                    merged_data["current_question_index"] = session_index

                existing_phase = existing_profile.get("phase", "discovery")
                session_phase = session.get("phase", "discovery")
                if existing_phase == "discovery" and session_phase in ["roi", "greenlight"]:
                    merged_data["phase"] = session_phase

                existing_answers = existing_profile.get("answers", {}) or {}
                session_answers = session.get("answers", {}) or {}
                if session_answers:
                    merged_answers = {**existing_answers, **session_answers}
                    if merged_answers != existing_answers:
                        merged_data["answers"] = merged_answers

                if not existing_profile.get("roi_inputs") and session.get("roi_inputs"):
                    merged_data["roi_inputs"] = session["roi_inputs"]

                existing_products = existing_profile.get("selected_product_ids", []) or []
                session_products = session.get("selected_product_ids", []) or []
                if not existing_products and session_products:
                    merged_data["selected_product_ids"] = session_products

                if not existing_profile.get("timeframe") and session.get("timeframe"):
                    merged_data["timeframe"] = session["timeframe"]

                if not existing_profile.get("greenlight") and session.get("greenlight"):
                    merged_data["greenlight"] = session["greenlight"]

            # Link to company if not already linked
            if company_id and not existing_profile.get("company_id"):
                merged_data["company_id"] = str(company_id)

            # Only update if there's something to merge
            if merged_data:
                query = (
                    self.client.table("discovery_profiles")
                    .update(merged_data)
                    .eq("id", existing_profile["id"])
                )
                response = await self._execute_sync(query)
                if response.data and len(response.data) > 0:
                    return response.data[0]
                return existing_profile
            else:
                # Nothing to merge, return existing profile as-is
                return existing_profile
        else:
            # Create new profile with session data
            profile_data: dict[str, Any] = {
                "profile_id": str(profile_id),
                "current_question_index": session.get("current_question_index", 0),
                "phase": session.get("phase", "discovery"),
                "answers": session.get("answers", {}),
                "roi_inputs": session.get("roi_inputs"),
                "selected_product_ids": session.get("selected_product_ids", []),
                "timeframe": session.get("timeframe"),
                "greenlight": session.get("greenlight"),
            }
            if company_id:
                profile_data["company_id"] = str(company_id)
            query = (
                self.client.table("discovery_profiles")
                .insert(profile_data)
            )
            response = await self._execute_sync(query)
            if response.data and len(response.data) > 0:
                return response.data[0]
            raise ValueError("Failed to create discovery profile")

    async def _transfer_conversation_ownership(
        self,
        conversation_id: UUID,
        profile_id: UUID,
        merge_strategy: str = "keep_account",
    ) -> None:
        """Transfer conversation ownership from session to user profile.

        Behavior depends on merge_strategy:
        - keep_account: skip transfer if user already has conversations (preserve existing)
        - keep_session: always transfer the anonymous conversation

        Args:
            conversation_id: The conversation UUID.
            profile_id: The profile UUID to transfer to.
            merge_strategy: "keep_account" or "keep_session".
        """
        if merge_strategy == "keep_account":
            # Check if user already has conversations — preserve existing
            existing_query = (
                self.client.table("conversations")
                .select("id")
                .eq("profile_id", str(profile_id))
                .limit(1)
            )
            existing_response = await self._execute_sync(existing_query)
            if existing_response.data:
                logger.info(
                    "Skipping conversation transfer — user %s already has conversations (keep_account)",
                    profile_id,
                )
                return

        # Update conversation to be owned by the profile instead of session
        query = self.client.table("conversations").update(
            {"profile_id": str(profile_id), "session_id": None}
        ).eq("id", str(conversation_id))
        await self._execute_sync(query)

    async def cleanup_expired_sessions(self) -> int:
        """Delete expired sessions to prevent table bloat.

        Removes all sessions where expires_at is in the past.

        Returns:
            int: Number of sessions deleted.
        """
        now = datetime.now(timezone.utc).isoformat()

        # Delete expired sessions and get the count
        query = (
            self.client.table("sessions")
            .delete()
            .lt("expires_at", now)
        )
        response = await self._execute_sync(query)

        return len(response.data) if response.data else 0
