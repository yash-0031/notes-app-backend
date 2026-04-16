import re

from flask import current_app
from sqlalchemy.orm import aliased

from app import db
from app.models import Note, NoteEmbedding, Share, User
from app.utils.permissions import get_accessible_note_ids
from app.utils.ai_helper import get_embedding, generate_answer


class QueryService:
    SELF_REFERENCES = {"i", "me", "my", "myself"}

    @staticmethod
    def _normalize_question(question: str) -> str:
        normalized = question.strip()
        normalized = re.sub(r"^\s*from\s+[a-zA-Z0-9_.@ -]+\s*:\s*", "", normalized, flags=re.IGNORECASE)
        return normalized

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
            r"did\s+([a-zA-Z0-9_.@ -]+)\s+share(?:\s+with\b|$)",
            r"what\s+(?:did|has)\s+([a-zA-Z0-9_.@ -]+)\s+share(?:\s+with\b|$)",
            r"which\s+notes\s+did\s+([a-zA-Z0-9_.@ -]+)\s+share(?:\s+with\b|$)",
        ]

        lowered = question.lower()
        for pattern in patterns:
            match = re.search(pattern, lowered)
            if match:
                return match.group(1).strip(" .?!,")
        return None

    @staticmethod
    def _extract_shared_with_filter(question: str) -> str | None:
        patterns = [
            r"shared with\s+([a-zA-Z0-9_.@ -]+)",
            r"share with\s+([a-zA-Z0-9_.@ -]+)",
            r"with\s+([a-zA-Z0-9_.@ -]+)\s*$",
        ]

        lowered = question.lower()
        for pattern in patterns:
            match = re.search(pattern, lowered)
            if match:
                return match.group(1).strip(" .?!,:;")
        return None

    @staticmethod
    def _is_share_listing_request(question: str) -> bool:
        lowered = question.lower()
        share_terms = ["share", "shared"]
        list_terms = [
            "which notes",
            "what notes",
            "list",
            "show",
            "tell me",
            "what did",
            "which did",
        ]
        return any(term in lowered for term in share_terms) and any(term in lowered for term in list_terms)

    @staticmethod
    def _build_share_listing_response(question: str, user_id: str) -> dict | None:
        normalized_question = QueryService._normalize_question(question)
        if not QueryService._is_share_listing_request(normalized_question):
            return None

        shared_by = QueryService._extract_shared_by_filter(normalized_question)
        shared_with = QueryService._extract_shared_with_filter(normalized_question)
        lowered = normalized_question.lower()

        if shared_by in QueryService.SELF_REFERENCES:
            shared_by = None
        if shared_with in QueryService.SELF_REFERENCES:
            shared_with = None

        owner_id = user_id if re.search(r"\b(i|my)\b", lowered) and any(term in lowered for term in ["share", "shared"]) else None
        recipient_id = user_id if re.search(r"\b(me)\b", lowered) else None

        if shared_by:
            owner = QueryService._resolve_user_by_name_or_email(shared_by)
            if not owner:
                return {
                    "answer": f"I couldn't find a user matching '{shared_by}'.",
                    "sources": [],
                }
            owner_id = str(owner.id)

        if shared_with:
            recipient = QueryService._resolve_user_by_name_or_email(shared_with)
            if not recipient:
                return {
                    "answer": f"I couldn't find a user matching '{shared_with}'.",
                    "sources": [],
                }
            recipient_id = str(recipient.id)

        recipient_user = aliased(User)
        share_query = (
            db.session.query(
                Share.note_id,
                Share.permission,
                Note.title.label("note_title"),
                User.full_name.label("owner_name"),
                User.email.label("owner_email"),
                recipient_user.full_name.label("recipient_name"),
                recipient_user.email.label("recipient_email"),
            )
            .join(Note, Note.id == Share.note_id)
            .join(User, User.id == Note.user_id)
            .join(recipient_user, recipient_user.id == Share.shared_with_user_id)
        )

        if owner_id:
            share_query = share_query.filter(Note.user_id == owner_id)
        if recipient_id:
            share_query = share_query.filter(Share.shared_with_user_id == recipient_id)

        share_rows = share_query.order_by(Note.updated_at.desc(), Note.title.asc()).all()

        if not share_rows:
            return {
                "answer": "I couldn't find any shared notes matching that request.",
                "sources": [],
            }

        if owner_id and recipient_id:
            if str(owner_id) == str(user_id):
                target_user = db.session.get(User, recipient_id)
                target_name = (
                    target_user.full_name
                    if target_user and target_user.full_name
                    else target_user.email
                    if target_user
                    else "that user"
                )
                intro = f"You shared these notes with {target_name}:"
            elif str(recipient_id) == str(user_id):
                owner = db.session.get(User, owner_id)
                owner_name = (
                    owner.full_name
                    if owner and owner.full_name
                    else owner.email
                    if owner
                    else "that user"
                )
                intro = f"{owner_name} shared these notes with you:"
            else:
                owner = db.session.get(User, owner_id)
                recipient = db.session.get(User, recipient_id)
                owner_name = (
                    owner.full_name
                    if owner and owner.full_name
                    else owner.email
                    if owner
                    else "that user"
                )
                recipient_name = (
                    recipient.full_name
                    if recipient and recipient.full_name
                    else recipient.email
                    if recipient
                    else "that user"
                )
                intro = f"{owner_name} shared these notes with {recipient_name}:"
        elif owner_id:
            owner = db.session.get(User, owner_id)
            owner_name = (
                owner.full_name
                if owner and owner.full_name
                else owner.email
                if owner
                else "that user"
            )
            intro = f"Here are the notes shared by {owner_name}:"
        elif recipient_id:
            recipient = db.session.get(User, recipient_id)
            recipient_name = (
                recipient.full_name
                if recipient and recipient.full_name
                else recipient.email
                if recipient
                else "that user"
            )
            intro = f"Here are the notes shared with {recipient_name}:"
        else:
            intro = "Here are the matching shared notes:"

        sources = []
        lines = [intro]
        for row in share_rows:
            recipient_name = row.recipient_name or row.recipient_email
            permission_value = row.permission.value if hasattr(row.permission, "value") else str(row.permission)
            lines.append(f"- {row.note_title} ({permission_value})")
            sources.append({
                "note_id": str(row.note_id),
                "note_title": row.note_title,
                "chunk_text": f"Shared with {recipient_name} as {permission_value}.",
                "similarity_score": 1.0,
            })

        return {
            "answer": "\n".join(lines),
            "sources": sources,
        }

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
        share_listing_response = QueryService._build_share_listing_response(question, user_id)
        if share_listing_response:
            return share_listing_response

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
