import uuid
from datetime import datetime, timezone

from app import db
from sqlalchemy.dialects.postgresql import UUID


class Note(db.Model):
    __tablename__ = "notes"

    id = db.Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True, 
    )

    title = db.Column(
        db.String(500),
        nullable=False,
    )

    content = db.Column(
        db.Text,      
        nullable=True, 
    )

    is_archived = db.Column(
        db.Boolean,
        default=False,
    )

    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    embeddings = db.relationship(
        "NoteEmbedding",
        backref="note",
        lazy=True,
        cascade="all, delete-orphan",
    )

    shares = db.relationship(
        "Share",
        backref="note",
        lazy=True,
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Note '{self.title[:30]}...'>"

    def to_dict(self, include_content=True):
        result = {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "title": self.title,
            "is_archived": self.is_archived,
            "share_count": len(self.shares),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_at": self.created_at.isoformat(),
        }
        if include_content:
            result["content"] = self.content
        return result
