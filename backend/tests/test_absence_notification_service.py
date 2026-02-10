"""
Unit Tests für AbsenceNotificationService

Getestet:
- send_submitted_notification() - Eingereicht: an Abteilungsleitung + Planer
- send_approved_notification()  - Genehmigt: an Lehrkraft + Planer
- send_completed_notification() - Erledigt: an Lehrkraft
- send_rejected_notification()  - Abgelehnt: an Lehrkraft

Alle Methoden: Silent error handling (kein Raise nach außen)
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from app.services.absence_notification_service import AbsenceNotificationService


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def service():
    return AbsenceNotificationService()


@pytest.fixture
def mock_absence():
    """Mock absence with teacher that has an email address"""
    teacher = Mock()
    teacher.email = "max.mustermann@schule.de"
    teacher.full_name = "Max Mustermann"
    teacher.username = "max.mustermann"

    absence = Mock()
    absence.id = 42
    absence.reason = "sick"
    absence.start_date = datetime(2026, 2, 10)
    absence.end_date = datetime(2026, 2, 12)
    absence.teacher = teacher
    return absence


@pytest.fixture
def mock_absence_no_teacher_email(mock_absence):
    """Mock absence with teacher that has NO email"""
    mock_absence.teacher.email = None
    return mock_absence


@pytest.fixture
def mock_absence_no_teacher(mock_absence):
    """Mock absence without teacher relationship loaded"""
    mock_absence.teacher = None
    return mock_absence


@pytest.fixture
def mock_submitter():
    """User who submitted the absence"""
    user = Mock()
    user.full_name = "Max Mustermann"
    user.username = "max.mustermann"
    user.email = "max.mustermann@schule.de"
    return user


@pytest.fixture
def mock_approver():
    """User who approved/rejected the absence"""
    user = Mock()
    user.full_name = "Dr. Abteilungsleiter"
    user.username = "dept.head"
    return user


@pytest.fixture
def mock_db():
    return Mock()


# ============================================================================
# Test send_submitted_notification()
# ============================================================================


class TestSendSubmittedNotification:
    """Test notification when absence is submitted"""

    @pytest.mark.asyncio
    @patch("app.services.absence_notification_service.email_service")
    @patch("app.services.absence_notification_service.get_recipients_by_roles")
    async def test_sends_to_dept_heads_and_planners(
        self,
        mock_get_recipients,
        mock_email_svc,
        service,
        mock_absence,
        mock_submitter,
        mock_db,
    ):
        """Test that recipients include dept heads and planners"""
        mock_get_recipients.side_effect = [
            ["head@schule.de"],  # dept_head_emails
            ["planner@schule.de"],  # planner_emails
        ]
        mock_email_svc.send_absence_submitted_notification = AsyncMock(
            return_value=True
        )

        await service.send_submitted_notification(mock_absence, mock_submitter, mock_db)

        mock_email_svc.send_absence_submitted_notification.assert_called_once()
        call_kwargs = mock_email_svc.send_absence_submitted_notification.call_args[1]
        assert call_kwargs["dept_head_emails"] == ["head@schule.de"]
        assert call_kwargs["planner_emails"] == ["planner@schule.de"]
        assert call_kwargs["absence_id"] == 42

    @pytest.mark.asyncio
    @patch("app.services.absence_notification_service.email_service")
    @patch("app.services.absence_notification_service.get_recipients_by_roles")
    async def test_uses_full_name_when_available(
        self,
        mock_get_recipients,
        mock_email_svc,
        service,
        mock_absence,
        mock_submitter,
        mock_db,
    ):
        """Test that teacher's full_name is used in notification"""
        mock_get_recipients.side_effect = [[], []]
        mock_email_svc.send_absence_submitted_notification = AsyncMock(
            return_value=True
        )

        await service.send_submitted_notification(mock_absence, mock_submitter, mock_db)

        call_kwargs = mock_email_svc.send_absence_submitted_notification.call_args[1]
        assert call_kwargs["teacher_name"] == "Max Mustermann"

    @pytest.mark.asyncio
    @patch("app.services.absence_notification_service.email_service")
    @patch("app.services.absence_notification_service.get_recipients_by_roles")
    async def test_uses_username_as_fallback(
        self,
        mock_get_recipients,
        mock_email_svc,
        service,
        mock_absence,
        mock_db,
    ):
        """Test that username is used when full_name is None"""
        submitter = Mock()
        submitter.full_name = None
        submitter.username = "max.mustermann"
        submitter.email = "max@schule.de"

        mock_get_recipients.side_effect = [[], []]
        mock_email_svc.send_absence_submitted_notification = AsyncMock(
            return_value=True
        )

        await service.send_submitted_notification(mock_absence, submitter, mock_db)

        call_kwargs = mock_email_svc.send_absence_submitted_notification.call_args[1]
        assert call_kwargs["teacher_name"] == "max.mustermann"

    @pytest.mark.asyncio
    @patch("app.services.absence_notification_service.email_service")
    @patch("app.services.absence_notification_service.get_recipients_by_roles")
    async def test_does_not_raise_on_send_failure(
        self,
        mock_get_recipients,
        mock_email_svc,
        service,
        mock_absence,
        mock_submitter,
        mock_db,
    ):
        """Test that email send failure is silently logged, not raised"""
        mock_get_recipients.side_effect = [[], []]
        mock_email_svc.send_absence_submitted_notification = AsyncMock(
            return_value=False  # failure
        )

        # Should NOT raise
        await service.send_submitted_notification(mock_absence, mock_submitter, mock_db)

    @pytest.mark.asyncio
    @patch("app.services.absence_notification_service.email_service")
    @patch("app.services.absence_notification_service.get_recipients_by_roles")
    async def test_does_not_raise_on_exception(
        self,
        mock_get_recipients,
        mock_email_svc,
        service,
        mock_absence,
        mock_submitter,
        mock_db,
    ):
        """Test that exceptions in email sending are caught silently"""
        mock_get_recipients.side_effect = Exception("DB connection lost")

        # Should NOT raise, just log the error
        await service.send_submitted_notification(mock_absence, mock_submitter, mock_db)


