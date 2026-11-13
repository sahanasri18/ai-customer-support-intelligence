"""
Analytics router: dashboard stats, trends, distributions.
All values derived from actual database records.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from datetime import datetime, timedelta
from database import get_db
import models
from schemas import DashboardStats
from auth import get_current_user, require_admin

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/dashboard", response_model=DashboardStats)
def dashboard(db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    # --- Counts ---
    total = db.query(func.count(models.Ticket.id)).scalar()
    open_count = db.query(func.count(models.Ticket.id)).filter(models.Ticket.status == "open").scalar()
    in_prog = db.query(func.count(models.Ticket.id)).filter(models.Ticket.status == "in_progress").scalar()
    resolved = db.query(func.count(models.Ticket.id)).filter(models.Ticket.status == "resolved").scalar()
    closed = db.query(func.count(models.Ticket.id)).filter(models.Ticket.status == "closed").scalar()
    high_pri = db.query(func.count(models.Ticket.id)).filter(
        models.Ticket.priority.in_(["high", "urgent"])
    ).scalar()
    urgent_count = db.query(func.count(models.Ticket.id)).filter(
        models.Ticket.is_urgent == True
    ).scalar()

    # --- Category distribution ---
    cat_rows = db.query(models.Ticket.category, func.count(models.Ticket.id)).group_by(models.Ticket.category).all()
    cat_dist = {(r[0] or "Uncategorized"): r[1] for r in cat_rows}

    predicted_cat_rows = (
        db.query(models.TicketPrediction.predicted_category, func.count(models.TicketPrediction.id))
        .filter(models.TicketPrediction.predicted_category.isnot(None))
        .group_by(models.TicketPrediction.predicted_category)
        .all()
    )
    predicted_cat_dist = {r[0]: r[1] for r in predicted_cat_rows}

    # --- Priority distribution ---
    pri_rows = db.query(models.Ticket.priority, func.count(models.Ticket.id)).group_by(models.Ticket.priority).all()
    pri_dist = {(r[0].value if r[0] else "unset"): r[1] for r in pri_rows}

    # --- Sentiment distribution (from predictions) ---
    sent_rows = (
        db.query(models.TicketPrediction.predicted_sentiment, func.count(models.TicketPrediction.id))
        .filter(models.TicketPrediction.predicted_sentiment.isnot(None))
        .group_by(models.TicketPrediction.predicted_sentiment)
        .all()
    )
    sent_dist = {(r[0].value if r[0] else "unknown"): r[1] for r in sent_rows}

    # --- Status distribution ---
    status_rows = db.query(models.Ticket.status, func.count(models.Ticket.id)).group_by(models.Ticket.status).all()
    status_dist = {(r[0].value if r[0] else "unknown"): r[1] for r in status_rows}

    # --- Recent tickets ---
    recent = db.query(models.Ticket).order_by(models.Ticket.created_at.desc()).limit(10).all()

    # --- Ticket trend: last 7 days ---
    trend = []
    for i in range(6, -1, -1):
        day_start = (datetime.utcnow() - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        count = db.query(func.count(models.Ticket.id)).filter(
            models.Ticket.created_at >= day_start,
            models.Ticket.created_at < day_end,
        ).scalar()
        trend.append({"date": day_start.strftime("%Y-%m-%d"), "count": count})

    return DashboardStats(
        total_tickets=total,
        open_tickets=open_count,
        in_progress_tickets=in_prog,
        resolved_tickets=resolved,
        closed_tickets=closed,
        high_priority_tickets=high_pri,
        urgent_tickets=urgent_count,
        category_distribution=cat_dist,
        predicted_category_distribution=predicted_cat_dist,
        priority_distribution=pri_dist,
        sentiment_distribution=sent_dist,
        status_distribution=status_dist,
        recent_tickets=recent,
        tickets_last_7_days=trend,
    )


@router.get("/audit-logs")
def audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    q = db.query(models.AuditLog).order_by(models.AuditLog.created_at.desc())
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [
            {
                "id": a.id,
                "user_id": a.user_id,
                "ticket_id": a.ticket_id,
                "action": a.action,
                "details": a.details,
                "created_at": a.created_at.isoformat(),
            }
            for a in items
        ],
        "total": total,
    }
