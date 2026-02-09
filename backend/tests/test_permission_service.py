"""
Tests for permission_service.py
Tests authorization logic for absence management (security-critical!)
"""

from unittest.mock import Mock

import pytest

from app.models.models import AbsenceStatus, UserRole
from app.services.permission_service import PermissionService


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def permission_service():
    """Create PermissionService instance"""
    return PermissionService()


@pytest.fixture
def teacher_user():
    """Create mock teacher user"""
    user = Mock()
    user.id = 1
    user.role = UserRole.TEACHER
    user.email = "teacher@example.com"
    return user


@pytest.fixture
def dept_head_user():
    """Create mock department head user"""
    user = Mock()
    user.id = 2
    user.role = UserRole.DEPARTMENT_HEAD
    user.email = "depthead@example.com"
    return user


@pytest.fixture
def planner_user():
    """Create mock planner user"""
    user = Mock()
    user.id = 3
    user.role = UserRole.PLANNER
    user.email = "planner@example.com"
    return user


@pytest.fixture
def admin_user():
    """Create mock admin user"""
    user = Mock()
    user.id = 4
    user.role = UserRole.ADMIN
    user.email = "admin@example.com"
    return user


@pytest.fixture
def other_teacher_user():
    """Create another mock teacher user (for ownership tests)"""
    user = Mock()
    user.id = 99
    user.role = UserRole.TEACHER
    user.email = "other_teacher@example.com"
    return user


@pytest.fixture
def submitted_absence():
    """Create mock absence in SUBMITTED status"""
    absence = Mock()
    absence.id = 1
    absence.teacher_id = 1  # Belongs to teacher_user
    absence.status = AbsenceStatus.SUBMITTED
    return absence


@pytest.fixture
def approved_absence():
    """Create mock absence in APPROVED status"""
    absence = Mock()
    absence.id = 2
    absence.teacher_id = 1
    absence.status = AbsenceStatus.APPROVED
    return absence


@pytest.fixture
def completed_absence():
    """Create mock absence in COMPLETED status"""
    absence = Mock()
    absence.id = 3
    absence.teacher_id = 1
    absence.status = AbsenceStatus.COMPLETED
    return absence


@pytest.fixture
def draft_absence():
    """Create mock absence in DRAFT status"""
    absence = Mock()
    absence.id = 4
    absence.teacher_id = 1
    absence.status = AbsenceStatus.DRAFT
    return absence


@pytest.fixture
def other_teacher_absence():
    """Create mock absence belonging to another teacher"""
    absence = Mock()
    absence.id = 5
    absence.teacher_id = 99  # Belongs to other_teacher_user
    absence.status = AbsenceStatus.SUBMITTED
    return absence


# ============================================================================
# Test can_view_absence()
# ============================================================================


class TestCanViewAbsence:
    """Test viewing permissions"""

    def test_teacher_can_view_own_absence(
        self, permission_service, teacher_user, submitted_absence
    ):
        """Teachers can view their own absences"""
        assert permission_service.can_view_absence(teacher_user, submitted_absence)

    def test_teacher_cannot_view_other_absence(
        self, permission_service, teacher_user, other_teacher_absence
    ):
        """Teachers cannot view other teachers' absences (SECURITY!)"""
        assert not permission_service.can_view_absence(
            teacher_user, other_teacher_absence
        )

    def test_dept_head_can_view_all_absences(
        self, permission_service, dept_head_user, submitted_absence, other_teacher_absence
    ):
        """Department heads can view all absences"""
        assert permission_service.can_view_absence(dept_head_user, submitted_absence)
        assert permission_service.can_view_absence(
            dept_head_user, other_teacher_absence
        )

    def test_planner_can_view_all_absences(
        self, permission_service, planner_user, submitted_absence, other_teacher_absence
    ):
        """Planners can view all absences"""
        assert permission_service.can_view_absence(planner_user, submitted_absence)
        assert permission_service.can_view_absence(planner_user, other_teacher_absence)

    def test_admin_can_view_all_absences(
        self, permission_service, admin_user, submitted_absence, other_teacher_absence
    ):
        """Admins can view all absences"""
        assert permission_service.can_view_absence(admin_user, submitted_absence)
        assert permission_service.can_view_absence(admin_user, other_teacher_absence)


