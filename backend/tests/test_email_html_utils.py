"""
Unit Tests für email_html_utils

Getestet:
- submitted_html()        - Neue Abwesenheit: grüner "Genehmigen"-Button, alle Felder
- approved_teacher_html() - Genehmigung an Lehrkraft: kein Button, nur Info
- approved_planner_html() - Genehmigung an Planer: grüner "Erledigt melden"-Button
- completed_html()        - Eingetragen an Lehrkraft: blauer "Details ansehen"-Button
- rejected_html()         - Abgelehnt an Lehrkraft: kein Button, roter Akzent
- deleted_html()          - Gelöscht an AL/Planer: kein Button, alle Felder
"""

import pytest

from app.utils.email_html_utils import (
    approved_planner_html,
    approved_teacher_html,
    completed_html,
    deleted_html,
    rejected_html,
    submitted_html,
)


# ============================================================================
# Helpers
# ============================================================================


def assert_valid_html(html: str) -> None:
    """Minimal sanity check: string is non-empty and wraps with html/body tags"""
    assert html
    assert "<html>" in html
    assert "</html>" in html
    assert "<body" in html
    assert "</body>" in html


# ============================================================================
# Test submitted_html()
# ============================================================================


class TestSubmittedHtml:
    """HTML template: new absence submitted (for dept heads & planners)"""

    def test_returns_valid_html(self):
        html = submitted_html(
            "Max Muster",
            "Krankheit",
            "10.02.2026",
            "12.02.2026",
            "http://example.com/absence/42",
        )
        assert_valid_html(html)

    def test_contains_teacher_name(self):
        html = submitted_html(
            "Anna Bauer",
            "Fortbildung",
            "01.03.2026",
            "01.03.2026",
            "http://example.com/absence/1",
        )
        assert "Anna Bauer" in html

    def test_contains_reason(self):
        html = submitted_html(
            "Max Muster",
            "Exkursion",
            "10.02.2026",
            "12.02.2026",
            "http://example.com/absence/42",
        )
        assert "Exkursion" in html

    def test_contains_dates(self):
        html = submitted_html(
            "Max Muster",
            "Krankheit",
            "10.02.2026",
            "12.02.2026",
            "http://example.com/absence/42",
        )
        assert "10.02.2026" in html
        assert "12.02.2026" in html

    def test_contains_absence_url(self):
        url = "http://schule.de/#/absence/99"
        html = submitted_html(
            "Max Muster", "Krankheit", "10.02.2026", "10.02.2026", url
        )
        assert url in html

    def test_has_green_approve_button(self):
        """Abteilungsleitung soll grünen Genehmigen-Button sehen"""
        html = submitted_html(
            "Max Muster",
            "Krankheit",
            "10.02.2026",
            "12.02.2026",
            "http://example.com/absence/42",
        )
        assert "Abwesenheit genehmigen" in html
        assert "#16a34a" in html  # green

    def test_button_href_matches_url(self):
        url = "http://schule.de/#/absence/5"
        html = submitted_html(
            "Max Muster", "Krankheit", "10.02.2026", "10.02.2026", url
        )
        assert f'href="{url}"' in html


# ============================================================================
# Test approved_teacher_html()
# ============================================================================


class TestApprovedTeacherHtml:
    """HTML template: absence approved, sent to teacher (info only, no action button)"""

    def test_returns_valid_html(self):
        html = approved_teacher_html(42, "Dr. Chef")
        assert_valid_html(html)

    def test_contains_absence_id(self):
        html = approved_teacher_html(42, "Dr. Chef")
        assert "42" in html

    def test_contains_approver_name(self):
        html = approved_teacher_html(42, "Dr. Abteilungsleiter")
        assert "Dr. Abteilungsleiter" in html

    def test_no_action_button(self):
        """Lehrkraft bekommt nur eine Info-Mail, keinen grünen Action-Button"""
        html = approved_teacher_html(42, "Dr. Chef")
        assert "Abwesenheit genehmigen" not in html
        assert "Erledigt melden" not in html


# ============================================================================
# Test approved_planner_html()
# ============================================================================


