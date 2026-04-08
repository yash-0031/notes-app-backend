import re


def chunk_text(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list[str]:
    if not text or not text.strip():
        return []
    
    sentences = _split_into_sentences(text)

    chunks = []
    current_chunk = []
    current_word_count = 0

    for sentence in sentences:
        sentence_words = len(sentence.split())  

        if current_word_count + sentence_words > chunk_size and current_chunk:
            chunk_text_str = " ".join(current_chunk)
            chunks.append(chunk_text_str.strip())

            overlap_words = 0
            overlap_sentences = []
            for s in reversed(current_chunk):
                overlap_words += len(s.split())
                if overlap_words > chunk_overlap:
                    break
                overlap_sentences.insert(0, s)

            current_chunk = overlap_sentences
            current_word_count = sum(len(s.split()) for s in current_chunk)

        current_chunk.append(sentence)
        current_word_count += sentence_words
    if current_chunk:
        chunk_text_str = " ".join(current_chunk)
        if chunk_text_str.strip():
            chunks.append(chunk_text_str.strip())

    return chunks


def _split_into_sentences(text: str) -> list[str]:
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]

def prepare_chunks_for_embedding(
    note_id: str,
    note_title: str,
    content: str,
) -> list[dict]:
    
    if not content:
        return []

    chunks = chunk_text(content)
    
    prepared = []
    for i, chunk in enumerate(chunks):
        text_with_title = f"{note_title}: {chunk}"

        prepared.append({
            "chunk_text": text_with_title,
            "metadata": {
                "note_id": str(note_id),
                "note_title": note_title,
                "chunk_index": i,
                "total_chunks": len(chunks),
            },
        })

    return prepared