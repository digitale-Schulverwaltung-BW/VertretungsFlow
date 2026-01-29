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

        # Caches für Stammdaten (ID -> Name Mapping)
        self._subjects_cache: Optional[dict] = None
        self._classes_cache: Optional[dict] = None
        self._rooms_cache: Optional[dict] = None
        self._timegrid_cache: Optional[dict] = None  # startTime -> period mapping
    
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
                    logger.info(f"📦 GetTimetable Response: {data}")

                    # Check for authentication error
                    if "error" in data and data["error"].get("code") == -8520:
                        logger.warning(f"⚠️ WebUntis Session abgelaufen, authentifiziere neu...")
                        self.session_id = None
                        # Clear caches (they were fetched with old session)
                        self._subjects_cache = None
                        self._classes_cache = None
                        self._rooms_cache = None
                        self._timegrid_cache = None
                        # Re-authenticate and retry
                        if await self.authenticate():
                            return await self.get_timetable_for_teacher(
                                teacher_username, start_date, end_date, webuntis_code
                            )
                        else:
                            logger.error("❌ Re-Authentifizierung fehlgeschlagen")
                            return []

                    if "result" in data:
                        raw_lessons = data["result"]
                        logger.info(f"📚 {len(raw_lessons)} Stundeneinträge von WebUntis erhalten")

                        if len(raw_lessons) == 0:
                            logger.warning(f"⚠️ WebUntis lieferte keine Stunden für den Zeitraum {start_date.date()} - {end_date.date()}")

                        parsed_lessons = await self._parse_timetable(raw_lessons, teacher_id)
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

                    # Check for authentication error
                    if "error" in data and data["error"].get("code") == -8520:
                        logger.warning(f"⚠️ WebUntis Session abgelaufen, authentifiziere neu...")
                        self.session_id = None
                        # Clear caches (they were fetched with old session)
                        self._subjects_cache = None
                        self._classes_cache = None
                        self._rooms_cache = None
                        self._timegrid_cache = None
                        # Re-authenticate and retry
                        if await self.authenticate():
                            return await self._get_teacher_id(username)
                        else:
                            logger.error("❌ Re-Authentifizierung fehlgeschlagen")
                            return None

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

    async def _load_subjects(self) -> dict:
        """
        Lädt Fächer-Stammdaten und erstellt ID->Name Mapping

        Returns:
            Dictionary mit subject_id -> subject_name
        """
        if self._subjects_cache is not None:
            return self._subjects_cache

        logger.info("📚 Lade Fächer-Stammdaten...")

        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "id": "getSubjects",
                    "method": "getSubjects",
                    "params": {},
                    "jsonrpc": "2.0"
                }

                response = await client.post(
                    f"{self.base_url}",
                    json=payload,
                    cookies={"JSESSIONID": self.session_id}
                )

                if response.status_code == 200:
                    data = response.json()

                    if "result" in data:
                        subjects = data["result"]
                        # Verwende Kurzname (name) statt Langname (longName) wegen sehr langer Fachnamen
                        self._subjects_cache = {
                            subj["id"]: subj.get("name", subj.get("longName", "Unbekannt"))
                            for subj in subjects
                        }
                        logger.info(f"✅ {len(self._subjects_cache)} Fächer geladen")
                        return self._subjects_cache

                logger.error(f"❌ Fächer laden fehlgeschlagen (Status: {response.status_code})")
                return {}

        except Exception as e:
            logger.error(f"❌ Exception beim Laden der Fächer: {e}", exc_info=True)
            return {}

    async def _load_classes(self) -> dict:
        """
        Lädt Klassen-Stammdaten und erstellt ID->Name Mapping

        Returns:
            Dictionary mit class_id -> class_name
        """
        if self._classes_cache is not None:
            return self._classes_cache

        logger.info("🎓 Lade Klassen-Stammdaten...")

        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "id": "getKlassen",
                    "method": "getKlassen",
                    "params": {},
                    "jsonrpc": "2.0"
                }

                response = await client.post(
                    f"{self.base_url}",
                    json=payload,
                    cookies={"JSESSIONID": self.session_id}
                )

                if response.status_code == 200:
                    data = response.json()

                    if "result" in data:
                        classes = data["result"]
                        # Verwende Kurzname (name) statt Langname (longName)
                        self._classes_cache = {
                            kl["id"]: kl.get("name", kl.get("longName", "Unbekannt"))
                            for kl in classes
                        }
                        logger.info(f"✅ {len(self._classes_cache)} Klassen geladen")
                        return self._classes_cache

                logger.error(f"❌ Klassen laden fehlgeschlagen (Status: {response.status_code})")
                return {}

        except Exception as e:
            logger.error(f"❌ Exception beim Laden der Klassen: {e}", exc_info=True)
            return {}

    async def _load_rooms(self) -> dict:
        """
        Lädt Raum-Stammdaten und erstellt ID->Name Mapping

        Returns:
            Dictionary mit room_id -> room_name
        """
        if self._rooms_cache is not None:
            return self._rooms_cache

        logger.info("🏫 Lade Raum-Stammdaten...")

        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "id": "getRooms",
                    "method": "getRooms",
                    "params": {},
                    "jsonrpc": "2.0"
                }

                response = await client.post(
                    f"{self.base_url}",
                    json=payload,
                    cookies={"JSESSIONID": self.session_id}
                )

                if response.status_code == 200:
                    data = response.json()

                    if "result" in data:
                        rooms = data["result"]
                        self._rooms_cache = {
                            room["id"]: room.get("longName", room.get("name", "Unbekannt"))
                            for room in rooms
                        }
                        logger.info(f"✅ {len(self._rooms_cache)} Räume geladen")
                        return self._rooms_cache

                logger.error(f"❌ Räume laden fehlgeschlagen (Status: {response.status_code})")
                return {}

        except Exception as e:
            logger.error(f"❌ Exception beim Laden der Räume: {e}", exc_info=True)
            return {}

    async def _load_timegrid(self) -> dict:
        """
        Lädt Stundenraster und erstellt startTime -> period Mapping

        Returns:
            Dictionary mit startTime -> period_number
        """
        if self._timegrid_cache is not None:
            return self._timegrid_cache

        logger.info("⏰ Lade Stundenraster...")

        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "id": "getTimegridUnits",
                    "method": "getTimegridUnits",
                    "params": {},
                    "jsonrpc": "2.0"
                }

                response = await client.post(
                    f"{self.base_url}",
                    json=payload,
                    cookies={"JSESSIONID": self.session_id}
                )

                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"📦 Timegrid Response: {data}")

                    if "result" in data:
                        timegrid_days = data["result"]
                        logger.info(f"📋 Timegrid hat {len(timegrid_days)} Tage")

                        # Erstelle Mapping: startTime -> period (Stundennummer)
                        # Structure: [{day: 2, timeUnits: [{name: "1", startTime: 730, ...}]}]
                        self._timegrid_cache = {}
                        for day_entry in timegrid_days:
                            day = day_entry.get("day")
                            time_units = day_entry.get("timeUnits", [])
                            logger.debug(f"Tag {day}: {len(time_units)} Zeiteinheiten")

                            for unit in time_units:
                                start_time = unit.get("startTime")
                                period_name = unit.get("name")  # "1", "2", "3" als String

                                if start_time and period_name:
                                    try:
                                        period = int(period_name)
                                        self._timegrid_cache[start_time] = period
                                        logger.debug(f"  {start_time} -> Stunde {period}")
                                    except ValueError:
                                        logger.warning(f"Ungültiger Period-Name: {period_name}")

                        logger.info(f"✅ Stundenraster mit {len(self._timegrid_cache)} Einträgen geladen")
                        return self._timegrid_cache
                    elif "error" in data:
                        logger.error(f"❌ WebUntis API Error beim Timegrid-Abruf: {data['error']}")
                        return {}

                logger.error(f"❌ Stundenraster laden fehlgeschlagen (Status: {response.status_code})")
                logger.error(f"Response: {response.text}")
                return {}

        except Exception as e:
            logger.error(f"❌ Exception beim Laden des Stundenrasters: {e}", exc_info=True)
            return {}

    async def _parse_timetable(self, timetable_data: List[dict], teacher_id: int) -> List[WebUntisLesson]:
        """
        Parsed Stundenplan-Daten von WebUntis

        Args:
            timetable_data: Rohdaten von WebUntis
            teacher_id: ID des Lehrers (zum Filtern bei Team-Teaching)

        Returns:
            Liste von WebUntisLesson Objekten
        """
        logger.debug(f"Parse Timetable: {len(timetable_data)} Einträge")

        # Stammdaten laden (werden gecached)
        subjects = await self._load_subjects()
        classes = await self._load_classes()
        rooms = await self._load_rooms()
        timegrid = await self._load_timegrid()

        lessons = []

        for i, entry in enumerate(timetable_data):
            try:
                logger.info(f"📝 Parse Entry {i+1}/{len(timetable_data)}: {entry}")

                # Filter: Nur Stunden wo der Lehrer tatsächlich dabei ist
                teacher_ids = [t.get("id") for t in entry.get("te", [])]
                if teacher_id not in teacher_ids:
                    logger.info(f"⏭️ Überspringe Entry {i+1}: Lehrer {teacher_id} nicht in {teacher_ids}")
                    continue

                # Datum parsen (Format: YYYYMMDD)
                date_str = str(entry.get("date", ""))
                date = datetime.strptime(date_str, "%Y%m%d")

                # IDs auflösen
                subject_ids = [s.get("id") for s in entry.get("su", [])]
                subject = subjects.get(subject_ids[0], "Unbekannt") if subject_ids else "Unbekannt"

                class_ids = [c.get("id") for c in entry.get("kl", [])]
                class_name = classes.get(class_ids[0], "Unbekannt") if class_ids else "Unbekannt"

                room_ids = [r.get("id") for r in entry.get("ro", [])]
                room = rooms.get(room_ids[0]) if room_ids else None

                # Stundennummer aus Timegrid ermitteln
                start_time = entry.get("startTime", 0)
                period = timegrid.get(start_time, start_time // 100)  # Fallback auf alte Methode

                lesson = WebUntisLesson(
                    date=date,
                    period=period,
                    subject=subject,
                    class_name=class_name,
                    room=room
                )

                logger.info(f"✅ Stunde geparst: {date.date()} #{period} - {subject} ({class_name}) in {room}")
                lessons.append(lesson)

            except Exception as e:
                logger.error(f"❌ Parse Lesson Error bei Entry {i+1}: {e}", exc_info=True)
                logger.error(f"Problematischer Entry: {entry}")
                continue

        logger.info(f"Parsing abgeschlossen: {len(lessons)}/{len(timetable_data)} Stunden erfolgreich geparst")

        # Doppelstunden zusammenfassen
        merged_lessons = self._merge_consecutive_lessons(lessons)
        logger.info(f"🔗 Nach Zusammenfassung: {len(merged_lessons)} Stundenblöcke")

        return merged_lessons

    def _merge_consecutive_lessons(self, lessons: List[WebUntisLesson]) -> List[WebUntisLesson]:
        """
        Fasst aufeinanderfolgende Stunden mit gleicher Klasse und gleichem Fach zusammen

        Args:
            lessons: Liste von einzelnen Stunden

        Returns:
            Liste mit zusammengefassten Stundenblöcken
        """
        if not lessons:
            return lessons

        # Sortieren nach Datum und Periode
        sorted_lessons = sorted(lessons, key=lambda l: (l.date, l.period))

        merged = []
        current_block = None

        for lesson in sorted_lessons:
            if current_block is None:
                # Erster Block
                current_block = {
                    "lesson": lesson,
                    "start_period": lesson.period,
                    "end_period": lesson.period
                }
            elif (
                lesson.date == current_block["lesson"].date
                and lesson.class_name == current_block["lesson"].class_name
                and lesson.subject == current_block["lesson"].subject
                and lesson.room == current_block["lesson"].room
                and lesson.period == current_block["end_period"] + 1
            ):
                # Aufeinanderfolgende Stunde mit gleicher Klasse/Fach -> erweitern
                current_block["end_period"] = lesson.period
                logger.debug(f"🔗 Erweitere Block: {lesson.class_name} {lesson.subject} "
                           f"({current_block['start_period']}-{current_block['end_period']})")
            else:
                # Neuer Block beginnt
                merged.append(current_block)
                current_block = {
                    "lesson": lesson,
                    "start_period": lesson.period,
                    "end_period": lesson.period
                }

        # Letzten Block hinzufügen
        if current_block:
            merged.append(current_block)

        # Konvertiere Blöcke zurück zu WebUntisLesson mit end_period
        result = []
        for block in merged:
            lesson = block["lesson"]
            # Setze end_period für Doppelstunden
            if block["start_period"] != block["end_period"]:
                # Erstelle neue WebUntisLesson mit end_period
                merged_lesson = WebUntisLesson(
                    date=lesson.date,
                    period=block["start_period"],
                    end_period=block["end_period"],
                    subject=lesson.subject,
                    class_name=lesson.class_name,
                    room=lesson.room
                )
                logger.info(f"📚 Stundenblock: {block['start_period']}.{block['end_period']}. Stunde - "
                          f"{lesson.subject} ({lesson.class_name})")
                result.append(merged_lesson)
            else:
                # Einzelstunde
                result.append(lesson)

        return result


# Singleton Instance
webuntis_service = WebUntisService()
