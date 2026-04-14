from app import db
from app.models import NoteEmbedding
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
