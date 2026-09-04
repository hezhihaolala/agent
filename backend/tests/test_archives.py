import hashlib
from contextlib import contextmanager

from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.main import create_app


@contextmanager
def archive_client(tmp_path):
    archive_dir = tmp_path / "archives"
    settings = Settings(
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'archives.db'}",
        archive_dir=archive_dir,
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
        client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
        yield client, archive_dir


def upload_pdf(client):
    content = b"%PDF-1.4\nprivate family record\n%%EOF"
    response = client.post(
        "/api/sources",
        data={
            "title": "民国族谱原件",
            "source_type": "document",
            "era": "民国",
            "provenance": "家中旧藏",
            "verification_status": "verified",
        },
        files={"file": ("family-record.pdf", content, "application/pdf")},
    )
    return response, content


def test_pdf_is_hashed_stored_randomly_and_download_is_private(tmp_path):
    with archive_client(tmp_path) as (client, archive_dir):
        response, content = upload_pdf(client)
        assert response.status_code == 201
        source = response.json()
        stored_files = list(archive_dir.iterdir())
        download = client.get(f"/api/sources/{source['id']}/download")

        with TestClient(client.app) as anonymous:
            rejected = anonymous.get(f"/api/sources/{source['id']}/download")

    assert source["original_filename"] == "family-record.pdf"
    assert source["sha256"] == hashlib.sha256(content).hexdigest()
    assert len(stored_files) == 1
    assert stored_files[0].name != "family-record.pdf"
    assert stored_files[0].suffix == ".pdf"
    assert download.status_code == 200
    assert download.content == content
    assert rejected.status_code == 401


def test_executable_upload_is_rejected_without_writing_a_file(tmp_path):
    with archive_client(tmp_path) as (client, archive_dir):
        response = client.post(
            "/api/sources",
            data={"title": "危险文件", "source_type": "document"},
            files={
                "file": (
                    "malware.exe",
                    b"MZ dangerous",
                    "application/x-msdownload",
                )
            },
        )

    assert response.status_code == 415
    assert list(archive_dir.iterdir()) == []


def test_source_can_be_linked_to_a_person(tmp_path):
    with archive_client(tmp_path) as (client, _):
        person = client.post(
            "/api/persons",
            json={"name": "张明远", "gender": "male"},
        ).json()
        source, _ = upload_pdf(client)
        linked = client.post(
            f"/api/sources/{source.json()['id']}/links",
            json={
                "entity_type": "person",
                "entity_id": person["id"],
                "field_name": "biography",
            },
        )
        detail = client.get(f"/api/sources/{source.json()['id']}")

    assert linked.status_code == 201
    assert linked.json()["entity_id"] == person["id"]
    assert detail.status_code == 200
    assert detail.json()["links"][0]["field_name"] == "biography"
