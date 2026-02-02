"""
E-Mail Service
Versand von Benachrichtigungen per E-Mail
"""
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List
from app.core.config import settings


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
        body: str,
        html: bool = False
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
            
            # E-Mail versenden
            await aiosmtplib.send(
                message,
                hostname=self.host,
                port=self.port,
                username=self.username if self.username else None,
                password=self.password if self.password else None,
                start_tls=self.use_tls  # STARTTLS for port 587
            )
            
            return True
            
        except Exception as e:
            print(f"Email Send Error: {e}")
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
        end_date: str
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

Link: {settings.API_URL}/absences/{absence_id}

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
        approver_name: str
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

Link: {settings.API_URL}/absences/{absence_id}

Mit freundlichen Grüßen,
AbsenzFlow System
        """
        
        for email in planner_emails:
            await self.send_email(email, planner_subject, planner_body)
        
        return True
    
    async def send_absence_completed_notification(
        self,
        teacher_email: str,
        absence_id: int
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


# Singleton Instance
email_service = EmailService()
