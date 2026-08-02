import random

from django.db.models import QuerySet

from exit_exams.models import Question, AttemptDetail


DEFAULT_APPROVED_FILTER = {
    "status": Question.Status.APPROVED,
    "is_active": True,
}


def _approved_queryset(base_qs):
    """Return only approved and active questions from a base queryset."""
    return base_qs.filter(**DEFAULT_APPROVED_FILTER)


def _user_department(user):
    """Return the user's department if they are authenticated, else None."""
    if not user or not user.is_authenticated:
        return None
    return getattr(user, "department", None)


def rank_questions_for_student(user, queryset):
    """
    Rank questions by consistent adaptive priority.

    Priority:
      1. Unseen questions — the student has never submitted an answer for them.
      2. Previously answered incorrectly.
      3. Remaining approved questions (answered correctly before).

    Args:
        user: the student (may be None for anonymous/global ranking).
        queryset: QuerySet of Question objects (should already be filtered).

    Returns:
        List of Question objects in priority order.
    """
    questions = list(
        queryset.select_related(
            "topic",
            "topic__domain",
            "topic__domain__course"
        ).prefetch_related("choices")
    )

    if not questions:
        return []

    if not user or not user.is_authenticated:
        random.shuffle(questions)
        return questions

    question_ids = [q.id for q in questions]

    attempted_ids = set(
        AttemptDetail.objects.filter(
            attempt__student=user,
            question_id__in=question_ids
        ).values_list("question_id", flat=True).distinct()
    )

    wrong_ids = set(
        AttemptDetail.objects.filter(
            attempt__student=user,
            question_id__in=question_ids,
            is_correct=False
        ).values_list("question_id", flat=True).distinct()
    )

    unseen_questions = [q for q in questions if q.id not in attempted_ids]
    wrong_questions = [q for q in questions if q.id in wrong_ids]
    remaining_questions = [
        q for q in questions
        if q.id in attempted_ids and q.id not in wrong_ids
    ]

    random.shuffle(unseen_questions)
    random.shuffle(wrong_questions)
    random.shuffle(remaining_questions)

    return unseen_questions + wrong_questions + remaining_questions


def select_questions_for_topic(user, topic, count):
    """
    Select `count` approved, active questions for a topic using adaptive priority.

    Raises:
        ValueError: if there are not enough approved active questions.
    """
    department = _user_department(user)
    if not department:
        return []

    all_questions = Question.objects.filter(
        topic=topic,
        topic__domain__course__department=department,
        **DEFAULT_APPROVED_FILTER
    ).select_related("topic", "topic__domain").prefetch_related("choices")

    available_count = all_questions.count()
    if available_count < count:
        raise ValueError(
            f"Not enough approved questions are available for this topic. "
            f"Available: {available_count}, required: {count}."
        )

    ranked = rank_questions_for_student(user, all_questions)
    return ranked[:count]


def select_questions_for_domain(user, domain, count):
    """
    Select `count` approved, active questions for a domain.

    Priority:
      1. Unseen questions
      2. Previously incorrect questions
      3. Remaining approved questions

    Raises:
        ValueError: if there are not enough approved active questions.
    """
    department = _user_department(user)
    if not department:
        return []

    all_questions = Question.objects.filter(
        topic__domain=domain,
        topic__domain__course__department=department,
        **DEFAULT_APPROVED_FILTER
    ).select_related("topic", "topic__domain").prefetch_related("choices")

    available_count = all_questions.count()
    if available_count < count:
        raise ValueError(
            f"Not enough approved questions are available for domain '{domain.name}'. "
            f"Available: {available_count}, required: {count}."
        )

    ranked = rank_questions_for_student(user, all_questions)
    return ranked[:count]


