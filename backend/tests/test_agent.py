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


def test_parent_lookup_bypasses_model_and_returns_all_parents(tmp_path):
    with agent_client(tmp_path, {"kind": "unexpected"}) as (client, model):
        child = add_person(client, "贺志豪", "male")
        father = add_person(client, "贺万彬", "male")
        mother = add_person(client, "王录飞", "female")
        for parent in (father, mother):
            client.post(
                "/api/relationships",
                json={"kind": "parent", "person_id": child["id"], "relative_id": parent["id"]},
            )

        response = client.post("/api/agent/query", json={"message": "贺志豪的父母是谁"})

    assert response.status_code == 200
    assert model.messages == []
    assert response.json()["type"] == "relative_list"
    assert response.json()["relation_type"] == "parents"
    assert [item["steps"][-1]["person_name"] for item in response.json()["relationships"]] == [
        "贺万彬",
        "王录飞",
    ]
    assert response.json()["answer"].startswith("贺志豪的父母是贺万彬、王录飞")


def test_sibling_and_paternal_cousin_lookup_use_formal_relationships(tmp_path):
    with agent_client(tmp_path, {"kind": "unexpected"}) as (client, model):
        source = add_person(client, "贺志豪", "male")
        sister = add_person(client, "贺志兰", "female")
        cousin = add_person(client, "贺志梅", "female")
        client.post(
            "/api/relationships",
            json={"kind": "sibling", "person_id": source["id"], "relative_id": sister["id"]},
        )
        client.post(
            "/api/relationships",
            json={"kind": "paternal_cousin", "person_id": source["id"], "relative_id": cousin["id"]},
        )

        sibling = client.post("/api/agent/query", json={"message": "贺志豪的兄弟姊妹是谁？"})
        paternal_cousin = client.post("/api/agent/query", json={"message": "贺志豪的堂兄弟姊妹是谁"})

    assert sibling.status_code == 200
    assert sibling.json()["relationships"][0]["label"] == "姐妹"
    assert paternal_cousin.status_code == 200
    assert paternal_cousin.json()["relationships"][0]["label"] == "堂姐妹"
    assert model.messages == []


def test_inferred_sibling_lookup_includes_unknown_gender(tmp_path):
    with agent_client(tmp_path, {"kind": "unexpected"}) as (client, model):
        source = add_person(client, "贺志豪", "male")
        sibling = add_person(client, "贺志宁", "unknown")
        parent = add_person(client, "贺万彬", "male")
        for child in (source, sibling):
            client.post(
                "/api/relationships",
                json={"kind": "parent", "person_id": child["id"], "relative_id": parent["id"]},
            )

        response = client.post("/api/agent/query", json={"message": "贺志豪的兄弟姊妹是谁"})

    assert response.status_code == 200
    assert response.json()["relationships"][0]["label"] == "兄弟姐妹"
    assert model.messages == []


def test_relationship_answer_only_uses_sources_from_the_selected_edge(tmp_path):
    intent = {
        "kind": "relationship_query",
        "source_name": "贺志豪",
        "target_name": "王录飞",
    }
    with agent_client(tmp_path, intent) as (client, _):
        child = add_person(client, "贺志豪", "male")
        mother = add_person(client, "王录飞", "female")
        parent = client.post(
            "/api/relationships",
            json={"kind": "parent", "person_id": child["id"], "relative_id": mother["id"]},
        ).json()
        spouse = client.post(
            "/api/relationships",
            json={"kind": "spouse", "person_id": child["id"], "relative_id": mother["id"]},
        ).json()
        for title, status, relationship_id in (
            ("父母档案", "verified", parent["id"]),
            ("错误配偶档案", "conflicting", spouse["id"]),
        ):
            source = client.post(
                "/api/sources",
                data={"title": title, "source_type": "text", "verification_status": status},
                files={"file": (f"{title}.txt", title.encode(), "text/plain")},
            ).json()
            client.post(
                f"/api/sources/{source['id']}/links",
                json={"entity_type": "relationship", "entity_id": relationship_id},
            )

        response = client.post("/api/agent/query", json={"message": "查询关系"})

    assert response.status_code == 200
    assert response.json()["verification_status"] == "verified"
    assert [source["title"] for source in response.json()["sources"]] == ["父母档案"]


def test_polite_relative_question_falls_back_to_model(tmp_path):
    intent = {
        "kind": "relative_lookup",
        "source_name": "贺志豪",
        "relation_type": "parents",
    }
    with agent_client(tmp_path, intent) as (client, model):
        child = add_person(client, "贺志豪", "male")
        mother = add_person(client, "王录飞", "female")
        client.post(
            "/api/relationships",
            json={"kind": "parent", "person_id": child["id"], "relative_id": mother["id"]},
        )

        message = "请问贺志豪的父母是谁"
        response = client.post("/api/agent/query", json={"message": message})

    assert response.status_code == 200
    assert model.messages == [message]
