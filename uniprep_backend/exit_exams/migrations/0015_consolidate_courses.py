from django.db import migrations
from django.db.models import Max

def consolidate_courses(apps, schema_editor):
    Course = apps.get_model("exit_exams", "Course")
    Domain = apps.get_model("exit_exams", "Domain")
    MockExam = apps.get_model("exit_exams", "MockExam")
    ExamBlueprint = apps.get_model("exit_exams", "ExamBlueprint")
    ExamPdfImport = apps.get_model("exit_exams", "ExamPdfImport")
    
    try:
        ReadinessScore = apps.get_model("analytics", "ReadinessScore")
    except LookupError:
        ReadinessScore = None

    try:
        FocusSession = apps.get_model("analytics", "FocusSession")
    except LookupError:
        FocusSession = None

    canonical_cs = Course.objects.filter(id=2).first()
    if canonical_cs:
        # 1. Reassign MockExams safely with renumbering to avoid unique(student, course, exam_number) collisions
        c1_exams = MockExam.objects.filter(course_id=1).order_by("student_id", "exam_number")
        for exam in c1_exams:
            max_num = MockExam.objects.filter(
                student_id=exam.student_id,
                course_id=2
            ).aggregate(Max("exam_number"))["exam_number__max"] or 0

            exam.course_id = 2
            exam.exam_number = max_num + 1
            exam.save()

        # 2. Reassign ExamBlueprints & ExamPdfImports
        ExamBlueprint.objects.filter(course_id=1).update(course_id=2)
        ExamPdfImport.objects.filter(course_id=1).update(course_id=2)

        # 3. Handle ReadinessScore safely
        if ReadinessScore:
            for rs in ReadinessScore.objects.filter(course_id=1):
                if ReadinessScore.objects.filter(student_id=rs.student_id, course_id=2).exists():
                    rs.delete()
                else:
                    rs.course_id = 2
                    rs.save()

        # 4. Handle FocusSession
        if FocusSession:
            FocusSession.objects.filter(course_id=1).update(course_id=2)

        # 5. Delete Course id=1
        Course.objects.filter(id=1).delete()

    # Clean up Course id=18 and Domain id=25
    Domain.objects.filter(id=25).delete()
    ExamPdfImport.objects.filter(course_id=18).delete()
    Course.objects.filter(id=18).delete()

    # Clean up Course id=16 and its PDF import
    ExamPdfImport.objects.filter(course_id=16).delete()
    Course.objects.filter(id=16).delete()

    # Rename Course id=15 to 'Business Administration BSc Exit Exam'
    ba_course = Course.objects.filter(id=15).first()
    if ba_course:
        ba_course.name = "Business Administration BSc Exit Exam"
        ba_course.save()

def reverse_consolidate_courses(apps, schema_editor):
    Course = apps.get_model("exit_exams", "Course")
    ba_course = Course.objects.filter(id=15).first()
    if ba_course:
        ba_course.name = "2016 Exit Exam"
        ba_course.save()

class Migration(migrations.Migration):

    dependencies = [
        ("exit_exams", "0014_systemsettings_restrict_blueprint_official"),
    ]

    operations = [
        migrations.RunPython(consolidate_courses, reverse_consolidate_courses),
    ]
