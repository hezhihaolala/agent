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


def test_admin_can_change_password_with_current_password_and_csrf(tmp_path):
    with app_client(tmp_path) as client:
        login = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "correct horse battery staple"},
        )
        changed = client.post(
            "/api/auth/password",
            headers={"X-CSRF-Token": login.json()["csrf_token"]},
            json={
                "current_password": "correct horse battery staple",
                "new_password": "new correct horse battery staple",
            },
        )
        audit_logs = client.get("/api/audit-logs")
        old_login = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "correct horse battery staple"},
        )
        new_login = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "new correct horse battery staple"},
        )

    assert changed.status_code == 204
    assert any(item["action"] == "admin.password_changed" for item in audit_logs.json())
    assert old_login.status_code == 401
    assert new_login.status_code == 200


def test_password_change_rejects_wrong_current_or_short_new_password(tmp_path):
    with app_client(tmp_path) as client:
        login = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "correct horse battery staple"},
        )
        headers = {"X-CSRF-Token": login.json()["csrf_token"]}
        wrong_current = client.post(
            "/api/auth/password",
            headers=headers,
            json={"current_password": "wrong", "new_password": "new correct horse battery staple"},
        )
        short_new = client.post(
            "/api/auth/password",
            headers=headers,
            json={"current_password": "correct horse battery staple", "new_password": "too-short"},
        )

    assert wrong_current.status_code == 400
    assert wrong_current.json()["detail"] == "当前密码不正确"
    assert short_new.status_code == 422
