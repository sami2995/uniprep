"""
ASGI config for uniprep_backend project.

Layers a Channels websocket router (user-authenticated) on top of the standard
Django HTTP/ASGI application so that realtime notification pushes can run.
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "uniprep_backend.settings")

from analytics.routing import websocket_urlpatterns  # noqa: E402
from analytics.ws_middleware import JwtQueryParamAuthMiddleware  # noqa: E402

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": JwtQueryParamAuthMiddleware(URLRouter(websocket_urlpatterns)),
    }
)