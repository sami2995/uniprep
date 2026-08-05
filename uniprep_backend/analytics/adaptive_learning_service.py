from django.utils import timezone
from django.db import models, transaction
from exit_exams.models import SystemSettings, Topic, Course, Question, MockExam, MockExamQuestion, ExamAttempt, AttemptDetail, Choice
from exit_exams.services.question_selector import select_questions_for_topic
from analytics.models import (
    LearningPath,
    LearningStep,
    StudentTopicPerformance,
    SpacedRepetitionQueue,
    ReadinessScore,
    Notification
)
from analytics.notification_service import notify_user
from analytics.services import calculate_readiness_score, update_topic_performance, add_wrong_question_to_spaced_repetition


def select_topic_for_student(student):
    """
    Selects the optimal topic for a student's adaptive learning path.
    Enforces dynamic thresholds from SystemSettings (mastery_threshold_accuracy, mastery_minimum_attempts).
    
    Priority:
    1. Spaced Repetition high priority due items
    2. Weakest analytics topic
    3. Topic in lowest readiness course
    4. Lowest accuracy / unmastered topic fallback
    """
    settings = SystemSettings.get_solo()
    mastery_accuracy = settings.mastery_threshold_accuracy
    min_attempts = settings.mastery_minimum_attempts

    # Identify mastered topics to exclude
    mastered_topic_ids = set()
    all_perfs = StudentTopicPerformance.objects.filter(student=student)
    for perf in all_perfs:
        if perf.total_attempts >= min_attempts and perf.accuracy >= mastery_accuracy:
            mastered_topic_ids.add(perf.topic_id)

    # Priority 1: Spaced Repetition active due items
    due_sr_item = SpacedRepetitionQueue.objects.filter(
        student=student,
        is_active=True,
        next_review_date__lte=timezone.now().date()
    ).exclude(
        topic_id__in=mastered_topic_ids
    ).order_by("mastery_level", "next_review_date").first()

    if due_sr_item:
        return due_sr_item.topic.name, "high"

    # Priority 2: Weakest analytics topic
    weak_perf = StudentTopicPerformance.objects.filter(
        student=student,
        total_attempts__gt=0
    ).exclude(
        topic_id__in=mastered_topic_ids
    ).order_by("correct_attempts", "total_attempts").first()

    if weak_perf:
        priority = "high" if weak_perf.accuracy < 50 else "medium"
        return weak_perf.topic.name, priority

    # Priority 3: Topic from lowest readiness score course
    lowest_readiness = ReadinessScore.objects.filter(
        student=student
    ).order_by("score").first()

    if lowest_readiness:
        candidate_topic = Topic.objects.filter(
            domain__course=lowest_readiness.course
        ).exclude(
            id__in=mastered_topic_ids
        ).first()

        if candidate_topic:
            return candidate_topic.name, "medium"

    # Priority 4: Any non-mastered topic
    candidate_topic = Topic.objects.exclude(
        id__in=mastered_topic_ids
    ).first()

    if candidate_topic:
        return candidate_topic.name, "low"

    # Fallback if all topics are mastered or database is empty
    any_topic = Topic.objects.first()
    topic_name = any_topic.name if any_topic else "General Review"
    return topic_name, "low"


def generate_learning_path(student):
    """
    Implements mandatory RESUME LOGIC.
    If student has an active 'in_progress' LearningPath, returns it immediately.
    Otherwise, selects topic and creates path + 4 LearningStep rows.
    """
    existing = LearningPath.objects.filter(student=student, status='in_progress').first()
    if existing:
        return existing  # RESUME existing active path

    topic_name, priority = select_topic_for_student(student)

    path = LearningPath.objects.create(
        student=student,
        topic=topic_name,
        priority=priority,
        status='in_progress',
        current_step='summary'
    )

    for step_type in ['summary', 'flashcards', 'quiz', 'mini_mock']:
        LearningStep.objects.create(
            learning_path=path,
            step_type=step_type,
            completed=False
        )

    notify_user(
        student,
        title=f"New Learning Path: {topic_name}",
        message=f"Your personalized learning path for {topic_name} is ready.",
        notification_type=Notification.NotificationType.LEARNING_PATH_READY,
        target_url="/student/learning",
    )

    return path


