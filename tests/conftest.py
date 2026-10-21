import pytest
from config import Config
from app import create_app
from app.models import db


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    LLM_API_KEY = ""


@pytest.fixture()
def app():
    application = create_app(TestConfig)
    yield application
    with application.app_context():
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()
