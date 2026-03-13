"""Invitation API routes for accepting/declining invitations."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from src.api.deps import CurrentUser
from src.schemas.company import InvitationResponse, InvitationStatusCheck, InvitationWithCompany
from src.services.invitation_service import InvitationService
from src.services.profile_service import ProfileService

router = APIRouter(prefix="/invitations", tags=["invitations"])


@router.get(
    "/{invitation_id}/status",
    response_model=InvitationStatusCheck,
    summary="Check invitation status (public)",
    description="Returns invitation status without requiring authentication. No PII is exposed.",
)
async def check_invitation_status(invitation_id: UUID) -> InvitationStatusCheck:
    """Check the status of an invitation (public, no auth required).

    Args:
        invitation_id: The invitation's UUID.

    Returns:
        InvitationStatusCheck: Status, company name, and expiration flag.

    Raises:
        HTTPException: 404 if invitation not found.
    """
    service = InvitationService()
    invitation = await service.get_invitation(invitation_id)

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    company_data = invitation.get("companies", {})
    company_name = company_data.get("name", "Unknown") if company_data else "Unknown"

    expired = False
    expires_at = invitation.get("expires_at")
    if expires_at:
        if isinstance(expires_at, str):
            exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        else:
            exp_dt = expires_at
        if exp_dt.tzinfo is None:
            exp_dt = exp_dt.replace(tzinfo=timezone.utc)
        expired = datetime.now(timezone.utc) > exp_dt

    return InvitationStatusCheck(
        status=invitation["status"],
        company_name=company_name,
        expired=expired,
    )


async def _get_user_profile_id(user: CurrentUser) -> UUID:
    """Get the profile ID for a user, creating profile if needed."""
    service = ProfileService()
    profile = await service.get_or_create_profile(user.user_id, user.email)
    return UUID(profile["id"])


@router.get(
    "",
    response_model=list[InvitationWithCompany],
    summary="List my invitations",
    description="Returns all pending invitations for the authenticated user's email.",
)
async def list_my_invitations(user: CurrentUser) -> list[InvitationWithCompany]:
    """List all pending invitations for the current user.

    Args:
        user: The authenticated user context.

    Returns:
        list[InvitationWithCompany]: List of pending invitations with company info.
    """
    if not user.email:
        return []

    service = InvitationService()
    invitations = await service.list_user_invitations(user.email)

    result = []
    for inv in invitations:
        company_data = inv.get("companies", {})
        result.append(
            InvitationWithCompany(
                id=inv["id"],
                company_id=inv["company_id"],
                email=inv["email"],
                invited_by=inv["invited_by"],
                status=inv["status"],
                expires_at=inv["expires_at"],
                created_at=inv["created_at"],
                accepted_at=inv.get("accepted_at"),
                company_name=company_data.get("name", "Unknown"),
            )
        )

    return result


@router.post(
    "/{invitation_id}/accept",
    response_model=InvitationResponse,
    summary="Accept invitation",
    description="Accepts an invitation and joins the company.",
)
async def accept_invitation(
    invitation_id: UUID,
    user: CurrentUser,
) -> InvitationResponse:
    """Accept an invitation to join a company.

    Args:
        invitation_id: The invitation's UUID.
        user: The authenticated user context.

    Returns:
        InvitationResponse: The updated invitation.

    Raises:
        HTTPException: 400 if invitation invalid/expired, 404 if not found.
    """
    if not user.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address required to accept invitation",
        )

    profile_id = await _get_user_profile_id(user)
    service = InvitationService()

    invitation = await service.accept_invitation(invitation_id, profile_id, user.email)
    return InvitationResponse(**invitation)


@router.post(
    "/{invitation_id}/decline",
    response_model=InvitationResponse,
    summary="Decline invitation",
    description="Declines an invitation.",
)
async def decline_invitation(
    invitation_id: UUID,
    user: CurrentUser,
) -> InvitationResponse:
    """Decline an invitation to join a company.

    Args:
        invitation_id: The invitation's UUID.
        user: The authenticated user context.

    Returns:
        InvitationResponse: The updated invitation.

    Raises:
        HTTPException: 400 if invitation not pending, 404 if not found.
    """
    if not user.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address required to decline invitation",
        )

    service = InvitationService()
    invitation = await service.decline_invitation(invitation_id, user.email)
    return InvitationResponse(**invitation)