def select_questions_for_course(user, course, total_questions):
    """
    Select `total_questions` approved, active questions across a whole course.

    Priority:
      1. Unseen questions
      2. Previously incorrect questions
      3. Remaining approved questions

    Raises:
        ValueError: if there are not enough approved active questions.
    """
    department = _user_department(user)
    if not department:
        return []

    all_questions = Question.objects.filter(
        topic__domain__course=course,
        topic__domain__course__department=department,
        **DEFAULT_APPROVED_FILTER
    ).select_related("topic", "topic__domain").prefetch_related("choices")

    available_count = all_questions.count()
    if available_count < total_questions:
        raise ValueError(
            f"Not enough approved questions are available for this course. "
            f"Available: {available_count}, requested: {total_questions}."
        )

    ranked = rank_questions_for_student(user, all_questions)
    return ranked[:total_questions]


def select_questions_for_blueprint(user, blueprint):
    """
    Generate an exam using blueprint topic/domain rules.

    Selection process:
      1. Select questions from the exact required topic.
      2. Fill shortages using other questions in the same domain.
      3. Fill remaining shortages using the whole course.
      4. Never duplicate a question inside the same mock exam.

    Returns:
        selected_questions, allocation_report, warnings
    """
    from exit_exams.models import ExamBlueprintTopicRule

    topic_rules = list(
        ExamBlueprintTopicRule.objects.filter(
            blueprint=blueprint
        ).select_related(
            "topic",
            "topic__domain",
            "topic__domain__course"
        ).order_by(
            "topic__domain__name",
            "topic__name"
        )
    )

    domain_rules = list(
        blueprint.domain_rules.select_related("domain").order_by("domain__name")
    )

    if not topic_rules and not domain_rules:
        raise ValueError("This blueprint has no domain or topic rules.")

    # Domain-only blueprint path
    if not topic_rules and domain_rules:
        domain_rule_total = sum(r.number_of_questions for r in domain_rules)
        if domain_rule_total != blueprint.total_questions:
            raise ValueError(
                f"Blueprint total_questions is {blueprint.total_questions}, "
                f"but domain rules add up to {domain_rule_total}."
            )

        department = _user_department(user)
        if not department:
            raise ValueError("Student has no department assigned; cannot generate blueprint exam.")

        selected_ids = set()
        selected_questions = []
        allocation_report = []
        warnings = []

        for rule in domain_rules:
            domain_qs = Question.objects.filter(
                topic__domain=rule.domain,
                topic__domain__course__department=department,
                **DEFAULT_APPROVED_FILTER
            ).exclude(id__in=selected_ids)

            ranked = rank_questions_for_student(user, domain_qs)
            chosen = list(ranked[:rule.number_of_questions])
            selected_questions.extend(chosen)
            selected_ids.update(q.id for q in chosen)

            if len(chosen) < rule.number_of_questions:
                shortage = rule.number_of_questions - len(chosen)
                warnings.append({
                    "domain": rule.domain.name,
                    "required": rule.number_of_questions,
                    "allocated": len(chosen),
                    "shortage": shortage
                })

            allocation_report.append({
                "domain": rule.domain.name,
                "required": rule.number_of_questions,
                "selected_total": len(chosen)
            })

        if len(selected_questions) < blueprint.total_questions:
            remaining_needed = blueprint.total_questions - len(selected_questions)
            course_qs = Question.objects.filter(
                topic__domain__course=blueprint.course,
                topic__domain__course__department=department,
                **DEFAULT_APPROVED_FILTER
            ).exclude(id__in=selected_ids)

            fallback = list(
                rank_questions_for_student(user, course_qs)[:remaining_needed]
            )
            selected_questions.extend(fallback)

        if len(selected_questions) < blueprint.total_questions:
            raise ValueError(
                f"Not enough approved questions available to fulfill blueprint. "
                f"Generated {len(selected_questions)} of {blueprint.total_questions}."
            )

        random.shuffle(selected_questions)
        return selected_questions, allocation_report, warnings

    # Topic-rule blueprint path
    department = _user_department(user)
    if not department:
        raise ValueError("Student has no department assigned; cannot generate blueprint exam.")

    topic_rule_total = sum(rule.question_count for rule in topic_rules)

    if topic_rule_total != blueprint.total_questions:
        raise ValueError(
            f"Blueprint total_questions is {blueprint.total_questions}, "
            f"but topic rules add up to {topic_rule_total}."
        )

    total_available = Question.objects.filter(
        topic__domain__course=blueprint.course,
        topic__domain__course__department=department,
        **DEFAULT_APPROVED_FILTER
    ).count()

    if total_available < blueprint.total_questions:
        raise ValueError(
            f"Not enough approved questions available for this blueprint. "
            f"Available: {total_available}, required: {blueprint.total_questions}."
        )

    selected_by_rule = {}
    selected_ids = set()
    allocation_report = []
    warnings = []

    # Pass 1: allocate each topic its exact questions before using fallbacks.
    for rule in topic_rules:
        topic_queryset = Question.objects.filter(
            topic=rule.topic,
            topic__domain__course__department=department,
            **DEFAULT_APPROVED_FILTER
        ).exclude(id__in=selected_ids)

        ranked_questions = rank_questions_for_student(user, topic_queryset)
        exact_questions = ranked_questions[:rule.question_count]

        selected_by_rule[rule.id] = list(exact_questions)
        selected_ids.update(q.id for q in exact_questions)

    # Pass 2: fill topic shortages from same-domain, then whole-course.
    for rule in topic_rules:
        topic = rule.topic
        required = rule.question_count

        selected_for_rule = selected_by_rule[rule.id]
        exact_count = len(selected_for_rule)
        domain_fallback_count = 0
        course_fallback_count = 0

        shortage = required - len(selected_for_rule)

        # Same-domain fallback
        if shortage > 0:
            domain_queryset = Question.objects.filter(
                topic__domain=topic.domain,
                topic__domain__course__department=department,
                **DEFAULT_APPROVED_FILTER
            ).exclude(id__in=selected_ids)

            domain_fallback = rank_questions_for_student(
                user, domain_queryset
            )[:shortage]

            selected_for_rule.extend(domain_fallback)
            selected_ids.update(q.id for q in domain_fallback)
            domain_fallback_count = len(domain_fallback)
            shortage = required - len(selected_for_rule)

        # Whole-course fallback
        if shortage > 0:
            course_queryset = Question.objects.filter(
                topic__domain__course=blueprint.course,
                topic__domain__course__department=department,
                **DEFAULT_APPROVED_FILTER
            ).exclude(id__in=selected_ids)

            course_fallback = rank_questions_for_student(
                user, course_queryset
            )[:shortage]

            selected_for_rule.extend(course_fallback)
            selected_ids.update(q.id for q in course_fallback)
            course_fallback_count = len(course_fallback)
            shortage = required - len(selected_for_rule)


        if shortage > 0:
            raise ValueError(
                f"Could not allocate enough approved questions for "
                f"topic '{topic.name}'. "
                f"Required: {required}, selected: {len(selected_for_rule)}."
            )

        if domain_fallback_count or course_fallback_count:
            warnings.append({
                "topic": topic.name,
                "domain": topic.domain.name,
                "required": required,
                "exact_topic_questions": exact_count,
                "domain_fallback_questions": domain_fallback_count,
                "course_fallback_questions": course_fallback_count,
            })

        allocation_report.append({
            "domain": topic.domain.name,
            "topic": topic.name,
            "required": required,
            "exact_topic_questions": exact_count,
            "domain_fallback_questions": domain_fallback_count,
            "course_fallback_questions": course_fallback_count,
            "selected_total": len(selected_for_rule),
        })

    selected_questions = []
    for rule in topic_rules:
        selected_questions.extend(selected_by_rule[rule.id])

    if len(selected_questions) != blueprint.total_questions:
        raise ValueError(
            f"Blueprint generated {len(selected_questions)} "
            f"questions instead of {blueprint.total_questions}."
        )

    random.shuffle(selected_questions)

    return selected_questions, allocation_report, warnings
