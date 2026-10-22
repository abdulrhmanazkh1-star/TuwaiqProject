import requests

from app.ai_engine import _demo_narrative, _parse_json, analyze_with_ai
from app.models import Company, TechnicalMonitoringEvent
from app.monitoring import gemini_api_metrics


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


class FakeResponse:
    def __init__(self, status=200, body=None):
        self.status_code = status
        self.headers = {}
        self.body = body or {"choices": [{"message": {"content": '{"opportunities":["فرصة"],"risks":[],"collaborations":[],"evidence_summary":"ملخص","caveats":[]}'}}], "usage": {"prompt_tokens": 123, "completion_tokens": 45}}

    def json(self):
        return self.body

    def raise_for_status(self):
        if self.status_code >= 400:
            error = requests.HTTPError(f"HTTP {self.status_code}")
            error.response = self
            raise error


def _pair(app):
    with app.app_context():
        return tuple(Company.query.limit(2).all())


def test_gemini_success_records_real_usage_and_monitoring(client, app, monkeypatch):
    import app.ai_engine as engine
    monkeypatch.setattr(engine.requests, "post", lambda *a, **k: FakeResponse())
    with app.app_context():
        app.config.update(LLM_API_KEY="test-secret", LLM_RETRY_ATTEMPTS=1)
        a, b = Company.query.limit(2).all()
        narrative, mode, input_tokens, output_tokens = analyze_with_ai(a, b, "partnership", {"overall_score": 65})
        event = TechnicalMonitoringEvent.query.filter_by(event_type="gemini_api_request").one()
        assert mode == "llm"
        assert narrative["opportunities"] == ["فرصة"]
        assert (input_tokens, output_tokens) == (123, 45)
        assert (event.tokens_in, event.tokens_out) == (123, 45)
        assert event.estimated_cost_usd is not None
        assert gemini_api_metrics()["status"] == "Healthy"


def test_missing_key_keeps_demo_without_fake_usage_or_api_event(app):
    with app.app_context():
        app.config["LLM_API_KEY"] = ""
        a, b = Company.query.limit(2).all()
        _, mode, tokens_in, tokens_out = analyze_with_ai(a, b, "partnership", {"overall_score": 60})
        assert mode == "demo_rules"
        assert tokens_in is tokens_out is None
        assert TechnicalMonitoringEvent.query.filter_by(event_type="gemini_api_request").count() == 0
        assert gemini_api_metrics()["status"] == "Not Configured"


def test_configured_but_no_real_request_is_not_tested(app):
    with app.app_context():
        app.config["LLM_API_KEY"] = "configured-test-key"
        assert gemini_api_metrics()["status"] == "Not Tested"


@__import__("pytest").mark.parametrize(("status", "expected"), [(401, "authentication_http_401"), (403, "authentication_http_403"), (429, "rate_limit_http_429")])
def test_gemini_http_errors_are_recorded_without_secret(client, app, monkeypatch, status, expected):
    import app.ai_engine as engine
    monkeypatch.setattr(engine.requests, "post", lambda *a, **k: FakeResponse(status=status))
    with app.app_context():
        app.config.update(LLM_API_KEY="test-secret", LLM_RETRY_ATTEMPTS=1)
        a, b = Company.query.limit(2).all()
        import pytest
        with pytest.raises(requests.HTTPError):
            analyze_with_ai(a, b, "partnership", {"overall_score": 60})
        event = TechnicalMonitoringEvent.query.filter_by(event_type="gemini_api_request").one()
        assert event.error_code == expected
        assert "test-secret" not in (event.details or "")
        assert gemini_api_metrics()["failed"] == 1


def test_gemini_timeout_is_recorded(client, app, monkeypatch):
    import app.ai_engine as engine
    monkeypatch.setattr(engine.requests, "post", lambda *a, **k: (_ for _ in ()).throw(requests.Timeout("secret-free")))
    with app.app_context():
        app.config.update(LLM_API_KEY="test-secret", LLM_RETRY_ATTEMPTS=1)
        a, b = Company.query.limit(2).all()
        import pytest
        with pytest.raises(requests.Timeout):
            analyze_with_ai(a, b, "partnership", {"overall_score": 60})
        assert TechnicalMonitoringEvent.query.filter_by(event_type="gemini_api_request", error_code="timeout").count() == 1


def test_invalid_gemini_response_recorded_as_failure(client, app, monkeypatch):
    import app.ai_engine as engine
    malformed = FakeResponse(body={"choices": [{"message": {"content": '{"wrong":true}'}}]})
    monkeypatch.setattr(engine.requests, "post", lambda *a, **k: malformed)
    with app.app_context():
        app.config.update(LLM_API_KEY="test-secret", LLM_RETRY_ATTEMPTS=1)
        a, b = Company.query.limit(2).all()
        import pytest
        with pytest.raises(ValueError):
            analyze_with_ai(a, b, "partnership", {"overall_score": 60})
        assert TechnicalMonitoringEvent.query.filter_by(event_type="gemini_api_request", error_code="invalid_response_http_200").count() == 1
