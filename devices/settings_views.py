from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView

from accounts.mixins import AdminRequiredMixin

from .forms import DeviceCheckoutPolicyForm, DeviceFineTypeForm
from .models import DeviceCheckoutPolicy, DeviceFineType


class DeviceSettingsHubView(AdminRequiredMixin, TemplateView):
    """Links to fine types, late-fee policy, and related device settings."""
    template_name = 'devices/settings_hub.html'


class DeviceFineTypeListView(AdminRequiredMixin, ListView):
    model = DeviceFineType
    template_name = 'devices/finetype_list.html'
    context_object_name = 'fine_types'
    paginate_by = 50

    def get_queryset(self):
        return DeviceFineType.objects.order_by('sort_order', 'name')


class DeviceFineTypeCreateView(AdminRequiredMixin, CreateView):
    model = DeviceFineType
    form_class = DeviceFineTypeForm
    template_name = 'devices/finetype_form.html'

    def form_valid(self, form):
        from django.utils.text import slugify

        instance = form.save(commit=False)
        base = slugify(instance.name)[:50] or 'fine'
        code = base
        n = 1
        while DeviceFineType.objects.filter(code=code).exists():
            code = f'{base}-{n}'[:50]
            n += 1
        instance.code = code
        instance.is_system = False
        instance.save()
        messages.success(self.request, 'Fine type created.')
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse('devices:finetype_list')


class DeviceFineTypeUpdateView(AdminRequiredMixin, UpdateView):
    model = DeviceFineType
    form_class = DeviceFineTypeForm
    template_name = 'devices/finetype_form.html'

    def form_valid(self, form):
        messages.success(self.request, 'Fine type updated.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('devices:finetype_list')


class DeviceFineTypeDeleteView(AdminRequiredMixin, DeleteView):
    model = DeviceFineType
    template_name = 'devices/finetype_confirm_delete.html'
    success_url = reverse_lazy('devices:finetype_list')

    def form_valid(self, form):
        if self.object.is_system:
            messages.error(self.request, 'System fine types cannot be deleted.')
            return redirect(self.success_url)
        self.object.delete()
        messages.success(self.request, 'Fine type deleted.')
        return redirect(self.success_url)


class DeviceCheckoutPolicyUpdateView(AdminRequiredMixin, UpdateView):
    """Configure late-fee rules (per day, grace days, cap)."""
    model = DeviceCheckoutPolicy
    form_class = DeviceCheckoutPolicyForm
    template_name = 'devices/checkout_policy_form.html'

    def get_object(self, queryset=None):
        return DeviceCheckoutPolicy.get_solo()

    def form_valid(self, form):
        messages.success(self.request, 'Late fee policy saved.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('devices:settings_hub')


class DeviceFineMarkStatusView(AdminRequiredMixin, View):
    """POST: mark a fine paid or waived."""

    def post(self, request, fine_pk):
        from .fine_service import set_fine_status
        from .models import DeviceFine

        fine = get_object_or_404(DeviceFine.objects.select_related('checkout__device'), pk=fine_pk)
        action = request.POST.get('status')
        if action not in (DeviceFine.Status.PAID, DeviceFine.Status.WAIVED):
            messages.error(request, 'Invalid status.')
        else:
            set_fine_status(fine=fine, actor=request.user, new_status=action)
            label = 'paid' if action == DeviceFine.Status.PAID else 'waived'
            messages.success(request, f'Fine marked {label}.')
        device_pk = fine.checkout.device_id
        next_url = request.POST.get('next') or reverse('devices:detail', kwargs={'pk': device_pk})
        return redirect(next_url)
