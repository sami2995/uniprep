from .models import Notification


def notify_user(student, title, message, notification_type, target_url=""):
    if isinstance(notification_type, Notification.NotificationType):
        notification_type = notification_type.value

    instance = Notification.objects.create(
        student=student,
        title=title,
        message=message,
        notification_type=notification_type,
        target_url=target_url or "",
    )
    instance._skip_signal = False
    return instance