from app import db
from app.models import User, Note, Share, PermissionType
from app.utils.permissions import is_note_owner


class ShareService:

    @staticmethod
    def share_note(
        note_id: str,
        owner_id: str,
        recipient_email: str,
        permission: str = "VIEWER",
    ) -> Share:

        note = Note.query.get(note_id)
        if not note:
            raise ValueError("Note not found")

        # 2. Check ownership
        if not is_note_owner(owner_id, note):
            raise PermissionError("Only the note owner can share it")

        # 3. Find the recipient
        recipient = User.query.filter_by(
            email=recipient_email.lower().strip()
        ).first()

        if not recipient:
            raise ValueError(f"No user found with email: {recipient_email}")

        # 4. Prevent self-sharing
        if str(recipient.id) == str(owner_id):
            raise ValueError("You cannot share a note with yourself")

        # 5. Check for existing share
        existing_share = Share.query.filter_by(
            note_id=note_id,
            shared_with_user_id=recipient.id,
        ).first()

        if existing_share:
            # Update the permission instead of creating a duplicate
            permission_enum = PermissionType(permission)
            existing_share.permission = permission_enum
            db.session.commit()
            return existing_share

        # 6. Create the share
        permission_enum = PermissionType(permission)
        share = Share(
            note_id=note_id,
            shared_with_user_id=recipient.id,
            permission=permission_enum,
        )

        db.session.add(share)
        db.session.commit()

        return share

    @staticmethod
    def revoke_share(share_id: str, note_id: str, owner_id: str) -> None:
        """
        Remove a sharing relationship.

        Only the note owner can revoke shares.
        """
        note = Note.query.get(note_id)
        if not note:
            raise ValueError("Note not found")

        if not is_note_owner(owner_id, note):
            raise PermissionError("Only the note owner can manage shares")

        share = Share.query.get(share_id)
        if not share or str(share.note_id) != str(note_id):
            raise ValueError("Share not found")

        db.session.delete(share)
        db.session.commit()

    @staticmethod
    def get_shared_with_me(user_id: str) -> list:
        shared_notes = (
            db.session.query(Note, Share.permission)
            .join(Share, Share.note_id == Note.id)
            .filter(
                Share.shared_with_user_id == user_id,
                Note.is_archived == False,
            )
            .order_by(Note.updated_at.desc())
            .all()
        )

        return shared_notes

    @staticmethod
    def get_note_shares(note_id: str, owner_id: str) -> list:
        note = Note.query.get(note_id)
        if not note:
            raise ValueError("Note not found")

        if not is_note_owner(owner_id, note):
            raise PermissionError("Only the note owner can view shares")

        shares = Share.query.filter_by(note_id=note_id).all()
        return shares