# ============================================================================
# Test can_edit_absence()
# ============================================================================


class TestCanEditAbsence:
    """Test editing permissions"""

    def test_teacher_can_edit_own_submitted_absence(
        self, permission_service, teacher_user, submitted_absence
    ):
        """Teachers can edit their own submitted absences"""
        assert permission_service.can_edit_absence(teacher_user, submitted_absence)

    def test_teacher_can_edit_own_approved_absence(
        self, permission_service, teacher_user, approved_absence
    ):
        """Teachers can edit their own approved absences"""
        assert permission_service.can_edit_absence(teacher_user, approved_absence)

    def test_teacher_cannot_edit_own_completed_absence(
        self, permission_service, teacher_user, completed_absence
    ):
        """Teachers cannot edit their own completed absences (SECURITY!)"""
        assert not permission_service.can_edit_absence(teacher_user, completed_absence)

    def test_teacher_cannot_edit_other_absence(
        self, permission_service, teacher_user, other_teacher_absence
    ):
        """Teachers cannot edit other teachers' absences (SECURITY!)"""
        assert not permission_service.can_edit_absence(
            teacher_user, other_teacher_absence
        )

    def test_admin_can_edit_completed_absence(
        self, permission_service, admin_user, completed_absence
    ):
        """Admins can edit completed absences"""
        assert permission_service.can_edit_absence(admin_user, completed_absence)

    def test_planner_can_edit_completed_absence(
        self, permission_service, planner_user, completed_absence
    ):
        """Planners can edit completed absences"""
        assert permission_service.can_edit_absence(planner_user, completed_absence)

    def test_dept_head_cannot_edit_completed_absence(
        self, permission_service, dept_head_user, completed_absence
    ):
        """Department heads cannot edit completed absences"""
        assert not permission_service.can_edit_absence(
            dept_head_user, completed_absence
        )

    def test_admin_can_edit_all_non_completed_absences(
        self,
        permission_service,
        admin_user,
        submitted_absence,
        approved_absence,
        other_teacher_absence,
    ):
        """Admins can edit all non-completed absences"""
        assert permission_service.can_edit_absence(admin_user, submitted_absence)
        assert permission_service.can_edit_absence(admin_user, approved_absence)
        assert permission_service.can_edit_absence(admin_user, other_teacher_absence)

    def test_planner_can_edit_all_non_completed_absences(
        self,
        permission_service,
        planner_user,
        submitted_absence,
        approved_absence,
        other_teacher_absence,
    ):
        """Planners can edit all non-completed absences"""
        assert permission_service.can_edit_absence(planner_user, submitted_absence)
        assert permission_service.can_edit_absence(planner_user, approved_absence)
        assert permission_service.can_edit_absence(planner_user, other_teacher_absence)


# ============================================================================
# Test can_approve_absence()
# ============================================================================


