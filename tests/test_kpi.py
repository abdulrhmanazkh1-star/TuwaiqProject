from datetime import date, timedelta
from types import SimpleNamespace
from app.kpis import investment_return_summary
from app.scoring import kpi_achievement, milestone_status


def test_higher_is_better_65_percent_off_track():
    pct, variance, status = kpi_achievement(1_000_000, 650_000, "higher_better")
    assert pct == 65.0
    assert variance == -350_000
    assert status == "Off Track"


def test_cost_metric_lower_is_better():
    good_pct, _, good_status = kpi_achievement(80_000, 70_000, "lower_better")
    bad_pct, _, bad_status = kpi_achievement(80_000, 120_000, "lower_better")
    assert good_pct > 100
    assert good_status == "On Track"
    assert bad_pct < 80
    assert bad_status == "Off Track"


def test_insufficient_data():
    pct, variance, status = kpi_achievement(100, None, "higher_better")
    assert status == "Insufficient Data"
    assert pct is None


def test_invalid_cannot_use_revenue_logic_on_cost():
    # Same numbers, different direction, different status meaning
    rev = kpi_achievement(100, 120, "higher_better")
    cost = kpi_achievement(100, 120, "lower_better")
    assert rev[2] == "On Track"
    assert cost[2] != "On Track"


def test_milestone_delay():
    yesterday = date.today() - timedelta(days=1)
    tomorrow = date.today() + timedelta(days=1)
    assert milestone_status(yesterday, None) == "delayed"
    assert milestone_status(tomorrow, None) == "pending"
    assert milestone_status(yesterday, date.today()) == "completed"


def test_alert_thresholds_needs_attention():
    pct, _, status = kpi_achievement(100, 80, "higher_better")
    assert pct == 80
    assert status == "Needs Attention"


def test_investment_roi_uses_only_recorded_values():
    basis = SimpleNamespace(name="أساس تكلفة الاستثمار", actuals=[])
    current = SimpleNamespace(name="القيمة الحالية للاستثمار", actuals=[SimpleNamespace(period="2026-06", actual_value=120)])
    dividends = SimpleNamespace(name="توزيعات مستلمة", actuals=[SimpleNamespace(period="2026-03", actual_value=2), SimpleNamespace(period="2026-06", actual_value=3)])
    proceeds = SimpleNamespace(name="حصيلة تخارج محققة", actuals=[])
    relationship = SimpleNamespace(relationship_type="equity_investment", initial_budget=100, kpi_targets=[basis, current, dividends, proceeds])
    result = investment_return_summary(relationship)
    assert result["roi_pct"] == 25.0
    assert result["total_return"] == 25


def test_investment_roi_discloses_missing_inputs():
    relationship = SimpleNamespace(relationship_type="equity_investment", initial_budget=None, kpi_targets=[])
    result = investment_return_summary(relationship)
    assert result["roi_pct"] is None
    assert "يلزم" in result["missing"]
