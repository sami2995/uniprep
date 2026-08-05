from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from analytics.models import Notification
from analytics.notification_service import notify_user


class Command(BaseCommand):
    help = (
        "Send a WEEKLY_REMINDER notification to every active student who has not "
        "received one in the last 7 days. Schedule this via cron / Celery beat "
        "(e.g. weekly on Monday morning)."
    )

    def handle(self, *args, **options):
        User = get_user_model()
        week_ago = timezone.now() - timezone.timedelta(days=7)
        sent = 0

        students = User.objects.filter(role="student", is_active=True)
        for student in students:
            already = Notification.objects.filter(
                student=student,
                notification_type=Notification.NotificationType.WEEKLY_REMINDER,
                created_at__gte=week_ago,
            ).exists()
            if already:
                continue

            notify_user(
                student,
                title="Weekly Study Reminder",
                message=(
                    "Keep your momentum going! Log in to continue your learning "
                    "path, attempt a mock, or join a quiz battle."
                ),
                notification_type=Notification.NotificationType.WEEKLY_REMINDER,
                target_url="/student/dashboard",
            )
            sent += 1

        self.stdout.write(self.style.SUCCESS(f"Weekly reminders sent: {sent}"))