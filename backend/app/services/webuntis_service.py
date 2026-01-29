"""
WebUntis API Service
Integration mit WebUntis für Stundenplan-Abfragen
"""
import logging
import httpx
from datetime import datetime, timedelta
from typing import List, Optional
from app.core.config import settings
from app.schemas.schemas import WebUntisLesson

logger = logging.getLogger(__name__)


class WebUntisService:
    """Service für WebUntis API Integration"""
    
    def __init__(self):
        self.school = settings.WEBUNTIS_SCHOOL
        self.username = settings.WEBUNTIS_USERNAME
        self.password = settings.WEBUNTIS_PASSWORD
        self.server = settings.WEBUNTIS_SERVER
        self.base_url = f"https://{self.server}/WebUntis/jsonrpc.do"
        self.session_id: Optional[str] = None
        self.person_id: Optional[int] = None
    
    async def authenticate(self) -> bool:
        """
        Authentifiziert gegen WebUntis API

        Returns:
            True wenn erfolgreich, sonst False
        """
        logger.info(f"🔐 Authentifizierung gegen WebUntis: {self.server} (Schule: {self.school})")

        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "id": "auth",
                    "method": "authenticate",
                    "params": {
                        "user": self.username,
                        "password": "***",  # Password in Logs nicht anzeigen
                        "client": "AbsenzFlow"
                    },
                    "jsonrpc": "2.0"
                }

                logger.debug(f"Auth Request URL: {self.base_url}")
                logger.debug(f"Auth Request Payload (ohne Passwort): {payload}")

                # Payload mit richtigem Passwort für den Request
                actual_payload = payload.copy()
                actual_payload["params"] = payload["params"].copy()
                actual_payload["params"]["password"] = self.password

                response = await client.post(
                    f"{self.base_url}", 
                    json=actual_payload
                )

                logger.debug(f"Auth Response Status: {response.status_code}")
                logger.debug(f"Auth Response Headers: {dict(response.headers)}")

                if response.status_code == 200:
                    data = response.json()
                    logger.debug(f"Auth Response Data: {data}")

                    if "result" in data:
                        self.session_id = data["result"]["sessionId"]
                        self.person_id = data["result"]["personId"]
                        logger.info(f"✅ Authentifizierung erfolgreich (PersonID: {self.person_id})")
                        return True
                    elif "error" in data:
                        logger.error(f"❌ WebUntis API Error: {data['error']}")
                        return False

                logger.error(f"❌ Authentifizierung fehlgeschlagen (Status: {response.status_code})")
                logger.error(f"Response Body: {response.text}")
                return False

        except Exception as e:
            logger.error(f"❌ WebUntis Auth Exception: {e}", exc_info=True)
            return False
    
    async def logout(self) -> bool:
        """Beendet WebUntis Session"""
        if not self.session_id:
            logger.debug("Keine aktive Session zum Ausloggen")
            return True

        logger.info("🔓 WebUntis Logout...")

        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "id": "logout",
                    "method": "logout",
                    "params": {},
                    "jsonrpc": "2.0"
                }

                response = await client.post(
                    f"{self.base_url}",
                    json=payload,
                    cookies={"JSESSIONID": self.session_id}
                )

                logger.debug(f"Logout Response Status: {response.status_code}")
                self.session_id = None

                if response.status_code == 200:
                    logger.info("✅ Logout erfolgreich")
                    return True
                else:
                    logger.warning(f"⚠️ Logout fehlgeschlagen (Status: {response.status_code})")
                    return False

        except Exception as e:
            logger.error(f"❌ WebUntis Logout Exception: {e}", exc_info=True)
            return False
    
    async def get_timetable_for_teacher(
        self,
        teacher_username: str,
        start_date: datetime,
        end_date: datetime,
        webuntis_code: Optional[str] = None
    ) -> List[WebUntisLesson]:
        """
        Holt Stundenplan für Lehrkraft im angegebenen Zeitraum

        Args:
            teacher_username: Username der Lehrkraft
            start_date: Startdatum
            end_date: Enddatum
            webuntis_code: WebUntis Lehrerkürzel (optional, Fallback auf teacher_username)

        Returns:
            Liste von Stunden
        """
        # Verwende WebUntis-Code wenn vorhanden, sonst Username
        teacher_lookup = webuntis_code if webuntis_code else teacher_username

        logger.info(f"📅 Stundenplan abrufen für {teacher_username} (WebUntis-Lookup: {teacher_lookup}) ({start_date.date()} - {end_date.date()})")

        # Authentifizieren wenn noch keine Session
        if not self.session_id:
            logger.info("Keine aktive Session, authentifiziere...")
            auth_success = await self.authenticate()
            if not auth_success:
                logger.error("❌ Authentifizierung fehlgeschlagen, kann Stundenplan nicht abrufen")
                return []

        try:
            # Zuerst: Teacher ID finden (mit WebUntis Code oder Username)
            teacher_id = await self._get_teacher_id(teacher_lookup)
            if not teacher_id:
                logger.warning(f"⚠️ Keine Teacher ID gefunden für {teacher_lookup}, gebe leere Liste zurück")
                return []

            # Dann: Stundenplan abrufen
            async with httpx.AsyncClient() as client:
                payload = {
                    "id": "getTimetable",
                    "method": "getTimetable",
                    "params": {
                        "id": teacher_id,
                        "type": 2,  # Type 2 = Teacher
                        "startDate": start_date.strftime("%Y%m%d"),
                        "endDate": end_date.strftime("%Y%m%d")
                    },
                    "jsonrpc": "2.0"
                }

                logger.debug(f"GetTimetable Request: {payload}")

                response = await client.post(
                    f"{self.base_url}",
                    json=payload,
                    cookies={"JSESSIONID": self.session_id}
                )

                logger.debug(f"GetTimetable Response Status: {response.status_code}")

                if response.status_code == 200:
                    data = response.json()
                    logger.debug(f"GetTimetable Response: {data}")

                    if "result" in data:
                        raw_lessons = data["result"]
                        logger.info(f"📚 {len(raw_lessons)} Stundeneinträge von WebUntis erhalten")

                        if len(raw_lessons) == 0:
                            logger.warning(f"⚠️ WebUntis lieferte keine Stunden für den Zeitraum {start_date.date()} - {end_date.date()}")

                        parsed_lessons = self._parse_timetable(raw_lessons)
                        logger.info(f"✅ {len(parsed_lessons)} Stunden erfolgreich geparst")
                        return parsed_lessons

                    elif "error" in data:
                        logger.error(f"❌ WebUntis API Error beim Stundenplan-Abruf: {data['error']}")
                        return []

                logger.error(f"❌ GetTimetable fehlgeschlagen (Status: {response.status_code})")
                logger.error(f"Response: {response.text}")
                return []

        except Exception as e:
            logger.error(f"❌ WebUntis Get Timetable Exception: {e}", exc_info=True)
            return []
    
    async def _get_teacher_id(self, username: str) -> Optional[int]:
        """
        Findet Teacher ID für Username

        Args:
            username: Username der Lehrkraft

        Returns:
            Teacher ID oder None
        """
        logger.info(f"🔍 Suche Teacher ID für Username: {username}")

        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "id": "getTeachers",
                    "method": "getTeachers",
                    "params": {},
                    "jsonrpc": "2.0"
                }

                logger.debug(f"GetTeachers Request: {payload}")

                response = await client.post(
                    f"{self.base_url}",
                    json=payload,
                    cookies={"JSESSIONID": self.session_id}
                )

                logger.debug(f"GetTeachers Response Status: {response.status_code}")

                if response.status_code == 200:
                    data = response.json()

                    if "result" in data:
                        teachers = data["result"]
                        logger.info(f"📋 {len(teachers)} Lehrer gefunden")
                        logger.debug(f"Alle Lehrer: {teachers}")

                        # Alle Lehrernamen loggen für Debugging
                        teacher_names = [t.get("name", "?") for t in teachers]
                        logger.debug(f"Lehrernamen: {teacher_names}")

                        for teacher in teachers:
                            teacher_name = teacher.get("name", "")
                            if teacher_name.lower() == username.lower():
                                teacher_id = teacher.get("id")
                                logger.info(f"✅ Teacher ID gefunden: {teacher_id} für {username}")
                                return teacher_id

                        logger.warning(f"⚠️ Kein Lehrer mit Username '{username}' gefunden")
                        logger.warning(f"Verfügbare Namen: {', '.join(teacher_names[:10])}")
                        return None

                    elif "error" in data:
                        logger.error(f"❌ WebUntis API Error beim Lehrer-Abruf: {data['error']}")
                        return None

                logger.error(f"❌ GetTeachers fehlgeschlagen (Status: {response.status_code})")
                logger.error(f"Response: {response.text}")
                return None

        except Exception as e:
            logger.error(f"❌ WebUntis Get Teacher ID Exception: {e}", exc_info=True)
            return None
    
    def _parse_timetable(self, timetable_data: List[dict]) -> List[WebUntisLesson]:
        """
        Parsed Stundenplan-Daten von WebUntis

        Args:
            timetable_data: Rohdaten von WebUntis

        Returns:
            Liste von WebUntisLesson Objekten
        """
        logger.debug(f"Parse Timetable: {len(timetable_data)} Einträge")
        lessons = []

        for i, entry in enumerate(timetable_data):
            try:
                logger.debug(f"Parse Entry {i+1}/{len(timetable_data)}: {entry}")

                # Datum parsen (Format: YYYYMMDD)
                date_str = str(entry.get("date", ""))
                date = datetime.strptime(date_str, "%Y%m%d")

                # Informationen extrahieren
                subject = self._get_subject_name(entry)
                class_name = self._get_class_name(entry)
                room = self._get_room_name(entry)
                period = entry.get("startTime", 0) // 100

                lesson = WebUntisLesson(
                    date=date,
                    period=period,
                    subject=subject,
                    class_name=class_name,
                    room=room
                )

                logger.debug(f"✅ Stunde geparst: {date.date()} #{period} - {subject} ({class_name})")
                lessons.append(lesson)

            except Exception as e:
                logger.error(f"❌ Parse Lesson Error bei Entry {i+1}: {e}", exc_info=True)
                logger.error(f"Problematischer Entry: {entry}")
                continue

        logger.info(f"Parsing abgeschlossen: {len(lessons)}/{len(timetable_data)} Stunden erfolgreich geparst")
        return lessons
    
    def _get_subject_name(self, entry: dict) -> str:
        """Extrahiert Fachname aus Entry"""
        subjects = entry.get("su", [])
        if subjects and len(subjects) > 0:
            return subjects[0].get("longname", "Unbekannt")
        return "Unbekannt"
    
    def _get_class_name(self, entry: dict) -> str:
        """Extrahiert Klassenname aus Entry"""
        classes = entry.get("kl", [])
        if classes and len(classes) > 0:
            return classes[0].get("name", "Unbekannt")
        return "Unbekannt"
    
    def _get_room_name(self, entry: dict) -> Optional[str]:
        """Extrahiert Raumname aus Entry"""
        rooms = entry.get("ro", [])
        if rooms and len(rooms) > 0:
            return rooms[0].get("name")
        return None


# Singleton Instance
webuntis_service = WebUntisService()
