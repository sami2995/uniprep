from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CourseViewSet, DomainViewSet, TopicViewSet, QuestionViewSet,
    ChoiceViewSet, MockExamViewSet, MockExamQuestionViewSet,
    ExamAttemptViewSet, AttemptDetailViewSet,generate_mock_exam,submit_mock_exam,ExamPdfImportViewSet,
ExtractedQuestionViewSet,process_exam_pdf_import,approve_extracted_question,ExamBlueprintViewSet,
ExamBlueprintDomainRuleViewSet,my_exam_results,exam_result_detail,admin_dashboard_stats,reject_extracted_question,auto_classify_extracted_questions,
bulk_approve_extracted_questions,question_availability_by_domain
)


router = DefaultRouter()

router.register("courses", CourseViewSet)
router.register("domains", DomainViewSet)
router.register("topics", TopicViewSet)
router.register("questions", QuestionViewSet)
router.register("choices", ChoiceViewSet)
router.register("mock-exams", MockExamViewSet, basename="mock-exams")
router.register("mock-exam-questions", MockExamQuestionViewSet)
router.register("exam-attempts", ExamAttemptViewSet, basename="exam-attempts")
router.register("attempt-details", AttemptDetailViewSet)
router.register("exam-pdf-imports", ExamPdfImportViewSet, basename="exam-pdf-imports")
router.register("extracted-questions", ExtractedQuestionViewSet, basename="extracted-questions")
router.register("exam-blueprints", ExamBlueprintViewSet, basename="exam-blueprints")
router.register("exam-blueprint-rules", ExamBlueprintDomainRuleViewSet, basename="exam-blueprint-rules")

urlpatterns = [
    path("generate-mock-exam/", generate_mock_exam, name="generate-mock-exam"),
    path("submit-mock-exam/", submit_mock_exam, name="submit-mock-exam"),
    path("my-results/", my_exam_results, name="my-exam-results"),
    path(
    "exam-pdf-imports/<int:import_id>/process/",
    process_exam_pdf_import,
    name="process-exam-pdf-import"
),
    path(
    "extracted-questions/<int:extracted_question_id>/approve/",
    approve_extracted_question,
    name="approve-extracted-question"
),
path(
    "my-results/<int:attempt_id>/",
    exam_result_detail,
    name="exam-result-detail"
),
path(
    "admin-dashboard/",
    admin_dashboard_stats,
    name="admin-dashboard-stats"
),
path(
    "extracted-questions/<int:extracted_question_id>/reject/",
    reject_extracted_question,
    name="reject-extracted-question"
),
path(
    "extracted-questions/auto-classify/",
    auto_classify_extracted_questions,
    name="auto-classify-extracted-questions"
),

path(
    "extracted-questions/bulk-approve/",
    bulk_approve_extracted_questions,
    name="bulk-approve-extracted-questions"
),


path(
    "question-availability/",
    question_availability_by_domain,
    name="question-availability"
),
    path("", include(router.urls)),
]