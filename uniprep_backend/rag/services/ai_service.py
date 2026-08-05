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


# ─── LLM-grounded material summary ───
#
# Map-reduce summarization thresholds. Documents with up to
# MAX_SUMMARY_CONTEXT_CHUNKS chunks go through a single LLM pass; larger
# documents are split into SUMARY_GROUP_SIZE-sized batches (map step) and
# the per-group summaries are combined in a final pass (reduce step).
MAX_SUMMARY_CONTEXT_CHUNKS = 20
SUMMARY_GROUP_SIZE = 15

MIN_SUMMARY_TEXT_LEN = 120

# Short refusal-like outputs we treat as "model did not summarize".
_REFUSAL_FRAGMENTS = (
    "i could not",
    "i cannot",
    "i can't",
    "unable to",
    "as an ai",
    "i'm sorry",
)


def _is_refusal(text):
    if not text:
        return True
    low = text.strip().lower()
    if len(low) < MIN_SUMMARY_TEXT_LEN:
        return True
    return any(frag in low for frag in _REFUSAL_FRAGMENTS)


# Some LLMs emit typographic punctuation that browsers/OS TTS engines may
# Mishandle silently (U+202F narrow no-break space, U+2011 figure dash,
# U+00A0 no-break space, U+2013/2014 en/em dashes). Normalize to plain
# ASCII equivalents defensively so Web Speech API reads the text cleanly.
_TTS_CHAR_NORMALIZATIONS = {
    "\u202f": " ",   # narrow no-break space
    "\u00a0": " ",   # no-break space
    "\u2009": " ",   # thin space
    "\u2011": "-",   # figure dash
    "\u2013": "-",   # en dash
    "\u2014": "-",   # em dash
    "\u2018": "'",   # left single quote
    "\u2019": "'",   # right single quote
    "\u201c": '"',   # left double quote
    "\u201d": '"',   # right double quote
}


def _normalize_for_tts(text):
    if not text:
        return text
    for src, dst in _TTS_CHAR_NORMALIZATIONS.items():
        text = text.replace(src, dst)
    return text


def _build_summary_prompt(context_text, mode="full"):
    """
    mode:
      - "full"   : produce final summary_text + key_points + important_terms
      - "group"  : produce only a short paragraph summary of one batch
    """
    if mode == "group":
        return f"""You are UniPrep AI, an academic study assistant.

Summarize the study material section below into clear, concise prose.

Rules:
- Return plain prose only. Do NOT use markdown, headings, or lists.
- Use blank lines (a single "\n\n") to separate paragraphs.
- Keep the summary focused on the most exam-relevant points from this section.
- Do not include any preface like "Here is a summary". Just return the summary.

Source material (one section):
{context_text}
"""

    return f"""You are UniPrep AI, an academic study assistant.

Produce a structured study summary of the provided material.

Return ONLY valid JSON in this exact format:
{{
  "summary_text": "Multi-paragraph summary prose here.\\n\\nSecond paragraph here.",
  "key_points": ["Point 1", "Point 2", "Point 3", "Point 4", "Point 5"],
  "important_terms": ["Term 1", "Term 2", "Term 3"]
}}

Rules:
- Return only JSON. Do not include markdown or any text outside JSON.
- summary_text must be plain prose, no markdown, no headings, no bullet lists.
- Separate paragraphs inside summary_text with a single "\\n\\n".
- key_points: 3-7 concise bullet phrases (strings), each a full short sentence.
- important_terms: 2-6 key topic-specific terms.
- Use only the provided material; do not invent facts.
- Keep summary_text focused and exam-oriented.

Material:
{context_text}
"""


def _extract_summary_json(text):
    """
    Parses the structured summary JSON returned by the model.
    Tolerates markdown fences if present and returns a normalized dict.
    """
    cleaned = clean_json_text(text)

    try:
        obj = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise ValueError("No JSON object found in summary response.")
        obj = json.loads(match.group(0))

    if not isinstance(obj, dict):
        raise ValueError("Summary response is not a JSON object.")

    summary_text = _normalize_for_tts(str(obj.get("summary_text", "")).strip())
    key_points = obj.get("key_points", []) or []
    important_terms = obj.get("important_terms", []) or []

    if isinstance(key_points, list):
        key_points = [str(p).strip() for p in key_points if str(p).strip()]
    else:
        key_points = []

    if isinstance(important_terms, list):
        important_terms = [str(t).strip() for t in important_terms if str(t).strip()]
    else:
        important_terms = []

    return {
        "summary_text": summary_text,
        "key_points": key_points,
        "important_terms": important_terms,
    }


def generate_summary_ai(context_chunks, mode="full"):
    """
    LLM-grounded summary over the provided context chunks.

    mode="full":  returns dict with summary_text, key_points, important_terms.
    mode="group": returns dict with summary_text only (short paragraph).

    Raises ValueError on a refusal / empty / unparseable response.
    """
    context_text = "\n\n".join(
        [
            f"Source {index + 1}:\n{chunk}"
            for index, chunk in enumerate(context_chunks)
            if chunk and str(chunk).strip()
        ]
    )

    if not context_text.strip():
        raise ValueError("Context text is empty.")

    prompt = _build_summary_prompt(context_text, mode=mode)

    raw = call_openrouter(
        prompt=prompt,
        temperature=0.3,
        max_tokens=800 if mode == "group" else 1600,
    )

    if mode == "group":
        summary_text = _normalize_for_tts(str(raw).strip())
        if _is_refusal(summary_text):
            raise ValueError("Model refused or produced an empty group summary.")
        return {"summary_text": summary_text}

    parsed = _extract_summary_json(raw)

    if _is_refusal(parsed.get("summary_text", "")):
        raise ValueError("Model refused or produced an empty summary.")

    return parsed


