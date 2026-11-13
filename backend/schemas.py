"""
Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ---------------------------------------------------------------------------
# Enums (mirroring ORM enums for Pydantic)
# ---------------------------------------------------------------------------
class RoleEnum(str, Enum):
    admin = "admin"
    agent = "agent"


class TicketStatusEnum(str, Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"


class PriorityEnum(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class SentimentEnum(str, Enum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
class UserRegister(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    password: str = Field(..., min_length=12, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    email: str
    full_name: str
    role: RoleEnum


class TokenData(BaseModel):
    user_id: Optional[int] = None
    role: Optional[str] = None


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------
class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: RoleEnum
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    is_active: Optional[bool] = None
    role: Optional[RoleEnum] = None


class PasswordChange(BaseModel):
    current_password: str = Field(..., max_length=128)
    new_password: str = Field(..., min_length=12, max_length=128)


# ---------------------------------------------------------------------------
# Ticket
# ---------------------------------------------------------------------------
class TicketCreate(BaseModel):
    subject: str = Field(..., min_length=3, max_length=500)
    description: str = Field(..., min_length=10, max_length=20000)
    customer_name: Optional[str] = Field(None, max_length=255)
    customer_email: Optional[EmailStr] = None
    priority: Optional[PriorityEnum] = None
    category: Optional[str] = Field(None, max_length=100)


class TicketUpdate(BaseModel):
    subject: Optional[str] = Field(None, min_length=3, max_length=500)
    description: Optional[str] = Field(None, min_length=10, max_length=20000)
    status: Optional[TicketStatusEnum] = None
    priority: Optional[PriorityEnum] = None
    category: Optional[str] = Field(None, max_length=100)
    assigned_to: Optional[int] = None
    comment: Optional[str] = Field(None, max_length=4000)


class PredictionInput(BaseModel):
    subject: str = Field(..., min_length=3, max_length=500)
    description: str = Field(..., min_length=10, max_length=20000)


class TaskPredictionResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    task: str
    prediction: Optional[str]
    confidence: Optional[float]
    model_version: Optional[str]
    status: str


class PredictionModelTaskStatus(BaseModel):
    available: bool
    confidence_available: bool
    reason: Optional[str] = None


class PredictionModelStatus(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_version: Optional[str]
    trained_at_utc: Optional[str]
    source_dataset: Optional[str]
    models: dict[str, PredictionModelTaskStatus]
    urgent_detection: dict


class PredictionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    predicted_category: Optional[str]
    category_confidence: Optional[float]
    predicted_priority: Optional[str]
    priority_confidence: Optional[float]
    predicted_sentiment: Optional[SentimentEnum]
    sentiment_confidence: Optional[float]
    is_urgent_rule_based: bool
    model_version: Optional[str]
    predicted_at: datetime

class StatusHistoryResponse(BaseModel):
    id: int
    old_status: Optional[TicketStatusEnum]
    new_status: TicketStatusEnum
    comment: Optional[str]
    changed_at: datetime
    changed_by: int

    model_config = ConfigDict(from_attributes=True)


class TicketResponse(BaseModel):
    id: int
    ticket_number: str
    subject: str
    description: str
    status: TicketStatusEnum
    priority: Optional[PriorityEnum]
    category: Optional[str]
    customer_name: Optional[str]
    customer_email: Optional[str]
    created_by: int
    assigned_to: Optional[int]
    is_urgent: bool
    created_at: datetime
    updated_at: Optional[datetime]
    resolved_at: Optional[datetime]
    predictions: Optional[PredictionResponse]
    status_history: List[StatusHistoryResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------
class DashboardStats(BaseModel):
    total_tickets: int
    open_tickets: int
    in_progress_tickets: int
    resolved_tickets: int
    closed_tickets: int
    high_priority_tickets: int
    urgent_tickets: int
    category_distribution: dict
    predicted_category_distribution: dict = Field(default_factory=dict)
    priority_distribution: dict
    sentiment_distribution: dict
    status_distribution: dict
    recent_tickets: List[TicketResponse]
    tickets_last_7_days: List[dict]


# ---------------------------------------------------------------------------
# Pagination wrapper
# ---------------------------------------------------------------------------
class PaginatedTickets(BaseModel):
    items: List[TicketResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
