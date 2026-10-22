"""Compatibility scoring API plus KPI calculation helpers."""

from datetime import date

from app.scoring_engine import (
    CAPABILITY_LABELS, CAPABILITY_SYNERGIES, CAPABILITY_TAXONOMY,
    JV_WEIGHTS, PARTNERSHIP_WEIGHTS, SCORING_VERSION, analyze_pair, clamp,
    company_profile, extract_capabilities, extract_tokens, financial_capacity_score,
    latest_financials, normalize_text, rank_candidates, score_joint_venture,
    score_partnership, weighted_overall,
)


def kpi_achievement(target_value, actual_value, direction, range_min=None, range_max=None):
    if actual_value is None or target_value is None:
        return None, None, "Insufficient Data"
    if direction == "range":
        if range_min is None or range_max is None:
            return None, None, "Insufficient Data"
        if range_min <= actual_value <= range_max:
            mid = (range_min + range_max) / 2
            variance = actual_value - mid
            return 100.0, variance, "On Track"
        if actual_value < range_min:
            variance = actual_value - range_min
            pct = (actual_value / range_min) * 100 if range_min else None
            return pct, variance, _status_from_pct((pct or 0) / 100)
        variance = actual_value - range_max
        over = (range_max / actual_value) * 100 if actual_value else 0
        return over, variance, _status_from_pct(over / 100)
    if direction == "lower_better":
        if actual_value <= 0 and target_value <= 0:
            return 100.0, 0.0, "On Track"
        if actual_value <= 0:
            return None, actual_value - target_value, "Insufficient Data"
        pct = (target_value / actual_value) * 100
        variance = actual_value - target_value
        return round(pct, 2), round(variance, 2), _status_from_pct(pct / 100)
    # higher_better
    if target_value == 0:
        return None, actual_value, "Insufficient Data"
    pct = (actual_value / target_value) * 100
    variance = actual_value - target_value
    return round(pct, 2), round(variance, 2), _status_from_pct(pct / 100)


def _status_from_pct(ratio, on_track=0.90, needs=0.70):
    if ratio >= on_track:
        return "On Track"
    if ratio >= needs:
        return "Needs Attention"
    return "Off Track"


def milestone_status(due_date, completed_at, today=None):
    today = today or date.today()
    if completed_at:
        return "completed"
    if due_date < today:
        return "delayed"
    return "pending"
