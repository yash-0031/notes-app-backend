from app import db
from app.models import NoteEmbedding, Share, PermissionType
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
