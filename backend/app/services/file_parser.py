from typing import List
from pypdf import PdfReader


def extract_text(filepath: str, file_type: str) -> str:
    """Extract raw text from a .txt or .pdf file."""
    if file_type == "pdf":
        reader = PdfReader(filepath)
        text_parts = []
        for page in reader.pages:
            text_parts.append(page.extract_text() or "")
        return "\n".join(text_parts)
    else:  # txt
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 80) -> List[str]:
    """
    Split text into overlapping word-based chunks so semantic search
    retrieves focused, relevant passages instead of whole documents.
    """
    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk.strip())
        if end >= len(words):
            break
        start = end - overlap
    return chunks
