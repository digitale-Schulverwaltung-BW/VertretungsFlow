"""
WebUntis Data Loader
Master data loading with generic patterns and caching
"""

import logging
from typing import Dict, Callable
from sqlalchemy.orm import Session

from app.services.webuntis.client import WebUntisAPIClient
from app.services.webuntis.cache import WebUntisCache

logger = logging.getLogger(__name__)


class WebUntisDataLoader:
    """
    Loads and caches WebUntis master data (subjects, classes, rooms, timegrid)
    Uses generic pattern to eliminate duplication
    """

    def __init__(self, client: WebUntisAPIClient, cache: WebUntisCache):
        """
        Initialize data loader

        Args:
            client: WebUntis API client for fetching data
            cache: Cache manager for 3-layer caching
        """
        self.client = client
        self.cache = cache

    async def _load_master_data(
        self,
        db: Session,
        cache_key: str,
        memory_cache_attr: str,
        api_method: Callable,
        transform_func: Callable[[list], Dict],
        force_refresh: bool = False,
    ) -> Dict:
        """
        Generic master data loader - eliminates duplication across 4 load methods

        Args:
            db: Database session
            cache_key: Cache key (e.g., 'webuntis:subjects')
            memory_cache_attr: Memory cache attribute name (e.g., '_subjects_cache')
            api_method: Client method to call (e.g., client.get_subjects)
            transform_func: Function to transform raw API data to dict
            force_refresh: Force API call even if cache exists

        Returns:
            Dictionary with transformed master data
        """

        async def fetch_from_api():
            # Call client API method
            raw_data = await api_method()
            if not raw_data:
                logger.warning(f"No data returned from API for {cache_key}")
                return {}
            # Transform raw data to desired format
            return transform_func(raw_data)

        return await self.cache.get_or_fetch(
            db=db,
            cache_key=cache_key,
            memory_cache_attr=memory_cache_attr,
            fetch_func=fetch_from_api,
            force_refresh=force_refresh,
        )

    async def load_subjects(self, db: Session, force_refresh: bool = False) -> Dict:
        """
        Lädt Fächer-Stammdaten und erstellt ID->Name Mapping

        Args:
            db: Database session
            force_refresh: Force API call even if cache exists

        Returns:
            Dictionary mit subject_id -> subject_name
        """

        def transform_subjects(subjects: list) -> Dict:
            # Verwende Kurzname (name) statt Langname (longName) wegen sehr langer Fachnamen
            return {
                subj["id"]: subj.get("name", subj.get("longName", "Unbekannt"))
                for subj in subjects
            }

        return await self._load_master_data(
            db=db,
            cache_key="webuntis:subjects",
            memory_cache_attr="_subjects_cache",
            api_method=self.client.get_subjects,
            transform_func=transform_subjects,
            force_refresh=force_refresh,
        )

    async def load_classes(self, db: Session, force_refresh: bool = False) -> Dict:
        """
        Lädt Klassen-Stammdaten und erstellt ID->Name Mapping

        Args:
            db: Database session
            force_refresh: Force API call even if cache exists

        Returns:
            Dictionary mit class_id -> class_name
        """

        def transform_classes(classes: list) -> Dict:
            # Verwende Kurzname (name) statt Langname (longName)
            return {
                kl["id"]: kl.get("name", kl.get("longName", "Unbekannt"))
                for kl in classes
            }

        return await self._load_master_data(
            db=db,
            cache_key="webuntis:classes",
            memory_cache_attr="_classes_cache",
            api_method=self.client.get_classes,
            transform_func=transform_classes,
            force_refresh=force_refresh,
        )

    async def load_rooms(self, db: Session, force_refresh: bool = False) -> Dict:
        """
        Lädt Raum-Stammdaten und erstellt ID->Name Mapping

        Args:
            db: Database session
            force_refresh: Force API call even if cache exists

        Returns:
            Dictionary mit room_id -> room_name
        """

        def transform_rooms(rooms: list) -> Dict:
            # Verwende Kurzname (name) statt Langname (longName)
            return {
                room["id"]: room.get("name", room.get("longName", "Unbekannt"))
                for room in rooms
            }

        return await self._load_master_data(
            db=db,
            cache_key="webuntis:rooms",
            memory_cache_attr="_rooms_cache",
            api_method=self.client.get_rooms,
            transform_func=transform_rooms,
            force_refresh=force_refresh,
        )

    async def load_timegrid(self, db: Session, force_refresh: bool = False) -> Dict:
        """
        Lädt Stundenraster (Timegrid) und erstellt startTime->period Mapping
        PUBLIC METHOD - used by pdf_service.py

        Args:
            db: Database session
            force_refresh: Force API call even if cache exists

        Returns:
            Dictionary mit startTime -> period_number
        """

        def transform_timegrid(timegrid_raw: list) -> Dict:
            """
            Transform timegrid from WebUntis format to startTime -> period mapping

            WebUntis format: [
                {day: 2, timeUnits: [{name: "1", startTime: 730, ...}, {name: "2", startTime: 820, ...}]}
            ]

            Output: {730: 1, 820: 2, ...}
            """
            timegrid = {}
            for day_entry in timegrid_raw:
                time_units = day_entry.get("timeUnits", [])
                for unit in time_units:
                    start_time = unit.get("startTime")
                    period_name = unit.get("name", "")

                    if start_time:
                        try:
                            # Period name is usually "1", "2", etc.
                            period_number = int(period_name)
                            timegrid[start_time] = period_number
                        except (ValueError, TypeError):
                            logger.warning(
                                f"Could not parse period number from: {period_name}"
                            )
                            # Fallback: use startTime // 100 as approximation
                            timegrid[start_time] = start_time // 100

            logger.info(f"✅ Timegrid erstellt mit {len(timegrid)} Zeitslots")
            return timegrid

        return await self._load_master_data(
            db=db,
            cache_key="webuntis:timegrid",
            memory_cache_attr="_timegrid_cache",
            api_method=self.client.get_timegrid,
            transform_func=transform_timegrid,
            force_refresh=force_refresh,
        )
