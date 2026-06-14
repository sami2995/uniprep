from django.contrib import admin
from .models import (
    StudyMaterial,
    DocumentChunk,
    AIChatSession,
    AIChatMessage,
    MaterialSummary,
    GeneratedFlashcard,
    GeneratedQuiz,
    GeneratedQuizQuestion
)


admin.site.register(StudyMaterial)
admin.site.register(DocumentChunk)
admin.site.register(AIChatSession)
admin.site.register(AIChatMessage)
admin.site.register(MaterialSummary)
admin.site.register(GeneratedFlashcard)
admin.site.register(GeneratedQuiz)
admin.site.register(GeneratedQuizQuestion)
