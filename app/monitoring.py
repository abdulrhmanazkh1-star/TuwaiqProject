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
    if tokens_in is not None and tokens_out is not None:
        cost = (tokens_in / 1_000_000) * in_cost + (tokens_out / 1_000_000) * out_cost
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
    gemini_q = q.filter(TechnicalMonitoringEvent.event_type == "gemini_api_request")
    tokens_in = gemini_q.with_entities(func.sum(TechnicalMonitoringEvent.tokens_in)).scalar()
    tokens_out = gemini_q.with_entities(func.sum(TechnicalMonitoringEvent.tokens_out)).scalar()
    cost = gemini_q.with_entities(func.sum(TechnicalMonitoringEvent.estimated_cost_usd)).scalar()
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
        "tokens_in": int(tokens_in) if tokens_in is not None else None,
        "tokens_out": int(tokens_out) if tokens_out is not None else None,
        "estimated_cost_usd": round(float(cost), 6) if cost is not None else None,
        "freshness_minutes": freshness_minutes,
        "by_type": [{"type": t, "count": c} for t, c in by_type],
        "recent": recent,
    }


def gemini_api_metrics():
    """Metrics sourced exclusively from actual Gemini HTTP attempts."""
    now = datetime.utcnow()
    day_start = datetime(now.year, now.month, now.day)
    month_start = datetime(now.year, now.month, 1)
    base = TechnicalMonitoringEvent.query.filter_by(event_type="gemini_api_request")
    events = base.order_by(TechnicalMonitoringEvent.created_at.desc()).all()
    configured = bool(current_app.config.get("LLM_API_KEY"))
    latest = events[0] if events else None
    recent_day = [e for e in events if e.created_at >= day_start]
    month = [e for e in events if e.created_at >= month_start]
    if not configured:
        status, reason = "Not Configured", "لم يُضف مفتاح Gemini إلى إعدادات البيئة."
    elif not latest:
        status, reason = "Not Tested", "لم يُسجّل أي طلب حقيقي إلى Gemini بعد."
    elif latest.created_at < now - timedelta(hours=24):
        status, reason = "Degraded", "آخر طلب مسجل أقدم من 24 ساعة؛ أجرِ طلباً جديداً للتحقق."
    elif latest.success and not any(not e.success for e in recent_day):
        status, reason = "Healthy", "آخر الطلبات المسجلة خلال 24 ساعة ناجحة."
    elif latest.error_code and ("http_401" in latest.error_code or "http_403" in latest.error_code or "http_404" in latest.error_code or latest.error_code in ("timeout", "connection_error")):
        status, reason = "Unavailable", "آخر طلب حقيقي تعذّر بسبب الاتصال أو المصادقة أو النموذج."
    else:
        status, reason = "Degraded", "سُجّل تعثر أو رد غير سليم في طلبات آخر 24 ساعة."

    def usage_totals(items):
        known_in = [e.tokens_in for e in items if e.tokens_in is not None]
        known_out = [e.tokens_out for e in items if e.tokens_out is not None]
        known_cost = [e.estimated_cost_usd for e in items if e.estimated_cost_usd is not None]
        return {
            "tokens_in": sum(known_in) if known_in else None,
            "tokens_out": sum(known_out) if known_out else None,
            "cost_usd": round(sum(known_cost), 6) if known_cost else None,
        }

    latencies = [e.latency_ms for e in events if e.latency_ms is not None]
    errors = {}
    for event in events:
        if not event.success:
            key = event.error_code or "unknown"
            errors[key] = errors.get(key, 0) + 1
    return {
        "status": status,
        "reason": reason,
        "model": current_app.config.get("LLM_MODEL", "gemini-3.5-flash-lite"),
        "total": len(events),
        "successful": sum(bool(e.success) for e in events),
        "failed": sum(not e.success for e in events),
        "input_tokens": usage_totals(events)["tokens_in"],
        "output_tokens": usage_totals(events)["tokens_out"],
        "daily": usage_totals(recent_day) | {"requests": len(recent_day)},
        "monthly": usage_totals(month) | {"requests": len(month)},
        "average_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else None,
        "estimated_cost_usd": usage_totals(events)["cost_usd"],
        "errors": sorted(errors.items(), key=lambda pair: pair[0]),
        "last_request_at": latest.created_at if latest else None,
    }
