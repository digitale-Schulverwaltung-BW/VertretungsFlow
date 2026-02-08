"""
WebUntis Cache
3-layer caching infrastructure (memory → DB → API)
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Callable, Optional, Any
from sqlalchemy.orm import Session

from app.core.config import settings

logger = logging.getLogger(__name__)


class WebUntisCache:
    """
    3-layer cache manager for WebUntis data
    Layer 1: In-memory cache (fast, volatile)
    Layer 2: Database cache (persistent, with TTL)
    Layer 3: API fetch (fallback)
    """

    def __init__(self):
        """Initialize cache with empty memory caches"""
        self._subjects_cache: Optional[Dict] = None
        self._classes_cache: Optional[Dict] = None
        self._rooms_cache: Optional[Dict] = None
        self._timegrid_cache: Optional[Dict] = None

    @staticmethod
    def convert_jsonb_keys(data: Dict) -> Dict:
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

    async def get_or_fetch(
        self,
        db: Session,
        cache_key: str,
        memory_cache_attr: str,
        fetch_func: Callable,
        force_refresh: bool = False,
    ) -> Dict:
        """
        Generische Cache-Lookup-Methode mit 3-Layer-Cache

        Args:
            db: Database session
            cache_key: Cache key (z.B. 'webuntis:subjects')
            memory_cache_attr: Attribute name for memory cache (e.g., '_subjects_cache')
            fetch_func: Async function to fetch from API if cache miss
            force_refresh: Force API call even if cache exists

        Returns:
            Cached or fresh data as dict
        """
        from app.models.models import WebUntisCache as WebUnitisCacheModel

        if not settings.WEBUNTIS_CACHE_ENABLED:
            return await fetch_func()

        # Layer 1: In-Memory Cache
        if not force_refresh and getattr(self, memory_cache_attr, None):
            logger.info(f"WebUntis cache hit (memory): {cache_key}")
            return getattr(self, memory_cache_attr)

        # Layer 2: DB Cache
        if not force_refresh:
            db_entry = (
                db.query(WebUnitisCacheModel)
                .filter(WebUnitisCacheModel.cache_key == cache_key)
                .first()
            )

            if db_entry:
                # Check if expired
                if (
                    db_entry.expires_at is None
                    or db_entry.expires_at > datetime.utcnow()
                ):
                    logger.info(f"WebUntis cache hit (DB): {cache_key}")
                    # JSONB konvertiert numerische Keys zu Strings - zurückkonvertieren
                    cached_data = self.convert_jsonb_keys(db_entry.cache_data)
                    setattr(self, memory_cache_attr, cached_data)
                    return cached_data
                else:
                    logger.info(f"WebUntis cache expired: {cache_key}")

        # Layer 3: Fetch from API
        logger.info(f"WebUntis cache miss, fetching from API: {cache_key}")
        data = await fetch_func()

        # Store in DB
        expires_at = datetime.utcnow() + timedelta(
            hours=settings.WEBUNTIS_CACHE_TTL_HOURS
        )

        db_entry = (
            db.query(WebUnitisCacheModel)
            .filter(WebUnitisCacheModel.cache_key == cache_key)
            .first()
        )

        if db_entry:
            db_entry.cache_data = data
            db_entry.expires_at = expires_at
            db_entry.updated_at = datetime.utcnow()
        else:
            db_entry = WebUnitisCacheModel(
                cache_key=cache_key, cache_data=data, expires_at=expires_at
            )
            db.add(db_entry)

        db.commit()

        # Store in memory
        setattr(self, memory_cache_attr, data)

        return data

    def clear_memory_cache(self) -> None:
        """
        Clears all in-memory caches
        Useful for admin operations or session expiration
        """
        logger.info("🗑️ Clearing WebUntis memory caches")
        self._subjects_cache = None
        self._classes_cache = None
        self._rooms_cache = None
        self._timegrid_cache = None

    async def clear_db_cache(self, db: Session) -> None:
        """
        Clears database cache entries
        Forces fresh API fetch on next request

        Args:
            db: Database session
        """
        from app.models.models import WebUntisCache as WebUnitisCacheModel

        logger.info("🗑️ Clearing WebUntis DB caches")
        db.query(WebUnitisCacheModel).delete()
        db.commit()
        logger.info("✅ DB cache cleared")

    async def clear_all_caches(self, db: Session) -> None:
        """
        Clears both memory and database caches

        Args:
            db: Database session
        """
        self.clear_memory_cache()
        await self.clear_db_cache(db)
