from backend.tests.test_agent import add_person, agent_client


def test_agent_change_is_only_written_after_confirmation(tmp_path):
    intent = {
        "kind": "create_child",
        "parent_name": "张明远",
        "person_name": "张予安",
        "gender": "male",
    }
    with agent_client(tmp_path, intent) as (client, _):
        add_person(client, "张明远", "male")
        before = len(client.get("/api/persons").json())
        preview = client.post(
            "/api/agent/query", json={"message": "新增张明远的儿子张予安"}
        )
        unchanged = len(client.get("/api/persons").json())
        confirmed = client.post(
            f"/api/change-drafts/{preview.json()['draft_id']}/confirm"
        )
        after = len(client.get("/api/persons").json())
        repeated = client.post(
            f"/api/change-drafts/{preview.json()['draft_id']}/confirm"
        )

    assert preview.status_code == 200
    assert preview.json()["type"] == "draft"
    assert before == unchanged
    assert after == before + 1
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"
    assert repeated.status_code == 409


def test_pending_draft_can_be_rejected_but_not_confirmed_afterward(tmp_path):
    intent = {
        "kind": "create_person",
        "person_name": "张予安",
        "gender": "male",
    }
    with agent_client(tmp_path, intent) as (client, _):
        preview = client.post("/api/agent/query", json={"message": "新增张予安"})
        rejected = client.post(
            f"/api/change-drafts/{preview.json()['draft_id']}/reject"
        )
        confirmed = client.post(
            f"/api/change-drafts/{preview.json()['draft_id']}/confirm"
        )
        detail = client.get(f"/api/change-drafts/{preview.json()['draft_id']}")

    assert rejected.status_code == 200
    assert detail.json()["status"] == "rejected"
    assert confirmed.status_code == 409
