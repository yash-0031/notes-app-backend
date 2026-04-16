import re

from flask import current_app

from app import db
from app.models import Note, NoteEmbedding, Share, User
from app.utils.permissions import get_accessible_note_ids
from app.utils.ai_helper import get_embedding, generate_answer


class QueryService:
    @staticmethod
    def _get_query_setting(name: str, default: int) -> int:
        value = current_app.config.get(name, default)
        try:
            return max(int(value), 1)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _get_search_window_limit() -> int:
        return QueryService._get_query_setting("AI_QUERY_MAX_NOTES", 50)

    @staticmethod
    def _get_summary_chunk_limit() -> int:
        return QueryService._get_query_setting("AI_QUERY_SUMMARY_CHUNK_LIMIT", 20)

    @staticmethod
    def _get_context_budget() -> int:
        return QueryService._get_query_setting("AI_QUERY_MAX_CONTEXT_CHARS", 12000)

    @staticmethod
    def _get_searchable_note_ids(user_id: str) -> tuple[list, int, int]:
        accessible_note_ids = list(dict.fromkeys(get_accessible_note_ids(user_id)))
        if not accessible_note_ids:
            return [], 0, QueryService._get_search_window_limit()

        window_limit = QueryService._get_search_window_limit()
        searchable_note_ids = [
            row[0]
            for row in db.session.query(Note.id)
            .filter(Note.id.in_(accessible_note_ids))
            .order_by(Note.updated_at.desc(), Note.created_at.desc())
            .limit(window_limit)
            .all()
        ]
        return searchable_note_ids, len(accessible_note_ids), window_limit

    @staticmethod
    def _extract_shared_by_filter(question: str) -> str | None:
        patterns = [
            r"shared by\s+([a-zA-Z0-9_.@ -]+)",
            r"from\s+([a-zA-Z0-9_.@ -]+)\s+that (?:was|were)\s+shared",
        ]

        lowered = question.lower()
        for pattern in patterns:
            match = re.search(pattern, lowered)
            if match:
                return match.group(1).strip(" .?!,")
        return None

    @staticmethod
    def _resolve_user_by_name_or_email(name_or_email: str) -> User | None:
        search = name_or_email.strip().lower()
        if not search:
            return None

        direct = User.query.filter(db.func.lower(User.email) == search).first()
        if direct:
            return direct

        by_full_name = (
            User.query.filter(User.full_name.isnot(None))
            .filter(db.func.lower(User.full_name) == search)
            .first()
        )
        if by_full_name:
            return by_full_name

        tokens = [token for token in re.split(r"\s+", search) if token]
        query = User.query
        for token in tokens:
            query = query.filter(db.func.lower(User.full_name).like(f"%{token}%"))
        return query.first()

    @staticmethod
    def _apply_note_filters(user_id: str, question: str, accessible_note_ids: list) -> tuple[list, str]:
        filtered_ids = accessible_note_ids
        cleaned_question = question.strip()

        shared_by = QueryService._extract_shared_by_filter(question)
        if shared_by:
            owner = QueryService._resolve_user_by_name_or_email(shared_by)
            cleaned_question = re.sub(
                r"shared by\s+[a-zA-Z0-9_.@ -]+",
                "",
                cleaned_question,
                flags=re.IGNORECASE,
            ).strip(" ,.")

            if not owner:
                return [], cleaned_question or question

            filtered_ids = [
                row[0]
                for row in db.session.query(Note.id)
                .join(Share, Share.note_id == Note.id)
                .filter(
                    Note.id.in_(accessible_note_ids),
                    Note.user_id == owner.id,
                    Share.shared_with_user_id == user_id,
                )
                .all()
            ]

        return filtered_ids, cleaned_question or question

    @staticmethod
    def _is_broad_summary_request(question: str) -> bool:
        lowered = question.lower()
        keywords = [
            "summarize everything",
            "summarise everything",
            "summary of everything",
            "all shared notes",
            "everything shared",
        ]
        return any(keyword in lowered for keyword in keywords)

    @staticmethod
    def _build_summary_fallback(sources: list[dict]) -> str:
        if not sources:
            return "I couldn't find this information in your notes."

        lines = ["Here is a summary from the matching shared notes:"]
        for source in sources:
            snippet = source["chunk_text"].replace("\n", " ").strip()
            lines.append(f"- {source['note_title']}: {snippet}")
        return "\n".join(lines)

    @staticmethod
    def get_index_status(user_id: str) -> dict:
        accessible_note_ids, accessible_total, search_window_limit = QueryService._get_searchable_note_ids(user_id)

        if not accessible_note_ids:
            return {
                "total_notes": 0,
                "indexed_notes": 0,
                "pending_notes": 0,
                "is_ready": False,
                "search_window_limit": search_window_limit,
                "accessible_total_notes": accessible_total,
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
            "search_window_limit": search_window_limit,
            "accessible_total_notes": accessible_total,
        }

    @staticmethod
    def query(user_id: str, question: str, top_k: int = 5) -> dict:
        accessible_note_ids, _, _ = QueryService._get_searchable_note_ids(user_id)

        if not accessible_note_ids:
            return {
                "answer": "You don't have any notes yet. Create some notes first, and I'll be able to answer questions about them.",
                "sources": [],
            }

        filtered_note_ids, filtered_question = QueryService._apply_note_filters(
            user_id=user_id,
            question=question,
            accessible_note_ids=accessible_note_ids,
        )

        if not filtered_note_ids:
            return {
                "answer": "I couldn't find any relevant information in your notes for this question.",
                "sources": [],
            }

        if QueryService._is_broad_summary_request(question):
            similar_chunks = (
                db.session.query(
                    NoteEmbedding,
                    db.literal(0.0).label("distance"),
                    Note.title.label("note_title"),
                )
                .join(Note, Note.id == NoteEmbedding.note_id)
                .filter(NoteEmbedding.note_id.in_(filtered_note_ids))
                .order_by(Note.updated_at.desc())
                .limit(max(top_k, QueryService._get_summary_chunk_limit()))
                .all()
            )
        else:
            question_vector = get_embedding(filtered_question)

            similar_chunks = (
                db.session.query(
                    NoteEmbedding,
                    NoteEmbedding.embedding.cosine_distance(question_vector).label("distance"),
                    Note.title.label("note_title"),
                )
                .join(Note, Note.id == NoteEmbedding.note_id)
                .filter(NoteEmbedding.note_id.in_(filtered_note_ids))
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
        context_length = 0
        context_budget = QueryService._get_context_budget()

        for chunk, distance, note_title in similar_chunks:
            resolved_title = note_title or "Unknown Note"
            prefix = f"[From note: {resolved_title}]\n"
            remaining_budget = context_budget - context_length - len(prefix)
            if remaining_budget <= 0:
                break

            chunk_text = chunk.chunk_text
            if len(chunk_text) > remaining_budget:
                if context_pieces:
                    break
                chunk_text = chunk_text[:remaining_budget].rstrip()

            snippet = f"{prefix}{chunk_text}"

            context_pieces.append(snippet)
            context_length += len(snippet)

            sources.append({
                "note_id": str(chunk.note_id),
                "note_title": resolved_title,
                "chunk_text": chunk.chunk_text[:200] + "..." if len(chunk.chunk_text) > 200 else chunk.chunk_text,
                "similarity_score": round(1 - distance, 4),
            })

        if not context_pieces:
            return {
                "answer": "Your notes matched, but the relevant context was too large to process. Please narrow the question or update the AI search limits.",
                "sources": [],
            }

        context = "\n\n---\n\n".join(context_pieces)

        answer = generate_answer(question, context)

        if (
            answer == "I couldn't find this information in your notes."
            and sources
            and QueryService._is_broad_summary_request(question)
        ):
            answer = QueryService._build_summary_fallback(sources)

        return {
            "answer": answer,
            "sources": sources,
        }
