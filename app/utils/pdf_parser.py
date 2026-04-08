import fitz
def extract_text_from_pdf(file_storage) -> str:
    pdf_bytes = file_storage.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    all_text = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()

        if text.strip():
            all_text.append(f"--- Page {page_num + 1} ---\n{text}")

    doc.close()

    return "\n\n".join(all_text)

def extract_text_from_pdf_path(file_path: str) -> str:
    doc = fitz.open(file_path)

    all_text = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        if text.strip():
            all_text.append(f"--- Page {page_num + 1} ---\n{text}")

    doc.close()

    return "\n\n".join(all_text)

def sanitize_query(query: str) -> str:
    dangerous_patterns = [
        "ignore previous instructions",
        "ignore all instructions",
        "disregard",
        "forget everything",
        "you are now",
        "new instructions",
        "system prompt",
    ]

    cleaned = query
    for pattern in dangerous_patterns:
        cleaned = cleaned.lower().replace(pattern, "[filtered]")

    return cleaned