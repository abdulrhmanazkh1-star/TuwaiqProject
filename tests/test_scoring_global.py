from types import SimpleNamespace

import pytest

from app.models import Company
from app.scoring import analyze_pair, rank_candidates


ANALYSIS_TYPES = ("partnership", "joint_venture")


@pytest.mark.parametrize("analysis_type", ANALYSIS_TYPES)
def test_all_seeded_ordered_company_pairs_are_deterministic_and_bounded(app, analysis_type):
    with app.app_context():
        companies = Company.query.order_by(Company.symbol).all()
        assert len(companies) == 27
        checked = 0
        for company_a in companies:
            for company_b in companies:
                if company_a.id == company_b.id:
                    continue
                forward = analyze_pair(company_a, company_b, analysis_type)
                reverse = analyze_pair(company_b, company_a, analysis_type)
                again = analyze_pair(company_a, company_b, analysis_type)
                assert forward["scoring_version"] == "cm-score-v2"
                assert 0 <= forward["overall_score"] <= 100
                assert forward["overall_score"] == reverse["overall_score"] == again["overall_score"]
                assert 0 <= forward["evidence_coverage"] <= 1
                assert all(c["score"] is None or 0 <= c["score"] <= 100 for c in forward["criteria"])
                checked += 1
        assert checked == 27 * 26


@pytest.mark.parametrize("analysis_type", ANALYSIS_TYPES)
def test_discovery_ranks_every_other_company_and_matches_pair_comparison(app, analysis_type):
    with app.app_context():
        companies = Company.query.order_by(Company.symbol).all()
        for start in companies:
            ranked = rank_candidates(start, companies, analysis_type)
            assert len(ranked) == len(companies) - 1
            assert all(row[2].id != start.id for row in ranked)
            assert ranked == rank_candidates(start, companies, analysis_type)
            assert ranked[:5] == sorted(
                ranked,
                key=lambda row: (-row[0], -row[1], row[2].symbol),
            )[:5]
            for score, _coverage, candidate, payload in ranked:
                compared = analyze_pair(start, candidate, analysis_type)
                assert score == compared["overall_score"]
                assert payload["criteria"] == compared["criteria"]


def test_new_company_is_automatically_ranked_without_symbol_specific_rules():
    start = SimpleNamespace(
        id=1001, official_name="شركة تقنية", official_name_en="Tech firm", sector="تقنية",
        subsector="خدمات رقمية", description="تطوير منصات رقمية وحوسبة سحابية للمنشآت",
        products_services="برمجيات، خدمات سحابية، حماية سيبرانية", financials=[],
        sources=[], is_synthetic=False,
    )
    new_candidate = SimpleNamespace(
        id=1002, official_name="شركة شبكات", official_name_en="Network firm", sector="اتصالات",
        subsector="اتصالات متقدمة", description="تشغيل شبكات اتصال ونقل بيانات",
        products_services="شبكات، اتصالات، إنترنت الأشياء", financials=[],
        sources=[], is_synthetic=False, symbol="NEW1",
    )
    unrelated = SimpleNamespace(
        id=1003, official_name="شركة أغذية", official_name_en="Food firm", sector="أغذية",
        subsector="إنتاج غذائي", description="تصنيع وتوزيع منتجات غذائية",
        products_services="تصنيع أغذية وتوزيع", financials=[],
        sources=[], is_synthetic=False, symbol="NEW2",
    )
    ranked = rank_candidates(start, [start, unrelated, new_candidate], "partnership")
    assert {row[2].id for row in ranked} == {1002, 1003}
    assert ranked[0][2].id == 1002


def test_missing_financial_data_is_not_scored_as_a_negative():
    left = SimpleNamespace(
        id=1101, official_name="A", sector="اتصالات", description="شبكات بيانات",
        products_services="إنترنت واتصالات", financials=[], sources=[], is_synthetic=False,
    )
    right = SimpleNamespace(
        id=1102, official_name="B", sector="مصارف", description="خدمات مصرفية وتمويل",
        products_services="تمويل ومدفوعات", financials=[], sources=[], is_synthetic=False,
    )
    result = analyze_pair(left, right, "partnership")
    financial = next(row for row in result["criteria"] if row["criterion"] == "financial_capacity")
    assert financial["score"] is None
    assert any("المالية الموثقة" in note for note in result["missing_information"])
