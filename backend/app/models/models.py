"""
SQLAlchemy Database Models für AbsenzFlow
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class UserRole(str, enum.Enum):
    """Benutzerrollen"""
    TEACHER = "teacher"           # Lehrkraft
    DEPARTMENT_HEAD = "dept_head" # Abteilungsleiter
    PLANNER = "planner"           # Vertretungsplaner
    ADMIN = "admin"               # Administrator


class AbsenceStatus(str, enum.Enum):
    """Status einer Abwesenheit"""
    DRAFT = "draft"               # Entwurf
    SUBMITTED = "submitted"       # Eingereicht
    APPROVED = "approved"         # Genehmigt
    COMPLETED = "completed"       # Eingetragen/Erledigt
    REJECTED = "rejected"         # Abgelehnt


class User(Base):
    """
    Benutzer-Modell
    Speichert zusätzliche Informationen zu LDAP-Benutzern
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True)
    full_name = Column(String(255))
    role = Column(Enum(UserRole), default=UserRole.TEACHER)
    webuntis_teacher_code = Column(String(20), nullable=True, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    absences = relationship("Absence", back_populates="teacher", foreign_keys="Absence.teacher_id")
    approvals = relationship("Absence", back_populates="approved_by_user", foreign_keys="Absence.approved_by")


class Absence(Base):
    """
    Abwesenheits-Modell
    Haupttabelle für Abwesenheitsmeldungen
    """
    __tablename__ = "absences"
    
    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Abwesenheitsdetails
    reason = Column(String(100), nullable=False)  # z.B. "Fortbildung", "Krankheit"
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    start_period = Column(Integer, nullable=False)  # Startstunde (1-10)
    end_period = Column(Integer, nullable=False)    # Endstunde (1-10)
    
    # Status & Workflow
    status = Column(Enum(AbsenceStatus), default=AbsenceStatus.SUBMITTED)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    teacher = relationship("User", back_populates="absences", foreign_keys=[teacher_id])
    approved_by_user = relationship("User", back_populates="approvals", foreign_keys=[approved_by])
    affected_lessons = relationship("AffectedLesson", back_populates="absence", cascade="all, delete-orphan")


class AffectedLesson(Base):
    """
    Betroffene Stunden
    Speichert Details zu einzelnen Stunden, die durch eine Abwesenheit ausfallen
    """
    __tablename__ = "affected_lessons"
    
    id = Column(Integer, primary_key=True, index=True)
    absence_id = Column(Integer, ForeignKey("absences.id"), nullable=False)
    
    # Stundendetails (aus WebUntis)
    date = Column(DateTime, nullable=False)
    period = Column(Integer, nullable=False)  # Start-Stundennummer (1-10)
    end_period = Column(Integer, nullable=True)  # End-Stundennummer (für Doppelstunden)
    subject = Column(String(100))
    class_name = Column(String(50))
    room = Column(String(50))
    
    # Vertretungshinweise
    notes = Column(Text)  # Hinweise für Vertretungsplaner
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    absence = relationship("Absence", back_populates="affected_lessons")


class Notification(Base):
    """
    Benachrichtigungen
    Tracking von versendeten E-Mails
    """
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    absence_id = Column(Integer, ForeignKey("absences.id"), nullable=True)
    
    # Notification Details
    notification_type = Column(String(50))  # z.B. "absence_submitted", "absence_approved"
    subject = Column(String(255))
    body = Column(Text)
    
    # Status
    sent = Column(Boolean, default=False)
    sent_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
