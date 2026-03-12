"""Email service using Resend for transactional emails."""

import html
import logging
from typing import Any
from urllib.parse import urlencode

import resend

from src.core.config import get_settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending transactional emails via Resend."""

    def __init__(self) -> None:
        """Initialize email service with Resend API key."""
        settings = get_settings()
        resend.api_key = settings.resend_api_key
        self.from_email = settings.email_from_address
        self.frontend_url = settings.frontend_url

    async def send_invitation_email(
        self,
        to_email: str,
        inviter_name: str,
        company_name: str,
        invitation_id: str,
        invitee_name: str | None = None,
    ) -> dict[str, Any]:
        """Send a company invitation email.

        Args:
            to_email: Recipient email address.
            inviter_name: Name of the person who sent the invite.
            company_name: Name of the company being invited to.
            invitation_id: UUID of the invitation for the accept link.
            invitee_name: Optional name of the invitee (for signup form prepopulation).

        Returns:
            dict: Resend API response with email ID.
        """
        params: dict[str, str] = {
            "email": to_email,
            "company": company_name,
            "inviter": inviter_name,
        }
        if invitee_name:
            params["name"] = invitee_name
        query_params = urlencode(params)
        accept_url = f"{self.frontend_url}/invitations/{invitation_id}/accept?{query_params}"

        safe_inviter = html.escape(inviter_name)
        safe_company = html.escape(company_name)

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>You're Invited!</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 10px 10px 0 0; text-align: center;">
        <h1 style="color: white; margin: 0; font-size: 24px;">You're Invited!</h1>
    </div>

    <div style="background: #f9fafb; padding: 30px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 10px 10px;">
        <p style="font-size: 16px; margin-bottom: 20px;">
            <strong>{safe_inviter}</strong> has invited you to join <strong>{safe_company}</strong> on Autopilot.
        </p>

        <p style="font-size: 14px; color: #6b7280; margin-bottom: 25px;">
            Autopilot helps companies discover and implement robotic automation solutions. Join your team to collaborate on finding the right robots for your facility.
        </p>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{accept_url}" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 14px 32px; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 16px; display: inline-block;">
                Accept Invitation
            </a>
        </div>

        <p style="font-size: 12px; color: #9ca3af; margin-top: 30px; text-align: center;">
            This invitation expires in 7 days. If you didn't expect this invitation, you can safely ignore this email.
        </p>

        <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 25px 0;">

        <p style="font-size: 12px; color: #9ca3af; text-align: center; margin: 0;">
            If the button doesn't work, copy and paste this link:<br>
            <a href="{accept_url}" style="color: #667eea; word-break: break-all;">{accept_url}</a>
        </p>
    </div>
</body>
</html>
"""

        text_content = f"""
You're Invited to {company_name}!

{inviter_name} has invited you to join {company_name} on Autopilot.

Autopilot helps companies discover and implement robotic automation solutions. Join your team to collaborate on finding the right robots for your facility.

Accept your invitation here:
{accept_url}

This invitation expires in 7 days. If you didn't expect this invitation, you can safely ignore this email.
"""

        try:
            response = resend.Emails.send({
                "from": self.from_email,
                "to": [to_email],
                "subject": f"You're invited to join {company_name} on Autopilot",
                "html": html_content,
                "text": text_content,
            })

            logger.info("Invitation email sent to %s, id: %s", to_email, response.get("id"))
            return {"success": True, "email_id": response.get("id")}

        except Exception as e:
            logger.error("Failed to send invitation email to %s: %s", to_email, str(e))
            return {"success": False, "error": str(e)}

    async def send_invitation_reminder_email(
        self,
        to_email: str,
        inviter_name: str,
        company_name: str,
        invitation_id: str,
        invitee_name: str | None = None,
    ) -> dict[str, Any]:
        """Send a reminder for a pending company invitation.

        Args:
            to_email: Recipient email address.
            inviter_name: Name of the person who sent the invite.
            company_name: Name of the company.
            invitation_id: UUID of the invitation.

        Returns:
            dict: Resend API response with email ID.
        """
        params: dict[str, str] = {
            "email": to_email,
            "company": company_name,
            "inviter": inviter_name,
        }
        if invitee_name:
            params["name"] = invitee_name
        query_params = urlencode(params)
        accept_url = f"{self.frontend_url}/invitations/{invitation_id}/accept?{query_params}"

        safe_inviter = html.escape(inviter_name)
        safe_company = html.escape(company_name)

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Reminder: You're Invited!</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 10px 10px 0 0; text-align: center;">
        <h1 style="color: white; margin: 0; font-size: 24px;">Friendly Reminder</h1>
    </div>
    <div style="background: #f9fafb; padding: 30px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 10px 10px;">
        <p style="font-size: 16px; margin-bottom: 20px;">
            <strong>{safe_inviter}</strong> invited you to join <strong>{safe_company}</strong> on Autopilot, and your invitation is still pending.
        </p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{accept_url}" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 14px 32px; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 16px; display: inline-block;">
                Accept Invitation
            </a>
        </div>
        <p style="font-size: 12px; color: #9ca3af; text-align: center;">
            This invitation will expire soon. If you didn't expect this, you can safely ignore this email.
        </p>
    </div>
