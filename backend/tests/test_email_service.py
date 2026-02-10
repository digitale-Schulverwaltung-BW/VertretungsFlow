"""
Unit Tests für EmailService

Getestet:
- send_email()                          - SMTP-Versand, TLS-Logik, Error Handling
- send_absence_submitted_notification() - Alle Empfänger, Erfolgs-/Fehlerbedingungen
- send_absence_approved_notification()  - Lehrkraft + Planer
- send_absence_completed_notification() - Nur Lehrkraft
- send_absence_rejected_notification()  - Nur Lehrkraft mit Ablehnungs-Info
"""

import pytest
from unittest.mock import AsyncMock, patch

import aiosmtplib

from app.services.email_service import EmailService


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def service():
    """EmailService with test SMTP configuration"""
    svc = EmailService()
    svc.host = "smtp.test.local"
    svc.port = 587
    svc.username = "testuser"
    svc.password = "testpass"
    svc.from_email = "absenzflow@test.de"
    svc.use_tls = True
    return svc


# ============================================================================
# Test send_email()
# ============================================================================


class TestSendEmail:
    """Test base SMTP send with TLS selection and error handling"""

    @pytest.mark.asyncio
    @patch("aiosmtplib.send", new_callable=AsyncMock)
    async def test_returns_true_on_success(self, mock_smtp_send, service):
        """Test that successful send returns True"""
        result = await service.send_email("lehrer@schule.de", "Betreff", "Nachricht")

        assert result is True
        mock_smtp_send.assert_called_once()

    @pytest.mark.asyncio
    @patch("aiosmtplib.send", new_callable=AsyncMock)
    async def test_port_587_uses_starttls(self, mock_smtp_send, service):
        """Test that port 587 sends with start_tls=True (STARTTLS)"""
        service.port = 587
        await service.send_email("lehrer@schule.de", "Betreff", "Nachricht")

        call_kwargs = mock_smtp_send.call_args[1]
        assert call_kwargs.get("start_tls") is True
        assert "use_tls" not in call_kwargs

    @pytest.mark.asyncio
    @patch("aiosmtplib.send", new_callable=AsyncMock)
    async def test_port_465_uses_implicit_tls(self, mock_smtp_send, service):
        """Test that port 465 sends with use_tls=True (SMTPS)"""
        service.port = 465
        await service.send_email("lehrer@schule.de", "Betreff", "Nachricht")

        call_kwargs = mock_smtp_send.call_args[1]
        assert call_kwargs.get("use_tls") is True
        assert "start_tls" not in call_kwargs

    @pytest.mark.asyncio
    @patch("aiosmtplib.send", new_callable=AsyncMock)
    async def test_port_25_no_tls(self, mock_smtp_send, service):
        """Test that port 25 without use_tls sends without TLS params"""
        service.port = 25
        service.use_tls = False
        await service.send_email("lehrer@schule.de", "Betreff", "Nachricht")

        call_kwargs = mock_smtp_send.call_args[1]
        assert "use_tls" not in call_kwargs
        assert "start_tls" not in call_kwargs

    @pytest.mark.asyncio
    @patch(
        "aiosmtplib.send",
        side_effect=aiosmtplib.SMTPAuthenticationError(535, "Auth failed"),
    )
    async def test_returns_false_on_auth_error(self, mock_smtp_send, service):
        """Test that SMTPAuthenticationError returns False (not raise)"""
        result = await service.send_email("lehrer@schule.de", "Betreff", "Nachricht")

        assert result is False

    @pytest.mark.asyncio
    @patch("aiosmtplib.send", side_effect=aiosmtplib.SMTPConnectError("Cannot connect"))
    async def test_returns_false_on_connect_error(self, mock_smtp_send, service):
        """Test that SMTPConnectError returns False (not raise)"""
        result = await service.send_email("lehrer@schule.de", "Betreff", "Nachricht")

        assert result is False

    @pytest.mark.asyncio
    @patch("aiosmtplib.send", side_effect=Exception("Unexpected network error"))
    async def test_returns_false_on_unexpected_exception(self, mock_smtp_send, service):
        """Test that any unexpected exception returns False (not raise)"""
        result = await service.send_email("lehrer@schule.de", "Betreff", "Nachricht")

        assert result is False


