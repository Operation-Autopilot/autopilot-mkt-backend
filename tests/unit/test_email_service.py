"""Unit tests for email_service — IDEA-10: Auto-invite reminders."""

from unittest.mock import MagicMock, patch

import pytest

from src.services.email_service import EmailService


class TestIDEA10InvitationReminderEmail:
    """IDEA-10: EmailService should support sending invitation reminder emails."""

    def test_has_reminder_method(self) -> None:
        """IDEA-10: EmailService should have send_invitation_reminder_email method."""
        with patch("src.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock()
            service = EmailService()
            assert hasattr(service, "send_invitation_reminder_email"), \
                "EmailService should have send_invitation_reminder_email method"

    @pytest.mark.asyncio
    async def test_reminder_sends_with_reminder_subject(self) -> None:
        """IDEA-10: Reminder email should have 'reminder' in subject."""
        with patch("src.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key="test-key",
                email_from_address="test@test.com",
                frontend_url="https://test.com",
            )
            with patch("src.services.email_service.resend") as mock_resend:
                mock_resend.Emails.send.return_value = {"id": "test-email-id"}

                service = EmailService()
                result = await service.send_invitation_reminder_email(
                    to_email="user@test.com",
                    inviter_name="Alice",
                    company_name="TestCo",
                    invitation_id="test-invitation-id",
                )

                assert result.get("success") is True
                call_args = mock_resend.Emails.send.call_args[0][0]
                assert "reminder" in call_args["subject"].lower(), \
                    f"Subject should contain 'reminder', got: {call_args['subject']}"


class TestHTMLEscaping:
    """Tests for HTML injection prevention in email templates."""

    @pytest.mark.asyncio
    async def test_inviter_name_with_script_tag_escaped(self) -> None:
        """Test that <script> tags in inviter_name are escaped."""
        with patch("src.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key="test-key",
                email_from_address="test@test.com",
                frontend_url="https://test.com",
            )
            with patch("src.services.email_service.resend") as mock_resend:
                mock_resend.Emails.send.return_value = {"id": "test-email-id"}

                service = EmailService()
                await service.send_invitation_email(
                    to_email="user@test.com",
                    inviter_name='<script>alert("xss")</script>',
                    company_name="TestCo",
                    invitation_id="test-id",
                )

                call_args = mock_resend.Emails.send.call_args[0][0]
                html_content = call_args["html"]
                assert "<script>" not in html_content
                assert "&lt;script&gt;" in html_content

    @pytest.mark.asyncio
    async def test_company_name_with_html_escaped(self) -> None:
        """Test that HTML in company_name is escaped."""
        with patch("src.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key="test-key",
                email_from_address="test@test.com",
                frontend_url="https://test.com",
            )
            with patch("src.services.email_service.resend") as mock_resend:
                mock_resend.Emails.send.return_value = {"id": "test-email-id"}

                service = EmailService()
                await service.send_invitation_email(
                    to_email="user@test.com",
                    inviter_name="Alice",
                    company_name='<img src=x onerror="alert(1)">',
                    invitation_id="test-id",
                )

                call_args = mock_resend.Emails.send.call_args[0][0]
                html_content = call_args["html"]
                assert '<img src=x' not in html_content
                assert "&lt;img" in html_content

    @pytest.mark.asyncio
    async def test_welcome_email_display_name_escaped(self) -> None:
        """Test that HTML in display_name is escaped in welcome email."""
        with patch("src.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key="test-key",
                email_from_address="test@test.com",
                frontend_url="https://test.com",
            )
            with patch("src.services.email_service.resend") as mock_resend:
                mock_resend.Emails.send.return_value = {"id": "test-email-id"}

                service = EmailService()
                await service.send_welcome_email(
                    to_email="user@test.com",
                    display_name='<b onmouseover="alert(1)">Bob</b>',
                )

                call_args = mock_resend.Emails.send.call_args[0][0]
                html_content = call_args["html"]
                assert '<b onmouseover' not in html_content
                assert "&lt;b" in html_content
