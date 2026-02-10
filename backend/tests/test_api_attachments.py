"""
Unit Tests für app/api/attachments.py

Getestet (Route-Logik, nicht Service-Logik):
- upload_attachment()   - 404/403-Checks, validate+save, DB-Persist, Audit-Log
- download_attachment() - 404/403-Checks, get_file_path, FileResponse
- delete_attachment()   - 404/403-Checks, delete_file, DB-Delete, Audit-Log

Strategie: Direkte Funktionsaufrufe via __wrapped__ (slowapi-Bypass),
Services und Audit-Funktionen via @patch isoliert.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from fastapi import HTTPException
from fastapi.responses import FileResponse

from app.api.attachments import (
    upload_attachment,
    download_attachment,
    delete_attachment,
)
from app.models.models import Absence, AbsenceAttachment, AbsenceStatus, UserRole


# ============================================================================
# Helpers & Fixtures
# ============================================================================


def make_mock_user(role=UserRole.TEACHER, user_id=1):
    user = Mock()
    user.id = user_id
    user.role = role
    user.is_active = True
    return user


def make_mock_absence(absence_id=1, teacher_id=1, status=AbsenceStatus.SUBMITTED):
    absence = Mock(spec=Absence)
    absence.id = absence_id
    absence.teacher_id = teacher_id
    absence.status = status
    return absence


def make_mock_attachment(attachment_id=1, absence_id=1):
    attachment = Mock(spec=AbsenceAttachment)
    attachment.id = attachment_id
    attachment.absence_id = absence_id
    attachment.filename = "nachweis.pdf"
    attachment.stored_filename = "uuid-nachweis.pdf"
    attachment.file_path = f"/app/uploads/absence_{absence_id}/uuid-nachweis.pdf"
    attachment.mime_type = "application/pdf"
    attachment.file_size = 12345
    attachment.absence = make_mock_absence(absence_id=absence_id)
    return attachment


def make_mock_upload_file(filename="nachweis.pdf", content_type="application/pdf"):
    """Mock für FastAPI UploadFile"""
    upload_file = Mock()
    upload_file.filename = filename
    upload_file.content_type = content_type
    return upload_file


def make_mock_saved_file(absence_id=1):
    """Mock für das Ergebnis von attachment_service.save_file"""
    saved = Mock()
    saved.stored_filename = "uuid-nachweis.pdf"
    saved.file_path = f"/app/uploads/absence_{absence_id}/uuid-nachweis.pdf"
    saved.file_size = 12345
    return saved


def make_mock_db(result=None):
    """DB mock für query().filter().first() chains"""
    db = Mock()
    q = Mock()
    q.filter.return_value = q
    q.first.return_value = result
    db.query.return_value = q
    return db


def make_mock_request():
    request = Mock()
    return request


def unwrap(func):
    """Bypass slowapi @limiter.limit() decorator (nutzt functools.wraps)"""
    return func.__wrapped__


@pytest.fixture
def teacher():
    return make_mock_user(role=UserRole.TEACHER, user_id=1)


@pytest.fixture
def planner():
    return make_mock_user(role=UserRole.PLANNER, user_id=2)


# ============================================================================
# Tests: upload_attachment()
# ============================================================================


class TestUploadAttachment:
    """upload_attachment: 404/403-Checks, validate+save+persist, Audit-Log"""

    @pytest.mark.asyncio
    async def test_raises_404_when_absence_not_found(self, teacher):
        """404 wenn Absenz nicht in DB"""
        db = make_mock_db(result=None)
        request = make_mock_request()

        with pytest.raises(HTTPException) as exc_info:
            await unwrap(upload_attachment)(
                request=request,
                absence_id=999,
                file=make_mock_upload_file(),
                current_user=teacher,
                db=db,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_403_when_no_permission(self, teacher):
        """403 wenn can_edit_absence=False"""
        mock_absence = make_mock_absence()
        db = make_mock_db(result=mock_absence)
        request = make_mock_request()

        with patch(
            "app.api.attachments.permission_service.can_edit_absence",
            return_value=False,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await unwrap(upload_attachment)(
                    request=request,
                    absence_id=1,
                    file=make_mock_upload_file(),
                    current_user=teacher,
                    db=db,
                )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_validates_and_saves_file_then_persists_to_db(self, teacher):
        """validate_file + save_file aufgerufen, Attachment in DB gespeichert"""
        mock_absence = make_mock_absence()
        mock_file = make_mock_upload_file()
        mock_saved = make_mock_saved_file(absence_id=1)
        db = make_mock_db(result=mock_absence)
        request = make_mock_request()

        with patch(
            "app.api.attachments.permission_service.can_edit_absence",
            return_value=True,
        ):
            with patch(
                "app.api.attachments.attachment_service.validate_file",
                new_callable=AsyncMock,
                return_value=(mock_saved.file_size, b"file content"),
            ) as mock_validate:
                with patch(
                    "app.api.attachments.attachment_service.save_file",
                    new_callable=AsyncMock,
                    return_value=mock_saved,
                ) as mock_save:
                    with patch("app.api.attachments.audit_file_uploaded"):
                        await unwrap(upload_attachment)(
                            request=request,
                            absence_id=1,
                            file=mock_file,
                            current_user=teacher,
                            db=db,
                        )

        mock_validate.assert_called_once_with(mock_file)
        mock_save.assert_called_once_with(mock_file, b"file content", 1)
        db.add.assert_called_once()
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_audit_log_called_after_successful_upload(self, teacher):
        """audit_file_uploaded wird nach erfolgreichem Upload aufgerufen"""
        mock_absence = make_mock_absence()
        mock_file = make_mock_upload_file()
        mock_saved = make_mock_saved_file(absence_id=1)
        db = make_mock_db(result=mock_absence)
        request = make_mock_request()

        with patch(
            "app.api.attachments.permission_service.can_edit_absence",
            return_value=True,
        ):
            with patch(
                "app.api.attachments.attachment_service.validate_file",
                new_callable=AsyncMock,
                return_value=(mock_saved.file_size, b"file content"),
            ):
                with patch(
                    "app.api.attachments.attachment_service.save_file",
                    new_callable=AsyncMock,
                    return_value=mock_saved,
                ):
                    with patch("app.api.attachments.audit_file_uploaded") as mock_audit:
                        await unwrap(upload_attachment)(
                            request=request,
                            absence_id=1,
                            file=mock_file,
                            current_user=teacher,
                            db=db,
                        )

        mock_audit.assert_called_once()


# ============================================================================
# Tests: download_attachment()
# ============================================================================


class TestDownloadAttachment:
    """download_attachment: 404/403-Checks, get_file_path, FileResponse"""

    @pytest.mark.asyncio
    async def test_raises_404_when_attachment_not_found(self, teacher):
        """404 wenn Attachment nicht in DB"""
        db = make_mock_db(result=None)
        request = make_mock_request()

        with pytest.raises(HTTPException) as exc_info:
            await unwrap(download_attachment)(
                request=request,
                absence_id=1,
                attachment_id=999,
                current_user=teacher,
                db=db,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_403_when_no_permission(self, teacher):
        """403 wenn can_view_absence=False"""
        mock_attachment = make_mock_attachment()
        db = make_mock_db(result=mock_attachment)
        request = make_mock_request()

        with patch(
            "app.api.attachments.permission_service.can_view_absence",
            return_value=False,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await unwrap(download_attachment)(
                    request=request,
                    absence_id=1,
                    attachment_id=1,
                    current_user=teacher,
                    db=db,
                )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_returns_file_response_when_authorized(self, teacher):
        """FileResponse mit korrektem Pfad/MIME/Filename zurückgegeben"""
        mock_attachment = make_mock_attachment()
        db = make_mock_db(result=mock_attachment)
        request = make_mock_request()
        resolved_path = "/app/uploads/absence_1/uuid-nachweis.pdf"

        with patch(
            "app.api.attachments.permission_service.can_view_absence",
            return_value=True,
        ):
            with patch(
                "app.api.attachments.attachment_service.get_file_path",
                return_value=resolved_path,
            ) as mock_get_path:
                response = await unwrap(download_attachment)(
                    request=request,
                    absence_id=1,
                    attachment_id=1,
                    current_user=teacher,
                    db=db,
                )

        mock_get_path.assert_called_once_with(mock_attachment.file_path)
        assert isinstance(response, FileResponse)
        assert response.path == resolved_path


# ============================================================================
# Tests: delete_attachment()
# ============================================================================


class TestDeleteAttachment:
    """delete_attachment: 404/403-Checks, delete_file, DB-Delete, Audit-Log"""

    @pytest.mark.asyncio
    async def test_raises_404_when_attachment_not_found(self, teacher):
        """404 wenn Attachment nicht in DB"""
        db = make_mock_db(result=None)
        request = make_mock_request()

        with pytest.raises(HTTPException) as exc_info:
            await unwrap(delete_attachment)(
                request=request,
                absence_id=1,
                attachment_id=999,
                current_user=teacher,
                db=db,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_403_when_no_permission(self, teacher):
        """403 wenn can_edit_absence=False"""
        mock_attachment = make_mock_attachment()
        db = make_mock_db(result=mock_attachment)
        request = make_mock_request()

        with patch(
            "app.api.attachments.permission_service.can_edit_absence",
            return_value=False,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await unwrap(delete_attachment)(
                    request=request,
                    absence_id=1,
                    attachment_id=1,
                    current_user=teacher,
                    db=db,
                )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_deletes_file_from_disk_and_db(self, planner):
        """delete_file aufgerufen + DB-Eintrag gelöscht + committed"""
        mock_attachment = make_mock_attachment()
        db = make_mock_db(result=mock_attachment)
        request = make_mock_request()

        with patch(
            "app.api.attachments.permission_service.can_edit_absence",
            return_value=True,
        ):
            with patch(
                "app.api.attachments.attachment_service.delete_file"
            ) as mock_delete_file:
                with patch("app.api.attachments.audit_file_deleted"):
                    result = await unwrap(delete_attachment)(
                        request=request,
                        absence_id=1,
                        attachment_id=1,
                        current_user=planner,
                        db=db,
                    )

        mock_delete_file.assert_called_once_with(mock_attachment.file_path)
        db.delete.assert_called_once_with(mock_attachment)
        db.commit.assert_called_once()
        assert result == {"message": "Attachment deleted"}

    @pytest.mark.asyncio
    async def test_audit_log_called_before_db_delete(self, planner):
        """audit_file_deleted wird aufgerufen (vor DB-Löschung)"""
        mock_attachment = make_mock_attachment()
        db = make_mock_db(result=mock_attachment)
        request = make_mock_request()
        call_order = []

        def track_audit(*args, **kwargs):
            call_order.append("audit")

        def track_db_delete(obj):
            call_order.append("db_delete")

        db.delete.side_effect = track_db_delete

        with patch(
            "app.api.attachments.permission_service.can_edit_absence",
            return_value=True,
        ):
            with patch("app.api.attachments.attachment_service.delete_file"):
                with patch(
                    "app.api.attachments.audit_file_deleted",
                    side_effect=track_audit,
                ):
                    await unwrap(delete_attachment)(
                        request=request,
                        absence_id=1,
                        attachment_id=1,
                        current_user=planner,
                        db=db,
                    )

        assert call_order == ["audit", "db_delete"]
