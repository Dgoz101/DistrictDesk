from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from accounts.mixins import AdminRequiredMixin
from core.audit import log_create, log_delete, log_ticket_lookup_change
from core.models import AdminAuditEntry

from .forms import LocationForm
from .models import Location


def _location_fields(instance) -> dict[str, str]:
    return {'name': instance.name, 'description': instance.description or ''}


class LocationListView(AdminRequiredMixin, ListView):
    model = Location
    template_name = 'core/location_list.html'
    context_object_name = 'locations'
    paginate_by = 25

    def get_queryset(self):
        return Location.objects.order_by('name')


class LocationCreateView(AdminRequiredMixin, CreateView):
    model = Location
    form_class = LocationForm
    template_name = 'core/location_form.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        log_create(
            self.request.user,
            entity_type=AdminAuditEntry.EntityType.LOCATION,
            instance=self.object,
            fields=_location_fields(self.object),
        )
        messages.success(self.request, 'Location created.')
        return response

    def get_success_url(self):
        return reverse('core:location_list')


class LocationUpdateView(AdminRequiredMixin, UpdateView):
    model = Location
    form_class = LocationForm
    template_name = 'core/location_form.html'

    def form_valid(self, form):
        old_fields = _location_fields(self.get_object())
        response = super().form_valid(form)
        log_ticket_lookup_change(
            self.request.user,
            self.object,
            entity_type=AdminAuditEntry.EntityType.LOCATION,
            old_fields=old_fields,
            new_fields=_location_fields(self.object),
        )
        messages.success(self.request, 'Location updated.')
        return response

    def get_success_url(self):
        return reverse('core:location_list')


class LocationDeleteView(AdminRequiredMixin, DeleteView):
    model = Location
    template_name = 'core/location_confirm_delete.html'
    success_url = reverse_lazy('core:location_list')

    def form_valid(self, form):
        label = self.object.name
        pk = self.object.pk
        if self.object.tickets.exists() or self.object.devices.exists():
            messages.error(
                self.request,
                'This location cannot be deleted while tickets or devices still reference it.',
            )
            return redirect(self.success_url)
        self.object.delete()
        log_delete(
            self.request.user,
            entity_type=AdminAuditEntry.EntityType.LOCATION,
            object_label=label,
            object_id=pk,
        )
        messages.success(self.request, 'Location deleted.')
        return redirect(self.success_url)
