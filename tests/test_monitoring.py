from app.models import Analysis, Company, Recommendation, TechnicalMonitoringEvent
from app.models import PortfolioRevision, PortfolioWorkspace, db
from app.monitoring import dashboard_metrics


def test_home_loads(client):
    res = client.get("/workspace")
    assert res.status_code == 200
    assert "مِشراك" in res.get_data(as_text=True)
    assert "7020" in res.get_data(as_text=True)
    assert "2222" in res.get_data(as_text=True)


def test_portfolio_is_public_and_workspace_requires_login(app):
    anonymous = app.test_client()
    portfolio = anonymous.get("/")
    assert portfolio.status_code == 200
    assert b"ARTIFICIAL INTELLIGENCE GRADUATE" in portfolio.data
    assert "الذكاء الاصطناعي" in portfolio.get_data(as_text=True)
    assert anonymous.get("/workspace").status_code == 302


def test_studio_keeps_two_prompts_independent_and_records_history(client, app):
    page = client.get("/studio")
    assert page.status_code == 200
    assert b"VERSION A" in page.data and b"VERSION B" in page.data
    assert b"not AI-generated" in page.data or b"not AI-generated" in client.get("/studio/preview/A").data
    with client.session_transaction() as session:
        csrf = session["portfolio_studio_csrf"]
    with app.app_context():
        owner_id = db.session.query(PortfolioWorkspace.user_id).first()[0]
        a = PortfolioWorkspace.query.filter_by(user_id=owner_id, version_key="A").one()
        b = PortfolioWorkspace.query.filter_by(user_id=owner_id, version_key="B").one()
        b_prompt = b.prompt
    response = client.post("/studio/save/A", data={
        "csrf_token": csrf, "prompt": "A saved prompt with its own project details", "style": "data",
    })
    assert response.status_code == 302
    with app.app_context():
        a = PortfolioWorkspace.query.filter_by(user_id=owner_id, version_key="A").one()
        b = PortfolioWorkspace.query.filter_by(user_id=owner_id, version_key="B").one()
        assert a.prompt == "A saved prompt with its own project details"
        assert a.style == "data"
        assert b.prompt == b_prompt
        assert PortfolioRevision.query.filter_by(workspace_id=a.id).count() == 2
    preview = client.get("/studio/preview/A")
    assert preview.status_code == 200
    assert "script-src 'none'" in preview.headers["Content-Security-Policy"]
    assert b"shared verified profile facts" in preview.data


def test_studio_csrf_and_workspace_ownership(client, app):
    assert client.post("/studio/save/A", data={"prompt": "cross-site"}).status_code == 400
    client.get("/studio")
    with client.session_transaction() as session:
        csrf = session["portfolio_studio_csrf"]
    with app.app_context():
        revision_id = PortfolioRevision.query.first().id
    other = app.test_client()
    other.post("/register", data={"username": "other-user", "password": "other-password-123"})
    assert other.get("/studio").status_code == 200
    with other.session_transaction() as session:
        other_csrf = session["portfolio_studio_csrf"]
    assert other.post(f"/studio/restore/{revision_id}", data={"csrf_token": other_csrf}).status_code == 404


def test_studio_without_ai_saves_locally_and_does_not_claim_generation(client, app):
    client.get("/studio")
    with client.session_transaction() as session:
        csrf = session["portfolio_studio_csrf"]
    response = client.post("/studio/generate/A", data={
        "csrf_token": csrf, "prompt": "Please make a clear portfolio", "style": "minimal", "external_consent": "yes",
    }, follow_redirects=True)
    assert response.status_code == 200
    assert "GEMINI_API_KEY" in response.get_data(as_text=True)
    with app.app_context():
        owner_id = db.session.query(PortfolioWorkspace.user_id).first()[0]
        a = PortfolioWorkspace.query.filter_by(user_id=owner_id, version_key="A").one()
        assert a.prompt == "Please make a clear portfolio"
        assert a.status == "saved"
        assert PortfolioRevision.query.filter_by(workspace_id=a.id).order_by(PortfolioRevision.id).count() == 2


