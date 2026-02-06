"""
Time Formatting Utilities
Pure functions for WebUntis time format conversions and period calculations
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from app.models.models import AffectedLesson

logger = logging.getLogger(__name__)


def format_webuntis_time(webuntis_time: int) -> str:
    """
    Convert WebUntis time format to HH:MM

    Args:
        webuntis_time: WebUntis time (e.g., 730 = 07:30, 815 = 08:15)

    Returns:
        Time string in format "HH:MM"

    Example:
        >>> format_webuntis_time(730)
        "07:30"
        >>> format_webuntis_time(1545)
        "15:45"
    """
    hours = webuntis_time // 100
    minutes = webuntis_time % 100
    return f"{hours:02d}:{minutes:02d}"


def _calculate_end_time(start_time: int) -> str:
    """
    Calculate end time by adding 45 minutes to start time

    Args:
        start_time: WebUntis start time (e.g., 730 = 07:30)

    Returns:
        End time in format "HH:MM"
    """
    hours = start_time // 100
    minutes = start_time % 100
    end_minutes = minutes + 45
    end_hours = hours
    if end_minutes >= 60:
        end_minutes -= 60
        end_hours += 1
    return f"{end_hours:02d}:{end_minutes:02d}"


def _load_time_from_config(
    config_path: Path,
    period: int,
    time_type: str,
) -> Optional[str]:
    """
    Load period time from config file fallback

    Args:
        config_path: Path to PDF config JSON
        period: Period number
        time_type: "start" or "end"

    Returns:
        Time string or None if config load fails
    """
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        if time_type == "end":
            period_mapping = config.get("period_end_time_mapping", {})
        else:
            period_mapping = config.get("period_time_mapping", {})

        return period_mapping.get(str(period))
    except Exception as e:
        logger.error(f"Error loading config for fallback: {e}")
        return None


def get_time_from_period(
    timegrid: Dict[int, int],
    period: int,
    time_type: str,
    config_path: Optional[Path] = None,
) -> str:
    """
    Reverse lookup: Find time for a given period from timegrid

    Args:
        timegrid: Timegrid dict from WebUntis ({start_time -> period})
        period: Period number (1-16)
        time_type: "start" or "end"
        config_path: Path to PDF config (for fallback mappings)

    Returns:
        Time string in format "HH:MM"
    """
    # Try timegrid lookup first
    for start_time, p in timegrid.items():
        # Handle both int and str keys (JSONB conversion)
        try:
            p_int = int(p)
        except (ValueError, TypeError):
            continue

        if p_int == period:
            if time_type == "start":
                return format_webuntis_time(start_time)
            else:
                return _calculate_end_time(start_time)

    # Timegrid lookup failed - try config fallback
    logger.warning(
        f"Period {period} nicht im WebUntis Timegrid gefunden, nutze Config Fallback"
    )

    if config_path and config_path.exists():
        time_from_config = _load_time_from_config(config_path, period, time_type)
        if time_from_config:
            return time_from_config

    # Ultimate fallback
    return "15:45" if time_type == "end" else "08:00"


def get_time_for_period(
    lessons: List[AffectedLesson],
    period: int,
    time_type: str,
    timegrid: Dict[int, int],
    config_path: Optional[Path] = None,
) -> str:
    """
    Get time for a specific period, preferring WebUntis lesson data over timegrid

    Args:
        lessons: List of affected lessons
        period: Period number (1-16)
        time_type: "start" or "end"
        timegrid: Timegrid dict from WebUntis ({start_time -> period})
        config_path: Path to PDF config (for fallback mappings)

    Returns:
        Time string in format "HH:MM"
    """
    # Try to find a lesson with the given period that has time data
    for lesson in lessons:
        if lesson.period == period:
            if time_type == "start" and lesson.start_time:
                return format_webuntis_time(lesson.start_time)
            elif time_type == "end" and lesson.end_time:
                return format_webuntis_time(lesson.end_time)

    # Fallback to timegrid reverse lookup
    return get_time_from_period(timegrid, period, time_type, config_path)
