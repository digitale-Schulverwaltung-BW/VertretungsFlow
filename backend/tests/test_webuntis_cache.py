"""
Unit tests for services/webuntis/cache.py

WebUntisCache – 3-layer cache manager:
- convert_jsonb_keys()  - String → Int key conversion (JSONB PostgreSQL)
- get_or_fetch()        - memory → DB → API fallback chain (8 paths)
- clear_memory_cache()  - sets all 4 in-memory caches to None
- clear_db_cache()      - deletes DB entries + commit
- clear_all_caches()    - calls both clear methods
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

from app.services.webuntis.cache import WebUntisCache
from app.core.config import settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_db(db_entry=None) -> Mock:
    """DB mock: query → filter → first chain."""
    db = Mock()
    q = Mock()
    q.filter.return_value = q
    q.first.return_value = db_entry
    db.query.return_value = q
    return db


# ---------------------------------------------------------------------------
# TestConvertJsonbKeys
# ---------------------------------------------------------------------------


class TestConvertJsonbKeys:
    def test_numeric_string_keys_converted_to_int(self):
        data = {"1": "Mathe", "42": "Englisch"}
        result = WebUntisCache.convert_jsonb_keys(data)
        assert result == {1: "Mathe", 42: "Englisch"}

    def test_non_numeric_keys_preserved_as_string(self):
        data = {"abc": "value", "xyz": 123}
        result = WebUntisCache.convert_jsonb_keys(data)
        assert result == {"abc": "value", "xyz": 123}

    def test_mixed_keys_handled_correctly(self):
        data = {"1": "num", "name": "str"}
        result = WebUntisCache.convert_jsonb_keys(data)
        assert result[1] == "num"
        assert result["name"] == "str"

    def test_empty_dict_returns_empty_dict(self):
        assert WebUntisCache.convert_jsonb_keys({}) == {}


# ---------------------------------------------------------------------------
# TestGetOrFetch
# ---------------------------------------------------------------------------


class TestGetOrFetch:
    @pytest.mark.asyncio
    async def test_cache_disabled_calls_fetch_directly(self):
        """If WEBUNTIS_CACHE_ENABLED=False, fetch_func is called immediately."""
        cache = WebUntisCache()
        db = Mock()
        expected = {"raw": "data"}
        fetch = AsyncMock(return_value=expected)

        with patch.object(settings, "WEBUNTIS_CACHE_ENABLED", False):
            result = await cache.get_or_fetch(
                db=db,
                cache_key="test:key",
                memory_cache_attr="_subjects_cache",
                fetch_func=fetch,
            )

        fetch.assert_called_once()
        assert result is expected
        db.query.assert_not_called()

    @pytest.mark.asyncio
    async def test_memory_cache_hit_returns_without_db_or_api(self):
        """Pre-populated memory cache → no DB query, no API call."""
        cache = WebUntisCache()
        cache._subjects_cache = {1: "Mathe", 2: "Englisch"}
        db = Mock()
        fetch = AsyncMock()

        with patch.object(settings, "WEBUNTIS_CACHE_ENABLED", True):
            result = await cache.get_or_fetch(
                db=db,
                cache_key="webuntis:subjects",
                memory_cache_attr="_subjects_cache",
                fetch_func=fetch,
            )

        fetch.assert_not_called()
        db.query.assert_not_called()
        assert result == {1: "Mathe", 2: "Englisch"}

    @pytest.mark.asyncio
    async def test_force_refresh_bypasses_memory_and_db_cache(self):
        """force_refresh=True skips memory cache, fetches from API."""
        cache = WebUntisCache()
        cache._subjects_cache = {1: "stale data"}
        db = Mock()
        db.query.return_value = Mock()
        fresh = {2: "fresh data"}
        fetch = AsyncMock(return_value=fresh)

        with patch.object(settings, "WEBUNTIS_CACHE_ENABLED", True):
            with patch.object(settings, "WEBUNTIS_CACHE_TTL_HOURS", 24):
                result = await cache.get_or_fetch(
                    db=db,
                    cache_key="webuntis:subjects",
                    memory_cache_attr="_subjects_cache",
                    fetch_func=fetch,
                    force_refresh=True,
                )

        fetch.assert_called_once()
        assert result is fresh

    @pytest.mark.asyncio
    async def test_db_cache_hit_not_expired_returns_converted_data(self):
        """Valid DB entry → convert keys, store in memory, return."""
        cache = WebUntisCache()
        db_entry = Mock()
        db_entry.cache_data = {"1": "Mathe", "2": "Englisch"}
        db_entry.expires_at = datetime.utcnow() + timedelta(hours=1)
        db = make_db(db_entry=db_entry)
        fetch = AsyncMock()

        with patch.object(settings, "WEBUNTIS_CACHE_ENABLED", True):
            result = await cache.get_or_fetch(
                db=db,
                cache_key="webuntis:subjects",
                memory_cache_attr="_subjects_cache",
                fetch_func=fetch,
            )

        fetch.assert_not_called()
        assert result == {1: "Mathe", 2: "Englisch"}
        assert cache._subjects_cache == {1: "Mathe", 2: "Englisch"}

    @pytest.mark.asyncio
    async def test_db_cache_no_expiry_treated_as_valid(self):
        """expires_at=None means never expires → use DB cache."""
        cache = WebUntisCache()
        db_entry = Mock()
        db_entry.cache_data = {"5": "Sport"}
        db_entry.expires_at = None
        db = make_db(db_entry=db_entry)
        fetch = AsyncMock()

        with patch.object(settings, "WEBUNTIS_CACHE_ENABLED", True):
            result = await cache.get_or_fetch(
                db=db,
                cache_key="webuntis:subjects",
                memory_cache_attr="_subjects_cache",
                fetch_func=fetch,
            )

        fetch.assert_not_called()
        assert result == {5: "Sport"}

    @pytest.mark.asyncio
    async def test_expired_db_entry_triggers_api_fetch_and_updates_entry(self):
        """Expired DB entry → fetch from API, update existing DB row."""
        cache = WebUntisCache()
        db_entry = Mock()
        db_entry.cache_data = {"old": "data"}
        db_entry.expires_at = datetime.utcnow() - timedelta(hours=1)
        db = make_db(db_entry=db_entry)
        fresh = {"new": "data"}
        fetch = AsyncMock(return_value=fresh)

        with patch.object(settings, "WEBUNTIS_CACHE_ENABLED", True):
            with patch.object(settings, "WEBUNTIS_CACHE_TTL_HOURS", 24):
                result = await cache.get_or_fetch(
                    db=db,
                    cache_key="webuntis:subjects",
                    memory_cache_attr="_subjects_cache",
                    fetch_func=fetch,
                )

        fetch.assert_called_once()
        assert result is fresh
        assert db_entry.cache_data is fresh  # existing row updated
        db.add.assert_not_called()  # no new row added
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_db_cache_miss_adds_new_entry_and_commits(self):
        """No DB entry at all → fetch, create new DB row, commit."""
        cache = WebUntisCache()
        db = make_db(db_entry=None)
        fresh = {1: "Mathe"}
        fetch = AsyncMock(return_value=fresh)

        with patch.object(settings, "WEBUNTIS_CACHE_ENABLED", True):
            with patch.object(settings, "WEBUNTIS_CACHE_TTL_HOURS", 24):
                result = await cache.get_or_fetch(
                    db=db,
                    cache_key="webuntis:subjects",
                    memory_cache_attr="_subjects_cache",
                    fetch_func=fetch,
                )

        db.add.assert_called_once()
        db.commit.assert_called_once()
        assert result is fresh

    @pytest.mark.asyncio
    async def test_api_fetch_result_stored_in_memory_cache(self):
        """After API fetch, result is stored in the memory cache attr."""
        cache = WebUntisCache()
        db = make_db(db_entry=None)
        fresh = {42: "Kunst"}
        fetch = AsyncMock(return_value=fresh)

        with patch.object(settings, "WEBUNTIS_CACHE_ENABLED", True):
            with patch.object(settings, "WEBUNTIS_CACHE_TTL_HOURS", 24):
                await cache.get_or_fetch(
                    db=db,
                    cache_key="webuntis:subjects",
                    memory_cache_attr="_subjects_cache",
                    fetch_func=fetch,
                )

        assert cache._subjects_cache is fresh


# ---------------------------------------------------------------------------
# TestClearMemoryCache
# ---------------------------------------------------------------------------


class TestClearMemoryCache:
    def test_sets_all_four_caches_to_none(self):
        cache = WebUntisCache()
        cache._subjects_cache = {1: "a"}
        cache._classes_cache = {2: "b"}
        cache._rooms_cache = {3: "c"}
        cache._timegrid_cache = {4: "d"}

        cache.clear_memory_cache()

        assert cache._subjects_cache is None
        assert cache._classes_cache is None
        assert cache._rooms_cache is None
        assert cache._timegrid_cache is None


# ---------------------------------------------------------------------------
# TestClearDbCache
# ---------------------------------------------------------------------------


class TestClearDbCache:
    @pytest.mark.asyncio
    async def test_deletes_all_entries_and_commits(self):
        cache = WebUntisCache()
        db = Mock()
        db.query.return_value = Mock()

        await cache.clear_db_cache(db)

        db.query.return_value.delete.assert_called_once()
        db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# TestClearAllCaches
# ---------------------------------------------------------------------------


class TestClearAllCaches:
    @pytest.mark.asyncio
    async def test_clears_memory_and_db_caches(self):
        cache = WebUntisCache()
        cache._subjects_cache = {1: "populated"}
        db = Mock()
        db.query.return_value = Mock()

        await cache.clear_all_caches(db)

        assert cache._subjects_cache is None  # memory cleared
        db.commit.assert_called_once()  # DB cleared
