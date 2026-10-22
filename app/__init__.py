from flask import Flask
from config import Config
from app.models import db


def create_app(config_object=None):
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(config_object or Config)
    db.init_app(app)

    from app.auth import auth_bp, bootstrap_admin
    from app.views import bp as main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    with app.app_context():
        db.create_all()
        from app.seed import seed_if_empty

        seed_if_empty()
        bootstrap_admin()

    return app
