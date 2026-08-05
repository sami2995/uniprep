from django.contrib.auth import get_user_model
from django.db import close_old_connections
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


class JwtQueryParamAuthMiddleware:
    """
    Channels middleware that authenticates a WebSocket connection by reading
    a SimpleJWT access token from the `token` query-string parameter (since
    browsers cannot set Authorization headers on WebSocket handshakes).

    Stacks like AuthMiddlewareStack: yields to the inner application after
    setting scope["user"] to the authenticated CustomUser (or AnonymousUser).
    """

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        close_old_connections()
        scope = dict(scope)
        scope["user"] = self._authenticate(scope)
        return await self.inner(scope, receive, send)

    @staticmethod
    def _authenticate(scope):
        from django.contrib.auth.models import AnonymousUser

        User = get_user_model()
        query_string = scope.get("query_string", b"").decode("utf-8", "ignore")
        token = None
        for pair in query_string.split("&"):
            if pair.startswith("token="):
                token = pair.split("=", 1)[1]
                break

        if not token:
            return AnonymousUser()

        try:
            jwt_auth = JWTAuthentication()
            validated_token = jwt_auth.get_validated_token(token)
            user = jwt_auth.get_user(validated_token)
            return user or AnonymousUser()
        except (InvalidToken, TokenError, Exception):
            return AnonymousUser()