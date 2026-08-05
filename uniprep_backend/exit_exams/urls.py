from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DepartmentViewSet, CourseViewSet, TeacherCourseAssignmentViewSet,
    TeacherTopicAssignmentViewSet,
    DomainViewSet, TopicViewSet, QuestionViewSet,
    ChoiceViewSet, MockExamViewSet, MockExamQuestionViewSet,
    ExamAttemptViewSet, AttemptDetailViewSet, generate_mock_exam, submit_mock_exam,
    ExamPdfImportViewSet, ExtractedQuestionViewSet, process_exam_pdf_import,
    approve_extracted_question, ExamBlueprintViewSet, ExamBlueprintDomainRuleViewSet,
    my_exam_results, exam_result_detail, admin_dashboard_stats, reject_extracted_question,
    auto_classify_extracted_questions, bulk_approve_extracted_questions,
    submit_extracted_questions_for_approval,
    question_availability_by_domain, my_assigned_courses, my_assigned_topics,
    submit_question_for_approval, pending_question_approvals, approve_question, reject_question,
    # Phase 2
    check_question_duplicate,
    question_search,
    validate_blueprint,
    exam_bank_stats,
    audit_log_list,
)


router = DefaultRouter()

router.register("departments", DepartmentViewSet)
router.register("courses", CourseViewSet)
router.register(
    "teacher-course-assignments",
    TeacherCourseAssignmentViewSet,
    basename="teacher-course-assignments"
)
router.register(
    "teacher-topic-assignments",
    TeacherTopicAssignmentViewSet,
    basename="teacher-topic-assignments"
)
router.register("domains", DomainViewSet)
router.register("topics", TopicViewSet)
router.register("questions", QuestionViewSet)
router.register("choices", ChoiceViewSet, basename="choices")
router.register("mock-exams", MockExamViewSet, basename="mock-exams")
router.register("mock-exam-questions", MockExamQuestionViewSet)
router.register("exam-attempts", ExamAttemptViewSet, basename="exam-attempts")
router.register("attempt-details", AttemptDetailViewSet)
router.register("exam-pdf-imports", ExamPdfImportViewSet, basename="exam-pdf-imports")
router.register("extracted-questions", ExtractedQuestionViewSet, basename="extracted-questions")
router.register("exam-blueprints", ExamBlueprintViewSet, basename="exam-blueprints")
router.register("exam-blueprint-rules", ExamBlueprintDomainRuleViewSet, basename="exam-blueprint-rules")

urlpatterns = [
    # Teacher course assignment (teacher sees own courses) — legacy, kept for backward compatibility
    path("my-assigned-courses/", my_assigned_courses, name="my-assigned-courses"),
    # Teacher topic assignment (teacher sees assigned topics) — canonical
    path("my-assigned-topics/", my_assigned_topics, name="my-assigned-topics"),

    # Question workflow
    path("questions/pending-approvals/", pending_question_approvals, name="pending-question-approvals"),
    path("questions/<int:question_id>/submit/", submit_question_for_approval, name="submit-question-for-approval"),
    path("questions/<int:question_id>/approve/", approve_question, name="approve-question"),
    path("questions/<int:question_id>/reject/", reject_question, name="reject-question"),

    # Phase 2 — Duplicate detection & search (must be BEFORE router to avoid conflict with <pk> routes)
    path("questions/check-duplicate/", check_question_duplicate, name="check-question-duplicate"),
    path("questions/search/", question_search, name="question-search"),

    # Mock exam
    path("generate-mock-exam/", generate_mock_exam, name="generate-mock-exam"),
    path("submit-mock-exam/", submit_mock_exam, name="submit-mock-exam"),
    path("my-results/", my_exam_results, name="my-exam-results"),
    path("my-results/<int:attempt_id>/", exam_result_detail, name="exam-result-detail"),

    # PDF imports
    path("exam-pdf-imports/<int:import_id>/process/", process_exam_pdf_import, name="process-exam-pdf-import"),
    path("extracted-questions/<int:extracted_question_id>/approve/", approve_extracted_question, name="approve-extracted-question"),
    path("extracted-questions/<int:extracted_question_id>/reject/", reject_extracted_question, name="reject-extracted-question"),
    path("extracted-questions/submit/", submit_extracted_questions_for_approval, name="submit-extracted-questions"),
    path("extracted-questions/auto-classify/", auto_classify_extracted_questions, name="auto-classify-extracted-questions"),
    path("extracted-questions/bulk-approve/", bulk_approve_extracted_questions, name="bulk-approve-extracted-questions"),

    # Dashboard & stats
    path("admin-dashboard/", admin_dashboard_stats, name="admin-dashboard-stats"),
    path("question-availability/", question_availability_by_domain, name="question-availability"),

    # Phase 2 — Blueprint validation
    path("exam-blueprints/<int:blueprint_id>/validate/", validate_blueprint, name="validate-blueprint"),

    # Phase 2 — Exam bank stats (department head)
    path("exam-bank-stats/", exam_bank_stats, name="exam-bank-stats"),

    # Phase 2 — Audit logs
    path("audit-logs/", audit_log_list, name="audit-logs"),

    # System Admin endpoints
    path("admin/", include("exit_exams.admin_urls")),

    # Router-registered ViewSet URLs (must be last)
    path("", include(router.urls)),
]