</body>
</html>
"""

        try:
            response = resend.Emails.send({
                "from": self.from_email,
                "to": [to_email],
                "subject": f"Reminder: You're invited to join {company_name} on Autopilot",
                "html": html_content,
            })

            logger.info("Reminder email sent to %s, id: %s", to_email, response.get("id"))
            return {"success": True, "email_id": response.get("id")}

        except Exception as e:
            logger.error("Failed to send reminder email to %s: %s", to_email, str(e))
            return {"success": False, "error": str(e)}

    async def send_order_confirmation_email(
        self,
        to_email: str,
        robot_name: str,
        amount_display: str,
        payment_type: str,
        order_id: str,
        target_start_date: str | None = None,
    ) -> dict[str, Any]:
        """Send an order confirmation email after a successful purchase.

        Args:
            to_email: Recipient email address.
            robot_name: Name of the purchased robot.
            amount_display: Formatted price string (e.g. "$1,100/mo" or "$25,000").
            payment_type: "lease", "purchase", or "gynger".
            order_id: Internal order UUID for reference.
            target_start_date: Optional deployment target date.

        Returns:
            dict: Resend API response with email ID.
        """
        safe_robot = html.escape(robot_name)
        safe_amount = html.escape(amount_display)
        safe_order = html.escape(order_id[:8])

        payment_label = {
            "lease": "Monthly Lease (Stripe)",
            "purchase": "One-Time Purchase (Stripe)",
            "gynger": "B2B Financing (Gynger)",
        }.get(payment_type, payment_type.title())

        start_row = ""
        if target_start_date:
            safe_date = html.escape(target_start_date)
            start_row = f"""
            <tr>
                <td style="padding: 10px 15px; color: #6b7280; font-size: 14px; border-bottom: 1px solid #e5e7eb;">Target Start Date</td>
                <td style="padding: 10px 15px; font-size: 14px; border-bottom: 1px solid #e5e7eb;">{safe_date}</td>
            </tr>"""

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Order Confirmed</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 10px 10px 0 0; text-align: center;">
        <h1 style="color: white; margin: 0; font-size: 24px;">Order Confirmed</h1>
    </div>

    <div style="background: #f9fafb; padding: 30px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 10px 10px;">
        <p style="font-size: 16px; margin-bottom: 20px;">
            Your order for <strong>{safe_robot}</strong> has been confirmed. Here are your order details:
        </p>

        <table style="width: 100%; border-collapse: collapse; margin: 20px 0; background: white; border-radius: 8px; overflow: hidden; border: 1px solid #e5e7eb;">
            <tr>
                <td style="padding: 10px 15px; color: #6b7280; font-size: 14px; border-bottom: 1px solid #e5e7eb;">Robot</td>
                <td style="padding: 10px 15px; font-size: 14px; border-bottom: 1px solid #e5e7eb; font-weight: 600;">{safe_robot}</td>
            </tr>
            <tr>
                <td style="padding: 10px 15px; color: #6b7280; font-size: 14px; border-bottom: 1px solid #e5e7eb;">Amount</td>
                <td style="padding: 10px 15px; font-size: 14px; border-bottom: 1px solid #e5e7eb; font-weight: 600;">{safe_amount}</td>
            </tr>
            <tr>
                <td style="padding: 10px 15px; color: #6b7280; font-size: 14px; border-bottom: 1px solid #e5e7eb;">Payment</td>
                <td style="padding: 10px 15px; font-size: 14px; border-bottom: 1px solid #e5e7eb;">{html.escape(payment_label)}</td>
            </tr>
            <tr>
                <td style="padding: 10px 15px; color: #6b7280; font-size: 14px; border-bottom: 1px solid #e5e7eb;">Order Ref</td>
                <td style="padding: 10px 15px; font-size: 14px; border-bottom: 1px solid #e5e7eb; font-family: monospace;">{safe_order}</td>
            </tr>{start_row}
        </table>

        <p style="font-size: 14px; color: #6b7280; margin-bottom: 25px;">
            Our team will be in touch to coordinate deployment logistics. In the meantime, you can review and update your deployment details in Greenlight.
        </p>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{self.frontend_url}?phase=greenlight" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 14px 32px; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 16px; display: inline-block;">
                View Greenlight
            </a>
        </div>

        <p style="font-size: 12px; color: #9ca3af; margin-top: 30px; text-align: center;">
            If you have any questions, reply to this email or contact us at support@tryautopilot.com.
        </p>
    </div>
</body>
</html>
"""

        text_content = f"""
Order Confirmed

Your order for {robot_name} has been confirmed.

Robot: {robot_name}
Amount: {amount_display}
Payment: {payment_label}
Order Ref: {order_id[:8]}
{f"Target Start Date: {target_start_date}" if target_start_date else ""}

Our team will be in touch to coordinate deployment logistics.

View your Greenlight details: {self.frontend_url}?phase=greenlight

Questions? Reply to this email or contact support@tryautopilot.com.
"""

        try:
            response = resend.Emails.send({
                "from": self.from_email,
                "to": [to_email],
                "subject": f"Order Confirmed — {robot_name}",
                "html": html_content,
                "text": text_content,
            })

            logger.info("Order confirmation email sent to %s, id: %s", to_email, response.get("id"))
            return {"success": True, "email_id": response.get("id")}

        except Exception as e:
            logger.error("Failed to send order confirmation email to %s: %s", to_email, str(e))
            return {"success": False, "error": str(e)}

    async def send_welcome_email(
        self,
        to_email: str,
        display_name: str | None = None,
    ) -> dict[str, Any]:
        """Send a welcome email to new users.

        Args:
            to_email: Recipient email address.
            display_name: User's display name (optional).

        Returns:
            dict: Resend API response.
        """
        name = html.escape(display_name) if display_name else "there"

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Welcome to Autopilot!</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="text-align: center; padding: 30px 0;">
        <h1 style="color: #667eea; margin-bottom: 10px;">Welcome to Autopilot!</h1>
        <p style="font-size: 18px; color: #6b7280;">Hi {name}, we're excited to have you.</p>
    </div>

    <div style="background: #f9fafb; padding: 25px; border-radius: 10px; margin: 20px 0;">
        <p>You're now ready to discover the perfect robotic automation solutions for your facility.</p>
        <p>Get started by telling us about your operations, and we'll help you find robots that can transform your business.</p>
    </div>

    <div style="text-align: center; margin: 30px 0;">
        <a href="{self.frontend_url}" style="background: #667eea; color: white; padding: 12px 28px; text-decoration: none; border-radius: 6px; font-weight: 600;">
            Get Started
        </a>
    </div>
</body>
</html>
"""

        try:
            response = resend.Emails.send({
                "from": self.from_email,
                "to": [to_email],
                "subject": "Welcome to Autopilot!",
                "html": html_content,
            })

            logger.info("Welcome email sent to %s", to_email)
            return {"success": True, "email_id": response.get("id")}

        except Exception as e:
            logger.error("Failed to send welcome email to %s: %s", to_email, str(e))
            return {"success": False, "error": str(e)}
