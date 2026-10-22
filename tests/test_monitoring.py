from app.models import Analysis, Company, Recommendation, TechnicalMonitoringEvent
from app.monitoring import dashboard_metrics


def test_home_loads(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "مِشراك" in res.get_data(as_text=True)
    assert "7020" in res.get_data(as_text=True)
    assert "2222" in res.get_data(as_text=True)


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
    page = client.get("/").get_data(as_text=True)
    assert "مراقبة الشراكات" not in page
    assert "مراقبة النظام" in page
