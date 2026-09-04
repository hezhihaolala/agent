from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient


@contextmanager
def app_client(tmp_path):
    try:
        from backend.app.config import Settings
        from backend.app.main import create_app
    except ModuleNotFoundError as error:
        pytest.fail(f"后端应用尚未实现: {error}")

    settings = Settings(
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        archive_dir=tmp_path / "archives",
        admin_username="admin",
        admin_password="correct horse battery staple",
        session_cookie_secure=False,
    )
    with TestClient(create_app(settings)) as client:
        yield client


def test_health_check_is_public(tmp_path):
    with app_client(tmp_path) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_login_sets_session_and_returns_csrf(tmp_path):
    with app_client(tmp_path) as client:
        response = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "correct horse battery staple"},
        )
        current = client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.json()["username"] == "admin"
    assert response.json()["csrf_token"]
    assert "guiyuan_session=" in response.headers["set-cookie"]
    assert "HttpOnly" in response.headers["set-cookie"]
    assert current.status_code == 200
    assert current.json()["username"] == "admin"


def test_wrong_password_and_anonymous_session_are_rejected(tmp_path):
    with app_client(tmp_path) as client:
        current = client.get("/api/auth/me")
        response = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "wrong"},
        )

    assert current.status_code == 401
    assert response.status_code == 401
    assert response.json()["detail"] == "用户名或密码错误"


def test_logout_requires_matching_csrf_token(tmp_path):
    with app_client(tmp_path) as client:
        login = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "correct horse battery staple"},
        )
        rejected = client.post("/api/auth/logout")
        accepted = client.post(
            "/api/auth/logout",
            headers={"X-CSRF-Token": login.json()["csrf_token"]},
        )
        current = client.get("/api/auth/me")

    assert rejected.status_code == 403
    assert accepted.status_code == 204
    assert current.status_code == 401
