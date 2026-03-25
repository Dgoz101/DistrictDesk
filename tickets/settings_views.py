from django.contrib import messages
from django.db.models import ProtectedError
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView

from accounts.mixins import AdminRequiredMixin

from .forms import PriorityLevelForm, TicketCategoryForm
from .models import PriorityLevel, TicketCategory


class TicketSettingsHubView(AdminRequiredMixin, TemplateView):
    """Links to category and priority management (FR-39)."""
    template_name = 'tickets/settings_hub.html'


class TicketCategoryListView(AdminRequiredMixin, ListView):
    model = TicketCategory
    template_name = 'tickets/ticketcategory_list.html'
    context_object_name = 'categories'
    paginate_by = 25

    def get_queryset(self):
        return TicketCategory.objects.order_by('sort_order', 'name')


class TicketCategoryCreateView(AdminRequiredMixin, CreateView):
    model = TicketCategory
    form_class = TicketCategoryForm
    template_name = 'tickets/ticketcategory_form.html'

    def form_valid(self, form):
        messages.success(self.request, 'Category created.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('tickets:category_list')


class TicketCategoryUpdateView(AdminRequiredMixin, UpdateView):
    model = TicketCategory
    form_class = TicketCategoryForm
    template_name = 'tickets/ticketcategory_form.html'

    def form_valid(self, form):
        messages.success(self.request, 'Category updated.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('tickets:category_list')


class TicketCategoryDeleteView(AdminRequiredMixin, DeleteView):
    model = TicketCategory
    template_name = 'tickets/ticketcategory_confirm_delete.html'
    success_url = reverse_lazy('tickets:category_list')

    def form_valid(self, form):
        try:
            self.object.delete()
            messages.success(self.request, 'Category deleted.')
        except ProtectedError:
            messages.error(
                self.request,
                'This category cannot be deleted while tickets still reference it.',
            )
        return redirect(self.get_success_url())


class PriorityLevelListView(AdminRequiredMixin, ListView):
    model = PriorityLevel
    template_name = 'tickets/prioritylevel_list.html'
    context_object_name = 'priorities'
    paginate_by = 25

    def get_queryset(self):
        return PriorityLevel.objects.order_by('sort_order', 'name')


class PriorityLevelCreateView(AdminRequiredMixin, CreateView):
    model = PriorityLevel
    form_class = PriorityLevelForm
    template_name = 'tickets/prioritylevel_form.html'

    def form_valid(self, form):
        messages.success(self.request, 'Priority level created.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('tickets:priority_list')


class PriorityLevelUpdateView(AdminRequiredMixin, UpdateView):
    model = PriorityLevel
    form_class = PriorityLevelForm
    template_name = 'tickets/prioritylevel_form.html'

    def form_valid(self, form):
        messages.success(self.request, 'Priority level updated.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('tickets:priority_list')


class PriorityLevelDeleteView(AdminRequiredMixin, DeleteView):
    model = PriorityLevel
    template_name = 'tickets/prioritylevel_confirm_delete.html'
    success_url = reverse_lazy('tickets:priority_list')

    def form_valid(self, form):
        try:
            self.object.delete()
            messages.success(self.request, 'Priority level deleted.')
        except ProtectedError:
            messages.error(
                self.request,
                'This priority cannot be deleted while tickets still reference it.',
            )
        return redirect(self.get_success_url())
