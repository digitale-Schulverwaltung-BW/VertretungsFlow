"""
WebUntis API Client
Low-level HTTP communication layer for WebUntis JSON-RPC API
"""

import logging
import httpx
from typing import List, Dict, Optional, Callable, Any
from app.core.config import settings

logger = logging.getLogger(__name__)


class WebUntisAPIClient:
    """
    HTTP client for WebUntis API communication
    Handles authentication, session management, and JSON-RPC calls
    """

    def __init__(
        self,
        server: str = None,
        username: str = None,
        password: str = None,
    ):
        """
        Initialize WebUntis API client

        Args:
            server: WebUntis server URL (default: from settings)
            username: API username (default: from settings)
            password: API password (default: from settings)
        """
        self.server = server or settings.WEBUNTIS_SERVER
        self.username = username or settings.WEBUNTIS_USERNAME
        self.password = password or settings.WEBUNTIS_PASSWORD
        self.base_url = f"https://{self.server}/WebUntis/jsonrpc.do"

        # Session state
        self.session_id: Optional[str] = None
        self.person_id: Optional[int] = None

    async def authenticate(self) -> bool:
        """
        Authentifiziert gegen WebUntis API

        Returns:
            True wenn erfolgreich, sonst False
        """
        logger.info(f"🔐 Authentifizierung gegen WebUntis: {self.server}")

        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "id": "auth",
                    "method": "authenticate",
                    "params": {
                        "user": self.username,
                        "password": "***",  # Password in Logs nicht anzeigen
                        "client": "AbsenzFlow",
                    },
                    "jsonrpc": "2.0",
                }

                logger.debug(f"Auth Request URL: {self.base_url}")
                logger.debug(f"Auth Request Payload (ohne Passwort): {payload}")

                # Payload mit richtigem Passwort für den Request
                actual_payload = payload.copy()
                actual_payload["params"] = payload["params"].copy()
                actual_payload["params"]["password"] = self.password

                response = await client.post(f"{self.base_url}", json=actual_payload)

                logger.debug(f"Auth Response Status: {response.status_code}")
                logger.debug(f"Auth Response Headers: {dict(response.headers)}")

                if response.status_code == 200:
                    data = response.json()
                    logger.debug(f"Auth Response Data: {data}")

                    if "result" in data:
                        self.session_id = data["result"]["sessionId"]
                        self.person_id = data["result"]["personId"]
                        logger.info(
                            f"✅ Authentifizierung erfolgreich (PersonID: {self.person_id})"
                        )
                        return True
                    elif "error" in data:
                        logger.error(f"❌ WebUntis API Error: {data['error']}")
                        return False

                logger.error(
                    f"❌ Authentifizierung fehlgeschlagen (Status: {response.status_code})"
                )
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
                    "jsonrpc": "2.0",
                }

                response = await client.post(
                    f"{self.base_url}",
                    json=payload,
                    cookies={"JSESSIONID": self.session_id},
                )

                logger.debug(f"Logout Response Status: {response.status_code}")
                self.session_id = None

                if response.status_code == 200:
                    logger.info("✅ Logout erfolgreich")
                    return True
                else:
                    logger.warning(
                        f"⚠️ Logout fehlgeschlagen (Status: {response.status_code})"
                    )
                    return False

        except Exception as e:
            logger.error(f"❌ WebUntis Logout Exception: {e}", exc_info=True)
            return False

    async def _call_api(
        self, method: str, params: Dict = None, handle_session_expiration: bool = True
    ) -> Optional[Dict]:
        """
        Generic WebUntis JSON-RPC API call

        Args:
            method: API method name (e.g., "getTeachers")
            params: Method parameters
            handle_session_expiration: Auto-retry on expired session

        Returns:
            API response data or None on error
        """
        if params is None:
            params = {}

        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "id": method,
                    "method": method,
                    "params": params,
                    "jsonrpc": "2.0",
                }

                logger.debug(f"{method} Request: {payload}")

                response = await client.post(
                    f"{self.base_url}",
                    json=payload,
                    cookies={"JSESSIONID": self.session_id},
                )

                logger.debug(f"{method} Response Status: {response.status_code}")

                if response.status_code == 200:
                    data = response.json()

                    # Check for session expiration
                    if (
                        handle_session_expiration
                        and "error" in data
                        and data["error"].get("code") == -8520
                    ):
                        logger.warning(
                            "⚠️ WebUntis Session abgelaufen, authentifiziere neu..."
                        )
                        if await self._handle_expired_session():
                            # Retry the call with new session
                            return await self._call_api(
                                method, params, handle_session_expiration=False
                            )
                        else:
                            logger.error("❌ Re-Authentifizierung fehlgeschlagen")
                            return None

                    if "result" in data:
                        return data["result"]
                    elif "error" in data:
                        logger.error(
                            f"❌ WebUntis API Error in {method}: {data['error']}"
                        )
                        return None

                logger.error(
                    f"❌ {method} fehlgeschlagen (Status: {response.status_code})"
                )
                logger.error(f"Response: {response.text}")
                return None

        except Exception as e:
            logger.error(f"❌ WebUntis {method} Exception: {e}", exc_info=True)
            return None

    async def _handle_expired_session(self) -> bool:
        """
        Centralized session expiration handler
        Clears session and re-authenticates

        Returns:
            True if re-authentication successful, False otherwise
        """
        logger.warning("🔄 Handling expired session...")
        self.session_id = None
        return await self.authenticate()

    async def get_teachers(self) -> List[Dict]:
        """
        Get list of all teachers

        Returns:
            List of teacher dictionaries with id, name, etc.
        """
        logger.info("🔍 Lade Lehrer-Stammdaten...")
        result = await self._call_api("getTeachers")
        if result is not None:
            logger.info(f"✅ {len(result)} Lehrer geladen")
            return result
        return []

    async def get_timetable(
        self, teacher_id: int, start_date: int, end_date: int
    ) -> List[Dict]:
        """
        Get timetable for a teacher

        Args:
            teacher_id: Teacher ID from WebUntis
            start_date: Start date (YYYYMMDD format as integer)
            end_date: End date (YYYYMMDD format as integer)

        Returns:
            List of lesson entries
        """
        logger.info(
            f"📚 Lade Stundenplan für Lehrer-ID {teacher_id} ({start_date} - {end_date})..."
        )

        params = {
            "options": {
                "element": {"id": teacher_id, "type": 2},  # 2 = teacher
                "startDate": start_date,
                "endDate": end_date,
                "showSubstText": True,
                "showInfo": True,
                "showLsText": True,
            }
        }

        result = await self._call_api("getTimetable", params)
        if result is not None:
            logger.info(f"✅ {len(result)} Stundeneinträge erhalten")
            return result
        return []

    async def get_subjects(self) -> List[Dict]:
        """
        Get list of all subjects

        Returns:
            List of subject dictionaries with id, name, longName, etc.
        """
        logger.info("📚 Lade Fächer-Stammdaten...")
        result = await self._call_api("getSubjects")
        if result is not None:
            logger.info(f"✅ {len(result)} Fächer geladen")
            return result
        return []

    async def get_classes(self) -> List[Dict]:
        """
        Get list of all classes

        Returns:
            List of class dictionaries with id, name, longName, etc.
        """
        logger.info("🎓 Lade Klassen-Stammdaten...")
        result = await self._call_api("getKlassen")
        if result is not None:
            logger.info(f"✅ {len(result)} Klassen geladen")
            return result
        return []

    async def get_rooms(self) -> List[Dict]:
        """
        Get list of all rooms

        Returns:
            List of room dictionaries with id, name, longName, etc.
        """
        logger.info("🏫 Lade Raum-Stammdaten...")
        result = await self._call_api("getRooms")
        if result is not None:
            logger.info(f"✅ {len(result)} Räume geladen")
            return result
        return []

    async def get_timegrid(self) -> List[Dict]:
        """
        Get timegrid (lesson period schedule)

        Returns:
            List of timegrid entries with day and timeUnits
        """
        logger.info("⏰ Lade Stundenraster (Timegrid)...")
        result = await self._call_api("getTimegridUnits")
        if result is not None:
            logger.info("✅ Stundenraster geladen")
            return result
        return []

    async def find_teacher_id(self, username: str) -> Optional[int]:
        """
        Find teacher ID by username

        Args:
            username: Teacher username to search for

        Returns:
            Teacher ID or None if not found
        """
        logger.info(f"🔍 Suche Teacher ID für Username: {username}")

        teachers = await self.get_teachers()
        if not teachers:
            return None

        # Log all teacher names for debugging
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
