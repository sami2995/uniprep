import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "uniprep_backend.settings")
django.setup()

from django.contrib.auth import get_user_model
from exit_exams.models import Course, Domain, Topic, Question, SystemSettings
from analytics.models import LearningPath, LearningStep, ReadinessScore, Notification
from analytics.adaptive_learning_service import (
    select_topic_for_student,
    generate_learning_path,
    complete_step,
    finish_learning_path
)

User = get_user_model()

def run_tests():
    print("--- Starting Phase 4 Adaptive Learning Tests ---")

    # 1. Check SystemSettings fields
    settings = SystemSettings.get_solo()
    assert hasattr(settings, "mastery_threshold_accuracy"), "Missing mastery_threshold_accuracy"
    assert hasattr(settings, "mastery_minimum_attempts"), "Missing mastery_minimum_attempts"
    assert hasattr(settings, "quiz_unlock_score"), "Missing quiz_unlock_score"
    print("[OK] SystemSettings model fields verified.")

    # Create test student
    student, created = User.objects.get_or_create(
        username="test_adaptive_student",
        defaults={"role": "student", "email": "adaptive@test.com"}
    )

    # Clean up any existing paths for clean test
    LearningPath.objects.filter(student=student).delete()

    # 2. Test Path Generation & RESUME LOGIC
    path1 = generate_learning_path(student)
    assert path1 is not None, "Path 1 creation failed"
    assert path1.status == "in_progress", "Path status should be in_progress"
    assert path1.steps.count() == 4, "Path should have 4 steps"
    print(f"[OK] Path 1 created (ID: {path1.id}, Topic: {path1.topic})")

    # Call generate_learning_path second time -> RESUME LOGIC check
    path2 = generate_learning_path(student)
    assert path2.id == path1.id, "RESUME LOGIC FAILED! Duplicate path was created."
    print(f"[OK] RESUME LOGIC VERIFIED: Same path returned (ID: {path2.id})")

    # 3. Test Step Unlocking & Quiz Gate
    path, unlocked, msg = complete_step(path1, "summary")
    assert unlocked is True, "Summary step should complete"
    assert path.current_step == "flashcards", f"Expected current_step 'flashcards', got {path.current_step}"
    print("[OK] Summary step completed -> advanced to flashcards.")

    path, unlocked, msg = complete_step(path, "flashcards")
    assert unlocked is True, "Flashcards step should complete"
    assert path.current_step == "quiz", f"Expected current_step 'quiz', got {path.current_step}"
    print("[OK] Flashcards step completed -> advanced to quiz.")

    # Quiz Gate Test 1: Score 60% (< 70% threshold)
    path, unlocked, msg = complete_step(path, "quiz", score=60)
    assert unlocked is False, "Quiz score below threshold should NOT unlock next step"
    assert path.current_step == "quiz", "Current step should remain quiz on failure"
    print("[OK] Quiz Unlock Gate verified: Low score (60%) blocked advancement.")

    # Quiz Gate Test 2: Score 85% (>= 70% threshold)
    path, unlocked, msg = complete_step(path, "quiz", score=85)
    assert unlocked is True, "Quiz score >= threshold should unlock mini_mock"
    assert path.current_step == "mini_mock", "Current step should advance to mini_mock"
    print("[OK] Quiz Unlock Gate verified: Score (85%) unlocked mini_mock.")

    # Mini Mock step completion
    path, unlocked, msg = complete_step(path, "mini_mock", score=90)
    assert unlocked is True, "Mini mock step should complete"

    # 4. Test Finish & Readiness Recalculation
    finish_res, err = finish_learning_path(path)
    assert err is None, f"Finish error: {err}"
    assert finish_res["status"] == "completed", "Status should be completed"
    print(f"[OK] Finish verified! Readiness Delta: {finish_res['readiness_delta']}% (Before: {finish_res['before_readiness']}%, After: {finish_res['after_readiness']}%)")

    # Verify notifications created
    notifs = Notification.objects.filter(student=student)
    assert notifs.filter(notification_type="learning_path_ready").exists(), "Missing path_ready notification"
    assert notifs.filter(notification_type="learning_step_unlocked").exists(), "Missing step_unlocked notification"
    assert notifs.filter(notification_type="learning_path_completed").exists(), "Missing path_completed notification"
    print("[OK] Notifications verified for path ready, step unlocked, and path completed.")

    print("\nALL PHASE 4 ADAPTIVE LEARNING TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
