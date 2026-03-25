"""
Core views (e.g. health check for load balancers and monitoring).
"""
from django.db import connection
from django.http import JsonResponse


def health(request):
    """
    Health check endpoint for load balancers and monitoring.
    Returns 200 if the app is up; optionally checks DB connectivity.
    """
    try:
        connection.ensure_connection()
        return JsonResponse({'status': 'ok', 'database': 'connected'})
    except Exception:
        return JsonResponse(
            {'status': 'error', 'database': 'disconnected'},
            status=503
        )
