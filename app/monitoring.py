from __future__ import annotations

from datetime import datetime, timedelta
from sqlalchemy import func
from app.models import db, TechnicalMonitoringEvent
from flask import current_app


def record_event(
    event_type: str,
    success: bool,
    latency_ms=None,
    error_code=None,
    tokens_in=None,
    tokens_out=None,
    details=None,
):
    in_cost = current_app.config.get("LLM_INPUT_COST_PER_1M", 0)
    out_cost = current_app.config.get("LLM_OUTPUT_COST_PER_1M", 0)
    cost = None
    if tokens_in or tokens_out:
        cost = ((tokens_in or 0) / 1_000_000) * in_cost + ((tokens_out or 0) / 1_000_000) * out_cost
    event = TechnicalMonitoringEvent(
        event_type=event_type,
        success=success,
        latency_ms=latency_ms,
        error_code=error_code,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        estimated_cost_usd=cost,
        details=details,
    )
    db.session.add(event)
    db.session.commit()
    return event


def dashboard_metrics(hours=24 * 14):
    since = datetime.utcnow() - timedelta(hours=hours)
    q = TechnicalMonitoringEvent.query.filter(TechnicalMonitoringEvent.created_at >= since)
    total = q.count()
    completed = q.filter_by(success=True).count()
    failed = q.filter_by(success=False).count()
    avg_latency = q.filter(TechnicalMonitoringEvent.latency_ms.isnot(None)).with_entities(
        func.avg(TechnicalMonitoringEvent.latency_ms)
    ).scalar()
    ai_failures = q.filter(
        TechnicalMonitoringEvent.event_type == "ai_analysis",
        TechnicalMonitoringEvent.success.is_(False),
    ).count()
    validation_failures = q.filter_by(event_type="validation_failure").count()
    tokens_in = q.with_entities(func.coalesce(func.sum(TechnicalMonitoringEvent.tokens_in), 0)).scalar()
    tokens_out = q.with_entities(func.coalesce(func.sum(TechnicalMonitoringEvent.tokens_out), 0)).scalar()
    cost = q.with_entities(func.coalesce(func.sum(TechnicalMonitoringEvent.estimated_cost_usd), 0)).scalar()
    last_event = TechnicalMonitoringEvent.query.order_by(TechnicalMonitoringEvent.created_at.desc()).first()
    freshness_minutes = None
    if last_event:
        freshness_minutes = int((datetime.utcnow() - last_event.created_at).total_seconds() // 60)
    by_type = (
        db.session.query(TechnicalMonitoringEvent.event_type, func.count(TechnicalMonitoringEvent.id))
        .filter(TechnicalMonitoringEvent.created_at >= since)
        .group_by(TechnicalMonitoringEvent.event_type)
        .all()
    )
    recent = (
        TechnicalMonitoringEvent.query.order_by(TechnicalMonitoringEvent.created_at.desc()).limit(25).all()
    )
    return {
        "total": total,
        "completed": completed,
        "failed": failed,
        "error_rate": round((failed / total) * 100, 2) if total else 0,
        "avg_latency_ms": round(avg_latency, 1) if avg_latency else 0,
        "ai_failures": ai_failures,
        "validation_failures": validation_failures,
        "tokens_in": int(tokens_in or 0),
        "tokens_out": int(tokens_out or 0),
        "estimated_cost_usd": round(float(cost or 0), 6),
        "freshness_minutes": freshness_minutes,
        "by_type": [{"type": t, "count": c} for t, c in by_type],
        "recent": recent,
    }
