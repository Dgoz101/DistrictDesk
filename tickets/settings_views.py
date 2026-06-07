from django.contrib import messages
from django.db.models import ProtectedError
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView

from accounts.mixins import AdminRequiredMixin
from core.audit import log_create, log_delete, log_ticket_lookup_change
from core.models import AdminAuditEntry

from .forms import PriorityLevelForm, TicketCategoryForm
from .models import PriorityLevel, TicketCategory


def _lookup_fields(instance) -> dict[str, str]:
    fields = {'name': instance.name, 'sort_order': str(instance.sort_order)}
    if hasattr(instance, 'due_days'):
        fields['due_days'] = '' if instance.due_days is None else str(instance.due_days)
    return fields


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
        response = super().form_valid(form)
        log_create(
            self.request.user,
            entity_type=AdminAuditEntry.EntityType.TICKET_CATEGORY,
            instance=self.object,
            fields=_lookup_fields(self.object),
        )
        messages.success(self.request, 'Category created.')
        return response

    def get_success_url(self):
        return reverse('tickets:category_list')


class TicketCategoryUpdateView(AdminRequiredMixin, UpdateView):
    model = TicketCategory
    form_class = TicketCategoryForm
    template_name = 'tickets/ticketcategory_form.html'

    def form_valid(self, form):
        old_fields = _lookup_fields(self.get_object())
        response = super().form_valid(form)
        log_ticket_lookup_change(
            self.request.user,
            self.object,
            entity_type=AdminAuditEntry.EntityType.TICKET_CATEGORY,
            old_fields=old_fields,
            new_fields=_lookup_fields(self.object),
        )
        messages.success(self.request, 'Category updated.')
        return response

    def get_success_url(self):
        return reverse('tickets:category_list')


class TicketCategoryDeleteView(AdminRequiredMixin, DeleteView):
    model = TicketCategory
    template_name = 'tickets/ticketcategory_confirm_delete.html'
    success_url = reverse_lazy('tickets:category_list')

    def form_valid(self, form):
        label = self.object.name
        pk = self.object.pk
        try:
            self.object.delete()
            log_delete(
                self.request.user,
                entity_type=AdminAuditEntry.EntityType.TICKET_CATEGORY,
                object_label=label,
                object_id=pk,
            )
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
        response = super().form_valid(form)
        log_create(
            self.request.user,
            entity_type=AdminAuditEntry.EntityType.PRIORITY_LEVEL,
            instance=self.object,
            fields=_lookup_fields(self.object),
        )
        messages.success(self.request, 'Priority level created.')
        return response

    def get_success_url(self):
        return reverse('tickets:priority_list')


class PriorityLevelUpdateView(AdminRequiredMixin, UpdateView):
    model = PriorityLevel
    form_class = PriorityLevelForm
    template_name = 'tickets/prioritylevel_form.html'

    def form_valid(self, form):
        old_fields = _lookup_fields(self.get_object())
        response = super().form_valid(form)
        log_ticket_lookup_change(
            self.request.user,
            self.object,
            entity_type=AdminAuditEntry.EntityType.PRIORITY_LEVEL,
            old_fields=old_fields,
            new_fields=_lookup_fields(self.object),
        )
        messages.success(self.request, 'Priority level updated.')
        return response

    def get_success_url(self):
        return reverse('tickets:priority_list')


class PriorityLevelDeleteView(AdminRequiredMixin, DeleteView):
    model = PriorityLevel
    template_name = 'tickets/prioritylevel_confirm_delete.html'
    success_url = reverse_lazy('tickets:priority_list')

    def form_valid(self, form):
        label = self.object.name
        pk = self.object.pk
        try:
            self.object.delete()
            log_delete(
                self.request.user,
                entity_type=AdminAuditEntry.EntityType.PRIORITY_LEVEL,
                object_label=label,
                object_id=pk,
            )
            messages.success(self.request, 'Priority level deleted.')
        except ProtectedError:
            messages.error(
                self.request,
                'This priority cannot be deleted while tickets still reference it.',
            )
        return redirect(self.get_success_url())
