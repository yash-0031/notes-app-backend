import pytest

from app.models import PermissionType, Share
from app.services.auth_service import AuthService
from app.services.notes_service import NotesService
from app.services.share_service import ShareService


def _register_user(email, full_name):
    return AuthService.register(
        email=email,
        password="Password123",
        full_name=full_name,
    )


def test_share_note_success(mock_celery):
    owner = _register_user("share-owner@example.com", "Share Owner")
    recipient = _register_user("share-recipient@example.com", "Share Recipient")
    note = NotesService.create_note(
        user_id=str(owner.id),
        title="Shareable Note",
        content="Share content",
    )

    share = ShareService.share_note(
        note_id=str(note.id),
        owner_id=str(owner.id),
        recipient_email=recipient.email,
        permission="EDITOR",
    )

    assert share.note_id == note.id
    assert share.shared_with_user_id == recipient.id
    assert share.permission == PermissionType.EDITOR


def test_share_note_not_owner(mock_celery):
    owner = _register_user("share-not-owner@example.com", "Share Owner")
    other = _register_user("share-not-owner-2@example.com", "Other User")
    recipient = _register_user("share-target@example.com", "Share Target")
    note = NotesService.create_note(
        user_id=str(owner.id),
        title="Private Note",
        content="Secret",
    )

    with pytest.raises(PermissionError, match="Only the note owner can share it"):
        ShareService.share_note(
            note_id=str(note.id),
            owner_id=str(other.id),
            recipient_email=recipient.email,
            permission="VIEWER",
        )


def test_share_note_self(mock_celery):
    owner = _register_user("share-self@example.com", "Share Self")
    note = NotesService.create_note(
        user_id=str(owner.id),
        title="Self Share Note",
        content="Secret",
    )

    with pytest.raises(ValueError, match="You cannot share a note with yourself"):
        ShareService.share_note(
            note_id=str(note.id),
            owner_id=str(owner.id),
            recipient_email=owner.email,
            permission="VIEWER",
        )


def test_share_note_nonexistent_recipient(mock_celery):
    owner = _register_user("share-missing@example.com", "Share Owner")
    note = NotesService.create_note(
        user_id=str(owner.id),
        title="Recipient Missing",
        content="Secret",
    )

    with pytest.raises(ValueError, match="No user found"):
        ShareService.share_note(
            note_id=str(note.id),
            owner_id=str(owner.id),
            recipient_email="missing@example.com",
            permission="VIEWER",
        )


def test_share_note_duplicate_updates_permission(mock_celery):
    owner = _register_user("share-update-owner@example.com", "Share Owner")
    recipient = _register_user("share-update-recipient@example.com", "Share Recipient")
    note = NotesService.create_note(
        user_id=str(owner.id),
        title="Duplicate Share Note",
        content="Secret",
    )

    first_share = ShareService.share_note(
        note_id=str(note.id),
        owner_id=str(owner.id),
        recipient_email=recipient.email,
        permission="VIEWER",
    )
    second_share = ShareService.share_note(
        note_id=str(note.id),
        owner_id=str(owner.id),
        recipient_email=recipient.email,
        permission="EDITOR",
    )

    assert second_share.id == first_share.id
    assert second_share.permission == PermissionType.EDITOR
    assert Share.query.filter_by(note_id=note.id, shared_with_user_id=recipient.id).count() == 1


def test_revoke_share_success(mock_celery):
    owner = _register_user("revoke-owner@example.com", "Revoke Owner")
    recipient = _register_user("revoke-recipient@example.com", "Revoke Recipient")
    note = NotesService.create_note(
        user_id=str(owner.id),
        title="Revoke Note",
        content="Secret",
    )
    share = ShareService.share_note(
        note_id=str(note.id),
        owner_id=str(owner.id),
        recipient_email=recipient.email,
        permission="VIEWER",
    )

    ShareService.revoke_share(
        share_id=str(share.id),
        note_id=str(note.id),
        owner_id=str(owner.id),
    )

    assert Share.query.get(share.id) is None


def test_revoke_share_not_owner(mock_celery):
    owner = _register_user("revoke-not-owner@example.com", "Revoke Owner")
    other = _register_user("revoke-other@example.com", "Revoke Other")
    recipient = _register_user("revoke-target@example.com", "Revoke Target")
    note = NotesService.create_note(
        user_id=str(owner.id),
        title="Protected Share",
        content="Secret",
    )
    share = ShareService.share_note(
        note_id=str(note.id),
        owner_id=str(owner.id),
        recipient_email=recipient.email,
        permission="VIEWER",
    )

    with pytest.raises(PermissionError, match="Only the note owner can manage shares"):
        ShareService.revoke_share(
            share_id=str(share.id),
            note_id=str(note.id),
            owner_id=str(other.id),
        )


def test_get_shared_with_me(mock_celery):
    owner = _register_user("shared-list-owner@example.com", "Shared List Owner")
    recipient = _register_user("shared-list-recipient@example.com", "Shared List Recipient")
    note_one = NotesService.create_note(
        user_id=str(owner.id),
        title="Shared One",
        content="A",
    )
    note_two = NotesService.create_note(
        user_id=str(owner.id),
        title="Shared Two",
        content="B",
    )

    ShareService.share_note(
        note_id=str(note_one.id),
        owner_id=str(owner.id),
        recipient_email=recipient.email,
        permission="VIEWER",
    )
    ShareService.share_note(
        note_id=str(note_two.id),
        owner_id=str(owner.id),
        recipient_email=recipient.email,
        permission="EDITOR",
    )

    shared = ShareService.get_shared_with_me(user_id=str(recipient.id))

    assert len(shared) == 2
    assert {note.title for note in shared} == {"Shared One", "Shared Two"}


def test_get_shared_with_me_excludes_archived(mock_celery):
    owner = _register_user("shared-archive-owner@example.com", "Shared Archive Owner")
    recipient = _register_user("shared-archive-recipient@example.com", "Shared Archive Recipient")
    note = NotesService.create_note(
        user_id=str(owner.id),
        title="Archive Later",
        content="A",
    )

    ShareService.share_note(
        note_id=str(note.id),
        owner_id=str(owner.id),
        recipient_email=recipient.email,
        permission="VIEWER",
    )
    NotesService.archive_note(note_id=str(note.id), user_id=str(owner.id))

    shared = ShareService.get_shared_with_me(user_id=str(recipient.id))

    assert shared == []
