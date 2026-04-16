#!/usr/bin/env python3
import bcrypt
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import create_app, db
from app.models import Note, NoteEmbedding, Share, User
from app.services.notes_service import NotesService


def build_yash_notes() -> list[dict[str, str]]:
    return [
        {
            "title": "SEM 6 Project Timeline",
            "content": (
                "Our final year BCS project demo for SPPU should be ready before the internal review. "
                "Finish login, note sharing, AI query flow, and Docker demo checklist by next Friday."
            ),
        },
        {
            "title": "DBMS Viva Revision",
            "content": (
                "Revise normalization up to BCNF, transaction properties, deadlocks, indexing, joins, "
                "and differences between clustered and non-clustered indexes before the Pune University viva."
            ),
        },
        {
            "title": "Computer Networks Quick Notes",
            "content": (
                "Prepare OSI layers, TCP three-way handshake, sliding window, subnetting examples, "
                "and common differences between TCP and UDP for semester exam answers."
            ),
        },
        {
            "title": "Placement Aptitude Plan",
            "content": (
                "Practice quantitative aptitude every morning, solve one logical reasoning set daily, "
                "and revise arrays, strings, and SQL for campus placement preparation."
            ),
        },
        {
            "title": "Pune University Attendance Tracker",
            "content": (
                "Need at least 75 percent attendance overall. Check the practical attendance sheet every Monday "
                "and message the class representative if any lecture is missing."
            ),
        },
        {
            "title": "Python Lab Submission",
            "content": (
                "Complete file handling, pandas cleaning task, matplotlib visualization, and mini Flask assignment "
                "before the Saturday practical submission deadline."
            ),
        },
        {
            "title": "Mini Project Demo Talking Points",
            "content": (
                "Explain the problem statement, show user login, note CRUD, sharing, and AI search, "
                "then finish with deployment using Docker Compose."
            ),
        },
        {
            "title": "Software Engineering Unit 4",
            "content": (
                "Focus on UML diagrams, test case design, agile ceremonies, requirement traceability matrix, "
                "and difference between verification and validation."
            ),
        },
        {
            "title": "College Hackathon Ideas",
            "content": (
                "Possible themes: placement prep assistant, attendance dashboard, hostel expense splitter, "
                "and smart notes app for final year BCS students."
            ),
        },
        {
            "title": "Cloud Computing Assignment",
            "content": (
                "Write short notes on IaaS, PaaS, SaaS, virtualization, autoscaling, containers, and "
                "compare AWS EC2 with Docker-based deployment."
            ),
        },
        {
            "title": "Operating Systems Revision",
            "content": (
                "Revise CPU scheduling algorithms, deadlock conditions, paging, segmentation, and producer-consumer "
                "problem with semaphore examples."
            ),
        },
        {
            "title": "Final Year Resume Checklist",
            "content": (
                "Update headline, add BCS final year under Savitribai Phule Pune University, mention React Native, "
                "Flask, PostgreSQL, Docker, and one solid academic project."
            ),
        },
        {
            "title": "Machine Learning Elective Notes",
            "content": (
                "Study supervised vs unsupervised learning, overfitting, train-test split, confusion matrix, "
                "and practical use of linear regression."
            ),
        },
        {
            "title": "Data Science Seminar Prep",
            "content": (
                "Talk about embeddings, vector search, retrieval augmented generation, and how notes can be "
                "queried using AI without hallucinating beyond the source material."
            ),
        },
        {
            "title": "Class Representative Tasks",
            "content": (
                "Collect assignment submissions, remind everyone about project synopsis approval, and confirm "
                "the external examiner schedule with the department office."
            ),
        },
        {
            "title": "Java Practical Topics",
            "content": (
                "Practice interfaces, exception handling, collections, JDBC basics, and servlet lifecycle "
                "because these are repeatedly asked in the final practical."
            ),
        },
        {
            "title": "Internship Follow-up List",
            "content": (
                "Mail the startup in Hinjawadi, update GitHub README, and prepare concise explanation of the "
                "NoteShare architecture for internship interviews."
            ),
        },
        {
            "title": "Seminar Attendance Notes",
            "content": (
                "The department seminar emphasized communication skills, presentation clarity, and practical demos. "
                "Need to keep project explanation short and confident."
            ),
        },
        {
            "title": "Exam Day Routine",
            "content": (
                "Reach college 30 minutes early, carry hall ticket and ID card, revise definitions first, "
                "and leave the last 10 minutes for answer review."
            ),
        },
        {
            "title": "Backend Deployment Notes",
            "content": (
                "Use Docker Compose for local demonstration. Verify database migrations, Celery worker startup, "
                "and `/api/v1/health` before sharing the demo."
            ),
        },
    ]


