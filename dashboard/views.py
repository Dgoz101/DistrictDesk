from django.http import JsonResponse
from django.views import View
from django.views.generic import TemplateView

from accounts.mixins import AdminRequiredMixin

from .services import get_dashboard_data


class DashboardHomeView(AdminRequiredMixin, TemplateView):
    """Administrator dashboard with ticket and device analytics (FR-31–FR-35)."""
    template_name = 'dashboard/home.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['dashboard_payload'] = get_dashboard_data()
        return ctx


class DashboardSummaryApiView(AdminRequiredMixin, View):
    """Optional JSON summary for the same aggregates (lazy-loading or integrations)."""

    def get(self, request):
        return JsonResponse(get_dashboard_data())
