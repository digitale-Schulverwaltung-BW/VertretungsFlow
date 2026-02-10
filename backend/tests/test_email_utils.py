"""
Tests for email_utils.py
Tests email helper functions and constants
"""

from unittest.mock import Mock

import pytest

from app.models.models import UserRole
from app.utils.email_utils import REASON_LABELS, get_recipients_by_roles


# ============================================================================
# Test REASON_LABELS constant
# ============================================================================


class TestReasonLabels:
    """Test reason label constants"""

    def test_all_reasons_present(self):
        """Test that all expected absence reasons have labels"""
        expected_reasons = ["sick", "training", "excursion", "personal", "other"]
        assert set(REASON_LABELS.keys()) == set(expected_reasons)

    def test_sick_label(self):
        """Test sick reason label"""
        assert REASON_LABELS["sick"] == "Krankheit"

    def test_training_label(self):
        """Test training reason label"""
        assert REASON_LABELS["training"] == "Fortbildung"

    def test_excursion_label(self):
        """Test excursion reason label"""
        assert REASON_LABELS["excursion"] == "Exkursion"

    def test_personal_label(self):
        """Test personal reason label"""
        assert REASON_LABELS["personal"] == "Privat"

    def test_other_label(self):
        """Test other reason label"""
        assert REASON_LABELS["other"] == "Sonstiges"

    def test_labels_are_german(self):
        """Test that all labels are in German"""
        german_labels = ["Krankheit", "Fortbildung", "Exkursion", "Privat", "Sonstiges"]
        assert set(REASON_LABELS.values()) == set(german_labels)


# ============================================================================
# Test get_recipients_by_roles()
# ============================================================================


class TestGetRecipientsByRoles:
    """Test getting email recipients by role"""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return Mock()

    @pytest.fixture
    def active_admin_user(self):
        """Create mock active admin user"""
        user = Mock()
        user.email = "admin@example.com"
        user.role = UserRole.ADMIN
        user.is_active = True
        return user

    @pytest.fixture
    def active_planner_user(self):
        """Create mock active planner user"""
        user = Mock()
        user.email = "planner@example.com"
        user.role = UserRole.PLANNER
        user.is_active = True
        return user

    @pytest.fixture
    def active_dept_head_user(self):
        """Create mock active dept head user"""
        user = Mock()
        user.email = "depthead@example.com"
        user.role = UserRole.DEPARTMENT_HEAD
        user.is_active = True
        return user

    @pytest.fixture
    def inactive_admin_user(self):
        """Create mock inactive admin user"""
        user = Mock()
        user.email = "inactive_admin@example.com"
        user.role = UserRole.ADMIN
        user.is_active = False
        return user

    @pytest.fixture
    def admin_without_email(self):
        """Create mock admin user without email"""
        user = Mock()
        user.email = None
        user.role = UserRole.ADMIN
        user.is_active = True
        return user

    def test_get_single_role_recipients(
        self, mock_db, active_admin_user, active_planner_user
    ):
        """Test getting recipients for a single role"""
        # Setup mock query chain
        mock_query = Mock()
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.all.return_value = [active_admin_user]
        mock_db.query.return_value = mock_query

        # Call function
        recipients = get_recipients_by_roles(mock_db, [UserRole.ADMIN])

        # Verify
        assert recipients == ["admin@example.com"]
        mock_db.query.assert_called_once()

    def test_get_multiple_roles_recipients(
        self, mock_db, active_admin_user, active_planner_user, active_dept_head_user
    ):
        """Test getting recipients for multiple roles"""
        # Setup mock query chain
        mock_query = Mock()
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.all.return_value = [
            active_admin_user,
            active_planner_user,
            active_dept_head_user,
        ]
        mock_db.query.return_value = mock_query

        # Call function
        recipients = get_recipients_by_roles(
            mock_db, [UserRole.ADMIN, UserRole.PLANNER, UserRole.DEPARTMENT_HEAD]
        )

        # Verify
        assert set(recipients) == {
            "admin@example.com",
            "planner@example.com",
            "depthead@example.com",
        }

    def test_excludes_inactive_users(
        self, mock_db, active_admin_user, inactive_admin_user
    ):
        """Test that inactive users are excluded (SECURITY!)"""
        # Setup mock query chain - only return active user
        mock_query = Mock()
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.all.return_value = [active_admin_user]  # Inactive user filtered out
        mock_db.query.return_value = mock_query

        # Call function
        recipients = get_recipients_by_roles(mock_db, [UserRole.ADMIN])

        # Verify - should only get active user
        assert recipients == ["admin@example.com"]
        assert "inactive_admin@example.com" not in recipients

    def test_excludes_users_without_email(self, mock_db, active_admin_user):
        """Test that users without email are excluded"""
        # Setup mock query chain - users without email already filtered by DB
        mock_query = Mock()
        mock_filter = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [active_admin_user]
        mock_db.query.return_value = mock_query

        # Call function
        recipients = get_recipients_by_roles(mock_db, [UserRole.ADMIN])

        # Verify
        assert recipients == ["admin@example.com"]
        assert None not in recipients

    def test_empty_result_when_no_users(self, mock_db):
        """Test that empty list is returned when no users match"""
        # Setup mock query chain
        mock_query = Mock()
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.all.return_value = []
        mock_db.query.return_value = mock_query

        # Call function
        recipients = get_recipients_by_roles(mock_db, [UserRole.ADMIN])

        # Verify
        assert recipients == []

    def test_query_filters_correctly(self, mock_db):
        """Test that database query applies correct filters"""
        # Setup mock query chain
        mock_query = Mock()
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.all.return_value = []
        mock_db.query.return_value = mock_query

        # Call function
        get_recipients_by_roles(mock_db, [UserRole.ADMIN, UserRole.PLANNER])

        # Verify query was called
        mock_db.query.assert_called_once()
        # Verify filter was called (should filter by role.in_(), is_active, email.isnot(None))
        mock_query.filter.assert_called_once()

    def test_returns_only_email_strings(
        self, mock_db, active_admin_user, active_planner_user
    ):
        """Test that function returns list of strings only"""
        # Setup mock query chain
        mock_query = Mock()
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.all.return_value = [active_admin_user, active_planner_user]
        mock_db.query.return_value = mock_query

        # Call function
        recipients = get_recipients_by_roles(
            mock_db, [UserRole.ADMIN, UserRole.PLANNER]
        )

        # Verify all are strings
        assert all(isinstance(email, str) for email in recipients)
        assert len(recipients) == 2

    def test_planner_and_admin_roles(
        self, mock_db, active_admin_user, active_planner_user
    ):
        """Test getting planners and admins (common notification use case)"""
        # Setup mock query chain
        mock_query = Mock()
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.all.return_value = [active_admin_user, active_planner_user]
        mock_db.query.return_value = mock_query

        # Call function
        recipients = get_recipients_by_roles(
            mock_db, [UserRole.ADMIN, UserRole.PLANNER]
        )

        # Verify
        assert set(recipients) == {"admin@example.com", "planner@example.com"}

    def test_department_head_only(self, mock_db, active_dept_head_user):
        """Test getting only department heads"""
        # Setup mock query chain
        mock_query = Mock()
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.all.return_value = [active_dept_head_user]
        mock_db.query.return_value = mock_query

        # Call function
        recipients = get_recipients_by_roles(mock_db, [UserRole.DEPARTMENT_HEAD])

        # Verify
        assert recipients == ["depthead@example.com"]