# ============================================================================
# Test send_approved_notification()
# ============================================================================


class TestSendApprovedNotification:
    """Test notification when absence is approved"""

    @pytest.mark.asyncio
    @patch("app.services.absence_notification_service.email_service")
    @patch("app.services.absence_notification_service.get_recipients_by_roles")
    async def test_sends_to_teacher_and_planners(
        self,
        mock_get_recipients,
        mock_email_svc,
        service,
        mock_absence,
        mock_approver,
        mock_db,
    ):
        """Test that approved notification is sent to teacher and planners"""
        mock_get_recipients.return_value = ["planner@schule.de"]
        mock_email_svc.send_absence_approved_notification = AsyncMock(return_value=True)

        await service.send_approved_notification(mock_absence, mock_approver, mock_db)

        mock_email_svc.send_absence_approved_notification.assert_called_once()
        call_kwargs = mock_email_svc.send_absence_approved_notification.call_args[1]
        assert call_kwargs["teacher_email"] == "max.mustermann@schule.de"
        assert call_kwargs["planner_emails"] == ["planner@schule.de"]
        assert call_kwargs["absence_id"] == 42

    @pytest.mark.asyncio
    @patch("app.services.absence_notification_service.email_service")
    @patch("app.services.absence_notification_service.get_recipients_by_roles")
    async def test_uses_approver_full_name(
        self,
        mock_get_recipients,
        mock_email_svc,
        service,
        mock_absence,
        mock_approver,
        mock_db,
    ):
        """Test that approver full_name is passed in notification"""
        mock_get_recipients.return_value = []
        mock_email_svc.send_absence_approved_notification = AsyncMock(return_value=True)

        await service.send_approved_notification(mock_absence, mock_approver, mock_db)

        call_kwargs = mock_email_svc.send_absence_approved_notification.call_args[1]
        assert call_kwargs["approver_name"] == "Dr. Abteilungsleiter"

    @pytest.mark.asyncio
    @patch("app.services.absence_notification_service.email_service")
    async def test_skips_when_no_teacher_email(
        self,
        mock_email_svc,
        service,
        mock_absence_no_teacher_email,
        mock_approver,
        mock_db,
    ):
        """Test that notification is skipped when teacher has no email"""
        mock_email_svc.send_absence_approved_notification = AsyncMock(return_value=True)

        await service.send_approved_notification(
            mock_absence_no_teacher_email, mock_approver, mock_db
        )

        mock_email_svc.send_absence_approved_notification.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.services.absence_notification_service.email_service")
    async def test_skips_when_no_teacher(
        self,
        mock_email_svc,
        service,
        mock_absence_no_teacher,
        mock_approver,
        mock_db,
    ):
        """Test that notification is skipped when teacher relationship is None"""
        mock_email_svc.send_absence_approved_notification = AsyncMock(return_value=True)

        await service.send_approved_notification(
            mock_absence_no_teacher, mock_approver, mock_db
        )

        mock_email_svc.send_absence_approved_notification.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.services.absence_notification_service.email_service")
    @patch("app.services.absence_notification_service.get_recipients_by_roles")
    async def test_does_not_raise_on_exception(
        self,
        mock_get_recipients,
        mock_email_svc,
        service,
        mock_absence,
        mock_approver,
        mock_db,
    ):
        """Test that exceptions are caught silently"""
        mock_get_recipients.side_effect = Exception("SMTP timeout")

        # Should NOT raise
        await service.send_approved_notification(mock_absence, mock_approver, mock_db)


