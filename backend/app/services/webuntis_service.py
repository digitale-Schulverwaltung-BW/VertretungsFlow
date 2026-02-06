"""
WebUntis API Service
Integration mit WebUntis für Stundenplan-Abfragen
"""

import logging
import httpx
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from app.core.config import settings
from app.schemas.schemas import WebUntisLesson
from app.services.webuntis.parser import parse_timetable, merge_consecutive_lessons
from app.services.webuntis.client import WebUntisAPIClient
from app.services.webuntis.cache import WebUntisCache
from app.services.webuntis.data_loader import WebUntisDataLoader

logger = logging.getLogger(__name__)


class WebUntisService:
    """Service für WebUntis API Integration"""

    def __init__(self):
        # Initialize API client, cache, and data loader
        self.client = WebUntisAPIClient()
        self.cache = WebUntisCache()
        self.data_loader = WebUntisDataLoader(self.client, self.cache)

        # Backwards compatibility: expose session attributes
        self.session_id = None
        self.person_id = None

    @property
    def session_id(self) -> Optional[str]:
        """Backwards compatibility: expose client session_id"""
        return self.client.session_id

    @session_id.setter
    def session_id(self, value: Optional[str]):
        """Backwards compatibility: set client session_id"""
        if hasattr(self, "client"):
            self.client.session_id = value
        else:
            self._session_id = value

    # Backwards compatibility: Property-based cache attribute access for admin.py
    @property
    def _subjects_cache(self) -> Optional[Dict]:
        return self.cache._subjects_cache

    @_subjects_cache.setter
    def _subjects_cache(self, value: Optional[Dict]):
        self.cache._subjects_cache = value

    @property
    def _classes_cache(self) -> Optional[Dict]:
        return self.cache._classes_cache

    @_classes_cache.setter
    def _classes_cache(self, value: Optional[Dict]):
        self.cache._classes_cache = value

    @property
    def _rooms_cache(self) -> Optional[Dict]:
        return self.cache._rooms_cache

    @_rooms_cache.setter
    def _rooms_cache(self, value: Optional[Dict]):
        self.cache._rooms_cache = value

    @property
    def _timegrid_cache(self) -> Optional[Dict]:
        return self.cache._timegrid_cache

    @_timegrid_cache.setter
    def _timegrid_cache(self, value: Optional[Dict]):
        self.cache._timegrid_cache = value

    async def authenticate(self) -> bool:
        """
        Authentifiziert gegen WebUntis API
        Delegates to client

        Returns:
            True wenn erfolgreich, sonst False
        """
        result = await self.client.authenticate()
        if result:
            # Update cached person_id for backwards compatibility
            self.person_id = self.client.person_id
            # Clear caches on new session
            self.cache.clear_memory_cache()
        return result

    async def logout(self) -> bool:
        """Beendet WebUntis Session - Delegates to client"""
        return await self.client.logout()

    def _log_webuntis_error(self, exception: Exception, teacher_lookup: str) -> None:
        """
        Log WebUntis error with appropriate message based on exception type

        Args:
            exception: The exception that occurred
            teacher_lookup: Teacher username for logging
        """
        # Map exception types to error messages
        error_messages = {
            httpx.TimeoutException: "Request took too long",
            httpx.ConnectError: "Cannot reach WebUntis server",
            httpx.HTTPStatusError: lambda e: f"Server returned status {e.response.status_code}",
            KeyError: "Missing expected field in response",
            ValueError: "Invalid data format in response",
        }

        # Get error message
        exc_type = type(exception)
        if exc_type in error_messages:
            msg_template = error_messages[exc_type]
            msg = msg_template(exception) if callable(msg_template) else msg_template
            logger.error(f"❌ WebUntis {msg} for {teacher_lookup}")
        else:
            logger.error(
                f"❌ WebUntis Unexpected Error for {teacher_lookup}: {exc_type.__name__}"
            )

        # Log debug details (with traceback for data errors)
        exc_info = isinstance(exception, (KeyError, ValueError))
        logger.debug(f"Error details: {exception}", exc_info=exc_info)

    async def _fetch_and_parse_timetable(
        self,
        teacher_id: int,
        start_date: datetime,
        end_date: datetime,
        db,
    ) -> List[WebUntisLesson]:
        """
        Fetch and parse timetable for teacher

        Args:
            teacher_id: WebUntis teacher ID
            start_date: Start date
            end_date: End date
            db: Database session

        Returns:
            List of parsed lessons

        Raises:
            Various httpx and data exceptions (handled by caller)
        """
        # Convert dates to WebUntis format
        start_date_int = int(start_date.strftime("%Y%m%d"))
        end_date_int = int(end_date.strftime("%Y%m%d"))

        # Fetch raw lessons from WebUntis
        raw_lessons = await self.client.get_timetable(
            teacher_id, start_date_int, end_date_int
        )

        if len(raw_lessons) == 0:
            logger.warning(
                f"⚠️ WebUntis lieferte keine Stunden für den Zeitraum {start_date.date()} - {end_date.date()}"
            )
            return []

        # Parse and return lessons
        parsed_lessons = await self._parse_timetable(raw_lessons, teacher_id, db)
        logger.info(f"✅ {len(parsed_lessons)} Stunden erfolgreich geparst")
        return parsed_lessons

    async def get_timetable_for_teacher(
        self,
        teacher_username: str,
        start_date: datetime,
        end_date: datetime,
        db,
        webuntis_code: Optional[str] = None,
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

        logger.info(
            f"📅 Stundenplan abrufen für {teacher_username} (WebUntis-Lookup: {teacher_lookup}) ({start_date.date()} - {end_date.date()})"
        )

        # Authentifizieren wenn noch keine Session
        if not self.session_id:
            logger.info("Keine aktive Session, authentifiziere...")
            auth_success = await self.authenticate()
            if not auth_success:
                logger.error(
                    "❌ Authentifizierung fehlgeschlagen, kann Stundenplan nicht abrufen"
                )
                return []

        try:
            # Get teacher ID
            teacher_id = await self._get_teacher_id(teacher_lookup)
            if not teacher_id:
                logger.warning(
                    f"⚠️ Keine Teacher ID gefunden für {teacher_lookup}, gebe leere Liste zurück"
                )
                return []

            # Fetch and parse timetable
            return await self._fetch_and_parse_timetable(
                teacher_id, start_date, end_date, db
            )

        except (
            httpx.TimeoutException,
            httpx.ConnectError,
            httpx.HTTPStatusError,
            KeyError,
            ValueError,
            Exception,
        ) as e:
            self._log_webuntis_error(e, teacher_lookup)
            return []

    async def _get_teacher_id(self, username: str) -> Optional[int]:
        """
        Findet Teacher ID für Username - Delegates to client

        Args:
            username: Username der Lehrkraft

        Returns:
            Teacher ID oder None
        """
        return await self.client.find_teacher_id(username)

    async def _load_subjects(self, db, force_refresh: bool = False) -> dict:
        """Lädt Fächer-Stammdaten - Delegates to data_loader"""
        return await self.data_loader.load_subjects(db, force_refresh)

    async def _load_classes(self, db, force_refresh: bool = False) -> dict:
        """Lädt Klassen-Stammdaten - Delegates to data_loader"""
        return await self.data_loader.load_classes(db, force_refresh)

    async def _load_rooms(self, db, force_refresh: bool = False) -> dict:
        """Lädt Raum-Stammdaten - Delegates to data_loader"""
        return await self.data_loader.load_rooms(db, force_refresh)

    async def _load_timegrid(self, db, force_refresh: bool = False) -> dict:
        """Lädt Stundenraster - Delegates to data_loader (PUBLIC: used by pdf_service)"""
        return await self.data_loader.load_timegrid(db, force_refresh)

    async def _parse_timetable(
        self, timetable_data: List[dict], teacher_id: int, db
    ) -> List[WebUntisLesson]:
        """
        Parsed Stundenplan-Daten von WebUntis

        Args:
            timetable_data: Rohdaten von WebUntis
            teacher_id: ID des Lehrers (zum Filtern bei Team-Teaching)
            db: Database session

        Returns:
            Liste von WebUntisLesson Objekten
        """
        # Stammdaten laden (werden gecached)
        subjects = await self._load_subjects(db)
        classes = await self._load_classes(db)
        rooms = await self._load_rooms(db)
        timegrid = await self._load_timegrid(db)

        # Delegate to pure parser function
        return parse_timetable(
            timetable_data, teacher_id, subjects, classes, rooms, timegrid
        )


# Singleton Instance
webuntis_service = WebUntisService()
