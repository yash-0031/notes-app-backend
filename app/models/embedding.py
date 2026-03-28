import uuid
from datetime import datetime, timezone

from app import db
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector


class NoteEmbedding(db.Model):
    __tablename__ = "note_embeddings"

    id = db.Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    note_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("notes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    chunk_text = db.Column(
        db.Text,
        nullable=False,
    )

    embedding = db.Column(
        Vector(1536),
    )

    metadata_ = db.Column(
        "metadata", 
        JSONB,
        default={},
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self):
        preview = self.chunk_text[:50] if self.chunk_text else "empty"
        return f"<NoteEmbedding '{preview}...'>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "note_id": str(self.note_id),
            "chunk_text": self.chunk_text,
            "metadata": self.metadata_,
            "created_at": self.created_at.isoformat(),
        }