"""
Unit tests for services/webuntis/client.py

WebUntisAPIClient — low-level HTTP communication:
- authenticate: success, API error, non-200, exception
- logout: no session (skip), success, non-200, exception
- _call_api: success, API error, session-expiration retry, re-auth failure, non-200, exception
- _handle_expired_session: clears session_id and delegates to authenticate
- get_teachers / get_timetable / get_subjects / get_classes / get_rooms / get_timegrid:
  wrapper behaviour (returns result / returns [] on None)
- find_teacher_id: exact match, case-insensitive, not found, empty list
"""

import contextlib
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.services.webuntis.client import WebUntisAPIClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_client() -> WebUntisAPIClient:
    """Create a client with explicit credentials (bypasses settings)."""
    return WebUntisAPIClient(
        server="test.webuntis.com",
        username="api_user",
        password="api_pass",
    )


def make_http_response(status_code: int = 200, json_data=None, text: str = "") -> Mock:
    response = Mock()
    response.status_code = status_code
    response.text = text
    response.headers = {}  # dict(response.headers) is called in authenticate()
    if json_data is not None:
        response.json.return_value = json_data
    return response


def make_mock_http_client(response=None, side_effects=None) -> AsyncMock:
    """Return an AsyncMock simulating httpx.AsyncClient."""
    mock_client = AsyncMock()
    if side_effects is not None:
        mock_client.post = AsyncMock(side_effect=side_effects)
    elif response is not None:
        mock_client.post = AsyncMock(return_value=response)
    return mock_client


