"""
Call model for AURA voice interaction system.

This module defines the Call session model for Twilio voice interactions.
"""

import uuid
from datetime import datetime
from typing import Dict, Any

from sqlalchemy import Column, String, DateTime, Enum, UniqueConstraint, Index, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from config.db import Base
from app.models.types import GUID
from app.models.enums import CallStatusEnum


class Call(Base):
    """
    Represents a phone call session via Twilio.

    Stores call information including caller details, Twilio session data,
    and call status.
    """
    __tablename__ = "calls"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    caller_number = Column(String(50), nullable=True)  # From Twilio "From"
    twilio_sid = Column(String(100), unique=True, nullable=False)  # Unique Twilio call SID
    language = Column(String(10), nullable=True)  # Detected language
    location = Column(String(255), nullable=True)  # From Twilio if available
    status = Column(Enum(CallStatusEnum), nullable=False, default=CallStatusEnum.ACTIVE)
    duration = Column(String(50), nullable=True)  # Call duration
    recording_url = Column(String(500), nullable=True)  # Recording URL if available
    metadata_ = Column(JSON, nullable=True, default=dict)  # Twilio payload, etc.
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    # TODO: Enable when Query model is enhanced with call_id foreign key
    # queries = relationship("Query", back_populates="call", cascade="all, delete-orphan", foreign_keys="Query.call_id")

    # Indexes and constraints
    __table_args__ = (
        Index("idx_call_created_at", "created_at"),
        Index("idx_call_language", "language"),
        Index("idx_call_status", "status"),
        Index("idx_call_caller_number", "caller_number"),
        UniqueConstraint("twilio_sid", name="uq_twilio_sid"),
    )

    def __repr__(self) -> str:
        return f"<Call(id={self.id}, caller={self.caller_number}, status={self.status})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for API responses."""
        return {
            "id": str(self.id),
            "caller_number": self.caller_number,
            "twilio_sid": self.twilio_sid,
            "language": self.language,
            "location": self.location,
            "status": self.status.value if self.status else None,
            "duration": self.duration,
            "recording_url": self.recording_url,
            "metadata": self.metadata_ or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
