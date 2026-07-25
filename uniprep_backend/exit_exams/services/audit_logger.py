"""
Audit logging service.

Call log_action() from any view to record a traceable history of changes
to questions, blueprints, and teacher assignments.
"""
from django.contrib.auth import get_user_model

from ..models import AuditLog


def log_action(
    user,
    action: str,
    entity_type: str,
    entity_id: int,
    previous_value: dict | None = None,
    new_value: dict | None = None,
    description: str = "",
) -> AuditLog:
    """
    Create an AuditLog entry.

    Args:
        user: The CustomUser performing the action (can be None for system).
        action: One of AuditLog.Action choices:
                created | updated | submitted | approved | rejected |
                blueprint_changed | assignment_changed
        entity_type: Human-readable entity name, e.g. "question", "blueprint",
                     "assignment".
        entity_id: Primary key of the entity being acted on.
        previous_value: Dict snapshot of values BEFORE the change.
        new_value: Dict snapshot of values AFTER the change.
        description: Optional free-text description.

    Returns:
        The created AuditLog instance.
    """
    return AuditLog.objects.create(
        user=user,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        previous_value=previous_value or {},
        new_value=new_value or {},
        description=description,
    )


def snapshot_question(question) -> dict:
    """Return a lightweight dict snapshot of a Question for audit storage."""
    return {
        "id": question.id,
        "text": question.text[:200],
        "status": question.status,
        "difficulty": question.difficulty,
        "bloom_level": question.bloom_level,
        "topic_id": question.topic_id,
        "is_active": question.is_active,
    }


def snapshot_blueprint(blueprint) -> dict:
    """Return a lightweight dict snapshot of an ExamBlueprint."""
    return {
        "id": blueprint.id,
        "title": blueprint.title,
        "course_id": blueprint.course_id,
        "total_questions": blueprint.total_questions,
        "duration_minutes": blueprint.duration_minutes,
        "pass_percentage": str(blueprint.pass_percentage),
        "marks_per_question": str(blueprint.marks_per_question),
        "difficulty_distribution": blueprint.difficulty_distribution,
        "is_active": blueprint.is_active,
    }


def snapshot_assignment(assignment) -> dict:
    """Return a lightweight dict snapshot of a TeacherCourseAssignment."""
    return {
        "id": assignment.id,
        "teacher_id": assignment.teacher_id,
        "teacher_username": assignment.teacher.username,
        "course_id": assignment.course_id,
        "course_name": assignment.course.name,
    }
