"""
E-Mail Service
Versand von Benachrichtigungen per E-Mail
"""

import logging
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from app.core.config import settings
from app.utils.email_html_utils import (
    submitted_html,
    approved_teacher_html,
    approved_planner_html,
    completed_html,
    rejected_html,
    deleted_html,
    deleted_teacher_html,
)

logger = logging.getLogger(__name__)


class EmailService:
    """Service für E-Mail-Versand"""

    def __init__(self):
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.username = settings.SMTP_USERNAME
        self.password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM
        self.use_tls = settings.SMTP_USE_TLS

    async def send_email(
        self,
        to: str,
        subject: str,
        body_plain: str,
        body_html: Optional[str] = None,
    ) -> bool:
        """
        Sendet eine E-Mail als multipart/alternative (Plaintext + optional HTML)

        Args:
            to: Empfänger E-Mail-Adresse
            subject: Betreff
            body_plain: Plaintext-Fallback (für Mail-Clients ohne HTML-Support)
            body_html: Optionaler HTML-Teil (wird bevorzugt angezeigt wenn vorhanden)

        Returns:
            True wenn erfolgreich, sonst False
        """
        try:
            message = MIMEMultipart("alternative")
            message["From"] = self.from_email
            message["To"] = to
            message["Subject"] = subject

            # Plaintext zuerst anhängen (Fallback), HTML als letzter Part (bevorzugt, RFC 2046)
            message.attach(MIMEText(body_plain, "plain"))
            if body_html:
                message.attach(MIMEText(body_html, "html"))

            # E-Mail versenden mit port-basierter TLS-Auswahl
            smtp_kwargs = {
                "hostname": self.host,
                "port": self.port,
                "username": self.username if self.username else None,
                "password": self.password if self.password else None,
            }

            # TLS-Methode basierend auf Port wählen
            if self.port == 465:
                # Port 465: Implizites TLS (SMTPS, legacy aber noch verwendet)
                smtp_kwargs["use_tls"] = True
            elif self.port == 587:
                # Port 587: STARTTLS (Standard für Submission)
                smtp_kwargs["start_tls"] = True
            elif self.use_tls:
                # Fallback: Verwende STARTTLS für andere Ports wenn aktiviert
                smtp_kwargs["start_tls"] = True
            # Port 25 oder andere ohne TLS: keine zusätzlichen Parameter

            await aiosmtplib.send(message, **smtp_kwargs)
            logger.info(f"✓ Email sent successfully to {to}: {subject}")

            return True

        except aiosmtplib.SMTPAuthenticationError as e:
            logger.error(
                f"SMTP authentication failed: Invalid credentials for {self.host}:{self.port}"
            )
            logger.debug(f"Auth error details: {e}", exc_info=True)
            return False
        except aiosmtplib.SMTPConnectError as e:
            logger.error(
                f"SMTP connection failed: Cannot reach server {self.host}:{self.port}"
            )
            logger.debug(f"Connection error details: {e}", exc_info=True)
            return False
        except aiosmtplib.SMTPException as e:
            logger.error(f"SMTP error sending email to {to}: {type(e).__name__}")
            logger.debug(f"SMTP error details: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending email to {to}: {type(e).__name__}")
            logger.debug(f"Unexpected error details: {e}", exc_info=True)
            return False

    async def send_absence_submitted_notification(
        self,
        teacher_name: str,
        teacher_email: str,
        dept_head_emails: List[str],
        planner_emails: List[str],
        absence_id: int,
        reason: str,
        start_date: str,
        end_date: str,
    ) -> bool:
        """
        Benachrichtigung bei neuer Abwesenheitsmeldung

        Args:
            teacher_name: Name der Lehrkraft
            teacher_email: E-Mail der Lehrkraft
            dept_head_emails: E-Mails der Abteilungsleiter
            planner_emails: E-Mails der Vertretungsplaner
            absence_id: ID der Abwesenheit
            reason: Grund
            start_date: Startdatum
            end_date: Enddatum

        Returns:
            True wenn erfolgreich
        """
        subject = f"Neue Abwesenheitsmeldung von {teacher_name}"
        body = f"""
Hallo,

{teacher_name} hat eine neue Abwesenheit gemeldet:

Grund: {reason}
Von: {start_date}
Bis: {end_date}

Bitte prüfen und genehmigen Sie die Abwesenheit im VertretungsFlow-System.

Link: {settings.FRONTEND_URL}/#/absence/{absence_id}

Mit freundlichen Grüßen,
VertretungsFlow System
        """

        html_body = submitted_html(
            teacher_name,
            reason,
            start_date,
            end_date,
            f"{settings.FRONTEND_URL}/#/absence/{absence_id}",
        )

        # An Abteilungsleiter und Vertretungsplaner
        recipients = dept_head_emails + planner_emails

        success = True
        for email in recipients:
            result = await self.send_email(email, subject, body, html_body)
            if not result:
                success = False

        return success

    async def send_absence_approved_notification(
        self,
        teacher_email: str,
        planner_emails: List[str],
        absence_id: int,
        approver_name: str,
    ) -> bool:
        """
        Benachrichtigung bei Genehmigung einer Abwesenheit

        Args:
            teacher_email: E-Mail der Lehrkraft
            planner_emails: E-Mails der Vertretungsplaner
            absence_id: ID der Abwesenheit
            approver_name: Name des Genehmigers

        Returns:
            True wenn erfolgreich
        """
        absence_url = f"{settings.FRONTEND_URL}/#/absence/{absence_id}"

        # An Lehrkraft
        teacher_subject = "Ihre Abwesenheit wurde genehmigt"
        teacher_body = f"""
Hallo,

Ihre Abwesenheitsmeldung (ID: {absence_id}) wurde von {approver_name} genehmigt.

Mit freundlichen Grüßen,
VertretungsFlow System
        """

        await self.send_email(
            teacher_email,
            teacher_subject,
            teacher_body,
            approved_teacher_html(absence_id, approver_name),
        )

        # An Vertretungsplaner
        planner_subject = f"Abwesenheit #{absence_id} genehmigt"
        planner_body = f"""
Hallo,

Die Abwesenheit #{absence_id} wurde von {approver_name} genehmigt und ist nun bereit zur Vertretungsplanung.

Link: {absence_url}

Mit freundlichen Grüßen,
VertretungsFlow System
        """

        for email in planner_emails:
            await self.send_email(
                email,
                planner_subject,
                planner_body,
                approved_planner_html(absence_id, approver_name, absence_url),
            )

        return True

    async def send_absence_completed_notification(
        self, teacher_email: str, absence_id: int
    ) -> bool:
        """
        Benachrichtigung wenn Abwesenheit als erledigt markiert wurde

        Args:
            teacher_email: E-Mail der Lehrkraft
            absence_id: ID der Abwesenheit

        Returns:
            True wenn erfolgreich
        """
        absence_url = f"{settings.FRONTEND_URL}/#/absence/{absence_id}"
        subject = "Ihre Abwesenheit wurde eingetragen"
        body = f"""
Hallo,

Ihre Abwesenheitsmeldung (ID: {absence_id}) wurde in den Vertretungsplan eingetragen.

Link: {absence_url}

Mit freundlichen Grüßen,
VertretungsFlow System
        """

        return await self.send_email(
            teacher_email, subject, body, completed_html(absence_id, absence_url)
        )

    async def send_absence_rejected_notification(
        self, teacher_email: str, absence_id: int, rejector_name: str
    ) -> bool:
        """
        Benachrichtigung wenn Abwesenheit abgelehnt wird

        Args:
            teacher_email: E-Mail der Lehrkraft
            absence_id: ID der Abwesenheit
            rejector_name: Name des Ablehnenden

        Returns:
            True wenn erfolgreich
        """
        subject = "Ihre Abwesenheit wurde abgelehnt"
        body = f"""
Hallo,

Ihre Abwesenheitsmeldung (ID: {absence_id}) wurde von {rejector_name} abgelehnt.

Mit freundlichen Grüßen,
VertretungsFlow System
        """

        return await self.send_email(
            teacher_email, subject, body, rejected_html(absence_id, rejector_name)
        )

    async def send_absence_deleted_notification(
        self,
        teacher_name: str,
        deleted_by_name: str,
        admin_emails: List[str],
        absence_id: int,
        reason: str,
        start_date: str,
        end_date: str,
        teacher_email: Optional[str] = None,
    ) -> bool:
        """
        Benachrichtigung wenn eine Abwesenheit gelöscht wurde

        Args:
            teacher_name: Name der betroffenen Lehrkraft
            deleted_by_name: Name der Person, die gelöscht hat
            admin_emails: E-Mails der Admins (immer benachrichtigt)
            absence_id: ID der gelöschten Abwesenheit
            reason: Grund
            start_date: Startdatum
            end_date: Enddatum
            teacher_email: E-Mail der Lehrkraft (nur wenn Absenz in Zukunft & nicht genehmigt)

        Returns:
            True wenn erfolgreich
        """
        success = True

        # Admin-Benachrichtigung (immer)
        admin_subject = f"Abwesenheitsmeldung von {teacher_name} wurde gelöscht"
        admin_body = f"""Hallo,

{deleted_by_name} hat die Abwesenheitsmeldung von {teacher_name} gelöscht:

Abwesenheits-ID: {absence_id}
Grund: {reason}
Von: {start_date}
Bis: {end_date}

Die Meldung wurde aus dem VertretungsFlow-System entfernt.

Mit freundlichen Grüßen,
VertretungsFlow System"""

        admin_html = deleted_html(
            teacher_name, reason, start_date, end_date, absence_id, deleted_by_name
        )
        for email in admin_emails:
            result = await self.send_email(email, admin_subject, admin_body, admin_html)
            if not result:
                success = False

        # Lehrkraft-Benachrichtigung (nur wenn Bedingung erfüllt)
        if teacher_email:
            teacher_subject = "Ihre Abwesenheitsmeldung wurde gelöscht"
            teacher_body = f"""Hallo {teacher_name},

Ihre Abwesenheitsmeldung wurde von {deleted_by_name} aus dem System entfernt:

Abwesenheits-ID: {absence_id}
Grund: {reason}
Von: {start_date}
Bis: {end_date}

Falls Sie Fragen haben, wenden Sie sich bitte an die Schulleitung.

Mit freundlichen Grüßen,
AbsenzFlow System"""

            teacher_html = deleted_teacher_html(
                teacher_name, reason, start_date, end_date, absence_id, deleted_by_name
            )
            result = await self.send_email(
                teacher_email, teacher_subject, teacher_body, teacher_html
            )
            if not result:
                success = False

        return success


# Singleton Instance
email_service = EmailService()
