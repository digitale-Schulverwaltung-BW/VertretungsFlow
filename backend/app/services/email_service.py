"""
E-Mail Service
Versand von Benachrichtigungen per E-Mail
"""

import logging
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List
from app.core.config import settings

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
        self, to: str, subject: str, body: str, html: bool = False
    ) -> bool:
        """
        Sendet eine E-Mail

        Args:
            to: Empfänger E-Mail-Adresse
            subject: Betreff
            body: Nachrichtentext
            html: True wenn body HTML ist

        Returns:
            True wenn erfolgreich, sonst False
        """
        try:
            message = MIMEMultipart("alternative")
            message["From"] = self.from_email
            message["To"] = to
            message["Subject"] = subject

            # Body hinzufügen
            if html:
                message.attach(MIMEText(body, "html"))
            else:
                message.attach(MIMEText(body, "plain"))

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

Bitte prüfen und genehmigen Sie die Abwesenheit im AbsenzFlow-System.

Link: {settings.FRONTEND_URL}/#/absence/{absence_id}

Mit freundlichen Grüßen,
AbsenzFlow System
        """

        # An Abteilungsleiter und Vertretungsplaner
        recipients = dept_head_emails + planner_emails

        success = True
        for email in recipients:
            result = await self.send_email(email, subject, body)
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
        # An Lehrkraft
        teacher_subject = "Ihre Abwesenheit wurde genehmigt"
        teacher_body = f"""
Hallo,

Ihre Abwesenheitsmeldung (ID: {absence_id}) wurde von {approver_name} genehmigt.

Mit freundlichen Grüßen,
AbsenzFlow System
        """

        await self.send_email(teacher_email, teacher_subject, teacher_body)

        # An Vertretungsplaner
        planner_subject = f"Abwesenheit #{absence_id} genehmigt"
        planner_body = f"""
Hallo,

Die Abwesenheit #{absence_id} wurde von {approver_name} genehmigt und ist nun bereit zur Vertretungsplanung.

Link: {settings.FRONTEND_URL}/#/absence/{absence_id}

Mit freundlichen Grüßen,
AbsenzFlow System
        """

        for email in planner_emails:
            await self.send_email(email, planner_subject, planner_body)

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
        subject = "Ihre Abwesenheit wurde eingetragen"
        body = f"""
Hallo,

Ihre Abwesenheitsmeldung (ID: {absence_id}) wurde in den Vertretungsplan eingetragen.

Mit freundlichen Grüßen,
AbsenzFlow System
        """

        return await self.send_email(teacher_email, subject, body)

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
AbsenzFlow System
        """

        return await self.send_email(teacher_email, subject, body)


# Singleton Instance
email_service = EmailService()
