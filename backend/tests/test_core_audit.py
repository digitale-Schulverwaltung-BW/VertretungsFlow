"""
Unit tests for core/audit.py

- get_client_ip: IP extraction from request headers
- audit_log: structured JSON logging
- Convenience functions: audit_user_created, audit_absence_approved, etc.
"""

import json
import logging
from unittest.mock import Mock, patch, call

import pytest

from app.core.audit import (
    audit_absence_approved,
    audit_absence_completed,
    audit_absence_created,
    audit_file_deleted,
    audit_file_uploaded,
    audit_log,
    audit_role_changed,
    audit_user_created,
    audit_user_updated,
    get_client_ip,
)


def make_mock_request(x_forwarded_for=None, x_real_ip=None, client_host=None):
    """Build a mock Request with configurable IP headers."""
    request = Mock()

    def headers_get(key, default=None):
        if key == "X-Forwarded-For":
            return x_forwarded_for
        if key == "X-Real-IP":
            return x_real_ip
        return default

    request.headers.get = Mock(side_effect=headers_get)

    if client_host is not None:
        request.client = Mock()
        request.client.host = client_host
    else:
        request.client = None

    return request


# ---------------------------------------------------------------------------
# TestGetClientIp
# ---------------------------------------------------------------------------


class TestGetClientIp:
    def test_x_forwarded_for_returns_first_ip(self):
        request = make_mock_request(x_forwarded_for="192.168.1.1, 10.0.0.1")
        assert get_client_ip(request) == "192.168.1.1"

    def test_x_forwarded_for_single_ip(self):
        request = make_mock_request(x_forwarded_for="203.0.113.42")
        assert get_client_ip(request) == "203.0.113.42"

    def test_x_real_ip_fallback_when_no_forwarded(self):
        request = make_mock_request(x_real_ip="10.0.0.5")
        assert get_client_ip(request) == "10.0.0.5"

    def test_client_host_fallback(self):
        request = make_mock_request(client_host="172.16.0.1")
        assert get_client_ip(request) == "172.16.0.1"

    def test_returns_unknown_when_no_ip_info(self):
        request = make_mock_request()  # no headers, no client
        assert get_client_ip(request) == "unknown"


# ---------------------------------------------------------------------------
# TestAuditLog
# ---------------------------------------------------------------------------


class TestAuditLog:
    def test_logs_json_with_correct_action(self):
        request = make_mock_request(x_forwarded_for="1.2.3.4")

        with patch("app.core.audit.logger") as mock_logger:
            audit_log("absence_created", 7, "absence", 99, {}, request=request)

        assert mock_logger.info.called
        log_msg = mock_logger.info.call_args[0][0]
        assert log_msg.startswith("AUDIT: ")
        data = json.loads(log_msg[len("AUDIT: ") :])
        assert data["action"] == "absence_created"
        assert data["user_id"] == 7
        assert data["resource_type"] == "absence"
        assert data["resource_id"] == 99

    def test_ip_extracted_from_request_when_not_provided(self):
        request = make_mock_request(x_forwarded_for="5.6.7.8")

        with patch("app.core.audit.logger") as mock_logger:
            audit_log("test_action", 1, "absence", request=request)

        log_msg = mock_logger.info.call_args[0][0]
        data = json.loads(log_msg[len("AUDIT: ") :])
        assert data["ip_address"] == "5.6.7.8"

    def test_explicit_ip_address_used_when_no_request(self):
        with patch("app.core.audit.logger") as mock_logger:
            audit_log("test_action", 1, "absence", ip_address="9.9.9.9")

        log_msg = mock_logger.info.call_args[0][0]
        data = json.loads(log_msg[len("AUDIT: ") :])
        assert data["ip_address"] == "9.9.9.9"

    def test_unknown_ip_when_neither_provided(self):
        with patch("app.core.audit.logger") as mock_logger:
            audit_log("test_action", 1, "absence")

        log_msg = mock_logger.info.call_args[0][0]
        data = json.loads(log_msg[len("AUDIT: ") :])
        assert data["ip_address"] == "unknown"


# ---------------------------------------------------------------------------
# TestConvenienceFunctions
# ---------------------------------------------------------------------------


class TestConvenienceFunctions:
    """Verify each convenience function calls audit_log with the right action."""

    def _extract_action(self, mock_logger):
        log_msg = mock_logger.info.call_args[0][0]
        data = json.loads(log_msg[len("AUDIT: ") :])
        return data["action"]

    def test_audit_user_created_action(self):
        request = make_mock_request(client_host="1.1.1.1")
        with patch("app.core.audit.logger") as mock_logger:
            audit_user_created(user_id=2, created_by=1, details={}, request=request)
        assert self._extract_action(mock_logger) == "user_created"

    def test_audit_user_updated_action(self):
        request = make_mock_request(client_host="1.1.1.1")
        with patch("app.core.audit.logger") as mock_logger:
            audit_user_updated(user_id=2, updated_by=1, details={}, request=request)
        assert self._extract_action(mock_logger) == "user_updated"

    def test_audit_absence_created_action(self):
        request = make_mock_request(client_host="1.1.1.1")
        with patch("app.core.audit.logger") as mock_logger:
            audit_absence_created(absence_id=5, user_id=1, details={}, request=request)
        assert self._extract_action(mock_logger) == "absence_created"

    def test_audit_absence_approved_action(self):
        request = make_mock_request(client_host="1.1.1.1")
        with patch("app.core.audit.logger") as mock_logger:
            audit_absence_approved(
                absence_id=5, approver_id=2, details={}, request=request
            )
        assert self._extract_action(mock_logger) == "absence_approved"

    def test_audit_absence_completed_action(self):
        request = make_mock_request(client_host="1.1.1.1")
        with patch("app.core.audit.logger") as mock_logger:
            audit_absence_completed(
                absence_id=5, completer_id=3, details={}, request=request
            )
        assert self._extract_action(mock_logger) == "absence_completed"

    def test_audit_file_uploaded_action(self):
        request = make_mock_request(client_host="1.1.1.1")
        with patch("app.core.audit.logger") as mock_logger:
            audit_file_uploaded(
                attachment_id=10, user_id=1, details={}, request=request
            )
        assert self._extract_action(mock_logger) == "file_uploaded"

    def test_audit_file_deleted_action(self):
        request = make_mock_request(client_host="1.1.1.1")
        with patch("app.core.audit.logger") as mock_logger:
            audit_file_deleted(attachment_id=10, user_id=1, details={}, request=request)
        assert self._extract_action(mock_logger) == "file_deleted"

    def test_audit_role_changed_stores_old_and_new_role(self):
        request = make_mock_request(client_host="1.1.1.1")
        with patch("app.core.audit.logger") as mock_logger:
            audit_role_changed(
                user_id=3,
                changed_by=1,
                old_role="teacher",
                new_role="admin",
                request=request,
            )

        log_msg = mock_logger.info.call_args[0][0]
        data = json.loads(log_msg[len("AUDIT: ") :])
        assert data["action"] == "role_changed"
        assert data["details"]["old_role"] == "teacher"
        assert data["details"]["new_role"] == "admin"
