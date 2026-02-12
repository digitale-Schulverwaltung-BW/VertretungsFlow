"""
E-Mail HTML Templates
Pure Functions für die Generierung von HTML-E-Mail-Inhalten
"""

# Gemeinsame Inline-Styles (viele Mail-Clients ignorieren <style>-Tags)
_BODY_STYLE = "font-family: Arial, sans-serif; background: #f3f4f6; margin: 0; padding: 20px;"
_CARD_STYLE = (
    "max-width: 600px; margin: 0 auto; background: #ffffff; "
    "border-radius: 8px; padding: 32px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);"
)
_FOOTER_STYLE = (
    "max-width: 600px; margin: 16px auto 0; text-align: center; "
    "font-size: 12px; color: #9ca3af;"
)
_TABLE_STYLE = (
    "width: 100%; border-collapse: collapse; margin: 16px 0; "
    "font-size: 14px; color: #374151;"
)
_TD_LABEL_STYLE = (
    "padding: 8px 12px 8px 0; color: #6b7280; white-space: nowrap; "
    "vertical-align: top; width: 120px;"
)
_TD_VALUE_STYLE = "padding: 8px 0; font-weight: 500;"
_DIVIDER_STYLE = "border: none; border-top: 1px solid #e5e7eb; margin: 20px 0;"

_BTN_GREEN = (
    "display: inline-block; margin-top: 20px; padding: 12px 28px; "
    "background: #16a34a; color: #ffffff; text-decoration: none; "
    "border-radius: 6px; font-weight: bold; font-size: 15px;"
)
_BTN_BLUE = (
    "display: inline-block; margin-top: 20px; padding: 12px 28px; "
    "background: #2563eb; color: #ffffff; text-decoration: none; "
    "border-radius: 6px; font-weight: bold; font-size: 15px;"
)

_HEADER_GREEN = "color: #15803d; font-size: 20px; margin: 0 0 4px 0;"
_HEADER_BLUE = "color: #1d4ed8; font-size: 20px; margin: 0 0 4px 0;"
_HEADER_RED = "color: #dc2626; font-size: 20px; margin: 0 0 4px 0;"
_HEADER_GRAY = "color: #374151; font-size: 20px; margin: 0 0 4px 0;"
_SUBTITLE_STYLE = "color: #6b7280; font-size: 13px; margin: 0 0 20px 0;"


def _detail_row(label: str, value: str) -> str:
    return (
        f'<tr>'
        f'<td style="{_TD_LABEL_STYLE}">{label}</td>'
        f'<td style="{_TD_VALUE_STYLE}">{value}</td>'
        f"</tr>"
    )


def _wrap(header_html: str, content_html: str) -> str:
    return (
        f'<html><body style="{_BODY_STYLE}">'
        f'<div style="{_CARD_STYLE}">'
        f"{header_html}"
        f'<hr style="{_DIVIDER_STYLE}">'
        f"{content_html}"
        f"</div>"
        f'<div style="{_FOOTER_STYLE}">AbsenzFlow System &ndash; Diese Nachricht wurde automatisch generiert.</div>'
        f"</body></html>"
    )


def submitted_html(
    teacher_name: str,
    reason: str,
    start_date: str,
    end_date: str,
    absence_url: str,
) -> str:
    """
    HTML-Template: Neue Abwesenheitsmeldung (an Abteilungsleitung + Planer)

    Args:
        teacher_name: Name der Lehrkraft
        reason: Abwesenheitsgrund (bereits übersetzt)
        start_date: Startdatum (DD.MM.YYYY)
        end_date: Enddatum (DD.MM.YYYY)
        absence_url: Direktlink zur Abwesenheit

    Returns:
        HTML-String
    """
    header = (
        f'<h2 style="{_HEADER_GREEN}">Neue Abwesenheitsmeldung</h2>'
        f'<p style="{_SUBTITLE_STYLE}">Eine neue Abwesenheit wurde zur Genehmigung eingereicht.</p>'
    )
    content = (
        f'<table style="{_TABLE_STYLE}">'
        + _detail_row("Lehrkraft", teacher_name)
        + _detail_row("Grund", reason)
        + _detail_row("Von", start_date)
        + _detail_row("Bis", end_date)
        + "</table>"
        + f'<a href="{absence_url}" style="{_BTN_GREEN}">Abwesenheit genehmigen</a>'
    )
    return _wrap(header, content)


def approved_teacher_html(absence_id: int, approver_name: str) -> str:
    """
    HTML-Template: Genehmigungsbestätigung (an Lehrkraft)

    Args:
        absence_id: ID der Abwesenheit
        approver_name: Name der genehmigenden Person

    Returns:
        HTML-String
    """
    header = (
        f'<h2 style="{_HEADER_BLUE}">Abwesenheit genehmigt</h2>'
        f'<p style="{_SUBTITLE_STYLE}">Ihre Abwesenheitsmeldung wurde genehmigt.</p>'
    )
    content = (
        f'<table style="{_TABLE_STYLE}">'
        + _detail_row("Abwesenheits-ID", f"#{absence_id}")
        + _detail_row("Genehmigt von", approver_name)
        + "</table>"
        + f'<p style="color: #374151; font-size: 14px; margin-top: 16px;">'
        f"Ihre Abwesenheit wurde von {approver_name} genehmigt und an die "
        f"Vertretungsplanung weitergeleitet.</p>"
    )
    return _wrap(header, content)


