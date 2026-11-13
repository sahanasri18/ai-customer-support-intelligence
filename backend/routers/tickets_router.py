"""
Tickets router: CRUD + ML prediction trigger + status history + CSV export.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import Optional, List
from datetime import datetime
import io
import csv

from database import get_db
import models
from schemas import (
    TicketCreate, TicketUpdate, TicketResponse, PaginatedTickets,
    PredictionResponse, TicketStatusEnum
)
from auth import get_current_user, require_admin
from utils import generate_ticket_number, is_urgent_rule_based
from ml_predictor import predict
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tickets", tags=["tickets"])


def _csv_value(value):
    if value is None:
        return ""
    value = str(value)
    if value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def _get_ticket_or_404(ticket_id: int, db: Session) -> models.Ticket:
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.post("/", response_model=TicketResponse, status_code=201)
def create_ticket(
    payload: TicketCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    urgent = is_urgent_rule_based(payload.subject, payload.description)
    ticket = models.Ticket(
        ticket_number=generate_ticket_number(),
        subject=payload.subject,
        description=payload.description,
        customer_name=payload.customer_name,
        customer_email=payload.customer_email,
        priority=payload.priority,
        category=payload.category,
        created_by=current_user.id,
        is_urgent=urgent,
    )
    db.add(ticket)
    db.flush()  # get ticket.id before commit
    db.add(models.TicketStatusHistory(
        ticket_id=ticket.id,
        old_status=None,
        new_status=models.TicketStatusEnum.open,
        changed_by=current_user.id,
        comment="Ticket created",
    ))

    # --- Run ML predictions ---
    try:
        pred_data = predict(payload.subject, payload.description)
        prediction = models.TicketPrediction(
            ticket_id=ticket.id,
            predicted_category=pred_data.get("predicted_category"),
            category_confidence=pred_data.get("category_confidence"),
            predicted_priority=pred_data.get("predicted_priority"),
            priority_confidence=pred_data.get("priority_confidence"),
            predicted_sentiment=pred_data.get("predicted_sentiment"),
            sentiment_confidence=pred_data.get("sentiment_confidence"),
            is_urgent_rule_based=urgent,
            model_version=pred_data.get("model_version"),
        )
        db.add(prediction)
    except Exception as e:
        logger.warning(f"ML prediction error on ticket creation: {e}")

    # --- Audit log ---
    db.add(models.AuditLog(user_id=current_user.id, ticket_id=ticket.id, action="ticket_created"))
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("/", response_model=PaginatedTickets)
def list_tickets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[TicketStatusEnum] = None,
    priority: Optional[models.PriorityEnum] = None,
    category: Optional[str] = Query(None, max_length=100),
    search: Optional[str] = Query(None, max_length=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    q = db.query(models.Ticket)
    if status:
        q = q.filter(models.Ticket.status == status)
    if priority:
        q = q.filter(models.Ticket.priority == priority)
    if category:
        q = q.filter(models.Ticket.category == category)
    if search:
        like = f"%{search}%"
        q = q.filter(or_(
            models.Ticket.subject.like(like),
            models.Ticket.description.like(like),
            models.Ticket.ticket_number.like(like),
        ))

    total = q.count()
    items = q.order_by(models.Ticket.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedTickets(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/export/csv")
def export_csv(
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    tickets = db.query(models.Ticket).order_by(models.Ticket.created_at.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ticket_number", "subject", "status", "priority", "category",
        "customer_name", "customer_email", "is_urgent", "created_at",
        "predicted_category", "predicted_sentiment", "predicted_priority",
    ])
    for t in tickets:
        pred = t.predictions
        writer.writerow([_csv_value(value) for value in [
            t.ticket_number, t.subject, t.status.value if t.status else "",
            t.priority.value if t.priority else "",
            t.category or "",
            t.customer_name or "", t.customer_email or "",
            t.is_urgent, t.created_at.isoformat(),
            pred.predicted_category if pred else "",
            pred.predicted_sentiment.value if pred and pred.predicted_sentiment else "",
            pred.predicted_priority if pred else "",
        ]])
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=tickets_export.csv"},
    )


@router.get("/{ticket_id}", response_model=TicketResponse)
def get_ticket(ticket_id: int, db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    return _get_ticket_or_404(ticket_id, db)


@router.patch("/{ticket_id}", response_model=TicketResponse)
def update_ticket(
    ticket_id: int,
    payload: TicketUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    ticket = _get_ticket_or_404(ticket_id, db)
    old_status = ticket.status

    update_data = payload.model_dump(exclude_none=True)
    comment = update_data.pop("comment", None)

    for field, val in update_data.items():
        setattr(ticket, field, val)

    if "assigned_to" in update_data and update_data["assigned_to"] is not None:
        assignee = db.query(models.User).filter(
            models.User.id == update_data["assigned_to"], models.User.is_active.is_(True)
        ).first()
        if assignee is None:
            raise HTTPException(status_code=422, detail="Assignee does not exist or is inactive")

    # Record status change
    if payload.status and payload.status != old_status:
        history = models.TicketStatusHistory(
            ticket_id=ticket.id,
            old_status=old_status,
            new_status=payload.status,
            changed_by=current_user.id,
            comment=comment,
        )
        db.add(history)
        if payload.status in (models.TicketStatusEnum.resolved, models.TicketStatusEnum.closed):
            ticket.resolved_at = datetime.utcnow()
        else:
            ticket.resolved_at = None

    db.add(models.AuditLog(user_id=current_user.id, ticket_id=ticket.id, action="ticket_updated"))
    db.commit()
    db.refresh(ticket)
    return ticket


@router.delete("/{ticket_id}", status_code=204)
def delete_ticket(ticket_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    ticket = _get_ticket_or_404(ticket_id, db)
    db.add(models.AuditLog(
        user_id=current_user.id,
        action="ticket_deleted",
        details=f"ticket_id={ticket.id}",
    ))
    db.delete(ticket)
    db.commit()


@router.post("/{ticket_id}/predict", response_model=PredictionResponse)
def re_predict(ticket_id: int, db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    ticket = _get_ticket_or_404(ticket_id, db)
    pred_data = predict(ticket.subject, ticket.description)
    urgent = is_urgent_rule_based(ticket.subject, ticket.description)

    pred = ticket.predictions
    if pred is None:
        pred = models.TicketPrediction(ticket_id=ticket.id)
        db.add(pred)

    pred.predicted_category = pred_data.get("predicted_category")
    pred.category_confidence = pred_data.get("category_confidence")
    pred.predicted_priority = pred_data.get("predicted_priority")
    pred.priority_confidence = pred_data.get("priority_confidence")
    pred.predicted_sentiment = pred_data.get("predicted_sentiment")
    pred.sentiment_confidence = pred_data.get("sentiment_confidence")
    pred.is_urgent_rule_based = urgent
    pred.model_version = pred_data.get("model_version")
    pred.predicted_at = datetime.utcnow()

    db.commit()
    db.refresh(pred)
    return pred
