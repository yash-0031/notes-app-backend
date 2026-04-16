from datetime import datetime, timedelta, timezone

from app import db
from app.models import Note, NoteEmbedding, Share, PermissionType
from app.services.auth_service import AuthService
from app.services.notes_service import NotesService
from app.services.query_service import QueryService


def _register_user(email, full_name):
    return AuthService.register(
        email=email,
        password="Password123",
        full_name=full_name,
    )


def test_query_no_notes():
    user = _register_user("query-empty@example.com", "Query Empty")

    result = QueryService.query(user_id=str(user.id), question="What do I know?")

    assert result["answer"].startswith("You don't have any notes yet")
    assert result["sources"] == []


def test_query_success(mock_openai):
    user = _register_user("query-success@example.com", "Query Success")
    note = NotesService.create_note(
        user_id=str(user.id),
        title="Project Roadmap",
        content="We should ship the feature next week.",
    )

    db.session.add(
        NoteEmbedding(
            note_id=note.id,
            chunk_text="We should ship the feature next week.",
            embedding=[0.1] * 1536,
            metadata_={"chunk_index": 0},
        )
    )
    db.session.commit()

    result = QueryService.query(user_id=str(user.id), question="When do we ship?", top_k=3)

    assert result["answer"] == "Mocked AI answer"
    assert len(result["sources"]) == 1
    assert result["sources"][0]["note_id"] == str(note.id)
    assert result["sources"][0]["note_title"] == "Project Roadmap"
    assert mock_openai["get_embedding"].called
    assert mock_openai["generate_answer"].called


def test_query_filters_shared_by_owner_for_summary(mock_openai):
    recipient = _register_user("query-recipient@example.com", "Query Recipient")
    soham = _register_user("soham.demo@example.com", "Soham Kulkarni")
    yash = _register_user("yash.demo@example.com", "Yash Andure")

    shared_note = NotesService.create_note(
        user_id=str(soham.id),
        title="Distributed Systems Revision",
        content="Consensus, leader election, replication, and CAP theorem.",
    )
    own_note = NotesService.create_note(
        user_id=str(yash.id),
        title="Own Personal Note",
        content="This should not be used for the Soham summary filter.",
    )

    db.session.add(
        Share(
            note_id=shared_note.id,
            shared_with_user_id=recipient.id,
            permission=PermissionType.VIEWER,
        )
    )
    db.session.add(
        NoteEmbedding(
            note_id=shared_note.id,
            chunk_text="Consensus, leader election, replication, and CAP theorem.",
            embedding=[0.1] * 1536,
            metadata_={"chunk_index": 0},
        )
    )
    db.session.add(
        NoteEmbedding(
            note_id=own_note.id,
            chunk_text="This should not be used for the Soham summary filter.",
            embedding=[0.1] * 1536,
            metadata_={"chunk_index": 0},
        )
    )
    db.session.commit()

    result = QueryService.query(
        user_id=str(recipient.id),
        question="Summarize everything shared by Soham",
        top_k=5,
    )

    assert result["answer"] == "Mocked AI answer"
    assert len(result["sources"]) == 1
    assert result["sources"][0]["note_id"] == str(shared_note.id)
    assert result["sources"][0]["note_title"] == "Distributed Systems Revision"
    assert mock_openai["generate_answer"].called


def test_query_uses_summary_fallback_when_model_returns_no_text(mock_openai):
    recipient = _register_user("summary-recipient@example.com", "Summary Recipient")
    soham = _register_user("summary-soham@example.com", "Soham Kulkarni")

    shared_note = NotesService.create_note(
        user_id=str(soham.id),
        title="Cloud Lab Viva",
        content="Prepare answers on containers, orchestration basics, scaling, and monitoring.",
    )

    db.session.add(
        Share(
            note_id=shared_note.id,
            shared_with_user_id=recipient.id,
            permission=PermissionType.VIEWER,
        )
    )
    db.session.add(
        NoteEmbedding(
            note_id=shared_note.id,
            chunk_text="Prepare answers on containers, orchestration basics, scaling, and monitoring.",
            embedding=[0.1] * 1536,
            metadata_={"chunk_index": 0},
        )
    )
    db.session.commit()

    mock_openai["generate_answer"].return_value = "I couldn't find this information in your notes."

    result = QueryService.query(
        user_id=str(recipient.id),
        question="Summarize everything shared by Soham",
        top_k=5,
    )

    assert result["answer"].startswith("Here is a summary from the matching shared notes:")
    assert "Cloud Lab Viva" in result["answer"]


def test_query_respects_latest_note_window(app, mock_openai):
    app.config["AI_QUERY_MAX_NOTES"] = 2

    user = _register_user("latest-window@example.com", "Latest Window")

    first_note = NotesService.create_note(
        user_id=str(user.id),
        title="Old Note",
        content="Old context that should be excluded from AI search.",
    )
    second_note = NotesService.create_note(
        user_id=str(user.id),
        title="Recent Note",
        content="Recent context that should stay searchable.",
    )
    third_note = NotesService.create_note(
        user_id=str(user.id),
        title="Newest Note",
        content="Newest context that should stay searchable.",
    )

    base_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    Note.query.filter_by(id=first_note.id).update({"updated_at": base_time})
    Note.query.filter_by(id=second_note.id).update({"updated_at": base_time + timedelta(days=1)})
    Note.query.filter_by(id=third_note.id).update({"updated_at": base_time + timedelta(days=2)})

    db.session.add_all(
        [
            NoteEmbedding(
                note_id=first_note.id,
                chunk_text="Old context that should be excluded from AI search.",
                embedding=[0.1] * 1536,
                metadata_={"chunk_index": 0},
            ),
            NoteEmbedding(
                note_id=second_note.id,
                chunk_text="Recent context that should stay searchable.",
                embedding=[0.1] * 1536,
                metadata_={"chunk_index": 0},
            ),
            NoteEmbedding(
                note_id=third_note.id,
                chunk_text="Newest context that should stay searchable.",
                embedding=[0.1] * 1536,
                metadata_={"chunk_index": 0},
            ),
        ]
    )
    db.session.commit()

    result = QueryService.query(
        user_id=str(user.id),
        question="Summarize everything in my notes",
        top_k=5,
    )

    returned_titles = {source["note_title"] for source in result["sources"]}
    assert returned_titles == {"Recent Note", "Newest Note"}


def test_get_index_status_reports_search_window(app):
    app.config["AI_QUERY_MAX_NOTES"] = 1

    user = _register_user("status-window@example.com", "Status Window")

    older_note = NotesService.create_note(
        user_id=str(user.id),
        title="Older Indexed Note",
        content="This note is already indexed.",
    )
    newer_note = NotesService.create_note(
        user_id=str(user.id),
        title="Newest Pending Note",
        content="This note should be in the active AI window.",
    )

    base_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    Note.query.filter_by(id=older_note.id).update({"updated_at": base_time})
    Note.query.filter_by(id=newer_note.id).update({"updated_at": base_time + timedelta(days=1)})

    db.session.add(
        NoteEmbedding(
            note_id=older_note.id,
            chunk_text="This note is already indexed.",
            embedding=[0.1] * 1536,
            metadata_={"chunk_index": 0},
        )
    )
    db.session.commit()

    status = QueryService.get_index_status(user_id=str(user.id))

    assert status["search_window_limit"] == 1
    assert status["accessible_total_notes"] == 2
    assert status["total_notes"] == 1
    assert status["indexed_notes"] == 0
    assert status["pending_notes"] == 1
    assert status["is_ready"] is False
