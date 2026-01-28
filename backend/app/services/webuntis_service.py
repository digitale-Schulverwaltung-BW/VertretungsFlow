"""
WebUntis API Service
Integration mit WebUntis für Stundenplan-Abfragen
"""
import httpx
from datetime import datetime, timedelta
from typing import List, Optional
from app.core.config import settings
from app.schemas.schemas import WebUntisLesson


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
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "id": "auth",
                    "method": "authenticate",
                    "params": {
                        "user": self.username,
                        "password": self.password,
                        "client": "AbsenzFlow"
                    },
                    "jsonrpc": "2.0"
                }
                
                response = await client.post(
                    f"{self.base_url}?school={self.school}",
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if "result" in data:
                        self.session_id = data["result"]["sessionId"]
                        self.person_id = data["result"]["personId"]
                        return True
                
                return False
                
        except Exception as e:
            print(f"WebUntis Auth Error: {e}")
            return False
    
    async def logout(self) -> bool:
        """Beendet WebUntis Session"""
        if not self.session_id:
            return True
        
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "id": "logout",
                    "method": "logout",
                    "params": {},
                    "jsonrpc": "2.0"
                }
                
                response = await client.post(
                    f"{self.base_url}?school={self.school}",
                    json=payload,
                    cookies={"JSESSIONID": self.session_id}
                )
                
                self.session_id = None
                return response.status_code == 200
                
        except Exception as e:
            print(f"WebUntis Logout Error: {e}")
            return False
    
    async def get_timetable_for_teacher(
        self,
        teacher_username: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[WebUntisLesson]:
        """
        Holt Stundenplan für Lehrkraft im angegebenen Zeitraum
        
        Args:
            teacher_username: Username der Lehrkraft
            start_date: Startdatum
            end_date: Enddatum
            
        Returns:
            Liste von Stunden
        """
        # Authentifizieren wenn noch keine Session
        if not self.session_id:
            await self.authenticate()
        
        try:
            # Zuerst: Teacher ID finden
            teacher_id = await self._get_teacher_id(teacher_username)
            if not teacher_id:
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
                
                response = await client.post(
                    f"{self.base_url}?school={self.school}",
                    json=payload,
                    cookies={"JSESSIONID": self.session_id}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if "result" in data:
                        return self._parse_timetable(data["result"])
                
                return []
                
        except Exception as e:
            print(f"WebUntis Get Timetable Error: {e}")
            return []
    
    async def _get_teacher_id(self, username: str) -> Optional[int]:
        """
        Findet Teacher ID für Username
        
        Args:
            username: Username der Lehrkraft
            
        Returns:
            Teacher ID oder None
        """
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "id": "getTeachers",
                    "method": "getTeachers",
                    "params": {},
                    "jsonrpc": "2.0"
                }
                
                response = await client.post(
                    f"{self.base_url}?school={self.school}",
                    json=payload,
                    cookies={"JSESSIONID": self.session_id}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if "result" in data:
                        teachers = data["result"]
                        for teacher in teachers:
                            # Annahme: name entspricht username
                            if teacher.get("name", "").lower() == username.lower():
                                return teacher.get("id")
                
                return None
                
        except Exception as e:
            print(f"WebUntis Get Teacher ID Error: {e}")
            return None
    
    def _parse_timetable(self, timetable_data: List[dict]) -> List[WebUntisLesson]:
        """
        Parsed Stundenplan-Daten von WebUntis
        
        Args:
            timetable_data: Rohdaten von WebUntis
            
        Returns:
            Liste von WebUntisLesson Objekten
        """
        lessons = []
        
        for entry in timetable_data:
            try:
                # Datum parsen (Format: YYYYMMDD)
                date_str = str(entry.get("date", ""))
                date = datetime.strptime(date_str, "%Y%m%d")
                
                # Informationen extrahieren
                lesson = WebUntisLesson(
                    date=date,
                    period=entry.get("startTime", 0) // 100,  # Vereinfachte Stundenberechnung
                    subject=self._get_subject_name(entry),
                    class_name=self._get_class_name(entry),
                    room=self._get_room_name(entry)
                )
                
                lessons.append(lesson)
                
            except Exception as e:
                print(f"Parse Lesson Error: {e}")
                continue
        
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
