from app.ai_engine import _demo_narrative, _parse_json


def test_malformed_json_recovery():
    parsed = _parse_json('intro {"opportunities": ["x"], "risks": [] } trailing')
    assert parsed["opportunities"] == ["x"]


def test_demo_mode_not_claiming_live_ai():
    class C:
        official_name = "A"
        sector = "اتصالات"
        products_services = "بيانات"
        is_synthetic = True
        financials = []
        sources = []

    a, b = C(), C()
    b.official_name = "B"
    out = _demo_narrative(a, b, "partnership", {"overall_score": 70, "scoring_version": "cm-score-v2", "limitations": []})
    assert out["demo_mode"] is True
    assert "حي" in out["evidence_summary"] or "Demo" in out["evidence_summary"] or "حتمية" in out["evidence_summary"]
