import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Notification
from .serializers import NotificationSerializer

logger = logging.getLogger(__name__)


def _get_channel_layer():
    try:
        from channels.layers import get_channel_layer
    except ImportError:
        return None, None
    try:
        from asgiref.sync import async_to_sync
    except ImportError:
        return None, None
    return get_channel_layer(), async_to_sync


@receiver(post_save, sender=Notification)
def broadcast_notification(sender, instance, created, **kwargs):
    if not created:
        return

    channel_layer, async_to_sync = _get_channel_layer()
    if channel_layer is None:
        return  # Django Channels not installed; client falls back to polling.

    payload = NotificationSerializer(instance).data
    group_name = f"notifications_{instance.student_id}"

    try:
        async_to_sync(channel_layer.group_send)(
            group_name,
            {"type": "notification.new", "payload": payload},
        )
    except Exception as broadcast_error:
        logger.warning(
            "Notification broadcast failed (non-fatal): %s",
            broadcast_error,
        )