class TestCanApproveAbsence:
    """Test approval permissions"""

    def test_teacher_cannot_approve(self, permission_service, teacher_user):
        """Teachers cannot approve absences (SECURITY!)"""
        assert not permission_service.can_approve_absence(teacher_user)

    def test_teacher_cannot_approve_with_absence(
        self, permission_service, teacher_user, submitted_absence
    ):
        """Teachers cannot approve absences even with absence provided (SECURITY!)"""
        assert not permission_service.can_approve_absence(
            teacher_user, submitted_absence
        )

    def test_dept_head_can_approve(self, permission_service, dept_head_user):
        """Department heads can approve absences"""
        assert permission_service.can_approve_absence(dept_head_user)

    def test_planner_can_approve(self, permission_service, planner_user):
        """Planners can approve absences"""
        assert permission_service.can_approve_absence(planner_user)

    def test_admin_can_approve(self, permission_service, admin_user):
        """Admins can approve absences"""
        assert permission_service.can_approve_absence(admin_user)

    def test_dept_head_can_approve_submitted_absence(
        self, permission_service, dept_head_user, submitted_absence
    ):
        """Department heads can approve submitted absences"""
        assert permission_service.can_approve_absence(dept_head_user, submitted_absence)

    def test_dept_head_cannot_approve_approved_absence(
        self, permission_service, dept_head_user, approved_absence
    ):
        """Department heads cannot approve already-approved absences"""
        assert not permission_service.can_approve_absence(
            dept_head_user, approved_absence
        )

    def test_dept_head_cannot_approve_completed_absence(
        self, permission_service, dept_head_user, completed_absence
    ):
        """Department heads cannot approve completed absences"""
        assert not permission_service.can_approve_absence(
            dept_head_user, completed_absence
        )

    def test_admin_can_approve_any_status(
        self,
        permission_service,
        admin_user,
        submitted_absence,
        approved_absence,
        completed_absence,
    ):
        """Admins can approve absences regardless of status"""
        assert permission_service.can_approve_absence(admin_user, submitted_absence)
        assert permission_service.can_approve_absence(admin_user, approved_absence)
        assert permission_service.can_approve_absence(admin_user, completed_absence)

    def test_planner_can_approve_any_status(
        self,
        permission_service,
        planner_user,
        submitted_absence,
        approved_absence,
        completed_absence,
    ):
        """Planners can approve absences regardless of status"""
        assert permission_service.can_approve_absence(planner_user, submitted_absence)
        assert permission_service.can_approve_absence(planner_user, approved_absence)
        assert permission_service.can_approve_absence(planner_user, completed_absence)


# ============================================================================
# Test can_complete_absence()
# ============================================================================


class TestCanCompleteAbsence:
    """Test completion permissions"""

    def test_teacher_cannot_complete(self, permission_service, teacher_user):
        """Teachers cannot complete absences (SECURITY!)"""
        assert not permission_service.can_complete_absence(teacher_user)

    def test_teacher_cannot_complete_with_setting_enabled(
        self, permission_service, teacher_user
    ):
        """Teachers cannot complete absences even with setting enabled (SECURITY!)"""
        assert not permission_service.can_complete_absence(
            teacher_user, dept_heads_can_complete=True
        )

    def test_dept_head_cannot_complete_by_default(
        self, permission_service, dept_head_user
    ):
        """Department heads cannot complete by default"""
        assert not permission_service.can_complete_absence(dept_head_user)

    def test_dept_head_can_complete_with_setting_enabled(
        self, permission_service, dept_head_user
    ):
        """Department heads can complete when setting is enabled"""
        assert permission_service.can_complete_absence(
            dept_head_user, dept_heads_can_complete=True
        )

    def test_planner_can_complete_by_default(self, permission_service, planner_user):
        """Planners can complete absences by default"""
        assert permission_service.can_complete_absence(planner_user)

    def test_planner_can_complete_with_setting_disabled(
        self, permission_service, planner_user
    ):
        """Planners can complete even when dept_heads setting is disabled"""
        assert permission_service.can_complete_absence(
            planner_user, dept_heads_can_complete=False
        )

    def test_admin_can_complete_by_default(self, permission_service, admin_user):
        """Admins can complete absences by default"""
        assert permission_service.can_complete_absence(admin_user)

    def test_admin_can_complete_with_setting_disabled(
        self, permission_service, admin_user
    ):
        """Admins can complete even when dept_heads setting is disabled"""
        assert permission_service.can_complete_absence(
            admin_user, dept_heads_can_complete=False
        )


# ============================================================================
# Test can_delete_absence()
# ============================================================================


