"""
Unit Tests für AbsenceService

Getestet:
- create_absence()   - Erstellung mit DB, WebUntis, Benachrichtigung
- approve_absence()  - Genehmigung / Ablehnung mit Audit-Log
- complete_absence() - Erledigt mit Datei-Löschung
- delete_absence()   - Löschung mit Cascade
- cleanup_old_absences() - Scheduled Cleanup
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from fastapi import HTTPException

from app.models.models import Absence, AbsenceStatus, UserRole
from app.services.absence_service import AbsenceService


# ============================================================================
# Helpers & Fixtures
# ============================================================================


def make_mock_db(absence=None, all_absences=None):
    """Create mock DB session returning given absence on queries"""
    db = Mock()
    mock_query = Mock()
    mock_query.options.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.first.return_value = absence
    mock_query.all.return_value = all_absences if all_absences is not None else []
    db.query.return_value = mock_query
    return db


@pytest.fixture
def service():
    return AbsenceService()


@pytest.fixture
def mock_teacher():
    user = Mock()
    user.id = 1
    user.username = "max.mustermann"
    user.webuntis_teacher_code = "MUS"
    user.role = UserRole.TEACHER
    return user


@pytest.fixture
def mock_approver():
    user = Mock()
    user.id = 2
    user.username = "dept.head"
    user.role = UserRole.DEPARTMENT_HEAD
    return user


@pytest.fixture
def mock_planner():
    user = Mock()
    user.id = 3
    user.username = "planner"
    user.role = UserRole.PLANNER
    return user


@pytest.fixture
def mock_absence():
    """Mock absence in SUBMITTED status without attachments"""
    absence = Mock()
    absence.id = 42
    absence.teacher_id = 1
    absence.status = AbsenceStatus.SUBMITTED
    absence.attachments = []
    absence.affected_lessons = []
    return absence


@pytest.fixture
def mock_absence_with_attachments():
    """Mock absence in APPROVED status with 2 attachments"""
    att1 = Mock()
    att1.file_path = "/app/uploads/absence_42/file1.pdf"
    att2 = Mock()
    att2.file_path = "/app/uploads/absence_42/file2.jpg"

    absence = Mock()
    absence.id = 42
    absence.teacher_id = 1
    absence.status = AbsenceStatus.APPROVED
    absence.attachments = [att1, att2]
    absence.affected_lessons = []
    return absence


@pytest.fixture
def mock_request():
    """Mock FastAPI Request for audit logging"""
    request = Mock()
    request.headers = {}
    request.client = Mock()
    request.client.host = "127.0.0.1"
    return request


@pytest.fixture
def absence_data():
    """Mock AbsenceCreate data (healthy defaults)"""
    data = Mock()
    data.start_date = datetime(2026, 2, 10)
    data.end_date = datetime(2026, 2, 10)
    data.start_period = 1
    data.end_period = 4
    data.reason = "sick"
    data.excursion_classes = None
    data.personal_reason = None
    data.admin_notes = None
    data.affected_lessons = []
    return data


# ============================================================================
# Test create_absence()
# ============================================================================


class TestCreateAbsence:
    """Test absence creation: DB persistence, WebUntis, notifications"""

    @pytest.mark.asyncio
    @patch("app.services.absence_service.webuntis_service")
    @patch("app.services.absence_service.absence_notification_service")
    @patch("app.services.absence_service.validate_date_range")
    async def test_create_absence_success(
        self,
        mock_validate,
        mock_notification,
        mock_webuntis,
        service,
        absence_data,
        mock_teacher,
    ):
        """Test successful absence creation saves to DB and returns absence"""
        mock_webuntis.get_timetable_for_teacher = AsyncMock(return_value=[])
        mock_notification.send_submitted_notification = AsyncMock()
        mock_absence = Mock()
        mock_absence.id = 42
        db = make_mock_db(absence=mock_absence)

        result = await service.create_absence(absence_data, mock_teacher, db)

        db.add.assert_called()
        db.commit.assert_called()
        assert result == mock_absence

    @pytest.mark.asyncio
    @patch("app.services.absence_service.webuntis_service")
    @patch("app.services.absence_service.absence_notification_service")
    @patch("app.services.absence_service.validate_date_range")
    async def test_create_absence_calls_validate_date_range(
        self,
        mock_validate,
        mock_notification,
        mock_webuntis,
        service,
        absence_data,
        mock_teacher,
    ):
        """Test that validate_date_range is called with correct arguments"""
        mock_webuntis.get_timetable_for_teacher = AsyncMock(return_value=[])
        mock_notification.send_submitted_notification = AsyncMock()
        db = make_mock_db(absence=Mock())

        await service.create_absence(absence_data, mock_teacher, db)

        mock_validate.assert_called_once_with(
            absence_data.start_date,
            absence_data.end_date,
            absence_data.start_period,
            absence_data.end_period,
        )

    @pytest.mark.asyncio
    @patch("app.services.absence_service.validate_date_range")
    async def test_create_absence_validation_error_propagates(
        self, mock_validate, service, absence_data, mock_teacher
    ):
        """Test that HTTPException from validate_date_range propagates"""
        mock_validate.side_effect = HTTPException(
            status_code=400, detail="Invalid date range"
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.create_absence(absence_data, mock_teacher, Mock())

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    @patch("app.services.absence_service.webuntis_service")
    @patch("app.services.absence_service.absence_notification_service")
    @patch("app.services.absence_service.validate_date_range")
    async def test_create_absence_sends_submitted_notification(
        self,
        mock_validate,
        mock_notification,
        mock_webuntis,
        service,
        absence_data,
        mock_teacher,
    ):
        """Test that submitted notification email is sent after creation"""
        mock_webuntis.get_timetable_for_teacher = AsyncMock(return_value=[])
        mock_notification.send_submitted_notification = AsyncMock()
        db = make_mock_db(absence=Mock())

        await service.create_absence(absence_data, mock_teacher, db)

        mock_notification.send_submitted_notification.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.absence_service.webuntis_service")
    @patch("app.services.absence_service.absence_notification_service")
    @patch("app.services.absence_service.validate_date_range")
    @patch("app.services.absence_service.is_lesson_in_period")
    async def test_create_absence_stores_matching_lessons(
        self,
        mock_is_in_period,
        mock_validate,
        mock_notification,
        mock_webuntis,
        service,
        absence_data,
        mock_teacher,
    ):
        """Test that lessons matching the period are stored as AffectedLesson"""
        mock_lesson = Mock()
        mock_lesson.date = Mock()
        mock_lesson.date.date.return_value = Mock()
        mock_lesson.period = 2
        mock_lesson.end_period = 2
        mock_lesson.start_time = 900
        mock_lesson.end_time = 945
        mock_lesson.subject = "Mathematik"
        mock_lesson.class_name = "5A"
        mock_lesson.room = "101"
        mock_webuntis.get_timetable_for_teacher = AsyncMock(return_value=[mock_lesson])
        mock_notification.send_submitted_notification = AsyncMock()
        mock_is_in_period.return_value = True
        mock_absence = Mock()
        mock_absence.id = 42
        db = make_mock_db(absence=mock_absence)

        await service.create_absence(absence_data, mock_teacher, db)

        # db.add called at least twice: once for Absence, once for AffectedLesson
        assert db.add.call_count >= 2

    @pytest.mark.asyncio
    @patch("app.services.absence_service.webuntis_service")
    @patch("app.services.absence_service.absence_notification_service")
    @patch("app.services.absence_service.validate_date_range")
    @patch("app.services.absence_service.is_lesson_in_period")
    async def test_create_absence_skips_non_matching_lessons(
        self,
        mock_is_in_period,
        mock_validate,
        mock_notification,
        mock_webuntis,
        service,
        absence_data,
        mock_teacher,
    ):
        """Test that lessons outside the period are NOT stored"""
        mock_lesson = Mock()
        mock_webuntis.get_timetable_for_teacher = AsyncMock(return_value=[mock_lesson])
        mock_notification.send_submitted_notification = AsyncMock()
        mock_is_in_period.return_value = False  # Lesson outside period

        mock_absence = Mock()
        mock_absence.id = 42
        db = make_mock_db(absence=mock_absence)

        await service.create_absence(absence_data, mock_teacher, db)

        # db.add called exactly once: only for Absence, NOT for AffectedLesson
        assert db.add.call_count == 1


# ============================================================================
# Test approve_absence()
# ============================================================================


class TestApproveAbsence:
    """Test absence approval and rejection workflow with audit logging"""

    @pytest.mark.asyncio
    @patch("app.services.absence_service.audit_absence_approved")
    @patch("app.services.absence_service.absence_notification_service")
    async def test_approve_absence_sets_status_approved(
        self,
        mock_notification,
        mock_audit,
        service,
        mock_absence,
        mock_approver,
        mock_request,
    ):
        """Test that approved=True changes status to APPROVED"""
        mock_notification.send_approved_notification = AsyncMock()
        db = make_mock_db(absence=mock_absence)

        result = await service.approve_absence(
            42, True, mock_approver, db, mock_request
        )

        assert mock_absence.status == AbsenceStatus.APPROVED
        assert mock_absence.approved_by == mock_approver.id
        assert mock_absence.approved_at is not None
        assert result == "Absence approved"

    @pytest.mark.asyncio
    @patch("app.services.absence_service.audit_log")
    @patch("app.services.absence_service.absence_notification_service")
    async def test_reject_absence_sets_status_rejected(
        self,
        mock_notification,
        mock_audit,
        service,
        mock_absence,
        mock_approver,
        mock_request,
    ):
        """Test that approved=False changes status to REJECTED"""
        mock_notification.send_rejected_notification = AsyncMock()
        db = make_mock_db(absence=mock_absence)

        result = await service.approve_absence(
            42, False, mock_approver, db, mock_request
        )

        assert mock_absence.status == AbsenceStatus.REJECTED
        assert result == "Absence rejected"

    @pytest.mark.asyncio
    async def test_approve_absence_not_found_raises_404(
        self, service, mock_approver, mock_request
    ):
        """Test that approving non-existent absence raises 404"""
        db = make_mock_db(absence=None)

        with pytest.raises(HTTPException) as exc_info:
            await service.approve_absence(999, True, mock_approver, db, mock_request)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @patch("app.services.absence_service.audit_absence_approved")
    @patch("app.services.absence_service.absence_notification_service")
    async def test_approve_absence_sends_approved_notification(
        self,
        mock_notification,
        mock_audit,
        service,
        mock_absence,
        mock_approver,
        mock_request,
    ):
        """Test that approval sends email notification"""
        mock_notification.send_approved_notification = AsyncMock()
        db = make_mock_db(absence=mock_absence)

        await service.approve_absence(42, True, mock_approver, db, mock_request)

        mock_notification.send_approved_notification.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.absence_service.audit_log")
    @patch("app.services.absence_service.absence_notification_service")
    async def test_reject_absence_sends_rejected_notification(
        self,
        mock_notification,
        mock_audit,
        service,
        mock_absence,
        mock_approver,
        mock_request,
    ):
        """Test that rejection sends email notification"""
        mock_notification.send_rejected_notification = AsyncMock()
        db = make_mock_db(absence=mock_absence)

        await service.approve_absence(42, False, mock_approver, db, mock_request)

        mock_notification.send_rejected_notification.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.absence_service.audit_absence_approved")
    @patch("app.services.absence_service.absence_notification_service")
    async def test_approve_absence_commits_to_db(
        self,
        mock_notification,
        mock_audit,
        service,
        mock_absence,
        mock_approver,
        mock_request,
    ):
        """Test that approval is persisted to DB"""
        mock_notification.send_approved_notification = AsyncMock()
        db = make_mock_db(absence=mock_absence)

        await service.approve_absence(42, True, mock_approver, db, mock_request)

        db.commit.assert_called()


# ============================================================================
# Test complete_absence()
# ============================================================================


class TestCompleteAbsence:
    """Test marking absence as completed with automatic attachment cleanup"""

    @pytest.mark.asyncio
    @patch("app.services.absence_service.audit_absence_completed")
    @patch("app.services.absence_service.absence_notification_service")
    async def test_complete_absence_sets_status_completed(
        self,
        mock_notification,
        mock_audit,
        service,
        mock_absence,
        mock_planner,
        mock_request,
    ):
        """Test that complete_absence changes status to COMPLETED"""
        mock_notification.send_completed_notification = AsyncMock()
        db = make_mock_db(absence=mock_absence)

        result = await service.complete_absence(42, mock_planner, db, mock_request)

        assert mock_absence.status == AbsenceStatus.COMPLETED
        assert mock_absence.completed_at is not None
        assert "completed" in result

    @pytest.mark.asyncio
    async def test_complete_absence_not_found_raises_404(
        self, service, mock_planner, mock_request
    ):
        """Test that completing non-existent absence raises 404"""
        db = make_mock_db(absence=None)

        with pytest.raises(HTTPException) as exc_info:
            await service.complete_absence(999, mock_planner, db, mock_request)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @patch("app.services.absence_service.audit_absence_completed")
    @patch("app.services.absence_service.absence_notification_service")
    @patch("app.services.absence_service.attachment_service")
    async def test_complete_absence_deletes_all_attachments(
        self,
        mock_attachment_svc,
        mock_notification,
        mock_audit,
        service,
        mock_absence_with_attachments,
        mock_planner,
        mock_request,
    ):
        """Test that completing absence deletes all attachment files"""
        mock_notification.send_completed_notification = AsyncMock()
        db = make_mock_db(absence=mock_absence_with_attachments)

        await service.complete_absence(42, mock_planner, db, mock_request)

        assert mock_attachment_svc.delete_file.call_count == 2

    @pytest.mark.asyncio
    @patch("app.services.absence_service.audit_absence_completed")
    @patch("app.services.absence_service.absence_notification_service")
    @patch("app.services.absence_service.attachment_service")
    async def test_complete_absence_no_attachments_ok(
        self,
        mock_attachment_svc,
        mock_notification,
        mock_audit,
        service,
        mock_absence,
        mock_planner,
        mock_request,
    ):
        """Test that complete_absence works fine without attachments"""
        mock_notification.send_completed_notification = AsyncMock()
        db = make_mock_db(absence=mock_absence)

        result = await service.complete_absence(42, mock_planner, db, mock_request)

        mock_attachment_svc.delete_file.assert_not_called()
        assert "completed" in result

    @pytest.mark.asyncio
    @patch("app.services.absence_service.audit_absence_completed")
    @patch("app.services.absence_service.absence_notification_service")
    async def test_complete_absence_sends_notification(
        self,
        mock_notification,
        mock_audit,
        service,
        mock_absence,
        mock_planner,
        mock_request,
    ):
        """Test that completion sends email notification to teacher"""
        mock_notification.send_completed_notification = AsyncMock()
        db = make_mock_db(absence=mock_absence)

        await service.complete_absence(42, mock_planner, db, mock_request)

        mock_notification.send_completed_notification.assert_called_once()


# ============================================================================
# Test delete_absence()
# ============================================================================


class TestDeleteAbsence:
    """Test absence deletion with file cleanup and cascade"""

    @pytest.mark.asyncio
    @patch("app.services.absence_service.attachment_service")
    async def test_delete_absence_success(
        self, mock_attachment_svc, service, mock_absence
    ):
        """Test successful absence deletion removes DB record"""
        db = make_mock_db(absence=mock_absence)

        result = await service.delete_absence(42, Mock(), db)

        db.delete.assert_called_once_with(mock_absence)
        db.commit.assert_called()
        assert result == "Absence deleted"

    @pytest.mark.asyncio
    async def test_delete_absence_not_found_raises_404(self, service):
        """Test that deleting non-existent absence raises 404"""
        db = make_mock_db(absence=None)

        with pytest.raises(HTTPException) as exc_info:
            await service.delete_absence(999, Mock(), db)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @patch("app.services.absence_service.attachment_service")
    async def test_delete_absence_removes_attachment_files(
        self, mock_attachment_svc, service, mock_absence_with_attachments
    ):
        """Test that attachment files are deleted before DB record"""
        db = make_mock_db(absence=mock_absence_with_attachments)

        await service.delete_absence(42, Mock(), db)

        assert mock_attachment_svc.delete_file.call_count == 2

    @pytest.mark.asyncio
    @patch("app.services.absence_service.attachment_service")
    async def test_delete_absence_continues_on_file_error(
        self, mock_attachment_svc, service, mock_absence_with_attachments
    ):
        """Test that deletion continues even if a file cannot be deleted"""
        mock_attachment_svc.delete_file.side_effect = Exception("File locked")
        db = make_mock_db(absence=mock_absence_with_attachments)

        # Should NOT raise, just log warning
        result = await service.delete_absence(42, Mock(), db)

        assert result == "Absence deleted"
        db.delete.assert_called_once_with(mock_absence_with_attachments)


# ============================================================================
# Test cleanup_old_absences()
# ============================================================================


class TestCleanupOldAbsences:
    """Test scheduled cleanup of absences past retention period"""

    def test_cleanup_disabled_when_retention_zero(self, service):
        """Test that cleanup is skipped when retention_days=0"""
        db = Mock()

        result = service.cleanup_old_absences(db, retention_days=0)

        assert result["deleted_count"] == 0
        assert result["errors"] == 0
        db.query.assert_not_called()

    def test_cleanup_disabled_when_retention_negative(self, service):
        """Test that cleanup is skipped when retention_days is negative"""
        db = Mock()

        result = service.cleanup_old_absences(db, retention_days=-5)

        assert result["deleted_count"] == 0
        db.query.assert_not_called()

    @patch("app.services.absence_service.attachment_service")
    def test_cleanup_deletes_old_absences(self, mock_attachment_svc, service):
        """Test that absences older than retention_days are deleted"""
        old1 = Mock()
        old1.id = 10
        old1.end_date = datetime(2025, 1, 1)
        old1.teacher = Mock()
        old1.teacher.username = "teacher1"
        old1.attachments = []

        old2 = Mock()
        old2.id = 11
        old2.end_date = datetime(2025, 1, 2)
        old2.teacher = Mock()
        old2.teacher.username = "teacher2"
        old2.attachments = []

        db = Mock()
        mock_query = Mock()
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [old1, old2]
        # delete_absence() calls .first() once per absence
        mock_query.first.side_effect = [old1, old2]
        db.query.return_value = mock_query

        result = service.cleanup_old_absences(db, retention_days=90)

        assert result["deleted_count"] == 2
        assert result["errors"] == 0

    def test_cleanup_counts_errors_and_continues(self, service):
        """Test that cleanup tracks errors per absence and keeps going"""
        old_absence = Mock()
        old_absence.id = 10
        old_absence.end_date = datetime(2025, 1, 1)
        old_absence.teacher = Mock()
        old_absence.teacher.username = "teacher1"

        db = Mock()
        mock_query = Mock()
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [old_absence]
        # .first() in delete_absence returns None → raises 404 → caught as error
        mock_query.first.return_value = None
        db.query.return_value = mock_query

        result = service.cleanup_old_absences(db, retention_days=90)

        assert result["errors"] == 1
        assert result["deleted_count"] == 0

    def test_cleanup_result_includes_cutoff_date(self, service):
        """Test that cleanup result includes cutoff_date as ISO string"""
        db = make_mock_db(all_absences=[])

        result = service.cleanup_old_absences(db, retention_days=90)

        assert "cutoff_date" in result
        assert isinstance(result["cutoff_date"], str)
