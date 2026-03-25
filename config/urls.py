"""
URL configuration for DistrictDesk.
"""
from django.contrib import admin
from django.urls import include, path

from core.views import health, home

urlpatterns = [
    path('', home, name='home'),
    path('admin/', admin.site.urls),
    path('health/', health),
    path('accounts/', include('accounts.urls')),
    path('tickets/', include('tickets.urls')),
    path('devices/', include('devices.urls')),
    path('dashboard/', include('dashboard.urls')),
]
