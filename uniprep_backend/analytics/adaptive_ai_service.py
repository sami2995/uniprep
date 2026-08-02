"""
analytics/adaptive_ai_service.py

AI-powered content generation for the Adaptive Learning Engine.
Sources content from the EXAM BANK (Question model), NOT from student-uploaded StudyMaterial.

Two functions:
- generate_topic_summary(topic_obj)           → narrative summary for the Summary step
- generate_topic_flashcards(topic_obj, student, count=10) → gap-weighted flashcards for the Flashcards step

Both call call_openrouter() from rag/services/ai_service.py — no new AI dependency.
Quiz and Mini Mock steps remain AI-FREE (direct exam bank question selection).
"""

import logging
from exit_exams.models import Question
from exit_exams.services.question_selector import rank_questions_for_student
from rag.services.ai_service import call_openrouter

logger = logging.getLogger(__name__)


def _build_question_corpus(questions):
    """
    Given an ordered list of Question objects (with prefetched choices),
    returns a list of dicts: {question_text, correct_answer, explanation}.
    Explanation is included only when it meaningfully differs from the correct answer.
    """
    corpus = []
    for q in questions:
        correct_choice = next(
            (c for c in q.choices.all() if c.is_correct), None
        )
        if not correct_choice:
            continue

        correct_text = correct_choice.text.strip()
        expl = q.explanation.strip()

        # Only include explanation when it adds information beyond the correct answer
        explanation_is_trivial = (
            not expl
            or expl.lower() == correct_text.lower()
            or len(expl) <= len(correct_text) + 2
        )
        explanation = "" if explanation_is_trivial else expl

        corpus.append({
            "question_text": q.text.strip(),
            "correct_answer": correct_text,
            "explanation": explanation,
        })
    return corpus


def _get_approved_questions(topic_obj):
    """
    Returns a queryset of approved, active questions for a topic with choices prefetched.
    """
    return Question.objects.filter(
        topic=topic_obj,
        status="approved",
        is_active=True,
    ).prefetch_related("choices")


def generate_topic_summary(topic_obj):
    """
    Generates a structured topic summary from the exam bank questions for that topic.
    Feeds (question_text, correct_answer, [explanation]) tuples to OpenRouter and asks
    for a narrative teaching summary — NOT a list of Q&A pairs.

    Returns:
        dict with keys: summary_text, key_points, important_terms
        OR raises Exception on AI failure.
    """
    questions = _get_approved_questions(topic_obj)

    if not questions.exists():
        return {
            "summary_text": f"No approved exam questions found for {topic_obj.name}.",
            "key_points": [],
            "important_terms": [],
        }

    corpus = _build_question_corpus(list(questions))

    if not corpus:
        return {
            "summary_text": f"Could not build content corpus for {topic_obj.name}.",
            "key_points": [],
            "important_terms": [],
        }

    # Format question bank as a numbered list for the prompt
    qa_lines = []
    for i, item in enumerate(corpus, 1):
        line = f"{i}. Q: {item['question_text']}\n   A: {item['correct_answer']}"
        if item["explanation"]:
            line += f"\n   Explanation: {item['explanation']}"
        qa_lines.append(line)

    qa_text = "\n\n".join(qa_lines)
    topic_name = topic_obj.name
    domain_name = topic_obj.domain.name

    prompt = f"""You are UniPrep AI, an academic study assistant helping a student prepare for their university exit exam.

The student needs to study the topic: "{topic_name}" (part of the domain: "{domain_name}").

Below are {len(corpus)} approved exam questions for this topic, with their correct answers:

{qa_text}

Based ONLY on these questions and answers, write a structured study summary to help the student understand this topic deeply.

Your summary MUST include three sections, formatted EXACTLY as shown:

SUMMARY:
Write 3-5 clear paragraphs explaining the key concepts, rules, and principles that this topic tests. Write this as teaching prose, not as a list of Q&A pairs. Help the student understand WHY each answer is correct, not just WHAT the answer is.

KEY_POINTS:
- List 5-8 bullet points covering the most important testable facts, definitions, and rules.

IMPORTANT_TERMS:
- Term: brief definition
- Term: brief definition
(List 5-8 important terms and their definitions.)

Do not add any text outside these three sections. Do not repeat questions verbatim."""

    try:
        raw = call_openrouter(prompt=prompt, temperature=0.3, max_tokens=2000)
    except Exception as exc:
        logger.error("generate_topic_summary AI call failed: %s", exc)
        raise

    # Parse the structured response into fields
    summary_text = ""
    key_points = []
    important_terms = []

    current_section = None
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith("SUMMARY:"):
            current_section = "summary"
            remainder = stripped[len("SUMMARY:"):].strip()
            if remainder:
                summary_text += remainder + "\n"
        elif stripped.startswith("KEY_POINTS:"):
            current_section = "key_points"
        elif stripped.startswith("IMPORTANT_TERMS:"):
            current_section = "terms"
        elif current_section == "summary":
            summary_text += stripped + "\n"
        elif current_section == "key_points" and stripped.startswith("-"):
            key_points.append(stripped[1:].strip())
        elif current_section == "terms" and stripped.startswith("-"):
            important_terms.append(stripped[1:].strip())

    return {
        "summary_text": summary_text.strip(),
        "key_points": key_points,
        "important_terms": important_terms,
    }