def approved_planner_html(
    absence_id: int,
    approver_name: str,
    absence_url: str,
) -> str:
    """
    HTML-Template: Genehmigung weitergeleitet (an Planer)

    Args:
        absence_id: ID der Abwesenheit
        approver_name: Name der genehmigenden Person
        absence_url: Direktlink zur Abwesenheit

    Returns:
        HTML-String
    """
    header = (
        f'<h2 style="{_HEADER_GREEN}">Abwesenheit zur Vertretungsplanung</h2>'
        f'<p style="{_SUBTITLE_STYLE}">'
        f"Abwesenheit #{absence_id} wurde genehmigt und wartet auf Eintragung.</p>"
    )
    content = (
        f'<table style="{_TABLE_STYLE}">'
        + _detail_row("Abwesenheits-ID", f"#{absence_id}")
        + _detail_row("Genehmigt von", approver_name)
        + "</table>"
        + f'<a href="{absence_url}" style="{_BTN_GREEN}">Erledigt melden</a>'
    )
    return _wrap(header, content)


def completed_html(absence_id: int, absence_url: str) -> str:
    """
    HTML-Template: Abwesenheit eingetragen (an Lehrkraft)

    Args:
        absence_id: ID der Abwesenheit
        absence_url: Direktlink zur Abwesenheit

    Returns:
        HTML-String
    """
    header = (
        f'<h2 style="{_HEADER_BLUE}">Abwesenheit eingetragen</h2>'
        f'<p style="{_SUBTITLE_STYLE}">'
        f"Ihre Abwesenheit wurde in den Vertretungsplan eingetragen.</p>"
    )
    content = (
        f'<table style="{_TABLE_STYLE}">'
        + _detail_row("Abwesenheits-ID", f"#{absence_id}")
        + _detail_row("Status", "Erledigt")
        + "</table>"
        + f'<a href="{absence_url}" style="{_BTN_BLUE}">Details ansehen</a>'
    )
    return _wrap(header, content)


def rejected_html(absence_id: int, rejector_name: str) -> str:
    """
    HTML-Template: Abwesenheit abgelehnt (an Lehrkraft)

    Args:
        absence_id: ID der Abwesenheit
        rejector_name: Name der ablehnenden Person

    Returns:
        HTML-String
    """
    header = (
        f'<h2 style="{_HEADER_RED}">Abwesenheit abgelehnt</h2>'
        f'<p style="{_SUBTITLE_STYLE}">'
        f"Ihre Abwesenheitsmeldung wurde leider abgelehnt.</p>"
    )
    content = (
        f'<table style="{_TABLE_STYLE}">'
        + _detail_row("Abwesenheits-ID", f"#{absence_id}")
        + _detail_row("Abgelehnt von", rejector_name)
        + "</table>"
        + f'<p style="color: #374151; font-size: 14px; margin-top: 16px;">'
        f"Bitte wenden Sie sich bei Rückfragen direkt an {rejector_name}.</p>"
    )
    return _wrap(header, content)


def deleted_html(
    teacher_name: str,
    reason: str,
    start_date: str,
    end_date: str,
    absence_id: int,
) -> str:
    """
    HTML-Template: Abwesenheit zurückgezogen (an Abteilungsleitung + Planer)

    Args:
        teacher_name: Name der Lehrkraft
        reason: Abwesenheitsgrund (bereits übersetzt)
        start_date: Startdatum (DD.MM.YYYY)
        end_date: Enddatum (DD.MM.YYYY)
        absence_id: ID der gelöschten Abwesenheit

    Returns:
        HTML-String
    """
    header = (
        f'<h2 style="{_HEADER_GRAY}">Abwesenheitsmeldung zurückgezogen</h2>'
        f'<p style="{_SUBTITLE_STYLE}">'
        f"{teacher_name} hat eine Abwesenheitsmeldung zurückgezogen.</p>"
    )
    content = (
        f'<table style="{_TABLE_STYLE}">'
        + _detail_row("Lehrkraft", teacher_name)
        + _detail_row("Abwesenheits-ID", f"#{absence_id}")
        + _detail_row("Grund", reason)
        + _detail_row("Von", start_date)
        + _detail_row("Bis", end_date)
        + "</table>"
        + f'<p style="color: #6b7280; font-size: 13px; margin-top: 16px;">'
        f"Die Meldung wurde aus dem AbsenzFlow-System entfernt.</p>"
    )
    return _wrap(header, content)
