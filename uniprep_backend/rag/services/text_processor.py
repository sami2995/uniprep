import uuid
from pypdf import PdfReader
from docx import Document


def extract_text_from_pdf(file_path):
    reader = PdfReader(file_path)
    full_text = ""

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        full_text += f"\n\n--- Page {page_number} ---\n{text}"

    return full_text.strip()


def extract_text_from_docx(file_path):
    document = Document(file_path)

    paragraphs = [
        paragraph.text
        for paragraph in document.paragraphs
        if paragraph.text.strip()
    ]

    return "\n".join(paragraphs).strip()


def chunk_text(text, chunk_size=800, overlap=150):
    chunks = []

    if not text:
        return chunks

    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start = end - overlap

    return chunks




def generate_local_chunk_id():
    return str(uuid.uuid4())

def create_basic_summary(text, max_sentences=8):
    """
    Simple temporary summary.
    Later we will replace this with Gemini/OpenAI.
    """
    if not text:
        return ""

    sentences = text.replace("\n", " ").split(".")

    clean_sentences = [
        sentence.strip()
        for sentence in sentences
        if len(sentence.strip()) > 40
    ]

    selected = clean_sentences[:max_sentences]

    if not selected:
        return text[:1000]

    return ". ".join(selected) + "."