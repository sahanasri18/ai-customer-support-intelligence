"""
SQLAlchemy ORM models for the Customer Support Intelligence Platform.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey,
    Enum, Boolean, Float, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from database import Base
import enum


class RoleEnum(str, enum.Enum):
    admin = "admin"
    agent = "agent"


class TicketStatusEnum(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"


class PriorityEnum(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class SentimentEnum(str, enum.Enum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"


# ---------------------------------------------------------------------------
# User & Role
# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(RoleEnum), default=RoleEnum.agent, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tickets = relationship("Ticket", back_populates="created_by_user", foreign_keys="[Ticket.created_by]")
    assigned_tickets = relationship("Ticket", back_populates="assigned_to_user", foreign_keys="[Ticket.assigned_to]")
    audit_logs = relationship("AuditLog", back_populates="user")


# ---------------------------------------------------------------------------
# Ticket
# ---------------------------------------------------------------------------
class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        Index("ix_tickets_status", "status"),
        Index("ix_tickets_priority", "priority"),
        Index("ix_tickets_created_at", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    ticket_number = Column(String(20), unique=True, nullable=False, index=True)
    subject = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(Enum(TicketStatusEnum), default=TicketStatusEnum.open, nullable=False)
    priority = Column(Enum(PriorityEnum), nullable=True)
    category = Column(String(100), nullable=True)
    customer_name = Column(String(255), nullable=True)
    customer_email = Column(String(255), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_urgent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    created_by_user = relationship("User", back_populates="tickets", foreign_keys=[created_by])
    assigned_to_user = relationship("User", back_populates="assigned_tickets", foreign_keys=[assigned_to])
    predictions = relationship("TicketPrediction", back_populates="ticket", uselist=False, cascade="all, delete-orphan")
    status_history = relationship("TicketStatusHistory", back_populates="ticket", cascade="all, delete-orphan", order_by="TicketStatusHistory.changed_at")
    audit_logs = relationship("AuditLog", back_populates="ticket")


# ---------------------------------------------------------------------------
# Ticket Prediction
# ---------------------------------------------------------------------------
class TicketPrediction(Base):
    __tablename__ = "ticket_predictions"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), unique=True, nullable=False)
    predicted_category = Column(String(100), nullable=True)
    category_confidence = Column(Float, nullable=True)
    predicted_priority = Column(String(50), nullable=True)
    priority_confidence = Column(Float, nullable=True)
    predicted_sentiment = Column(Enum(SentimentEnum), nullable=True)
    sentiment_confidence = Column(Float, nullable=True)
    is_urgent_rule_based = Column(Boolean, default=False)
    model_version = Column(String(50), nullable=True)
    predicted_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    ticket = relationship("Ticket", back_populates="predictions")


# ---------------------------------------------------------------------------
# Ticket Status History
# ---------------------------------------------------------------------------
class TicketStatusHistory(Base):
    __tablename__ = "ticket_status_history"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    old_status = Column(Enum(TicketStatusEnum), nullable=True)
    new_status = Column(Enum(TicketStatusEnum), nullable=False)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    comment = Column(Text, nullable=True)
    changed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    ticket = relationship("Ticket", back_populates="status_history")
    changed_by_user = relationship("User")


# ---------------------------------------------------------------------------
# Audit Log
# ---------------------------------------------------------------------------
class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_created_at", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="audit_logs")
    ticket = relationship("Ticket", back_populates="audit_logs")
