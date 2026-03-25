from django.urls import path

from .views import DashboardHomeView, DashboardSummaryApiView

app_name = 'dashboard'

urlpatterns = [
    path('', DashboardHomeView.as_view(), name='home'),
    path('api/summary/', DashboardSummaryApiView.as_view(), name='api_summary'),
]
