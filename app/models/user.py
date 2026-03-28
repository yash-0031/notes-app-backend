import uuid
from datetime import datetime, timezone

from app import db
from sqlalchemy.dialects.postgresql import UUID


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    email = db.Column(
        db.String(255),
        unique=True,      
        nullable=False,  
        index=True,      
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False,
    )

    full_name = db.Column(
        db.String(100),
        nullable=True,    
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    notes = db.relationship(
        "Note",
        backref="owner",
        lazy=True,
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        """How this object looks when you print it (useful for debugging)."""
        return f"<User {self.email}>"

    def to_dict(self):
        """Convert to a dictionary (for JSON responses)."""
        return {
            "id": str(self.id),
            "email": self.email,
            "full_name": self.full_name,
            "created_at": self.created_at.isoformat(),
        }