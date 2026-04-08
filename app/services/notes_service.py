import bleach
from typing import Optional

from app import db
from app.models import Note, Share, PermissionType
from app.utils.permissions import can_user_read_note, can_user_edit_note, is_note_owner


class NotesService:
    ALLOWED_TAGS = [
        "p", "br", "strong", "em", "u", "h1", "h2", "h3",
        "ul", "ol", "li", "blockquote", "code", "pre", "a",
    ]
    ALLOWED_ATTRIBUTES = {
        "a": ["href", "title"],
    }

    @staticmethod
    def create_note(
        user_id: str,
        title: str,
        content: Optional[str] = None,
    ) -> Note:
        clean_content = None
        if content:
            clean_content = bleach.clean(
                content,
                tags=NotesService.ALLOWED_TAGS,
                attributes=NotesService.ALLOWED_ATTRIBUTES,
                strip=True,  # Remove tags entirely (don't escape them)
            )

        note = Note(
            user_id=user_id,
            title=title.strip(),
            content=clean_content,
        )

        db.session.add(note)
        db.session.commit()

        from app.tasks.embedding_tasks import generate_embeddings
        generate_embeddings.delay(str(note.id))

        return note

    @staticmethod
    def list_notes(
        user_id: str,
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None,
        is_archived: bool = False,
    ) -> dict:
        query = Note.query.filter_by(
            user_id=user_id,
            is_archived=is_archived,
        )

        # Apply search filter if provided
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                db.or_(
                    Note.title.ilike(search_term),
                    Note.content.ilike(search_term),
                )
            )

        query = query.order_by(Note.updated_at.desc())

        paginated = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False,  # Return empty list instead of 404 for invalid pages
        )

        return {
            "notes": [note.to_dict(include_content=False) for note in paginated.items],
            "pagination": {
                "page": paginated.page,
                "per_page": paginated.per_page,
                "total": paginated.total,
                "pages": paginated.pages,
                "has_next": paginated.has_next,
                "has_prev": paginated.has_prev,
            },
        }

    @staticmethod
    def get_note(note_id: str, user_id: str) -> Note:
        note = Note.query.get(note_id)

        if not note:
            raise ValueError("Note not found")

        if not can_user_read_note(user_id, note):
            raise PermissionError("You do not have access to this note")

        return note

    @staticmethod
    def update_note(note_id: str, user_id: str, **kwargs) -> Note:
        note = Note.query.get(note_id)

        if not note:
            raise ValueError("Note not found")

        if not can_user_edit_note(user_id, note):
            raise PermissionError("You do not have permission to edit this note")

        # Update only the fields that were provided
        if "title" in kwargs and kwargs["title"] is not None:
            note.title = kwargs["title"].strip()

        if "content" in kwargs:
            if kwargs["content"] is not None:
                note.content = bleach.clean(
                    kwargs["content"],
                    tags=NotesService.ALLOWED_TAGS,
                    attributes=NotesService.ALLOWED_ATTRIBUTES,
                    strip=True,
                )
            else:
                note.content = None

        if "is_archived" in kwargs:
            note.is_archived = kwargs["is_archived"]

        db.session.commit()

        if "content" in kwargs:
            from app.tasks.embedding_tasks import generate_embeddings
            generate_embeddings.delay(str(note.id))

        return note

    @staticmethod
    def archive_note(note_id: str, user_id: str) -> None:

        note = Note.query.get(note_id)

        if not note:
            raise ValueError("Note not found")

        if not is_note_owner(user_id, note):
            raise PermissionError("Only the note owner can delete it")

        note.is_archived = True
        db.session.commit()