from app.models import Note, Share, PermissionType


def get_accessible_note_ids(user_id: str) -> list:

    owned = Note.query.filter_by(
        user_id=user_id,
        is_archived=False,
    ).with_entities(Note.id).all()

    # Notes shared with the user
    shared = Share.query.filter_by(
        shared_with_user_id=user_id,
    ).with_entities(Share.note_id).all()

    all_ids = [row[0] for row in owned] + [row[0] for row in shared]
    return all_ids


def can_user_read_note(user_id: str, note: Note) -> bool:
    if str(note.user_id) == str(user_id):
        return True  # Owner can always read

    share = Share.query.filter_by(
        note_id=note.id,
        shared_with_user_id=user_id,
    ).first()
    return share is not None


def can_user_edit_note(user_id: str, note: Note) -> bool:
    if str(note.user_id) == str(user_id):
        return True 
    
    share = Share.query.filter_by(
        note_id=note.id,
        shared_with_user_id=user_id,
        permission=PermissionType.EDITOR,
    ).first()
    return share is not None


def is_note_owner(user_id: str, note: Note) -> bool:
    return str(note.user_id) == str(user_id)