class TestCanDeleteAbsence:
    """Test deletion permissions"""

    def test_teacher_can_delete_own_draft_absence(
        self, permission_service, teacher_user, draft_absence
    ):
        """Teachers can delete their own draft absences"""
        assert permission_service.can_delete_absence(teacher_user, draft_absence)

    def test_teacher_can_delete_own_submitted_absence(
        self, permission_service, teacher_user, submitted_absence
    ):
        """Teachers can delete their own submitted absences"""
        assert permission_service.can_delete_absence(teacher_user, submitted_absence)

    def test_teacher_cannot_delete_own_approved_absence(
        self, permission_service, teacher_user, approved_absence
    ):
        """Teachers cannot delete their own approved absences (SECURITY!)"""
        assert not permission_service.can_delete_absence(teacher_user, approved_absence)

    def test_teacher_cannot_delete_own_completed_absence(
        self, permission_service, teacher_user, completed_absence
    ):
        """Teachers cannot delete their own completed absences (SECURITY!)"""
        assert not permission_service.can_delete_absence(
            teacher_user, completed_absence
        )

    def test_teacher_cannot_delete_other_absence(
        self, permission_service, teacher_user, other_teacher_absence
    ):
        """Teachers cannot delete other teachers' absences (SECURITY!)"""
        assert not permission_service.can_delete_absence(
            teacher_user, other_teacher_absence
        )

    def test_dept_head_cannot_delete_other_absence(
        self, permission_service, dept_head_user, other_teacher_absence
    ):
        """Department heads cannot delete absences (not their job)"""
        assert not permission_service.can_delete_absence(
            dept_head_user, other_teacher_absence
        )

    def test_admin_can_delete_any_absence(
        self,
        permission_service,
        admin_user,
        draft_absence,
        submitted_absence,
        approved_absence,
        completed_absence,
        other_teacher_absence,
    ):
        """Admins can delete any absence regardless of status or owner"""
        assert permission_service.can_delete_absence(admin_user, draft_absence)
        assert permission_service.can_delete_absence(admin_user, submitted_absence)
        assert permission_service.can_delete_absence(admin_user, approved_absence)
        assert permission_service.can_delete_absence(admin_user, completed_absence)
        assert permission_service.can_delete_absence(admin_user, other_teacher_absence)

    def test_planner_can_delete_any_absence(
        self,
        permission_service,
        planner_user,
        draft_absence,
        submitted_absence,
        approved_absence,
        completed_absence,
        other_teacher_absence,
    ):
        """Planners can delete any absence regardless of status or owner"""
        assert permission_service.can_delete_absence(planner_user, draft_absence)
        assert permission_service.can_delete_absence(planner_user, submitted_absence)
        assert permission_service.can_delete_absence(planner_user, approved_absence)
        assert permission_service.can_delete_absence(planner_user, completed_absence)
        assert permission_service.can_delete_absence(planner_user, other_teacher_absence)


# ============================================================================
# Integration Tests - Real-world scenarios
# ============================================================================