@contextlib.contextmanager
def patch_httpx(mock_http_client):
    """Context manager that patches httpx.AsyncClient.__aenter__."""
    with patch("app.services.webuntis.client.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        yield mock_cls


# ---------------------------------------------------------------------------
# TestAuthenticate
# ---------------------------------------------------------------------------


class TestAuthenticate:
    @pytest.mark.asyncio
    async def test_success_sets_session_and_person_id(self):
        client = make_client()
        response = make_http_response(
            json_data={"result": {"sessionId": "sess-abc", "personId": 42}}
        )
        with patch_httpx(make_mock_http_client(response)):
            result = await client.authenticate()

        assert result is True
        assert client.session_id == "sess-abc"
        assert client.person_id == 42

    @pytest.mark.asyncio
    async def test_api_error_in_response_returns_false(self):
        client = make_client()
        response = make_http_response(
            json_data={"error": {"code": 500, "message": "bad credentials"}}
        )
        with patch_httpx(make_mock_http_client(response)):
            result = await client.authenticate()

        assert result is False
        assert client.session_id is None

    @pytest.mark.asyncio
    async def test_non_200_status_returns_false(self):
        client = make_client()
        response = make_http_response(status_code=503)
        with patch_httpx(make_mock_http_client(response)):
            result = await client.authenticate()

        assert result is False

    @pytest.mark.asyncio
    async def test_exception_during_request_returns_false(self):
        client = make_client()
        mock_http = make_mock_http_client(side_effects=ConnectionError("unreachable"))
        with patch_httpx(mock_http):
            result = await client.authenticate()

        assert result is False

    @pytest.mark.asyncio
    async def test_actual_password_sent_not_masked(self):
        """Verify the real password (not '***') is used in the actual POST."""
        client = make_client()
        response = make_http_response(
            json_data={"result": {"sessionId": "s", "personId": 1}}
        )
        mock_http = make_mock_http_client(response)
        with patch_httpx(mock_http):
            await client.authenticate()

        call_kwargs = mock_http.post.call_args
        sent_json = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert sent_json["params"]["password"] == "api_pass"


# ---------------------------------------------------------------------------
# TestLogout
# ---------------------------------------------------------------------------


class TestLogout:
    @pytest.mark.asyncio
    async def test_no_session_returns_true_without_http_call(self):
        client = make_client()
        client.session_id = None

        with patch("app.services.webuntis.client.httpx.AsyncClient") as mock_cls:
            result = await client.logout()

        assert result is True
        mock_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_success_clears_session_and_returns_true(self):
        client = make_client()
        client.session_id = "active-session"
        response = make_http_response(status_code=200)
        with patch_httpx(make_mock_http_client(response)):
            result = await client.logout()

        assert result is True
        assert client.session_id is None

    @pytest.mark.asyncio
    async def test_non_200_clears_session_and_returns_false(self):
        client = make_client()
        client.session_id = "active-session"
        response = make_http_response(status_code=500)
        with patch_httpx(make_mock_http_client(response)):
            result = await client.logout()

        assert result is False
        assert client.session_id is None  # always cleared

    @pytest.mark.asyncio
    async def test_exception_returns_false(self):
        client = make_client()
        client.session_id = "active-session"
        mock_http = make_mock_http_client(side_effects=OSError("network error"))
        with patch_httpx(mock_http):
            result = await client.logout()

        assert result is False


# ---------------------------------------------------------------------------
# TestCallApi
# ---------------------------------------------------------------------------


class TestCallApi:
    @pytest.mark.asyncio
    async def test_success_returns_result(self):
        client = make_client()
        client.session_id = "valid-session"
        expected = [{"id": 1, "name": "Müller"}]
        response = make_http_response(json_data={"result": expected})
        with patch_httpx(make_mock_http_client(response)):
            result = await client._call_api("getTeachers")

        assert result == expected

    @pytest.mark.asyncio
    async def test_api_error_returns_none(self):
        client = make_client()
        response = make_http_response(
            json_data={"error": {"code": -8504, "message": "method not found"}}
        )
        with patch_httpx(make_mock_http_client(response)):
            result = await client._call_api("unknownMethod")

        assert result is None

    @pytest.mark.asyncio
    async def test_session_expiration_retries_and_returns_result(self):
        client = make_client()
        client.session_id = "expired"

        expiry_response = make_http_response(
            json_data={"error": {"code": -8520, "message": "Session expired"}}
        )
        success_response = make_http_response(json_data={"result": [{"id": 7}]})
        mock_http = make_mock_http_client(
            side_effects=[expiry_response, success_response]
        )

        with patch.object(
            client, "_handle_expired_session", new_callable=AsyncMock
        ) as mock_handle:
            mock_handle.return_value = True
            with patch_httpx(mock_http):
                result = await client._call_api("getTeachers")

        assert result == [{"id": 7}]
        mock_handle.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_expiration_with_reauth_failure_returns_none(self):
        client = make_client()
        client.session_id = "expired"

        expiry_response = make_http_response(
            json_data={"error": {"code": -8520, "message": "Session expired"}}
        )
        with patch.object(
            client, "_handle_expired_session", new_callable=AsyncMock
        ) as mock_handle:
            mock_handle.return_value = False
            with patch_httpx(make_mock_http_client(expiry_response)):
                result = await client._call_api("getTeachers")

        assert result is None

    @pytest.mark.asyncio
    async def test_non_200_status_returns_none(self):
        client = make_client()
        response = make_http_response(status_code=502)
        with patch_httpx(make_mock_http_client(response)):
            result = await client._call_api("getTeachers")

        assert result is None

    @pytest.mark.asyncio
    async def test_exception_returns_none(self):
        client = make_client()
        mock_http = make_mock_http_client(
            side_effects=TimeoutError("connection timeout")
        )
        with patch_httpx(mock_http):
            result = await client._call_api("getTeachers")

        assert result is None

    @pytest.mark.asyncio
    async def test_session_expiry_not_handled_when_flag_false(self):
        """With handle_session_expiration=False, expiry error is treated as a plain error."""
        client = make_client()
        client.session_id = "expired"

        expiry_response = make_http_response(
            json_data={"error": {"code": -8520, "message": "Session expired"}}
        )
        with patch.object(
            client, "_handle_expired_session", new_callable=AsyncMock
        ) as mock_handle:
            with patch_httpx(make_mock_http_client(expiry_response)):
                result = await client._call_api(
                    "getTeachers", handle_session_expiration=False
                )

        assert result is None
        mock_handle.assert_not_called()


# ---------------------------------------------------------------------------
# TestHandleExpiredSession
# ---------------------------------------------------------------------------


class TestHandleExpiredSession:
    @pytest.mark.asyncio
    async def test_clears_session_id_before_authenticate(self):
        client = make_client()
        client.session_id = "stale-session"

        with patch.object(client, "authenticate", new_callable=AsyncMock) as mock_auth:
            mock_auth.return_value = True
            await client._handle_expired_session()

        assert client.session_id is None
        mock_auth.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_authenticate_result(self):
        client = make_client()
        client.session_id = "stale"

        with patch.object(client, "authenticate", new_callable=AsyncMock) as mock_auth:
            mock_auth.return_value = False
            result = await client._handle_expired_session()

        assert result is False


# ---------------------------------------------------------------------------
# TestWrapperMethods  (get_teachers, get_timetable, get_subjects, etc.)
# ---------------------------------------------------------------------------


class TestWrapperMethods:
    @pytest.mark.asyncio
    async def test_get_teachers_returns_result(self):
        client = make_client()
        expected = [{"id": 1, "name": "Schmidt"}]
        with patch.object(
            client, "_call_api", new_callable=AsyncMock, return_value=expected
        ):
            result = await client.get_teachers()
        assert result == expected

    @pytest.mark.asyncio
    async def test_get_teachers_returns_empty_list_on_none(self):
        client = make_client()
        with patch.object(
            client, "_call_api", new_callable=AsyncMock, return_value=None
        ):
            result = await client.get_teachers()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_timetable_passes_params_and_returns_result(self):
        client = make_client()
        expected = [{"lessonId": 10}]
        with patch.object(
            client, "_call_api", new_callable=AsyncMock, return_value=expected
        ) as mock_call:
            result = await client.get_timetable(
                teacher_id=5, start_date=20260101, end_date=20260131
            )

        assert result == expected
        call_params = mock_call.call_args[0][1]  # second positional arg = params dict
        assert call_params["options"]["element"]["id"] == 5
        assert call_params["options"]["startDate"] == 20260101
        assert call_params["options"]["endDate"] == 20260131

    @pytest.mark.asyncio
    async def test_get_timetable_returns_empty_list_on_none(self):
        client = make_client()
        with patch.object(
            client, "_call_api", new_callable=AsyncMock, return_value=None
        ):
            result = await client.get_timetable(1, 20260101, 20260131)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_subjects_returns_result(self):
        client = make_client()
        expected = [{"id": 3, "name": "Math"}]
        with patch.object(
            client, "_call_api", new_callable=AsyncMock, return_value=expected
        ):
            result = await client.get_subjects()
        assert result == expected

    @pytest.mark.asyncio
    async def test_get_subjects_returns_empty_list_on_none(self):
        client = make_client()
        with patch.object(
            client, "_call_api", new_callable=AsyncMock, return_value=None
        ):
            assert await client.get_subjects() == []

    @pytest.mark.asyncio
    async def test_get_classes_returns_result(self):
        client = make_client()
        expected = [{"id": 1, "name": "5A"}, {"id": 2, "name": "5B"}]
        with patch.object(
            client, "_call_api", new_callable=AsyncMock, return_value=expected
        ):
            result = await client.get_classes()
        assert result == expected

    @pytest.mark.asyncio
    async def test_get_classes_returns_empty_list_on_none(self):
        client = make_client()
        with patch.object(
            client, "_call_api", new_callable=AsyncMock, return_value=None
        ):
            assert await client.get_classes() == []

    @pytest.mark.asyncio
    async def test_get_rooms_returns_result(self):
        client = make_client()
        expected = [{"id": 1, "name": "Raum 101"}]
        with patch.object(
            client, "_call_api", new_callable=AsyncMock, return_value=expected
        ):
            result = await client.get_rooms()
        assert result == expected

    @pytest.mark.asyncio
    async def test_get_rooms_returns_empty_list_on_none(self):
        client = make_client()
        with patch.object(
            client, "_call_api", new_callable=AsyncMock, return_value=None
        ):
            assert await client.get_rooms() == []

    @pytest.mark.asyncio
    async def test_get_timegrid_returns_result(self):
        client = make_client()
        expected = [{"day": 2, "timeUnits": []}]
        with patch.object(
            client, "_call_api", new_callable=AsyncMock, return_value=expected
        ):
            result = await client.get_timegrid()
        assert result == expected

    @pytest.mark.asyncio
    async def test_get_timegrid_returns_empty_list_on_none(self):
        client = make_client()
        with patch.object(
            client, "_call_api", new_callable=AsyncMock, return_value=None
        ):
            assert await client.get_timegrid() == []


# ---------------------------------------------------------------------------
# TestFindTeacherId
# ---------------------------------------------------------------------------


class TestFindTeacherId:
    @pytest.mark.asyncio
    async def test_returns_id_for_exact_match(self):
        client = make_client()
        teachers = [
            {"id": 10, "name": "Mueller"},
            {"id": 20, "name": "Schmidt"},
        ]
        with patch.object(
            client, "get_teachers", new_callable=AsyncMock, return_value=teachers
        ):
            result = await client.find_teacher_id("Mueller")

        assert result == 10

    @pytest.mark.asyncio
    async def test_case_insensitive_match(self):
        client = make_client()
        teachers = [{"id": 15, "name": "Maier"}]
        with patch.object(
            client, "get_teachers", new_callable=AsyncMock, return_value=teachers
        ):
            result = await client.find_teacher_id("MAIER")

        assert result == 15

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        client = make_client()
        teachers = [{"id": 1, "name": "Braun"}]
        with patch.object(
            client, "get_teachers", new_callable=AsyncMock, return_value=teachers
        ):
            result = await client.find_teacher_id("Schwarz")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_teacher_list_empty(self):
        client = make_client()
        with patch.object(
            client, "get_teachers", new_callable=AsyncMock, return_value=[]
        ):
            result = await client.find_teacher_id("anyone")

        assert result is None
