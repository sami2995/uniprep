import logging
import django.db.utils
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        logger.exception("Unhandled exception in API request: %s", exc)

        if isinstance(exc, (django.db.utils.OperationalError, django.db.utils.ProgrammingError, django.db.utils.DatabaseError)):
            error_msg = str(exc)
            if "doesn't exist" in error_msg or "Table" in error_msg or "relation" in error_msg:
                detail = (
                    "Database tables are not migrated yet. "
                    "Please run migrations on Render (or set USE_SQLITE=True in Render environment variables)."
                )
            elif "2013" in error_msg or "Lost connection" in error_msg:
                detail = (
                    "Lost connection to MySQL database. "
                    "The database server may be asleep, unreachable, or requires SSL. "
                    "Check DB_HOST / DB_SSL or set USE_SQLITE=True in Render."
                )
            elif "2003" in error_msg or "Can't connect" in error_msg:
                detail = (
                    "Cannot connect to MySQL server. "
                    "Please verify DB_HOST, DB_PORT, and DB_USER in Render environment variables."
                )
            elif "1045" in error_msg or "Access denied" in error_msg:
                detail = "Database authentication failed: incorrect DB_USER or DB_PASSWORD."
            else:
                detail = f"Database error: {error_msg}"

            return Response(
                {"detail": detail, "error_type": exc.__class__.__name__},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {"detail": f"Internal server error: {str(exc)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return response
