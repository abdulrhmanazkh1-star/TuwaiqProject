from flask import Flask
from config import Config
from app.models import db
from sqlalchemy import inspect, text


def _upgrade_portfolio_revision_schema():
    """Apply additive SQLite changes for databases created by earlier app runs."""
    inspector = inspect(db.engine)
    if "portfolio_revisions" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("portfolio_revisions")}
    if "workspace_status" in columns:
        return
    with db.engine.begin() as connection:
        connection.execute(text(
            "ALTER TABLE portfolio_revisions "
            "ADD COLUMN workspace_status VARCHAR(24) NOT NULL DEFAULT 'saved'"
        ))
        connection.execute(text(
            "UPDATE portfolio_revisions SET workspace_status = CASE event_type "
            "WHEN 'starter' THEN 'starter' WHEN 'generated' THEN 'generated' "
            "WHEN 'generation_error' THEN 'error' ELSE 'saved' END"
        ))


def create_app(config_object=None):
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(config_object or Config)
    db.init_app(app)

    from app.auth import auth_bp, bootstrap_admin
    from app.portfolio_studio import studio_bp
    from app.views import bp as main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(studio_bp)

    with app.app_context():
        db.create_all()
        _upgrade_portfolio_revision_schema()
        from app.seed import seed_if_empty

        seed_if_empty()
        bootstrap_admin()

    return app