# ============================================================================
# Test send_absence_submitted_notification()
# ============================================================================


class TestSendAbsenceSubmittedNotification:
    """Test notification sent when absence is submitted"""

    @pytest.mark.asyncio
    async def test_sends_to_dept_heads_and_planners(self, service):
        """Test that all dept_head and planner emails receive the notification"""
        with patch.object(
            service, "send_email", new_callable=AsyncMock, return_value=True
        ) as mock_send:
            await service.send_absence_submitted_notification(
                teacher_name="Max Mustermann",
                teacher_email="max@schule.de",
                dept_head_emails=["head1@schule.de", "head2@schule.de"],
                planner_emails=["planner@schule.de"],
                absence_id=42,
                reason="Krankheit",
                start_date="10.02.2026",
                end_date="12.02.2026",
            )

        # 2 dept_heads + 1 planner = 3 calls
        assert mock_send.call_count == 3
        recipients = [call[0][0] for call in mock_send.call_args_list]
        assert "head1@schule.de" in recipients
        assert "head2@schule.de" in recipients
        assert "planner@schule.de" in recipients

    @pytest.mark.asyncio
    async def test_returns_true_when_all_succeed(self, service):
        """Test that True is returned when all sends succeed"""
        with patch.object(
            service, "send_email", new_callable=AsyncMock, return_value=True
        ):
            result = await service.send_absence_submitted_notification(
                teacher_name="Max Mustermann",
                teacher_email="max@schule.de",
                dept_head_emails=["head@schule.de"],
                planner_emails=[],
                absence_id=42,
                reason="Krankheit",
                start_date="10.02.2026",
                end_date="10.02.2026",
            )

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_any_send_fails(self, service):
        """Test that False is returned when at least one send fails"""
        with patch.object(
            service,
            "send_email",
            new_callable=AsyncMock,
            side_effect=[True, False],  # second recipient fails
        ):
            result = await service.send_absence_submitted_notification(
                teacher_name="Max Mustermann",
                teacher_email="max@schule.de",
                dept_head_emails=["head@schule.de"],
                planner_emails=["planner@schule.de"],
                absence_id=42,
                reason="Krankheit",
                start_date="10.02.2026",
                end_date="10.02.2026",
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_subject_contains_teacher_name(self, service):
        """Test that the email subject contains the teacher's name"""
        with patch.object(
            service, "send_email", new_callable=AsyncMock, return_value=True
        ) as mock_send:
            await service.send_absence_submitted_notification(
                teacher_name="Max Mustermann",
                teacher_email="max@schule.de",
                dept_head_emails=["head@schule.de"],
                planner_emails=[],
                absence_id=42,
                reason="Krankheit",
                start_date="10.02.2026",
                end_date="10.02.2026",
            )

        subject = mock_send.call_args[0][1]  # positional arg: subject
        assert "Max Mustermann" in subject

    @pytest.mark.asyncio
    async def test_returns_true_with_no_recipients(self, service):
        """Test that True is returned when recipient lists are empty"""
        with patch.object(service, "send_email", new_callable=AsyncMock) as mock_send:
            result = await service.send_absence_submitted_notification(
                teacher_name="Max Mustermann",
                teacher_email="max@schule.de",
                dept_head_emails=[],
                planner_emails=[],
                absence_id=42,
                reason="Krankheit",
                start_date="10.02.2026",
                end_date="10.02.2026",
            )

        mock_send.assert_not_called()
        assert result is True


# ============================================================================
# Test send_absence_approved_notification()
# ============================================================================


class TestSendAbsenceApprovedNotification:
    """Test notification sent when absence is approved"""

    @pytest.mark.asyncio
    async def test_sends_to_teacher_and_all_planners(self, service):
        """Test that teacher and all planners receive notification"""
        with patch.object(
            service, "send_email", new_callable=AsyncMock, return_value=True
        ) as mock_send:
            await service.send_absence_approved_notification(
                teacher_email="max@schule.de",
                planner_emails=["p1@schule.de", "p2@schule.de"],
                absence_id=42,
                approver_name="Dr. Abteilungsleiter",
            )

        # 1 teacher + 2 planners = 3 calls
        assert mock_send.call_count == 3
        recipients = [call[0][0] for call in mock_send.call_args_list]
        assert "max@schule.de" in recipients
        assert "p1@schule.de" in recipients
        assert "p2@schule.de" in recipients

    @pytest.mark.asyncio
    async def test_teacher_body_contains_approver_name(self, service):
        """Test that teacher notification body contains approver name"""
        with patch.object(
            service, "send_email", new_callable=AsyncMock, return_value=True
        ) as mock_send:
            await service.send_absence_approved_notification(
                teacher_email="max@schule.de",
                planner_emails=[],
                absence_id=42,
                approver_name="Dr. Abteilungsleiter",
            )

        # First call is to teacher
        teacher_body = mock_send.call_args_list[0][0][2]
        assert "Dr. Abteilungsleiter" in teacher_body

    @pytest.mark.asyncio
    async def test_returns_true(self, service):
        """Test that approved notification always returns True"""
        with patch.object(
            service, "send_email", new_callable=AsyncMock, return_value=False
        ):
            result = await service.send_absence_approved_notification(
                teacher_email="max@schule.de",
                planner_emails=[],
                absence_id=42,
                approver_name="Chef",
            )

        assert result is True


# ============================================================================
# Test send_absence_completed_notification()
# ============================================================================


class TestSendAbsenceCompletedNotification:
    """Test notification sent when absence is marked as completed"""

    @pytest.mark.asyncio
    async def test_sends_to_teacher_email(self, service):
        """Test that notification is sent to teacher's email"""
        with patch.object(
            service, "send_email", new_callable=AsyncMock, return_value=True
        ) as mock_send:
            await service.send_absence_completed_notification(
                teacher_email="max@schule.de", absence_id=42
            )

        mock_send.assert_called_once()
        assert mock_send.call_args[0][0] == "max@schule.de"

    @pytest.mark.asyncio
    async def test_returns_send_email_result(self, service):
        """Test that return value reflects send_email result"""
        with patch.object(
            service, "send_email", new_callable=AsyncMock, return_value=False
        ):
            result = await service.send_absence_completed_notification(
                teacher_email="max@schule.de", absence_id=42
            )

        assert result is False


# ============================================================================
# Test send_absence_rejected_notification()
# ============================================================================


class TestSendAbsenceRejectedNotification:
    """Test notification sent when absence is rejected"""

    @pytest.mark.asyncio
    async def test_sends_to_teacher_email(self, service):
        """Test that rejection notification is sent to teacher's email"""
        with patch.object(
            service, "send_email", new_callable=AsyncMock, return_value=True
        ) as mock_send:
            await service.send_absence_rejected_notification(
                teacher_email="max@schule.de",
                absence_id=42,
                rejector_name="Chef",
            )

        mock_send.assert_called_once()
        assert mock_send.call_args[0][0] == "max@schule.de"

    @pytest.mark.asyncio
    async def test_body_contains_rejector_name(self, service):
        """Test that rejection body contains rejector's name"""
        with patch.object(
            service, "send_email", new_callable=AsyncMock, return_value=True
        ) as mock_send:
            await service.send_absence_rejected_notification(
                teacher_email="max@schule.de",
                absence_id=42,
                rejector_name="Dr. Ablehnungsleiter",
            )

        body = mock_send.call_args[0][2]
        assert "Dr. Ablehnungsleiter" in body

    @pytest.mark.asyncio
    async def test_returns_send_email_result(self, service):
        """Test that return value reflects send_email result"""
        with patch.object(
            service, "send_email", new_callable=AsyncMock, return_value=False
        ):
            result = await service.send_absence_rejected_notification(
                teacher_email="max@schule.de",
                absence_id=42,
                rejector_name="Chef",
            )

        assert result is False
