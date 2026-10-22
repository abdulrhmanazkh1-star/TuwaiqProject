import pytest
from config import Config
from app import create_app
from app.models import User, db
from werkzeug.security import generate_password_hash


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
    test_client = app.test_client()
    with app.app_context():
        db.session.add(User(
            username="test-admin",
            password_hash=generate_password_hash("test-password-123"),
            role="admin",
        ))
        db.session.commit()
    test_client.post("/login", data={
        "username": "test-admin",
        "password": "test-password-123",
        "role": "admin",
    })
    return test_client
