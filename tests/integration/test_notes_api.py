from io import BytesIO

from app import db
from app.models import NoteEmbedding
from app.api.v1 import upload as upload_module


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
    return login_response.get_json()


def test_auth_register_login_me_and_refresh(client):
    auth = _register_and_login(
        client,
        "api-auth@example.com",
        "Password123",
        "API Auth User",
    )

    me_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {auth['access_token']}"},
    )
    assert me_response.status_code == 200
    assert me_response.get_json()["user"]["email"] == "api-auth@example.com"

    refresh_response = client.post(
        "/api/v1/auth/refresh",
        headers={"Authorization": f"Bearer {auth['refresh_token']}"},
    )
    assert refresh_response.status_code == 200
    assert refresh_response.get_json()["access_token"]


def test_notes_crud_end_to_end(client, auth_headers):
    create_response = client.post(
        "/api/v1/notes",
        json={
            "title": "End-to-End Note",
            "content": "<p>Original content</p>",
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 201, create_response.get_json()
    note = create_response.get_json()["note"]

    list_response = client.get("/api/v1/notes", headers=auth_headers)
    assert list_response.status_code == 200
    assert len(list_response.get_json()["notes"]) == 1

    get_response = client.get(f"/api/v1/notes/{note['id']}", headers=auth_headers)
    assert get_response.status_code == 200
    assert get_response.get_json()["note"]["content"] == "<p>Original content</p>"

    update_response = client.put(
        f"/api/v1/notes/{note['id']}",
        json={
            "title": "Updated End-to-End Note",
            "content": "Updated content",
        },
        headers=auth_headers,
    )
    assert update_response.status_code == 200
    assert update_response.get_json()["note"]["title"] == "Updated End-to-End Note"

    delete_response = client.delete(f"/api/v1/notes/{note['id']}", headers=auth_headers)
    assert delete_response.status_code == 200

    archived_response = client.get(
        "/api/v1/notes?is_archived=true",
        headers=auth_headers,
    )
    assert archived_response.status_code == 200
    archived_notes = archived_response.get_json()["notes"]
    assert len(archived_notes) == 1
    assert archived_notes[0]["id"] == note["id"]


def test_sharing_and_shared_listing(client, auth_headers, second_user_headers):
    create_response = client.post(
        "/api/v1/notes",
        json={
            "title": "Shared API Note",
            "content": "Shared content",
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 201, create_response.get_json()
    note = create_response.get_json()["note"]

    share_response = client.post(
        f"/api/v1/notes/{note['id']}/share",
        json={
            "email": "second.user@example.com",
            "permission": "VIEWER",
        },
        headers=auth_headers,
    )
    assert share_response.status_code == 201, share_response.get_json()
    share = share_response.get_json()["share"]

    shared_response = client.get("/api/v1/shared", headers=second_user_headers)
    assert shared_response.status_code == 200
    assert len(shared_response.get_json()["notes"]) == 1
    assert shared_response.get_json()["notes"][0]["id"] == note["id"]

    revoke_response = client.delete(
        f"/api/v1/notes/{note['id']}/share/{share['id']}",
        headers=auth_headers,
    )
    assert revoke_response.status_code == 200

    shared_after_revoke = client.get("/api/v1/shared", headers=second_user_headers)
    assert shared_after_revoke.status_code == 200
    assert shared_after_revoke.get_json()["notes"] == []


def test_query_endpoint_returns_answer_and_sources(client, auth_headers, mock_openai):
    create_response = client.post(
        "/api/v1/notes",
        json={
            "title": "Queryable Note",
            "content": "The release is scheduled for Friday.",
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 201, create_response.get_json()
    note = create_response.get_json()["note"]

    db.session.add(
        NoteEmbedding(
            note_id=note["id"],
            chunk_text="The release is scheduled for Friday.",
            embedding=[0.1] * 1536,
            metadata_={"chunk_index": 0},
        )
    )
    db.session.commit()

    query_response = client.post(
        "/api/v1/query",
        json={
            "question": "When is the release?",
            "top_k": 3,
        },
        headers=auth_headers,
    )

    assert query_response.status_code == 200, query_response.get_json()
    payload = query_response.get_json()
    assert payload["answer"] == "Mocked AI answer"
    assert len(payload["sources"]) == 1
    assert payload["sources"][0]["note_id"] == note["id"]


def test_upload_pdf_success(client, auth_headers, monkeypatch):
    monkeypatch.setattr(upload_module, "extract_text_from_pdf", lambda file: "PDF extracted content")

    upload_response = client.post(
        "/api/v1/upload",
        data={
            "file": (BytesIO(b"%PDF-1.4 fake"), "sample.pdf"),
        },
        content_type="multipart/form-data",
        headers=auth_headers,
    )

    assert upload_response.status_code == 201, upload_response.get_json()
    note = upload_response.get_json()["note"]
    assert note["title"] == "PDF: sample"
    assert note["content"] == "PDF extracted content"