class TestRealWorldScenarios:
    """Test realistic authorization scenarios"""

    def test_teacher_workflow_permissions(
        self,
        permission_service,
        teacher_user,
        draft_absence,
        submitted_absence,
        approved_absence,
        completed_absence,
    ):
        """Test typical teacher workflow permissions"""
        # Can view all own absences
        assert permission_service.can_view_absence(teacher_user, draft_absence)
        assert permission_service.can_view_absence(teacher_user, submitted_absence)
        assert permission_service.can_view_absence(teacher_user, approved_absence)
        assert permission_service.can_view_absence(teacher_user, completed_absence)

        # Can edit draft, submitted, approved
        assert permission_service.can_edit_absence(teacher_user, draft_absence)
        assert permission_service.can_edit_absence(teacher_user, submitted_absence)
        assert permission_service.can_edit_absence(teacher_user, approved_absence)

        # Cannot edit completed
        assert not permission_service.can_edit_absence(teacher_user, completed_absence)

        # Can delete only draft and submitted
        assert permission_service.can_delete_absence(teacher_user, draft_absence)
        assert permission_service.can_delete_absence(teacher_user, submitted_absence)
        assert not permission_service.can_delete_absence(teacher_user, approved_absence)
        assert not permission_service.can_delete_absence(
            teacher_user, completed_absence
        )

        # Cannot approve or complete
        assert not permission_service.can_approve_absence(teacher_user)
        assert not permission_service.can_complete_absence(teacher_user)

    def test_dept_head_workflow_permissions(
        self,
        permission_service,
        dept_head_user,
        submitted_absence,
        approved_absence,
        completed_absence,
    ):
        """Test typical department head workflow permissions"""
        # Can view all absences
        assert permission_service.can_view_absence(dept_head_user, submitted_absence)
        assert permission_service.can_view_absence(dept_head_user, approved_absence)
        assert permission_service.can_view_absence(dept_head_user, completed_absence)

        # Cannot edit any absences (not their job)
        assert not permission_service.can_edit_absence(dept_head_user, submitted_absence)
        assert not permission_service.can_edit_absence(dept_head_user, approved_absence)
        assert not permission_service.can_edit_absence(dept_head_user, completed_absence)

        # Can approve only submitted
        assert permission_service.can_approve_absence(dept_head_user, submitted_absence)
        assert not permission_service.can_approve_absence(
            dept_head_user, approved_absence
        )
        assert not permission_service.can_approve_absence(
            dept_head_user, completed_absence
        )

        # Cannot complete by default
        assert not permission_service.can_complete_absence(dept_head_user)

        # Cannot delete
        assert not permission_service.can_delete_absence(
            dept_head_user, submitted_absence
        )

    def test_planner_workflow_permissions(
        self,
        permission_service,
        planner_user,
        draft_absence,
        submitted_absence,
        approved_absence,
        completed_absence,
    ):
        """Test typical planner workflow permissions (full power)"""
        # Can view all
        assert permission_service.can_view_absence(planner_user, draft_absence)
        assert permission_service.can_view_absence(planner_user, submitted_absence)
        assert permission_service.can_view_absence(planner_user, approved_absence)
        assert permission_service.can_view_absence(planner_user, completed_absence)

        # Can edit all (including completed)
        assert permission_service.can_edit_absence(planner_user, draft_absence)
        assert permission_service.can_edit_absence(planner_user, submitted_absence)
        assert permission_service.can_edit_absence(planner_user, approved_absence)
        assert permission_service.can_edit_absence(planner_user, completed_absence)

        # Can approve all
        assert permission_service.can_approve_absence(planner_user, submitted_absence)
        assert permission_service.can_approve_absence(planner_user, approved_absence)
        assert permission_service.can_approve_absence(planner_user, completed_absence)

        # Can complete all
        assert permission_service.can_complete_absence(planner_user)

        # Can delete all
        assert permission_service.can_delete_absence(planner_user, draft_absence)
        assert permission_service.can_delete_absence(planner_user, submitted_absence)
        assert permission_service.can_delete_absence(planner_user, approved_absence)
        assert permission_service.can_delete_absence(planner_user, completed_absence)

    def test_security_isolation_between_teachers(
        self, permission_service, teacher_user, other_teacher_user, other_teacher_absence
    ):
        """Test that teachers are properly isolated from each other (SECURITY!)"""
        # Teacher cannot view other teacher's absence
        assert not permission_service.can_view_absence(
            teacher_user, other_teacher_absence
        )

        # Teacher cannot edit other teacher's absence
        assert not permission_service.can_edit_absence(
            teacher_user, other_teacher_absence
        )

        # Teacher cannot delete other teacher's absence
        assert not permission_service.can_delete_absence(
            teacher_user, other_teacher_absence
        )

        # But other_teacher can do all of the above
        assert permission_service.can_view_absence(
            other_teacher_user, other_teacher_absence
        )
        assert permission_service.can_edit_absence(
            other_teacher_user, other_teacher_absence
        )
        assert permission_service.can_delete_absence(
            other_teacher_user, other_teacher_absence
        )
