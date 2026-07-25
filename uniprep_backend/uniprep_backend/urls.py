from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from analytics.views import (
    notifications,
    mark_notification_read,
    unread_notification_count,
)


urlpatterns = [
    path("admin/", admin.site.urls),

    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    path("api/users/", include("users.urls")),
    path("api/admin/", include("exit_exams.admin_urls")),
    path("api/exit-exams/", include("exit_exams.urls")),
    path("api/analytics/", include("analytics.urls")),
    path("api/rag/", include("rag.urls")),
    path("api/collaboration/", include("collaboration.urls")),

    path("api/notifications/", notifications, name="notifications"),
    path(
        "api/notifications/read/<int:notification_id>/",
        mark_notification_read,
        name="mark-notification-read",
    ),
    path(
        "api/notifications/unread-count/",
        unread_notification_count,
        name="unread-notification-count",
    ),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