def complete_step(learning_path, step_type, score=None):
    """
    Completes a step and handles sequential progress unlocking.
    Validates quiz score against SystemSettings.quiz_unlock_score.
    """
    settings = SystemSettings.get_solo()
    step = learning_path.steps.filter(step_type=step_type).first()

    if not step:
        return learning_path, False, f"Step '{step_type}' not found on this learning path."

    if step_type == 'quiz':
        if score is not None:
            step.score = float(score)

        if score is not None and score < settings.quiz_unlock_score:
            step.save()
            return (
                learning_path,
                False,
                f"Quiz score ({score}%) is below the required unlock threshold ({settings.quiz_unlock_score}%). Please retry."
            )

        step.completed = True
        step.completed_at = timezone.now()
        step.save()

        learning_path.current_step = 'mini_mock'
        learning_path.save()

        notify_user(
        learning_path.student,
        title=f"Mini Mock Unlocked: {learning_path.topic}",
        message=f"Congratulations! You unlocked the Mini Mock step for {learning_path.topic}.",
        notification_type=Notification.NotificationType.LEARNING_STEP_UNLOCKED,
        target_url="/student/learning",
    )

        return learning_path, True, "Quiz step completed successfully. Mini Mock unlocked!"

    # Summary and Flashcards steps
    step.completed = True
    step.completed_at = timezone.now()
    if score is not None:
        step.score = float(score)
    step.save()

    next_step_map = {
        'summary': 'flashcards',
        'flashcards': 'quiz',
        'mini_mock': 'mini_mock',
    }

    learning_path.current_step = next_step_map.get(step_type, 'quiz')
    learning_path.save()

    notify_user(
        learning_path.student,
        title=f"Step Completed: {step_type.title()}",
        message=f"You completed the {step_type} step for {learning_path.topic}.",
        notification_type=Notification.NotificationType.LEARNING_STEP_UNLOCKED,
        target_url="/student/learning",
    )

    return learning_path, True, f"{step_type.title()} step completed."


def finish_learning_path(learning_path):
    """
    Runs completion logic when all 4 steps are done.
    Recalculates readiness score, updates path status, updates Spaced Repetition queue,
    and returns readiness delta comparison.
    """
    incomplete_steps = learning_path.steps.filter(completed=False)
    if incomplete_steps.exists():
        return None, "Cannot finish path until all 4 steps are completed."

    # Identify course for readiness score calculation
    topic_obj = Topic.objects.filter(name=learning_path.topic).first()
    if topic_obj:
        course = topic_obj.domain.course
    else:
        course = Course.objects.first()

    before_score = 0.0
    if course:
        existing_readiness = ReadinessScore.objects.filter(
            student=learning_path.student,
            course=course
        ).first()
        if existing_readiness:
            before_score = float(existing_readiness.score)

        new_readiness_obj = calculate_readiness_score(learning_path.student, course)
        after_score = float(new_readiness_obj.score)
    else:
        after_score = before_score

    learning_path.status = 'completed'
    learning_path.completed_at = timezone.now()
    learning_path.save()

    # Update Spaced Repetition Queue entry if present
    if topic_obj:
        SpacedRepetitionQueue.objects.filter(
            student=learning_path.student,
            topic=topic_obj
        ).update(
            mastery_level=models.F('mastery_level') + 1,
            is_active=False
        )

    notify_user(
        learning_path.student,
        title=f"Learning Path Completed: {learning_path.topic}",
        message=f"Great job! You completed your learning path for {learning_path.topic}. Readiness score updated from {before_score}% to {after_score}%.",
        notification_type=Notification.NotificationType.LEARNING_PATH_COMPLETED,
        target_url="/student/learning",
    )

    delta = round(after_score - before_score, 2)
    return {
        "learning_path_id": learning_path.id,
        "topic": learning_path.topic,
        "status": learning_path.status,
        "before_readiness": before_score,
        "after_readiness": after_score,
        "readiness_delta": delta,
    }, None


QUIZ_QUESTION_COUNT = 5


def get_current_learning_path_topic(student):
    """Return the active LearningPath for a student, or None."""
    return LearningPath.objects.filter(student=student, status='in_progress').first()


