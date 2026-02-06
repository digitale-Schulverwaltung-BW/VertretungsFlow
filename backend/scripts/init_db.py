#!/usr/bin/env python3
"""
Database initialization script
Creates all tables and optionally seeds initial data
"""
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.append(str(Path(__file__).parent.parent))

from app.core.database import engine, Base
from app.models import (
    User,
    Absence,
    AffectedLesson,
    Notification,
    AbsenceAttachment,
    WebUntisCache,
)


def init_db():
    """Initialize database by creating all tables"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")


if __name__ == "__main__":
    init_db()
