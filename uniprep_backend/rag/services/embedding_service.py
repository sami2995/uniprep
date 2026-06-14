from django.conf import settings
from google import genai


EMBEDDING_MODEL = "gemini-embedding-001"


def get_gemini_client():
    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is missing in .env")

    return genai.Client(api_key=settings.GEMINI_API_KEY)


def generate_embedding(text):
    client = get_gemini_client()

    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text
    )

    return response.embeddings[0].values