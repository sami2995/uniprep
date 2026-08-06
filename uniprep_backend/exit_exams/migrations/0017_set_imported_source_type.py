from django.db import migrations


def set_imported_source_type(apps, schema_editor):
    Question = apps.get_model("exit_exams", "Question")
    ExtractedQuestion = apps.get_model("exit_exams", "ExtractedQuestion")

    pdf_question_texts = set(
        ExtractedQuestion.objects.values_list("question_text", flat=True)
    )
    Question.objects.filter(text__in=pdf_question_texts).update(source_type="imported")


def reverse_set_imported_source_type(apps, schema_editor):
    Question = apps.get_model("exit_exams", "Question")
    ExtractedQuestion = apps.get_model("exit_exams", "ExtractedQuestion")

    pdf_question_texts = set(
        ExtractedQuestion.objects.values_list("question_text", flat=True)
    )
    Question.objects.filter(text__in=pdf_question_texts).update(source_type="manual")


class Migration(migrations.Migration):

    dependencies = [
        ("exit_exams", "0016_auto_20260806_1855"),
    ]

    operations = [
        migrations.RunPython(
            set_imported_source_type,
            reverse_code=reverse_set_imported_source_type,
        ),
    ]
