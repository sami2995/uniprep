from django.contrib import admin
from .models import (
    StudentTopicPerformance,
    SpacedRepetitionQueue,
    ReadinessScore,
    FocusSession,
    Notification
)

admin.site.register(StudentTopicPerformance)
admin.site.register(SpacedRepetitionQueue)
admin.site.register(ReadinessScore)
admin.site.register(FocusSession)
admin.site.register(Notification)
