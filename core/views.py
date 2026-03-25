"""
Core views (e.g. health check for load balancers and monitoring).
"""
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import redirect


def home(request):
    """Send users to login, tickets, or dashboard based on auth and role."""
    if request.user.is_authenticated:
        if request.user.is_administrator:
            return redirect('dashboard:home')
        return redirect('tickets:list')
    return redirect('accounts:login')


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