def test_studio_generation_requires_consent_and_renders_ai_text_safely(client, app, monkeypatch):
    import app.portfolio_studio as studio_module

    client.get("/studio")
    with client.session_transaction() as session:
        csrf = session["portfolio_studio_csrf"]
    monkeypatch.setattr(studio_module, "llm_configured", lambda: True)
    generated = {"headline": "Hello", "introduction": "Intro", "about": "About", "career": "Career", "seeasist": "<script>alert(1)</script>", "compatibility": "In progress"}
    calls = []
    monkeypatch.setattr(studio_module, "_generate", lambda prompt, style: calls.append((prompt, style)) or generated)
    denied = client.post("/studio/generate/A", data={"csrf_token": csrf, "prompt": "Prompt", "style": "minimal"}, follow_redirects=True)
    assert "وافق أولاً" in denied.get_data(as_text=True)
    assert calls == []
    with client.session_transaction() as session:
        csrf = session["portfolio_studio_csrf"]
    accepted = client.post("/studio/generate/A", data={
        "csrf_token": csrf, "prompt": "Prompt", "style": "minimal", "external_consent": "yes",
    }, follow_redirects=True)
    assert accepted.status_code == 200
    assert len(calls) == 1
    preview = client.get("/studio/preview/A")
    assert b"AI DRAFT" in preview.data
    assert b"&lt;script&gt;alert(1)&lt;/script&gt;" in preview.data
    assert b"<script>alert(1)</script>" not in preview.data


def test_catalogue_is_real_listed_companies_without_fake_financials(app):
    with app.app_context():
        companies = Company.query.all()
        assert 20 <= len(companies) <= 30
        assert all(not company.is_synthetic for company in companies)
        assert all(company.source_url and "saudiexchange.sa" in company.source_url for company in companies)
        assert Company.query.filter_by(symbol="7010").first().official_name_en.startswith("Saudi Telecom")
        assert Company.query.filter_by(symbol="2222").first().official_name_en.startswith("Saudi Arabian Oil")
        assert not any(company.financials for company in companies)


def test_compare_records_event(client, app):
    with app.app_context():
        a, b = Company.query.limit(2).all()
    res = client.post(
        "/compare",
        data={"company_a": a.id, "company_b": b.id, "analysis_type": "partnership"},
        follow_redirects=True,
    )
    assert res.status_code == 200
    with app.app_context():
        assert TechnicalMonitoringEvent.query.filter_by(event_type="ai_analysis").count() >= 1


def test_timeout_simulation_records_failure(client, app):
    with app.app_context():
        a, b = Company.query.limit(2).all()
    client.post(
        "/compare",
        data={"company_a": a.id, "company_b": b.id, "analysis_type": "partnership", "simulate": "timeout"},
        follow_redirects=True,
    )
    with app.app_context():
        failed = TechnicalMonitoringEvent.query.filter_by(event_type="ai_analysis", success=False).count()
        assert failed >= 1
        metrics = dashboard_metrics()
        assert metrics["failed"] >= 1
        assert metrics["total"] == TechnicalMonitoringEvent.query.count() or metrics["total"] >= 1


def test_fault_simulation_is_not_counted_as_gemini_request(client, app):
    client.post("/system/simulate", data={"kind": "ai_timeout"}, follow_redirects=True)
    with app.app_context():
        assert TechnicalMonitoringEvent.query.filter_by(event_type="fault_simulation").count() == 1
        assert TechnicalMonitoringEvent.query.filter_by(event_type="gemini_api_request").count() == 0


def test_discovery_page(client, app):
    with app.app_context():
        company = Company.query.filter_by(symbol="7010").first()
    res = client.post("/discover", data={"company_a": company.id, "analysis_type": "partnership"})
    assert res.status_code == 200
    with app.app_context():
        discovery = Analysis.query.filter_by(company_a_id=company.id, company_b_id=None).order_by(Analysis.id.desc()).first()
        assert discovery is not None
        assert Recommendation.query.filter_by(analysis_id=discovery.id).count() == 5


def test_business_monitoring_pages_are_removed(client):
    for path in ("/partnerships", "/partnerships/create", "/partnerships/1"):
        assert client.get(path).status_code == 404
    page = client.get("/workspace").get_data(as_text=True)
    assert "مراقبة الشراكات" not in page
    assert "مراقبة النظام" in page
