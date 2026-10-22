from types import SimpleNamespace
from app.scoring import (
    analyze_pair,
    kpi_achievement,
    score_partnership,
)


def _fin(year, revenue, net_income, assets, liab, ca, cl, market_cap=None):
    return SimpleNamespace(
        period_year=year,
        revenue=revenue,
        net_income=net_income,
        total_assets=assets,
        total_liabilities=liab,
        current_assets=ca,
        current_liabilities=cl,
        market_cap=market_cap,
        is_synthetic=True,
        company_id=1,
    )


def _company(name, sector, products, financials, cid=1):
    return SimpleNamespace(
        id=cid,
        official_name=name,
        sector=sector,
        products_services=products,
        is_synthetic=True,
        financials=financials,
        sources=[],
    )


def test_partnership_telecom_fintech_outranks_same_sector():
    tel = _company("Tel", "اتصالات", "شبكات، بيانات", [_fin(2023, 100, 10, 200, 80, 50, 30), _fin(2024, 110, 12, 210, 78, 52, 29)], 1)
    fin = _company("Fin", "تقنية مالية", "مدفوعات، محافظ", [_fin(2023, 20, 1, 30, 8, 10, 4), _fin(2024, 28, 2, 35, 7, 12, 4)], 2)
    other_tel = _company("Tel2", "اتصالات", "شبكات", [_fin(2023, 90, 8, 180, 70, 40, 25), _fin(2024, 92, 8, 182, 71, 41, 26)], 3)
    a = score_partnership(tel, fin)
    b = score_partnership(tel, other_tel)
    assert a["overall_score"] > b["overall_score"]
    assert a["scoring_version"] == "cm-score-v2"


def test_missing_financials_lowers_confidence():
    a = _company("A", "تجزئة", "متاجر", [], 1)
    b = _company("B", "خدمات لوجستية", "نقل", [], 2)
    result = analyze_pair(a, b, "partnership")
    fin_crit = next(c for c in result["criteria"] if c["criterion"] == "financial_capacity")
    assert fin_crit["score"] is None
    assert result["confidence"] < 0.8


def test_ranking_consistency():
    tel = _company("Tel", "اتصالات", "بيانات", [_fin(2023, 100, 10, 200, 80, 50, 30), _fin(2024, 110, 12, 210, 70, 55, 28)], 1)
    c1 = _company("F", "تقنية مالية", "مدفوعات", [_fin(2023, 20, 2, 30, 10, 12, 5), _fin(2024, 26, 3, 32, 9, 14, 5)], 2)
    c2 = _company("X", "عقارات", "تطوير", [_fin(2023, 40, 6, 100, 40, 20, 15), _fin(2024, 41, 6, 101, 41, 21, 15)], 3)
    s1 = analyze_pair(tel, c1, "partnership")["overall_score"]
    s2 = analyze_pair(tel, c2, "partnership")["overall_score"]
    again = analyze_pair(tel, c1, "partnership")["overall_score"]
    assert s1 == again
    assert 0 <= s1 <= 100
    assert 0 <= s2 <= 100