def build_soham_notes() -> list[dict[str, str]]:
    return [
        {
            "title": "Final Year Study Timetable",
            "content": (
                "Morning slot for aptitude, afternoon for BCS theory subjects, and evening for project coding. "
                "Reserve Sundays for revision and backlog practice questions."
            ),
        },
        {
            "title": "Advanced Java Revision",
            "content": (
                "Cover JDBC connection flow, servlet request lifecycle, JSP basics, session handling, "
                "and MVC example before the practical exam."
            ),
        },
        {
            "title": "Statistics for Computer Science",
            "content": (
                "Revise mean, median, standard deviation, correlation, probability basics, and hypothesis testing "
                "for the university written paper."
            ),
        },
        {
            "title": "Distributed Systems Revision",
            "content": (
                "Focus on consensus basics, leader election, replication strategies, distributed transactions, "
                "and the CAP theorem before the exam."
            ),
        },
        {
            "title": "Soft Skills Interview Notes",
            "content": (
                "Prepare introduction, final year project explanation, strengths, teamwork example, and a reason "
                "for choosing software development as a career."
            ),
        },
        {
            "title": "College Project Meeting Summary",
            "content": (
                "Frontend should finish lazy loading and share management, backend should verify Celery indexing, "
                "and testing must cover login, notes, AI, and Docker setup."
            ),
        },
        {
            "title": "SPPU Exam Strategy",
            "content": (
                "Write definitions first, use neat bullet points, include diagrams where possible, and "
                "attempt long answers with practical examples."
            ),
        },
        {
            "title": "Hackathon Planning",
            "content": (
                "Set up roles for frontend, backend, and presentation. Keep the final demo small, polished, "
                "and easy to explain to judges."
            ),
        },
        {
            "title": "Frontend Debug Checklist",
            "content": (
                "Check pagination, logout flow, shared notes, AI tab fallback, note detail styling, "
                "and mobile responsiveness before final submission."
            ),
        },
        {
            "title": "Cyber Security Notes",
            "content": (
                "Revise SQL injection, XSS, hashing, salting, HTTPS, authentication vs authorization, "
                "and secure password storage."
            ),
        },
        {
            "title": "Reading List",
            "content": (
                "Finish the papers on vector search, retrieval augmented generation, evaluation of note-grounded "
                "assistants, and practical AI product tradeoffs."
            ),
        },
        {
            "title": "Mobile App UI Review",
            "content": (
                "Need bordered note editor, clear sharing state, better empty states, and smooth infinite scroll "
                "to impress the project guide during review."
            ),
        },
        {
            "title": "Practical File Completion",
            "content": (
                "Complete Python, Java, DBMS, and web technology practical journals before signature day. "
                "Leave printed copies ready in the college bag."
            ),
        },
        {
            "title": "Networking Lab Experiments",
            "content": (
                "Revise IP classes, subnetting, cabling basics, router configuration concepts, and packet flow "
                "so the oral exam answers are confident."
            ),
        },
        {
            "title": "Capstone Demo Script",
            "content": (
                "Open with the student problem, show note creation, demonstrate sharing between Yash and Soham, "
                "then finish with AI answering from stored notes."
            ),
        },
        {
            "title": "Job Fair Preparation",
            "content": (
                "Print three resumes, keep project screenshots ready, prepare answers for Flask, React Native, "
                "Docker, PostgreSQL, and Gemini API questions."
            ),
        },
        {
            "title": "Hostel Study Goals",
            "content": (
                "Finish one unit per night after dinner, avoid distractions after 10 PM, and revise formulas "
                "before sleeping."
            ),
        },
        {
            "title": "Version Control Notes",
            "content": (
                "Use clear branch names, checkpoint commits, avoid rebasing shared history, and write commit messages "
                "that explain the user-facing change."
            ),
        },
        {
            "title": "Cloud Lab Viva",
            "content": (
                "Prepare answers on containers, orchestration basics, scaling, storage volumes, environment variables, "
                "and service monitoring."
            ),
        },
        {
            "title": "Final Practical Day Checklist",
            "content": (
                "Carry journal, lab manual, hall ticket, pen drive backup, and verify the project runs locally "
                "before leaving for college."
            ),
        },
    ]


DEMO_USERS = [
    {
        "email": "yash@noteshare.demo",
        "full_name": "Yash Andure",
        "password": "YashDemo@123",
        "notes": build_yash_notes(),
    },
    {
        "email": "soham@noteshare.demo",
        "full_name": "Soham Kulkarni",
        "password": "SohamDemo@123",
        "notes": build_soham_notes(),
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


def reset_demo_user_content(user: User) -> None:
    note_ids = [note.id for note in Note.query.filter_by(user_id=user.id).all()]

    if note_ids:
        Share.query.filter(Share.note_id.in_(note_ids)).delete(synchronize_session=False)
        NoteEmbedding.query.filter(NoteEmbedding.note_id.in_(note_ids)).delete(
            synchronize_session=False
        )
        Note.query.filter(Note.id.in_(note_ids)).delete(synchronize_session=False)
        db.session.commit()


def create_demo_note(user: User, title: str, content: str) -> None:
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

        reset_demo_user_content(user)

        for note in demo_user["notes"]:
            create_demo_note(
                user=user,
                title=note["title"],
                content=note["content"],
            )

    print("Demo users were reset and seeded successfully.")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        seed_demo_data()
