"""
Unit tests for services/webuntis/data_loader.py

WebUntisDataLoader – generic master data loader:
- load_subjects()   - transform: {id: name} (name preferred, longName fallback)
- load_classes()    - transform: {id: name}
- load_rooms()      - transform: {id: name}
- load_timegrid()   - transform: {startTime: period_number}, fallback for non-numeric

Strategy: WEBUNTIS_CACHE_ENABLED=False → cache.get_or_fetch calls fetch_func()
directly, which applies the transform on the mocked client response.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from app.services.webuntis.cache import WebUntisCache
from app.services.webuntis.data_loader import WebUntisDataLoader
from app.core.config import settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_loader(subjects=None, classes=None, rooms=None, timegrid=None):
    """
    Returns a WebUntisDataLoader with mocked client methods.
    Pass raw API responses as lists.
    """
    mock_client = AsyncMock()
    mock_client.get_subjects = AsyncMock(return_value=subjects or [])
    mock_client.get_classes = AsyncMock(return_value=classes or [])
    mock_client.get_rooms = AsyncMock(return_value=rooms or [])
    mock_client.get_timegrid = AsyncMock(return_value=timegrid or [])
    return WebUntisDataLoader(client=mock_client, cache=WebUntisCache())


# ---------------------------------------------------------------------------
# TestLoadSubjects
# ---------------------------------------------------------------------------


class TestLoadSubjects:
    @pytest.mark.asyncio
    async def test_uses_name_field_over_long_name(self):
        """Transform prefers short name (name) over longName."""
        loader = make_loader(
            subjects=[
                {"id": 1, "name": "Mathe", "longName": "Mathematik"},
                {"id": 2, "name": "Eng", "longName": "Englisch"},
            ]
        )

        with patch.object(settings, "WEBUNTIS_CACHE_ENABLED", False):
            result = await loader.load_subjects(db=Mock())

        assert result == {1: "Mathe", 2: "Eng"}

    @pytest.mark.asyncio
    async def test_falls_back_to_long_name_when_name_missing(self):
        loader = make_loader(subjects=[{"id": 5, "longName": "Physik"}])

        with patch.object(settings, "WEBUNTIS_CACHE_ENABLED", False):
            result = await loader.load_subjects(db=Mock())

        assert result[5] == "Physik"

    @pytest.mark.asyncio
    async def test_falls_back_to_unbekannt_when_both_names_missing(self):
        loader = make_loader(subjects=[{"id": 9}])

        with patch.object(settings, "WEBUNTIS_CACHE_ENABLED", False):
            result = await loader.load_subjects(db=Mock())

        assert result[9] == "Unbekannt"

    @pytest.mark.asyncio
    async def test_empty_api_response_returns_empty_dict(self):
        loader = make_loader(subjects=[])

        with patch.object(settings, "WEBUNTIS_CACHE_ENABLED", False):
            result = await loader.load_subjects(db=Mock())

        assert result == {}

    @pytest.mark.asyncio
    async def test_none_api_response_returns_empty_dict(self):
        """None from API (e.g. connection error) → empty dict, no crash."""
        loader = make_loader()
        loader.client.get_subjects = AsyncMock(return_value=None)

        with patch.object(settings, "WEBUNTIS_CACHE_ENABLED", False):
            result = await loader.load_subjects(db=Mock())

        assert result == {}


# ---------------------------------------------------------------------------
# TestLoadClasses
# ---------------------------------------------------------------------------


class TestLoadClasses:
    @pytest.mark.asyncio
    async def test_transforms_classes_to_id_name_mapping(self):
        loader = make_loader(
            classes=[{"id": 10, "name": "10A"}, {"id": 11, "name": "11B"}]
        )

        with patch.object(settings, "WEBUNTIS_CACHE_ENABLED", False):
            result = await loader.load_classes(db=Mock())

        assert result == {10: "10A", 11: "11B"}

    @pytest.mark.asyncio
    async def test_falls_back_to_long_name_for_classes(self):
        loader = make_loader(classes=[{"id": 7, "longName": "Klasse 7"}])

        with patch.object(settings, "WEBUNTIS_CACHE_ENABLED", False):
            result = await loader.load_classes(db=Mock())

        assert result[7] == "Klasse 7"


# ---------------------------------------------------------------------------
# TestLoadRooms
# ---------------------------------------------------------------------------


class TestLoadRooms:
    @pytest.mark.asyncio
    async def test_transforms_rooms_to_id_name_mapping(self):
        loader = make_loader(
            rooms=[
                {"id": 101, "name": "A101"},
                {"id": 102, "longName": "Turnhalle"},
            ]
        )

        with patch.object(settings, "WEBUNTIS_CACHE_ENABLED", False):
            result = await loader.load_rooms(db=Mock())

        assert result[101] == "A101"
        assert result[102] == "Turnhalle"


# ---------------------------------------------------------------------------
# TestLoadTimegrid
# ---------------------------------------------------------------------------


class TestLoadTimegrid:
    @pytest.mark.asyncio
    async def test_maps_start_time_to_period_number(self):
        """Main happy path: numeric period names → {startTime: period_int}."""
        loader = make_loader(
            timegrid=[
                {
                    "day": 2,
                    "timeUnits": [
                        {"name": "1", "startTime": 730},
                        {"name": "2", "startTime": 820},
                    ],
                }
            ]
        )

        with patch.object(settings, "WEBUNTIS_CACHE_ENABLED", False):
            result = await loader.load_timegrid(db=Mock())

        assert result[730] == 1
        assert result[820] == 2

    @pytest.mark.asyncio
    async def test_non_numeric_period_name_uses_start_time_fallback(self):
        """Non-numeric period name (e.g. 'A') → fallback: startTime // 100."""
        loader = make_loader(
            timegrid=[{"day": 2, "timeUnits": [{"name": "A", "startTime": 730}]}]
        )

        with patch.object(settings, "WEBUNTIS_CACHE_ENABLED", False):
            result = await loader.load_timegrid(db=Mock())

        assert result[730] == 7  # 730 // 100 = 7

    @pytest.mark.asyncio
    async def test_multiple_days_all_time_units_included(self):
        """Time units from all days of the week are merged into one dict."""
        loader = make_loader(
            timegrid=[
                {"day": 2, "timeUnits": [{"name": "1", "startTime": 730}]},
                {"day": 3, "timeUnits": [{"name": "2", "startTime": 820}]},
                {"day": 4, "timeUnits": [{"name": "3", "startTime": 910}]},
            ]
        )

        with patch.object(settings, "WEBUNTIS_CACHE_ENABLED", False):
            result = await loader.load_timegrid(db=Mock())

        assert len(result) == 3
        assert 730 in result
        assert 820 in result
        assert 910 in result

    @pytest.mark.asyncio
    async def test_time_unit_without_start_time_is_skipped(self):
        """Entries with no startTime are silently skipped."""
        loader = make_loader(
            timegrid=[
                {
                    "day": 2,
                    "timeUnits": [
                        {"name": "1"},  # no startTime
                        {"name": "2", "startTime": 820},
                    ],
                }
            ]
        )

        with patch.object(settings, "WEBUNTIS_CACHE_ENABLED", False):
            result = await loader.load_timegrid(db=Mock())

        assert len(result) == 1
        assert 820 in result

    @pytest.mark.asyncio
    async def test_empty_time_units_returns_empty_dict(self):
        loader = make_loader(timegrid=[{"day": 2, "timeUnits": []}])

        with patch.object(settings, "WEBUNTIS_CACHE_ENABLED", False):
            result = await loader.load_timegrid(db=Mock())

        assert result == {}