# ============================================================================
# Test send_completed_notification()
# ============================================================================


class TestSendCompletedNotification:
    """Test notification when absence is marked as completed"""

    @pytest.mark.asyncio
    @patch("app.services.absence_notification_service.email_service")
    async def test_sends_to_teacher(
        self, mock_email_svc, service, mock_absence, mock_db
    ):
        """Test that completed notification is sent to teacher"""
        mock_email_svc.send_absence_completed_notification = AsyncMock(
            return_value=True
        )

        await service.send_completed_notification(mock_absence, mock_db)

        mock_email_svc.send_absence_completed_notification.assert_called_once_with(
            teacher_email="max.mustermann@schule.de", absence_id=42
        )

    @pytest.mark.asyncio
    @patch("app.services.absence_notification_service.email_service")
    async def test_skips_when_no_teacher_email(
        self, mock_email_svc, service, mock_absence_no_teacher_email, mock_db
    ):
        """Test that notification is skipped when teacher has no email"""
        mock_email_svc.send_absence_completed_notification = AsyncMock(
            return_value=True
        )

        await service.send_completed_notification(
            mock_absence_no_teacher_email, mock_db
        )

        mock_email_svc.send_absence_completed_notification.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.services.absence_notification_service.email_service")
    async def test_skips_when_no_teacher(
        self, mock_email_svc, service, mock_absence_no_teacher, mock_db
    ):
        """Test that notification is skipped when teacher is None"""
        mock_email_svc.send_absence_completed_notification = AsyncMock(
            return_value=True
        )

        await service.send_completed_notification(mock_absence_no_teacher, mock_db)

        mock_email_svc.send_absence_completed_notification.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.services.absence_notification_service.email_service")
    async def test_does_not_raise_on_exception(
        self, mock_email_svc, service, mock_absence, mock_db
    ):
        """Test that exceptions are caught silently"""
        mock_email_svc.send_absence_completed_notification = AsyncMock(
            side_effect=Exception("Connection refused")
        )

        # Should NOT raise
        await service.send_completed_notification(mock_absence, mock_db)


# ============================================================================
# Test send_rejected_notification()
# ============================================================================


class TestSendRejectedNotification:
    """Test notification when absence is rejected"""

    @pytest.mark.asyncio
    @patch("app.services.absence_notification_service.email_service")
    async def test_sends_to_teacher(
        self, mock_email_svc, service, mock_absence, mock_approver, mock_db
    ):
        """Test that rejected notification is sent to teacher"""
        mock_email_svc.send_absence_rejected_notification = AsyncMock(return_value=True)

        await service.send_rejected_notification(mock_absence, mock_approver, mock_db)

        mock_email_svc.send_absence_rejected_notification.assert_called_once()
        call_kwargs = mock_email_svc.send_absence_rejected_notification.call_args[1]
        assert call_kwargs["teacher_email"] == "max.mustermann@schule.de"
        assert call_kwargs["absence_id"] == 42

    @pytest.mark.asyncio
    @patch("app.services.absence_notification_service.email_service")
    async def test_uses_rejector_full_name(
        self, mock_email_svc, service, mock_absence, mock_approver, mock_db
    ):
        """Test that rejector full_name is passed in notification"""
        mock_email_svc.send_absence_rejected_notification = AsyncMock(return_value=True)

        await service.send_rejected_notification(mock_absence, mock_approver, mock_db)

        call_kwargs = mock_email_svc.send_absence_rejected_notification.call_args[1]
        assert call_kwargs["rejector_name"] == "Dr. Abteilungsleiter"

    @pytest.mark.asyncio
    @patch("app.services.absence_notification_service.email_service")
    async def test_skips_when_no_teacher_email(
        self,
        mock_email_svc,
        service,
        mock_absence_no_teacher_email,
        mock_approver,
        mock_db,
    ):
        """Test that notification is skipped when teacher has no email"""
        mock_email_svc.send_absence_rejected_notification = AsyncMock(return_value=True)

        await service.send_rejected_notification(
            mock_absence_no_teacher_email, mock_approver, mock_db
        )

        mock_email_svc.send_absence_rejected_notification.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.services.absence_notification_service.email_service")
    async def test_does_not_raise_on_send_failure(
        self, mock_email_svc, service, mock_absence, mock_approver, mock_db
    ):
        """Test that send failure (return_value=False) is logged, not raised"""
        mock_email_svc.send_absence_rejected_notification = AsyncMock(
            return_value=False
        )

        # Should NOT raise
        await service.send_rejected_notification(mock_absence, mock_approver, mock_db)