def generate_topic_flashcards(topic_obj, student=None, count=10):
    """
    Generates gap-weighted flashcards from the exam bank for a topic.

    If student is provided:
      - Prioritizes unseen questions first (student has no exposure)
      - Then questions answered incorrectly (student's confirmed gaps)
      - Then remaining questions (content already partially known)

    This ensures flashcards target the student's actual knowledge gaps,
    not content they already answer correctly.

    Returns:
        list of dicts: [{front, back, difficulty}]
        OR raises Exception on AI failure.
    """
    questions = _get_approved_questions(topic_obj)

    if not questions.exists():
        return []

    # Apply consistent gap-weighted ordering (student-aware, or full topic if no student)
    ranked = rank_questions_for_student(student, questions)

    # Take the top `count` questions as the flashcard corpus
    selected = ranked[:count]
    corpus = _build_question_corpus(list(selected))

    if not corpus:
        return []

    qa_lines = []
    for i, item in enumerate(corpus, 1):
        line = f"{i}. Q: {item['question_text']}\n   A: {item['correct_answer']}"
        if item["explanation"]:
            line += f"\n   Explanation: {item['explanation']}"
        qa_lines.append(line)

    qa_text = "\n\n".join(qa_lines)
    topic_name = topic_obj.name

    prompt = f"""You are UniPrep AI, an academic study assistant.

The student needs to review the topic: "{topic_name}".

Below are exam questions the student has likely gotten wrong or never seen before:

{qa_text}

Generate {count} study flashcards to help the student master this topic.

Rules:
- Each flashcard MUST target a concept, rule, or definition from the questions above.
- The "front" should be a clear question or concept prompt (NOT just a copy of the exam question).
- The "back" should be a clear, concise answer or explanation (NOT just the correct choice letter).
- Prefer conceptual understanding over rote memorization.
- Return ONLY valid JSON — no markdown, no extra text.

Return ONLY this JSON format:
[
  {{
    "front": "concept question or prompt",
    "back": "clear explanation or answer",
    "difficulty": "easy|medium|hard"
  }}
]"""

    try:
        raw = call_openrouter(prompt=prompt, temperature=0.3, max_tokens=2000)
    except Exception as exc:
        logger.error("generate_topic_flashcards AI call failed: %s", exc)
        raise

    # Parse JSON response
    from rag.services.ai_service import extract_json_array
    try:
        cards = extract_json_array(raw)
    except (ValueError, Exception) as exc:
        logger.error("Failed to parse flashcards JSON: %s | Raw: %s", exc, raw[:500])
        raise ValueError(f"AI returned invalid flashcard JSON: {exc}") from exc

    # Normalise and validate each card
    result = []
    for card in cards:
        if isinstance(card, dict) and card.get("front") and card.get("back"):
            result.append({
                "front": str(card["front"]).strip(),
                "back": str(card["back"]).strip(),
                "difficulty": str(card.get("difficulty", "medium")).strip(),
            })

    return result
