"""
Unit tests for api/pdf_forms.py

Two endpoints:
- GET /absences/{id}/pdf-forms         → list_available_forms
- GET /absences/{id}/pdf-forms/{type}  → download_pdf_form
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from fastapi import HTTPException
from starlette.responses import Response

from app.api.pdf_forms import download_pdf_form, list_available_forms
from app.models.models import UserRole


def unwrap(func):
    """Return the original function, bypassing slowapi @limiter.limit() decorator"""
    return func.__wrapped__


def make_mock_db(absence=None):
    db = Mock()
    q = Mock()
    q.options.return_value = q
    q.filter.return_value = q
    q.first.return_value = absence
    db.query.return_value = q
    return db


def make_mock_absence(absence_id=1, reason="excursion"):
    absence = Mock()
    absence.id = absence_id
    absence.reason = reason
    return absence


def make_mock_user(role=UserRole.TEACHER):
    user = Mock()
    user.username = "testuser"
    user.role = role
    return user


# ---------------------------------------------------------------------------
# TestListAvailableForms
# ---------------------------------------------------------------------------


class TestListAvailableForms:
    @pytest.mark.asyncio
    async def test_absence_not_found_raises_404(self):
        db = make_mock_db(absence=None)
        user = make_mock_user()
        request = Mock()

        with pytest.raises(HTTPException) as exc_info:
            await unwrap(list_available_forms)(
                request=request, absence_id=1, current_user=user, db=db
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_no_permission_raises_403(self):
        absence = make_mock_absence()
        db = make_mock_db(absence=absence)
        user = make_mock_user()
        request = Mock()

        with patch(
            "app.api.pdf_forms.permission_service.can_view_absence",
            return_value=False,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await unwrap(list_available_forms)(
                    request=request, absence_id=1, current_user=user, db=db
                )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_returns_available_forms_from_service(self):
        absence = make_mock_absence()
        db = make_mock_db(absence=absence)
        user = make_mock_user()
        request = Mock()
        mock_forms = [{"type": "excursion_form", "label": "Exkursionsantrag"}]

        with patch(
            "app.api.pdf_forms.permission_service.can_view_absence", return_value=True
        ):
            with patch(
                "app.api.pdf_forms.pdf_service.get_available_forms",
                return_value=mock_forms,
            ):
                result = await unwrap(list_available_forms)(
                    request=request, absence_id=1, current_user=user, db=db
                )

        assert result == mock_forms

    @pytest.mark.asyncio
    async def test_pdf_service_called_with_queried_absence(self):
        absence = make_mock_absence()
        db = make_mock_db(absence=absence)
        user = make_mock_user()
        request = Mock()

        with patch(
            "app.api.pdf_forms.permission_service.can_view_absence", return_value=True
        ):
            with patch(
                "app.api.pdf_forms.pdf_service.get_available_forms",
                return_value=[],
            ) as mock_get_forms:
                await unwrap(list_available_forms)(
                    request=request, absence_id=1, current_user=user, db=db
                )

        mock_get_forms.assert_called_once_with(absence)


# ---------------------------------------------------------------------------
# TestDownloadPdfForm
# ---------------------------------------------------------------------------


class TestDownloadPdfForm:
    @pytest.mark.asyncio
    async def test_absence_not_found_raises_404(self):
        db = make_mock_db(absence=None)
        user = make_mock_user()
        request = Mock()

        with pytest.raises(HTTPException) as exc_info:
            await unwrap(download_pdf_form)(
                request=request,
                absence_id=1,
                form_type="excursion_form",
                current_user=user,
                db=db,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_no_permission_raises_403(self):
        absence = make_mock_absence()
        db = make_mock_db(absence=absence)
        user = make_mock_user()
        request = Mock()

        with patch(
            "app.api.pdf_forms.permission_service.can_view_absence",
            return_value=False,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await unwrap(download_pdf_form)(
                    request=request,
                    absence_id=1,
                    form_type="excursion_form",
                    current_user=user,
                    db=db,
                )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_invalid_form_type_raises_400(self):
        absence = make_mock_absence(reason="illness")
        db = make_mock_db(absence=absence)
        user = make_mock_user()
        request = Mock()
        # Only "illness_form" available, not "excursion_form"
        mock_forms = [{"type": "illness_form", "label": "Krankmeldung"}]

        with patch(
            "app.api.pdf_forms.permission_service.can_view_absence", return_value=True
        ):
            with patch(
                "app.api.pdf_forms.pdf_service.get_available_forms",
                return_value=mock_forms,
            ):
                with pytest.raises(HTTPException) as exc_info:
                    await unwrap(download_pdf_form)(
                        request=request,
                        absence_id=1,
                        form_type="excursion_form",
                        current_user=user,
                        db=db,
                    )

        assert exc_info.value.status_code == 400
        assert "excursion_form" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_success_returns_pdf_response_with_correct_content(self):
        absence = make_mock_absence(absence_id=5, reason="excursion")
        db = make_mock_db(absence=absence)
        user = make_mock_user()
        request = Mock()
        mock_forms = [{"type": "excursion_form", "label": "Exkursionsantrag"}]
        pdf_bytes = b"%PDF-1.4 fake pdf content"

        with patch(
            "app.api.pdf_forms.permission_service.can_view_absence", return_value=True
        ):
            with patch(
                "app.api.pdf_forms.pdf_service.get_available_forms",
                return_value=mock_forms,
            ):
                with patch(
                    "app.api.pdf_forms.pdf_service.generate_filled_pdf",
                    new_callable=AsyncMock,
                    return_value=pdf_bytes,
                ):
                    result = await unwrap(download_pdf_form)(
                        request=request,
                        absence_id=5,
                        form_type="excursion_form",
                        current_user=user,
                        db=db,
                    )

        assert isinstance(result, Response)
        assert result.body == pdf_bytes
        assert result.media_type == "application/pdf"

    @pytest.mark.asyncio
    async def test_filename_contains_absence_id_and_label(self):
        absence = make_mock_absence(absence_id=42, reason="excursion")
        db = make_mock_db(absence=absence)
        user = make_mock_user()
        request = Mock()
        mock_forms = [{"type": "excursion_form", "label": "Exkursionsantrag"}]
        pdf_bytes = b"%PDF fake"

        with patch(
            "app.api.pdf_forms.permission_service.can_view_absence", return_value=True
        ):
            with patch(
                "app.api.pdf_forms.pdf_service.get_available_forms",
                return_value=mock_forms,
            ):
                with patch(
                    "app.api.pdf_forms.pdf_service.generate_filled_pdf",
                    new_callable=AsyncMock,
                    return_value=pdf_bytes,
                ):
                    result = await unwrap(download_pdf_form)(
                        request=request,
                        absence_id=42,
                        form_type="excursion_form",
                        current_user=user,
                        db=db,
                    )

        content_disp = result.headers["content-disposition"]
        assert "42" in content_disp
        assert "Exkursionsantrag" in content_disp

    @pytest.mark.asyncio
    async def test_filename_sanitizes_special_characters(self):
        """Special chars in form label (/, (, ), §) must be replaced with _"""
        absence = make_mock_absence(absence_id=7, reason="other")
        db = make_mock_db(absence=absence)
        user = make_mock_user()
        request = Mock()
        mock_forms = [{"type": "other_form", "label": "Antrag/Formular (§3)"}]
        pdf_bytes = b"%PDF fake"

        with patch(
            "app.api.pdf_forms.permission_service.can_view_absence", return_value=True
        ):
            with patch(
                "app.api.pdf_forms.pdf_service.get_available_forms",
                return_value=mock_forms,
            ):
                with patch(
                    "app.api.pdf_forms.pdf_service.generate_filled_pdf",
                    new_callable=AsyncMock,
                    return_value=pdf_bytes,
                ):
                    result = await unwrap(download_pdf_form)(
                        request=request,
                        absence_id=7,
                        form_type="other_form",
                        current_user=user,
                        db=db,
                    )

        content_disp = result.headers["content-disposition"]
        # Extract filename value (strip surrounding quotes)
        filename = content_disp.split('filename="')[1].rstrip('"')
        assert "/" not in filename
        assert "(" not in filename
        assert ")" not in filename
