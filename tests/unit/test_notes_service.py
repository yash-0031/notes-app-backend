from uuid import uuid4

import pytest

from app.models import PermissionType
from app.services.auth_service import AuthService
from app.services.notes_service import NotesService
from app.services.share_service import ShareService


def _register_user(email, full_name):
    return AuthService.register(
        email=email,
        password="Password123",
        full_name=full_name,
    )


def test_create_note_success(mock_celery):
    user = _register_user("owner@example.com", "Owner User")

    note = NotesService.create_note(
        user_id=str(user.id),
        title="  My Test Note  ",
        content="<p>Hello</p>",
    )

    assert note.user_id == user.id
    assert note.title == "My Test Note"
    assert note.content == "<p>Hello</p>"
    mock_celery["delay"].assert_called_once_with(str(note.id))


def test_create_note_no_content(mock_celery):
    user = _register_user("nocontent@example.com", "No Content User")

    note = NotesService.create_note(
        user_id=str(user.id),
        title="Note Without Content",
        content=None,
    )

    assert note.content is None
    mock_celery["delay"].assert_called_once_with(str(note.id))


def test_create_note_sanitizes_html(mock_celery):
    user = _register_user("sanitize@example.com", "Sanitize User")

    note = NotesService.create_note(
        user_id=str(user.id),
        title="Unsafe Note",
        content="<script>alert('xss')</script><p>Safe</p>",
    )

    assert "<script>" not in note.content
    assert "alert('xss')" in note.content
    assert "<p>Safe</p>" in note.content
    mock_celery["delay"].assert_called_once_with(str(note.id))


def test_list_notes_pagination(mock_celery):
    user = _register_user("pager@example.com", "Pager User")

    for index in range(25):
        NotesService.create_note(
            user_id=str(user.id),
            title=f"Note {index}",
            content=f"Content {index}",
        )

    result = NotesService.list_notes(user_id=str(user.id), page=1, per_page=10)

    assert len(result["notes"]) == 10
    assert result["pagination"]["total"] == 25
    assert result["pagination"]["pages"] == 3
    mock_celery["delay"].assert_called()


def test_list_notes_search(mock_celery):
    user = _register_user("search@example.com", "Search User")

    NotesService.create_note(
        user_id=str(user.id),
        title="Alpha Release",
        content="Planning note",
    )
    NotesService.create_note(
        user_id=str(user.id),
        title="Beta Launch",
        content="Launch checklist",
    )
    NotesService.create_note(
        user_id=str(user.id),
        title="Gamma Planning",
        content="Some other content",
    )

    result = NotesService.list_notes(user_id=str(user.id), search="Beta")

    assert len(result["notes"]) == 1
    assert result["notes"][0]["title"] == "Beta Launch"
    mock_celery["delay"].assert_called()


def test_list_notes_excludes_archived(mock_celery):
    user = _register_user("archive-list@example.com", "Archive List User")

    note_one = NotesService.create_note(
        user_id=str(user.id),
        title="Keep 1",
        content="A",
    )
    note_two = NotesService.create_note(
        user_id=str(user.id),
        title="Archive Me",
        content="B",
    )
    NotesService.create_note(
        user_id=str(user.id),
        title="Keep 2",
        content="C",
    )

    NotesService.archive_note(note_id=str(note_two.id), user_id=str(user.id))

    result = NotesService.list_notes(user_id=str(user.id), is_archived=False)

    assert len(result["notes"]) == 2
    assert {note["title"] for note in result["notes"]} == {"Keep 1", "Keep 2"}
    mock_celery["delay"].assert_called()


def test_get_note_owner_access(mock_celery):
    user = _register_user("owner-read@example.com", "Owner Read User")
    note = NotesService.create_note(
        user_id=str(user.id),
        title="Owned Note",
        content="Full content",
    )

    fetched = NotesService.get_note(note_id=str(note.id), user_id=str(user.id))

    assert fetched.id == note.id
    assert fetched.content == "Full content"
    mock_celery["delay"].assert_called_once_with(str(note.id))


