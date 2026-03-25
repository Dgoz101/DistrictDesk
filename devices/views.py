from django.contrib import messages
from django.urls import reverse
from django.views.generic import CreateView, ListView, UpdateView

from accounts.mixins import AdminRequiredMixin

from .forms import DeviceForm
from .models import Device


class DeviceListView(AdminRequiredMixin, ListView):
    """Device inventory list (FR-26); administrators only."""
    model = Device
    template_name = 'devices/device_list.html'
    context_object_name = 'devices'
    paginate_by = 25

    def get_queryset(self):
        return Device.objects.select_related(
            'device_type', 'status', 'assigned_user', 'location'
        ).order_by('asset_tag')


class DeviceCreateView(AdminRequiredMixin, CreateView):
    """Create a device record (FR-27)."""
    model = Device
    form_class = DeviceForm
    template_name = 'devices/device_form.html'

    def form_valid(self, form):
        messages.success(self.request, 'Device created.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('devices:list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form_title'] = 'Add device'
        ctx['submit_label'] = 'Create device'
        return ctx


class DeviceUpdateView(AdminRequiredMixin, UpdateView):
    """Edit a device record (FR-27)."""
    model = Device
    form_class = DeviceForm
    template_name = 'devices/device_form.html'

    def form_valid(self, form):
        messages.success(self.request, 'Device updated.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('devices:list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form_title'] = f'Edit device: {self.object.asset_tag}'
        ctx['submit_label'] = 'Save changes'
        return ctx
