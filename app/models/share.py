import uuid
import enum
from datetime import datetime, timezone

from app import db
from sqlalchemy.dialects.postgresql import UUID


class PermissionType(enum.Enum):
    VIEWER = "VIEWER"
    EDITOR = "EDITOR"

class Share(db.Model):
    __tablename__ = "shares"

    id = db.Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    note_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("notes.id", ondelete="CASCADE"),
        nullable=False,
    )

    shared_with_user_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    permission = db.Column(
        db.Enum(PermissionType),
        default=PermissionType.VIEWER,
        nullable=False,
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.UniqueConstraint(
            "note_id",
            "shared_with_user_id",
            name="unique_note_share",
        ),
    )

    shared_with_user = db.relationship(
        "User",
        foreign_keys=[shared_with_user_id],
        backref="shared_notes_received",
    )

    def __repr__(self):
        return f"<Share note={self.note_id} → user={self.shared_with_user_id} ({self.permission.value})>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "note_id": str(self.note_id),
            "shared_with_user_id": str(self.shared_with_user_id),
            "permission": self.permission.value,
            "created_at": self.created_at.isoformat(),
        }