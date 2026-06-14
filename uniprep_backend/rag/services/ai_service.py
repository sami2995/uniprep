import json
import re
import requests

from django.conf import settings


OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"


def get_openrouter_headers():
    if not settings.OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY is missing in .env")

    return {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": settings.OPENROUTER_SITE_URL,
        "X-Title": settings.OPENROUTER_APP_NAME,
    }


def call_openrouter(prompt, temperature=0.2, max_tokens=1200):
    """
    Generic OpenRouter chat completion call.
    Used for RAG answer, flashcards, and quiz generation.
    """

    payload = {
        "model": settings.OPENROUTER_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are UniPrep AI, an academic study assistant. "
                    "Give clear, accurate, student-friendly answers."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    response = requests.post(
        OPENROUTER_CHAT_URL,
        headers=get_openrouter_headers(),
        json=payload,
        timeout=60,
    )

    if response.status_code >= 400:
        raise Exception(
            f"OpenRouter error {response.status_code}: {response.text}"
        )

    data = response.json()

    return data["choices"][0]["message"]["content"]


def clean_json_text(text):
    """
    Removes markdown code fences if model returns:
    ```json
    [...]
    ```
    """

    text = text.strip()

    text = re.sub(r"^```json", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"^```", "", text).strip()
    text = re.sub(r"```$", "", text).strip()

    return text


def extract_json_array(text):
    """
    Tries to safely extract a JSON array from model output.
    """

    text = clean_json_text(text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\[.*\]", text, re.DOTALL)

    if not match:
        raise ValueError("No JSON array found in AI response.")

    return json.loads(match.group(0))


def generate_rag_answer(question, context_chunks):
    context_text = "\n\n".join(
        [
            f"Source {index + 1}:\n{chunk}"
            for index, chunk in enumerate(context_chunks)
        ]
    )

    prompt = f"""
You are UniPrep AI, an academic study assistant.

Answer the student's question using ONLY the provided context.

If the answer is not found in the context, say:
"I could not find this in your uploaded material."

Keep the answer clear, student-friendly, and exam-focused.

Context:
{context_text}

Student question:
{question}
"""

    return call_openrouter(
        prompt=prompt,
        temperature=0.2,
        max_tokens=1000,
    )


def generate_flashcards_ai(context_chunks, count=5):
    context_text = "\n\n".join(
        [
            f"Source {index + 1}:\n{chunk}"
            for index, chunk in enumerate(context_chunks)
        ]
    )

    prompt = f"""
You are UniPrep AI.

Generate {count} useful study flashcards from the context.

Return ONLY valid JSON in this exact format:

[
  {{
    "front": "Question here",
    "back": "Answer here"
  }}
]

Rules:
- Return only JSON.
- Do not include markdown.
- Do not include explanations outside JSON.
- Use only the provided context.
- Make the flashcards useful for exam preparation.

Context:
{context_text}
"""

    text = call_openrouter(
        prompt=prompt,
        temperature=0.2,
        max_tokens=1200,
    )

    return extract_json_array(text)


def generate_quiz_ai(context_chunks, count=5):
    context_text = "\n\n".join(
        [
            f"Source {index + 1}:\n{chunk}"
            for index, chunk in enumerate(context_chunks)
        ]
    )

    prompt = f"""
You are UniPrep AI.

Generate {count} multiple-choice quiz questions from the provided context.

Return ONLY valid JSON in this exact format:

[
  {{
    "question_text": "Question here",
    "choices": ["Option A", "Option B", "Option C", "Option D"],
    "correct_answer": "Option A",
    "explanation": "Short explanation here"
  }}
]

Rules:
- Return only JSON.
- Do not include markdown.
- Use only the provided context.
- Make questions exam-focused.
- Each question must have exactly 4 choices.
- correct_answer must exactly match one of the choices.

Context:
{context_text}
"""

    text = call_openrouter(
        prompt=prompt,
        temperature=0.2,
        max_tokens=1600,
    )

    return extract_json_array(text)