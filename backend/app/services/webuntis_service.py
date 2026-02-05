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

    def _convert_string_keys_to_int(self, data: dict) -> dict:
        """
        Konvertiert String-Keys zurück zu Integer-Keys
        JSONB in PostgreSQL speichert numerische Keys als Strings

        Args:
            data: Dictionary mit möglicherweise String-Keys

        Returns:
            Dictionary mit Integer-Keys (wo möglich)
        """
        converted = {}
        for key, value in data.items():
            try:
                # Versuche Key in Integer zu konvertieren
                int_key = int(key)
                converted[int_key] = value
            except (ValueError, TypeError):
                # Wenn Konvertierung fehlschlägt, behalte String-Key
                converted[key] = value
        return converted

    async def _get_cached_data(
        self,
        db,
        cache_key: str,
        fetch_func,
        force_refresh: bool = False
    ) -> dict:
        """
        Generische Cache-Lookup-Methode mit 3-Layer-Cache

        Args:
            db: Database session
            cache_key: Cache key (z.B. 'webuntis:subjects')
            fetch_func: Async function to fetch from API if cache miss
            force_refresh: Force API call even if cache exists

        Returns:
            Cached or fresh data as dict
        """
        from app.models.models import WebUntisCache

        if not settings.WEBUNTIS_CACHE_ENABLED:
            return await fetch_func()

        # Layer 1: In-Memory Cache
        memory_cache_key = cache_key.replace('webuntis:', '_') + '_cache'
        if not force_refresh and getattr(self, memory_cache_key, None):
            logger.info(f"WebUntis cache hit (memory): {cache_key}")
            return getattr(self, memory_cache_key)

        # Layer 2: DB Cache
        if not force_refresh:
            db_entry = db.query(WebUntisCache).filter(
                WebUntisCache.cache_key == cache_key
            ).first()

            if db_entry:
                # Check if expired
                if db_entry.expires_at is None or db_entry.expires_at > datetime.utcnow():
                    logger.info(f"WebUntis cache hit (DB): {cache_key}")
                    # JSONB konvertiert numerische Keys zu Strings - zurückkonvertieren
                    cached_data = self._convert_string_keys_to_int(db_entry.cache_data)
                    setattr(self, memory_cache_key, cached_data)
                    return cached_data
                else:
                    logger.info(f"WebUntis cache expired: {cache_key}")

        # Layer 3: Fetch from API
        logger.info(f"WebUntis cache miss, fetching from API: {cache_key}")
        data = await fetch_func()

        # Store in DB
        expires_at = datetime.utcnow() + timedelta(hours=settings.WEBUNTIS_CACHE_TTL_HOURS)

        db_entry = db.query(WebUntisCache).filter(
            WebUntisCache.cache_key == cache_key
        ).first()

        if db_entry:
            db_entry.cache_data = data
            db_entry.expires_at = expires_at
            db_entry.updated_at = datetime.utcnow()
        else:
            db_entry = WebUntisCache(
                cache_key=cache_key,
                cache_data=data,
                expires_at=expires_at
            )
            db.add(db_entry)

        db.commit()

        # Store in memory
        setattr(self, memory_cache_key, data)

        return data

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
        db,
        webuntis_code: Optional[str] = None
    ) -> List[WebUntisLesson]:
        """
        Holt Stundenplan für Lehrkraft im angegebenen Zeitraum

        Args:
            teacher_username: Username der Lehrkraft
            start_date: Startdatum
            end_date: Enddatum
            db: Database session
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
                                teacher_username, start_date, end_date, db, webuntis_code
                            )
                        else:
                            logger.error("❌ Re-Authentifizierung fehlgeschlagen")
                            return []

                    if "result" in data:
                        raw_lessons = data["result"]
                        logger.info(f"📚 {len(raw_lessons)} Stundeneinträge von WebUntis erhalten")

                        if len(raw_lessons) == 0:
                            logger.warning(f"⚠️ WebUntis lieferte keine Stunden für den Zeitraum {start_date.date()} - {end_date.date()}")

                        parsed_lessons = await self._parse_timetable(raw_lessons, teacher_id, db)
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

    async def _load_subjects(self, db, force_refresh: bool = False) -> dict:
        """
        Lädt Fächer-Stammdaten und erstellt ID->Name Mapping

        Args:
            db: Database session
            force_refresh: Force API call even if cache exists

        Returns:
            Dictionary mit subject_id -> subject_name
        """
        async def fetch_from_api():
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
                            subjects_dict = {
                                subj["id"]: subj.get("name", subj.get("longName", "Unbekannt"))
                                for subj in subjects
                            }
                            logger.info(f"✅ {len(subjects_dict)} Fächer geladen")
                            return subjects_dict

                    logger.error(f"❌ Fächer laden fehlgeschlagen (Status: {response.status_code})")
                    return {}

            except Exception as e:
                logger.error(f"❌ Exception beim Laden der Fächer: {e}", exc_info=True)
                return {}

        return await self._get_cached_data(
            db=db,
            cache_key='webuntis:subjects',
            fetch_func=fetch_from_api,
            force_refresh=force_refresh
        )

    async def _load_classes(self, db, force_refresh: bool = False) -> dict:
        """
        Lädt Klassen-Stammdaten und erstellt ID->Name Mapping

        Args:
            db: Database session
            force_refresh: Force API call even if cache exists

        Returns:
            Dictionary mit class_id -> class_name
        """
        async def fetch_from_api():
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
                            classes_dict = {
                                kl["id"]: kl.get("name", kl.get("longName", "Unbekannt"))
                                for kl in classes
                            }
                            logger.info(f"✅ {len(classes_dict)} Klassen geladen")
                            return classes_dict

                    logger.error(f"❌ Klassen laden fehlgeschlagen (Status: {response.status_code})")
                    return {}

            except Exception as e:
                logger.error(f"❌ Exception beim Laden der Klassen: {e}", exc_info=True)
                return {}

        return await self._get_cached_data(
            db=db,
            cache_key='webuntis:classes',
            fetch_func=fetch_from_api,
            force_refresh=force_refresh
        )

    async def _load_rooms(self, db, force_refresh: bool = False) -> dict:
        """
        Lädt Raum-Stammdaten und erstellt ID->Name Mapping

        Args:
            db: Database session
            force_refresh: Force API call even if cache exists

        Returns:
            Dictionary mit room_id -> room_name
        """
        async def fetch_from_api():
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
                            rooms_dict = {
                                room["id"]: room.get("longName", room.get("name", "Unbekannt"))
                                for room in rooms
                            }
                            logger.info(f"✅ {len(rooms_dict)} Räume geladen")
                            return rooms_dict

                    logger.error(f"❌ Räume laden fehlgeschlagen (Status: {response.status_code})")
                    return {}

            except Exception as e:
                logger.error(f"❌ Exception beim Laden der Räume: {e}", exc_info=True)
                return {}

        return await self._get_cached_data(
            db=db,
            cache_key='webuntis:rooms',
            fetch_func=fetch_from_api,
            force_refresh=force_refresh
        )

    async def _load_timegrid(self, db, force_refresh: bool = False) -> dict:
        """
        Lädt Stundenraster und erstellt startTime -> period Mapping

        Args:
            db: Database session
            force_refresh: Force API call even if cache exists

        Returns:
            Dictionary mit startTime -> period_number
        """
        async def fetch_from_api():
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
                            timegrid_dict = {}
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
                                            timegrid_dict[start_time] = period
                                            logger.debug(f"  {start_time} -> Stunde {period}")
                                        except ValueError:
                                            logger.warning(f"Ungültiger Period-Name: {period_name}")

                            logger.info(f"✅ Stundenraster mit {len(timegrid_dict)} Einträgen geladen")
                            return timegrid_dict
                        elif "error" in data:
                            logger.error(f"❌ WebUntis API Error beim Timegrid-Abruf: {data['error']}")
                            return {}

                    logger.error(f"❌ Stundenraster laden fehlgeschlagen (Status: {response.status_code})")
                    logger.error(f"Response: {response.text}")
                    return {}

            except Exception as e:
                logger.error(f"❌ Exception beim Laden des Stundenrasters: {e}", exc_info=True)
                return {}

        return await self._get_cached_data(
            db=db,
            cache_key='webuntis:timegrid',
            fetch_func=fetch_from_api,
            force_refresh=force_refresh
        )

    async def _parse_timetable(self, timetable_data: List[dict], teacher_id: int, db) -> List[WebUntisLesson]:
        """
        Parsed Stundenplan-Daten von WebUntis

        Args:
            timetable_data: Rohdaten von WebUntis
            teacher_id: ID des Lehrers (zum Filtern bei Team-Teaching)
            db: Database session

        Returns:
            Liste von WebUntisLesson Objekten
        """
        logger.debug(f"Parse Timetable: {len(timetable_data)} Einträge")

        # Stammdaten laden (werden gecached)
        subjects = await self._load_subjects(db)
        classes = await self._load_classes(db)
        rooms = await self._load_rooms(db)
        timegrid = await self._load_timegrid(db)

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
                # WICHTIG: JSONB speichert numerische Keys als Strings, daher beide Varianten probieren
                subject_ids = [s.get("id") for s in entry.get("su", [])]
                if subject_ids:
                    subject_id = subject_ids[0]
                    subject = subjects.get(subject_id) or subjects.get(str(subject_id), "Unbekannt")
                else:
                    subject = "Unbekannt"

                class_ids = [c.get("id") for c in entry.get("kl", [])]
                if class_ids:
                    class_id = class_ids[0]
                    class_name = classes.get(class_id) or classes.get(str(class_id), "Unbekannt")
                else:
                    class_name = "Unbekannt"

                room_ids = [r.get("id") for r in entry.get("ro", [])]
                if room_ids:
                    room_id = room_ids[0]
                    room = rooms.get(room_id) or rooms.get(str(room_id))
                else:
                    room = None

                # Stundennummer aus Timegrid ermitteln
                start_time = entry.get("startTime", 0)
                end_time = entry.get("endTime", 0)
                # JSONB konvertiert auch hier Keys zu Strings
                period = timegrid.get(start_time) or timegrid.get(str(start_time), start_time // 100)

                lesson = WebUntisLesson(
                    date=date,
                    period=period,
                    start_time=start_time if start_time else None,
                    end_time=end_time if end_time else None,
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
