from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(16), nullable=False, default="user")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Company(db.Model):
    __tablename__ = "companies"
    id = db.Column(db.Integer, primary_key=True)
    identifier = db.Column(db.String(64), unique=True, nullable=False)
    official_name = db.Column(db.String(255), nullable=False)
    official_name_en = db.Column(db.String(255), nullable=False)
    symbol = db.Column(db.String(32), unique=True, nullable=False)
    sector = db.Column(db.String(128), nullable=False)
    subsector = db.Column(db.String(128))
    description = db.Column(db.Text, nullable=False)
    products_services = db.Column(db.Text, nullable=False)
    is_synthetic = db.Column(db.Boolean, default=True, nullable=False)
    source_url = db.Column(db.String(512))
    data_publication_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    financials = db.relationship("CompanyFinancial", backref="company", lazy=True)
    sources = db.relationship("CompanySource", backref="company", lazy=True)


class CompanyFinancial(db.Model):
    __tablename__ = "company_financials"
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    period_year = db.Column(db.Integer, nullable=False)
    revenue = db.Column(db.Float)
    net_income = db.Column(db.Float)
    total_assets = db.Column(db.Float)
    total_liabilities = db.Column(db.Float)
    current_assets = db.Column(db.Float)
    current_liabilities = db.Column(db.Float)
    market_cap = db.Column(db.Float)
    source_url = db.Column(db.String(512))
    is_synthetic = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class CompanySource(db.Model):
    __tablename__ = "company_sources"
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(512))
    published_at = db.Column(db.Date)
    notes = db.Column(db.Text)


class Analysis(db.Model):
    __tablename__ = "analyses"
    id = db.Column(db.Integer, primary_key=True)
    company_a_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    company_b_id = db.Column(db.Integer, db.ForeignKey("companies.id"))
    analysis_type = db.Column(db.String(64), nullable=False)
    direction = db.Column(db.String(32), default="a_to_b")
    status = db.Column(db.String(32), default="completed")
    scoring_version = db.Column(db.String(32), nullable=False)
    mode = db.Column(db.String(32), nullable=False)
    latency_ms = db.Column(db.Integer)
    error_message = db.Column(db.Text)
    report_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    company_a = db.relationship("Company", foreign_keys=[company_a_id])
    company_b = db.relationship("Company", foreign_keys=[company_b_id])
    scores = db.relationship("CompatibilityScore", backref="analysis", lazy=True)
    recommendations = db.relationship("Recommendation", backref="analysis", lazy=True)


class CompatibilityScore(db.Model):
    __tablename__ = "compatibility_scores"
    id = db.Column(db.Integer, primary_key=True)
    analysis_id = db.Column(db.Integer, db.ForeignKey("analyses.id"), nullable=False)
    criterion = db.Column(db.String(64), nullable=False)
    score = db.Column(db.Float)
    weight = db.Column(db.Float, nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    explanation = db.Column(db.Text)
    evidence = db.Column(db.Text)


class Recommendation(db.Model):
    __tablename__ = "recommendations"
    id = db.Column(db.Integer, primary_key=True)
    analysis_id = db.Column(db.Integer, db.ForeignKey("analyses.id"), nullable=False)
    candidate_company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    rank = db.Column(db.Integer, nullable=False)
    overall_score = db.Column(db.Float, nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    why = db.Column(db.Text)
    risks = db.Column(db.Text)
    limitations = db.Column(db.Text)
    candidate = db.relationship("Company")


class BusinessRelationship(db.Model):
    __tablename__ = "business_relationships"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    company_a_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    company_b_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    relationship_type = db.Column(db.String(64), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    planned_end_date = db.Column(db.Date)
    status = db.Column(db.String(32), default="draft", nullable=False)
    initial_budget = db.Column(db.Float)
    reporting_frequency = db.Column(db.String(32), default="monthly")
    is_simulated = db.Column(db.Boolean, default=True, nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    company_a = db.relationship("Company", foreign_keys=[company_a_id])
    company_b = db.relationship("Company", foreign_keys=[company_b_id])
    objectives = db.relationship("RelationshipObjective", backref="relationship", lazy=True)
    kpi_targets = db.relationship("KPITarget", backref="relationship", lazy=True)
    milestones = db.relationship("Milestone", backref="relationship", lazy=True)
    alerts = db.relationship("BusinessAlert", backref="relationship", lazy=True)


class RelationshipObjective(db.Model):
    __tablename__ = "relationship_objectives"
    id = db.Column(db.Integer, primary_key=True)
    relationship_id = db.Column(db.Integer, db.ForeignKey("business_relationships.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(64), default="operational")


class KPITarget(db.Model):
    __tablename__ = "kpi_targets"
    id = db.Column(db.Integer, primary_key=True)
    relationship_id = db.Column(db.Integer, db.ForeignKey("business_relationships.id"), nullable=False)
    name = db.Column(db.String(128), nullable=False)
    unit = db.Column(db.String(32), default="SAR")
    target_value = db.Column(db.Float, nullable=False)
    direction = db.Column(db.String(32), default="higher_better")
    range_min = db.Column(db.Float)
    range_max = db.Column(db.Float)
    period_label = db.Column(db.String(64), default="monthly")
    actuals = db.relationship("KPIActual", backref="target", lazy=True, order_by="KPIActual.period")


class KPIActual(db.Model):
    __tablename__ = "kpi_actuals"
    id = db.Column(db.Integer, primary_key=True)
    target_id = db.Column(db.Integer, db.ForeignKey("kpi_targets.id"), nullable=False)
    period = db.Column(db.String(32), nullable=False)
    actual_value = db.Column(db.Float, nullable=False)
    source = db.Column(db.String(32), default="manual")
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Milestone(db.Model):
    __tablename__ = "milestones"
    id = db.Column(db.Integer, primary_key=True)
    relationship_id = db.Column(db.Integer, db.ForeignKey("business_relationships.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    completed_at = db.Column(db.Date)
    status = db.Column(db.String(32), default="pending")
    progress_pct = db.Column(db.Float, default=0)


class BusinessAlert(db.Model):
    __tablename__ = "business_alerts"
    id = db.Column(db.Integer, primary_key=True)
    relationship_id = db.Column(db.Integer, db.ForeignKey("business_relationships.id"), nullable=False)
    kpi_target_id = db.Column(db.Integer, db.ForeignKey("kpi_targets.id"))
    severity = db.Column(db.String(32), nullable=False)
    status_label = db.Column(db.String(32), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    acknowledged = db.Column(db.Boolean, default=False)


class TechnicalMonitoringEvent(db.Model):
    __tablename__ = "technical_monitoring_events"
    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(64), nullable=False)
    success = db.Column(db.Boolean, nullable=False)
    latency_ms = db.Column(db.Integer)
    error_code = db.Column(db.String(64))
    tokens_in = db.Column(db.Integer)
    tokens_out = db.Column(db.Integer)
    estimated_cost_usd = db.Column(db.Float)
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class AIEvaluationResult(db.Model):
    __tablename__ = "ai_evaluation_results"
    id = db.Column(db.Integer, primary_key=True)
    analysis_id = db.Column(db.Integer, db.ForeignKey("analyses.id"), nullable=False)
    reviewer = db.Column(db.String(128))
    factual_support_score = db.Column(db.Float)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
