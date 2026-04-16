#!/usr/bin/env python3
import bcrypt
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import create_app, db
from app.models import Note, User
from app.services.notes_service import NotesService


DEMO_USERS = [
    {
        "email": "yash@noteshare.demo",
        "full_name": "Yash Andure",
        "password": "YashDemo@123",
        "notes": [
            {
                "title": "Product Launch Checklist",
                "content": (
                    "Finalize landing page copy, confirm beta user emails, "
                    "prepare launch metrics dashboard, and send the launch-day "
                    "status note by 9 AM."
                ),
            },
            {
                "title": "Backend Deployment Notes",
                "content": (
                    "Use Docker Compose for local demonstration. Verify database "
                    "migrations, Celery worker startup, and `/api/v1/health` "
                    "before sharing the demo."
                ),
            },
            {
                "title": "Investor Meeting Prep",
                "content": (
                    "Highlight user growth, explain AI-powered note search, and "
                    "show how shared notes improve collaboration for students."
                ),
            },
        ],
    },
    {
        "email": "soham@noteshare.demo",
        "full_name": "Soham Kulkarni",
        "password": "SohamDemo@123",
        "notes": [
            {
                "title": "Distributed Systems Revision",
                "content": (
                    "Focus on consensus basics, leader election, replication "
                    "strategies, and the CAP theorem before the exam."
                ),
            },
            {
                "title": "Hackathon Planning",
                "content": (
                    "Set up roles for frontend, backend, and presentation. Keep "
                    "the final demo small, polished, and easy to explain."
                ),
            },
            {
                "title": "Reading List",
                "content": (
                    "Finish the papers on vector search, retrieval augmented "
                    "generation, and evaluation of note-grounded assistants."
                ),
            },
        ],
    },
]


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def upsert_user(email: str, full_name: str, password: str) -> User:
    user = User.query.filter_by(email=email.lower().strip()).first()

    if user:
        user.full_name = full_name
        user.password_hash = hash_password(password)
    else:
        user = User(
            email=email.lower().strip(),
            full_name=full_name,
            password_hash=hash_password(password),
        )
        db.session.add(user)

    db.session.commit()
    return user


def upsert_note(user: User, title: str, content: str) -> None:
    note = Note.query.filter_by(user_id=user.id, title=title).first()

    if note:
        NotesService.update_note(
            note_id=str(note.id),
            user_id=str(user.id),
            title=title,
            content=content,
            is_archived=False,
        )
    else:
        NotesService.create_note(
            user_id=str(user.id),
            title=title,
            content=content,
        )


def seed_demo_data() -> None:
    for demo_user in DEMO_USERS:
        user = upsert_user(
            email=demo_user["email"],
            full_name=demo_user["full_name"],
            password=demo_user["password"],
        )

        for note in demo_user["notes"]:
            upsert_note(
                user=user,
                title=note["title"],
                content=note["content"],
            )

    print("Demo users and notes are seeded successfully.")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        seed_demo_data()
