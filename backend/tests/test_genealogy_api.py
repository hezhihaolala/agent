from contextlib import contextmanager

from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.main import create_app


@contextmanager
def authenticated_client(tmp_path):
    settings = Settings(
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'genealogy.db'}",
        archive_dir=tmp_path / "archives",
        admin_username="admin",
        admin_password="correct horse battery staple",
    )
    with TestClient(create_app(settings)) as client:
        login = client.post(
            "/api/auth/login",
            json={
                "username": "admin",
                "password": "correct horse battery staple",
            },
        )
        assert login.status_code == 200
        client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
        yield client


def create_person(client, name, gender):
    response = client.post(
        "/api/persons",
        json={"name": name, "gender": gender, "verification_status": "verified"},
    )
    assert response.status_code == 201
    return response.json()


def test_person_crud_requires_authentication_and_creates_audit_log(tmp_path):
    with authenticated_client(tmp_path) as client:
        anonymous = TestClient(client.app).get("/api/persons")
        person = create_person(client, "张明远", "male")
        updated = client.patch(
            f"/api/persons/{person['id']}",
            json={"native_place": "江苏苏州"},
        )
        listed = client.get("/api/persons")
        audits = client.get("/api/audit-logs")
        deleted = client.delete(f"/api/persons/{person['id']}")

    assert anonymous.status_code == 401
    assert updated.status_code == 200
    assert updated.json()["native_place"] == "江苏苏州"
    assert [item["name"] for item in listed.json()] == ["张明远"]
    assert any(item["action"] == "person.created" for item in audits.json())
    assert deleted.status_code == 204


def test_relationship_path_duplicate_and_cycle_validation(tmp_path):
    with authenticated_client(tmp_path) as client:
        child = create_person(client, "张明远", "male")
        mother = create_person(client, "陈素贞", "female")
        grandfather = create_person(client, "陈守义", "male")

        first = client.post(
            "/api/relationships",
            json={
                "kind": "parent",
                "person_id": child["id"],
                "relative_id": mother["id"],
                "verification_status": "verified",
            },
        )
        second = client.post(
            "/api/relationships",
            json={
                "kind": "parent",
                "person_id": mother["id"],
                "relative_id": grandfather["id"],
                "verification_status": "verified",
            },
        )
        duplicate = client.post(
            "/api/relationships",
            json={
                "kind": "parent",
                "person_id": child["id"],
                "relative_id": mother["id"],
                "verification_status": "verified",
            },
        )
        cycle = client.post(
            "/api/relationships",
            json={
                "kind": "parent",
                "person_id": grandfather["id"],
                "relative_id": child["id"],
                "verification_status": "verified",
            },
        )
        path = client.get(
            "/api/relationships/path",
            params={"source_id": child["id"], "target_id": grandfather["id"]},
        )

    assert first.status_code == 201
    assert second.status_code == 201
    assert duplicate.status_code == 409
    assert cycle.status_code == 409
    assert "祖先循环" in cycle.json()["detail"]
    assert path.status_code == 200
    assert path.json()["label"] == "外祖父"
    assert [step["person_name"] for step in path.json()["steps"]] == [
        "张明远",
        "陈素贞",
        "陈守义",
    ]
