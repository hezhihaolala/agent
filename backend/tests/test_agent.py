from contextlib import contextmanager

from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.main import create_app
from backend.tests.fakes import FakeModelClient


@contextmanager
def agent_client(tmp_path, model_result=None, model_error=None):
    settings = Settings(
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'agent.db'}",
        archive_dir=tmp_path / "archives",
        admin_password="correct horse battery staple",
    )
    model = FakeModelClient(model_result, model_error)
    with TestClient(create_app(settings, model_client=model)) as client:
        login = client.post(
            "/api/auth/login",
            json={
                "username": "admin",
                "password": "correct horse battery staple",
            },
        )
        client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
        yield client, model


def add_person(client, name, gender):
    return client.post(
        "/api/persons", json={"name": name, "gender": gender}
    ).json()


def test_relationship_answer_uses_deterministic_path_and_linked_source(tmp_path):
    intent = {
        "kind": "relationship_query",
        "source_name": "张明远",
        "target_name": "陈守义",
    }
    with agent_client(tmp_path, intent) as (client, model):
        child = add_person(client, "张明远", "male")
        mother = add_person(client, "陈素贞", "female")
        grandfather = add_person(client, "陈守义", "male")
        client.post(
            "/api/relationships",
            json={"kind": "parent", "person_id": child["id"], "relative_id": mother["id"]},
        )
        second_relationship = client.post(
            "/api/relationships",
            json={"kind": "parent", "person_id": mother["id"], "relative_id": grandfather["id"]},
        ).json()
        source = client.post(
            "/api/sources",
            data={"title": "陈氏族谱", "source_type": "document", "verification_status": "verified"},
            files={"file": ("record.pdf", b"%PDF-1.4\nrecord\n%%EOF", "application/pdf")},
        ).json()
        client.post(
            f"/api/sources/{source['id']}/links",
            json={
                "entity_type": "relationship",
                "entity_id": second_relationship["id"],
            },
        )

        response = client.post("/api/agent/query", json={"message": "张明远和陈守义是什么关系？"})

    assert response.status_code == 200
    assert model.messages == ["张明远和陈守义是什么关系？"]
    assert response.json()["type"] == "answer"
    assert response.json()["relationship"]["label"] == "外祖父"
    assert response.json()["sources"][0]["title"] == "陈氏族谱"
    assert "陈守义是张明远的外祖父" in response.json()["answer"]


def test_agent_reports_ambiguous_names_and_missing_paths(tmp_path):
    intent = {
        "kind": "relationship_query",
        "source_name": "张明远",
        "target_name": "陈守义",
    }
    with agent_client(tmp_path, intent) as (client, _):
        add_person(client, "张明远", "male")
        add_person(client, "张明远", "male")
        add_person(client, "陈守义", "male")
        ambiguous = client.post("/api/agent/query", json={"message": "查询关系"})

    assert ambiguous.status_code == 409
    assert "重名" in ambiguous.json()["detail"]

    with agent_client(tmp_path / "missing", intent) as (client, _):
        add_person(client, "张明远", "male")
        add_person(client, "陈守义", "male")
        missing = client.post("/api/agent/query", json={"message": "查询关系"})

    assert missing.status_code == 404
    assert "路径" in missing.json()["detail"]


def test_agent_handles_timeout_and_malformed_model_output(tmp_path):
    with agent_client(tmp_path / "timeout", model_error=TimeoutError()) as (client, _):
        timeout = client.post("/api/agent/query", json={"message": "查询关系"})

    with agent_client(tmp_path / "malformed", {"kind": "unexpected"}) as (client, _):
        malformed = client.post("/api/agent/query", json={"message": "查询关系"})

    assert timeout.status_code == 503
    assert malformed.status_code == 502


def test_conflicting_source_is_marked_for_verification(tmp_path):
    intent = {
        "kind": "relationship_query",
        "source_name": "张明远",
        "target_name": "陈素贞",
    }
    with agent_client(tmp_path, intent) as (client, _):
        child = add_person(client, "张明远", "male")
        mother = add_person(client, "陈素贞", "female")
        client.post(
            "/api/relationships",
            json={"kind": "parent", "person_id": child["id"], "relative_id": mother["id"]},
        )
        source = client.post(
            "/api/sources",
            data={"title": "待考口述", "source_type": "text", "verification_status": "conflicting"},
            files={"file": ("memo.txt", b"conflicting memory", "text/plain")},
        ).json()
        client.post(
            f"/api/sources/{source['id']}/links",
            json={"entity_type": "person", "entity_id": mother["id"]},
        )
        response = client.post("/api/agent/query", json={"message": "查询关系"})

    assert response.status_code == 200
    assert response.json()["verification_status"] == "conflicting"
    assert "待核实" in response.json()["answer"]