def _student_question_payload(question):
    """Serialize a question for a student quiz (no correct answer exposed)."""
    return {
        "id": question.id,
        "text": question.text,
        "bloom_level": question.bloom_level,
        "difficulty": question.difficulty,
        "choices": [
            {"id": choice.id, "text": choice.text}
            for choice in question.choices.all()
        ],
    }


def generate_adaptive_quiz(student, topic_obj, count=QUIZ_QUESTION_COUNT):
    """
    Generate a real adaptive quiz for a topic using only approved, active questions.

    Returns:
        list of Question objects selected with adaptive priority.
    """
    selected = select_questions_for_topic(
        user=student,
        topic=topic_obj,
        count=count
    )
    return selected


def evaluate_adaptive_quiz(student, topic_obj, answers, duration_seconds=0):
    """
    Submit a real adaptive quiz, create MockExam/ExamAttempt/AttemptDetail records,
    update topic performance, and update spaced repetition.

    Args:
        student: the student user.
        topic_obj: the Topic being quizzed.
        answers: list of dicts [{question_id, selected_choice_id}].
        duration_seconds: optional quiz duration.

    Returns:
        dict with score, correct_count, total_questions, details.
    """
    # Validate the submitted answers are for the generated quiz questions.
    answer_map = {
        int(item.get("question_id")): item.get("selected_choice_id")
        for item in answers if item.get("question_id")
    }

    question_ids = set(answer_map.keys())
    questions = Question.objects.filter(
        id__in=question_ids,
        topic=topic_obj,
        status=Question.Status.APPROVED,
        is_active=True
    ).prefetch_related("choices")

    if questions.count() != len(question_ids):
        raise ValueError("One or more submitted questions are invalid or not approved.")

    course = topic_obj.domain.course

    with transaction.atomic():
        exam_number = MockExam.objects.filter(
            student=student,
            course=course
        ).count() + 1

        mock_exam = MockExam.objects.create(
            student=student,
            course=course,
            title=f"Adaptive Quiz - {topic_obj.name} {exam_number}",
            exam_number=exam_number,
            total_questions=len(question_ids),
            duration_minutes=0,
            status=MockExam.Status.GENERATED
        )

        for index, question in enumerate(questions, start=1):
            MockExamQuestion.objects.create(
                mock_exam=mock_exam,
                question=question,
                order=index
            )

        attempt = ExamAttempt.objects.create(
            mock_exam=mock_exam,
            student=student,
            status=ExamAttempt.Status.SUBMITTED,
            duration_seconds=duration_seconds,
            submitted_at=timezone.now()
        )

        correct_count = 0
        details = []

        for question in questions:
            selected_choice_id = answer_map.get(question.id)
            selected_choice = None
            is_correct = False

            if selected_choice_id:
                selected_choice = Choice.objects.filter(
                    id=selected_choice_id,
                    question=question
                ).first()
                if selected_choice:
                    is_correct = selected_choice.is_correct

            if is_correct:
                correct_count += 1

            AttemptDetail.objects.create(
                attempt=attempt,
                question=question,
                selected_choice=selected_choice,
                is_correct=is_correct,
                response_time_seconds=0
            )

            update_topic_performance(
                student=student,
                question=question,
                is_correct=is_correct,
                response_time_seconds=0
            )

            if not is_correct:
                add_wrong_question_to_spaced_repetition(
                    student=student,
                    question=question
                )

            correct_choice = question.choices.filter(is_correct=True).first()
            details.append({
                "question_id": question.id,
                "question": question.text,
                "selected_choice_id": selected_choice.id if selected_choice else None,
                "selected_answer": selected_choice.text if selected_choice else None,
                "correct_answer": correct_choice.text if correct_choice else None,
                "is_correct": is_correct,
                "explanation": question.explanation
            })

        total_questions = len(question_ids)
        score = round((correct_count / total_questions) * 100, 2) if total_questions else 0

        attempt.total_score = score
        attempt.save()

        mock_exam.status = MockExam.Status.SUBMITTED
        mock_exam.save()

    settings = SystemSettings.get_solo()

    return {
        "attempt_id": attempt.id,
        "score": score,
        "correct_count": correct_count,
        "total_questions": total_questions,
        "quiz_unlock_score": settings.quiz_unlock_score,
        "details": details,
    }
