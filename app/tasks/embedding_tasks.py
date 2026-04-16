from app.tasks import celery_app
from app import db, create_app
from app.models import Note, NoteEmbedding
from app.utils.ai_helper import get_embeddings_batch
from app.utils.vector_ops import prepare_chunks_for_embedding


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="generate_embeddings",
)
def generate_embeddings(self, note_id: str):
    app = create_app()

    with app.app_context():
        try:
            note = Note.query.get(note_id)

            if not note:
                return {"status": "skipped", "reason": "Note not found"}

            if not note.content:
                return {"status": "skipped", "reason": "Note has no content"}

            if note.is_archived:
                return {"status": "skipped", "reason": "Note is archived"}

            NoteEmbedding.query.filter_by(note_id=note_id).delete()
            db.session.commit()

            chunks = prepare_chunks_for_embedding(
                note_id=note.id,
                note_title=note.title,
                content=note.content,
            )

            if not chunks:
                return {"status": "skipped", "reason": "No content to embed"}
            
            texts = [c["chunk_text"] for c in chunks]
            embeddings = get_embeddings_batch(texts)

            if len(embeddings) != len(chunks):
                raise ValueError(
                    f"Embedding count mismatch for note {note_id}: "
                    f"expected {len(chunks)}, received {len(embeddings)}"
                )

            for chunk_data, embedding_vector in zip(chunks, embeddings):
                record = NoteEmbedding(
                    note_id=note_id,
                    chunk_text=chunk_data["chunk_text"],
                    embedding=embedding_vector,
                    metadata_=chunk_data["metadata"],
                )
                db.session.add(record)

            db.session.commit()

            return {
                "status": "success",
                "note_id": note_id,
                "chunks_created": len(chunks),
            }

        except Exception as exc:
            db.session.rollback()
            raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="cleanup_archived_embeddings",
)
def cleanup_archived_embeddings(self):
    app = create_app()

    with app.app_context():
        try:
            archived_notes_with_embeddings = (
                db.session.query(Note.id)
                .filter(Note.is_archived == True)
                .join(NoteEmbedding, NoteEmbedding.note_id == Note.id)
                .distinct()
                .all()
            )

            count = 0
            for (note_id,) in archived_notes_with_embeddings:
                NoteEmbedding.query.filter_by(note_id=note_id).delete()
                count += 1

            db.session.commit()

            return {
                "status": "success",
                "notes_cleaned": count,
            }

        except Exception as exc:
            db.session.rollback()
            raise self.retry(exc=exc)
