import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import text
from flask_jwt_extended import create_access_token


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


os.environ.setdefault("REDIS_URL", "memory://")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")

from app import create_app, db  # noqa: E402
from app.models import Note, NoteEmbedding, PermissionType, Share, User  # noqa: E402,F401
from app.services.auth_service import AuthService  # noqa: E402
from app.services import query_service as query_service_module  # noqa: E402
from app.tasks import embedding_tasks  # noqa: E402
from app.utils import ai_helper  # noqa: E402


TEST_USER_EMAIL = "test.user@example.com"
TEST_USER_PASSWORD = "Password123"
SECOND_USER_EMAIL = "second.user@example.com"
SECOND_USER_PASSWORD = "Password123"


def _register_and_login(client, email, password, full_name):
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": full_name,
        },
    )
    assert register_response.status_code == 201, register_response.get_json()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )
    assert login_response.status_code == 200, login_response.get_json()
    payload = login_response.get_json()
    return payload["user"], payload["access_token"], payload["refresh_token"]


@pytest.fixture(scope="session")
def app():
    app = create_app("testing")
    app.config["RATELIMIT_ENABLED"] = False

    ctx = app.app_context()
    ctx.push()

    db.session.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
    db.session.commit()
    db.create_all()

    yield app

    db.session.remove()
    db.drop_all()
    ctx.pop()


@pytest.fixture(scope="function", autouse=True)
def db_session(app):
    db.session.remove()
    db.drop_all()
    db.create_all()

    yield db.session

    db.session.rollback()
    db.session.remove()
    db.drop_all()


@pytest.fixture(scope="function")
def client(app):
    return app.test_client()


@pytest.fixture(scope="function")
def mock_openai(monkeypatch):
    embedding_vector = [0.1] * 1536

    get_embedding_mock = MagicMock(return_value=embedding_vector)
    get_embeddings_batch_mock = MagicMock(
        side_effect=lambda texts: [[0.1] * 1536 for _ in texts]
    )
    generate_answer_mock = MagicMock(return_value="Mocked AI answer")

    monkeypatch.setattr(ai_helper, "get_embedding", get_embedding_mock)
    monkeypatch.setattr(ai_helper, "get_embeddings_batch", get_embeddings_batch_mock)
    monkeypatch.setattr(ai_helper, "generate_answer", generate_answer_mock)
    monkeypatch.setattr(query_service_module, "get_embedding", get_embedding_mock)
    monkeypatch.setattr(query_service_module, "generate_answer", generate_answer_mock)
    monkeypatch.setattr(embedding_tasks, "get_embeddings_batch", get_embeddings_batch_mock)

    return {
        "get_embedding": get_embedding_mock,
        "get_embeddings_batch": get_embeddings_batch_mock,
        "generate_answer": generate_answer_mock,
    }


@pytest.fixture(scope="function", autouse=True)
def mock_celery(monkeypatch):
    delay_mock = MagicMock(return_value=None)
    monkeypatch.setattr(embedding_tasks.generate_embeddings, "delay", delay_mock)
    return {"delay": delay_mock}


@pytest.fixture(scope="function")
def auth_headers(client):
    user = AuthService.register(
        email=TEST_USER_EMAIL,
        password=TEST_USER_PASSWORD,
        full_name="Test User",
    )
    access_token = create_access_token(identity=str(user.id))
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture(scope="function")
def second_user_headers(client):
    user = AuthService.register(
        email=SECOND_USER_EMAIL,
        password=SECOND_USER_PASSWORD,
        full_name="Second User",
    )
    access_token = create_access_token(identity=str(user.id))
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture(scope="function")
def sample_note(client, auth_headers):
    response = client.post(
        "/api/v1/notes",
        json={
            "title": "Test Note",
            "content": "Test content",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()["note"]