def test_get_note_no_access(mock_celery):
    owner = _register_user("owner-no-access@example.com", "Owner")
    other = _register_user("other-no-access@example.com", "Other")
    note = NotesService.create_note(
        user_id=str(owner.id),
        title="Private Note",
        content="Secret",
    )

    with pytest.raises(PermissionError, match="You do not have access to this note"):
        NotesService.get_note(note_id=str(note.id), user_id=str(other.id))


def test_get_note_shared_viewer_access(mock_celery):
    owner = _register_user("viewer-owner@example.com", "Viewer Owner")
    viewer = _register_user("viewer@example.com", "Viewer")
    note = NotesService.create_note(
        user_id=str(owner.id),
        title="Shared Note",
        content="Shared content",
    )

    ShareService.share_note(
        note_id=str(note.id),
        owner_id=str(owner.id),
        recipient_email=viewer.email,
        permission="VIEWER",
    )

    fetched = NotesService.get_note(note_id=str(note.id), user_id=str(viewer.id))

    assert fetched.id == note.id
    assert fetched.content == "Shared content"


def test_get_note_not_found():
    user = _register_user("notfound@example.com", "Not Found")

    with pytest.raises(ValueError, match="Note not found"):
        NotesService.get_note(note_id=str(uuid4()), user_id=str(user.id))


def test_update_note_owner(mock_celery):
    user = _register_user("update-owner@example.com", "Update Owner")
    note = NotesService.create_note(
        user_id=str(user.id),
        title="Original Title",
        content="Original content",
    )

    updated = NotesService.update_note(
        note_id=str(note.id),
        user_id=str(user.id),
        title="Updated Title",
        content="<p>Updated content</p>",
    )

    assert updated.title == "Updated Title"
    assert updated.content == "<p>Updated content</p>"
    mock_celery["delay"].assert_called_with(str(note.id))


def test_update_note_editor_access(mock_celery):
    owner = _register_user("editor-owner@example.com", "Editor Owner")
    editor = _register_user("editor@example.com", "Editor")
    note = NotesService.create_note(
        user_id=str(owner.id),
        title="Editable Note",
        content="Before",
    )

    ShareService.share_note(
        note_id=str(note.id),
        owner_id=str(owner.id),
        recipient_email=editor.email,
        permission="EDITOR",
    )

    updated = NotesService.update_note(
        note_id=str(note.id),
        user_id=str(editor.id),
        content="After",
    )

    assert updated.content == "After"
    mock_celery["delay"].assert_called_with(str(note.id))


def test_update_note_viewer_cannot_edit(mock_celery):
    owner = _register_user("viewer-edit-owner@example.com", "Viewer Owner")
    viewer = _register_user("viewer-edit@example.com", "Viewer")
    note = NotesService.create_note(
        user_id=str(owner.id),
        title="Viewer Note",
        content="Before",
    )

    ShareService.share_note(
        note_id=str(note.id),
        owner_id=str(owner.id),
        recipient_email=viewer.email,
        permission="VIEWER",
    )

    with pytest.raises(
        PermissionError,
        match="You do not have permission to edit this note",
    ):
        NotesService.update_note(
            note_id=str(note.id),
            user_id=str(viewer.id),
            content="After",
        )


def test_archive_note_owner(mock_celery):
    user = _register_user("archive-owner@example.com", "Archive Owner")
    note = NotesService.create_note(
        user_id=str(user.id),
        title="Archive Target",
        content="Archive content",
    )

    NotesService.archive_note(note_id=str(note.id), user_id=str(user.id))

    archived = NotesService.get_note(note_id=str(note.id), user_id=str(user.id))
    assert archived.is_archived is True


def test_archive_note_non_owner(mock_celery):
    owner = _register_user("archive-non-owner@example.com", "Archive Owner")
    other = _register_user("archive-other@example.com", "Archive Other")
    note = NotesService.create_note(
        user_id=str(owner.id),
        title="Archive Protected",
        content="Archive content",
    )

    with pytest.raises(PermissionError, match="Only the note owner can delete it"):
        NotesService.archive_note(note_id=str(note.id), user_id=str(other.id))
