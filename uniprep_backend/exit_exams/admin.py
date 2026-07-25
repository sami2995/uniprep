from django.contrib import admin
from .models import *

admin.site.register(Department)
admin.site.register(Course)
admin.site.register(TeacherCourseAssignment)
admin.site.register(Domain)
admin.site.register(Topic)
admin.site.register(Question)
admin.site.register(Choice)
admin.site.register(MockExam)
admin.site.register(MockExamQuestion)
admin.site.register(ExamAttempt)
admin.site.register(AttemptDetail)
admin.site.register(ExamPdfImport)
admin.site.register(ExtractedQuestion)
admin.site.register(ExamBlueprint)
admin.site.register(ExamBlueprintDomainRule)
