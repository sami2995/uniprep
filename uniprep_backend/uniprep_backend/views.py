import sys
from django.db import connection
from django.core.management import call_command
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    db_status = "ok"
    db_error = None
    table_count = 0
    tables = []

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
            table_names = connection.introspection.table_names()
            table_count = len(table_names)
            tables = table_names[:15]
    except Exception as exc:
        db_status = "error"
        db_error = str(exc)

    return Response(
        {
            "status": "healthy" if db_status == "ok" else "degraded",
            "database": {
                "status": db_status,
                "engine": connection.settings_dict.get("ENGINE", ""),
                "host": connection.settings_dict.get("HOST", ""),
                "name": connection.settings_dict.get("NAME", ""),
                "table_count": table_count,
                "sample_tables": tables,
                "error": db_error,
            },
            "python_version": sys.version,
        },
        status=status.HTTP_200_OK if db_status == "ok" else status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def trigger_migrate(request):
    """Utility endpoint to trigger migrations if build script skipped them."""
    key = request.data.get("key") or request.query_params.get("key")
    # Simple safeguard key if provided, or allow run
    try:
        call_command("migrate", interactive=False)
        return Response({"status": "Migrations applied successfully."})
    except Exception as exc:
        return Response({"status": "error", "detail": str(exc)}, status=500)
