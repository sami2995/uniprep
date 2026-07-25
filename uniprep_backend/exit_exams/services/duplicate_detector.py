"""
Duplicate question detection service.

Uses difflib.SequenceMatcher (stdlib) for fuzzy text similarity.
No external dependencies required.
"""
import re
import difflib

from ..models import Question


def _normalize(text: str) -> str:
    """Lowercase, strip extra whitespace and punctuation for comparison."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def calculate_similarity(text_a: str, text_b: str) -> float:
    """
    Return similarity ratio in [0.0, 1.0] between two question texts.
    Uses SequenceMatcher on normalised strings.
    """
    a = _normalize(text_a)
    b = _normalize(text_b)
    return difflib.SequenceMatcher(None, a, b).ratio()


def find_duplicates(
    text: str,
    course_id: int | None = None,
    threshold: float = 0.85,
    exclude_question_id: int | None = None,
) -> list[dict]:
    """
    Search the question bank for questions similar to *text*.

    Args:
        text: The candidate question text to check.
        course_id: If provided, only compare against questions in that course.
        threshold: Similarity ratio (0–1) above which a question counts as a
                   potential duplicate. Default 0.85 (≈85%).
        exclude_question_id: ID of an existing question to skip (for edits).

    Returns:
        List of dicts sorted by similarity descending:
            [{"question_id": int, "text": str, "similarity": float,
              "status": str, "topic_name": str, "domain_name": str}, ...]
    """
    queryset = Question.objects.select_related(
        "topic", "topic__domain", "topic__domain__course"
    )

    if course_id:
        queryset = queryset.filter(topic__domain__course_id=course_id)

    if exclude_question_id:
        queryset = queryset.exclude(id=exclude_question_id)

    # Only check active statuses (draft, submitted, approved) — not archived
    queryset = queryset.exclude(status=Question.Status.ARCHIVED)

    duplicates = []

    for question in queryset:
        similarity = calculate_similarity(text, question.text)

        if similarity >= threshold:
            duplicates.append(
                {
                    "question_id": question.id,
                    "text": question.text,
                    "similarity": round(similarity * 100, 1),
                    "status": question.status,
                    "topic_name": question.topic.name if question.topic else "",
                    "domain_name": (
                        question.topic.domain.name
                        if question.topic and question.topic.domain
                        else ""
                    ),
                }
            )

    duplicates.sort(key=lambda x: x["similarity"], reverse=True)
    return duplicates
