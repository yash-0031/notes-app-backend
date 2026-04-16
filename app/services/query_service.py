from app import db
from app.models import Note, NoteEmbedding
from app.utils.permissions import get_accessible_note_ids
from app.utils.ai_helper import get_embedding, generate_answer


class QueryService:
    @staticmethod
    def get_index_status(user_id: str) -> dict:

        accessible_note_ids = get_accessible_note_ids(user_id)

        if not accessible_note_ids:
            return {
                "total_notes": 0,
                "indexed_notes": 0,
                "pending_notes": 0,
                "is_ready": False,
            }

        total_notes = (
            db.session.query(Note.id)
            .filter(Note.id.in_(accessible_note_ids))
            .distinct()
            .count()
        )

        indexed_notes = (
            db.session.query(NoteEmbedding.note_id)
            .filter(NoteEmbedding.note_id.in_(accessible_note_ids))
            .distinct()
            .count()
        )

        pending_notes = max(total_notes - indexed_notes, 0)

        return {
            "total_notes": total_notes,
            "indexed_notes": indexed_notes,
            "pending_notes": pending_notes,
            "is_ready": total_notes > 0 and pending_notes == 0,
        }

    @staticmethod
    def query(user_id: str, question: str, top_k: int = 5) -> dict:

        accessible_note_ids = get_accessible_note_ids(user_id)

        if not accessible_note_ids:
            return {
                "answer": "You don't have any notes yet. Create some notes first, and I'll be able to answer questions about them.",
                "sources": [],
            }
        
        question_vector = get_embedding(question)

        similar_chunks = (
            db.session.query(
                NoteEmbedding,
                NoteEmbedding.embedding.cosine_distance(question_vector).label("distance"),
            )
            .filter(NoteEmbedding.note_id.in_(accessible_note_ids))
            .order_by("distance")
            .limit(top_k)
            .all()
        )

        if not similar_chunks:
            return {
                "answer": "I couldn't find any relevant information in your notes for this question.",
                "sources": [],
            }
        
        context_pieces = []
        sources = []

        for chunk, distance in similar_chunks:
            note = Note.query.get(chunk.note_id)
            note_title = note.title if note else "Unknown Note"

            context_pieces.append(
                f"[From note: {note_title}]\n{chunk.chunk_text}"
            )

            sources.append({
                "note_id": str(chunk.note_id),
                "note_title": note_title,
                "chunk_text": chunk.chunk_text[:200] + "..." if len(chunk.chunk_text) > 200 else chunk.chunk_text,
                "similarity_score": round(1 - distance, 4),
            })

        context = "\n\n---\n\n".join(context_pieces)

        answer = generate_answer(question, context)

        return {
            "answer": answer,
            "sources": sources,
        }
