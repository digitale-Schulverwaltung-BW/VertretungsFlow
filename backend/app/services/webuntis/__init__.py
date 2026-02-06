"""
WebUntis API Integration
Modular architecture for timetable fetching and master data management

This package provides a clean separation of concerns:
- client.py: Low-level HTTP communication with WebUntis API
- cache.py: 3-layer caching infrastructure (memory → DB → API)
- data_loader.py: Master data loading with generic patterns
- parser.py: Pure parsing and transformation functions
- webuntis_service.py: High-level facade (for backwards compatibility)
"""

from app.services.webuntis.client import WebUntisAPIClient
from app.services.webuntis.cache import WebUntisCache
from app.services.webuntis.data_loader import WebUntisDataLoader
from app.services.webuntis.parser import parse_timetable, merge_consecutive_lessons

# Import from parent module for backwards compatibility
# Users can import from either:
#   from app.services.webuntis_service import webuntis_service  # Old way
#   from app.services.webuntis import WebUntisService           # New way
try:
    from app.services.webuntis_service import WebUntisService, webuntis_service
except ImportError:
    # During initial loading, webuntis_service might not be available yet
    WebUntisService = None
    webuntis_service = None

__all__ = [
    "WebUntisAPIClient",
    "WebUntisCache",
    "WebUntisDataLoader",
    "WebUntisService",
    "webuntis_service",
    "parse_timetable",
    "merge_consecutive_lessons"
]