class TestApprovedPlannerHtml:
    """HTML template: absence approved, sent to planner (with action button)"""

    def test_returns_valid_html(self):
        html = approved_planner_html(42, "Dr. Chef", "http://example.com/absence/42")
        assert_valid_html(html)

    def test_contains_absence_id(self):
        html = approved_planner_html(42, "Dr. Chef", "http://example.com/absence/42")
        assert "42" in html

    def test_contains_approver_name(self):
        html = approved_planner_html(
            42, "Dr. Approver", "http://example.com/absence/42"
        )
        assert "Dr. Approver" in html

    def test_contains_absence_url(self):
        url = "http://schule.de/#/absence/42"
        html = approved_planner_html(42, "Chef", url)
        assert url in html

    def test_has_green_complete_button(self):
        """Planer soll grünen 'Erledigt melden'-Button sehen"""
        html = approved_planner_html(42, "Chef", "http://example.com/absence/42")
        assert "Erledigt melden" in html
        assert "#16a34a" in html  # green

    def test_button_href_matches_url(self):
        url = "http://schule.de/#/absence/7"
        html = approved_planner_html(7, "Chef", url)
        assert f'href="{url}"' in html


# ============================================================================
# Test completed_html()
# ============================================================================


class TestCompletedHtml:
    """HTML template: absence completed, sent to teacher (blue details button)"""

    def test_returns_valid_html(self):
        html = completed_html(42, "http://example.com/absence/42")
        assert_valid_html(html)

    def test_contains_absence_id(self):
        html = completed_html(42, "http://example.com/absence/42")
        assert "42" in html

    def test_contains_absence_url(self):
        url = "http://schule.de/#/absence/42"
        html = completed_html(42, url)
        assert url in html

    def test_has_blue_details_button(self):
        """Lehrkraft soll blauen 'Details ansehen'-Button bekommen"""
        html = completed_html(42, "http://example.com/absence/42")
        assert "Details ansehen" in html
        assert "#2563eb" in html  # blue

    def test_no_green_action_button(self):
        """Kein grüner Action-Button für Lehrkraft in Completed-Mail"""
        html = completed_html(42, "http://example.com/absence/42")
        assert "Erledigt melden" not in html
        assert "Abwesenheit genehmigen" not in html


# ============================================================================
# Test rejected_html()
# ============================================================================


class TestRejectedHtml:
    """HTML template: absence rejected, sent to teacher (red accent, no button)"""

    def test_returns_valid_html(self):
        html = rejected_html(42, "Dr. Ablehnungsleiter")
        assert_valid_html(html)

    def test_contains_absence_id(self):
        html = rejected_html(42, "Chef")
        assert "42" in html

    def test_contains_rejector_name(self):
        html = rejected_html(42, "Dr. Ablehnungsleiter")
        assert "Dr. Ablehnungsleiter" in html

    def test_has_red_accent(self):
        """Ablehnungs-Mail soll roten Farbakzent im Header haben"""
        html = rejected_html(42, "Chef")
        assert "#dc2626" in html  # red

    def test_no_action_button(self):
        """Keine Action-Buttons in Ablehnungs-Mail"""
        html = rejected_html(42, "Chef")
        assert "Abwesenheit genehmigen" not in html
        assert "Erledigt melden" not in html
        assert "Details ansehen" not in html


# ============================================================================
# Test deleted_html()
# ============================================================================


class TestDeletedHtml:
    """HTML template: absence deleted by teacher (info for dept heads & planners)"""

    def test_returns_valid_html(self):
        html = deleted_html("Max Muster", "Krankheit", "10.02.2026", "12.02.2026", 42)
        assert_valid_html(html)

    def test_contains_teacher_name(self):
        html = deleted_html("Anna Bauer", "Fortbildung", "01.03.2026", "01.03.2026", 5)
        assert "Anna Bauer" in html

    def test_contains_reason(self):
        html = deleted_html("Max Muster", "Exkursion", "10.02.2026", "12.02.2026", 42)
        assert "Exkursion" in html

    def test_contains_dates(self):
        html = deleted_html("Max Muster", "Krankheit", "10.02.2026", "12.02.2026", 42)
        assert "10.02.2026" in html
        assert "12.02.2026" in html

    def test_contains_absence_id(self):
        html = deleted_html("Max Muster", "Krankheit", "10.02.2026", "12.02.2026", 99)
        assert "99" in html

    def test_no_action_button(self):
        """Info-Mail: keine Action-Buttons"""
        html = deleted_html("Max Muster", "Krankheit", "10.02.2026", "12.02.2026", 42)
        assert "Abwesenheit genehmigen" not in html
        assert "Erledigt melden" not in html
