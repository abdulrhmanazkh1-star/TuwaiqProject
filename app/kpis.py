from __future__ import annotations

from datetime import date
from app.models import db, BusinessAlert, KPIActual
from app.scoring import kpi_achievement, milestone_status


def evaluate_target(target):
    latest = None
    if target.actuals:
        latest = sorted(target.actuals, key=lambda a: a.period)[-1]
    if not latest:
        return {
            "name": target.name,
            "unit": target.unit,
            "target_value": target.target_value,
            "actual_value": None,
            "period": None,
            "achievement_pct": None,
            "variance": None,
            "status": "Insufficient Data",
            "direction": target.direction,
            "history": [],
        }
    pct, variance, status = kpi_achievement(
        target.target_value,
        latest.actual_value,
        target.direction,
        target.range_min,
        target.range_max,
    )
    history = [
        {"period": a.period, "actual": a.actual_value, "source": a.source} for a in target.actuals
    ]
    return {
        "id": target.id,
        "name": target.name,
        "unit": target.unit,
        "target_value": target.target_value,
        "actual_value": latest.actual_value,
        "period": latest.period,
        "achievement_pct": pct,
        "variance": variance,
        "status": status,
        "direction": target.direction,
        "history": history,
    }


def refresh_alerts(relationship):
    BusinessAlert.query.filter_by(relationship_id=relationship.id).delete()
    created = []
    for target in relationship.kpi_targets:
        row = evaluate_target(target)
        if row["status"] in ("Needs Attention", "Off Track"):
            alert = BusinessAlert(
                relationship_id=relationship.id,
                kpi_target_id=target.id,
                severity="high" if row["status"] == "Off Track" else "medium",
                status_label=row["status"],
                message=_alert_message(row),
            )
            db.session.add(alert)
            created.append(alert)
        elif row["status"] == "Insufficient Data":
            alert = BusinessAlert(
                relationship_id=relationship.id,
                kpi_target_id=target.id,
                severity="low",
                status_label=row["status"],
                message=f"المؤشر «{row['name']}» بلا قيمة فعلية كافية للحساب.",
            )
            db.session.add(alert)
            created.append(alert)
    today = date.today()
    for milestone in relationship.milestones:
        milestone.status = milestone_status(milestone.due_date, milestone.completed_at, today)
        if milestone.status == "delayed":
            alert = BusinessAlert(
                relationship_id=relationship.id,
                severity="high",
                status_label="Off Track",
                message=f"معلم متأخر: {milestone.title} (الاستحقاق {milestone.due_date}).",
            )
            db.session.add(alert)
            created.append(alert)
    db.session.commit()
    return created


def investment_return_summary(relationship):
    """Compute ROI only from a recorded cost basis and observed investment inputs."""
    if relationship.relationship_type != "equity_investment":
        return None

    def latest_value(names):
        target = next((t for t in relationship.kpi_targets if t.name in names), None)
        if not target or not target.actuals:
            return None
        return max(target.actuals, key=lambda a: a.period).actual_value

    def recorded_total(names):
        target = next((t for t in relationship.kpi_targets if t.name in names), None)
        if not target:
            return 0.0
        return sum(actual.actual_value for actual in target.actuals)

    cost_basis = relationship.initial_budget or latest_value({"أساس تكلفة الاستثمار", "Investment cost basis"})
    current_value = latest_value({"القيمة الحالية للاستثمار", "Current investment value"})
    dividends = recorded_total({"توزيعات مستلمة", "Dividends received"})
    realized_proceeds = recorded_total({"حصيلة تخارج محققة", "Realized exit proceeds"})
    if cost_basis is None or cost_basis <= 0 or current_value is None:
        return {
            "roi_pct": None,
            "total_return": None,
            "cost_basis": cost_basis,
            "current_value": current_value,
            "dividends": dividends,
            "realized_proceeds": realized_proceeds,
            "missing": "يلزم تسجيل أساس تكلفة موجب وقيمة حالية موثقة لحساب ROI.",
        }
    total_return = current_value + dividends + realized_proceeds - cost_basis
    return {
        "roi_pct": round(total_return / cost_basis * 100, 2),
        "total_return": round(total_return, 2),
        "cost_basis": cost_basis,
        "current_value": current_value,
        "dividends": round(dividends, 2),
        "realized_proceeds": round(realized_proceeds, 2),
        "missing": None,
    }


def _alert_message(row):
    pct = row["achievement_pct"]
    shortfall = None if pct is None else round(100 - pct, 2)
    return (
        f"المؤشر «{row['name']}»: المستهدف {row['target_value']} {row['unit']}، "
        f"الفعلي {row['actual_value']}، الإنجاز {pct}% "
        f"{'(عجز ' + str(shortfall) + '%)' if shortfall is not None else ''}. "
        f"الحالة: {row['status']}. يُنصح بالتحقق من البيانات والتنفيذ دون افتراض السبب الجذري."
    )


def add_actual(target, period, value, source="manual"):
    if value is None:
        raise ValueError("قيمة المؤشر مطلوبة")
    try:
        value = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("قيمة المؤشر غير رقمية") from exc
    if target.direction == "higher_better" and value < 0 and target.unit == "SAR":
        # negative revenue is allowed but flagged later; still valid number
        pass
    existing = KPIActual.query.filter_by(target_id=target.id, period=period).first()
    if existing:
        existing.actual_value = value
        existing.source = source
    else:
        db.session.add(KPIActual(target_id=target.id, period=period, actual_value=value, source=source))
    db.session.commit()
    return True