def generate_summary_map_reduce(context_chunks):
    """
    Map-reduce summarization for documents larger than the single-pass
    budget.

    Map:  summarize each SUMMARY_GROUP_SIZE-batch of chunks into a short
          paragraph.
    Reduce: pass all batch summaries to a final generate_summary_ai() call
            to produce the final summary_text + key_points + important_terms.
    """
    if not context_chunks:
        raise ValueError("No context chunks provided.")

    group_summaries = []
    for start in range(0, len(context_chunks), SUMMARY_GROUP_SIZE):
        batch = context_chunks[start:start + SUMMARY_GROUP_SIZE]
        result = generate_summary_ai(batch, mode="group")
        para = result.get("summary_text", "").strip()
        if para:
            group_summaries.append(para)

    if not group_summaries:
        raise ValueError("All group summaries were empty.")

    group_context = [
        f"[Section {i + 1}]\n{para}"
        for i, para in enumerate(group_summaries)
    ]

    return generate_summary_ai(group_context, mode="full")


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


class InsufficientQuizMaterialError(Exception):
    """
    Raised when the model cannot produce the exact number of distinct,
    valid quiz questions requested, even after retries.
    """

    def __init__(self, requested, supported):
        self.requested = requested
        self.supported = supported
        super().__init__(
            f"This material only supports approximately {supported} "
            f"distinct quiz question(s), but {requested} were requested. "
            f"Please request {supported} or fewer questions."
        )


# How many extra times we re-prompt when the model under-delivers.
MAX_QUIZ_COUNT_RETRIES = 2


def _quiz_max_tokens(count):
    """
    Scales the completion budget with the requested question count.
    One MCQ with 4 choices + explanation is roughly 150-200 tokens.
    """
    return max(1600, min(400 + count * 200, 6500))


def _normalize_quiz_item(item):
    """
    Validates one raw quiz item from the model.
    Returns a cleaned dict, or None if the item is unusable.
    """
    if not isinstance(item, dict):
        return None

    question_text = str(item.get("question_text", "")).strip()
    choices = item.get("choices", [])
    correct_answer = str(item.get("correct_answer", "")).strip()
    explanation = str(item.get("explanation", "")).strip()

    if not question_text or not correct_answer:
        return None

    if not isinstance(choices, list) or len(choices) != 4:
        return None

    choices = [str(choice).strip() for choice in choices]

    if any(not choice for choice in choices):
        return None

    if correct_answer not in choices:
        return None

    return {
        "question_text": question_text,
        "choices": choices,
        "correct_answer": correct_answer,
        "explanation": explanation,
    }


def _collect_valid_quiz_items(raw_items, existing_questions):
    """
    Normalizes raw model output, dropping invalid items and
    duplicates of questions we have already accepted.
    """
    valid = []

    if not isinstance(raw_items, list):
        return valid

    for item in raw_items:
        normalized = _normalize_quiz_item(item)

        if not normalized:
            continue

        fingerprint = normalized["question_text"].strip().lower()

        if fingerprint in existing_questions:
            continue

        existing_questions.add(fingerprint)
        valid.append(normalized)

    return valid


def _build_quiz_prompt(context_text, count, existing_question_texts=None):
    avoid_block = ""

    if existing_question_texts:
        listed = "\n".join(
            f"- {text}" for text in existing_question_texts
        )
        avoid_block = f"""
Do NOT repeat or paraphrase any of these already-generated questions:
{listed}
"""

    return f"""
You are UniPrep AI.

Generate EXACTLY {count} multiple-choice quiz questions from the provided context.

The JSON array you return MUST contain EXACTLY {count} question objects \
- no more, no fewer. Count them before responding.

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
- Every question must be distinct.
{avoid_block}
Context:
{context_text}
"""


def generate_quiz_ai(context_chunks, count=5):
    """
    Generates exactly `count` valid, distinct quiz questions.

    Strategy: prompt for the exact count, validate the response, and if
    the model under-delivers, re-prompt (up to MAX_QUIZ_COUNT_RETRIES)
    for only the shortfall. Over-delivery is truncated for free.

    Raises InsufficientQuizMaterialError if the exact count cannot be
    produced after retries.
    """
    context_text = "\n\n".join(
        [
            f"Source {index + 1}:\n{chunk}"
            for index, chunk in enumerate(context_chunks)
        ]
    )

    collected = []
    seen_questions = set()

    for attempt in range(1 + MAX_QUIZ_COUNT_RETRIES):
        shortfall = count - len(collected)

        if shortfall <= 0:
            break

        existing_texts = [item["question_text"] for item in collected]

        prompt = _build_quiz_prompt(
            context_text=context_text,
            count=shortfall if attempt > 0 else count,
            existing_question_texts=existing_texts or None,
        )

        text = call_openrouter(
            prompt=prompt,
            temperature=0.2,
            max_tokens=_quiz_max_tokens(shortfall if attempt > 0 else count),
        )

        raw_items = extract_json_array(text)

        collected.extend(
            _collect_valid_quiz_items(raw_items, seen_questions)
        )

    if len(collected) < count:
        raise InsufficientQuizMaterialError(
            requested=count,
            supported=len(collected),
        )

    return collected[:count]